# RealtyScope Phase 3.7 Observation History Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an observation/price-history layer so daily captures preserve time-series listing observations instead of only overwriting the latest canonical listing row.

**Architecture:** Keep `listings` as the canonical latest-state table and add immutable/deduped `listing_observations` rows for each normalized listing observation. Persistence upserts canonical listing/source-link state, then inserts an observation snapshot with price, price-per-square-meter, area, rooms, floor, and status fields. Identical repeated payloads are deduped so scheduled reprocessing does not spam history.

**Tech Stack:** Python 3.12, SQLAlchemy 2.0, Alembic, PostgreSQL, pytest, ruff, GitNexus, mem0.

---

## Status

- Execution status: `Completed`.
- Completion commit: `d2bb740 feat: add listing observation history`.
- Branch: `phase3-5-real-data-slice`.
- Current GitNexus index: `realtyscope-phase3-5-index`, refreshed after Phase 3 docs at commit `eeeeb47`.

This document is retrospective because the implementation was completed before this plan was written to disk. It exists to keep `docs/superpowers/plans/` synchronized with the actual phase history.

## Implemented Scope

- Created `listing_observations` SQLAlchemy model.
- Added Alembic migration `20260602_0002_listing_observations.py`.
- Updated persistence so every normalized listing updates canonical `listings` and writes a deduped observation row.
- Added observation fields for listing/source identity, raw listing linkage, observed time, price, price per square meter, area/rooms/floor snapshot, active/status data, and payload hash/deduplication.
- Added offline tests for price-change history and repeated identical payload deduplication.
- Updated docs EN/VI to explain canonical latest listing state versus observation history.
- Created course User Story traceability docs EN/VI before implementation.

## Files Changed By The Phase

- `src/realtyscope/database/models.py`: `ListingObservation` model and relationships.
- `alembic/versions/20260602_0002_listing_observations.py`: migration for observation table/indexes/constraints.
- `src/realtyscope/database/persistence.py`: canonical upsert plus observation insert/dedup behavior.
- `tests/test_database_persistence.py`: price-change and dedup regression tests.
- `docs/data/realtyscope-observation-history.md`: English explanation.
- `docs/data/realtyscope-observation-history.vi.md`: Vietnamese explanation.
- `docs/course-guidance/realtyscope-user-story-traceability.md`: assignment story mapping.
- `docs/course-guidance/realtyscope-user-story-traceability.vi.md`: Vietnamese assignment story mapping.

## Acceptance Gates

- [x] A price change for the same `source_listing_id` updates canonical `listings.price_rub`.
- [x] The same price change creates a new `listing_observations` row.
- [x] Reprocessing an identical payload does not create duplicate observation spam.
- [x] Observation rows preserve enough listing snapshot fields for future trend dashboards, EDA, and ML features.
- [x] Alembic migration applies cleanly.
- [x] Docs explain latest canonical state versus historical observations.
- [x] Live 2026-06-02 scheduled run inserted `2000` observations.

## Verification Evidence

Commands run for Phase 3.7 and later hardening:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m ruff format --check .
git diff --check
python -m realtyscope.ingestion.domclick_scheduled_batch status --database-url postgresql+psycopg://realtyscope:realtyscope@localhost:5432/realtyscope --json
```

Observed results after the final Phase 3 state:

```text
pytest: 74 passed, one existing StarletteDeprecationWarning.
ruff check: All checks passed.
ruff format --check: 52 files already formatted.
git diff --check: passed with Git CRLF warnings only.
DB counts: listings=2000, raw_listings=2000, listing_source_links=2000, listing_observations=2000, rejected_listings=0.
latest run: status=success, records_seen=2000, normalized_count=2000.
```

## Follow-Up Notes

- Phase 4 should build trend/EDA features from `listing_observations`, not from `listings` alone.
- API and Streamlit should expose latest listing state and history/trend views separately.
- Future ML feature snapshots should define whether they use latest-only features, observation-window features, or both.
- Observation history is the correct foundation for price-change, listing freshness, days-on-market approximation, and temporal train/test splitting.
