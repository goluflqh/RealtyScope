from pathlib import Path


def test_alembic_env_imports_model_metadata() -> None:
    env_py = Path("alembic/env.py").read_text(encoding="utf-8")

    assert "from realtyscope.database.base import Base" in env_py
    assert "target_metadata = Base.metadata" in env_py
    assert "get_settings().database_url" in env_py


def test_initial_migration_creates_phase3_core_tables() -> None:
    migration = Path("alembic/versions/20260531_0001_initial_database_foundation.py")
    content = migration.read_text(encoding="utf-8")

    for table_name in (
        "sources",
        "ingestion_runs",
        "raw_listings",
        "listings",
        "listing_source_links",
        "rejected_listings",
        "app_logs",
    ):
        assert f'"{table_name}"' in content
    assert "uq_raw_listings_source_payload_hash" in content
    assert "uq_listing_source_links_source_listing" in content
