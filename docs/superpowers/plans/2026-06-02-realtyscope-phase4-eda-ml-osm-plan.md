# RealtyScope Phase 4 EDA, OSM Enrichment, and Baseline ML Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the stable Phase 3 real-data foundation into defensible EDA, OpenStreetMap infrastructure features, baseline ML training, MLflow evidence, and the first model-ready API/UI contract.

**Architecture:** Phase 4 starts from PostgreSQL data produced by Phase 3: canonical `listings`, `listing_observations`, raw/source links, ingestion runs, and rejected rows. OSM enrichment is introduced after data stability because it needs reliable coordinates and should feed ML feature snapshots, not replace the Domclick listing source. The phase remains offline/testable: tests use fixtures and local DB rows, while public OSM/Overpass access is bounded, cached, attributed, and never called in test loops.

**Tech Stack:** Python 3.12, SQLAlchemy 2.0, Alembic, PostgreSQL, pandas, Jupyter, scikit-learn, MLflow, OpenStreetMap/Overpass or local OSM extracts, pytest, ruff, GitNexus, mem0.

---

## Current Starting Point

- Branch: `phase3-5-real-data-slice`.
- Latest pushed commit: `eeeeb47 docs: standardize phase plans and workflow`.
- GitNexus current index: `realtyscope-phase3-5-index` at commit `eeeeb47`.
- Live 2026-06-02 data: `2000` canonical listings, `2000` raw listings, `2000` source links, `2000` observations, `0` rejected rows.
- Phase 3.7 observation history is available for trend and temporal split features.
- Existing course/design spec already names OpenStreetMap as the enrichment source and requires attribution.

## Non-Negotiable Workflow Gates

1. **Memory gate:** call `resume_project(project_id="python", limit=3, include_global=true)` before phase work.
2. **GitNexus freshness gate:** run GitNexus preflight before code changes. The indexed commit must equal `git rev-parse HEAD`.
3. **Plan gate:** save/update this plan and Vietnamese companion before implementation.
4. **TDD gate:** behavior changes require failing tests first.
5. **No live OSM in tests:** tests use fixtures or mocked/local data only.
6. **Attribution gate:** any OSM-derived UI/docs must include OpenStreetMap attribution.
7. **Verification gate:** no completion claim without fresh test/lint/format/diff checks.

## Recommended Phase 4 Order

1. Phase 4.0a: Capture Runtime Hardening for Domclick scheduled Chrome/CDP automation.
2. Phase 4.0: GitNexus/workflow preflight and data-readiness audit.
3. Phase 4.1: EDA refinement using `listings` + `listing_observations`.
4. Phase 4.2: OSM infrastructure enrichment foundation.
5. Phase 4.3: ML feature snapshot generation.
6. Phase 4.4: Naive and scikit-learn baseline training with MLflow.
7. Phase 4.5: API/UI contracts for predictions and trend/model pages.

## Task 0a: Capture Runtime Hardening

**Files:**
- Modify: `src/realtyscope/ingestion/domclick_chrome_capture.py`
- Modify: `scripts/run_domclick_scheduled_batch.ps1`
- Test: `tests/test_domclick_chrome_capture.py`
- Docs: `docs/operations/domclick-scheduled-batch-ingestion.md`
- Docs: `docs/operations/domclick-scheduled-batch-ingestion.vi.md`
- Docs: `docs/operations/domclick-daily-collection.md`
- Docs: `docs/operations/domclick-daily-collection.vi.md`

- [ ] **Step 1: Write failing offline tests for runtime config**

Tests must cover:

```text
REALTYSCOPE_CAPTURE_RUNTIME defaults to cdp
REALTYSCOPE_CHROME_BINARY overrides legacy REALTYSCOPE_CHROME_PATH
REALTYSCOPE_CHROME_USER_DATA_DIR points to a dedicated automation profile
REALTYSCOPE_CHROME_PROFILE_DIRECTORY defaults to Default inside the dedicated user-data dir
REALTYSCOPE_CHROME_REMOTE_DEBUGGING_PORT is parsed and passed into the CDP dumper
```

- [ ] **Step 2: Keep CDP as the only implemented runtime**

`playwright-sidecar` and other browser sidecars are future deployment options only. Phase 4.0a must keep the existing Chrome DevTools/CDP capture approach and fail clearly if an unsupported runtime is requested.

- [ ] **Step 3: Update scheduled command behavior**

The PowerShell wrapper should pass runtime env overrides through to `realtyscope.ingestion.domclick_chrome_capture`, default to the Python helper's dedicated automation profile, and provide a dry run that prints planned capture/batch commands without starting Docker, Alembic, Chrome, ingestion, or database commits.

- [ ] **Step 4: Update operator docs EN/VI**

Docs must explicitly distinguish interactive Codex `@chrome` from scheduled CDP automation, explain the dedicated profile default, document Docker/Linux portability caveats, and name Playwright/browser sidecar as a future option only.

- [ ] **Step 5: Verify**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_domclick_chrome_capture.py -q
.\scripts\run_domclick_scheduled_batch.ps1 -DryRun -SkipDockerStart -CollectionDate 2099-01-01
```

Expected:

```text
Offline tests pass. Dry run prints capture and batch commands without running live Domclick or writing to PostgreSQL.
```

## Task 0: GitNexus And Workflow Preflight

**Files:**
- Read: `docs/superpowers/realtyscope-agent-workflow.md`
- Read: `docs/superpowers/realtyscope-agent-workflow.vi.md`
- No code changes expected.

- [ ] **Step 1: Verify repo and memory context**

Run:

```powershell
git status --short --branch
git rev-parse HEAD
```

Expected:

```text
Working tree state is known. If dirty, inspect diff before editing and do not overwrite user changes.
```

- [ ] **Step 2: Verify GitNexus freshness**

Preferred current index path:

```powershell
$IndexPath = "C:\Users\lequa\gitnexus-worktrees\realtyscope-phase3-5-index"
git -C $IndexPath checkout --detach (git rev-parse HEAD)
git -C $IndexPath status --short --branch
Push-Location $IndexPath
gitnexus analyze .
gitnexus status
Pop-Location
```

Expected:

```text
GitNexus status says indexed commit equals current commit. MCP `list_repos` shows `realtyscope-phase3-5-index` at the same commit.
```

- [ ] **Step 3: Query impact before edits**

Run GitNexus MCP queries for the target area:

```text
query: "OSM enrichment feature snapshot listings observations ML training"
context: target symbol or file returned by query
impact: upstream/downstream for any shared persistence/model/API symbol before editing
```

Expected:

```text
The implementation task starts with known dependencies and likely affected files.
```

## Task 1: Phase 4 Data-Readiness Audit

**Files:**
- Create: `src/realtyscope/analysis/data_readiness.py`
- Test: `tests/test_data_readiness.py`
- Docs: `docs/data/phase4-data-readiness.vi.md`

- [ ] **Step 1: Write failing tests for DB-readiness metrics**

Test cases should seed a temporary database and assert:

```python
from realtyscope.analysis.data_readiness import summarize_data_readiness


def test_data_readiness_counts_coordinates_and_observations(session):
    summary = summarize_data_readiness(session)
    assert summary.listings_total == 2
    assert summary.with_coordinates == 1
    assert summary.observations_total == 3
    assert summary.price_changes_detected == 1
```

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_data_readiness.py -q
```

Expected before implementation:

```text
FAIL because `realtyscope.analysis.data_readiness` does not exist.
```

- [ ] **Step 2: Implement minimal readiness summary**

Implementation should calculate:

```text
listings_total
with_coordinates
without_coordinates
observations_total
listings_with_multiple_observations
price_changes_detected
ml_ready_listings
missing core fields: price, area, rooms, coordinates
```

- [ ] **Step 3: Verify test passes and run on live DB**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_data_readiness.py -q
.\.venv\Scripts\python.exe -m realtyscope.analysis.data_readiness --database-url $env:DATABASE_URL --json
```

Expected:

```text
Test passes. Live DB output is saved or summarized in `docs/data/phase4-data-readiness.vi.md`.
```

## Task 2: EDA Refinement With Observation History

**Files:**
- Modify: `notebooks/phase3_eda_skeleton.ipynb` or create `notebooks/phase4_eda_observations.ipynb`
- Create: `docs/data/phase4-eda-observations.md`
- Create: `docs/data/phase4-eda-observations.vi.md`
- Test: `tests/test_phase4_eda_notebook.py`

- [ ] **Step 1: Add notebook structure test**

The test must assert notebook sections exist for:

```text
latest listing distributions
observation count and price-change analysis
coordinate coverage
candidate OSM enrichment readiness
naive baseline target distribution
Vietnamese conclusions
```

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_phase4_eda_notebook.py -q
```

Expected before notebook update:

```text
FAIL because Phase 4 EDA notebook does not exist or lacks required sections.
```

- [ ] **Step 2: Add real EDA notebook and summaries**

Notebook must read from PostgreSQL and produce stable outputs for:

```text
price_rub distribution
price_per_m2 distribution
area/rooms/floor distributions
missingness and outlier candidates
coordinate coverage
latest vs observation history counts
price-change examples if available
recommendation on whether data is enough for baseline ML
```

- [ ] **Step 3: Verify notebook structure and docs**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_phase4_eda_notebook.py -q
git diff --check
```

Expected:

```text
Notebook structure test passes and docs contain evidence-based conclusions, not generic claims.
```

## Task 3: OSM Infrastructure Enrichment Foundation

**Files:**
- Create: `src/realtyscope/enrichment/osm.py`
- Create: `src/realtyscope/enrichment/__init__.py`
- Create: `tests/test_osm_enrichment.py`
- Create: Alembic migration for `osm_features` if table is not already present.
- Modify: `src/realtyscope/database/models.py`
- Docs: `docs/data/osm-enrichment.md`, `docs/data/osm-enrichment.vi.md`

- [ ] **Step 1: Write failing tests for fixture-based OSM feature extraction**

Use a small local fixture representing Overpass-like elements. Do not call public OSM in tests.

```python
from realtyscope.enrichment.osm import compute_osm_features


def test_compute_osm_features_counts_infrastructure_within_radius():
    listing = {"latitude": 55.75, "longitude": 37.61}
    elements = [
        {"type": "node", "lat": 55.7505, "lon": 37.6105, "tags": {"amenity": "school"}},
        {"type": "node", "lat": 55.7510, "lon": 37.6110, "tags": {"public_transport": "station"}},
    ]

    features = compute_osm_features(listing, elements, radii_m=(500, 1000))

    assert features.schools_500m == 1
    assert features.transport_500m == 1
    assert features.nearest_transport_m is not None
```

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_osm_enrichment.py -q
```

Expected before implementation:

```text
FAIL because OSM enrichment module does not exist.
```

- [ ] **Step 2: Implement local feature computation only**

Features should include a conservative first set:

```text
transport_count_500m, transport_count_1000m
nearest_transport_m
schools_count_1000m
parks_count_1000m
shops_count_1000m
healthcare_count_1000m
osm_feature_version
```

- [ ] **Step 3: Add persistence model/migration if Phase 4 stores OSM features**

Recommended table:

```text
osm_features:
  id
  listing_id
  latitude
  longitude
  feature_version
  transport_count_500m
  transport_count_1000m
  nearest_transport_m
  schools_count_1000m
  parks_count_1000m
  shops_count_1000m
  healthcare_count_1000m
  source_summary
  created_at
unique(listing_id, feature_version)
```

- [ ] **Step 4: Add bounded live enrichment command only after fixture tests pass**

The command must support dry-run and strict limits:

```powershell
.\.venv\Scripts\python.exe -m realtyscope.enrichment.osm --database-url $env:DATABASE_URL --limit 50 --dry-run --json
```

Rules:

```text
No public Nominatim bulk geocoding.
Use listing coordinates already present.
Use cache or local extract where possible.
Rate-limit public Overpass calls.
Do not run public OSM calls in automated tests.
Show OpenStreetMap attribution in docs/UI if derived features are shown.
```

## Task 4: ML Feature Snapshot Generation

**Files:**
- Create: `src/realtyscope/ml/features.py`
- Create: `tests/test_ml_features.py`
- Optional migration/model: `ml_feature_snapshots` if not already present.

- [ ] **Step 1: Write failing tests for feature rows**

Test should assert a seeded listing plus optional OSM features produces a model-ready row:

```python
from realtyscope.ml.features import build_feature_rows


def test_build_feature_rows_joins_listing_observations_and_osm(session):
    rows = build_feature_rows(session)
    assert rows[0].target_price_rub > 0
    assert "total_area_m2" in rows[0].features
    assert "nearest_transport_m" in rows[0].features
```

- [ ] **Step 2: Implement feature builder**

Feature builder must use:

```text
listing latest facts
latest or selected observation facts
OSM features when available
missingness flags for optional OSM/coordinate fields
stable feature_version
```

- [ ] **Step 3: Verify tests and export small feature summary**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_ml_features.py -q
```

Expected:

```text
Tests pass and feature rows are deterministic.
```

## Task 5: Naive Baseline And Scikit-Learn Baseline With MLflow

**Files:**
- Create: `src/realtyscope/ml/train.py`
- Create: `tests/test_ml_training.py`
- Docs: `docs/ml/phase4-baseline-model.md`, `docs/ml/phase4-baseline-model.vi.md`

- [ ] **Step 1: Write failing smoke tests for training**

Tests should use tiny deterministic feature fixtures:

```python
from realtyscope.ml.train import train_baseline_model


def test_train_baseline_model_beats_naive_on_tiny_fixture(tmp_path):
    result = train_baseline_model(feature_rows=tiny_feature_rows(), output_dir=tmp_path)
    assert result.metrics["mae"] <= result.metrics["naive_mae"]
    assert result.artifact_path.exists()
```

- [ ] **Step 2: Implement naive and baseline models**

Start conservative:

```text
naive median or median price_per_m2 baseline
Ridge/Linear Regression or RandomForestRegressor baseline
MAE, RMSE, MAPE, R2 metrics
model artifact via joblib
MLflow logging when tracking URI is configured
```

- [ ] **Step 3: Verify training command on live data**

Run:

```powershell
.\.venv\Scripts\python.exe -m realtyscope.ml.train --database-url $env:DATABASE_URL --output-dir data/processed/models/phase4 --json
```

Expected:

```text
Training completes, metrics are documented, model artifact is ignored by git, and MLflow run ID is recorded if MLflow is enabled.
```

## Task 6: Prediction Contract And Dashboard Planning Hook

**Files:**
- Create or modify: `services/api/app/schemas.py`
- Modify: `services/api/app/main.py`
- Modify: `services/streamlit/app.py` only after API contract exists.
- Tests: `tests/test_api_prediction_contract.py`, `tests/test_streamlit_scaffold.py`

- [ ] **Step 1: Add API contract tests before endpoint implementation**

Test `/predict` schema with a fake model dependency or temporary artifact. Do not train inside the API test.

- [ ] **Step 2: Implement minimal prediction endpoint**

Endpoint returns:

```text
predicted_price_rub
model_version or run_id
metrics_summary
input_features_echo or validated feature metadata
```

- [ ] **Step 3: Add Streamlit page only after API contract is stable**

Streamlit should show prediction form, result, model version, and caveat that it is baseline if Phase 4 has not selected a final model.

## Task 7: Documentation, Verification, Commit, Checkpoint

**Files:**
- Modify: `README.md`
- Modify: `docs/course-guidance/realtyscope-user-story-traceability.md`
- Modify: `docs/course-guidance/realtyscope-user-story-traceability.vi.md`
- Modify: this plan and Vietnamese companion if execution changes.

- [ ] **Step 1: Update docs with Phase 4 evidence**

Docs must state:

```text
EDA findings
OSM features implemented or explicitly deferred
ML baseline metrics
MLflow run/artifact evidence
API/UI prediction status
OpenStreetMap attribution
```

- [ ] **Step 2: Run full verification**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m ruff format --check .
git diff --check
gitnexus status
```

Expected:

```text
All pass. GitNexus indexed commit must match the final commit after re-analyze.
```

- [ ] **Step 3: Commit and push when clean**

Use scoped commits, for example:

```bash
git commit -m "feat: add osm enrichment foundation"
git commit -m "feat: train baseline price model"
git push
```

- [ ] **Step 4: Save mem0 checkpoint**

Checkpoint must include:

```text
commit hashes
GitNexus indexed repo/path and commit
row counts and data-readiness findings
OSM feature status
ML metrics and MLflow run ID
verification commands
next phase recommendation
```

## Completion Definition

Phase 4 can be called complete only when:

```text
GitNexus current-branch index is fresh before and after implementation;
EDA conclusions are based on persisted real Domclick rows and observation history;
OSM enrichment is either implemented with bounded/cached/tested behavior or explicitly split into a later subphase with evidence why;
feature snapshot generation is deterministic and tested;
a baseline model trains on real persisted data and is compared against a naive baseline;
MLflow/artifact evidence exists when enabled;
API/UI prediction contract is at least minimally tested or explicitly deferred to Phase 5;
full verification passes;
commits are pushed;
mem0 checkpoint is saved.
```
