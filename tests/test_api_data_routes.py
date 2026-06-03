import json
from collections.abc import Iterator
from datetime import UTC, datetime

from fastapi.testclient import TestClient
from services.api.app import main as api_main
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from realtyscope.database.base import Base
from realtyscope.database.persistence import persist_ingestion_batch
from realtyscope.ingestion.contracts import (
    IngestionBatch,
    NormalizedListing,
    RawListing,
    RejectedListing,
)


class _FakeRedisCache:
    def __init__(self, *, cached_payload: str | None = None) -> None:
        self.cached_payload = cached_payload
        self.get_calls = 0
        self.setex_calls: list[tuple[str, int, str]] = []

    def get(self, key: str) -> str | None:
        self.get_calls += 1
        return self.cached_payload

    def setex(self, key: str, ttl_seconds: int, value: str) -> None:
        self.setex_calls.append((key, ttl_seconds, value))


def _seed_session(session: Session) -> None:
    observed_at = datetime(2026, 5, 31, 12, 0, tzinfo=UTC)
    batch = IngestionBatch(
        raw_listings=(
            RawListing(
                source_name="domclick",
                source_listing_id="api-1",
                source_url="https://domclick.ru/card/sale__flat__api-1/",
                observed_at=observed_at,
                raw_payload={"id": "api-1", "price": 18_000_000},
            ),
        ),
        normalized_listings=(
            NormalizedListing(
                source_name="domclick",
                source_listing_id="api-1",
                source_url="https://domclick.ru/card/sale__flat__api-1/",
                observed_at=observed_at,
                city="Moscow",
                address_text="Москва, API улица, 1",
                latitude=55.751,
                longitude=37.618,
                price_rub=18_000_000,
                total_area_m2=60.5,
                rooms=2,
                floor=7,
                floors_total=18,
                building_year=2016,
                property_type="apartment",
            ),
        ),
        rejected_listings=(
            RejectedListing(
                source_name="domclick",
                row_number=2,
                reason="price_rub is required",
                raw_payload={"id": "bad"},
            ),
        ),
    )
    persist_ingestion_batch(session, batch, source_name="domclick")
    session.commit()


def _client_with_seeded_database(tmp_path) -> TestClient:
    database_path = tmp_path / "api_data_routes.sqlite3"
    engine = create_engine(
        f"sqlite+pysqlite:///{database_path.as_posix()}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        _seed_session(session)

    def override_session() -> Iterator[Session]:
        with Session(engine) as session:
            yield session

    api_main.app.dependency_overrides[api_main.get_database_session] = override_session
    return TestClient(api_main.app)


def test_listings_endpoint_reads_persisted_database_rows(tmp_path) -> None:
    client = _client_with_seeded_database(tmp_path)
    try:
        response = client.get("/listings", params={"limit": 10, "offset": 0})
    finally:
        api_main.app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "items": [
            {
                "id": 1,
                "city": "Moscow",
                "address_text": "Москва, API улица, 1",
                "latitude": 55.751,
                "longitude": 37.618,
                "price_rub": 18_000_000,
                "total_area_m2": 60.5,
                "rooms": 2,
                "floor": 7,
                "floors_total": 18,
                "building_year": 2016,
                "property_type": "apartment",
                "has_coordinates": True,
                "is_ml_ready": True,
                "cleaning_status": "ml_ready",
            }
        ],
        "limit": 10,
        "offset": 0,
        "total": 1,
    }


def test_data_alias_matches_listings_payload(tmp_path) -> None:
    client = _client_with_seeded_database(tmp_path)
    try:
        listings_response = client.get("/listings", params={"limit": 10, "offset": 0})
        data_response = client.get("/data", params={"limit": 10, "offset": 0})
    finally:
        api_main.app.dependency_overrides.clear()

    assert data_response.status_code == 200
    assert data_response.json() == listings_response.json()


def test_listings_endpoint_serves_redis_cache_hit_without_database_query() -> None:
    cached_payload = {
        "items": [],
        "limit": 10,
        "offset": 0,
        "total": 0,
    }
    fake_cache = _FakeRedisCache(cached_payload=json.dumps(cached_payload))

    def override_session() -> Iterator[object]:
        yield object()

    api_main.app.dependency_overrides[api_main.get_database_session] = override_session
    api_main.app.dependency_overrides[api_main.get_redis_client] = lambda: fake_cache
    client = TestClient(api_main.app)
    try:
        response = client.get("/listings", params={"limit": 10, "offset": 0})
    finally:
        api_main.app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == cached_payload
    assert fake_cache.get_calls == 1
    assert fake_cache.setex_calls == []


def test_data_endpoint_populates_redis_cache_from_database(tmp_path) -> None:
    fake_cache = _FakeRedisCache()
    client = _client_with_seeded_database(tmp_path)
    api_main.app.dependency_overrides[api_main.get_redis_client] = lambda: fake_cache
    try:
        response = client.get("/data", params={"limit": 10, "offset": 0})
    finally:
        api_main.app.dependency_overrides.clear()

    assert response.status_code == 200
    assert fake_cache.get_calls == 1
    assert len(fake_cache.setex_calls) == 1
    _, ttl_seconds, cached_json = fake_cache.setex_calls[0]
    assert ttl_seconds > 0
    assert json.loads(cached_json) == response.json()


def test_data_quality_stats_endpoint_reads_database_counts(tmp_path) -> None:
    client = _client_with_seeded_database(tmp_path)
    try:
        response = client.get("/stats/data-quality")
    finally:
        api_main.app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload == {
        "sources_total": 1,
        "ingestion_runs_total": 1,
        "raw_listings_total": 1,
        "listings_total": 1,
        "ml_ready_listings": 1,
        "rejected_listings_total": 1,
        "latest_ingestion_run": {
            "id": 1,
            "source_name": "domclick",
            "status": "success",
            "started_at": "2026-05-31T12:00:00+00:00",
            "finished_at": payload["latest_ingestion_run"]["finished_at"],
            "records_seen": 2,
            "raw_count": 1,
            "normalized_count": 1,
            "rejected_count": 1,
            "inserted_count": 4,
            "updated_count": 0,
            "error_summary": None,
        },
    }
    assert isinstance(payload["latest_ingestion_run"]["finished_at"], str)
