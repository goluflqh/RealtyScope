from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import joblib
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from realtyscope.database.base import Base
from realtyscope.database.models import Listing, ListingObservation, RawListingRecord, Source
from realtyscope.ml.features import FEATURE_VERSION, FeatureRow
from realtyscope.ml.train import main, train_baseline_model


def test_train_baseline_model_beats_naive_on_tiny_fixture(tmp_path: Path) -> None:
    result = train_baseline_model(feature_rows=_tiny_feature_rows(), output_dir=tmp_path)

    assert result.metrics["mae"] <= result.metrics["naive_mae"]
    assert result.metrics["rows_total"] == 8
    assert result.metrics["feature_count"] >= 3
    assert result.model_version == "baseline_ridge_v1"
    assert result.mlflow_run_id is None
    assert result.artifact_path.exists()
    artifact = joblib.load(result.artifact_path)
    assert artifact["model_version"] == result.model_version
    assert artifact["feature_names"] == sorted(_tiny_feature_rows()[0].features)


def test_train_cli_reads_feature_rows_and_writes_artifact(tmp_path: Path, capsys) -> None:
    database_url = _seed_training_database(tmp_path)
    output_dir = tmp_path / "models"

    assert main(["--database-url", database_url, "--output-dir", str(output_dir), "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["model_version"] == "baseline_ridge_v1"
    assert payload["metrics"]["rows_total"] == 12
    assert payload["metrics"]["mae"] <= payload["metrics"]["naive_mae"]
    assert Path(payload["artifact_path"]).exists()


def _tiny_feature_rows() -> list[FeatureRow]:
    rows: list[FeatureRow] = []
    for index, area in enumerate([40, 45, 50, 55, 60, 65, 70, 75], start=1):
        target = 2_000_000 + area * 220_000
        rows.append(
            FeatureRow(
                listing_id=index,
                feature_version=FEATURE_VERSION,
                target_price_rub=target,
                features={
                    "total_area_m2": float(area),
                    "rooms": 1.0 if area < 50 else 2.0,
                    "latest_observation_price_per_m2": 220_000.0,
                    "osm_missing": 1.0,
                },
            )
        )
    return rows


def _seed_training_database(tmp_path: Path) -> str:
    database_path = tmp_path / "ml-training.sqlite3"
    database_url = f"sqlite+pysqlite:///{database_path.as_posix()}"
    engine = create_engine(database_url)
    Base.metadata.create_all(engine)

    observed_at = datetime(2026, 6, 2, 9, 0, tzinfo=UTC)
    with Session(engine) as session:
        source = Source(name="domclick", source_type="listing")
        session.add(source)
        session.flush()
        for index, area in enumerate(range(40, 100, 5), start=1):
            price = 2_000_000 + area * 220_000
            raw = RawListingRecord(
                source_id=source.id,
                source_listing_id=f"train-{index}",
                observed_at=observed_at,
                payload_hash=f"train-hash-{index}",
                raw_payload={"id": f"train-{index}", "price": price},
            )
            listing = Listing(
                city="Moscow",
                latitude=55.75 + index * 0.001,
                longitude=37.61 + index * 0.001,
                price_rub=price,
                total_area_m2=float(area),
                rooms=1 if area < 50 else 2 if area < 75 else 3,
                floor=5,
                floors_total=20,
                building_year=2018,
                property_type="apartment",
                has_coordinates=True,
                is_ml_ready=True,
                cleaning_status="ml_ready",
            )
            session.add_all([raw, listing])
            session.flush()
            session.add(
                ListingObservation(
                    listing_id=listing.id,
                    source_id=source.id,
                    raw_listing_id=raw.id,
                    source_listing_id=f"train-{index}",
                    observed_at=observed_at,
                    price_rub=price,
                    price_per_m2=price / area,
                    total_area_m2=float(area),
                    rooms=listing.rooms,
                    floor=5,
                    floors_total=20,
                    active=True,
                    status="observed",
                )
            )
        session.commit()
    return database_url
