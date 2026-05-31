from __future__ import annotations

import argparse
import json
import re
import sys
from collections.abc import Sequence
from contextlib import suppress
from datetime import UTC, datetime
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

from realtyscope.database.persistence import PersistedIngestionResult, persist_ingestion_batch
from realtyscope.database.session import (
    create_database_engine,
    create_session_factory,
    session_scope,
)
from realtyscope.ingestion.contracts import IngestionBatch
from realtyscope.ingestion.domclick import DomclickCollectorConfig, parse_domclick_payload

DOMCLICK_SOURCE_NAME = "domclick"
SUPPORTED_SOURCE_TYPES = {"domclick_html", "domclick_json", "domclick_snapshot_dir"}


class _JsonScriptCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.payloads: list[str] = []
        self._capturing = False
        self._chunks: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "script":
            return
        attr_map = {name.lower(): value or "" for name, value in attrs}
        script_type = attr_map.get("type", "").lower()
        script_id = attr_map.get("id", "")
        script_src = attr_map.get("src", "")
        if "json" not in script_type and script_id != "__NEXT_DATA__" and script_src:
            return
        self._capturing = True
        self._chunks = []

    def handle_data(self, data: str) -> None:
        if self._capturing:
            self._chunks.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() != "script" or not self._capturing:
            return
        payload = "".join(self._chunks).strip()
        if payload:
            self.payloads.append(payload)
        self._capturing = False
        self._chunks = []


def _parse_domclick_payload(
    payload: dict[str, Any] | list[Any],
    *,
    source_url: str,
    observed_at: datetime | None,
    max_records: int,
) -> IngestionBatch:
    return parse_domclick_payload(
        payload,
        source_url=source_url,
        observed_at=observed_at or datetime.now(UTC),
        config=DomclickCollectorConfig(max_records=max_records),
    )


def load_domclick_json_snapshot(
    path: Path,
    *,
    observed_at: datetime | None = None,
    max_records: int = 100,
) -> IngestionBatch:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict | list):
        raise ValueError("Domclick JSON snapshot must contain a JSON object or array")
    return _parse_domclick_payload(
        payload,
        source_url=path.resolve().as_uri(),
        observed_at=observed_at,
        max_records=max_records,
    )


def load_domclick_html_snapshot(
    path: Path,
    *,
    observed_at: datetime | None = None,
    max_records: int = 100,
) -> IngestionBatch:
    collector = _JsonScriptCollector()
    collector.feed(path.read_text(encoding="utf-8"))
    for script_payload in collector.payloads:
        payload = _load_script_payload(script_payload)
        if payload is None:
            continue
        if not isinstance(payload, dict | list):
            continue
        batch = _parse_domclick_payload(
            payload,
            source_url=path.resolve().as_uri(),
            observed_at=observed_at,
            max_records=max_records,
        )
        if batch.records_seen:
            return batch
    raise ValueError("Domclick HTML snapshot does not contain parseable embedded listing JSON")


def _load_script_payload(script_payload: str) -> dict[str, Any] | list[Any] | None:
    try:
        payload = json.loads(script_payload)
    except json.JSONDecodeError:
        payload = _extract_ssr_state_payload(script_payload)
    return payload if isinstance(payload, dict | list) else None


def _extract_ssr_state_payload(script_payload: str) -> dict[str, Any] | list[Any] | None:
    marker = "window.__SSR_STATE__="
    marker_index = script_payload.find(marker)
    if marker_index < 0:
        return None

    object_start = script_payload.find("{", marker_index + len(marker))
    if object_start < 0:
        return None
    object_end = _find_balanced_json_object_end(script_payload, object_start)
    if object_end is None:
        return None

    object_text = script_payload[object_start : object_end + 1]
    object_text = re.sub(r"(?<=[\[:,])\s*undefined\s*(?=[,}\]])", "null", object_text)
    try:
        payload = json.loads(object_text)
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict | list) else None


def _find_balanced_json_object_end(text: str, start: int) -> int | None:
    depth = 0
    in_string = False
    escaped = False
    for index in range(start, len(text)):
        char = text[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return index
    return None


def load_domclick_snapshot_directory(
    path: Path,
    *,
    observed_at: datetime | None = None,
    max_records: int = 100,
) -> IngestionBatch:
    if not path.is_dir():
        raise ValueError("Domclick snapshot directory source_path must be a directory")

    raw_listings = []
    normalized_listings = []
    rejected_listings = []
    files_seen = 0

    for snapshot_file in _iter_domclick_snapshot_files(path):
        remaining_records = max_records - len(normalized_listings)
        if remaining_records <= 0:
            break
        try:
            batch = _load_domclick_snapshot_file(
                snapshot_file,
                observed_at=observed_at,
                max_records=remaining_records,
            )
        except ValueError:
            continue
        if batch.records_seen == 0:
            continue
        files_seen += 1
        raw_listings.extend(batch.raw_listings)
        normalized_listings.extend(batch.normalized_listings)
        rejected_listings.extend(batch.rejected_listings)

    if files_seen == 0:
        raise ValueError(
            "Domclick snapshot directory does not contain parseable JSON or HTML files"
        )

    return IngestionBatch(
        raw_listings=tuple(raw_listings),
        normalized_listings=tuple(normalized_listings),
        rejected_listings=tuple(rejected_listings),
    )


def _iter_domclick_snapshot_files(path: Path) -> list[Path]:
    supported_suffixes = {".htm", ".html", ".json"}
    return sorted(
        candidate
        for candidate in path.rglob("*")
        if candidate.is_file()
        and candidate.name.lower() != "manifest.json"
        and candidate.suffix.lower() in supported_suffixes
    )


def _load_domclick_snapshot_file(
    path: Path,
    *,
    observed_at: datetime | None,
    max_records: int,
) -> IngestionBatch:
    suffix = path.suffix.lower()
    if suffix == ".json":
        return load_domclick_json_snapshot(path, observed_at=observed_at, max_records=max_records)
    if suffix in {".htm", ".html"}:
        return load_domclick_html_snapshot(path, observed_at=observed_at, max_records=max_records)
    raise ValueError(f"Unsupported Domclick snapshot file suffix: {path.suffix}")


def load_real_source_snapshot(
    *,
    source_type: str,
    source_path: Path,
    max_records: int = 100,
) -> IngestionBatch:
    if source_type not in SUPPORTED_SOURCE_TYPES:
        supported = ", ".join(sorted(SUPPORTED_SOURCE_TYPES))
        raise ValueError(f"Unsupported source_type={source_type!r}; supported: {supported}")

    if source_type == "domclick_html":
        return load_domclick_html_snapshot(source_path, max_records=max_records)
    if source_type == "domclick_json":
        return load_domclick_json_snapshot(source_path, max_records=max_records)
    if source_type == "domclick_snapshot_dir":
        return load_domclick_snapshot_directory(source_path, max_records=max_records)
    raise AssertionError(f"Unhandled source_type={source_type!r}")  # pragma: no cover


def persist_real_source_snapshot(
    *,
    source_type: str,
    source_path: Path,
    database_url: str | None = None,
    max_records: int = 100,
) -> PersistedIngestionResult:
    batch = load_real_source_snapshot(
        source_type=source_type,
        source_path=source_path,
        max_records=max_records,
    )

    engine = create_database_engine(database_url)
    session_factory = create_session_factory(engine)
    with session_scope(session_factory) as session:
        return persist_ingestion_batch(
            session,
            batch,
            source_name=DOMCLICK_SOURCE_NAME,
            source_type="listing",
        )


def _result_payload(
    *,
    source_type: str,
    source_path: Path,
    result: PersistedIngestionResult,
) -> dict[str, Any]:
    return {
        "source_type": source_type,
        "source_path": str(source_path),
        **result.model_dump(mode="json"),
    }


def _inspect_payload(
    *,
    source_type: str,
    source_path: Path,
    batch: IngestionBatch,
) -> dict[str, Any]:
    return {
        "source_type": source_type,
        "source_path": str(source_path),
        "mode": "inspect_only",
        "records_seen": batch.records_seen,
        "raw_listings": len(batch.raw_listings),
        "normalized_listings": len(batch.normalized_listings),
        "rejected_listings": len(batch.rejected_listings),
        "ml_ready_listings": sum(
            1 for listing in batch.normalized_listings if listing.has_coordinates
        ),
    }


def _print_json(payload: dict[str, Any]) -> None:
    with suppress(AttributeError):
        sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Persist RealtyScope real-source ingestion data into the database."
    )
    parser.add_argument(
        "--source-type",
        choices=sorted(SUPPORTED_SOURCE_TYPES),
        required=True,
        help="Real source snapshot type to import.",
    )
    parser.add_argument(
        "--source-path", required=True, help="Path to the real source snapshot file."
    )
    parser.add_argument("--database-url", default=None, help="Override database URL for this run.")
    parser.add_argument("--max-records", type=int, default=100, help="Maximum records to parse.")
    parser.add_argument(
        "--inspect-only",
        action="store_true",
        help="Parse the snapshot and print counts without writing to the database.",
    )
    parser.add_argument("--json", action="store_true", help="Print a JSON summary.")
    args = parser.parse_args(argv)

    source_path = Path(args.source_path)
    if args.inspect_only:
        batch = load_real_source_snapshot(
            source_type=args.source_type,
            source_path=source_path,
            max_records=args.max_records,
        )
        payload = _inspect_payload(
            source_type=args.source_type,
            source_path=source_path,
            batch=batch,
        )
        if args.json:
            _print_json(payload)
        else:
            print(
                "Inspected real source snapshot "
                f"source_type={args.source_type} records_seen={batch.records_seen} "
                f"normalized={len(batch.normalized_listings)} "
                f"rejected={len(batch.rejected_listings)}"
            )
        return 0

    result = persist_real_source_snapshot(
        source_type=args.source_type,
        source_path=source_path,
        database_url=args.database_url,
        max_records=args.max_records,
    )
    payload = _result_payload(source_type=args.source_type, source_path=source_path, result=result)

    if args.json:
        _print_json(payload)
    else:
        print(
            "Persisted real source ingestion "
            f"source_type={args.source_type} records_seen={result.records_seen} "
            f"raw_inserted={result.raw_inserted} listings_created={result.listings_created} "
            f"rejected={result.rejected_inserted}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
