from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from realtyscope.ingestion.contracts import NormalizedListing, RawListing, stable_listing_id


def test_raw_listing_keeps_source_payload_and_hash() -> None:
    listing = RawListing(
        source_name="domclick",
        source_listing_id="42",
        source_url="https://example.test/listing/42",
        observed_at=datetime(2026, 5, 31, tzinfo=UTC),
        raw_payload={"price": 12_000_000, "rooms": 2},
    )

    assert listing.payload_hash == (
        "238678a1681edb14f496b4d30cb2e4643e2dfafaa4098dcad4db954dd38bc2aa"
    )
    assert listing.raw_payload["price"] == 12_000_000


def test_normalized_listing_requires_ml_core_fields() -> None:
    listing = NormalizedListing(
        source_name="domclick",
        source_listing_id="42",
        observed_at=datetime(2026, 5, 31, tzinfo=UTC),
        city="Moscow",
        price_rub=12_000_000,
        total_area_m2=48.5,
        rooms=2,
        property_type="apartment",
    )

    assert listing.city == "Moscow"
    assert listing.has_coordinates is False
    assert listing.price_per_m2 == pytest.approx(247422.6804)


def test_normalized_listing_rejects_non_positive_price() -> None:
    with pytest.raises(ValidationError):
        NormalizedListing(
            source_name="domclick",
            source_listing_id="bad",
            observed_at=datetime(2026, 5, 31, tzinfo=UTC),
            city="Moscow",
            price_rub=0,
            total_area_m2=48.5,
            rooms=2,
            property_type="apartment",
        )


def test_stable_listing_id_is_deterministic() -> None:
    first = stable_listing_id(
        source_name="teammate_file",
        source_url="https://example.test/a",
        address_text="Moscow, Test street, 1",
        price_rub=10_000_000,
        total_area_m2=40,
        rooms=1,
    )
    second = stable_listing_id(
        source_name="teammate_file",
        source_url="https://example.test/a",
        address_text="Moscow, Test street, 1",
        price_rub=10_000_000,
        total_area_m2=40,
        rooms=1,
    )

    assert first == second
    assert first.startswith("generated_")
