from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
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
        if "json" not in script_type and script_id != "__NEXT_DATA__":
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
        try:
            payload = json.loads(script_payload)
        except json.JSONDecodeError:
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
        batch = _load_domclick_snapshot_file(
            snapshot_file,
            observed_at=observed_at,
            max_records=remaining_records,
        )
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


def persist_real_source_snapshot(
    *,
    source_type: str,
    source_path: Path,
    database_url: str | None = None,
    max_records: int = 100,
) -> PersistedIngestionResult:
    if source_type not in SUPPORTED_SOURCE_TYPES:
        supported = ", ".join(sorted(SUPPORTED_SOURCE_TYPES))
        raise ValueError(f"Unsupported source_type={source_type!r}; supported: {supported}")

    if source_type == "domclick_html":
        batch = load_domclick_html_snapshot(source_path, max_records=max_records)
    elif source_type == "domclick_json":
        batch = load_domclick_json_snapshot(source_path, max_records=max_records)
    elif source_type == "domclick_snapshot_dir":
        batch = load_domclick_snapshot_directory(source_path, max_records=max_records)
    else:  # pragma: no cover - guarded by source type validation above.
        raise AssertionError(f"Unhandled source_type={source_type!r}")

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
    parser.add_argument("--json", action="store_true", help="Print a JSON summary.")
    args = parser.parse_args(argv)

    source_path = Path(args.source_path)
    result = persist_real_source_snapshot(
        source_type=args.source_type,
        source_path=source_path,
        database_url=args.database_url,
        max_records=args.max_records,
    )
    payload = _result_payload(source_type=args.source_type, source_path=source_path, result=result)

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
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
