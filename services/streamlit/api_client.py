from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Protocol

import requests


class HttpResponse(Protocol):
    def raise_for_status(self) -> None: ...

    def json(self) -> Any: ...


HttpGet = Callable[..., HttpResponse]


@dataclass(frozen=True)
class DashboardData:
    stats: dict[str, Any] | None
    listings: list[dict[str, Any]]
    errors: list[str]


def fetch_dashboard_data(
    api_base_url: str,
    *,
    limit: int = 25,
    get: HttpGet = requests.get,
    timeout: float = 10.0,
) -> DashboardData:
    base_url = api_base_url.rstrip("/")
    errors: list[str] = []
    stats: dict[str, Any] | None = None
    listings: list[dict[str, Any]] = []

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
    except Exception as exc:  # noqa: BLE001 - UI should show upstream API errors.
        errors.append(f"Could not load listings: {exc}")

    return DashboardData(stats=stats, listings=listings, errors=errors)


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
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict):
        raise ValueError("Expected JSON object from RealtyScope API")
    return payload
