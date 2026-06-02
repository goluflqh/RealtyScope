from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
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


@dataclass(frozen=True)
class PredictionData:
    result: dict[str, Any] | None
    errors: list[str]


def fetch_dashboard_data(
    api_base_url: str,
    *,
    limit: int = 1000,
    get: HttpGet = requests.get,
    timeout: float = 10.0,
) -> DashboardData:
    base_url = api_base_url.rstrip("/")
    errors: list[str] = []
    stats: dict[str, Any] | None = None
    listings: list[dict[str, Any]] = []
    listings_total: int | None = None

    try:
        stats = _get_json_object(get, f"{base_url}/stats/data-quality", timeout=timeout)
    except Exception as exc:  # noqa: BLE001 - UI should show upstream API errors.
        errors.append(f"Could not load data-quality stats: {exc}")

    try:
        listings_payload = _get_json_object(
            get,
            f"{base_url}/listings",
            params={"limit": limit, "offset": 0},
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

    return DashboardData(
        stats=stats,
        listings=listings,
        listings_total=listings_total,
        errors=errors,
    )


def request_prediction(
    api_base_url: str,
    *,
    features: dict[str, float],
    post: HttpPost = requests.post,
    timeout: float = 10.0,
) -> PredictionData:
    base_url = api_base_url.rstrip("/")
    try:
        result = _post_json_object(
            post,
            f"{base_url}/predict",
            json_payload={"features": features},
            timeout=timeout,
        )
    except Exception as exc:  # noqa: BLE001 - UI should show upstream API errors.
        return PredictionData(result=None, errors=[f"Could not request prediction: {exc}"])
    return PredictionData(result=result, errors=[])


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
