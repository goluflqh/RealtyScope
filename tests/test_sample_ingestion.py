import json
from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from realtyscope.database.base import Base
from realtyscope.database.models import Listing, RejectedListingRecord, Source
from realtyscope.database.sample_ingestion import (
    SAMPLE_SOURCE_NAME,
    build_sample_ingestion_batch,
    main,
    persist_sample_ingestion,
)


def test_build_sample_ingestion_batch_has_mixed_quality_rows() -> None:
    batch = build_sample_ingestion_batch()

    assert batch.records_seen == 4
    assert len(batch.raw_listings) == 3
    assert len(batch.normalized_listings) == 3
    assert len(batch.rejected_listings) == 1
    assert sum(item.has_coordinates for item in batch.normalized_listings) == 2
    assert batch.rejected_listings[0].reason == "price_rub is required"


def test_persist_sample_ingestion_writes_expected_rows() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        result = persist_sample_ingestion(session)
        session.commit()

        assert result.records_seen == 4
        assert result.raw_inserted == 3
        assert result.listings_created == 3
        assert result.rejected_inserted == 1
        assert session.scalar(select(Source).where(Source.name == SAMPLE_SOURCE_NAME)) is not None
        listings = session.scalars(select(Listing)).all()
        assert len(listings) == 3
        assert sum(listing.is_ml_ready for listing in listings) == 2
        cleaning_statuses = {listing.cleaning_status for listing in listings}
        assert cleaning_statuses == {"ml_ready", "needs_coordinates"}
        assert session.scalar(select(RejectedListingRecord)).reason == "price_rub is required"


def test_sample_ingestion_module_cli_persists_to_database_url(tmp_path: Path, capsys) -> None:
    database_path = tmp_path / "sample.sqlite3"
    database_url = f"sqlite+pysqlite:///{database_path.as_posix()}"
    engine = create_engine(database_url)
    Base.metadata.create_all(engine)

    exit_code = main(["--database-url", database_url, "--json"])

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["source_name"] == SAMPLE_SOURCE_NAME
    assert payload["records_seen"] == 4
    with Session(engine) as session:
        assert len(session.scalars(select(Listing)).all()) == 3
