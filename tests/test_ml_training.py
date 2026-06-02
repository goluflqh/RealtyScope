from __future__ import annotations

import json
import sys
from contextlib import AbstractContextManager
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import joblib
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from realtyscope.database.base import Base
from realtyscope.database.models import Listing, ListingObservation, RawListingRecord, Source
from realtyscope.ml.features import FEATURE_VERSION, FeatureRow
from realtyscope.ml.train import main, train_baseline_model

NON_LEAKY_FEATURE_VERSION = "ml_features_v2_non_leaky"


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


def test_train_baseline_model_records_non_leaky_feature_version(tmp_path: Path) -> None:
    feature_rows = _tiny_feature_rows(
        feature_version=NON_LEAKY_FEATURE_VERSION,
        include_latest_price_feature=False,
    )

    result = train_baseline_model(feature_rows=feature_rows, output_dir=tmp_path)

    assert result.feature_version == NON_LEAKY_FEATURE_VERSION
    assert result.model_version == "baseline_ridge_v2_non_leaky"
    artifact = joblib.load(result.artifact_path)
    assert artifact["feature_version"] == NON_LEAKY_FEATURE_VERSION
    assert artifact["model_version"] == result.model_version
    assert not any("price" in feature_name for feature_name in artifact["feature_names"])


def test_train_baseline_model_groups_duplicate_listings_before_split(tmp_path: Path) -> None:
    feature_rows = _duplicate_listing_feature_rows()

    result = train_baseline_model(feature_rows=feature_rows, output_dir=tmp_path)

    artifact = joblib.load(result.artifact_path)
    train_listing_ids = set(artifact["split"]["train_listing_ids"])
    test_listing_ids = set(artifact["split"]["test_listing_ids"])
    assert train_listing_ids.isdisjoint(test_listing_ids)
    assert train_listing_ids | test_listing_ids == {1, 2, 3, 4, 5, 6}
    assert result.metrics["rows_total"] == 12
    assert result.metrics["train_listing_groups"] + result.metrics["test_listing_groups"] == 6


def test_train_baseline_model_logs_actual_feature_version_to_mlflow(
    tmp_path: Path, monkeypatch
) -> None:
    fake_mlflow = _FakeMlflow()
    monkeypatch.setitem(sys.modules, "mlflow", fake_mlflow)
    feature_rows = _tiny_feature_rows(
        feature_version=NON_LEAKY_FEATURE_VERSION,
        include_latest_price_feature=False,
    )

    result = train_baseline_model(
        feature_rows=feature_rows,
        output_dir=tmp_path,
        mlflow_tracking_uri=tmp_path.as_uri(),
    )

    assert result.mlflow_run_id == "run-123"
    assert fake_mlflow.tracking_uri == tmp_path.as_uri()
    assert fake_mlflow.params["feature_version"] == NON_LEAKY_FEATURE_VERSION
    assert fake_mlflow.params["model_version"] == "baseline_ridge_v2_non_leaky"
    assert fake_mlflow.artifacts == [str(result.artifact_path)]


def test_train_cli_reads_feature_rows_and_writes_artifact(tmp_path: Path, capsys) -> None:
    database_url = _seed_training_database(tmp_path)
    output_dir = tmp_path / "models"

    assert main(["--database-url", database_url, "--output-dir", str(output_dir), "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["model_version"] == "baseline_ridge_v1"
    assert payload["metrics"]["rows_total"] == 12
    assert payload["metrics"]["mae"] <= payload["metrics"]["naive_mae"]
    assert Path(payload["artifact_path"]).exists()


def test_train_cli_can_use_non_leaky_feature_version(tmp_path: Path, capsys) -> None:
    database_url = _seed_training_database(tmp_path)
    output_dir = tmp_path / "models"

    assert (
        main(
            [
                "--database-url",
                database_url,
                "--output-dir",
                str(output_dir),
                "--feature-version",
                NON_LEAKY_FEATURE_VERSION,
                "--json",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)

    assert payload["feature_version"] == NON_LEAKY_FEATURE_VERSION
    assert payload["model_version"] == "baseline_ridge_v2_non_leaky"
    artifact = joblib.load(payload["artifact_path"])
    assert not any("price" in feature_name for feature_name in artifact["feature_names"])


def _tiny_feature_rows(
    *,
    feature_version: str = FEATURE_VERSION,
    include_latest_price_feature: bool = True,
) -> list[FeatureRow]:
    rows: list[FeatureRow] = []
    for index, area in enumerate([40, 45, 50, 55, 60, 65, 70, 75], start=1):
        target = 2_000_000 + area * 220_000
        features = {
            "total_area_m2": float(area),
            "rooms": 1.0 if area < 50 else 2.0,
            "osm_missing": 1.0,
        }
        if include_latest_price_feature:
            features["latest_observation_price_per_m2"] = 220_000.0
        rows.append(
            FeatureRow(
                listing_id=index,
                feature_version=feature_version,
                target_price_rub=target,
                features=features,
            )
        )
    return rows


def _duplicate_listing_feature_rows() -> list[FeatureRow]:
    rows: list[FeatureRow] = []
    for listing_id, area in enumerate([40, 45, 50, 55, 60, 65], start=1):
        for observation_index in range(2):
            rows.append(
                FeatureRow(
                    listing_id=listing_id,
                    feature_version=NON_LEAKY_FEATURE_VERSION,
                    target_price_rub=2_000_000 + area * 220_000 + observation_index * 10_000,
                    features={
                        "total_area_m2": float(area),
                        "rooms": 1.0 if area < 50 else 2.0,
                        "observation_count": float(observation_index + 1),
                        "osm_missing": 1.0,
                    },
                )
            )
    return rows


class _FakeRunContext(AbstractContextManager[SimpleNamespace]):
    def __enter__(self) -> SimpleNamespace:
        return SimpleNamespace(info=SimpleNamespace(run_id="run-123"))

    def __exit__(self, *exc_info: object) -> None:
        return None


class _FakeMlflow:
    def __init__(self) -> None:
        self.tracking_uri: str | None = None
        self.params: dict[str, object] = {}
        self.metrics: dict[str, float] = {}
        self.artifacts: list[str] = []

    def set_tracking_uri(self, tracking_uri: str) -> None:
        self.tracking_uri = tracking_uri

    def start_run(self, *, run_name: str) -> _FakeRunContext:
        self.params["run_name"] = run_name
        return _FakeRunContext()

    def log_params(self, params: dict[str, object]) -> None:
        self.params.update(params)

    def log_metrics(self, metrics: dict[str, float]) -> None:
        self.metrics.update(metrics)

    def log_artifact(self, artifact_path: str) -> None:
        self.artifacts.append(artifact_path)


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
