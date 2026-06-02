from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from realtyscope.database.base import Base
from realtyscope.database.models import Listing, OsmFeature
from realtyscope.enrichment.osm import compute_osm_features, main


def test_compute_osm_features_counts_infrastructure_within_radius() -> None:
    listing = {"latitude": 55.75, "longitude": 37.61}
    elements = [
        {"type": "node", "lat": 55.7505, "lon": 37.6105, "tags": {"amenity": "school"}},
        {
            "type": "node",
            "lat": 55.7510,
            "lon": 37.6110,
            "tags": {"public_transport": "station"},
        },
        {"type": "node", "lat": 55.7520, "lon": 37.6120, "tags": {"leisure": "park"}},
        {"type": "node", "lat": 55.7530, "lon": 37.6130, "tags": {"shop": "supermarket"}},
        {"type": "node", "lat": 55.7540, "lon": 37.6140, "tags": {"amenity": "clinic"}},
        {"type": "node", "lat": 55.9000, "lon": 37.9000, "tags": {"amenity": "school"}},
    ]

    features = compute_osm_features(listing, elements, radii_m=(500, 1000))

    assert features.transport_count_500m == 1
    assert features.transport_count_1000m == 1
    assert features.nearest_transport_m is not None
    assert 120 <= features.nearest_transport_m <= 140
    assert features.schools_count_1000m == 1
    assert features.parks_count_1000m == 1
    assert features.shops_count_1000m == 1
    assert features.healthcare_count_1000m == 1
    assert features.osm_feature_version == "osm_local_v1"
    assert features.source_summary["elements_seen"] == 6
    assert features.source_summary["elements_used"] == 5


def test_compute_osm_features_rejects_listing_without_coordinates() -> None:
    with pytest.raises(ValueError, match="latitude and longitude"):
        compute_osm_features({"latitude": None, "longitude": 37.61}, [])


def test_osm_feature_model_is_unique_per_listing_and_version() -> None:
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
        session.add_all(
            [
                OsmFeature(
                    listing_id=listing.id,
                    latitude=55.75,
                    longitude=37.61,
                    feature_version="osm_local_v1",
                    transport_count_500m=1,
                    transport_count_1000m=1,
                    nearest_transport_m=128.5,
                    schools_count_1000m=1,
                    parks_count_1000m=1,
                    shops_count_1000m=1,
                    healthcare_count_1000m=1,
                    source_summary={"fixture": True},
                ),
                OsmFeature(
                    listing_id=listing.id,
                    latitude=55.75,
                    longitude=37.61,
                    feature_version="osm_local_v1",
                    transport_count_500m=0,
                    transport_count_1000m=0,
                    nearest_transport_m=None,
                    schools_count_1000m=0,
                    parks_count_1000m=0,
                    shops_count_1000m=0,
                    healthcare_count_1000m=0,
                    source_summary={"fixture": True},
                ),
            ]
        )

        with pytest.raises(IntegrityError):
            session.commit()


def test_osm_enrichment_dry_run_cli_reports_limited_coordinate_ready_rows(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    database_url = _seed_coordinate_ready_database(tmp_path)

    assert main(["--database-url", database_url, "--limit", "1", "--dry-run", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["dry_run"] is True
    assert payload["live_osm_called"] is False
    assert payload["rows_selected"] == 1
    assert payload["rows_available"] == 2
    assert payload["feature_version"] == "osm_local_v1"
    assert "OpenStreetMap" in payload["attribution"]


def test_osm_enrichment_module_runs_without_package_import_warning(tmp_path: Path) -> None:
    database_url = _seed_coordinate_ready_database(tmp_path)

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "realtyscope.enrichment.osm",
            "--database-url",
            database_url,
            "--limit",
            "1",
            "--dry-run",
            "--json",
        ],
        capture_output=True,
        check=False,
        text=True,
    )

    assert result.returncode == 0
    assert "RuntimeWarning" not in result.stderr
    payload = json.loads(result.stdout)
    assert payload["rows_selected"] == 1


def _seed_coordinate_ready_database(tmp_path: Path) -> str:
    database_path = tmp_path / "osm-dry-run.sqlite3"
    database_url = f"sqlite+pysqlite:///{database_path.as_posix()}"
    engine = create_engine(database_url)
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        session.add_all(
            [
                Listing(
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
                ),
                Listing(
                    city="Moscow",
                    latitude=55.76,
                    longitude=37.62,
                    price_rub=15_000_000,
                    total_area_m2=55.0,
                    rooms=2,
                    property_type="apartment",
                    has_coordinates=True,
                    is_ml_ready=True,
                    cleaning_status="clean",
                ),
            ]
        )
        session.commit()
    return database_url
