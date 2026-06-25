from typing import Any

from services.streamlit import api_client
from services.streamlit.api_client import fetch_dashboard_data, request_prediction

EMPTY_TREND = {
    "status": "missing",
    "can_forecast": False,
    "metric": "median_price_per_m2",
    "rows": [],
}
EMPTY_EXPOSURE_FORECAST = {
    "status": "missing",
    "can_forecast": False,
    "target_source": "listing_lifecycle",
    "forecast_segments": [],
}


class FakeResponse:
    def __init__(self, payload: dict[str, Any], status_code: int = 200) -> None:
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self) -> dict[str, Any]:
        return self._payload


def test_fetch_dashboard_data_reads_stats_and_data_alias_from_api() -> None:
    calls = []

    def fake_get(url: str, **kwargs: Any) -> FakeResponse:
        calls.append((url, kwargs))
        if url.endswith("/stats/data-quality"):
            return FakeResponse({"listings_total": 1, "ml_ready_listings": 1})
        if url.endswith("/stats/observation-trend"):
            return FakeResponse(EMPTY_TREND)
        if url.endswith("/stats/exposure-forecast"):
            return FakeResponse(EMPTY_EXPOSURE_FORECAST)
        if url.endswith("/data"):
            return FakeResponse({"items": [{"id": 1, "price_rub": 18_000_000}], "total": 1})
        raise AssertionError(f"Unexpected URL: {url}")

    data = fetch_dashboard_data("http://api.test/", limit=25, get=fake_get)

    assert data.errors == []
    assert data.stats == {"listings_total": 1, "ml_ready_listings": 1}
    assert data.listings == [{"id": 1, "price_rub": 18_000_000}]
    assert data.listings_total == 1
    assert calls == [
        ("http://api.test/stats/data-quality", {"timeout": 10.0}),
        ("http://api.test/stats/observation-trend", {"params": {"limit": 60}, "timeout": 10.0}),
        ("http://api.test/stats/exposure-forecast", {"timeout": 10.0}),
        ("http://api.test/data", {"params": {"limit": 25, "offset": 0}, "timeout": 10.0}),
    ]


def test_fetch_dashboard_data_passes_listing_filters_to_data_alias() -> None:
    calls = []

    def fake_get(url: str, **kwargs: Any) -> FakeResponse:
        calls.append((url, kwargs))
        if url.endswith("/stats/data-quality"):
            return FakeResponse({"listings_total": 3})
        if url.endswith("/stats/observation-trend"):
            return FakeResponse(EMPTY_TREND)
        if url.endswith("/stats/exposure-forecast"):
            return FakeResponse(EMPTY_EXPOSURE_FORECAST)
        if url.endswith("/data"):
            return FakeResponse({"items": [], "total": 0})
        raise AssertionError(f"Unexpected URL: {url}")

    data = fetch_dashboard_data(
        "http://api.test/",
        limit=25,
        filters={
            "min_price_rub": 15_000_000,
            "rooms": 2,
            "search": "api street",
            "source_name": "",
            "max_area_m2": None,
        },
        get=fake_get,
    )

    assert data.errors == []
    assert calls == [
        ("http://api.test/stats/data-quality", {"timeout": 10.0}),
        ("http://api.test/stats/observation-trend", {"params": {"limit": 60}, "timeout": 10.0}),
        ("http://api.test/stats/exposure-forecast", {"timeout": 10.0}),
        (
            "http://api.test/data",
            {
                "params": {
                    "limit": 25,
                    "offset": 0,
                    "min_price_rub": 15_000_000,
                    "rooms": 2,
                    "search": "api street",
                },
                "timeout": 10.0,
            },
        ),
    ]


def test_fetch_dashboard_data_passes_offset_to_data_alias() -> None:
    calls = []

    def fake_get(url: str, **kwargs: Any) -> FakeResponse:
        calls.append((url, kwargs))
        if url.endswith("/stats/data-quality"):
            return FakeResponse({"listings_total": 100})
        if url.endswith("/stats/observation-trend"):
            return FakeResponse(EMPTY_TREND)
        if url.endswith("/stats/exposure-forecast"):
            return FakeResponse(EMPTY_EXPOSURE_FORECAST)
        if url.endswith("/data"):
            return FakeResponse({"items": [], "total": 100})
        raise AssertionError(f"Unexpected URL: {url}")

    data = fetch_dashboard_data("http://api.test/", limit=25, offset=50, get=fake_get)

    assert data.errors == []
    assert calls == [
        ("http://api.test/stats/data-quality", {"timeout": 10.0}),
        ("http://api.test/stats/observation-trend", {"params": {"limit": 60}, "timeout": 10.0}),
        ("http://api.test/stats/exposure-forecast", {"timeout": 10.0}),
        ("http://api.test/data", {"params": {"limit": 25, "offset": 50}, "timeout": 10.0}),
    ]


def test_fetch_dashboard_data_can_fetch_full_analytics_pages_from_api() -> None:
    calls = []
    pages = {
        0: [{"id": 1, "address_text": "Россия, Москва, район Раменки, улица 1"}],
        2: [{"id": 2, "address_text": "Россия, Москва, Можайский район, улица 2"}],
        4: [{"id": 3, "address_text": "Москва, Тверская улица, 3"}],
    }

    def fake_get(url: str, **kwargs: Any) -> FakeResponse:
        calls.append((url, kwargs))
        if url.endswith("/stats/data-quality"):
            return FakeResponse({"listings_total": 5})
        if url.endswith("/stats/observation-trend"):
            return FakeResponse(EMPTY_TREND)
        if url.endswith("/stats/exposure-forecast"):
            return FakeResponse(EMPTY_EXPOSURE_FORECAST)
        if url.endswith("/data"):
            params = kwargs.get("params", {})
            offset = int(params.get("offset", 0))
            return FakeResponse({"items": pages[offset], "total": 5})
        raise AssertionError(f"Unexpected URL: {url}")

    data = fetch_dashboard_data(
        "http://api.test/",
        limit=1,
        analytics_limit=2,
        analytics_max_listings=5,
        get=fake_get,
    )

    assert data.errors == []
    assert data.listings == pages[0]
    assert data.analytics_listings == [*pages[0], *pages[2], *pages[4]]
    assert calls == [
        ("http://api.test/stats/data-quality", {"timeout": 10.0}),
        ("http://api.test/stats/observation-trend", {"params": {"limit": 60}, "timeout": 10.0}),
        ("http://api.test/stats/exposure-forecast", {"timeout": 10.0}),
        ("http://api.test/data", {"params": {"limit": 1, "offset": 0}, "timeout": 10.0}),
        ("http://api.test/data", {"params": {"limit": 2, "offset": 0}, "timeout": 10.0}),
        ("http://api.test/data", {"params": {"limit": 2, "offset": 2}, "timeout": 10.0}),
        ("http://api.test/data", {"params": {"limit": 2, "offset": 4}, "timeout": 10.0}),
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


def test_fetch_dashboard_data_reads_observation_trend_from_api() -> None:
    calls = []
    trend_payload = {
        "status": "partial",
        "can_forecast": False,
        "metric": "median_price_per_m2",
        "rows": [
            {
                "observed_date": "2026-06-23",
                "observation_count": 2000,
                "listing_count": 1987,
                "median_price_rub": 24_000_000,
                "median_price_per_m2": 420_000.0,
            }
        ],
    }

    def fake_get(url: str, **kwargs: Any) -> FakeResponse:
        calls.append((url, kwargs))
        if url.endswith("/stats/data-quality"):
            return FakeResponse({"listings_total": 1})
        if url.endswith("/stats/observation-trend"):
            return FakeResponse(trend_payload)
        if url.endswith("/stats/exposure-forecast"):
            return FakeResponse(EMPTY_EXPOSURE_FORECAST)
        if url.endswith("/data"):
            return FakeResponse({"items": [], "total": 0})
        raise AssertionError(f"Unexpected URL: {url}")

    data = fetch_dashboard_data("http://api.test/", get=fake_get)

    assert data.errors == []
    assert data.observation_trend == trend_payload
    assert calls == [
        ("http://api.test/stats/data-quality", {"timeout": 10.0}),
        ("http://api.test/stats/observation-trend", {"params": {"limit": 60}, "timeout": 10.0}),
        ("http://api.test/stats/exposure-forecast", {"timeout": 10.0}),
        ("http://api.test/data", {"params": {"limit": 1000, "offset": 0}, "timeout": 10.0}),
    ]


def test_fetch_dashboard_data_reads_exposure_forecast_from_api() -> None:
    calls = []
    forecast_payload = {
        "status": "partial",
        "can_forecast": False,
        "target_source": "observed_history_lower_bound",
        "observed_exposure_can_forecast": True,
        "observed_exposure_target_rows": 7_456,
        "median_observed_exposure_days": 7,
        "forecast_segments": [
            {
                "rooms": 2,
                "target_rows": 2_440,
                "median_observed_exposure_days": 6,
                "target_source": "observed_history_lower_bound",
            }
        ],
    }

    def fake_get(url: str, **kwargs: Any) -> FakeResponse:
        calls.append((url, kwargs))
        if url.endswith("/stats/data-quality"):
            return FakeResponse({"listings_total": 1})
        if url.endswith("/stats/observation-trend"):
            return FakeResponse(EMPTY_TREND)
        if url.endswith("/stats/exposure-forecast"):
            return FakeResponse(forecast_payload)
        if url.endswith("/data"):
            return FakeResponse({"items": [], "total": 0})
        raise AssertionError(f"Unexpected URL: {url}")

    data = fetch_dashboard_data("http://api.test/", get=fake_get)

    assert data.errors == []
    assert data.exposure_forecast == forecast_payload
    assert calls == [
        ("http://api.test/stats/data-quality", {"timeout": 10.0}),
        ("http://api.test/stats/observation-trend", {"params": {"limit": 60}, "timeout": 10.0}),
        ("http://api.test/stats/exposure-forecast", {"timeout": 10.0}),
        ("http://api.test/data", {"params": {"limit": 1000, "offset": 0}, "timeout": 10.0}),
    ]


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
    assert data.observation_trend == {
        "status": "missing",
        "can_forecast": False,
        "metric": "median_price_per_m2",
        "rows": [],
        "error": "API unavailable",
    }


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
    assert data.observation_trend == {
        "status": "missing",
        "can_forecast": False,
        "metric": "median_price_per_m2",
        "rows": [],
        "error": "Expected JSON object from RealtyScope API",
    }


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


def test_request_prediction_posts_requested_candidate_to_api() -> None:
    calls = []
    payload = {
        "predicted_price_rub": 15_250_000.0,
        "model_version": "selected_price_model_v1_non_leaky",
        "feature_version": "ml_features_v2_non_leaky",
        "metrics_summary": {"mae": 48_610.18},
        "input_features_echo": {"rooms": 2.0, "total_area_m2": 60.5},
        "feature_names": ["rooms", "total_area_m2"],
        "selected_candidate": "ridge",
        "caveat": "Candidate comparison result.",
    }

    def fake_post(url: str, **kwargs: Any) -> FakeResponse:
        calls.append((url, kwargs))
        return FakeResponse(payload)

    prediction = request_prediction(
        "http://api.test/",
        features={"rooms": 2.0, "total_area_m2": 60.5},
        model_candidate="ridge",
        post=fake_post,
    )

    assert prediction.errors == []
    assert prediction.result == payload
    assert calls == [
        (
            "http://api.test/predict",
            {
                "json": {
                    "features": {"rooms": 2.0, "total_area_m2": 60.5},
                    "model_candidate": "ridge",
                },
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


def test_fetch_monitoring_data_reads_status_and_model_metadata_from_api() -> None:
    calls = []
    monitoring_payload = {
        "status": "ok",
        "data_quality": {"listings_total": 1},
        "recent_errors": [],
    }
    model_payload = {
        "status": "ready",
        "model_version": "baseline_ridge_v2_non_leaky",
        "feature_version": "ml_features_v2_non_leaky",
        "feature_names": ["rooms", "total_area_m2"],
        "feature_importance": [{"feature": "total_area_m2", "importance": 0.8, "coefficient": 0.8}],
    }

    def fake_get(url: str, **kwargs: Any) -> FakeResponse:
        calls.append((url, kwargs))
        if url.endswith("/monitoring/status"):
            return FakeResponse(monitoring_payload)
        if url.endswith("/model/metadata"):
            return FakeResponse(model_payload)
        raise AssertionError(f"Unexpected URL: {url}")

    data = api_client.fetch_monitoring_data("http://api.test/", get=fake_get)

    assert data.errors == []
    assert data.status == monitoring_payload
    assert data.model_metadata == model_payload
    assert calls == [
        ("http://api.test/monitoring/status", {"timeout": 10.0}),
        ("http://api.test/model/metadata", {"timeout": 10.0}),
    ]


def test_fetch_monitoring_data_reports_errors_without_mocking_payloads() -> None:
    def fake_get(_url: str, **_kwargs: Any) -> FakeResponse:
        raise RuntimeError("API unavailable")

    data = api_client.fetch_monitoring_data("http://api.test", get=fake_get)

    assert data.status is None
    assert data.model_metadata is None
    assert data.errors == [
        "Could not load monitoring status: API unavailable",
        "Could not load model metadata: API unavailable",
    ]
