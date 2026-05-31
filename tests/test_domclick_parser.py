from datetime import UTC, datetime

from realtyscope.ingestion.domclick import DomclickCollectorConfig, parse_domclick_payload


def test_parse_domclick_payload_extracts_nested_listing_items() -> None:
    payload = {
        "result": {
            "items": [
                {
                    "id": "d-1",
                    "url": "https://domclick.ru/card/1",
                    "price": 12_500_000,
                    "area": 51.2,
                    "rooms": 2,
                    "floor": 5,
                    "floorsTotal": 18,
                    "address": "Moscow, Test street, 1",
                    "lat": 55.75,
                    "lng": 37.62,
                    "description": "Test listing",
                }
            ]
        }
    }

    batch = parse_domclick_payload(
        payload,
        source_url="https://domclick.ru/search",
        observed_at=datetime(2026, 5, 31, tzinfo=UTC),
    )

    assert batch.records_seen == 1
    assert batch.normalized_listings[0].source_name == "domclick"
    assert batch.normalized_listings[0].source_listing_id == "d-1"
    assert batch.normalized_listings[0].total_area_m2 == 51.2
    assert batch.normalized_listings[0].longitude == 37.62


def test_parse_domclick_payload_extracts_search_page_entities() -> None:
    payload = {
        "search": {
            "pages": [
                {
                    "ids": [2077280654],
                    "entities": {
                        "2077280654": {
                            "id": 2077280654,
                            "path": "https://domclick.ru/card/sale__flat__2077280654",
                            "offerType": "flat",
                            "address": {"displayName": "Москва, улица Перерва, 58"},
                            "objectInfo": {"area": 38.8, "rooms": 1, "floor": 6},
                            "house": {"floors": 17, "buildYear": 2000},
                            "location": {"lat": 55.663109, "lon": 37.761034},
                            "price": 13_400_000,
                            "description": "Real Domclick-like search result row.",
                        }
                    },
                }
            ]
        }
    }

    batch = parse_domclick_payload(
        payload,
        source_url="https://domclick.ru/search?deal_type=sale",
        observed_at=datetime(2026, 6, 1, tzinfo=UTC),
    )

    assert batch.records_seen == 1
    listing = batch.normalized_listings[0]
    assert listing.source_listing_id == "2077280654"
    assert listing.source_url == "https://domclick.ru/card/sale__flat__2077280654"
    assert listing.address_text == "Москва, улица Перерва, 58"
    assert listing.price_rub == 13_400_000
    assert listing.total_area_m2 == 38.8
    assert listing.rooms == 1
    assert listing.floor == 6
    assert listing.floors_total == 17
    assert listing.building_year == 2000
    assert listing.latitude == 55.663109
    assert listing.longitude == 37.761034


def test_parse_domclick_payload_extracts_new_building_layout_entities() -> None:
    payload = {
        "search": {
            "pages": [
                {
                    "ids": [2069068416],
                    "entities": {
                        "2069068416": {
                            "id": 2069068416,
                            "path": "https://domclick.ru/card/sale__new_flat__2069068416",
                            "offerType": "layout",
                            "address": {"displayName": "Россия, Москва, Строящийся жилой"},
                            "generalInfo": {
                                "area": 70.5,
                                "rooms": 2,
                                "minFloor": 11,
                                "floors": 32,
                            },
                            "location": {"lat": 55.89016403594024, "lon": 37.55611790309228},
                            "price": 29_588_638,
                        }
                    },
                }
            ]
        }
    }

    batch = parse_domclick_payload(
        payload,
        source_url="https://domclick.ru/search?deal_type=sale",
        observed_at=datetime(2026, 6, 1, tzinfo=UTC),
    )

    assert batch.records_seen == 1
    listing = batch.normalized_listings[0]
    assert listing.source_listing_id == "2069068416"
    assert listing.property_type == "layout"
    assert listing.total_area_m2 == 70.5
    assert listing.floor == 11
    assert listing.floors_total == 32


def test_parse_domclick_payload_extracts_search_pages_object_entities() -> None:
    payload = {
        "search": {
            "pages": {
                "0": {
                    "ids": [2077280654],
                    "entities": {
                        "2077280654": {
                            "id": 2077280654,
                            "path": "https://domclick.ru/card/sale__flat__2077280654",
                            "offerType": "flat",
                            "address": {"displayName": "Москва, улица Перерва, 58"},
                            "objectInfo": {"area": 38.8, "rooms": 1, "floor": 6},
                            "house": {"floors": 17},
                            "location": {"lat": 55.663109, "lon": 37.761034},
                            "price": 13_400_000,
                        }
                    },
                }
            }
        }
    }

    batch = parse_domclick_payload(
        payload,
        source_url="https://domclick.ru/search?deal_type=sale",
        observed_at=datetime(2026, 6, 1, tzinfo=UTC),
    )

    assert batch.records_seen == 1
    assert batch.normalized_listings[0].source_listing_id == "2077280654"


def test_parse_domclick_payload_rejects_incomplete_items() -> None:
    payload = {"items": [{"id": "bad", "price": 12_500_000}]}

    batch = parse_domclick_payload(
        payload,
        source_url="https://domclick.ru/search",
        observed_at=datetime(2026, 5, 31, tzinfo=UTC),
    )

    assert len(batch.normalized_listings) == 0
    assert len(batch.rejected_listings) == 1
    assert "total_area_m2" in batch.rejected_listings[0].reason


def test_domclick_collector_config_has_safe_defaults() -> None:
    config = DomclickCollectorConfig()

    assert config.max_records == 100
    assert config.request_delay_seconds >= 1.0
    assert "RealtyScope" in config.user_agent
