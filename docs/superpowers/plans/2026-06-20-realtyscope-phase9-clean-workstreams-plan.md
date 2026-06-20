# RealtyScope Phase 9 Clean Workstreams Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move RealtyScope from the recovered real-data Russian UI and validated scheduler state into a final, reviewable Phase 9 without mixing `main`, UI, scheduler, data, backend, MLOps, API, monitoring, and documentation workstreams.

**Architecture:** Phase 9 is a clean-branch orchestration phase, not a single mega-branch. Start from the already recovered and verified workstreams, publish/readiness-check Phase 8 first, then implement backend/data and MLOps correctness before continuing the Russian UI redesign from `ui/recovered-real-data-dashboard-20260620`. Each slice must produce fresh evidence from the current state and must not use fake/sample UI data as production proof.

**Tech Stack:** Python 3.12, FastAPI, Streamlit, PostgreSQL, Redis, SQLAlchemy 2.0, Alembic, scikit-learn, MLflow, Docker Compose, Windows Task Scheduler, pytest, ruff, GitHub Actions.

---

## Source Context And Non-Negotiables

Authoritative starting points:

- Main checkout `E:\Магистр\2-курс\python\RealtyScope` is clean but local `main` is ahead of `origin/main` by five commits. Do not push or merge this mixed local `main`.
- Phase 8 scheduler publication branch: `ops/domclick-scheduler-validated-20260619`, worktree `C:\Users\lequa\.config\superpowers\worktrees\RealtyScope\domclick-scheduler-validated-20260619`, head `e62b068`.
- Data import branch: `data/teammate-json-import-20260618`, worktree `C:\Users\lequa\.config\superpowers\worktrees\RealtyScope\teammate-json-import-20260618`, head `5db4a44`.
- PostgreSQL guardrails branch: `ops/postgres-guardrails-20260618`, worktree `C:\Users\lequa\.config\superpowers\worktrees\RealtyScope\postgres-guardrails-20260618`, head `f5464c1`.
- MLOps planning branch: `ml/model-promotion-workflow`, worktree `C:\Users\lequa\.config\superpowers\worktrees\RealtyScope\model-promotion-workflow`, head `189f315`; this branch currently records intended behavior in `docs/project-status.md` only and does not yet implement dry-run compare/promote/rollback behavior.
- Required UI continuation branch: `ui/recovered-real-data-dashboard-20260620`, worktree `C:\Users\lequa\.config\superpowers\worktrees\RealtyScope\ui-recovered-real-data-dashboard-20260620`, head `b6922b7`. Continue Phase 9D from this branch, not from `ui/realtyscope-ultimate-redesign`.
- Existing scheduler success evidence is two consecutive automatic runs: 2026-06-19 and 2026-06-20 Moscow, both `LastTaskResult=0`, with runtime logs and Domclick reports. Preserve this evidence; do not change scheduler triggers or run live Domclick capture without explicit approval.

Pause immediately if a step would reset or repoint `main`, delete branches or stashes, rewrite history, change scheduler behavior, run live Domclick capture, push or merge to remote, add heavy ML dependencies such as XGBoost without a separate dependency plan, or if real API/PostgreSQL/model evidence contradicts the plan.

## File Structure

Phase 9 should keep responsibilities separated by workstream:

- `docs/project-status.md`: operating status board. Update only from docs/final-readiness branches after fresh evidence exists.
- `docs/superpowers/plans/2026-06-20-realtyscope-phase9-clean-workstreams-plan.md`: this technical plan.
- `docs/superpowers/plans/2026-06-20-realtyscope-phase9-clean-workstreams-plan.vi.md`: Vietnamese companion summary for handoff and user-facing progress.
- `src/realtyscope/ingestion/teammate_import.py` and `tests/test_teammate_import.py`: Phase 9A data import readiness, starting from `data/teammate-json-import-20260618` if publication or extension is required.
- `docker-compose.yml`: PostgreSQL temp/storage guardrails, starting from `ops/postgres-guardrails-20260618` if publication or extension is required.
- `src/realtyscope/ml/train.py`: existing trainer; keep it focused on reproducible training and MLflow logging.
- `src/realtyscope/ml/model_selection.py`: create in Phase 9B for selected-model pointer, decision reports, and rollback state.
- `src/realtyscope/ml/model_compare.py`: create in Phase 9B for metric comparison and promotion gates.
- `src/realtyscope/ml/promotion_cli.py`: create in Phase 9B for dry-run compare, gated promote, reject, and rollback commands.
- `tests/test_ml_model_compare.py` and `tests/test_ml_model_selection.py`: create in Phase 9B for pass/reject/rollback behavior without live external services.
- `services/api/app/main.py`, `services/api/app/schemas.py`, and API tests: Phase 9C model metadata/monitoring/API gaps only after model selection behavior exists.
- `services/streamlit/app.py`, `services/streamlit/dashboard_charts.py`, `services/streamlit/api_client.py`, and Streamlit tests: Phase 9D Russian UI continuation from the recovered real-data dashboard.
- `docs/demo-script.md`, `docs/demo-script.vi.md`, README, traceability docs, and CI notes: Phase 9E final evidence consolidation.

## Phase 8: Branch Publication And Readiness

**Branch/worktree:** `ops/domclick-scheduler-validated-20260619` at `C:\Users\lequa\.config\superpowers\worktrees\RealtyScope\domclick-scheduler-validated-20260619`.

**Goal:** Prepare the scheduler reliability work for push/PR without touching mixed local `main`.

**Acceptance checks:** Worktree clean; branch diff against `origin/main` contains only scheduler reliability code/docs/tests; targeted scheduler tests pass; no scheduler trigger changes are made; two automatic scheduler successes from 2026-06-19 and 2026-06-20 are cited in PR notes as operational evidence.

### Task 1: Verify Phase 8 Branch Shape

**Files:** no edits expected.

- [ ] **Step 1: Confirm branch and cleanliness**

Run:

```powershell
git -C "C:\Users\lequa\.config\superpowers\worktrees\RealtyScope\domclick-scheduler-validated-20260619" status --short --branch
```

Expected: branch is `ops/domclick-scheduler-validated-20260619`; status has no modified/untracked files.

- [ ] **Step 2: Confirm diff scope**

Run:

```powershell
git -C "C:\Users\lequa\.config\superpowers\worktrees\RealtyScope\domclick-scheduler-validated-20260619" diff --stat origin/main..HEAD
```

Expected: changes are limited to scheduler reliability docs, `scripts/run_domclick_scheduled_batch.ps1`, Domclick capture/scheduled batch code, and focused tests.

### Task 2: Run Phase 8 Verification

**Files:** no edits expected unless a verification failure reveals a real bug.

- [ ] **Step 1: Run static checks**

Run:

```powershell
python -m ruff check src/realtyscope/ingestion tests/test_domclick_chrome_capture.py tests/test_domclick_scheduled_batch.py
python -m ruff format --check src/realtyscope/ingestion tests/test_domclick_chrome_capture.py tests/test_domclick_scheduled_batch.py
```

Expected: both commands exit 0.

- [ ] **Step 2: Run focused tests**

Run:

```powershell
python -m pytest tests/test_domclick_chrome_capture.py tests/test_domclick_scheduled_batch.py -q -p no:cacheprovider
```

Expected: all selected tests pass.

- [ ] **Step 3: Record publication notes without pushing**

Create local PR notes in the final report or a docs branch only. Include the exact branch, commit, test commands, and automatic scheduler evidence. Do not push unless the user explicitly approves.

## Phase 9A: Data And Backend Readiness

**Branches/worktrees:** `data/teammate-json-import-20260618`, `ops/postgres-guardrails-20260618`, and a new `data/phase9-backend-readiness-YYYYMMDD` branch only if new backend/data edits are required.

**Goal:** Make the real-data foundation ready for MLOps and UI work without changing scheduler behavior or running live capture.

**Acceptance checks:** Teammate JSON import branch is clean and verified; PostgreSQL guardrail branch is clean and verified; runtime API reads real PostgreSQL data; Redis cache proof is fresh; data counts and model feature coverage are recorded from current runtime, not stale docs.

### Task 1: Verify Existing Data Split Branches

**Files:** no edits expected.

- [ ] **Step 1: Verify teammate JSON import branch**

Run:

```powershell
git -C "C:\Users\lequa\.config\superpowers\worktrees\RealtyScope\teammate-json-import-20260618" status --short --branch
git -C "C:\Users\lequa\.config\superpowers\worktrees\RealtyScope\teammate-json-import-20260618" diff --stat origin/main..HEAD
python -m pytest tests/test_teammate_import.py -q -p no:cacheprovider
```

Expected: clean branch; diff limited to teammate import code/tests; tests pass.

- [ ] **Step 2: Verify PostgreSQL guardrails branch**

Run:

```powershell
git -C "C:\Users\lequa\.config\superpowers\worktrees\RealtyScope\postgres-guardrails-20260618" status --short --branch
git -C "C:\Users\lequa\.config\superpowers\worktrees\RealtyScope\postgres-guardrails-20260618" diff --stat origin/main..HEAD
git -C "C:\Users\lequa\.config\superpowers\worktrees\RealtyScope\postgres-guardrails-20260618" diff --check origin/main..HEAD
```

Expected: clean branch; diff limited to Docker Compose PostgreSQL guardrails; diff check exits 0.

### Task 2: Refresh Runtime Data Evidence Without Live Capture

**Files:** update `docs/project-status.md` only on a dedicated docs/final-readiness branch after command evidence exists.

- [ ] **Step 1: Check API and real data counts**

Run against the existing local runtime only:

```powershell
Invoke-RestMethod "http://127.0.0.1:8000/health"
Invoke-RestMethod "http://127.0.0.1:8000/data?limit=3&offset=0"
Invoke-RestMethod "http://127.0.0.1:8000/monitoring/status"
Invoke-RestMethod "http://127.0.0.1:8000/model/metadata"
```

Expected: HTTP 200 responses; `/data` returns real rows from PostgreSQL; monitoring reports latest successful ingestion; model metadata reports the selected baseline artifact or a clear unavailable state.

- [ ] **Step 2: Prove Redis read cache after a filtered API call**

Run the filtered `/data` request used by earlier evidence and inspect Redis from the running Compose project if Docker is available through WSL.

Expected: Redis contains the matching `realtyscope:listings:v1:*` key with a positive TTL after the API request.

## Phase 9B: MLOps Retrain, Compare, Promote Workflow

**Branch/worktree:** continue or replace `ml/model-promotion-workflow` at `C:\Users\lequa\.config\superpowers\worktrees\RealtyScope\model-promotion-workflow` after confirming it is clean. If the existing branch remains docs-only, implement there; if it contains unrelated edits later, create `ml/phase9-model-promotion-YYYYMMDD` from `origin/main` and port only the accepted docs text.

**Goal:** Add a controlled model lifecycle: dry-run train/compare, gated promote/reject, selected-model pointer, rollback behavior, decision report, and tests.

**Acceptance checks:** Dry-run compare does not change active selection; promote changes selection only when gates pass; reject keeps active selection unchanged; rollback restores the previous selected artifact; `/predict` remains serving-only; tests do not call live Domclick or live OSM.

### Task 1: Add Metric Comparison Gate

**Files:** create `src/realtyscope/ml/model_compare.py`; create `tests/test_ml_model_compare.py`.

- [ ] **Step 1: Write failing comparison tests**

Add tests for three outcomes: candidate passes when MAE and RMSE improve by threshold and R2 is within tolerance; candidate rejects when MAE is worse; candidate rejects when required metrics are missing.

Run:

```powershell
python -m pytest tests/test_ml_model_compare.py -q -p no:cacheprovider
```

Expected: fail because `realtyscope.ml.model_compare` does not exist.

- [ ] **Step 2: Implement minimal comparison module**

Implement typed dataclasses for active metrics, candidate metrics, gate thresholds, and `compare_candidate(active, candidate, gates)` returning `promote` or `reject` with reasons.

- [ ] **Step 3: Verify comparison tests**

Run:

```powershell
python -m pytest tests/test_ml_model_compare.py -q -p no:cacheprovider
python -m ruff check src/realtyscope/ml/model_compare.py tests/test_ml_model_compare.py
python -m ruff format --check src/realtyscope/ml/model_compare.py tests/test_ml_model_compare.py
```

Expected: all commands exit 0.

### Task 2: Add Selected Model State And Rollback

**Files:** create `src/realtyscope/ml/model_selection.py`; create `tests/test_ml_model_selection.py`.

- [ ] **Step 1: Write failing selection tests**

Tests should cover initial selected model read, promotion writing a new selection without deleting the old artifact, and rollback restoring the previous selection.

Run:

```powershell
python -m pytest tests/test_ml_model_selection.py -q -p no:cacheprovider
```

Expected: fail because `realtyscope.ml.model_selection` does not exist.

- [ ] **Step 2: Implement JSON-backed selection state**

Use a small JSON file under a configurable path such as `data/processed/models/selected_model.json`. Store active artifact path, model version, feature version, metrics, decision timestamp, and previous selection. Do not overwrite or delete model artifacts.

- [ ] **Step 3: Verify selection tests**

Run:

```powershell
python -m pytest tests/test_ml_model_selection.py -q -p no:cacheprovider
python -m ruff check src/realtyscope/ml/model_selection.py tests/test_ml_model_selection.py
python -m ruff format --check src/realtyscope/ml/model_selection.py tests/test_ml_model_selection.py
```

Expected: all commands exit 0.

### Task 3: Add Dry-Run/Promote/Rollback CLI

**Files:** create `src/realtyscope/ml/promotion_cli.py`; modify `pyproject.toml` only if adding a console entry point matches current repo patterns; add CLI tests if needed.

- [ ] **Step 1: Add dry-run compare command**

The command must train or load a candidate, compare against selected active metadata, print/write a decision report, and exit without changing `selected_model.json`.

- [ ] **Step 2: Add gated promote command**

Promotion must require a passing comparison result and must write the previous active model as rollback target.

- [ ] **Step 3: Add rollback command**

Rollback must restore the previous selection and write a decision report. It must not train or call API endpoints.

- [ ] **Step 4: Verify CLI behavior**

Run focused tests plus a local temp-directory CLI smoke that proves dry-run leaves selection unchanged and rollback restores the prior selection.

Expected: dry-run, promote-pass, promote-reject, and rollback behavior all have deterministic tests.

## Phase 9C: API And Monitoring Gaps

**Branch/worktree:** create `api/phase9-monitoring-model-selection-YYYYMMDD` from `origin/main` after Phase 9B passes or from the verified Phase 9B branch if it must consume model-selection code.

**Goal:** Expose selected-model and operational status clearly through API/monitoring without training during API requests.

**Acceptance checks:** `/model/metadata` reports selected artifact state and rollback target when available; `/monitoring/status` includes fresh ingestion/model status without fake data; tests cover unavailable model state and selected model state; FastAPI startup still loads resources once.

### Task 1: Wire Selected Model Metadata Into API

**Files:** modify `services/api/app/main.py`, `services/api/app/schemas.py`, and `tests/test_api_monitoring.py`.

- [ ] **Step 1: Add failing tests for selected-model metadata**

Expected metadata should include active model name, artifact path, model version, feature version, metric summary, selected timestamp, and rollback availability.

- [ ] **Step 2: Implement read-only selected-model loading**

API must read selection state at startup or through a bounded helper. It must not train, compare, promote, or rollback during requests.

- [ ] **Step 3: Verify API tests**

Run:

```powershell
python -m pytest tests/test_api_monitoring.py tests/test_api_prediction_contract.py -q -p no:cacheprovider
python -m ruff check services/api/app tests/test_api_monitoring.py tests/test_api_prediction_contract.py
python -m ruff format --check services/api/app tests/test_api_monitoring.py tests/test_api_prediction_contract.py
```

Expected: all commands exit 0.

## Phase 9D: Russian Real-Data UI Redesign

**Branch/worktree:** `ui/recovered-real-data-dashboard-20260620` at `C:\Users\lequa\.config\superpowers\worktrees\RealtyScope\ui-recovered-real-data-dashboard-20260620`.

**Goal:** Continue the accepted dark Russian direction from the recovered real-data dashboard while preserving real API/PostgreSQL data paths.

**Acceptance checks:** UI starts from commit `b6922b7`; no fake/sample production evidence; UI-facing text remains Russian; real API data populates dashboard sections; browser/runtime check confirms the recovered UI can restart against API/PostgreSQL; tests continue to forbid known fake sample literals.

### Task 1: Reconfirm Recovered UI Runtime

**Files:** no edits before baseline evidence.

- [ ] **Step 1: Verify branch and recovered diff**

Run:

```powershell
git -C "C:\Users\lequa\.config\superpowers\worktrees\RealtyScope\ui-recovered-real-data-dashboard-20260620" status --short --branch
git -C "C:\Users\lequa\.config\superpowers\worktrees\RealtyScope\ui-recovered-real-data-dashboard-20260620" rev-parse --short HEAD
git -C "C:\Users\lequa\.config\superpowers\worktrees\RealtyScope\ui-recovered-real-data-dashboard-20260620" diff --stat origin/main..HEAD
```

Expected: branch is clean, head is `b6922b7`, and diff touches only Streamlit UI/chart/test files.

- [ ] **Step 2: Run Streamlit tests**

Run:

```powershell
python -m pytest tests/test_streamlit_dashboard_charts.py tests/test_streamlit_scaffold.py tests/test_streamlit_api_client.py -q -p no:cacheprovider
python -m ruff check services/streamlit tests/test_streamlit_dashboard_charts.py tests/test_streamlit_scaffold.py tests/test_streamlit_api_client.py
python -m ruff format --check services/streamlit tests/test_streamlit_dashboard_charts.py tests/test_streamlit_scaffold.py tests/test_streamlit_api_client.py
```

Expected: all commands exit 0.

### Task 2: Continue Dark Russian UI Polish Without Data Regression

**Files:** modify `services/streamlit/app.py`, `services/streamlit/dashboard_charts.py`, and focused Streamlit tests only.

- [ ] **Step 1: Add failing tests for real-data-only UI guardrails**

Keep or extend assertions that forbid mock literals such as `273 680`, `12.46`, `Хамовники`, and `Смотреть все предложения` as production evidence. Add Russian text expectations for the accepted navigation and sections.

- [ ] **Step 2: Polish layout and copy in Russian**

Preserve calls to `fetch_dashboard_data`, `fetch_monitoring_data`, and `request_prediction`. Do not replace API data with static fixtures. Keep UI text Russian and avoid overclaiming model quality.

- [ ] **Step 3: Browser-check against real API/PostgreSQL**

Start API and Streamlit using the repo's existing local/Docker path. Verify in browser that dashboard values come from API data, prediction calls return model output or a clear unavailable state, and monitoring reflects current ingestion/model status.

Expected: no visible fake sample data, no layout overlap in the checked desktop viewport, and no Streamlit crash on first load.

## Phase 9E: Final Docs, CI, And Demo Readiness

**Branch/worktree:** create `docs/phase9-final-readiness-YYYYMMDD` from the latest verified integration point only after Phase 8, 9A, 9B, 9C, and 9D evidence exists.

**Goal:** Produce honest final handoff docs and CI/demo expectations without merging to `main` until explicitly approved.

**Acceptance checks:** README, status board, traceability docs, and demo scripts reflect current verified state; final docs distinguish baseline/partial behavior from completed behavior; CI expectations are clear for each branch/PR; no branch is pushed or merged without approval.

### Task 1: Update Status And Traceability From Evidence

**Files:** `docs/project-status.md`, `docs/course-guidance/*.md`, `docs/demo-script.md`, `docs/demo-script.vi.md`, and README as needed.

- [ ] **Step 1: Collect evidence table**

For each workstream, record branch, commit, commands run, test results, runtime checks, and known limitations.

- [ ] **Step 2: Update docs honestly**

Write docs from evidence only. If a runtime check was not run, say it remains unverified. If model promotion is dry-run only, do not describe it as automatic production retraining.

- [ ] **Step 3: Verify docs and full project readiness**

Run:

```powershell
git diff --check
python -m ruff check .
python -m ruff format --check .
python -m pytest -q -p no:cacheprovider
```

Expected: all commands exit 0 before any final readiness claim. If Docker/Browser/CI cannot be run locally, record exactly what remains unverified.

## Phase 9 Completion Gate

Phase 9 is complete only when every item below has current evidence:

- Phase 8 scheduler branch is publication-ready, with 2026-06-19 and 2026-06-20 automatic scheduler successes preserved.
- Phase 9A data/backend readiness has fresh API/PostgreSQL/Redis evidence and clean branch checks for data import and PostgreSQL guardrails.
- Phase 9B MLOps has dry-run compare, gated promote/reject, rollback/selection behavior, decision reports, and tests.
- Phase 9C API/monitoring exposes selected-model and runtime status without training in API requests.
- Phase 9D recovered Russian UI restarts from `ui/recovered-real-data-dashboard-20260620`, renders real API/PostgreSQL data, keeps UI-facing text Russian, and has browser/runtime evidence.
- Phase 9E docs/CI/demo evidence is fresh and honest.
- No push, PR, merge, stash drop, branch deletion, scheduler trigger change, live Domclick capture, or heavy ML dependency addition happened without explicit user approval.
