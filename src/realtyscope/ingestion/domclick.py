from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from pydantic import ValidationError

from realtyscope.ingestion.contracts import (
    IngestionBatch,
    NormalizedListing,
    RawListing,
    RejectedListing,
    stable_listing_id,
)


@dataclass(frozen=True)
class DomclickCollectorConfig:
    max_records: int = 100
    request_delay_seconds: float = 1.0
    user_agent: str = "RealtyScope semester project ingestion contact: local-development"


def parse_domclick_payload(
    payload: dict[str, Any] | list[Any],
    *,
    source_url: str,
    observed_at: datetime,
    config: DomclickCollectorConfig | None = None,
) -> IngestionBatch:
    config = config or DomclickCollectorConfig()
    raw_listings: list[RawListing] = []
    normalized_listings: list[NormalizedListing] = []
    rejected_listings: list[RejectedListing] = []

    for index, item in enumerate(_iter_candidate_items(payload), start=1):
        if len(normalized_listings) >= config.max_records:
            break
        if not isinstance(item, dict):
            continue
        try:
            normalized = _item_to_normalized(item, source_url=source_url, observed_at=observed_at)
            raw = RawListing(
                source_name="domclick",
                source_listing_id=normalized.source_listing_id,
                source_url=normalized.source_url or source_url,
                observed_at=observed_at,
                raw_payload=item,
            )
        except (ValueError, ValidationError) as exc:
            rejected_listings.append(
                RejectedListing(
                    source_name="domclick",
                    row_number=index,
                    reason=str(exc),
                    raw_payload=item,
                )
            )
            continue

        raw_listings.append(raw)
        normalized_listings.append(normalized)

    return IngestionBatch(
        raw_listings=tuple(raw_listings),
        normalized_listings=tuple(normalized_listings),
        rejected_listings=tuple(rejected_listings),
    )


def _iter_candidate_items(payload: Any) -> list[Any]:
    domclick_search_items = _iter_domclick_search_items(payload)
    if domclick_search_items:
        return domclick_search_items

    if isinstance(payload, list):
        return payload
    if not isinstance(payload, dict):
        return []
    for key in ("items", "listings", "offers", "cards"):
        value = payload.get(key)
        if isinstance(value, list):
            return value
    for value in payload.values():
        nested = _iter_candidate_items(value)
        if nested:
            return nested
    return []


def _iter_domclick_search_items(payload: Any) -> list[Any]:
    if not isinstance(payload, dict):
        return []

    search = payload.get("search")
    if not isinstance(search, dict):
        return []

    pages = search.get("pages")
    if isinstance(pages, dict):
        page_values = pages.values()
    elif isinstance(pages, list):
        page_values = pages
    else:
        return []

    items: list[Any] = []
    for page in page_values:
        if not isinstance(page, dict):
            continue
        entities = page.get("entities")
        if not isinstance(entities, dict):
            continue
        ids = page.get("ids")
        if isinstance(ids, list):
            for listing_id in ids:
                item = entities.get(str(listing_id)) or entities.get(listing_id)
                if item is not None:
                    items.append(item)
        else:
            items.extend(entities.values())
    return items


def _item_to_normalized(
    item: dict[str, Any],
    *,
    source_url: str,
    observed_at: datetime,
) -> NormalizedListing:
    source_listing_id = _first_text(item, "id", "offerId", "listingId")
    item_url = _first_text(item, "url", "absoluteUrl", "path") or source_url
    address_text = _first_text(
        item,
        "address.displayName",
        "address",
        "addressText",
        "location.displayName",
        "location",
    )
    price_rub = _required_int(item, "price_rub", "price", "cost")
    total_area_m2 = _required_float(
        item,
        "total_area_m2",
        "area",
        "totalArea",
        "square",
        "objectInfo.area",
        "generalInfo.area",
    )
    rooms = _required_int(item, "rooms", "roomsCount", "objectInfo.rooms", "generalInfo.rooms")

    if source_listing_id is None:
        source_listing_id = stable_listing_id(
            source_name="domclick",
            source_url=item_url,
            address_text=address_text,
            price_rub=price_rub,
            total_area_m2=total_area_m2,
            rooms=rooms,
        )

    return NormalizedListing(
        source_name="domclick",
        source_listing_id=source_listing_id,
        source_url=item_url,
        observed_at=observed_at,
        city="Moscow",
        address_text=address_text,
        latitude=_optional_float(item, "latitude", "lat", "location.lat"),
        longitude=_optional_float(item, "longitude", "lng", "lon", "location.lon"),
        price_rub=price_rub,
        total_area_m2=total_area_m2,
        rooms=rooms,
        floor=_optional_int(item, "floor", "objectInfo.floor", "generalInfo.minFloor"),
        floors_total=_optional_int(
            item,
            "floors_total",
            "floorsTotal",
            "floorCount",
            "house.floors",
            "generalInfo.floors",
        ),
        building_year=_optional_int(
            item, "building_year", "builtYear", "buildYear", "house.buildYear"
        ),
        property_type=_first_text(item, "property_type", "propertyType", "category", "offerType")
        or "apartment",
        description=_first_text(item, "description", "desc"),
    )


def _first_text(item: dict[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = _first_value(item, key)
        if value is None:
            continue
        if isinstance(value, (dict, list)):
            continue
        value = str(value).strip()
        if value:
            return value
    return None


def _required_int(item: dict[str, Any], *keys: str) -> int:
    value = _optional_int(item, *keys)
    if value is None:
        raise ValueError(f"{keys[0]} is required")
    return value


def _optional_int(item: dict[str, Any], *keys: str) -> int | None:
    value = _first_value(item, *keys)
    if value is None:
        return None
    return int(float(value))


def _required_float(item: dict[str, Any], *keys: str) -> float:
    value = _optional_float(item, *keys)
    if value is None:
        raise ValueError(f"{keys[0]} is required")
    return value


def _optional_float(item: dict[str, Any], *keys: str) -> float | None:
    value = _first_value(item, *keys)
    if value is None:
        return None
    return float(value)


def _first_value(item: dict[str, Any], *keys: str) -> Any | None:
    for key in keys:
        value = _resolve_key_path(item, key)
        if value not in (None, ""):
            return value
    return None


def _resolve_key_path(item: dict[str, Any], key: str) -> Any | None:
    value: Any = item
    for part in key.split("."):
        if not isinstance(value, dict):
            return None
        value = value.get(part)
    return value
