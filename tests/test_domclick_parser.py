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
