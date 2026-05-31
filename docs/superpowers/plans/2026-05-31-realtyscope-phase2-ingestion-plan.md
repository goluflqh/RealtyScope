# RealtyScope Phase 2 Ingestion Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Phase 2 ingestion foundation for RealtyScope: typed listing contracts, teammate import validation, a replaceable Domclick snapshot/parser collector, and a raw-to-normalized local data path that can be persisted to PostgreSQL in Phase 3.

**Architecture:** Phase 2 keeps ingestion logic inside the shared `realtyscope` package and persists only local JSONL artifacts for development/tests. It deliberately avoids Alembic migrations, PostgreSQL writes, OSM enrichment, ML training, API endpoints, Streamlit pages, Docker changes, and CI changes; those stay in later phases from the approved design spec.

**Tech Stack:** Python 3.11, pydantic 2, pytest, ruff, standard-library CSV/JSON/pathlib/hashlib/datetime utilities.

---

## Scope Check

This plan implements only the Phase 2 slice named in `docs/superpowers/specs/2026-05-31-realtyscope-design.md`: Domclick collector, teammate import contract, and raw/normalized data path. Phase 3 will add PostgreSQL schema, Alembic migrations, cleaning, OSM enrichment, and EDA. Phase 5 will expose monitoring in API/Streamlit.

The Phase 0 spec file still says it was awaiting final review, but Phase 1 has already been implemented, tagged, and merged into `main`. The working assumption for this Phase 2 plan is that the design spec has been accepted as the controlling requirements source.

## Repo Root

All paths are relative to:

```text
E:\Магистр\2-курс\python\RealtyScope
```

## File Structure for Phase 2

Create or modify only these implementation/test/docs files during this plan:

```text
docs/superpowers/plans/2026-05-31-realtyscope-phase2-ingestion-plan.md
src/realtyscope/ingestion/__init__.py
src/realtyscope/ingestion/contracts.py
src/realtyscope/ingestion/teammate_import.py
src/realtyscope/ingestion/domclick.py
src/realtyscope/ingestion/pipeline.py
tests/test_ingestion_contracts.py
tests/test_teammate_import.py
tests/test_domclick_parser.py
tests/test_ingestion_pipeline.py
README.md
```

No database, migration, OSM, ML, API, Streamlit, Docker, or CI files should change in Phase 2 unless a verification command proves a narrow tooling fix is required.

---

### Task 1: Add Typed Ingestion Contracts

**Files:**
- Create: `src/realtyscope/ingestion/__init__.py`
- Create: `src/realtyscope/ingestion/contracts.py`
- Create: `tests/test_ingestion_contracts.py`

- [ ] **Step 1: Write the failing tests**

Create tests for these exact behaviors:

```python
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
```

- [ ] **Step 2: Verify red**

Run: `python -m pytest tests/test_ingestion_contracts.py -q`

Expected: fail because `realtyscope.ingestion` does not exist yet.

- [ ] **Step 3: Implement contracts**

Implement:

- `canonical_json(value: Any) -> str`: deterministic compact JSON with UTF-8-safe text, sorted keys, and no whitespace.
- `payload_hash(payload: Any) -> str`: SHA-256 of `canonical_json(payload)`.
- `stable_listing_id(...) -> str`: `generated_` plus the first 16 hex characters of a SHA-256 hash over source, URL, address, price, area, and rooms.
- `RawListing`: frozen pydantic model with `source_name`, `source_listing_id`, `source_url`, `observed_at`, `raw_payload`, and computed `payload_hash`.
- `NormalizedListing`: frozen pydantic model with source metadata, city/address/coordinates, price, area, rooms, floor metadata, building year, property type, description, computed `has_coordinates`, and computed `price_per_m2`.
- `RejectedListing`: frozen pydantic model with source name, optional row number, reason, and raw payload.
- `IngestionBatch`: frozen pydantic model with raw, normalized, and rejected tuple fields plus computed `records_seen`.

- [ ] **Step 4: Verify green**

Run: `python -m pytest tests/test_ingestion_contracts.py -q`

Expected: pass.

- [ ] **Step 5: Run style check**

Run: `python -m ruff check src/realtyscope/ingestion tests/test_ingestion_contracts.py`

Expected: pass.

---

### Task 2: Add Teammate CSV Import Contract

**Files:**
- Create: `src/realtyscope/ingestion/teammate_import.py`
- Create: `tests/test_teammate_import.py`

- [ ] **Step 1: Write the failing tests**

Create tests for these exact behaviors:

```python
from pathlib import Path

from realtyscope.ingestion.teammate_import import import_teammate_csv


def test_import_teammate_csv_accepts_valid_rows(tmp_path: Path) -> None:
    csv_path = tmp_path / "teammate.csv"
    csv_path.write_text(
        "source_name,source_listing_id,source_url,observed_at,city,address_text,latitude,longitude,price_rub,total_area_m2,rooms,floor,floors_total,building_year,property_type,description\n"
        "teammate_file,t-1,https://example.test/1,2026-05-31T10:00:00+00:00,Moscow,Test address,55.75,37.62,12000000,48.5,2,4,12,2010,apartment,Sunny flat\n",
        encoding="utf-8",
    )

    batch = import_teammate_csv(csv_path)

    assert batch.records_seen == 1
    assert len(batch.raw_listings) == 1
    assert len(batch.normalized_listings) == 1
    assert len(batch.rejected_listings) == 0
    assert batch.normalized_listings[0].source_listing_id == "t-1"
    assert batch.normalized_listings[0].has_coordinates is True


def test_import_teammate_csv_generates_missing_listing_id(tmp_path: Path) -> None:
    csv_path = tmp_path / "teammate.csv"
    csv_path.write_text(
        "source_name,source_listing_id,source_url,observed_at,city,price_rub,total_area_m2,rooms,property_type\n"
        "teammate_file,,https://example.test/1,2026-05-31T10:00:00+00:00,Moscow,12000000,48.5,2,apartment\n",
        encoding="utf-8",
    )

    batch = import_teammate_csv(csv_path)

    assert batch.normalized_listings[0].source_listing_id.startswith("generated_")


def test_import_teammate_csv_rejects_missing_required_fields(tmp_path: Path) -> None:
    csv_path = tmp_path / "teammate.csv"
    csv_path.write_text(
        "source_name,source_listing_id,observed_at,city,price_rub,total_area_m2,rooms,property_type\n"
        "teammate_file,t-1,2026-05-31T10:00:00+00:00,Moscow,,48.5,2,apartment\n",
        encoding="utf-8",
    )

    batch = import_teammate_csv(csv_path)

    assert len(batch.normalized_listings) == 0
    assert len(batch.rejected_listings) == 1
    assert "price_rub" in batch.rejected_listings[0].reason
```

- [ ] **Step 2: Verify red**

Run: `python -m pytest tests/test_teammate_import.py -q`

Expected: fail because `realtyscope.ingestion.teammate_import` does not exist yet.

- [ ] **Step 3: Implement teammate importer**

Implement `import_teammate_csv(path: Path) -> IngestionBatch` with these rules:

- Read UTF-8/UTF-8-BOM CSV with `csv.DictReader`.
- Required source fields: `source_name`, `observed_at`, `city`, `price_rub`, `total_area_m2`, `rooms`, `property_type`.
- Optional source fields: `source_listing_id`, `source_url`, `address_text`, `latitude`, `longitude`, `floor`, `floors_total`, `building_year`, `description`.
- If `source_listing_id` is blank, generate it with `stable_listing_id`.
- Always keep the original CSV row as `RawListing.raw_payload`.
- Invalid rows become `RejectedListing` records and do not enter `normalized_listings`.

- [ ] **Step 4: Verify green**

Run: `python -m pytest tests/test_teammate_import.py -q`

Expected: pass.

---

### Task 3: Add Replaceable Domclick Snapshot Parser

**Files:**
- Create: `src/realtyscope/ingestion/domclick.py`
- Create: `tests/test_domclick_parser.py`

- [ ] **Step 1: Write the failing tests**

Create tests for these exact behaviors:

```python
from datetime import UTC, datetime

from realtyscope.ingestion.domclick import DomclickCollectorConfig, parse_domclick_payload


def test_parse_domclick_payload_extracts_nested_listing_items() -> None:
    payload = {
        "result": {
            "items": [
                {
                    "id": "d-1",
                    "url": "https://domclick.ru/card/1",
                    "price": 12500000,
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
    payload = {"items": [{"id": "bad", "price": 12500000}]}

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
```

- [ ] **Step 2: Verify red**

Run: `python -m pytest tests/test_domclick_parser.py -q`

Expected: fail because `realtyscope.ingestion.domclick` does not exist yet.

- [ ] **Step 3: Implement parser**

Implement:

- `DomclickCollectorConfig` dataclass with safe defaults: `max_records=100`, `request_delay_seconds=1.0`, and a clear RealtyScope user agent.
- `parse_domclick_payload(payload, source_url, observed_at, config=None) -> IngestionBatch`.
- Recursive discovery of listing arrays under keys `items`, `listings`, `offers`, or `cards`.
- Field aliases for common Domclick-like payloads: IDs from `id`/`offerId`/`listingId`, URL from `url`/`absoluteUrl`, price from `price`/`cost`, area from `area`/`totalArea`/`square`, rooms from `rooms`/`roomsCount`, longitude from `longitude`/`lng`/`lon`, floors total from `floors_total`/`floorsTotal`/`floorCount`.
- Reject incomplete listing items into `RejectedListing`.
- Do not perform live HTTP requests in Phase 2 tests.

- [ ] **Step 4: Verify green**

Run: `python -m pytest tests/test_domclick_parser.py -q`

Expected: pass.

---

### Task 4: Add Raw/Normalized JSONL Pipeline

**Files:**
- Create: `src/realtyscope/ingestion/pipeline.py`
- Create: `tests/test_ingestion_pipeline.py`
- Modify: `README.md`

- [ ] **Step 1: Write the failing tests**

Create tests for these exact behaviors:

```python
import json
from datetime import UTC, datetime
from pathlib import Path

from realtyscope.ingestion.contracts import IngestionBatch, NormalizedListing, RawListing
from realtyscope.ingestion.pipeline import write_ingestion_batch


def test_write_ingestion_batch_creates_raw_and_normalized_jsonl(tmp_path: Path) -> None:
    batch = IngestionBatch(
        raw_listings=(
            RawListing(
                source_name="domclick",
                source_listing_id="d-1",
                source_url="https://example.test/1",
                observed_at=datetime(2026, 5, 31, tzinfo=UTC),
                raw_payload={"id": "d-1", "price": 12000000},
            ),
        ),
        normalized_listings=(
            NormalizedListing(
                source_name="domclick",
                source_listing_id="d-1",
                source_url="https://example.test/1",
                observed_at=datetime(2026, 5, 31, tzinfo=UTC),
                city="Moscow",
                price_rub=12000000,
                total_area_m2=48.5,
                rooms=2,
                property_type="apartment",
            ),
        ),
    )

    manifest = write_ingestion_batch(batch, output_dir=tmp_path, run_name="test-run")

    raw_line = json.loads(manifest.raw_path.read_text(encoding="utf-8").splitlines()[0])
    normalized_line = json.loads(
        manifest.normalized_path.read_text(encoding="utf-8").splitlines()[0]
    )

    assert manifest.records_seen == 1
    assert manifest.raw_count == 1
    assert manifest.normalized_count == 1
    assert raw_line["payload_hash"]
    assert normalized_line["price_per_m2"]
```

- [ ] **Step 2: Verify red**

Run: `python -m pytest tests/test_ingestion_pipeline.py -q`

Expected: fail because `realtyscope.ingestion.pipeline` does not exist yet.

- [ ] **Step 3: Implement JSONL writer**

Implement:

- `IngestionManifest` frozen pydantic model with paths and counts.
- `write_ingestion_batch(batch, output_dir, run_name) -> IngestionManifest`.
- Output files named `{run_name}.raw.jsonl`, `{run_name}.normalized.jsonl`, and `{run_name}.rejected.jsonl`.
- JSON rows generated with `model_dump(mode="json")`, `ensure_ascii=False`, and `sort_keys=True`.

- [ ] **Step 4: Add README Phase 2 note**

Modify `README.md` so the status section says Phase 2 has started and now includes local ingestion contracts/parsers only. It must still say PostgreSQL persistence, OSM enrichment, ML training, Redis usage, and full dashboard pages are future phases.

- [ ] **Step 5: Verify green**

Run: `python -m pytest tests/test_ingestion_pipeline.py -q`

Expected: pass.

---

### Task 5: Final Phase 2 Foundation Verification

**Files:**
- Modify only files listed above if verification exposes a Phase 2 issue.

- [ ] **Step 1: Run focused ingestion tests**

Run:

```powershell
python -m pytest tests/test_ingestion_contracts.py tests/test_teammate_import.py tests/test_domclick_parser.py tests/test_ingestion_pipeline.py -q
```

Expected: all focused ingestion tests pass.

- [ ] **Step 2: Run full test suite**

Run:

```powershell
python -m pytest -q
```

Expected: all tests pass.

- [ ] **Step 3: Run ruff checks**

Run:

```powershell
python -m ruff check .
python -m ruff format --check .
```

Expected: both commands pass.

- [ ] **Step 4: Review Phase 2 scope**

Run:

```powershell
git diff --stat
git diff -- src/realtyscope/ingestion tests README.md docs/superpowers/plans/2026-05-31-realtyscope-phase2-ingestion-plan.md
```

Expected: diff touches only the allowed Phase 2 files and contains no DB migrations, OSM enrichment, ML training, API endpoint, Streamlit page, Docker, or CI implementation.
