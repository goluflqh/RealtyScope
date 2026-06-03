# RealtyScope Project Status

Date: 2026-06-03
Branch: `phase7-course-readiness-polish`
Base commit: `30bce998f1c3e5a6d13085d08a0b3692a52234a2`

This document is the operating status board for the final course-readiness work. It consolidates the assignment requirements, implemented phase evidence, current gaps, and the next smaller workstreams so future sessions do not have to reload the full history.

## Branch And CI State

| Item | Status | Evidence |
| --- | --- | --- |
| Phase 6 branch | Preserved as milestone | `phase6-mlflow-redis-readiness` remains on local and remote at `30bce998...`. |
| Base branch | Merged | `main` was fast-forwarded from `c6e422b` to `30bce998...` on 2026-06-03. |
| New Phase 7 branch | Active | `phase7-course-readiness-polish` was created from the updated `main` and pushed to origin. |
| GitHub Actions on `main` | Passing | `ci` run `26893951979`, SHA `30bce998...`, conclusion `success`. |
| GitHub Actions on Phase 7 | Passing | `ci` run `26893965255`, SHA `30bce998...`, conclusion `success`. |
| Local verification before merge | Passing | `.venv` ruff check passed, ruff format check found 69 formatted files, pytest reported `125 passed in 13.06s` with `-p no:cacheprovider`. |
| GitNexus freshness | Fresh for base SHA | `realtyscope-phase6-index` is indexed at `30bce998...`. Refresh or create a Phase 7 index before relying on graph impact after new Phase 7 commits. |

## Phase 7.1 Runtime Audit Snapshot

Fresh checks from 2026-06-03 on `phase7-course-readiness-polish`:

| Check | Result | Evidence |
| --- | --- | --- |
| Docker runtime location | WSL2 Docker, not PowerShell PATH | PowerShell has no `docker` command; WSL reports Docker `29.2.1` and Compose `v5.1.0`. |
| Compose services | Running | `db`, `redis`, `api`, and `streamlit` are healthy; `mlflow` is up on port `5000`. |
| API health and docs | HTTP 200 | `/health`, `/docs`, `/data?limit=3`, `/model/metadata`, and `/monitoring/status` responded from localhost. |
| Data status | Healthy | Runtime DB has `3019` listings, `3191` raw listings, `3` ingestion runs, `0` rejected rows, and latest run status `success`. |
| Data readiness | Improved since older docs | `3019` listings, `3989` observations, `970` listings with multiple observations, `26` price changes, coordinate coverage `1.0`, ML-ready coverage `1.0`. |
| ML artifact | Ready | `/model/metadata` reports `realtyscope-price-model`, `baseline_ridge_v2_non_leaky`, `ml_features_v2_non_leaky`, and 23 features. |
| Streamlit browser check | Loads and renders data | Browser shows `RealtyScope`, `Listings 3019`, `ML-ready 3019`, `Rejected 0`, `Runs 3`, latest ingestion success, and model version `baseline_ridge_v2_non_leaky`. |
| Current visible UI gap | Still present | Streamlit works, but remains a single-page dashboard with limited row-count control and no rich charts/maps/filter workflow yet. |

## Course Requirement Status

Source requirements: `E:\Магистр\2-курс\python\MISIS_2025\season_2\Описание проекта.html`, `Примерный план семестра.htm`, and repository traceability docs under `docs/course-guidance/`.

| Requirement | Current status | Evidence | Remaining Phase 7 gap |
| --- | --- | --- | --- |
| One-command Docker project | Runtime smoke green, final re-smoke still required | WSL `docker compose -p realtyscope ps` shows `db`, `redis`, `api`, and `streamlit` healthy, with `mlflow` up. Phase 6 also verified `docker compose -p realtyscope up --build -d`. | Re-run final Docker smoke after future Phase 7 UI/docs changes and add safe cleanup instructions for containers, volumes, raw data, and model artifacts. |
| Automatic data collection | Implemented as bounded batch | Domclick Chrome/CDP capture, scheduled batch runner, Windows scheduled task, and ingestion status command exist. Current task is daily at `00:00` Moscow and last result was `0`. | Decide whether to keep daily or add a second run only after checking freshness value versus anti-abuse risk and duplicate-observation semantics. |
| PostgreSQL storage and Alembic | Implemented | SQLAlchemy 2.0 models, Alembic migrations, persisted listings, observations, OSM features, ingestion runs, and app logs. | Fresh data count check should be part of final readiness, not inferred from old docs. |
| Data volume and quality | Runtime audit green | Fresh data-readiness reports `3019` listings, `3989` observations, `970` listings with multiple observations, `26` price changes, coordinate coverage `1.0`, ML-ready coverage `1.0`, and `0` rejected rows. | Use these fresh numbers in the demo, then re-run after any new ingestion or DB reset. |
| EDA and visual conclusions | Partial but data is improving | Phase 4 EDA docs cover cross-sectional data quality; fresh runtime data now has multiple observations for `970` listings and `26` detected price changes. | Add reviewer-facing charts in Streamlit. Trend conclusions can become less conservative only after validating observation freshness and repeated capture semantics. |
| ML baseline and metrics | Implemented as honest baseline | `baseline_ridge_v2_non_leaky` removes latest-price leakage and uses grouped validation; Phase 6 adds Docker-backed MLflow evidence. | The model is still a baseline appraisal model. Forecast-vs-actual and richer model trust need repeated observations and/or final UI explanation. |
| MLflow MLOps | Implemented for baseline evidence | MLflow run `4999892d2d92402ab78e1209203c338e`, registered model `realtyscope-price-model`, version `3`, and persisted artifacts. | Final demo should show MLflow URL and explain what is baseline versus final-quality claim. |
| FastAPI and Swagger | Partial but usable | Runtime HTTP checks returned 200 for `/health`, `/docs`, `/data?limit=3`, `/model/metadata`, and `/monitoring/status`; tests cover contracts. | Add richer filters/search parameters if Phase 7 upgrades the Data Explorer. Verify Swagger in browser during final smoke. |
| Redis cache | Implemented for read path | Redis-backed `/listings` and `/data` read path is code/test-covered. | Include a runtime check or demo note proving cache path is active in Docker. |
| Streamlit dashboard | Partial and highest visible gap | Browser check confirms the app renders runtime data: `3019` listings, `3019` ML-ready rows, `0` rejected rows, `3` runs, and model version `baseline_ridge_v2_non_leaky`. | Add clearer multipage/tabs, charts, maps or geo summary, filters/search/table ergonomics, last-update display, and visible OSM attribution when maps/OSM-derived views are shown. |
| Monitoring/logs | Partial | `/monitoring/status` reports environment `docker`, latest ingestion run success, `2000` normalized records, and recent errors `0`; Streamlit displays the monitoring slice. | Populate/display runtime logs more consistently and make last successful collection time obvious. |
| Documentation and demo | Partial | README, course guidance docs, ML docs, operation docs, and this status board exist. | Add a concise demo script/runbook and safe storage cleanup instructions. Keep README current with Phase 6 and Phase 7 evidence. |

## Domclick Schedule Decision

Current evidence:

- Scheduled task name: `RealtyScope Domclick Scheduled Batch`.
- Trigger: daily, `StartBoundary = 2026-06-02T00:00:00+03:00`, `DaysInterval = 1`.
- Last run: `03.06.2026 0:00:00`, result `0`.
- Next run: `04.06.2026 0:00:00`.

Recommendation for now: keep the installed schedule at once per day until Phase 7.1 validates runtime data freshness. A second run per day can help trend evidence only if it either captures fresh data or intentionally records a new observation timestamp without misleading the reviewer. It also increases Domclick access pressure and duplicate-report noise. If adopted, prefer two explicit daily triggers such as `00:00` and `12:00` Moscow, not an infinite loop.

## Phase 7 Workstreams

Phase 7 should be split into small, independently verifiable slices. Do not batch all UI, data, docs, and ops changes into one commit.

### Phase 7.0: Status And README Sync

Goal: make the project state readable and management-friendly.

- Create this status board.
- Update README so it no longer presents stale Phase 4 caveats as the current state.
- Link the status board from README.
- Verify docs-only slice with ruff, format check, pytest, and CI after commit/push.

### Phase 7.1: Runtime And Data Readiness Audit

Goal: prove the current data/runtime state from fresh commands.

- [x] Re-run data-readiness/status commands against the runtime DB.
- [x] Re-run Docker Compose smoke from the current branch.
- [x] Verify API health, Swagger, Streamlit, MLflow reachability, and model artifact availability.
- [ ] Add safe cleanup docs for containers, named volumes, raw snapshots, reports, and model artifacts. Explicitly warn before destructive volume/data deletion.
- [ ] Add an explicit Redis runtime evidence command or demo note if the final reviewer script should prove cache behavior, not only endpoint behavior.

### Phase 7.2: Data Explorer Filters

Goal: satisfy the assignment's filter/search/table story.

- Add tested API query parameters for useful filters such as price range, area range, rooms, source, and text/address search.
- Update Streamlit with sidebar controls and a clearer paginated table view.
- Verify with API tests, Streamlit client tests, Docker smoke, and browser check.

### Phase 7.3: Reviewer-Facing Charts And Map

Goal: make the project visually explainable during demo.

- Add charts for price distribution, price per square meter, rooms/area breakdown, data quality, and model metrics.
- Add a map or geo summary only when OSM attribution is visible.
- Add trend/observation visuals only with conservative wording if data still lacks meaningful repeated observations.
- Verify text fitting, no overlap, and browser screenshots across desktop/mobile if UI layout changes substantially.

### Phase 7.4: Demo Script And Course Submission Polish

Goal: make the defense path easy to follow.

- Add a concise demo script: clone/setup, Docker start, seed/verify data, open API docs, open Streamlit, run prediction, inspect MLflow.
- Add final README runbook links and caveats.
- Decide and document whether Domclick remains daily or moves to twice daily.
- Confirm GitHub Actions, local checks, Docker smoke, and browser check are green.

## Success Check For Final Course Readiness

The final readiness claim should require all of the following fresh evidence:

- `ruff check .` exits 0.
- `ruff format --check .` exits 0.
- Full pytest exits 0, using the Windows cache workaround while `.pytest_cache` remains permission-broken.
- Docker Compose starts the runtime services from the repo without temp build contexts.
- API `/health`, `/docs`, `/data`, `/predict`, `/model/metadata`, and `/monitoring/status` are usable.
- Streamlit loads in browser and shows data, filters/charts, prediction, monitoring, and model insights without layout overlap.
- MLflow contains the registered baseline model evidence or the docs explain exactly how to reproduce it.
- GitHub Actions is green on the active branch and, after merge, on `main`.
- Final docs explain what is implemented, what remains baseline/partial, and how to clean up storage safely.
