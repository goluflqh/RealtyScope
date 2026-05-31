from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def payload_hash(payload: Any) -> str:
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def stable_listing_id(
    *,
    source_name: str,
    source_url: str | None,
    address_text: str | None,
    price_rub: int | None,
    total_area_m2: float | None,
    rooms: int | None,
) -> str:
    basis = canonical_json(
        {
            "source_name": source_name,
            "source_url": source_url,
            "address_text": address_text,
            "price_rub": price_rub,
            "total_area_m2": total_area_m2,
            "rooms": rooms,
        }
    )
    return f"generated_{hashlib.sha256(basis.encode('utf-8')).hexdigest()[:16]}"


class RawListing(BaseModel):
    model_config = ConfigDict(frozen=True)

    source_name: str = Field(min_length=1)
    source_listing_id: str = Field(min_length=1)
    source_url: str | None = None
    observed_at: datetime
    raw_payload: dict[str, Any]

    @computed_field
    @property
    def payload_hash(self) -> str:
        return payload_hash(self.raw_payload)


class NormalizedListing(BaseModel):
    model_config = ConfigDict(frozen=True)

    source_name: str = Field(min_length=1)
    source_listing_id: str = Field(min_length=1)
    source_url: str | None = None
    observed_at: datetime
    city: str = Field(min_length=1)
    address_text: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    price_rub: int = Field(gt=0)
    total_area_m2: float = Field(gt=0)
    rooms: int = Field(ge=0)
    floor: int | None = Field(default=None, ge=0)
    floors_total: int | None = Field(default=None, ge=0)
    building_year: int | None = Field(default=None, ge=1500)
    property_type: str = Field(min_length=1)
    description: str | None = None

    @field_validator("city", "property_type")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("value must not be blank")
        return value

    @computed_field
    @property
    def has_coordinates(self) -> bool:
        return self.latitude is not None and self.longitude is not None

    @computed_field
    @property
    def price_per_m2(self) -> float:
        return self.price_rub / self.total_area_m2


class RejectedListing(BaseModel):
    model_config = ConfigDict(frozen=True)

    source_name: str
    row_number: int | None = None
    reason: str
    raw_payload: dict[str, Any]


class IngestionBatch(BaseModel):
    model_config = ConfigDict(frozen=True)

    raw_listings: tuple[RawListing, ...] = ()
    normalized_listings: tuple[NormalizedListing, ...] = ()
    rejected_listings: tuple[RejectedListing, ...] = ()

    @computed_field
    @property
    def records_seen(self) -> int:
        return len(self.normalized_listings) + len(self.rejected_listings)
