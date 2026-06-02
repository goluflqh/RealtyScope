from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from realtyscope.database.base import Base
from realtyscope.database.models import (
    Listing,
    ListingObservation,
    OsmFeature,
    RawListingRecord,
    Source,
)
from realtyscope.ml.features import FEATURE_VERSION, build_feature_rows, main

NON_LEAKY_FEATURE_VERSION = "ml_features_v2_non_leaky"


def test_build_feature_rows_joins_latest_listing_observation_and_osm(tmp_path: Path) -> None:
    database_url = _seed_feature_database(tmp_path, include_osm=True)
    engine = create_engine(database_url)

    with Session(engine) as session:
        rows = build_feature_rows(session)

    assert len(rows) == 1
    row = rows[0]
    assert row.listing_id == 1
    assert row.feature_version == FEATURE_VERSION
    assert row.target_price_rub == 12_500_000
    assert row.features["total_area_m2"] == 50.0
    assert row.features["rooms"] == 2.0
    assert row.features["latest_observation_price_rub"] == 12_400_000.0
    assert row.features["latest_observation_price_per_m2"] == 248_000.0
    assert row.features["observation_count"] == 2.0
    assert row.features["transport_count_500m"] == 1.0
    assert row.features["nearest_transport_m"] == 130.0
    assert row.features["osm_missing"] == 0.0
    assert row.features["floor_missing"] == 0.0
    assert row.features["building_year_missing"] == 0.0


def test_build_feature_rows_sets_missing_flags_without_osm(tmp_path: Path) -> None:
    database_url = _seed_feature_database(tmp_path, include_osm=False)
    engine = create_engine(database_url)

    with Session(engine) as session:
        rows = build_feature_rows(session)

    assert len(rows) == 1
    row = rows[0]
    assert row.features["osm_missing"] == 1.0
    assert row.features["nearest_transport_m_missing"] == 1.0
    assert row.features["transport_count_500m"] == 0.0
    assert row.features["transport_count_1000m"] == 0.0
    assert row.features["schools_count_1000m"] == 0.0


def test_non_leaky_feature_version_excludes_latest_price_fields(tmp_path: Path) -> None:
    database_url = _seed_feature_database(tmp_path, include_osm=True)
    engine = create_engine(database_url)

    with Session(engine) as session:
        rows = build_feature_rows(session, feature_version=NON_LEAKY_FEATURE_VERSION)

    assert len(rows) == 1
    row = rows[0]
    assert row.feature_version == NON_LEAKY_FEATURE_VERSION
    assert row.target_price_rub == 12_500_000
    assert row.features["observation_count"] == 2.0
    assert row.features["osm_missing"] == 0.0
    assert "latest_observation_price_rub" not in row.features
    assert "latest_observation_price_per_m2" not in row.features
    assert not any("price" in feature_name for feature_name in row.features)


def test_feature_rows_are_deterministic_by_listing_id(tmp_path: Path) -> None:
    database_url = _seed_feature_database(tmp_path, include_osm=True)
    engine = create_engine(database_url)

    with Session(engine) as session:
        first = [row.model_dump() for row in build_feature_rows(session)]
        second = [row.model_dump() for row in build_feature_rows(session)]

    assert first == second


def test_ml_feature_cli_exports_summary_json(tmp_path: Path, capsys) -> None:
    database_url = _seed_feature_database(tmp_path, include_osm=True)

    assert main(["--database-url", database_url, "--limit", "10", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["feature_version"] == FEATURE_VERSION
    assert payload["rows_total"] == 1
    assert payload["feature_count"] >= 10
    assert payload["target_price_rub"]["min"] == 12_500_000
    assert payload["osm_rows_present"] == 1


def test_ml_feature_cli_exports_non_leaky_summary_json(tmp_path: Path, capsys) -> None:
    database_url = _seed_feature_database(tmp_path, include_osm=True)

    assert (
        main(
            [
                "--database-url",
                database_url,
                "--limit",
                "10",
                "--feature-version",
                NON_LEAKY_FEATURE_VERSION,
                "--json",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)

    assert payload["feature_version"] == NON_LEAKY_FEATURE_VERSION
    assert payload["rows_total"] == 1
    assert payload["feature_count"] >= 10
    assert payload["osm_rows_present"] == 1


def _seed_feature_database(tmp_path: Path, *, include_osm: bool) -> str:
    database_path = tmp_path / "ml-features.sqlite3"
    database_url = f"sqlite+pysqlite:///{database_path.as_posix()}"
    engine = create_engine(database_url)
    Base.metadata.create_all(engine)

    first_seen = datetime(2026, 6, 1, 8, 0, tzinfo=UTC)
    older_observed = datetime(2026, 6, 1, 9, 0, tzinfo=UTC)
    latest_observed = datetime(2026, 6, 2, 9, 0, tzinfo=UTC)
    with Session(engine) as session:
        source = Source(name="domclick", source_type="listing")
        session.add(source)
        session.flush()
        older_raw = RawListingRecord(
            source_id=source.id,
            source_listing_id="ml-1",
            observed_at=older_observed,
            payload_hash="ml-hash-older",
            raw_payload={"id": "ml-1", "price": 12_000_000},
        )
        latest_raw = RawListingRecord(
            source_id=source.id,
            source_listing_id="ml-1",
            observed_at=latest_observed,
            payload_hash="ml-hash-latest",
            raw_payload={"id": "ml-1", "price": 12_400_000},
        )
        listing = Listing(
            city="Moscow",
            address_text="Moscow ML street, 1",
            latitude=55.75,
            longitude=37.61,
            price_rub=12_500_000,
            total_area_m2=50.0,
            rooms=2,
            floor=7,
            floors_total=20,
            building_year=2018,
            property_type="apartment",
            has_coordinates=True,
            is_ml_ready=True,
            cleaning_status="ml_ready",
            first_seen_at=first_seen,
            last_seen_at=latest_observed,
        )
        session.add_all([older_raw, latest_raw, listing])
        session.flush()
        session.add_all(
            [
                ListingObservation(
                    listing_id=listing.id,
                    source_id=source.id,
                    raw_listing_id=older_raw.id,
                    source_listing_id="ml-1",
                    observed_at=older_observed,
                    price_rub=12_000_000,
                    price_per_m2=240_000.0,
                    total_area_m2=50.0,
                    rooms=2,
                    floor=7,
                    floors_total=20,
                    active=True,
                    status="observed",
                ),
                ListingObservation(
                    listing_id=listing.id,
                    source_id=source.id,
                    raw_listing_id=latest_raw.id,
                    source_listing_id="ml-1",
                    observed_at=latest_observed,
                    price_rub=12_400_000,
                    price_per_m2=248_000.0,
                    total_area_m2=50.0,
                    rooms=2,
                    floor=7,
                    floors_total=20,
                    active=True,
                    status="observed",
                ),
            ]
        )
        if include_osm:
            session.add(
                OsmFeature(
                    listing_id=listing.id,
                    latitude=55.75,
                    longitude=37.61,
                    feature_version="osm_local_v1",
                    transport_count_500m=1,
                    transport_count_1000m=2,
                    nearest_transport_m=130.0,
                    schools_count_1000m=1,
                    parks_count_1000m=1,
                    shops_count_1000m=2,
                    healthcare_count_1000m=1,
                    source_summary={"fixture": True},
                )
            )
        session.commit()
    return database_url
