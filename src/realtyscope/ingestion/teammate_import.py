from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path

from pydantic import ValidationError

from realtyscope.ingestion.contracts import (
    IngestionBatch,
    NormalizedListing,
    RawListing,
    RejectedListing,
    stable_listing_id,
)


def import_teammate_csv(path: Path) -> IngestionBatch:
    raw_listings: list[RawListing] = []
    normalized_listings: list[NormalizedListing] = []
    rejected_listings: list[RejectedListing] = []

    with path.open("r", encoding="utf-8-sig", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        for row_number, row in enumerate(reader, start=2):
            raw_payload = dict(row)
            try:
                normalized = _row_to_normalized(row)
                raw = RawListing(
                    source_name=normalized.source_name,
                    source_listing_id=normalized.source_listing_id,
                    source_url=normalized.source_url,
                    observed_at=normalized.observed_at,
                    raw_payload=raw_payload,
                )
            except (ValueError, ValidationError) as exc:
                rejected_listings.append(
                    RejectedListing(
                        source_name=row.get("source_name") or "unknown",
                        row_number=row_number,
                        reason=str(exc),
                        raw_payload=raw_payload,
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


def _row_to_normalized(row: dict[str, str | None]) -> NormalizedListing:
    source_name = _required_text(row, "source_name")
    observed_at = datetime.fromisoformat(_required_text(row, "observed_at"))
    source_listing_id = _optional_text(row, "source_listing_id")
    source_url = _optional_text(row, "source_url")
    address_text = _optional_text(row, "address_text")
    price_rub = _required_int(row, "price_rub")
    total_area_m2 = _required_float(row, "total_area_m2")
    rooms = _required_int(row, "rooms")

    if source_listing_id is None:
        source_listing_id = stable_listing_id(
            source_name=source_name,
            source_url=source_url,
            address_text=address_text,
            price_rub=price_rub,
            total_area_m2=total_area_m2,
            rooms=rooms,
        )

    return NormalizedListing(
        source_name=source_name,
        source_listing_id=source_listing_id,
        source_url=source_url,
        observed_at=observed_at,
        city=_required_text(row, "city"),
        address_text=address_text,
        latitude=_optional_float(row, "latitude"),
        longitude=_optional_float(row, "longitude"),
        price_rub=price_rub,
        total_area_m2=total_area_m2,
        rooms=rooms,
        floor=_optional_int(row, "floor"),
        floors_total=_optional_int(row, "floors_total"),
        building_year=_optional_int(row, "building_year"),
        property_type=_required_text(row, "property_type"),
        description=_optional_text(row, "description"),
    )


def _required_text(row: dict[str, str | None], field: str) -> str:
    value = _optional_text(row, field)
    if value is None:
        raise ValueError(f"{field} is required")
    return value


def _optional_text(row: dict[str, str | None], field: str) -> str | None:
    value = row.get(field)
    if value is None:
        return None
    value = value.strip()
    return value or None


def _required_int(row: dict[str, str | None], field: str) -> int:
    value = _optional_int(row, field)
    if value is None:
        raise ValueError(f"{field} is required")
    return value


def _optional_int(row: dict[str, str | None], field: str) -> int | None:
    value = _optional_text(row, field)
    if value is None:
        return None
    return int(float(value))


def _required_float(row: dict[str, str | None], field: str) -> float:
    value = _optional_float(row, field)
    if value is None:
        raise ValueError(f"{field} is required")
    return value


def _optional_float(row: dict[str, str | None], field: str) -> float | None:
    value = _optional_text(row, field)
    if value is None:
        return None
    return float(value)
