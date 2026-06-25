from datetime import UTC, datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from realtyscope.analysis.lifecycle_verification import (
    select_terminal_lifecycle_candidates,
)
from realtyscope.database.base import Base
from realtyscope.database.models import (
    Listing,
    ListingObservation,
    RawListingRecord,
    Source,
)


def test_select_terminal_lifecycle_candidates_requires_gap_history_and_source_url() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        source = Source(name="domclick", source_type="marketplace")
        session.add(source)
        session.flush()
        listing = _listing()
        session.add(listing)
        session.flush()
        raw = _raw(source.id, "gap-target", "https://example.test/gap-target")
        raw_without_url = _raw(source.id, "gap-without-url", None)
        session.add_all([raw, raw_without_url])
        session.flush()

        _add_observation(session, listing.id, source.id, raw.id, "gap-target", 1)
        _add_observation(session, listing.id, source.id, raw.id, "gap-target", 3)
        _add_observation(session, listing.id, source.id, raw.id, "still-observed", 10)
        _add_observation(session, listing.id, source.id, raw.id, "single-observation", 1)
        _add_observation(session, listing.id, source.id, raw_without_url.id, "gap-without-url", 1)
        _add_observation(session, listing.id, source.id, raw_without_url.id, "gap-without-url", 3)
        session.commit()

        candidates = select_terminal_lifecycle_candidates(
            session,
            min_gap_days=3,
            limit=10,
        )

    assert [candidate.source_listing_id for candidate in candidates] == ["gap-target"]
    assert candidates[0].source_name == "domclick"
    assert candidates[0].source_url == "https://example.test/gap-target"
    assert candidates[0].first_observed_date == "2026-06-01"
    assert candidates[0].last_observed_date == "2026-06-03"
    assert candidates[0].latest_source_observed_date == "2026-06-10"
    assert candidates[0].gap_days == 7
    assert candidates[0].observed_exposure_days == 2
    assert candidates[0].verification_status == "needs_source_verification"


def _listing() -> Listing:
    return Listing(
        city="Moscow",
        address_text="Moscow, Test street, 1",
        latitude=55.75,
        longitude=37.62,
        price_rub=12_000_000,
        total_area_m2=48.5,
        rooms=2,
        property_type="apartment",
        has_coordinates=True,
        is_ml_ready=True,
        cleaning_status="ml_ready",
    )


def _raw(source_id: int, source_listing_id: str, source_url: str | None) -> RawListingRecord:
    return RawListingRecord(
        source_id=source_id,
        source_listing_id=source_listing_id,
        source_url=source_url,
        observed_at=datetime(2026, 6, 1, tzinfo=UTC),
        payload_hash=f"hash-{source_listing_id}",
        raw_payload={"id": source_listing_id},
    )


def _add_observation(
    session: Session,
    listing_id: int,
    source_id: int,
    raw_listing_id: int,
    source_listing_id: str,
    day: int,
) -> None:
    session.add(
        ListingObservation(
            listing_id=listing_id,
            source_id=source_id,
            raw_listing_id=raw_listing_id,
            source_listing_id=source_listing_id,
            observed_at=datetime(2026, 6, day, 12, 0, tzinfo=UTC),
            price_rub=12_000_000,
            price_per_m2=247_422,
            total_area_m2=48.5,
            rooms=2,
            floor=7,
            floors_total=18,
            active=True,
            status="observed",
        )
    )
