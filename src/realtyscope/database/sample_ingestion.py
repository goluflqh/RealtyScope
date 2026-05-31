from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from realtyscope.database.persistence import PersistedIngestionResult, persist_ingestion_batch
from realtyscope.database.session import (
    create_database_engine,
    create_session_factory,
    session_scope,
)
from realtyscope.ingestion.contracts import (
    IngestionBatch,
    NormalizedListing,
    RawListing,
    RejectedListing,
)

SAMPLE_SOURCE_NAME = "sample_phase3_fixture"


def build_sample_ingestion_batch() -> IngestionBatch:
    observed_at = datetime(2026, 5, 31, 12, 0, tzinfo=UTC)
    raw_listings = (
        RawListing(
            source_name=SAMPLE_SOURCE_NAME,
            source_listing_id="sample-1",
            source_url="https://example.test/sample/1",
            observed_at=observed_at,
            raw_payload={
                "id": "sample-1",
                "address": "Moscow, Tverskaya street, 1",
                "price": 14_200_000,
                "area": 52.4,
                "rooms": 2,
                "lat": 55.7601,
                "lng": 37.6187,
            },
        ),
        RawListing(
            source_name=SAMPLE_SOURCE_NAME,
            source_listing_id="sample-2",
            source_url="https://example.test/sample/2",
            observed_at=observed_at,
            raw_payload={
                "id": "sample-2",
                "address": "Moscow, Leninsky prospect, 30",
                "price": 9_800_000,
                "area": 38.0,
                "rooms": 1,
                "lat": 55.7068,
                "lng": 37.5846,
            },
        ),
        RawListing(
            source_name=SAMPLE_SOURCE_NAME,
            source_listing_id="sample-3",
            source_url="https://example.test/sample/3",
            observed_at=observed_at,
            raw_payload={
                "id": "sample-3",
                "address": "Moscow, Draft address without coordinates",
                "price": 18_500_000,
                "area": 70.0,
                "rooms": 3,
            },
        ),
    )
    normalized_listings = (
        NormalizedListing(
            source_name=SAMPLE_SOURCE_NAME,
            source_listing_id="sample-1",
            source_url="https://example.test/sample/1",
            observed_at=observed_at,
            city="Moscow",
            address_text="Moscow, Tverskaya street, 1",
            latitude=55.7601,
            longitude=37.6187,
            price_rub=14_200_000,
            total_area_m2=52.4,
            rooms=2,
            floor=5,
            floors_total=12,
            building_year=2008,
            property_type="apartment",
            description="Sample listing with coordinates for Phase 3 persistence checks.",
        ),
        NormalizedListing(
            source_name=SAMPLE_SOURCE_NAME,
            source_listing_id="sample-2",
            source_url="https://example.test/sample/2",
            observed_at=observed_at,
            city="Moscow",
            address_text="Moscow, Leninsky prospect, 30",
            latitude=55.7068,
            longitude=37.5846,
            price_rub=9_800_000,
            total_area_m2=38.0,
            rooms=1,
            floor=8,
            floors_total=17,
            building_year=2014,
            property_type="apartment",
            description="Sample one-room listing with coordinates.",
        ),
        NormalizedListing(
            source_name=SAMPLE_SOURCE_NAME,
            source_listing_id="sample-3",
            source_url="https://example.test/sample/3",
            observed_at=observed_at,
            city="Moscow",
            address_text="Moscow, Draft address without coordinates",
            price_rub=18_500_000,
            total_area_m2=70.0,
            rooms=3,
            floor=2,
            floors_total=9,
            building_year=1998,
            property_type="apartment",
            description="Sample listing intentionally missing coordinates.",
        ),
    )
    rejected_listings = (
        RejectedListing(
            source_name=SAMPLE_SOURCE_NAME,
            row_number=4,
            reason="price_rub is required",
            raw_payload={"id": "sample-bad", "area": 41.0, "rooms": 1},
        ),
    )
    return IngestionBatch(
        raw_listings=raw_listings,
        normalized_listings=normalized_listings,
        rejected_listings=rejected_listings,
    )


def persist_sample_ingestion(
    session: Session,
    *,
    source_name: str = SAMPLE_SOURCE_NAME,
) -> PersistedIngestionResult:
    return persist_ingestion_batch(
        session,
        build_sample_ingestion_batch(),
        source_name=source_name,
        source_type="sample_fixture",
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Persist RealtyScope Phase 3 sample ingestion data."
    )
    parser.add_argument("--database-url", default=None, help="Override database URL for this run.")
    parser.add_argument("--source-name", default=SAMPLE_SOURCE_NAME, help="Source name to persist.")
    parser.add_argument("--json", action="store_true", help="Print a JSON summary.")
    args = parser.parse_args(argv)

    engine = create_database_engine(args.database_url)
    session_factory = create_session_factory(engine)
    with session_scope(session_factory) as session:
        result = persist_sample_ingestion(session, source_name=args.source_name)

    payload = {"source_name": args.source_name, **result.model_dump(mode="json")}
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    else:
        print(
            "Persisted sample ingestion "
            f"source={args.source_name} records_seen={result.records_seen} "
            f"listings_created={result.listings_created} rejected={result.rejected_inserted}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
