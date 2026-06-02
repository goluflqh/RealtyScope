# RealtyScope Phase 5 Ingestion And MLOps Hardening Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. The user has already requested inline execution, verification, commits, and pushes rather than stopping at planning.

**Goal:** Make RealtyScope's scheduled data product credible end-to-end by fixing daily observation evidence, adding real OSM rows, rebuilding leakage-controlled ML evidence, and hardening MLflow/API/Streamlit/monitoring behavior.

**Architecture:** Phase 5 starts from Phase 4 code at `36b41bc` plus the docs/ops playbook branch `ops-midnight-ingestor-guidance`. The first slice preserves raw payload deduplication while changing observation history semantics so a new deliberate `observed_at` can create a new observation even when raw content is reused. Later slices should keep the same pattern: small behavior change, RED test, minimal implementation, verification, commit, push.

**Tech Stack:** Python 3.12, SQLAlchemy 2.0, Alembic, PostgreSQL/SQLite tests, pandas, scikit-learn, MLflow, FastAPI, Streamlit, Redis, pytest, ruff, GitNexus, mem0.

---

## Current Starting Point

- Base branch: `phase5-ingestion-mlops-hardening`, created from `ops-midnight-ingestor-guidance`.
- Phase 4 code index: GitNexus `realtyscope-phase4-index` at `36b41bc91ad4465be088ad88794b1c133a54df29`.
- Code freshness gate: `git diff --quiet phase4-eda-ml-osm..HEAD -- src services tests scripts alembic` passed before code edits, so docs/ops changes did not alter indexed code paths.
- Highest-priority caveat from checkpoint: the 2026-06-02 scheduled run succeeded but reused an existing same-day raw snapshot and inserted no new observations.

## Non-Negotiable Gates

- [x] Resume mem0 with `resume_project(project_id="python", limit=3, include_global=true)`.
- [x] Confirm branch/base and GitNexus code freshness before editing code.
- [x] Use TDD for behavior changes: write RED test, verify it fails for the right reason, then implement.
- [x] Do not call live Domclick or live OSM from unit tests.
- [x] Run focused tests for each slice before commit.
- [ ] Before Phase 5 completion claim, run `pytest`, `ruff check`, `ruff format`, and `git diff --check` freshly.
- [ ] Commit and push each clean slice.
- [ ] Save a mem0 checkpoint with results, caveats, and next step.

## Slice 1: Scheduled Observation Semantics

**Files:**
- Modify: `src/realtyscope/database/models.py`
- Modify: `src/realtyscope/database/persistence.py`
- Create: `alembic/versions/20260602_0004_listing_observation_semantics.py`
- Modify: `tests/test_database_persistence.py`
- Modify: `tests/test_domclick_scheduled_batch.py`
- Modify: `tests/test_alembic_config.py`
- Modify docs after behavior is verified: `docs/operations/domclick-scheduled-batch-ingestion.md` and `.vi.md`

- [x] Add a failing persistence regression test: same raw payload, later `observed_at`, same listing, creates a second `ListingObservation` but reuses the raw row.
- [x] Add a failing scheduled batch regression test with the same behavior through `run_domclick_scheduled_batch` using offline snapshots.
- [x] Update observation uniqueness from raw-row-only to deliberate source/listing/observed timestamp semantics.
- [x] Keep same-run/same-timestamp reprocessing idempotent.
- [x] Update Alembic metadata expectations and operations docs.
- [x] Verify with `pytest tests/test_database_persistence.py tests/test_domclick_scheduled_batch.py tests/test_alembic_config.py -q`.
- [x] Commit and push the slice.

## Slice 2: Real OSM Rows

**Files:**
- Modify or add under `src/realtyscope/enrichment/`
- Modify tests under `tests/test_osm_enrichment.py`
- Update docs under `docs/data/osm-enrichment.*.md`

- [x] Add fixture/local OSM row persistence tests first.
- [x] Populate real DB rows from persisted coordinates using bounded, cached, non-test execution.
- [x] Record row counts and OpenStreetMap attribution.
- [x] Commit and push the slice.

## Slice 3: Non-Leaky ML Features And MLflow Evidence

**Files:**
- Modify `src/realtyscope/ml/features.py`
- Modify `src/realtyscope/ml/train.py`
- Modify `tests/test_ml_features.py` and `tests/test_ml_training.py`
- Update `docs/ml/phase4-baseline-model.*.md` or create Phase 5 ML docs

- [x] Add RED tests for `ml_features_v2_non_leaky` excluding target-like latest price fields from features.
- [x] Train/evaluate against a naive baseline with validation that does not leak duplicate observations across train/test.
- [x] Log params, metrics, and artifact metadata to MLflow when configured.
- [ ] Commit and push the slice.

## Slice 4: API, Streamlit, And Monitoring Hardening

**Files:**
- Modify `services/api/app/*`
- Modify `services/streamlit/*`
- Modify API/Streamlit tests

- [ ] Move model/resource loading toward app state or lifespan where practical.
- [ ] Add model health/metadata and ingestion monitoring payloads with tests.
- [ ] Add reviewer-facing Streamlit monitoring/model insight behavior backed by API client tests.
- [ ] Verify with focused tests and browser/runtime checks when services run locally.
- [ ] Commit and push the slice.

## Final Phase 5 Verification

- [ ] `pytest`
- [ ] `ruff check .`
- [ ] `ruff format .`
- [ ] `git diff --check`
- [ ] Push final branch state.
- [ ] Save mem0 checkpoint with outcome, caveats, and next step.
