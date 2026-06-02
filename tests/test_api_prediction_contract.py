from __future__ import annotations

from fastapi.testclient import TestClient
from services.api.app import main as api_main


class FakePredictionModel:
    feature_names = ("rooms", "total_area_m2")
    feature_version = "ml_features_v1"
    metrics = {"mae": 123.4, "naive_mae": 567.8}
    model_version = "fake_baseline_v1"

    def predict(self, features: dict[str, float]) -> float:
        return 10_000_000 + features["total_area_m2"] * 100_000 + features["rooms"] * 250_000


def test_predict_endpoint_returns_contract_with_fake_model_dependency() -> None:
    client = _client_with_fake_prediction_model()
    try:
        response = client.post(
            "/predict",
            json={"features": {"rooms": 2, "total_area_m2": 60.5}},
        )
    finally:
        api_main.app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "predicted_price_rub": 16_550_000.0,
        "model_version": "fake_baseline_v1",
        "feature_version": "ml_features_v1",
        "metrics_summary": {"mae": 123.4, "naive_mae": 567.8},
        "input_features_echo": {"rooms": 2.0, "total_area_m2": 60.5},
        "feature_names": ["rooms", "total_area_m2"],
        "caveat": (
            "Phase 5 non-leaky baseline contract result; not a final independent appraisal model."
        ),
    }


def test_predict_endpoint_rejects_missing_model_features() -> None:
    client = _client_with_fake_prediction_model()
    try:
        response = client.post("/predict", json={"features": {"rooms": 2}})
    finally:
        api_main.app.dependency_overrides.clear()

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert detail["missing_features"] == ["total_area_m2"]
    assert detail["unexpected_features"] == []


def test_predict_endpoint_rejects_unexpected_model_features() -> None:
    client = _client_with_fake_prediction_model()
    try:
        response = client.post(
            "/predict",
            json={"features": {"rooms": 2, "total_area_m2": 60.5, "extra": 1}},
        )
    finally:
        api_main.app.dependency_overrides.clear()

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert detail["missing_features"] == []
    assert detail["unexpected_features"] == ["extra"]


def _client_with_fake_prediction_model() -> TestClient:
    def override_model() -> FakePredictionModel:
        return FakePredictionModel()

    api_main.app.dependency_overrides[api_main.get_prediction_model] = override_model
    return TestClient(api_main.app)
