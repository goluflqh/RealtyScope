from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime

from fastapi.testclient import TestClient
from services.api.app import main as api_main
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from tests.test_api_data_routes import _seed_session

from realtyscope.database.base import Base
from realtyscope.database.models import AppLog


class FakePredictionModel:
    feature_names = ("rooms", "total_area_m2")
    feature_version = "ml_features_v2_non_leaky"
    metrics = {"mae": 21_189_758.79, "naive_mae": 23_656_479.23}
    model_version = "baseline_ridge_v2_non_leaky"
    feature_importance = (
        {"feature": "total_area_m2", "importance": 0.8, "coefficient": 0.8},
        {"feature": "rooms", "importance": 0.2, "coefficient": 0.2},
    )


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
        "artifact_path": "data/processed/models/phase5/baseline_ridge_v2_non_leaky.joblib",
        "model_version": "baseline_ridge_v2_non_leaky",
        "feature_version": "ml_features_v2_non_leaky",
        "feature_names": ["rooms", "total_area_m2"],
        "feature_count": 2,
        "metrics_summary": {"mae": 21_189_758.79, "naive_mae": 23_656_479.23},
        "feature_importance": [
            {"feature": "total_area_m2", "importance": 0.8, "coefficient": 0.8},
            {"feature": "rooms", "importance": 0.2, "coefficient": 0.2},
        ],
        "error": None,
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
    assert payload["model_version"] is None
    assert payload["feature_names"] == []
    assert payload["feature_importance"] == []
    assert isinstance(payload["error"], str)


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
    assert payload["recent_errors"] == [
        {
            "id": 1,
            "level": "ERROR",
            "event_type": "domclick.capture",
            "message": "Timed out during scheduled capture",
            "created_at": "2026-06-02T08:00:00+00:00",
            "source_id": None,
            "ingestion_run_id": None,
            "context": {"stage": "capture"},
        }
    ]


def _client_with_fake_model() -> TestClient:
    def override_model() -> FakePredictionModel:
        return FakePredictionModel()

    api_main.app.dependency_overrides[api_main.get_optional_prediction_model] = override_model
    return TestClient(api_main.app)


def _client_with_seeded_monitoring_database(tmp_path) -> TestClient:
    database_path = tmp_path / "api_monitoring.sqlite3"
    engine = create_engine(
        f"sqlite+pysqlite:///{database_path.as_posix()}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        _seed_session(session)
        session.add(
            AppLog(
                level="ERROR",
                event_type="domclick.capture",
                message="Timed out during scheduled capture",
                created_at=datetime(2026, 6, 2, 8, 0, tzinfo=UTC),
                context={"stage": "capture"},
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
    return TestClient(api_main.app)
