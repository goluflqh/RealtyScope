import json
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from realtyscope.analysis.eda_summary import build_eda_summary, main
from realtyscope.database.base import Base
from realtyscope.database.persistence import persist_ingestion_batch
from realtyscope.ingestion.contracts import (
    IngestionBatch,
    NormalizedListing,
    RawListing,
    RejectedListing,
)


def _seed_database(database_path: Path) -> str:
    database_url = f"sqlite+pysqlite:///{database_path.as_posix()}"
    engine = create_engine(database_url)
    Base.metadata.create_all(engine)
    observed_at = datetime(2026, 5, 31, 12, 0, tzinfo=UTC)
    batch = IngestionBatch(
        raw_listings=(
            RawListing(
                source_name="domclick",
                source_listing_id="eda-1",
                source_url="https://domclick.ru/card/sale__flat__eda-1/",
                observed_at=observed_at,
                raw_payload={"id": "eda-1", "price": 18_000_000},
            ),
            RawListing(
                source_name="domclick",
                source_listing_id="eda-2",
                source_url="https://domclick.ru/card/sale__flat__eda-2/",
                observed_at=observed_at,
                raw_payload={"id": "eda-2", "price": 9_000_000},
            ),
        ),
        normalized_listings=(
            NormalizedListing(
                source_name="domclick",
                source_listing_id="eda-1",
                source_url="https://domclick.ru/card/sale__flat__eda-1/",
                observed_at=observed_at,
                city="Moscow",
                address_text="Москва, EDA улица, 1",
                latitude=55.751,
                longitude=37.618,
                price_rub=18_000_000,
                total_area_m2=60.0,
                rooms=2,
                property_type="apartment",
            ),
            NormalizedListing(
                source_name="domclick",
                source_listing_id="eda-2",
                source_url="https://domclick.ru/card/sale__flat__eda-2/",
                observed_at=observed_at,
                city="Moscow",
                address_text="Москва, EDA улица, 2",
                price_rub=9_000_000,
                total_area_m2=45.0,
                rooms=1,
                property_type="apartment",
            ),
        ),
        rejected_listings=(
            RejectedListing(
                source_name="domclick",
                row_number=3,
                reason="price_rub is required",
                raw_payload={"id": "bad"},
            ),
        ),
    )
    with Session(engine) as session:
        persist_ingestion_batch(session, batch, source_name="domclick")
        session.commit()
    return database_url


def test_build_eda_summary_reads_persisted_database_metrics(tmp_path: Path) -> None:
    database_url = _seed_database(tmp_path / "eda.sqlite3")

    summary = build_eda_summary(database_url)

    assert summary.sources_total == 1
    assert summary.ingestion_runs_total == 1
    assert summary.raw_listings_total == 2
    assert summary.listings_total == 2
    assert summary.rejected_listings_total == 1
    assert summary.ml_ready_listings == 1
    assert summary.coordinate_coverage == 0.5
    assert summary.rejected_rate == 1 / 3
    assert summary.price_rub_min == 9_000_000
    assert summary.price_rub_max == 18_000_000
    assert summary.price_rub_avg == 13_500_000
    assert summary.total_area_m2_avg == 52.5
    assert summary.price_per_m2_avg == 250_000
    assert summary.rooms_distribution == {"1": 1, "2": 1}
    assert summary.ml_readiness_conclusion.startswith("Chưa đủ cơ sở")


def test_eda_summary_cli_writes_markdown_and_json(tmp_path: Path, capsys) -> None:
    database_url = _seed_database(tmp_path / "eda_cli.sqlite3")
    output_path = tmp_path / "phase3_5_eda_summary.vi.md"

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
    assert payload["ml_ready_listings"] == 1
    report = output_path.read_text(encoding="utf-8")
    assert "# RealtyScope Phase 3.5 EDA Summary" in report
    assert "## Tổng quan dữ liệu" in report
    assert "Số listing đã chuẩn hóa: 2" in report
    assert "Tỷ lệ có tọa độ: 50.00%" in report
    assert "Chưa đủ cơ sở" in report
