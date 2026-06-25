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
from realtyscope.enrichment.osm import (
    compute_osm_features,
    main,
    persist_osm_features,
    persist_osm_features_for_matching_coordinates,
    persist_osm_features_from_geojson_file,
)


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


def test_persist_osm_features_writes_and_updates_coordinate_ready_rows(tmp_path: Path) -> None:
    database_url = _seed_coordinate_ready_database(tmp_path)
    engine = create_engine(database_url)

    with Session(engine) as session:
        first = persist_osm_features(
            session,
            elements_by_listing_id={
                1: [
                    {
                        "type": "node",
                        "lat": 55.7510,
                        "lon": 37.6110,
                        "tags": {"public_transport": "station"},
                    }
                ],
                2: [],
            },
            limit=2,
        )
        session.commit()

    assert first.rows_available == 2
    assert first.rows_selected == 2
    assert first.rows_inserted == 2
    assert first.rows_updated == 0
    assert first.live_osm_called is False
    assert "OpenStreetMap" in first.attribution

    with Session(engine) as session:
        rows = session.query(OsmFeature).order_by(OsmFeature.listing_id).all()
        assert len(rows) == 2
        assert rows[0].transport_count_500m == 1
        assert rows[0].source_summary["elements_seen"] == 1
        assert rows[1].source_summary["elements_seen"] == 0

        second = persist_osm_features(
            session,
            elements_by_listing_id={1: [], 2: []},
            limit=2,
        )
        session.commit()

    assert second.rows_inserted == 0
    assert second.rows_updated == 2

    with Session(engine) as session:
        updated = session.query(OsmFeature).filter_by(listing_id=1).one()
        assert updated.transport_count_500m == 0


def test_persist_osm_features_records_fetch_errors_without_aborting_successes(
    tmp_path: Path,
) -> None:
    database_url = _seed_coordinate_ready_database(tmp_path)
    engine = create_engine(database_url)

    def fetch_elements(listing: Listing) -> list[dict[str, object]]:
        if listing.id == 2:
            raise TimeoutError("Overpass timed out")
        return [
            {
                "type": "node",
                "lat": 55.7510,
                "lon": 37.6110,
                "tags": {"public_transport": "station"},
            }
        ]

    with Session(engine) as session:
        result = persist_osm_features(
            session,
            fetch_elements=fetch_elements,
            limit=2,
        )
        session.commit()

    assert result.rows_inserted == 1
    assert result.rows_failed == 1
    assert result.errors == ({"listing_id": 2, "error": "TimeoutError: Overpass timed out"},)

    with Session(engine) as session:
        assert session.query(OsmFeature).count() == 1


def test_live_osm_persistence_fetches_only_missing_distinct_coordinates(
    tmp_path: Path,
) -> None:
    database_url = _seed_coordinate_ready_database(tmp_path)
    engine = create_engine(database_url)

    with Session(engine) as session:
        listing_with_feature = session.get(Listing, 1)
        assert listing_with_feature is not None
        listing_to_duplicate = session.get(Listing, 2)
        assert listing_to_duplicate is not None
        session.add(
            OsmFeature(
                listing_id=listing_with_feature.id,
                latitude=listing_with_feature.latitude,
                longitude=listing_with_feature.longitude,
                feature_version="osm_local_v1",
                transport_count_500m=1,
                transport_count_1000m=2,
                nearest_transport_m=120.0,
                schools_count_1000m=1,
                parks_count_1000m=1,
                shops_count_1000m=1,
                healthcare_count_1000m=1,
                source_summary={
                    "attribution": "OpenStreetMap contributors",
                    "live_osm_called": True,
                },
            )
        )
        session.add(
            Listing(
                city="Moscow",
                latitude=listing_to_duplicate.latitude,
                longitude=listing_to_duplicate.longitude,
                price_rub=16_000_000,
                total_area_m2=57.0,
                rooms=2,
                property_type="apartment",
                has_coordinates=True,
                is_ml_ready=True,
                cleaning_status="clean",
            )
        )
        session.commit()

    called_listing_ids: list[int] = []

    def fetch_elements(listing: Listing) -> list[dict[str, object]]:
        called_listing_ids.append(int(listing.id))
        return [
            {
                "type": "node",
                "lat": float(listing.latitude or 0) + 0.001,
                "lon": float(listing.longitude or 0) + 0.001,
                "tags": {"public_transport": "station"},
            }
        ]

    with Session(engine) as session:
        result = persist_osm_features(
            session,
            fetch_elements=fetch_elements,
            limit=10,
        )
        session.commit()

    assert called_listing_ids == [2]
    assert result.rows_available == 1
    assert result.rows_selected == 1
    assert result.rows_inserted == 1
    assert result.rows_updated == 0
    assert result.selected_listing_ids == (2,)

    with Session(engine) as session:
        assert session.query(OsmFeature).count() == 2
        assert session.query(OsmFeature).filter_by(listing_id=3).count() == 0


def test_persist_osm_features_for_matching_coordinates_derives_exact_coordinate_rows(
    tmp_path: Path,
) -> None:
    database_url = _seed_coordinate_ready_database(tmp_path)
    engine = create_engine(database_url)

    with Session(engine) as session:
        listing = session.get(Listing, 1)
        assert listing is not None
        session.add(
            OsmFeature(
                listing_id=listing.id,
                latitude=listing.latitude,
                longitude=listing.longitude,
                feature_version="osm_local_v1",
                transport_count_500m=2,
                transport_count_1000m=3,
                nearest_transport_m=180.0,
                schools_count_1000m=1,
                parks_count_1000m=4,
                shops_count_1000m=5,
                healthcare_count_1000m=1,
                source_summary={
                    "attribution": "OpenStreetMap contributors",
                    "live_osm_called": True,
                    "elements_seen": 12,
                },
            )
        )
        same_point = Listing(
            city="Moscow",
            latitude=listing.latitude,
            longitude=listing.longitude,
            price_rub=13_000_000,
            total_area_m2=50.0,
            rooms=2,
            property_type="apartment",
            has_coordinates=True,
            is_ml_ready=True,
            cleaning_status="clean",
        )
        session.add(same_point)
        session.commit()

    with Session(engine) as session:
        result = persist_osm_features_for_matching_coordinates(session)
        session.commit()

    assert result.rows_inserted == 1
    assert result.rows_updated == 0
    assert result.rows_selected == 1
    assert result.selected_listing_ids == (3,)

    with Session(engine) as session:
        derived = session.query(OsmFeature).filter_by(listing_id=3).one()
        assert derived.transport_count_500m == 2
        assert derived.parks_count_1000m == 4
        assert derived.source_summary["derivation"] == "coordinate_exact_match"
        assert derived.source_summary["derived_from_listing_id"] == 1
        assert derived.source_summary["live_osm_called"] is False
        assert derived.source_summary["source_live_osm_called"] is True
        assert session.query(OsmFeature).filter_by(listing_id=2).count() == 0


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


def test_osm_enrichment_dry_run_live_overpass_reports_missing_distinct_coordinates(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    database_url = _seed_coordinate_ready_database(tmp_path)
    engine = create_engine(database_url)

    with Session(engine) as session:
        listing_with_feature = session.get(Listing, 1)
        assert listing_with_feature is not None
        listing_to_duplicate = session.get(Listing, 2)
        assert listing_to_duplicate is not None
        session.add(
            OsmFeature(
                listing_id=listing_with_feature.id,
                latitude=listing_with_feature.latitude,
                longitude=listing_with_feature.longitude,
                feature_version="osm_local_v1",
                transport_count_500m=1,
                transport_count_1000m=2,
                nearest_transport_m=120.0,
                schools_count_1000m=1,
                parks_count_1000m=1,
                shops_count_1000m=1,
                healthcare_count_1000m=1,
                source_summary={"live_osm_called": True},
            )
        )
        session.add(
            Listing(
                city="Moscow",
                latitude=listing_to_duplicate.latitude,
                longitude=listing_to_duplicate.longitude,
                price_rub=16_000_000,
                total_area_m2=57.0,
                rooms=2,
                property_type="apartment",
                has_coordinates=True,
                is_ml_ready=True,
                cleaning_status="clean",
            )
        )
        session.commit()

    assert (
        main(
            [
                "--database-url",
                database_url,
                "--limit",
                "10",
                "--live-overpass",
                "--dry-run",
                "--json",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)

    assert payload["rows_available"] == 1
    assert payload["rows_selected"] == 1
    assert payload["selected_listing_ids"] == [2]
    assert payload["selection_mode"] == "live_overpass_missing_distinct_coordinates"


def test_osm_enrichment_write_cli_persists_fixture_elements(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    database_url = _seed_coordinate_ready_database(tmp_path)
    elements_file = tmp_path / "osm-elements.json"
    elements_file.write_text(
        json.dumps(
            {
                "1": [
                    {
                        "type": "node",
                        "lat": 55.7510,
                        "lon": 37.6110,
                        "tags": {"public_transport": "station"},
                    }
                ],
                "2": [],
            }
        ),
        encoding="utf-8",
    )

    assert (
        main(
            [
                "--database-url",
                database_url,
                "--limit",
                "2",
                "--elements-file",
                str(elements_file),
                "--write",
                "--json",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)

    assert payload["dry_run"] is False
    assert payload["live_osm_called"] is False
    assert payload["rows_inserted"] == 2
    assert payload["rows_updated"] == 0

    engine = create_engine(database_url)
    with Session(engine) as session:
        assert session.query(OsmFeature).count() == 2


def test_osm_enrichment_cli_appends_progress_log_for_write_batch(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    database_url = _seed_coordinate_ready_database(tmp_path)
    elements_file = tmp_path / "osm-elements.json"
    progress_log = tmp_path / "logs" / "osm-batches.jsonl"
    elements_file.write_text(
        json.dumps(
            {
                "1": [
                    {
                        "type": "node",
                        "lat": 55.7510,
                        "lon": 37.6110,
                        "tags": {"public_transport": "station"},
                    }
                ],
                "2": [],
            }
        ),
        encoding="utf-8",
    )

    assert (
        main(
            [
                "--database-url",
                database_url,
                "--limit",
                "2",
                "--elements-file",
                str(elements_file),
                "--write",
                "--json",
                "--progress-log",
                str(progress_log),
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)
    log_payloads = [
        json.loads(line) for line in progress_log.read_text(encoding="utf-8").splitlines()
    ]

    assert payload["rows_inserted"] == 2
    assert len(log_payloads) == 1
    assert log_payloads[0]["operation"] == "elements_file"
    assert log_payloads[0]["limit"] == 2
    assert log_payloads[0]["radius_m"] == 1000
    assert log_payloads[0]["delay_seconds"] == 1.0
    assert log_payloads[0]["timeout_seconds"] == 30.0
    assert log_payloads[0]["result"]["selected_listing_ids"] == [1, 2]
    assert log_payloads[0]["result"]["rows_inserted"] == 2


def test_osm_enrichment_cli_derives_exact_coordinate_matches(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    database_url = _seed_coordinate_ready_database(tmp_path)
    engine = create_engine(database_url)

    with Session(engine) as session:
        listing = session.get(Listing, 1)
        assert listing is not None
        session.add(
            Listing(
                city="Moscow",
                latitude=listing.latitude,
                longitude=listing.longitude,
                price_rub=13_000_000,
                total_area_m2=50.0,
                rooms=2,
                property_type="apartment",
                has_coordinates=True,
                is_ml_ready=True,
                cleaning_status="clean",
            )
        )
        session.add(
            OsmFeature(
                listing_id=listing.id,
                latitude=listing.latitude,
                longitude=listing.longitude,
                feature_version="osm_local_v1",
                transport_count_500m=1,
                transport_count_1000m=2,
                nearest_transport_m=120.0,
                schools_count_1000m=1,
                parks_count_1000m=1,
                shops_count_1000m=1,
                healthcare_count_1000m=1,
                source_summary={
                    "attribution": "OpenStreetMap contributors",
                    "live_osm_called": True,
                },
            )
        )
        session.commit()

    assert (
        main(
            [
                "--database-url",
                database_url,
                "--derive-coordinate-matches",
                "--write",
                "--json",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)

    assert payload["rows_inserted"] == 1
    assert payload["live_osm_called"] is False
    assert payload["selected_listing_ids"] == [3]


def test_persist_osm_features_from_geojson_file_uses_local_extract(
    tmp_path: Path,
) -> None:
    database_url = _seed_coordinate_ready_database(tmp_path)
    geojson_file = _write_geojson_extract(tmp_path)
    engine = create_engine(database_url)

    with Session(engine) as session:
        result = persist_osm_features_from_geojson_file(
            session,
            geojson_file,
            limit=2,
        )
        session.commit()

    assert result.rows_available == 2
    assert result.rows_selected == 2
    assert result.rows_inserted == 2
    assert result.rows_updated == 0
    assert result.live_osm_called is False

    with Session(engine) as session:
        first = session.query(OsmFeature).filter_by(listing_id=1).one()
        second = session.query(OsmFeature).filter_by(listing_id=2).one()

    assert first.transport_count_1000m == 1
    assert first.schools_count_1000m == 1
    assert first.source_summary["source"] == "bbbike_geojson_extract"
    assert first.source_summary["live_osm_called"] is False
    assert first.source_summary["source_features_indexed"] == 2
    assert second.transport_count_1000m == 0
    assert second.schools_count_1000m == 0


def test_osm_enrichment_cli_persists_local_geojson_extract(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    database_url = _seed_coordinate_ready_database(tmp_path)
    geojson_file = _write_geojson_extract(tmp_path)
    progress_log = tmp_path / "logs" / "osm-batches.jsonl"

    assert (
        main(
            [
                "--database-url",
                database_url,
                "--limit",
                "2",
                "--geojson-file",
                str(geojson_file),
                "--write",
                "--json",
                "--progress-log",
                str(progress_log),
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)
    log_payloads = [
        json.loads(line) for line in progress_log.read_text(encoding="utf-8").splitlines()
    ]

    assert payload["rows_inserted"] == 2
    assert payload["live_osm_called"] is False
    assert log_payloads[0]["operation"] == "geojson_file"
    assert log_payloads[0]["geojson_file"] == str(geojson_file)


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


def _write_geojson_extract(tmp_path: Path) -> Path:
    geojson_file = tmp_path / "moscow.geojson"
    lines = [
        '{"type":"FeatureCollection","features":[\n',
        json.dumps(
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [37.611, 55.751]},
                "properties": {"public_transport": "station"},
            }
        )
        + ",\n",
        json.dumps(
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [37.612, 55.7505]},
                "properties": {"amenity": "school"},
            }
        )
        + "\n",
        "]}\n",
    ]
    geojson_file.write_text("".join(lines), encoding="utf-8")
    return geojson_file


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
