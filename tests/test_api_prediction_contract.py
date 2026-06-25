from __future__ import annotations

from fastapi.testclient import TestClient
from services.api.app import main as api_main


class FakePredictionModel:
    feature_names = ("rooms", "total_area_m2")
    feature_version = "ml_features_v1"
    metrics = {"mae": 123.4, "naive_mae": 567.8}
    model_version = "fake_baseline_v1"
    selected_candidate = "random_forest"
    feature_importance = [
        {"feature": "total_area_m2", "importance": 0.8, "coefficient": 100_000.0},
        {"feature": "rooms", "importance": 0.2, "coefficient": 250_000.0},
    ]

    def predict(self, features: dict[str, float]) -> float:
        return 10_000_000 + features["total_area_m2"] * 100_000 + features["rooms"] * 250_000

    def candidate_model(self, candidate_name: str) -> FakePredictionModel:
        if candidate_name != "ridge":
            raise KeyError(candidate_name)
        model = FakePredictionModel()
        model.model_version = "fake_ridge_v1"
        model.selected_candidate = "ridge"
        model.metrics = {"mae": 321.0, "r2": 0.5}
        model.feature_importance = [
            {"feature": "rooms", "importance": 0.9, "coefficient": 42.0},
        ]
        return model

    def available_candidate_names(self) -> list[str]:
        return ["ridge"]


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
        "selected_candidate": "random_forest",
        "feature_importance": [
            {"feature": "total_area_m2", "importance": 0.8, "coefficient": 100_000.0},
            {"feature": "rooms", "importance": 0.2, "coefficient": 250_000.0},
        ],
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


def test_predict_endpoint_can_use_requested_candidate_model() -> None:
    client = _client_with_fake_prediction_model()
    try:
        response = client.post(
            "/predict",
            json={
                "features": {"rooms": 2, "total_area_m2": 60.5},
                "model_candidate": "ridge",
            },
        )
    finally:
        api_main.app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["model_version"] == "fake_ridge_v1"
    assert payload["selected_candidate"] == "ridge"
    assert payload["metrics_summary"] == {"mae": 321.0, "r2": 0.5}
    assert payload["feature_importance"] == [
        {"feature": "rooms", "importance": 0.9, "coefficient": 42.0}
    ]
    assert payload["predicted_price_rub"] == 16_550_000.0


def test_predict_endpoint_rejects_unknown_candidate_model() -> None:
    client = _client_with_fake_prediction_model()
    try:
        response = client.post(
            "/predict",
            json={
                "features": {"rooms": 2, "total_area_m2": 60.5},
                "model_candidate": "catboost",
            },
        )
    finally:
        api_main.app.dependency_overrides.clear()

    assert response.status_code == 422
    assert response.json()["detail"] == {
        "model_candidate": "catboost",
        "available_candidates": ["ridge"],
    }


def test_predict_endpoint_allows_browser_preflight_from_streamlit_origin() -> None:
    client = _client_with_fake_prediction_model()
    try:
        response = client.options(
            "/predict",
            headers={
                "Origin": "http://127.0.0.1:8502",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type",
            },
        )
    finally:
        api_main.app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "*"
    assert "POST" in response.headers["access-control-allow-methods"]
    assert "content-type" in response.headers["access-control-allow-headers"].lower()


def _client_with_fake_prediction_model() -> TestClient:
    def override_model() -> FakePredictionModel:
        return FakePredictionModel()

    api_main.app.dependency_overrides[api_main.get_prediction_model] = override_model
    return TestClient(api_main.app)
