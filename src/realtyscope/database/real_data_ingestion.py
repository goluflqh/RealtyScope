from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from datetime import UTC, datetime
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
SUPPORTED_SOURCE_TYPES = {"domclick_json"}


def load_domclick_json_snapshot(
    path: Path,
    *,
    observed_at: datetime | None = None,
    max_records: int = 100,
) -> IngestionBatch:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict | list):
        raise ValueError("Domclick JSON snapshot must contain a JSON object or array")
    return parse_domclick_payload(
        payload,
        source_url=path.resolve().as_uri(),
        observed_at=observed_at or datetime.now(UTC),
        config=DomclickCollectorConfig(max_records=max_records),
    )


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

    if source_type == "domclick_json":
        batch = load_domclick_json_snapshot(source_path, max_records=max_records)
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
