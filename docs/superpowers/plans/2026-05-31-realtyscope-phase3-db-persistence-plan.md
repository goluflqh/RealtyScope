# RealtyScope Phase 3 Database Persistence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Phase 3 database foundation for RealtyScope: SQLAlchemy 2.0 models, Alembic initial migration, tested persistence from Phase 2 `IngestionBatch` objects, and auditable cleaning/ML-readiness flags.

**Architecture:** Keep the database layer inside the shared `realtyscope` package under `src/realtyscope/database`. Alembic owns schema creation for real databases; focused unit tests may create metadata in temporary SQLite only to test pure ORM and persistence behavior quickly. Persistence stores raw snapshots, canonical listings, source links, rejected rows, ingestion run accounting, and structured app logs without adding production API, Streamlit, Redis, MLflow, model training, or live OSM behavior.

**Tech Stack:** Python 3.11, SQLAlchemy 2.0 typed declarative ORM, Alembic, PostgreSQL/psycopg for real migrations, SQLite for fast unit tests, Pydantic v2 ingestion contracts, pytest, ruff.

---

## Vietnamese Companion

A full Vietnamese version with proper accents and explanations for technical terms lives at:

```text
docs/superpowers/plans/2026-05-31-realtyscope-phase3-db-persistence-plan.vi.md
```

Short Vietnamese summary: Phase 3 xây nền tảng cơ sở dữ liệu đúng phạm vi, gồm SQLAlchemy 2.0 models, Alembic initial migration, persistence từ Phase 2 `IngestionBatch` vào database, audit trail cho rejected rows/logs, và các cờ cleaning cơ bản để biết row nào đủ điều kiện cho machine learning. Phase này chưa làm model training, MLflow tracking, FastAPI data/predict endpoints, Streamlit dashboard, Redis cache thật, hoặc OpenStreetMap enrichment live.

## Scope Check

Inputs reviewed before this plan:

- Latest mem0 checkpoint: course-guidance docs were consolidated, CI for commit `5a9b553` passed, next step is Phase 3 plan before coding.
- `docs/course-guidance/realtyscope-course-review.md`
- `docs/course-guidance/realtyscope-course-review.vi.md`
- `docs/superpowers/specs/2026-05-31-realtyscope-design.md`
- `docs/superpowers/plans/2026-05-31-realtyscope-phase2-ingestion-plan.md`
- Current README, `pyproject.toml`, `docker-compose.yml`, config, ingestion contracts/parsers/pipeline, and tests.

Phase 2 result evidence exists through commits, README status, ingestion source files, and tests; there is no separate Phase 2 result document in the repo.

Phase 3 includes:

- SQLAlchemy database package with settings-aware engine/session helpers.
- Core ORM tables: `sources`, `ingestion_runs`, `raw_listings`, `listings`, `listing_source_links`, `rejected_listings`, `app_logs`.
- Alembic root setup and one reviewed initial migration.
- Persistence function for Phase 2 `IngestionBatch` with idempotent raw snapshot handling and run accounting.
- Cleaning and ML-readiness flags on canonical listings.
- Tests for settings, model metadata, persistence, duplicates, rejected rows, and migration smoke behavior.
- README status update that honestly says Phase 3 database foundation has started.
- Sample ingestion command/fixture and an EDA notebook skeleton for persisted database tables.

Phase 3 does not include:

- Full OSM enrichment or bulk geocoding.
- EDA conclusions or completed notebooks.
- ML training, MLflow experiment tracking, model registry behavior.
- FastAPI `/data`, `/predict`, or monitoring endpoints.
- Streamlit multipage dashboard.
- Redis production caching.

## Repo Root

All paths are relative to:

```text
E:\Магистр\2-курс\python\RealtyScope
```

## File Structure for Phase 3

Create or modify only these files unless verification exposes a narrow tooling issue:

```text
alembic.ini
alembic/env.py
alembic/script.py.mako
alembic/versions/20260531_0001_initial_database_foundation.py
docs/superpowers/plans/2026-05-31-realtyscope-phase3-db-persistence-plan.md
docs/superpowers/plans/2026-05-31-realtyscope-phase3-db-persistence-plan.vi.md
README.md
src/realtyscope/config.py
src/realtyscope/database/__init__.py
src/realtyscope/database/base.py
src/realtyscope/database/models.py
src/realtyscope/database/session.py
src/realtyscope/database/persistence.py
tests/test_config.py
tests/test_database_models.py
tests/test_database_persistence.py
tests/test_alembic_config.py
src/realtyscope/database/sample_ingestion.py
tests/test_sample_ingestion.py
notebooks/phase3_eda_skeleton.ipynb
tests/test_phase3_eda_notebook.py
```

Do not change parser/importer behavior from Phase 2 unless a failing Phase 3 persistence test proves an integration mismatch.

---

### Task 1: Database URL Override and Session Helpers

**Files:**
- Modify: `src/realtyscope/config.py`
- Create: `src/realtyscope/database/__init__.py`
- Create: `src/realtyscope/database/base.py`
- Create: `src/realtyscope/database/session.py`
- Modify: `tests/test_config.py`
- Create: `tests/test_database_models.py`

- [ ] **Step 1: Write failing settings tests**

Append these tests to `tests/test_config.py`:

```python
def test_database_url_can_be_overridden_by_environment_alias() -> None:
    settings = Settings(DATABASE_URL="sqlite+pysqlite:///:memory:")

    assert settings.database_url == "sqlite+pysqlite:///:memory:"


def test_database_url_override_does_not_change_default() -> None:
    settings = Settings()

    assert settings.database_url == (
        "postgresql+psycopg://realtyscope:realtyscope@localhost:5432/realtyscope"
    )
```

- [ ] **Step 2: Verify red**

Run:

```powershell
python -m pytest tests/test_config.py -q
```

Expected: the first new test fails because `DATABASE_URL` is ignored by `Settings`.

- [ ] **Step 3: Implement database URL override**

Modify `Settings` in `src/realtyscope/config.py`:

```python
database_url_override: str | None = Field(default=None, alias="DATABASE_URL")

@property
def database_url(self) -> str:
    if self.database_url_override:
        return self.database_url_override
    return (
        "postgresql+psycopg://"
        f"{self.postgres_user}:{self.postgres_password}"
        f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
    )
```

- [ ] **Step 4: Verify green**

Run:

```powershell
python -m pytest tests/test_config.py -q
```

Expected: all config tests pass.

- [ ] **Step 5: Write failing database helper tests**

Create `tests/test_database_models.py` with the first helper tests:

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from realtyscope.database.base import Base
from realtyscope.database.models import Source
from realtyscope.database.session import create_session_factory


def test_database_base_metadata_contains_core_tables() -> None:
    expected_tables = {
        "sources",
        "ingestion_runs",
        "raw_listings",
        "listings",
        "listing_source_links",
        "rejected_listings",
        "app_logs",
    }

    assert expected_tables.issubset(Base.metadata.tables)


def test_session_factory_creates_sqlalchemy_session() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    factory = create_session_factory(engine)

    with factory() as session:
        assert isinstance(session, Session)
```

- [ ] **Step 6: Verify red**

Run:

```powershell
python -m pytest tests/test_database_models.py -q
```

Expected: fail because `realtyscope.database` does not exist.

- [ ] **Step 7: Implement base and session helpers**

Create `src/realtyscope/database/base.py`:

```python
from __future__ import annotations

from typing import Any

from sqlalchemy import JSON, MetaData
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase

json_type = JSON().with_variant(JSONB(), "postgresql")


class Base(DeclarativeBase):
    metadata = MetaData(
        naming_convention={
            "ix": "ix_%(column_0_label)s",
            "uq": "uq_%(table_name)s_%(column_0_name)s",
            "ck": "ck_%(table_name)s_%(constraint_name)s",
            "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
            "pk": "pk_%(table_name)s",
        }
    )
    type_annotation_map = {dict[str, Any]: json_type}
```

Create `src/realtyscope/database/session.py`:

```python
from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from realtyscope.config import get_settings


def create_database_engine(database_url: str | None = None) -> Engine:
    url = database_url or get_settings().database_url
    return create_engine(url, pool_pre_ping=True)


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


@contextmanager
def session_scope(factory: sessionmaker[Session]) -> Iterator[Session]:
    with factory() as session:
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
```

Create `src/realtyscope/database/__init__.py`:

```python
"""Database models, sessions, migrations, and persistence helpers for RealtyScope."""
```

- [ ] **Step 8: Verify current expected failure**

Run:

```powershell
python -m pytest tests/test_database_models.py -q
```

Expected: `test_session_factory_creates_sqlalchemy_session` passes, metadata table test still fails until Task 2 adds models.

---

### Task 2: SQLAlchemy ORM Models

**Files:**
- Create: `src/realtyscope/database/models.py`
- Modify: `tests/test_database_models.py`

- [ ] **Step 1: Add failing model behavior tests**

Append these imports and tests to `tests/test_database_models.py`:

```python
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from realtyscope.database.models import Listing, ListingSourceLink, RawListingRecord


def test_source_name_is_unique() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        session.add_all(
            [
                Source(name="domclick", source_type="listing"),
                Source(name="domclick", source_type="listing"),
            ]
        )
        try:
            session.commit()
        except IntegrityError:
            session.rollback()
            return

    raise AssertionError("duplicate source names must violate a unique constraint")


def test_listing_cleaning_flags_are_explicit() -> None:
    listing = Listing(
        city="Moscow",
        price_rub=12_000_000,
        total_area_m2=48.5,
        rooms=2,
        property_type="apartment",
        has_coordinates=False,
        is_ml_ready=False,
        cleaning_status="needs_coordinates",
    )

    assert listing.has_coordinates is False
    assert listing.is_ml_ready is False
    assert listing.cleaning_status == "needs_coordinates"


def test_raw_listing_payload_hash_is_unique_per_source() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        source = Source(name="domclick", source_type="listing")
        session.add(source)
        session.flush()
        session.add_all(
            [
                RawListingRecord(
                    source_id=source.id,
                    source_listing_id="d-1",
                    observed_at=datetime(2026, 5, 31, tzinfo=UTC),
                    payload_hash="same-hash",
                    raw_payload={"id": "d-1"},
                ),
                RawListingRecord(
                    source_id=source.id,
                    source_listing_id="d-1",
                    observed_at=datetime(2026, 5, 31, tzinfo=UTC),
                    payload_hash="same-hash",
                    raw_payload={"id": "d-1"},
                ),
            ]
        )
        try:
            session.commit()
        except IntegrityError:
            session.rollback()
            return

    raise AssertionError("duplicate payload hashes per source must violate a unique constraint")


def test_model_relationships_can_insert_minimal_listing_graph() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        source = Source(name="domclick", source_type="listing")
        session.add(source)
        session.flush()
        raw = RawListingRecord(
            source_id=source.id,
            source_listing_id="d-1",
            observed_at=datetime(2026, 5, 31, tzinfo=UTC),
            payload_hash="hash-1",
            raw_payload={"id": "d-1"},
        )
        listing = Listing(
            city="Moscow",
            price_rub=12_000_000,
            total_area_m2=48.5,
            rooms=2,
            property_type="apartment",
            has_coordinates=False,
            is_ml_ready=False,
            cleaning_status="needs_coordinates",
        )
        session.add_all([raw, listing])
        session.flush()
        listing.links.append(
            ListingSourceLink(
                source_id=source.id,
                raw_listing_id=raw.id,
                source_listing_id="d-1",
                match_strategy="exact_source_listing_id",
                match_confidence=1.0,
            )
        )
        session.commit()

    with Session(engine) as session:
        loaded = session.scalars(select(Listing)).one()
        assert loaded.links[0].source_listing_id == "d-1"
```

- [ ] **Step 2: Verify red**

Run:

```powershell
python -m pytest tests/test_database_models.py -q
```

Expected: fail because models and constraints are incomplete.

- [ ] **Step 3: Implement ORM models**

Create `src/realtyscope/database/models.py` with these exact model responsibilities:

- `TimestampMixin`: `created_at`, `updated_at` timezone-aware server defaults.
- `Source`: `id`, unique `name`, `source_type`, `enabled`; relationships to runs and raw listings.
- `IngestionRun`: source FK, `started_at`, `finished_at`, `status`, `records_seen`, `raw_count`, `normalized_count`, `rejected_count`, `inserted_count`, `updated_count`, `error_summary`; index on `source_id/status`.
- `RawListingRecord`: source FK, optional run FK, source listing ID, URL, observed time, payload hash, JSON raw payload; unique `(source_id, payload_hash)`; index `(source_id, source_listing_id, observed_at)`.
- `Listing`: canonical listing facts from `NormalizedListing`, `has_coordinates`, `is_ml_ready`, `cleaning_status`, `cleaning_notes`, `active`, first/last seen timestamps; indexes for city/price, geo, and ML-ready rows.
- `ListingSourceLink`: listing FK, raw listing FK, source FK, source listing ID, match strategy/confidence; unique raw listing link and unique `(source_id, source_listing_id)`.
- `RejectedListingRecord`: source/run FK, row number, reason, JSON raw payload; index on source/run.
- `AppLog`: level, event type, message, optional source/run FK, JSON context; index on level/created time.

Use SQLAlchemy 2.0 typed declarative style from the official docs:

```python
from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from realtyscope.database.base import Base
```

For relationships, use `back_populates` where both sides are declared. Keep `from __future__ import annotations` so forward references work.

- [ ] **Step 4: Verify green**

Run:

```powershell
python -m pytest tests/test_database_models.py -q
```

Expected: all database model tests pass.

---

### Task 3: Persistence from IngestionBatch

**Files:**
- Create: `src/realtyscope/database/persistence.py`
- Create: `tests/test_database_persistence.py`

- [ ] **Step 1: Write failing persistence tests**

Create `tests/test_database_persistence.py`:

```python
from datetime import UTC, datetime

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from realtyscope.database.base import Base
from realtyscope.database.models import IngestionRun, Listing, RawListingRecord, RejectedListingRecord, Source
from realtyscope.database.persistence import persist_ingestion_batch
from realtyscope.ingestion.contracts import IngestionBatch, NormalizedListing, RawListing, RejectedListing


def _session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def _batch() -> IngestionBatch:
    observed_at = datetime(2026, 5, 31, 10, 0, tzinfo=UTC)
    return IngestionBatch(
        raw_listings=(
            RawListing(
                source_name="domclick",
                source_listing_id="d-1",
                source_url="https://example.test/1",
                observed_at=observed_at,
                raw_payload={"id": "d-1", "price": 12_000_000},
            ),
        ),
        normalized_listings=(
            NormalizedListing(
                source_name="domclick",
                source_listing_id="d-1",
                source_url="https://example.test/1",
                observed_at=observed_at,
                city="Moscow",
                address_text="Moscow, Test street, 1",
                latitude=55.75,
                longitude=37.62,
                price_rub=12_000_000,
                total_area_m2=48.5,
                rooms=2,
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


def test_persist_ingestion_batch_creates_run_raw_listing_link_and_rejection() -> None:
    with _session() as session:
        result = persist_ingestion_batch(session, _batch(), source_name="domclick")
        session.commit()

        assert result.records_seen == 2
        assert result.raw_inserted == 1
        assert result.listings_created == 1
        assert result.rejected_inserted == 1
        assert session.scalar(select(Source).where(Source.name == "domclick")) is not None
        assert session.scalar(select(IngestionRun)).status == "success"
        assert session.scalar(select(RawListingRecord)).payload_hash
        listing = session.scalar(select(Listing))
        assert listing is not None
        assert listing.has_coordinates is True
        assert listing.is_ml_ready is True
        assert listing.cleaning_status == "ml_ready"
        assert session.scalar(select(RejectedListingRecord)).reason == "price_rub is required"


def test_persist_ingestion_batch_is_idempotent_for_same_raw_payload() -> None:
    with _session() as session:
        first = persist_ingestion_batch(session, _batch(), source_name="domclick")
        second = persist_ingestion_batch(session, _batch(), source_name="domclick")
        session.commit()

        assert first.raw_inserted == 1
        assert second.raw_inserted == 0
        assert second.raw_reused == 1
        assert len(session.scalars(select(RawListingRecord)).all()) == 1
        assert len(session.scalars(select(Listing)).all()) == 1


def test_persist_ingestion_batch_marks_missing_coordinates_not_ml_ready() -> None:
    observed_at = datetime(2026, 5, 31, 10, 0, tzinfo=UTC)
    batch = IngestionBatch(
        raw_listings=(
            RawListing(
                source_name="teammate_file",
                source_listing_id="t-1",
                observed_at=observed_at,
                raw_payload={"id": "t-1"},
            ),
        ),
        normalized_listings=(
            NormalizedListing(
                source_name="teammate_file",
                source_listing_id="t-1",
                observed_at=observed_at,
                city="Moscow",
                price_rub=9_000_000,
                total_area_m2=40,
                rooms=1,
                property_type="apartment",
            ),
        ),
    )

    with _session() as session:
        persist_ingestion_batch(session, batch, source_name="teammate_file")
        session.commit()
        listing = session.scalar(select(Listing))

    assert listing is not None
    assert listing.has_coordinates is False
    assert listing.is_ml_ready is False
    assert listing.cleaning_status == "needs_coordinates"
```

- [ ] **Step 2: Verify red**

Run:

```powershell
python -m pytest tests/test_database_persistence.py -q
```

Expected: fail because `realtyscope.database.persistence` does not exist.

- [ ] **Step 3: Implement persistence**

Create `src/realtyscope/database/persistence.py` with:

- `PersistedIngestionResult` frozen Pydantic model with `ingestion_run_id`, `records_seen`, `raw_inserted`, `raw_reused`, `listings_created`, `listings_updated`, `rejected_inserted`.
- `persist_ingestion_batch(session, batch, *, source_name, source_type="listing")`.
- `_get_or_create_source` selecting by unique source name.
- `_get_or_create_raw_listing` selecting by `(source_id, payload_hash)` before insert.
- `_upsert_listing_from_normalized` selecting existing `ListingSourceLink` by `(source_id, source_listing_id)` before creating a new canonical listing.
- `_is_ml_ready(normalized)` returning `True` only when `price_rub`, `total_area_m2`, and coordinates are present.
- Cleaning status values: `ml_ready` or `needs_coordinates`.
- One `IngestionRun` per persisted batch with accurate counts.
- One `RejectedListingRecord` per rejected row.

Minimal public signature:

```python
def persist_ingestion_batch(
    session: Session,
    batch: IngestionBatch,
    *,
    source_name: str,
    source_type: str = "listing",
) -> PersistedIngestionResult:
    ...
```

- [ ] **Step 4: Verify green**

Run:

```powershell
python -m pytest tests/test_database_persistence.py -q
```

Expected: all persistence tests pass.

- [ ] **Step 5: Run model and persistence tests together**

Run:

```powershell
python -m pytest tests/test_database_models.py tests/test_database_persistence.py -q
```

Expected: all database-focused tests pass together.

---

### Task 4: Alembic Setup and Initial Migration

**Files:**
- Create: `alembic.ini`
- Create: `alembic/env.py`
- Create: `alembic/script.py.mako`
- Create: `alembic/versions/20260531_0001_initial_database_foundation.py`
- Create: `tests/test_alembic_config.py`

- [ ] **Step 1: Write failing Alembic config tests**

Create `tests/test_alembic_config.py`:

```python
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
```

- [ ] **Step 2: Verify red**

Run:

```powershell
python -m pytest tests/test_alembic_config.py -q
```

Expected: fail because Alembic files do not exist.

- [ ] **Step 3: Add Alembic files**

Create `alembic/env.py` so it:

- Imports `get_settings`, `Base`, and `realtyscope.database.models`.
- Sets `target_metadata = Base.metadata`.
- Uses `get_settings().database_url` for offline and online migrations.
- Calls `context.configure(..., target_metadata=target_metadata)`.

Create `alembic.ini` with `script_location = alembic`, `prepend_sys_path = .`, logging sections, and a placeholder `sqlalchemy.url` that is overridden in `env.py`.

Create `alembic/script.py.mako` using Alembic's standard template with `upgrade()` and `downgrade()`.

- [ ] **Step 4: Generate and review initial migration**

Preferred command after the local DB is healthy:

```powershell
python -m alembic revision --autogenerate -m "initial database foundation" --rev-id 20260531_0001
```

Review the generated file manually. The migration must create exactly the Phase 3 core tables, constraints, foreign keys, and indexes from Task 2. It must not create ML, API, Redis, Streamlit, or OSM tables.

- [ ] **Step 5: Verify Alembic config tests green**

Run:

```powershell
python -m pytest tests/test_alembic_config.py -q
```

Expected: all Alembic config tests pass.

- [ ] **Step 6: Verify migration upgrade on PostgreSQL**

Start only the database service:

```powershell
docker compose up -d db
```

Run migration against the local Docker database:

```powershell
$env:DATABASE_URL="postgresql+psycopg://realtyscope:realtyscope@localhost:5432/realtyscope"
python -m alembic upgrade head
```

Expected: Alembic logs show upgrade to `20260531_0001` and exit code 0.

---

### Task 5: README Status and Dependency Check

**Files:**
- Modify: `README.md`
- Modify: `pyproject.toml` only if test execution proves SQLAlchemy/Alembic are unavailable in the default dev install.

- [ ] **Step 1: Update README status text**

Change `## Статус Phase 2` to `## Статус Phase 3` and add bullets for:

- SQLAlchemy database package foundation.
- Alembic initial migration foundation.
- DB persistence from Phase 2 ingestion batches.
- Cleaning/ML-readiness flags and rejected-row audit trail.

Keep explicit future-scope wording for OSM enrichment, EDA conclusions, ML training, Redis cache behavior, and full dashboard pages.

- [ ] **Step 2: Check whether default dev install needs data dependencies**

Run:

```powershell
python -c "import sqlalchemy, alembic, psycopg; print(sqlalchemy.__version__)"
```

Expected: command exits 0 in the current environment.

If it fails because the local dev environment was installed without `[data]`, do not move SQLAlchemy/Alembic into base dependencies automatically. Instead, update README development commands to include `--extra data` and use the repo's lock/update workflow to refresh `uv.lock` if dependency metadata changes.

---

### Task 6: Final Phase 3 Foundation Verification

**Files:**
- Modify only Phase 3 files listed above if verification exposes an issue.

- [ ] **Step 1: Run focused database tests**

Run:

```powershell
python -m pytest tests/test_config.py tests/test_database_models.py tests/test_database_persistence.py tests/test_alembic_config.py -q
```

Expected: all focused Phase 3 tests pass.

- [ ] **Step 2: Run full test suite**

Run:

```powershell
python -m pytest -q
```

Expected: all tests pass, allowing the existing FastAPI/Starlette deprecation warning already present in earlier sessions.

- [ ] **Step 3: Run ruff checks**

Run:

```powershell
python -m ruff check .
python -m ruff format --check .
```

Expected: both commands pass.

- [ ] **Step 4: Verify Alembic upgrade on fresh PostgreSQL**

Run:

```powershell
docker compose up -d db
$env:DATABASE_URL="postgresql+psycopg://realtyscope:realtyscope@localhost:5432/realtyscope"
python -m alembic upgrade head
```

Expected: migration reaches head successfully.

- [ ] **Step 5: Review Phase 3 scope**

Run:

```powershell
git diff --stat
git diff -- alembic.ini alembic src/realtyscope/config.py src/realtyscope/database tests README.md docs/superpowers/plans/2026-05-31-realtyscope-phase3-db-persistence-plan.md
```

Expected: diff is limited to Phase 3 database/Alembic/persistence/cleaning foundation files, with no production API endpoints, Streamlit pages, Redis behavior, MLflow training, model artifacts, or live OSM calls.

---

### Task 7: Sample Ingestion Fixture and EDA Skeleton

**Files:**
- Create: `src/realtyscope/database/sample_ingestion.py`
- Create: `tests/test_sample_ingestion.py`
- Create: `notebooks/phase3_eda_skeleton.ipynb`
- Create: `tests/test_phase3_eda_notebook.py`
- Modify: `README.md`

**Scope:** Add a small DB-backed sample path that proves Phase 2 `IngestionBatch` data can be persisted into the Phase 3 schema, plus an EDA notebook skeleton that reads persisted database tables. This task still does not implement production API endpoints, model training, Redis cache behavior, Streamlit dashboard pages, or live OSM enrichment.

**Verification:**

```powershell
python -m pytest tests/test_sample_ingestion.py tests/test_phase3_eda_notebook.py -q
python -m realtyscope.database.sample_ingestion --database-url <migrated-db-url> --json
```

## Plan Self-Review

- Spec coverage: covers Phase 0 DB/Alembic expectations, course-guidance Phase 3 recommendations, and Phase 2 `IngestionBatch` persistence handoff.
- Placeholder scan: no placeholder markers or intentionally vague implementation steps remain.
- Type consistency: table/model names and test imports use the same names across tasks.
- Scope check: plan is one subsystem foundation and postpones ML/API/UI/Redis/OSM live work to later phases.
