from datetime import UTC, datetime

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from realtyscope.database.base import Base
from realtyscope.database.models import (
    IngestionRun,
    Listing,
    ListingObservation,
    ListingSourceLink,
    RawListingRecord,
    RejectedListingRecord,
    Source,
)
from realtyscope.database.persistence import persist_ingestion_batch
from realtyscope.ingestion.contracts import (
    IngestionBatch,
    NormalizedListing,
    RawListing,
    RejectedListing,
)


def _session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def _batch(observed_at: datetime | None = None) -> IngestionBatch:
    observed_at = observed_at or datetime(2026, 5, 31, 10, 0, tzinfo=UTC)
    return IngestionBatch(
        raw_listings=(
            RawListing(
                source_name="domclick",
                source_listing_id="d-1",
                source_url="https://example.test/1",
                observed_at=observed_at,
                raw_payload={"id": "d-1", "price": 12_000_000},
            ),
        ),
        normalized_listings=(
            NormalizedListing(
                source_name="domclick",
                source_listing_id="d-1",
                source_url="https://example.test/1",
                observed_at=observed_at,
                city="Moscow",
                address_text="Moscow, Test street, 1",
                latitude=55.75,
                longitude=37.62,
                price_rub=12_000_000,
                total_area_m2=48.5,
                rooms=2,
                property_type="apartment",
            ),
        ),
        rejected_listings=(
            RejectedListing(
                source_name="domclick",
                row_number=2,
                reason="price_rub is required",
                raw_payload={"id": "bad"},
            ),
        ),
    )


def test_persist_ingestion_batch_creates_run_raw_listing_link_and_rejection() -> None:
    with _session() as session:
        result = persist_ingestion_batch(session, _batch(), source_name="domclick")
        session.commit()

        assert result.records_seen == 2
        assert result.raw_inserted == 1
        assert result.listings_created == 1
        assert result.rejected_inserted == 1
        assert session.scalar(select(Source).where(Source.name == "domclick")) is not None
        assert session.scalar(select(IngestionRun)).status == "success"
        assert session.scalar(select(RawListingRecord)).payload_hash
        listing = session.scalar(select(Listing))
        assert listing is not None
        assert listing.has_coordinates is True
        assert listing.is_ml_ready is True
        assert listing.cleaning_status == "ml_ready"
        assert session.scalar(select(RejectedListingRecord)).reason == "price_rub is required"


def test_persist_ingestion_batch_is_idempotent_for_same_raw_payload() -> None:
    with _session() as session:
        first = persist_ingestion_batch(session, _batch(), source_name="domclick")
        second = persist_ingestion_batch(session, _batch(), source_name="domclick")
        session.commit()

        assert first.raw_inserted == 1
        assert second.raw_inserted == 0
        assert second.raw_reused == 1
        assert second.observations_inserted == 0
        assert len(session.scalars(select(RawListingRecord)).all()) == 1
        assert len(session.scalars(select(Listing)).all()) == 1
        assert len(session.scalars(select(ListingObservation)).all()) == 1


def test_persist_ingestion_batch_creates_later_observation_for_reused_raw_payload() -> None:
    first_observed_at = datetime(2026, 6, 1, 0, 0, tzinfo=UTC)
    second_observed_at = datetime(2026, 6, 2, 0, 0, tzinfo=UTC)

    with _session() as session:
        persist_ingestion_batch(
            session,
            _batch(observed_at=first_observed_at),
            source_name="domclick",
        )
        second = persist_ingestion_batch(
            session,
            _batch(observed_at=second_observed_at),
            source_name="domclick",
        )
        session.commit()

        raw_records = session.scalars(select(RawListingRecord)).all()
        observations = session.scalars(
            select(ListingObservation).order_by(ListingObservation.observed_at)
        ).all()

        assert second.raw_inserted == 0
        assert second.raw_reused == 1
        assert second.observations_inserted == 1
        assert len(raw_records) == 1
        assert len(observations) == 2
        assert [_as_utc(observation.observed_at) for observation in observations] == [
            first_observed_at,
            second_observed_at,
        ]
        assert {observation.raw_listing_id for observation in observations} == {raw_records[0].id}


def test_persist_ingestion_batch_updates_listing_and_latest_raw_link() -> None:
    observed_at = datetime(2026, 5, 31, 11, 0, tzinfo=UTC)
    changed_batch = IngestionBatch(
        raw_listings=(
            RawListing(
                source_name="domclick",
                source_listing_id="d-1",
                source_url="https://example.test/1",
                observed_at=observed_at,
                raw_payload={"id": "d-1", "price": 13_000_000},
            ),
        ),
        normalized_listings=(
            NormalizedListing(
                source_name="domclick",
                source_listing_id="d-1",
                source_url="https://example.test/1",
                observed_at=observed_at,
                city="Moscow",
                address_text="Moscow, Test street, 1",
                latitude=55.75,
                longitude=37.62,
                price_rub=13_000_000,
                total_area_m2=48.5,
                rooms=2,
                property_type="apartment",
            ),
        ),
    )

    with _session() as session:
        persist_ingestion_batch(session, _batch(), source_name="domclick")
        result = persist_ingestion_batch(session, changed_batch, source_name="domclick")
        session.commit()

        raw_records = session.scalars(select(RawListingRecord).order_by(RawListingRecord.id)).all()
        observations = session.scalars(
            select(ListingObservation).order_by(ListingObservation.observed_at)
        ).all()
        listing = session.scalar(select(Listing))
        link = session.scalar(select(ListingSourceLink))

        assert result.raw_inserted == 1
        assert result.listings_updated == 1
        assert result.observations_inserted == 1
        assert len(raw_records) == 2
        assert [observation.price_rub for observation in observations] == [12_000_000, 13_000_000]
        assert observations[-1].raw_listing_id == raw_records[-1].id
        assert observations[-1].rooms == 2
        assert observations[-1].floor is None
        assert listing is not None
        assert listing.price_rub == 13_000_000
        assert link is not None
        assert link.raw_listing_id == raw_records[-1].id


def test_persist_ingestion_batch_marks_missing_coordinates_not_ml_ready() -> None:
    observed_at = datetime(2026, 5, 31, 10, 0, tzinfo=UTC)
    batch = IngestionBatch(
        raw_listings=(
            RawListing(
                source_name="teammate_file",
                source_listing_id="t-1",
                observed_at=observed_at,
                raw_payload={"id": "t-1"},
            ),
        ),
        normalized_listings=(
            NormalizedListing(
                source_name="teammate_file",
                source_listing_id="t-1",
                observed_at=observed_at,
                city="Moscow",
                price_rub=9_000_000,
                total_area_m2=40,
                rooms=1,
                property_type="apartment",
            ),
        ),
    )

    with _session() as session:
        persist_ingestion_batch(session, batch, source_name="teammate_file")
        session.commit()
        listing = session.scalar(select(Listing))

    assert listing is not None
    assert listing.has_coordinates is False
    assert listing.is_ml_ready is False
    assert listing.cleaning_status == "needs_coordinates"


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value
