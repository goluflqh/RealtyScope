from __future__ import annotations

import joblib
from fastapi.testclient import TestClient
from services.api.app import main as api_main


class ToyArtifactModel:
    def __init__(self, bias: float) -> None:
        self.bias = bias

    def predict(self, rows: list[list[float]]) -> list[float]:
        return [self.bias + sum(row) for row in rows]


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


class NegativePredictionModel(FakePredictionModel):
    model_version = "negative_candidate_v1"
    selected_candidate = "ridge"

    def predict(self, features: dict[str, float]) -> float:
        return -1.0


class FakeModelWithNegativeCandidate(FakePredictionModel):
    def candidate_model(self, candidate_name: str) -> NegativePredictionModel:
        if candidate_name != "ridge":
            raise KeyError(candidate_name)
        return NegativePredictionModel()


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
        "target_variable": "price_rub",
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


def test_predict_endpoint_accepts_candidate_model_alias_from_ui() -> None:
    client = _client_with_fake_prediction_model()
    try:
        response = client.post(
            "/predict",
            json={
                "features": {"rooms": 2, "total_area_m2": 60.5},
                "candidate_model": "ridge",
            },
        )
    finally:
        api_main.app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["model_version"] == "fake_ridge_v1"
    assert payload["selected_candidate"] == "ridge"


def test_predict_endpoint_accepts_ui_body_with_both_candidate_fields() -> None:
    client = _client_with_fake_prediction_model()
    try:
        response = client.post(
            "/predict",
            json={
                "features": {"rooms": 2, "total_area_m2": 60.5},
                "model_candidate": "ridge",
                "candidate_model": "ridge",
            },
        )
    finally:
        api_main.app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["model_version"] == "fake_ridge_v1"
    assert payload["selected_candidate"] == "ridge"


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


def test_predict_endpoint_rejects_non_positive_candidate_prediction() -> None:
    client = _client_with_prediction_model(FakeModelWithNegativeCandidate())
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

    assert response.status_code == 422
    assert response.json()["detail"] == {
        "model_candidate": "ridge",
        "reason": "non_positive_prediction",
        "available_candidates": ["ridge"],
        "model_version": "negative_candidate_v1",
        "feature_version": "ml_features_v1",
        "metrics_summary": {"mae": 123.4, "naive_mae": 567.8},
        "feature_names": ["rooms", "total_area_m2"],
        "selected_candidate": "ridge",
        "feature_importance": [
            {"feature": "total_area_m2", "importance": 0.8, "coefficient": 100_000.0},
            {"feature": "rooms", "importance": 0.2, "coefficient": 250_000.0},
        ],
    }


def test_artifact_prediction_model_loads_candidate_from_selection_artifacts(tmp_path) -> None:
    selected_path = tmp_path / "selected_price_model_v1_non_leaky.joblib"
    ridge_path = tmp_path / "baseline_ridge_v2_non_leaky.joblib"
    feature_names = ("rooms", "total_area_m2")
    joblib.dump(
        {
            "feature_names": feature_names,
            "feature_version": "ml_features_v2_non_leaky",
            "metrics": {"mae": 10.0, "r2": 0.9},
            "model": ToyArtifactModel(1_000_000),
            "model_version": "selected_price_model_v1_non_leaky",
            "selected_candidate": "random_forest",
            "candidate_metrics": [{"candidate_name": "ridge", "mae": 20.0}],
        },
        selected_path,
    )
    joblib.dump(
        {
            "feature_names": feature_names,
            "feature_version": "ml_features_v2_non_leaky",
            "metrics": {"mae": 20.0, "r2": 0.5},
            "model": ToyArtifactModel(2_000_000),
            "model_version": "baseline_ridge_v2_non_leaky",
        },
        ridge_path,
    )
    selection = api_main.ModelArtifactSelection(
        path=selected_path,
        mode="best_metric",
        reason="test",
        candidates=(
            {
                "artifact_path": str(selected_path),
                "model_version": "selected_price_model_v1_non_leaky",
            },
            {"artifact_path": str(ridge_path), "model_version": "baseline_ridge_v2_non_leaky"},
        ),
    )

    model = api_main.ArtifactPredictionModel.from_artifact(selected_path, selection=selection)

    assert model.available_candidate_names() == ["random_forest", "ridge"]
    ridge = model.candidate_model("ridge")
    assert ridge.model_version == "baseline_ridge_v2_non_leaky"
    assert ridge.selected_candidate == "ridge"
    assert ridge.predict({"rooms": 2, "total_area_m2": 60}) == 2_000_062


def test_artifact_prediction_model_scales_price_per_m2_by_requested_area(tmp_path) -> None:
    artifact_path = tmp_path / "price_per_m2.joblib"
    joblib.dump(
        {
            "feature_names": ("rooms", "total_area_m2"),
            "feature_version": "ml_features_v2_non_leaky",
            "metrics": {"mae": 10.0, "r2": 0.9},
            "model": ToyArtifactModel(500_000),
            "model_version": "price_per_m2_v1",
            "target_variable": "price_per_m2",
        },
        artifact_path,
    )
    model = api_main.ArtifactPredictionModel.from_artifact(artifact_path)

    small = model.predict({"rooms": 2, "total_area_m2": 40})
    large = model.predict({"rooms": 2, "total_area_m2": 80})

    assert small == 500_042 * 40
    assert large == 500_082 * 80
    assert large > small


def test_artifact_prediction_model_prefers_selected_candidate_artifact_over_stale_baseline(
    tmp_path,
) -> None:
    selected_path = tmp_path / "selected_price_model_v1_non_leaky.joblib"
    stale_baseline_path = tmp_path / "baseline_ridge_v2_non_leaky.joblib"
    ridge_candidate_path = tmp_path / "selected_price_model_v1_non_leaky__ridge.joblib"
    feature_names = ("rooms", "total_area_m2")
    joblib.dump(
        {
            "feature_names": feature_names,
            "feature_version": "ml_features_v2_non_leaky",
            "metrics": {"mae": 10.0, "r2": 0.9},
            "model": ToyArtifactModel(1_000_000),
            "model_version": "selected_price_model_v1_non_leaky",
            "selected_candidate": "random_forest",
            "candidate_metrics": [{"candidate_name": "ridge", "mae": 20.0}],
        },
        selected_path,
    )
    joblib.dump(
        {
            "feature_names": feature_names,
            "feature_version": "ml_features_v2_non_leaky",
            "metrics": {"mae": 1.0, "r2": 0.99},
            "model": ToyArtifactModel(9_000_000),
            "model_version": "baseline_ridge_v2_non_leaky",
        },
        stale_baseline_path,
    )
    joblib.dump(
        {
            "feature_names": feature_names,
            "feature_version": "ml_features_v2_non_leaky",
            "metrics": {"mae": 20.0, "r2": 0.5},
            "model": ToyArtifactModel(2_000_000),
            "model_version": "selected_price_model_v1_non_leaky",
            "selected_candidate": "ridge",
        },
        ridge_candidate_path,
    )
    selection = api_main.ModelArtifactSelection(
        path=selected_path,
        mode="best_metric",
        reason="test",
        candidates=(
            {
                "artifact_path": str(selected_path),
                "model_version": "selected_price_model_v1_non_leaky",
                "selected_candidate": "random_forest",
            },
            {
                "artifact_path": str(stale_baseline_path),
                "model_version": "baseline_ridge_v2_non_leaky",
            },
            {
                "artifact_path": str(ridge_candidate_path),
                "model_version": "selected_price_model_v1_non_leaky",
                "selected_candidate": "ridge",
            },
        ),
    )

    model = api_main.ArtifactPredictionModel.from_artifact(selected_path, selection=selection)

    ridge = model.candidate_model("ridge")

    assert ridge.artifact_path == ridge_candidate_path
    assert ridge.model_version == "selected_price_model_v1_non_leaky"
    assert ridge.selected_candidate == "ridge"
    assert ridge.predict({"rooms": 2, "total_area_m2": 60}) == 2_000_062


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
    return _client_with_prediction_model(FakePredictionModel())


def _client_with_prediction_model(model: FakePredictionModel) -> TestClient:
    def override_model() -> FakePredictionModel:
        return model

    api_main.app.dependency_overrides[api_main.get_prediction_model] = override_model
    return TestClient(api_main.app)
