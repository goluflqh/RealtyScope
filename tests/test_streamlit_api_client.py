from typing import Any

from services.streamlit.api_client import fetch_dashboard_data, request_prediction


class FakeResponse:
    def __init__(self, payload: dict[str, Any], status_code: int = 200) -> None:
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self) -> dict[str, Any]:
        return self._payload


def test_fetch_dashboard_data_reads_stats_and_listings_from_api() -> None:
    calls = []

    def fake_get(url: str, **kwargs: Any) -> FakeResponse:
        calls.append((url, kwargs))
        if url.endswith("/stats/data-quality"):
            return FakeResponse({"listings_total": 1, "ml_ready_listings": 1})
        if url.endswith("/listings"):
            return FakeResponse({"items": [{"id": 1, "price_rub": 18_000_000}], "total": 1})
        raise AssertionError(f"Unexpected URL: {url}")

    data = fetch_dashboard_data("http://api.test/", limit=25, get=fake_get)

    assert data.errors == []
    assert data.stats == {"listings_total": 1, "ml_ready_listings": 1}
    assert data.listings == [{"id": 1, "price_rub": 18_000_000}]
    assert data.listings_total == 1
    assert calls == [
        ("http://api.test/stats/data-quality", {"timeout": 10.0}),
        ("http://api.test/listings", {"params": {"limit": 25, "offset": 0}, "timeout": 10.0}),
    ]


def test_fetch_dashboard_data_reports_api_errors_without_mocking_data() -> None:
    def fake_get(url: str, **_kwargs: Any) -> FakeResponse:
        if url.endswith("/stats/data-quality"):
            raise RuntimeError("API unavailable")
        return FakeResponse({"items": [], "total": 0})

    data = fetch_dashboard_data("http://api.test", get=fake_get)

    assert data.stats is None
    assert data.listings == []
    assert data.listings_total == 0
    assert data.errors == ["Could not load data-quality stats: API unavailable"]


def test_fetch_dashboard_data_reports_listing_errors_without_mocking_data() -> None:
    def fake_get(_url: str, **_kwargs: Any) -> FakeResponse:
        raise RuntimeError("API unavailable")

    data = fetch_dashboard_data("http://api.test", get=fake_get)

    assert data.stats is None
    assert data.listings == []
    assert data.listings_total is None
    assert data.errors == [
        "Could not load data-quality stats: API unavailable",
        "Could not load listings: API unavailable",
    ]


def test_fetch_dashboard_data_reports_non_object_json_without_mocking_data() -> None:
    def fake_get(_url: str, **_kwargs: Any) -> FakeResponse:
        response = FakeResponse({})
        response.json = lambda: []  # type: ignore[method-assign]
        return response

    data = fetch_dashboard_data("http://api.test", get=fake_get)

    assert data.stats is None
    assert data.listings == []
    assert data.listings_total is None
    assert data.errors == [
        "Could not load data-quality stats: Expected JSON object from RealtyScope API",
        "Could not load listings: Expected JSON object from RealtyScope API",
    ]


def test_request_prediction_posts_feature_contract_to_api() -> None:
    calls = []
    payload = {
        "predicted_price_rub": 16_550_000.0,
        "model_version": "baseline_ridge_v1",
        "feature_version": "ml_features_v1",
        "metrics_summary": {"mae": 48_610.18},
        "input_features_echo": {"rooms": 2.0, "total_area_m2": 60.5},
        "feature_names": ["rooms", "total_area_m2"],
        "caveat": "Phase 4 baseline contract result; not a final independent appraisal model.",
    }

    def fake_post(url: str, **kwargs: Any) -> FakeResponse:
        calls.append((url, kwargs))
        return FakeResponse(payload)

    prediction = request_prediction(
        "http://api.test/",
        features={"rooms": 2.0, "total_area_m2": 60.5},
        post=fake_post,
    )

    assert prediction.errors == []
    assert prediction.result == payload
    assert calls == [
        (
            "http://api.test/predict",
            {
                "json": {"features": {"rooms": 2.0, "total_area_m2": 60.5}},
                "timeout": 10.0,
            },
        )
    ]


def test_request_prediction_reports_api_errors() -> None:
    def fake_post(_url: str, **_kwargs: Any) -> FakeResponse:
        raise RuntimeError("API unavailable")

    prediction = request_prediction("http://api.test", features={"rooms": 2.0}, post=fake_post)

    assert prediction.result is None
    assert prediction.errors == ["Could not request prediction: API unavailable"]
