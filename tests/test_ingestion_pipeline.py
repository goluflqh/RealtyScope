import json
from datetime import UTC, datetime
from pathlib import Path

from realtyscope.ingestion.contracts import IngestionBatch, NormalizedListing, RawListing
from realtyscope.ingestion.pipeline import write_ingestion_batch


def test_write_ingestion_batch_creates_raw_and_normalized_jsonl(tmp_path: Path) -> None:
    batch = IngestionBatch(
        raw_listings=(
            RawListing(
                source_name="domclick",
                source_listing_id="d-1",
                source_url="https://example.test/1",
                observed_at=datetime(2026, 5, 31, tzinfo=UTC),
                raw_payload={"id": "d-1", "price": 12_000_000},
            ),
        ),
        normalized_listings=(
            NormalizedListing(
                source_name="domclick",
                source_listing_id="d-1",
                source_url="https://example.test/1",
                observed_at=datetime(2026, 5, 31, tzinfo=UTC),
                city="Moscow",
                price_rub=12_000_000,
                total_area_m2=48.5,
                rooms=2,
                property_type="apartment",
            ),
        ),
    )

    manifest = write_ingestion_batch(batch, output_dir=tmp_path, run_name="test-run")

    raw_line = json.loads(manifest.raw_path.read_text(encoding="utf-8").splitlines()[0])
    normalized_line = json.loads(
        manifest.normalized_path.read_text(encoding="utf-8").splitlines()[0]
    )

    assert manifest.records_seen == 1
    assert manifest.raw_count == 1
    assert manifest.normalized_count == 1
    assert raw_line["payload_hash"]
    assert normalized_line["price_per_m2"]
