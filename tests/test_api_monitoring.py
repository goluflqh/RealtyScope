from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path

import joblib
from fastapi.testclient import TestClient
from services.api.app import main as api_main
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session
from tests.test_api_data_routes import _seed_session

from realtyscope.config import Settings
from realtyscope.database.base import Base
from realtyscope.database.models import (
    AppLog,
    Listing,
    ListingObservation,
    RawListingRecord,
    Source,
)
from realtyscope.ml.model_selection import SelectedModel, save_selected_model


class FakePredictionModel:
    feature_names = ("rooms", "total_area_m2")
    feature_version = "ml_features_v2_non_leaky"
    metrics = {"mae": 21_189_758.79, "naive_mae": 23_656_479.23}
    model_version = "selected_price_model_v1_non_leaky"
    feature_importance = (
        {"feature": "total_area_m2", "importance": 0.8, "coefficient": 0.8},
        {"feature": "rooms", "importance": 0.2, "coefficient": 0.2},
    )


class FakeRedisClient:
    pass


class ConstantPredictionModel:
    def __init__(self, value: float) -> None:
        self.value = value

    def predict(self, rows: list[list[float]]) -> list[float]:
        return [self.value for _ in rows]


def test_model_metadata_endpoint_reports_loaded_model_contract() -> None:
    client = _client_with_fake_model()
    try:
        response = client.get("/model/metadata")
    finally:
        api_main.app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "active_model_name": "realtyscope-price-model",
        "artifact_path": "data/processed/models/phase5/selected_price_model_v1_non_leaky.joblib",
        "model_selection_mode": "best_metric",
        "model_selection_reason": "dependency_override",
        "model_candidates": [],
        "selected_candidate": None,
        "training_candidates": [],
        "model_version": "selected_price_model_v1_non_leaky",
        "feature_version": "ml_features_v2_non_leaky",
        "feature_names": ["rooms", "total_area_m2"],
        "feature_count": 2,
        "metrics_summary": {"mae": 21_189_758.79, "naive_mae": 23_656_479.23},
        "feature_importance": [
            {"feature": "total_area_m2", "importance": 0.8, "coefficient": 0.8},
            {"feature": "rooms", "importance": 0.2, "coefficient": 0.2},
        ],
        "selected_model": None,
        "error": None,
    }


def test_model_metadata_endpoint_reports_selected_model_state(tmp_path: Path, monkeypatch) -> None:
    selection_path = tmp_path / "selected_model.json"
    active = SelectedModel(
        model_version="hist_gradient_boosting_v1",
        artifact_path=tmp_path / "hist_gradient_boosting_v1.joblib",
        feature_version="ml_features_v2_non_leaky",
        metrics={"mae": 90.0, "rmse": 120.0, "r2": 0.53},
        selected_at=datetime(2026, 6, 20, 7, 0, tzinfo=UTC),
        previous=SelectedModel(
            model_version="baseline_ridge_v2_non_leaky",
            artifact_path=tmp_path / "baseline_ridge_v2_non_leaky.joblib",
            feature_version="ml_features_v2_non_leaky",
            metrics={"mae": 100.0, "rmse": 140.0, "r2": 0.50},
            selected_at=datetime(2026, 6, 20, 6, 0, tzinfo=UTC),
        ),
    )
    save_selected_model(selection_path, active)
    monkeypatch.setattr(
        api_main,
        "get_settings",
        lambda: Settings(ACTIVE_MODEL_SELECTION_PATH=str(selection_path)),
    )
    client = _client_with_fake_model()
    try:
        response = client.get("/model/metadata")
    finally:
        api_main.app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["selected_model"] == {
        "model_version": "hist_gradient_boosting_v1",
        "artifact_path": str(tmp_path / "hist_gradient_boosting_v1.joblib"),
        "feature_version": "ml_features_v2_non_leaky",
        "metrics_summary": {"mae": 90.0, "rmse": 120.0, "r2": 0.53},
        "selected_at": "2026-06-20T07:00:00+00:00",
        "rollback_available": True,
        "previous_model_version": "baseline_ridge_v2_non_leaky",
        "previous_artifact_path": str(tmp_path / "baseline_ridge_v2_non_leaky.joblib"),
    }


def test_model_metadata_endpoint_reports_unavailable_model() -> None:
    def override_model() -> None:
        return None

    api_main.app.dependency_overrides[api_main.get_optional_prediction_model] = override_model
    client = TestClient(api_main.app)
    try:
        response = client.get("/model/metadata")
    finally:
        api_main.app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "unavailable"
    assert payload["model_selection_mode"] == "best_metric"
    assert payload["model_selection_reason"] == "unavailable"
    assert payload["model_candidates"] == []
    assert payload["selected_candidate"] is None
    assert payload["training_candidates"] == []
    assert payload["model_version"] is None
    assert payload["feature_names"] == []
    assert payload["feature_importance"] == []
    assert payload["selected_model"] is None
    assert isinstance(payload["error"], str)


def test_model_artifact_selector_prefers_best_validation_metric(tmp_path: Path) -> None:
    weak_artifact = _write_model_artifact(
        tmp_path / "phase4" / "baseline_ridge_v1.joblib",
        model_version="baseline_ridge_v1",
        r2=0.12,
        mae=30_000_000.0,
    )
    selected_artifact = _write_model_artifact(
        tmp_path / "phase5" / "baseline_ridge_v2_non_leaky.joblib",
        model_version="baseline_ridge_v2_non_leaky",
        r2=0.62,
        mae=21_000_000.0,
    )

    selection = api_main._select_model_artifact(
        explicit_path=weak_artifact,
        search_dir=tmp_path,
        selection_mode="best_metric",
    )

    assert selection.path == selected_artifact
    assert selection.mode == "best_metric"
    assert selection.reason == "best_validation_metric"
    assert [candidate["model_version"] for candidate in selection.candidates] == [
        "baseline_ridge_v2_non_leaky",
        "baseline_ridge_v1",
    ]


def test_model_artifact_selector_skips_unreadable_or_unrelated_joblibs(tmp_path: Path) -> None:
    joblib.dump(object(), tmp_path / "00-bare-estimator.joblib")
    (tmp_path / "01-corrupt.joblib").write_text("not a joblib", encoding="utf-8")
    selected_artifact = _write_model_artifact(
        tmp_path / "02-selected.joblib",
        model_version="selected_price_model_v1_non_leaky",
        r2=0.62,
        mae=21_000_000.0,
    )

    selection = api_main._select_model_artifact(
        explicit_path=tmp_path / "missing.joblib",
        search_dir=tmp_path,
        selection_mode="best_metric",
    )

    assert selection.path == selected_artifact
    assert [candidate["model_version"] for candidate in selection.candidates] == [
        "selected_price_model_v1_non_leaky"
    ]


def test_model_metadata_reports_selected_training_candidate(tmp_path: Path) -> None:
    artifact_path = _write_model_artifact(
        tmp_path / "selected_price_model_v1_non_leaky.joblib",
        model_version="selected_price_model_v1_non_leaky",
        r2=0.64,
        mae=20_000_000.0,
        selected_candidate="random_forest",
        candidate_metrics=[
            {"candidate_name": "random_forest", "r2": 0.64, "mae": 20_000_000.0},
            {"candidate_name": "ridge", "r2": 0.62, "mae": 21_000_000.0},
        ],
    )
    model = api_main.ArtifactPredictionModel.from_artifact(artifact_path)

    payload = api_main._model_metadata_payload(model)

    assert payload["model_version"] == "selected_price_model_v1_non_leaky"
    assert payload["selected_candidate"] == "random_forest"
    assert payload["training_candidates"] == [
        {"candidate_name": "random_forest", "r2": 0.64, "mae": 20_000_000.0},
        {"candidate_name": "ridge", "r2": 0.62, "mae": 21_000_000.0},
    ]


def test_monitoring_status_endpoint_combines_counts_model_and_recent_errors(tmp_path) -> None:
    client = _client_with_seeded_monitoring_database(tmp_path)
    try:
        response = client.get("/monitoring/status")
    finally:
        api_main.app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["service"] == "realtyscope-api"
    assert payload["status"] == "ok"
    assert payload["data_quality"]["listings_total"] == 1
    assert payload["data_quality"]["observations_total"] == 2
    assert payload["data_quality"]["observation_date_count"] == 2
    assert payload["data_quality"]["first_observed_date"] == "2026-05-31"
    assert payload["data_quality"]["last_observed_date"] == "2026-06-02"
    assert payload["data_quality"]["listings_with_observation_history"] == 1
    assert payload["data_quality"]["max_observation_dates_per_listing"] == 2
    assert payload["data_quality"]["listing_price_change_count"] == 1
    assert payload["data_quality"]["lifecycle_target_rows"] == 1
    assert payload["data_quality"]["observed_exposure_target_rows"] == 1
    assert payload["data_quality"]["observed_exposure_can_forecast"] is False
    assert payload["data_quality"]["observed_exposure_median_days"] == 2
    assert payload["data_quality"]["observed_exposure_target_source"] == (
        "observed_history_lower_bound"
    )
    assert payload["data_quality"]["observed_exposure_forecast_segments"] == [
        {
            "rooms": 2,
            "target_rows": 1,
            "median_observed_exposure_days": 2,
            "target_source": "observed_history_lower_bound",
        }
    ]
    assert payload["data_quality"]["observation_status_counts"] == {
        "observed": 1,
        "removed": 1,
    }
    assert payload["data_quality"]["inactive_observations_total"] == 1
    assert payload["data_quality"]["latest_ingestion_run"]["started_at"] == (
        "2026-05-31T12:00:00+00:00"
    )
    latest_success = payload["data_quality"]["latest_successful_ingestion_run"]
    assert latest_success["source_name"] == "domclick"
    assert latest_success["status"] == "success"
    assert latest_success["started_at"] == "2026-05-31T12:00:00+00:00"
    assert latest_success["records_seen"] == 2
    assert latest_success["normalized_count"] == 1
    assert payload["model"]["status"] == "ready"
    assert payload["model"]["feature_version"] == "ml_features_v2_non_leaky"
    assert payload["model"]["data_freshness"]["status"] == "unknown"
    service_rows = {row["key"]: row for row in payload["services"]}
    assert service_rows["api"]["status"] == "ok"
    assert service_rows["database"]["status"] == "ok"
    assert service_rows["cache"]["status"] == "ok"
    assert service_rows["model"]["status"] == "ok"
    assert service_rows["ingestion"]["status"] == "ok"
    assert service_rows["ingestion"]["count"] == 1
    assert payload["recent_errors"] == [
        {
            "id": 1,
            "level": "ERROR",
            "event_type": "domclick.capture",
            "message": "Timed out during scheduled capture Traceback hidden",
            "created_at": "2026-06-02T08:00:00+00:00",
            "source_id": None,
            "ingestion_run_id": None,
            "context": {"stage": "capture"},
        }
    ]
    assert payload["recent_logs"] == [
        {
            "id": 1,
            "level": "ERROR",
            "event_type": "domclick.capture",
            "message": "Timed out during scheduled capture Traceback hidden",
            "created_at": "2026-06-02T08:00:00+00:00",
            "source_id": None,
            "ingestion_run_id": None,
        },
        {
            "id": 2,
            "level": "INFO",
            "event_type": "api.monitoring",
            "message": "Monitoring status generated",
            "created_at": "2026-06-02T07:30:00+00:00",
            "source_id": None,
            "ingestion_run_id": None,
        },
    ]


def test_model_data_freshness_keeps_validated_snapshot_when_database_is_newer() -> None:
    freshness = api_main._model_data_freshness(
        model_payload={"metrics_summary": {"rows_total": 17_046}},
        data_quality={"listings_total": 17_287},
    )

    assert freshness == {
        "status": "validated_snapshot",
        "status_label": "validated training snapshot",
        "model_rows_total": 17_046,
        "current_listings_total": 17_287,
        "row_delta": 241,
        "row_delta_pct": 1.41,
        "requires_retrain": False,
        "note": (
            "Model remains the last validated artifact; retrain only after a candidate "
            "passes the promotion gate."
        ),
    }


def test_exposure_forecast_endpoint_reports_observed_lower_bound_target(tmp_path) -> None:
    client = _client_with_seeded_monitoring_database(tmp_path)
    try:
        response = client.get("/stats/exposure-forecast")
    finally:
        api_main.app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "partial"
    assert payload["can_forecast"] is False
    assert payload["target_source"] == "observed_history_lower_bound"
    assert payload["terminal_lifecycle_target_rows"] == 1
    assert payload["terminal_lifecycle_can_forecast"] is False
    assert payload["observed_exposure_target_rows"] == 1
    assert payload["observed_exposure_min_target_rows"] == 100
    assert payload["median_observed_exposure_days"] == 2
    assert payload["max_observed_exposure_days"] == 2
    assert payload["forecast_segments"] == [
        {
            "rooms": 2,
            "target_rows": 1,
            "median_observed_exposure_days": 2,
            "target_source": "observed_history_lower_bound",
        }
    ]
    assert "нижняя граница" in payload["caveat"]


def test_exposure_forecast_endpoint_does_not_treat_observed_lower_bound_as_terminal_forecast(
    tmp_path,
) -> None:
    client, engine = _client_and_engine_with_seeded_monitoring_database(tmp_path)
    with Session(engine) as session:
        source = session.query(Source).filter_by(name="domclick").one()
        listing = session.query(Listing).one()
        raw_listing = session.query(RawListingRecord).one()
        first_observed_at = datetime(2026, 6, 1, 12, 0, tzinfo=UTC)
        for index in range(100):
            source_listing_id = f"observed-only-{index}"
            for offset in (0, 3):
                session.add(
                    ListingObservation(
                        listing_id=listing.id,
                        source_id=source.id,
                        raw_listing_id=raw_listing.id,
                        source_listing_id=source_listing_id,
                        observed_at=first_observed_at + timedelta(days=offset),
                        price_rub=18_000_000,
                        price_per_m2=300_000,
                        total_area_m2=60,
                        rooms=2,
                        floor=7,
                        floors_total=18,
                        active=True,
                        status="observed",
                    )
                )
        session.commit()

    try:
        response = client.get("/stats/exposure-forecast")
    finally:
        api_main.app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "partial"
    assert payload["can_forecast"] is False
    assert payload["terminal_lifecycle_target_rows"] == 1
    assert payload["terminal_lifecycle_can_forecast"] is False
    assert payload["observed_exposure_target_rows"] == 101
    assert payload["observed_exposure_can_forecast"] is True
    assert payload["target_source"] == "observed_history_lower_bound"


def test_exposure_forecast_endpoint_uses_inferred_lifecycle_gap_target(
    tmp_path,
) -> None:
    client, engine = _client_and_engine_with_seeded_monitoring_database(tmp_path)
    with Session(engine) as session:
        source = session.query(Source).filter_by(name="domclick").one()
        listing = session.query(Listing).one()
        raw_listing = session.query(RawListingRecord).one()
        session.query(ListingObservation).delete()
        first_observed_at = datetime(2026, 6, 1, 12, 0, tzinfo=UTC)
        for index in range(100):
            source_listing_id = f"gap-target-{index}"
            for offset in (0, 2):
                session.add(
                    ListingObservation(
                        listing_id=listing.id,
                        source_id=source.id,
                        raw_listing_id=raw_listing.id,
                        source_listing_id=source_listing_id,
                        observed_at=first_observed_at + timedelta(days=offset),
                        price_rub=18_000_000,
                        price_per_m2=300_000,
                        total_area_m2=60,
                        rooms=2,
                        floor=7,
                        floors_total=18,
                        active=True,
                        status="observed",
                    )
                )
        session.add(
            ListingObservation(
                listing_id=listing.id,
                source_id=source.id,
                raw_listing_id=raw_listing.id,
                source_listing_id="still-observed",
                observed_at=first_observed_at + timedelta(days=5),
                price_rub=19_000_000,
                price_per_m2=316_666,
                total_area_m2=60,
                rooms=2,
                floor=7,
                floors_total=18,
                active=True,
                status="observed",
            )
        )
        session.commit()

    try:
        response = client.get("/stats/exposure-forecast")
    finally:
        api_main.app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ready"
    assert payload["can_forecast"] is True
    assert payload["target_source"] == "observation_gap_inferred_lifecycle"
    assert payload["terminal_lifecycle_target_rows"] == 0
    assert payload["terminal_lifecycle_can_forecast"] is False
    assert payload["inferred_lifecycle_target_rows"] == 100
    assert payload["inferred_lifecycle_can_forecast"] is True
    assert payload["inferred_lifecycle_min_gap_days"] == 3
    assert payload["inferred_lifecycle_median_days"] == 2
    assert payload["method"] == "gap_inferred_lifecycle_median_v1"
    assert payload["forecast_segments"] == [
        {
            "rooms": 2,
            "target_rows": 100,
            "median_inferred_exposure_days": 2,
            "target_source": "observation_gap_inferred_lifecycle",
        }
    ]
    assert "прогноз исчезновения" in payload["caveat"]


def test_observation_trend_endpoint_forecasts_when_history_is_sufficient(tmp_path) -> None:
    client, engine = _client_and_engine_with_seeded_monitoring_database(tmp_path)
    with Session(engine) as session:
        source = session.query(Source).filter_by(name="domclick").one()
        listing = session.query(Listing).one()
        raw_listing = session.query(RawListingRecord).one()
        session.query(ListingObservation).delete()
        first_observed_at = datetime(2026, 6, 1, 12, 0, tzinfo=UTC)
        for day in range(8):
            price_per_m2 = 300_000 + day * 10_000
            session.add(
                ListingObservation(
                    listing_id=listing.id,
                    source_id=source.id,
                    raw_listing_id=raw_listing.id,
                    source_listing_id="trend-1",
                    observed_at=first_observed_at + timedelta(days=day),
                    price_rub=price_per_m2 * 60,
                    price_per_m2=price_per_m2,
                    total_area_m2=60,
                    rooms=2,
                    floor=7,
                    floors_total=18,
                    active=True,
                    status="observed",
                )
            )
        session.commit()

    try:
        response = client.get("/stats/observation-trend")
    finally:
        api_main.app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ready"
    assert payload["can_forecast"] is True
    assert payload["forecast_method"] == "linear_median_price_per_m2_v1"
    assert payload["forecast_horizon_days"] == 7
    assert payload["history_points"] == 8
    assert payload["trend_slope_per_day"] == 10_000
    assert payload["forecast_rows"][0] == {
        "observed_date": "2026-06-09",
        "forecast_median_price_per_m2": 380_000,
    }
    assert payload["forecast_rows"][-1] == {
        "observed_date": "2026-06-15",
        "forecast_median_price_per_m2": 440_000,
    }


def _client_with_fake_model() -> TestClient:
    def override_model() -> FakePredictionModel:
        return FakePredictionModel()

    api_main.app.dependency_overrides[api_main.get_optional_prediction_model] = override_model
    return TestClient(api_main.app)


def _write_model_artifact(
    path: Path,
    *,
    model_version: str,
    r2: float,
    mae: float,
    selected_candidate: str | None = None,
    candidate_metrics: list[dict[str, object]] | None = None,
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    artifact = {
        "feature_names": ["rooms", "total_area_m2"],
        "feature_version": "ml_features_v2_non_leaky",
        "metrics": {"r2": r2, "mae": mae, "rows_total": 100},
        "model": ConstantPredictionModel(18_000_000.0),
        "model_version": model_version,
    }
    if selected_candidate is not None:
        artifact["selected_candidate"] = selected_candidate
    if candidate_metrics is not None:
        artifact["candidate_metrics"] = candidate_metrics
    joblib.dump(artifact, path)
    return path


def _client_with_seeded_monitoring_database(tmp_path) -> TestClient:
    client, _engine = _client_and_engine_with_seeded_monitoring_database(tmp_path)
    return client


def _client_and_engine_with_seeded_monitoring_database(
    tmp_path,
) -> tuple[TestClient, Engine]:
    database_path = tmp_path / "api_monitoring.sqlite3"
    engine = create_engine(
        f"sqlite+pysqlite:///{database_path.as_posix()}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        _seed_session(session)
        _seed_terminal_observation(session)
        session.add(
            AppLog(
                level="ERROR",
                event_type="domclick.capture",
                message="Timed out during scheduled capture\nTraceback hidden",
                created_at=datetime(2026, 6, 2, 8, 0, tzinfo=UTC),
                context={"stage": "capture"},
            )
        )
        session.add(
            AppLog(
                level="INFO",
                event_type="api.monitoring",
                message="Monitoring status generated",
                created_at=datetime(2026, 6, 2, 7, 30, tzinfo=UTC),
            )
        )
        session.commit()

    def override_session() -> Iterator[Session]:
        with Session(engine) as session:
            yield session

    def override_model() -> FakePredictionModel:
        return FakePredictionModel()

    api_main.app.dependency_overrides[api_main.get_database_session] = override_session
    api_main.app.dependency_overrides[api_main.get_optional_prediction_model] = override_model
    api_main.app.dependency_overrides[api_main.get_redis_client] = lambda: FakeRedisClient()
    return TestClient(api_main.app), engine


def _seed_terminal_observation(session: Session) -> None:
    source = session.query(Source).filter_by(name="domclick").one()
    listing = session.query(Listing).one()
    raw_listing = session.query(RawListingRecord).one()
    session.add(
        ListingObservation(
            listing_id=listing.id,
            source_id=source.id,
            raw_listing_id=raw_listing.id,
            source_listing_id="api-1",
            observed_at=datetime(2026, 6, 2, 12, 0, tzinfo=UTC),
            price_rub=17_500_000,
            price_per_m2=289_256.2,
            total_area_m2=60.5,
            rooms=2,
            floor=7,
            floors_total=18,
            active=False,
            status="removed",
        )
    )
