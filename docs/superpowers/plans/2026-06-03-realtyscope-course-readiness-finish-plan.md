# RealtyScope Course Readiness Finish Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Finish the post-Phase-6 course-readiness work so RealtyScope is easy to inspect, demo, manage, and submit without overstating baseline model or trend evidence.

**Architecture:** Treat `docs/project-status.md` as the live status board and keep requirement traceability docs as the reviewer-facing contract. Execute the remaining work in small, independently verifiable slices on `phase7-course-readiness-polish`; do not resume work on old phase branches. Behavior changes require RED/GREEN tests, Docker/runtime smoke, Browser validation for UI, clean commit/push, and GitHub Actions success.

**Tech Stack:** Python 3.12, FastAPI, Streamlit, pandas, SQLAlchemy, Alembic, PostgreSQL, Redis, MLflow, Docker Compose, pytest, ruff, GitHub Actions, Browser plugin, mem0, GitNexus.

---

## Current Evidence Baseline

- Phase 6 is merged into `main` at `30bce998f1c3e5a6d13085d08a0b3692a52234a2` and preserved as branch `phase6-mlflow-redis-readiness`.
- Active branch is `phase7-course-readiness-polish`.
- Latest runtime/UI behavior slice is `6cb103b12717103369cd52fba843d31fcf0c65db feat: show last successful collection`.
- Local checks for that monitoring slice passed: `git diff --check`, `ruff check .`, `ruff format --check .`, and full `pytest -p no:cacheprovider` with `135 passed`.
- Docker smoke after Streamlit rebuild showed the compose services healthy and `http://localhost:8501` returning HTTP `200`.
- Browser DOM snapshot confirmed `Reviewer visuals`, `Price distribution`, `Median price by rooms`, `Listing map`, and `OpenStreetMap contributors` rendered with no browser error logs.
- GitHub Actions `ci` run `26904040922` passed for behavior SHA `6cb103b`; docs-audit run `26904605045` also passed for `66bb5be`.
- GitNexus remains indexed only through `realtyscope-phase6-index` at `30bce998`; create/refresh a Phase 7 index before using graph impact for future code edits, or explicitly treat the graph as stale.

## Requirement Coverage Snapshot

The assignment source `MISIS_2025/season_2/Описание проекта.html` expects a Docker-launched data service with automatic collection, PostgreSQL, EDA, ML prediction, FastAPI/Swagger, Streamlit filters/charts/pages, monitoring/logs, MLflow, Redis, CI/tests, and course documentation. RealtyScope now covers the foundation and most grade-5 stack evidence. Remaining gaps are mostly reviewer visibility and honest final polish:

- trend and forecast-vs-actual language must stay conservative unless observation freshness is revalidated;
- table pagination/tabs and final Streamlit layout can be clearer;
- demo script/runbook exists and should be used for final smoke evidence;
- Domclick schedule should remain daily unless the data value of a second daily run is proven and the user approves the operational change;
- final merge back to `main` needs fresh local, Docker, Browser, and GitHub Actions evidence.

## Task 1: Requirement Traceability And Status Sync

**Files:**
- Modify: `README.md`
- Modify: `docs/project-status.md`
- Modify: `docs/course-guidance/realtyscope-user-story-traceability.md`
- Modify: `docs/course-guidance/realtyscope-stack-architecture-traceability.md`
- Create: `docs/superpowers/plans/2026-06-03-realtyscope-course-readiness-finish-plan.md`

- [ ] Update README so Phase 7.2/7.3 filters, charts, and map are no longer described as missing.
- [ ] Update `docs/project-status.md` with the latest Phase 7 commit and CI run.
- [ ] Update user-story traceability for US-04, US-05, US-07, and the Phase 7 contribution section.
- [ ] Update stack traceability for Streamlit filters/charts/map and remaining frontend gaps.
- [ ] Run `git diff --check`, `ruff check .`, `ruff format --check .`, and `pytest -p no:cacheprovider`.
- [ ] Commit as `docs: refresh course readiness plan`, push, and wait for GitHub Actions `ci` to pass.

## Task 2: Demo Script And Reviewer Runbook

**Files:**
- Create: `docs/demo-script.md`
- Create: `docs/demo-script.vi.md` if the Vietnamese companion is useful for handoff.
- Modify: `README.md`
- Modify: `docs/project-status.md`

- [x] Write a linear demo path: start Docker, open Swagger, inspect `/health`, `/data`, `/model/metadata`, `/monitoring/status`, open Streamlit, apply filters, inspect charts/map, run prediction, open MLflow, prove Redis cache, and cleanly stop services.
- [x] Include exact WSL Docker commands because PowerShell does not have `docker` in PATH on this machine.
- [x] Include destructive cleanup warnings: do not run `docker compose down -v` or volume prune unless the user explicitly wants data/model artifacts deleted.
- [x] Verify docs links from README.
- [x] Run the standard local checks and push/CI.

## Task 3: Last-Update Monitoring And Domclick Schedule Decision

**Files:**
- Modify: `services/api/app/main.py`
- Modify: `services/api/app/schemas.py` if response schema needs explicit fields.
- Modify: `services/streamlit/api_client.py`
- Modify: `services/streamlit/app.py`
- Modify: `tests/test_api_monitoring.py`
- Modify: `tests/test_streamlit_api_client.py`
- Modify: `tests/test_streamlit_scaffold.py`
- Modify: `docs/project-status.md`
- Modify: `docs/operations/domclick-scheduled-batch-ingestion.md`
- Modify: `docs/operations/domclick-scheduled-batch-ingestion.vi.md`

- [x] Write RED API tests requiring `latest_success_started_at`, `latest_success_finished_at`, and `latest_success_record_count` or equivalent clear fields in `/monitoring/status`.
- [x] Implement the smallest schema/query change that exposes last successful collection time without breaking existing fields.
- [x] Write Streamlit client/scaffold tests requiring visible last-success text.
- [x] Render the last successful collection time in the Streamlit monitoring section.
- [x] Check current schedule evidence. Keep the installed schedule daily unless fresh data proves a second daily run improves trend evidence and the user approves changing the real scheduled task.
- [x] If only documenting the decision, commit docs/code normally. If changing the actual Windows scheduled task, ask the user immediately before the state-changing command.
- [x] Verify with local tests, Docker smoke, and Browser check.
- [x] Push and wait for CI.

## Task 4: Streamlit Final UX Polish

**Files:**
- Modify: `services/streamlit/app.py`
- Modify or create focused helpers under `services/streamlit/`
- Modify: `tests/test_streamlit_scaffold.py`
- Modify or create focused Streamlit helper tests under `tests/`
- Modify: `docs/project-status.md`

- [ ] Decide whether tabs are needed for demo clarity: overview, data explorer, visuals, prediction, monitoring/model.
- [ ] If tabs are added, write scaffold tests first for expected tab labels and section ownership.
- [ ] Add table pagination or a clearer row-window control only if it improves the reviewer workflow beyond the current row limit.
- [ ] Add richer charts only when they explain a course requirement: data quality, model metrics, or conservative observation trends.
- [ ] Keep OSM attribution visible for maps and OSM-derived views.
- [ ] Browser-check desktop and a mobile/narrow viewport for text fitting and no incoherent overlap.
- [ ] Rebuild Streamlit image after code changes because compose does not bind-mount source.
- [ ] Verify with tests, Docker smoke, Browser, push, and CI.

## Task 5: Final Data And Runtime Evidence

**Files:**
- Modify: `docs/project-status.md`
- Modify: `docs/demo-script.md`
- Modify: README if final command/evidence changed.

- [ ] Re-run fresh data-readiness commands against the runtime database.
- [ ] Re-run API smoke for `/health`, `/docs`, `/data`, `/predict`, `/model/metadata`, and `/monitoring/status`.
- [ ] Re-run Redis proof for one filtered `/data` call and document the cache key pattern.
- [ ] Re-run MLflow/model evidence check and keep the baseline caveat explicit.
- [ ] Re-run Streamlit Browser smoke after final UI changes.
- [ ] Update status docs with fresh counts and evidence dates.
- [ ] Run standard checks, push, and CI.

## Task 6: Final Merge And Submission Checkpoint

**Files:**
- Modify only docs if the final merge produces new evidence to record.

- [ ] Ensure `phase7-course-readiness-polish` is clean and CI-green.
- [ ] Decide whether to merge into `main` directly or via PR, based on branch state and user preference.
- [ ] Preserve old phase branches as milestones.
- [ ] Merge to `main`, push, and wait for GitHub Actions on `main` to pass.
- [ ] Save a mem0 checkpoint with final commit SHA, CI run IDs, local checks, Docker/Browser evidence, and remaining caveats.

## Verification Gate For Every Slice

Run these before any completion claim unless the slice is explicitly docs-only and the user approves a narrower check:

```powershell
git diff --check
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m ruff format --check .
.\.venv\Scripts\python.exe -m pytest -p no:cacheprovider
```

For runtime/UI slices also run:

```powershell
wsl -d Ubuntu -- bash -lc "cd /mnt/e/Магистр/2-курс/python/RealtyScope && docker compose -p realtyscope ps"
wsl -d Ubuntu -- bash -lc "curl -sS -o /dev/null -w '%{http_code}' http://localhost:8501"
```

Use Browser plugin for Streamlit UI evidence and wait for GitHub Actions after every push.
