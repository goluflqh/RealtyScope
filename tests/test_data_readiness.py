import json
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from realtyscope.analysis.data_readiness import main, summarize_data_readiness
from realtyscope.database.base import Base
from realtyscope.database.persistence import persist_ingestion_batch
from realtyscope.ingestion.contracts import IngestionBatch, NormalizedListing, RawListing


def _seed_readiness_database(database_path: Path) -> str:
    database_url = f"sqlite+pysqlite:///{database_path.as_posix()}"
    engine = create_engine(database_url)
    Base.metadata.create_all(engine)
    first_observed_at = datetime(2026, 6, 1, 10, 0, tzinfo=UTC)
    second_observed_at = datetime(2026, 6, 2, 10, 0, tzinfo=UTC)

    first_batch = IngestionBatch(
        raw_listings=(
            RawListing(
                source_name="domclick",
                source_listing_id="ready-1",
                source_url="https://domclick.ru/card/sale__flat__ready-1/",
                observed_at=first_observed_at,
                raw_payload={"id": "ready-1", "price": 12_000_000},
            ),
            RawListing(
                source_name="domclick",
                source_listing_id="ready-2",
                source_url="https://domclick.ru/card/sale__flat__ready-2/",
                observed_at=first_observed_at,
                raw_payload={"id": "ready-2", "price": 9_000_000},
            ),
        ),
        normalized_listings=(
            NormalizedListing(
                source_name="domclick",
                source_listing_id="ready-1",
                source_url="https://domclick.ru/card/sale__flat__ready-1/",
                observed_at=first_observed_at,
                city="Moscow",
                address_text="Moscow, Readiness street, 1",
                latitude=55.75,
                longitude=37.62,
                price_rub=12_000_000,
                total_area_m2=48.0,
                rooms=2,
                property_type="apartment",
            ),
            NormalizedListing(
                source_name="domclick",
                source_listing_id="ready-2",
                source_url="https://domclick.ru/card/sale__flat__ready-2/",
                observed_at=first_observed_at,
                city="Moscow",
                address_text="Moscow, Readiness street, 2",
                price_rub=9_000_000,
                total_area_m2=40.0,
                rooms=0,
                property_type="apartment",
            ),
        ),
    )
    changed_batch = IngestionBatch(
        raw_listings=(
            RawListing(
                source_name="domclick",
                source_listing_id="ready-1",
                source_url="https://domclick.ru/card/sale__flat__ready-1/",
                observed_at=second_observed_at,
                raw_payload={"id": "ready-1", "price": 13_000_000},
            ),
        ),
        normalized_listings=(
            NormalizedListing(
                source_name="domclick",
                source_listing_id="ready-1",
                source_url="https://domclick.ru/card/sale__flat__ready-1/",
                observed_at=second_observed_at,
                city="Moscow",
                address_text="Moscow, Readiness street, 1",
                latitude=55.75,
                longitude=37.62,
                price_rub=13_000_000,
                total_area_m2=48.0,
                rooms=2,
                property_type="apartment",
            ),
        ),
    )
    with Session(engine) as session:
        persist_ingestion_batch(session, first_batch, source_name="domclick")
        persist_ingestion_batch(session, changed_batch, source_name="domclick")
        session.commit()
    return database_url


def test_data_readiness_counts_coordinates_and_observations(tmp_path: Path) -> None:
    database_url = _seed_readiness_database(tmp_path / "readiness.sqlite3")
    engine = create_engine(database_url)

    with Session(engine) as session:
        summary = summarize_data_readiness(session)

    assert summary.listings_total == 2
    assert summary.with_coordinates == 1
    assert summary.without_coordinates == 1
    assert summary.observations_total == 3
    assert summary.listings_with_multiple_observations == 1
    assert summary.price_changes_detected == 1
    assert summary.ml_ready_listings == 1
    assert summary.missing_core_fields == {
        "price": 0,
        "area": 0,
        "rooms": 0,
        "coordinates": 1,
    }


def test_data_readiness_cli_writes_markdown_and_json(tmp_path: Path, capsys) -> None:
    database_url = _seed_readiness_database(tmp_path / "readiness_cli.sqlite3")
    output_path = tmp_path / "phase4-data-readiness.vi.md"

    exit_code = main(
        [
            "--database-url",
            database_url,
            "--output",
            str(output_path),
            "--json",
        ]
    )

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["listings_total"] == 2
    assert payload["price_changes_detected"] == 1
    report = output_path.read_text(encoding="utf-8")
    assert "# RealtyScope Phase 4 Data Readiness" in report
    assert "Số listing có tọa độ: 1" in report
    assert "Listing có price changes: 1" in report
