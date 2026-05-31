# RealtyScope Phase 3.5 Real Data Slice Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first honest, usable RealtyScope data slice from a real listing source into PostgreSQL, produce real EDA conclusions, then expose the first DB-backed API/dashboard read path.

**Architecture:** Phase 3.5 sits between the Phase 3 database foundation and later ML/API/UI phases. It must not create another empty scaffold: every implemented slice must be backed by a real data source, persisted rows, verifiable counts, and tests or runtime evidence. If no real source is available, the phase stops at the data-source gate and asks for a source decision instead of inventing data.

**Tech Stack:** Python 3.12, pydantic 2, SQLAlchemy 2.0, Alembic, PostgreSQL, pandas, FastAPI, Streamlit, pytest, ruff, Docker Compose.

---

## Current Evidence

- Current branch: `phase2-ingestion`, clean, ahead of origin by commit `308c8ce feat: add phase 3 database persistence foundation`.
- Existing Phase 3 foundation includes SQLAlchemy models, Alembic initial migration, persistence from `IngestionBatch`, sample ingestion command, and EDA skeleton.
- Workspace inventory on 2026-05-31 found no real listing dataset under `E:\Магистр\2-курс\python` or `RealtyScope`, including ignored files.
- Required real source strategy is not arbitrary public data: Domclick must remain the main listing source from the Phase 0/course requirements, with OSM used later for coordinate enrichment. Teammate CSV is allowed only as an additional real source, not as a replacement for Domclick.
- Existing usable ingestion adapters:
  - `src/realtyscope/ingestion/teammate_import.py` for CSV files matching the teammate contract.
  - `src/realtyscope/ingestion/domclick.py` for Domclick-like JSON payload snapshots.
- Existing API/UI are skeletons only: FastAPI has `/health`; Streamlit shows a Phase 1 placeholder.
- Controlled live access findings on 2026-05-31: Domclick `robots.txt` disallows `/search`; the realty sitemap index is accessible and lists sitemap children; child `.xml.gz` sitemap fetches return `401 Unauthorized` even after the index sets QRATOR cookies; direct `/search` and sample card pages return QRATOR challenge HTML.
- `src/realtyscope/ingestion/domclick_live.py` records this access-probe path in code: it checks robots rules, detects QRATOR challenge pages, and extracts sitemap index locations when allowed.

## Non-Negotiable Gates

1. **Real source gate:** do not persist sample fixtures as Phase 3.5 real data. A real source must be selected and recorded.
2. **Persistence gate:** real rows must pass through Phase 2 contracts and Phase 3 persistence into PostgreSQL.
3. **EDA gate:** conclusions must be computed from persisted real rows, not from sample fixtures or assumptions.
4. **API gate:** any new backend endpoint must read from the database, not return mock data.
5. **Dashboard gate:** any new Streamlit view must show real persisted data through the API or a clearly documented local development path.
6. **Verification gate:** every completed slice must have tests or runtime evidence before it is claimed complete.

## Out Of Scope For Phase 3.5

- ML training and model selection.
- MLflow experiment tracking.
- `/predict` production behavior.
- Redis cache behavior.
- Large UI polish or multi-page final dashboard.
- Unbounded live scraping.
- Committing raw dumps, `.env`, database dumps, model artifacts, or notebook outputs.

## Task 1: Real Data Source Decision

**Files:**
- Modify later only if a source is chosen: `README.md`
- Create or modify later only after source choice: source-specific ingestion module/tests

- [ ] **Step 1: Confirm whether a real data file already exists outside the repo**

Ask the user for one of these source decisions:

```text
Choose the Phase 3.5 required source path:
1. Provide a real Domclick snapshot path on this machine: JSON, JSONL, or HTML captured from Domclick.
2. Allow a controlled live Domclick collector with strict max records and delay.
3. Provide a real teammate-source file only as an additional source after Domclick is working.
```

Acceptance evidence:

```text
A concrete Domclick collection path/permission is recorded in the plan/checkpoint. A teammate file can be recorded as an additional source, but not as the main substitute for Domclick.
```

- [ ] **Step 2: Re-run bounded inventory if the user gives a directory**

Run:

```powershell
rg --files -uuu <provided-directory> -g '*.csv' -g '*.json' -g '*.jsonl' -g '*.html' -g '*.htm' -g '*.xlsx' -g '*.parquet'
```

Expected:

```text
At least one Domclick snapshot candidate file is found, or the user-provided directory is reported as having no usable Domclick snapshot files.
```

- [ ] **Step 3: Inspect only a small safe sample of the chosen source**

For CSV:

```powershell
python -c "import csv, pathlib; p=pathlib.Path(r'<SOURCE_PATH>'); f=p.open('r',encoding='utf-8-sig',newline=''); r=csv.DictReader(f); print(r.fieldnames); [print(row) for _, row in zip(range(3), r)]; f.close()"
```

For JSON/JSONL/HTML, use a bounded reader and do not dump the entire file.

Expected:

```text
Fields or payload shape are known well enough to map into RawListing and NormalizedListing.
```

## Task 2: Real Source Adapter Or Existing Importer Path

**Files:**
- Use if compatible: `src/realtyscope/ingestion/teammate_import.py`
- Use if compatible: `src/realtyscope/ingestion/domclick.py`
- Create only if required: `src/realtyscope/ingestion/<source_name>_import.py`
- Test: `tests/test_<source_name>_import.py`

- [ ] **Step 1: Prefer existing importer when the source matches it**

Decision rules:

```text
Domclick-like JSON payload -> use parse_domclick_payload.
Domclick HTML snapshot -> parse embedded structured data or page metadata into IngestionBatch.
CSV with teammate contract columns -> use import_teammate_csv only as an additional source after Domclick works.
Different teammate-source schema -> add a small source-specific adapter after the Domclick path is in place.
```

- [ ] **Step 2: Write a failing test from a tiny real-source fixture shape**

The test must assert:

```text
valid rows become NormalizedListing rows;
invalid rows become RejectedListing rows with reasons;
raw_payload preserves original source fields;
records_seen equals normalized + rejected count.
```

Run:

```powershell
python -m pytest tests/test_<source_name>_import.py -q
```

Expected before implementation:

```text
FAIL because the source-specific mapping or command does not exist yet.
```

- [ ] **Step 3: Implement the minimal adapter**

Implementation constraints:

```text
No live network calls in tests.
No broad parser framework.
No silent row drops.
Every rejected row must include source_name, row_number when available, reason, and raw_payload.
```

- [ ] **Step 4: Verify adapter tests pass**

Run:

```powershell
python -m pytest tests/test_<source_name>_import.py -q
```

Expected:

```text
PASS with valid rows, rejected rows, and raw payload preservation covered.
```

## Task 3: Real Persistence Command

**Files:**
- Create or modify: `src/realtyscope/database/real_data_ingestion.py`
- Test: `tests/test_real_data_ingestion.py`

- [ ] **Step 1: Write a failing CLI-level test**

The test should use SQLite or a migrated temporary database where practical and assert:

```text
command accepts --source-path and --database-url;
command persists the real-source IngestionBatch;
JSON output includes records_seen, raw_inserted, listings_created or listings_updated, rejected_inserted;
DB row counts match the output.
```

Run:

```powershell
python -m pytest tests/test_real_data_ingestion.py -q
```

Expected before implementation:

```text
FAIL because real_data_ingestion module or command behavior does not exist.
```

- [ ] **Step 2: Implement the command with explicit source type selection**

Command shape:

```powershell
python -m realtyscope.database.real_data_ingestion --source-type <domclick_json|domclick_html|domclick_live> --source-path <path-or-url> --database-url <url> --json
```

Output shape:

```json
{
  "source_type": "domclick_json",
  "source_path": "...",
  "records_seen": 0,
  "raw_inserted": 0,
  "raw_reused": 0,
  "listings_created": 0,
  "listings_updated": 0,
  "rejected_inserted": 0
}
```

- [ ] **Step 3: Verify command test passes**

Run:

```powershell
python -m pytest tests/test_real_data_ingestion.py -q
```

Expected:

```text
PASS and no raw data file is committed.
```

## Task 4: PostgreSQL Real Data Verification

**Files:**
- No source changes unless tests expose a bug.
- Local runtime: PostgreSQL from Docker Compose.

- [ ] **Step 1: Start PostgreSQL**

Run:

```powershell
wsl -d Ubuntu -- bash -lc "cd /mnt/e/Магистр/2-курс/python/RealtyScope && docker compose up -d db"
```

Expected:

```text
Container db starts and pg_isready reports accepting connections.
```

- [ ] **Step 2: Create temporary verification database**

Run:

```powershell
wsl -d Ubuntu -- bash -lc "cd /mnt/e/Магистр/2-курс/python/RealtyScope && docker compose exec -T db psql -U realtyscope -d postgres -c 'DROP DATABASE IF EXISTS realtyscope_phase35_verify;' -c 'CREATE DATABASE realtyscope_phase35_verify;'"
```

- [ ] **Step 3: Run Alembic migration**

Run:

```powershell
$env:DATABASE_URL="postgresql+psycopg://realtyscope:realtyscope@localhost:5432/realtyscope_phase35_verify"
python -m alembic upgrade head
```

Expected:

```text
Alembic upgrades from empty database to current head without error.
```

- [ ] **Step 4: Run real ingestion command**

Run:

```powershell
python -m realtyscope.database.real_data_ingestion --source-type <domclick_json|domclick_html|domclick_live> --source-path <selected-domclick-source> --database-url postgresql+psycopg://realtyscope:realtyscope@localhost:5432/realtyscope_phase35_verify --json
```

Expected:

```text
records_seen > 0;
raw_inserted + raw_reused > 0;
listings_created + listings_updated > 0 unless the source contains only invalid rows;
rejected_inserted is reported honestly.
```

- [ ] **Step 5: Query row counts**

Run a bounded SQL count query for:

```text
sources
ingestion_runs
raw_listings
listings
listing_source_links
rejected_listings
```

Expected:

```text
Counts match the JSON output and are recorded in final response/checkpoint.
```

## Task 5: Real EDA Notebook And Summary

**Files:**
- Modify: `notebooks/phase3_eda_skeleton.ipynb`
- Create: `docs/data/phase3-5-real-eda-summary.vi.md`
- Optional create: `docs/data/phase3-5-real-eda-summary.md`
- Test: `tests/test_phase3_eda_notebook.py`

- [ ] **Step 1: Convert skeleton into real-data EDA notebook**

Notebook must include cells for:

```text
DB connection through DATABASE_URL;
listing count and schema;
missing values;
duplicate source links and duplicate-like listings;
price, area, rooms distributions;
price per square meter;
coordinate coverage;
ML-ready coverage;
ingestion run and rejected row stats;
Vietnamese conclusions based on observed persisted rows.
```

- [ ] **Step 2: Write/update notebook structure test**

Run:

```powershell
python -m pytest tests/test_phase3_eda_notebook.py -q
```

Expected:

```text
PASS only if notebook contains real-data EDA sections and no text claiming final conclusions without persisted data evidence.
```

- [ ] **Step 3: Write Vietnamese EDA summary**

Summary must include:

```text
source used;
row counts;
missingness observations;
outlier observations;
duplicate observations;
coordinate and ML-ready coverage;
whether data is sufficient for ML now;
next data-quality action.
```

## Task 6: First DB-Backed FastAPI Slice

**Files:**
- Modify: `services/api/app/main.py`
- Create if helpful: `services/api/app/schemas.py`
- Create if helpful: `services/api/app/database.py`
- Test: `tests/test_api_data.py`

- [ ] **Step 1: Write failing API tests**

Tests should cover:

```text
GET /listings returns database-backed listing rows with limit/offset;
GET /stats/data-quality returns persisted counts and ML-ready/rejected stats;
responses do not contain mock/sample hardcoded data.
```

Run:

```powershell
python -m pytest tests/test_api_data.py -q
```

Expected before implementation:

```text
FAIL because endpoints do not exist.
```

- [ ] **Step 2: Implement minimal DB-backed endpoints**

Constraints:

```text
Use existing Settings.database_url.
Keep `/health` unchanged except for narrowly needed setup.
Do not add prediction behavior.
Do not add Redis yet.
```

- [ ] **Step 3: Verify API tests pass**

Run:

```powershell
python -m pytest tests/test_api_health.py tests/test_api_data.py -q
```

Expected:

```text
PASS with database-backed behavior covered.
```

## Task 7: First Usable Streamlit Slice

**Files:**
- Modify: `services/streamlit/app.py`
- Test: `tests/test_streamlit_scaffold.py` or a new Streamlit structure test

- [ ] **Step 1: Add minimal real-data dashboard view**

The page should show:

```text
overall listing count;
ML-ready count;
rejected row count;
small listing preview;
source/ingestion status summary.
```

Preferred data path:

```text
Streamlit calls FastAPI when API_BASE_URL is configured.
A local development fallback may read database only if clearly documented and tested.
```

- [ ] **Step 2: Verify structure test passes**

Run:

```powershell
python -m pytest tests/test_streamlit_scaffold.py -q
```

Expected:

```text
PASS and no dashboard text claims ML/prediction readiness.
```

## Task 8: Documentation, Verification, Commit, Checkpoint

**Files:**
- Modify: `README.md`
- Modify: this plan if execution details change.
- Modify: Vietnamese companion plan.

- [ ] **Step 1: Update README status honestly**

README must state:

```text
which real source was used;
how to run ingestion;
how to run EDA;
which API/dashboard slices are real;
what remains out of scope.
```

- [ ] **Step 2: Run full verification**

Run:

```powershell
python -m pytest -q
python -m ruff check .
python -m ruff format --check .
git diff --check
```

Expected:

```text
All pass. Existing unrelated warnings may be reported but not hidden.
```

- [ ] **Step 3: Commit only when the completed slice is verified**

Commit message:

```bash
git commit -m "feat: add phase 3.5 real data slice"
```

If only the Phase 3.5 plan is committed before source selection, use:

```bash
git commit -m "docs: plan phase 3.5 real data slice"
```

- [ ] **Step 4: Save mem0 checkpoint**

Checkpoint must include:

```text
commit hash;
real data source used or source blocker;
row counts;
EDA conclusions if available;
verification commands;
next step.
```

## Completion Definition

Phase 3.5 is complete only when:

```text
the Domclick listing source path has been selected and used, with teammate data only as an optional additional source;
real rows are persisted to PostgreSQL through Alembic-managed schema;
row counts are recorded;
EDA has real conclusions;
at least the first API data endpoint reads from DB;
dashboard slice exists if scope and source quality allow it;
full verification passes;
commit and mem0 checkpoint are saved.
```

If Domclick access is blocked after repeated controlled attempts, keep the goal active until the strict blocked-audit threshold is met, then mark blocked with evidence or ask for a Domclick snapshot export instead of substituting mock data or an unrelated public dataset.
