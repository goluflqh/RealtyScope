from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from realtyscope.ingestion.contracts import IngestionBatch


class IngestionManifest(BaseModel):
    model_config = ConfigDict(frozen=True)

    run_name: str
    output_dir: Path
    raw_path: Path
    normalized_path: Path
    rejected_path: Path
    records_seen: int
    raw_count: int
    normalized_count: int
    rejected_count: int


def write_ingestion_batch(
    batch: IngestionBatch,
    *,
    output_dir: Path,
    run_name: str,
) -> IngestionManifest:
    output_dir.mkdir(parents=True, exist_ok=True)
    raw_path = output_dir / f"{run_name}.raw.jsonl"
    normalized_path = output_dir / f"{run_name}.normalized.jsonl"
    rejected_path = output_dir / f"{run_name}.rejected.jsonl"

    _write_jsonl(raw_path, [item.model_dump(mode="json") for item in batch.raw_listings])
    _write_jsonl(
        normalized_path,
        [item.model_dump(mode="json") for item in batch.normalized_listings],
    )
    _write_jsonl(
        rejected_path,
        [item.model_dump(mode="json") for item in batch.rejected_listings],
    )

    return IngestionManifest(
        run_name=run_name,
        output_dir=output_dir,
        raw_path=raw_path,
        normalized_path=normalized_path,
        rejected_path=rejected_path,
        records_seen=batch.records_seen,
        raw_count=len(batch.raw_listings),
        normalized_count=len(batch.normalized_listings),
        rejected_count=len(batch.rejected_listings),
    )


def _write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8") as output_file:
        for row in rows:
            output_file.write(json.dumps(row, ensure_ascii=False, sort_keys=True))
            output_file.write("\n")
