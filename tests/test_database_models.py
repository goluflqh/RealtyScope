from datetime import UTC, datetime

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from realtyscope.database.base import Base
from realtyscope.database.models import (
    Listing,
    ListingObservation,
    ListingSourceLink,
    OsmFeature,
    RawListingRecord,
    Source,
)
from realtyscope.database.session import create_session_factory


def test_database_base_metadata_contains_core_tables() -> None:
    expected_tables = {
        "sources",
        "ingestion_runs",
        "raw_listings",
        "listings",
        "listing_source_links",
        "listing_observations",
        "osm_features",
        "rejected_listings",
        "app_logs",
    }

    assert expected_tables.issubset(Base.metadata.tables)


def test_session_factory_creates_sqlalchemy_session() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    factory = create_session_factory(engine)

    with factory() as session:
        assert isinstance(session, Session)


def test_source_name_is_unique() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        session.add_all(
            [
                Source(name="domclick", source_type="listing"),
                Source(name="domclick", source_type="listing"),
            ]
        )

        with pytest.raises(IntegrityError):
            session.commit()


def test_listing_cleaning_flags_are_explicit() -> None:
    listing = Listing(
        city="Moscow",
        price_rub=12_000_000,
        total_area_m2=48.5,
        rooms=2,
        property_type="apartment",
        has_coordinates=False,
        is_ml_ready=False,
        cleaning_status="needs_coordinates",
    )

    assert listing.has_coordinates is False
    assert listing.is_ml_ready is False
    assert listing.cleaning_status == "needs_coordinates"


def test_raw_listing_payload_hash_is_unique_per_source() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        source = Source(name="domclick", source_type="listing")
        session.add(source)
        session.flush()
        session.add_all(
            [
                RawListingRecord(
                    source_id=source.id,
                    source_listing_id="d-1",
                    observed_at=datetime(2026, 5, 31, tzinfo=UTC),
                    payload_hash="same-hash",
                    raw_payload={"id": "d-1"},
                ),
                RawListingRecord(
                    source_id=source.id,
                    source_listing_id="d-1",
                    observed_at=datetime(2026, 5, 31, tzinfo=UTC),
                    payload_hash="same-hash",
                    raw_payload={"id": "d-1"},
                ),
            ]
        )

        with pytest.raises(IntegrityError):
            session.commit()


def test_model_relationships_can_insert_minimal_listing_graph() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        source = Source(name="domclick", source_type="listing")
        session.add(source)
        session.flush()
        raw = RawListingRecord(
            source_id=source.id,
            source_listing_id="d-1",
            observed_at=datetime(2026, 5, 31, tzinfo=UTC),
            payload_hash="hash-1",
            raw_payload={"id": "d-1"},
        )
        listing = Listing(
            city="Moscow",
            price_rub=12_000_000,
            total_area_m2=48.5,
            rooms=2,
            property_type="apartment",
            has_coordinates=False,
            is_ml_ready=False,
            cleaning_status="needs_coordinates",
        )
        session.add_all([raw, listing])
        session.flush()
        listing.links.append(
            ListingSourceLink(
                source_id=source.id,
                raw_listing_id=raw.id,
                source_listing_id="d-1",
                match_strategy="exact_source_listing_id",
                match_confidence=1.0,
            )
        )
        session.commit()

    with Session(engine) as session:
        loaded = session.scalars(select(Listing)).one()
        assert loaded.links[0].source_listing_id == "d-1"


def test_listing_observation_records_snapshot_fields() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)

    observed_at = datetime(2026, 6, 2, 10, 30, tzinfo=UTC)
    with Session(engine) as session:
        source = Source(name="domclick", source_type="listing")
        session.add(source)
        session.flush()
        raw = RawListingRecord(
            source_id=source.id,
            source_listing_id="d-1",
            observed_at=observed_at,
            payload_hash="hash-observation-1",
            raw_payload={"id": "d-1", "price": 12_000_000},
        )
        listing = Listing(
            city="Moscow",
            price_rub=12_000_000,
            total_area_m2=48.5,
            rooms=2,
            floor=7,
            floors_total=22,
            property_type="apartment",
            has_coordinates=False,
            is_ml_ready=False,
            cleaning_status="needs_coordinates",
        )
        session.add_all([raw, listing])
        session.flush()
        session.add(
            ListingObservation(
                listing_id=listing.id,
                source_id=source.id,
                raw_listing_id=raw.id,
                source_listing_id="d-1",
                observed_at=observed_at,
                price_rub=12_000_000,
                price_per_m2=247_422.68,
                total_area_m2=48.5,
                rooms=2,
                floor=7,
                floors_total=22,
                active=True,
                status="observed",
            )
        )
        session.commit()

    with Session(engine) as session:
        observation = session.scalars(select(ListingObservation)).one()
        assert observation.source_listing_id == "d-1"
        assert observation.price_rub == 12_000_000
        assert observation.rooms == 2
        assert observation.floor == 7


def test_listing_can_store_osm_feature_snapshot() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        listing = Listing(
            city="Moscow",
            latitude=55.75,
            longitude=37.61,
            price_rub=12_000_000,
            total_area_m2=48.5,
            rooms=2,
            property_type="apartment",
            has_coordinates=True,
            is_ml_ready=True,
            cleaning_status="clean",
        )
        session.add(listing)
        session.flush()
        listing.osm_features.append(
            OsmFeature(
                latitude=55.75,
                longitude=37.61,
                feature_version="osm_local_v1",
                transport_count_500m=1,
                transport_count_1000m=2,
                nearest_transport_m=128.5,
                schools_count_1000m=1,
                parks_count_1000m=1,
                shops_count_1000m=1,
                healthcare_count_1000m=0,
                source_summary={"fixture": True},
            )
        )
        session.commit()

    with Session(engine) as session:
        loaded = session.scalars(select(Listing)).one()
        assert loaded.osm_features[0].feature_version == "osm_local_v1"
        assert loaded.osm_features[0].transport_count_500m == 1
