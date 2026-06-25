from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Protocol

import requests


class HttpResponse(Protocol):
    def raise_for_status(self) -> None: ...

    def json(self) -> Any: ...


HttpGet = Callable[..., HttpResponse]
HttpPost = Callable[..., HttpResponse]


@dataclass(frozen=True)
class DashboardData:
    stats: dict[str, Any] | None
    listings: list[dict[str, Any]]
    listings_total: int | None
    errors: list[str]
    analytics_listings: list[dict[str, Any]] = field(default_factory=list)
    observation_trend: dict[str, Any] | None = None
    exposure_forecast: dict[str, Any] | None = None


@dataclass(frozen=True)
class PredictionData:
    result: dict[str, Any] | None
    errors: list[str]


@dataclass(frozen=True)
class MonitoringData:
    status: dict[str, Any] | None
    model_metadata: dict[str, Any] | None
    errors: list[str]


def fetch_dashboard_data(
    api_base_url: str,
    *,
    limit: int = 1000,
    offset: int = 0,
    analytics_limit: int | None = None,
    analytics_max_listings: int | None = None,
    filters: dict[str, Any] | None = None,
    get: HttpGet = requests.get,
    timeout: float = 10.0,
) -> DashboardData:
    base_url = api_base_url.rstrip("/")
    errors: list[str] = []
    stats: dict[str, Any] | None = None
    observation_trend: dict[str, Any] | None = None
    exposure_forecast: dict[str, Any] | None = None
    listings: list[dict[str, Any]] = []
    analytics_listings: list[dict[str, Any]] = []
    listings_total: int | None = None

    try:
        stats = _get_json_object(get, f"{base_url}/stats/data-quality", timeout=timeout)
    except Exception as exc:  # noqa: BLE001 - UI should show upstream API errors.
        errors.append(f"Could not load data-quality stats: {exc}")

    try:
        observation_trend = _get_json_object(
            get,
            f"{base_url}/stats/observation-trend",
            params={"limit": 60},
            timeout=timeout,
        )
    except Exception as exc:  # noqa: BLE001 - UI should show upstream API errors.
        observation_trend = {
            "status": "missing",
            "can_forecast": False,
            "metric": "median_price_per_m2",
            "rows": [],
            "error": str(exc),
        }

    try:
        exposure_forecast = _get_json_object(
            get,
            f"{base_url}/stats/exposure-forecast",
            timeout=timeout,
        )
    except Exception as exc:  # noqa: BLE001 - optional endpoint has a safe UI fallback.
        exposure_forecast = {
            "status": "missing",
            "can_forecast": False,
            "target_source": "listing_lifecycle",
            "forecast_segments": [],
            "error": str(exc),
        }

    try:
        listings_payload = _get_json_object(
            get,
            f"{base_url}/data",
            params=_listing_query_params(limit=limit, offset=offset, filters=filters),
            timeout=timeout,
        )
        items = listings_payload.get("items", [])
        if not isinstance(items, list):
            raise ValueError("Expected listings payload 'items' to be a list")
        listings = [item for item in items if isinstance(item, dict)]
        total = listings_payload.get("total")
        if isinstance(total, int):
            listings_total = total
    except Exception as exc:  # noqa: BLE001 - UI should show upstream API errors.
        errors.append(f"Could not load listings: {exc}")

    if analytics_limit is not None and analytics_max_listings is not None:
        try:
            analytics_listings = _fetch_analytics_listings(
                base_url,
                analytics_limit=analytics_limit,
                analytics_max_listings=analytics_max_listings,
                listings_total=listings_total,
                filters=filters,
                get=get,
                timeout=timeout,
            )
        except Exception as exc:  # noqa: BLE001 - UI should show upstream API errors.
            errors.append(f"Could not load analytics listings: {exc}")

    return DashboardData(
        stats=stats,
        listings=listings,
        listings_total=listings_total,
        errors=errors,
        analytics_listings=analytics_listings,
        observation_trend=observation_trend,
        exposure_forecast=exposure_forecast,
    )


def _fetch_analytics_listings(
    base_url: str,
    *,
    analytics_limit: int,
    analytics_max_listings: int,
    listings_total: int | None,
    filters: dict[str, Any] | None,
    get: HttpGet,
    timeout: float,
) -> list[dict[str, Any]]:
    page_limit = max(1, int(analytics_limit))
    max_listings = max(0, int(analytics_max_listings))
    if max_listings == 0:
        return []
    target_total = (
        min(listings_total, max_listings) if isinstance(listings_total, int) else max_listings
    )
    rows: list[dict[str, Any]] = []
    for page_offset in range(0, target_total, page_limit):
        payload = _get_json_object(
            get,
            f"{base_url}/data",
            params=_listing_query_params(
                limit=page_limit,
                offset=page_offset,
                filters=filters,
            ),
            timeout=timeout,
        )
        items = payload.get("items", [])
        if not isinstance(items, list):
            raise ValueError("Expected analytics listings payload 'items' to be a list")
        page_rows = [item for item in items if isinstance(item, dict)]
        rows.extend(page_rows)
        if not page_rows:
            break
    return rows[:target_total]


def request_prediction(
    api_base_url: str,
    *,
    features: dict[str, float],
    model_candidate: str | None = None,
    post: HttpPost = requests.post,
    timeout: float = 10.0,
) -> PredictionData:
    base_url = api_base_url.rstrip("/")
    payload: dict[str, Any] = {"features": features}
    if model_candidate:
        payload["model_candidate"] = model_candidate
    try:
        result = _post_json_object(
            post,
            f"{base_url}/predict",
            json_payload=payload,
            timeout=timeout,
        )
    except Exception as exc:  # noqa: BLE001 - UI should show upstream API errors.
        return PredictionData(result=None, errors=[f"Could not request prediction: {exc}"])
    return PredictionData(result=result, errors=[])


def fetch_monitoring_data(
    api_base_url: str,
    *,
    get: HttpGet = requests.get,
    timeout: float = 10.0,
) -> MonitoringData:
    base_url = api_base_url.rstrip("/")
    errors: list[str] = []
    status: dict[str, Any] | None = None
    model_metadata: dict[str, Any] | None = None

    try:
        status = _get_json_object(get, f"{base_url}/monitoring/status", timeout=timeout)
    except Exception as exc:  # noqa: BLE001 - UI should show upstream API errors.
        errors.append(f"Could not load monitoring status: {exc}")

    try:
        model_metadata = _get_json_object(get, f"{base_url}/model/metadata", timeout=timeout)
    except Exception as exc:  # noqa: BLE001 - UI should show upstream API errors.
        errors.append(f"Could not load model metadata: {exc}")

    return MonitoringData(status=status, model_metadata=model_metadata, errors=errors)


def _listing_query_params(
    *,
    limit: int,
    offset: int,
    filters: dict[str, Any] | None,
) -> dict[str, Any]:
    params: dict[str, Any] = {"limit": limit, "offset": offset}
    for key, value in (filters or {}).items():
        if value is None:
            continue
        if isinstance(value, str):
            value = value.strip()
            if not value:
                continue
        params[key] = value
    return params


def _get_json_object(
    get: HttpGet,
    url: str,
    *,
    timeout: float,
    params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    kwargs: dict[str, Any] = {"timeout": timeout}
    if params is not None:
        kwargs["params"] = params
    response = get(url, **kwargs)
    return _json_object_from_response(response)


def _post_json_object(
    post: HttpPost,
    url: str,
    *,
    json_payload: dict[str, Any],
    timeout: float,
) -> dict[str, Any]:
    response = post(url, json=json_payload, timeout=timeout)
    return _json_object_from_response(response)


def _json_object_from_response(response: HttpResponse) -> dict[str, Any]:
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict):
        raise ValueError("Expected JSON object from RealtyScope API")
    return payload
