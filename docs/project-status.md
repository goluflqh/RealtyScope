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
| GitHub Actions on Phase 7 | Passing | Latest `ci` evidence is run `26906383719` for SHA `83ad3e1...`, conclusion `success`. Earlier Phase 7 runs for `6cb103b`, `66bb5be`, and `a5e2583` also passed. |
| Local verification before merge | Passing | Phase 6 merge checks passed with `125 passed`. Latest committed UI slice passed `git diff --check`, `ruff check .`, `ruff format --check .`, and full pytest `137 passed` with `-p no:cacheprovider`. |
| Latest runtime/UI behavior commit | Pushed and CI-green | `83ad3e1 feat: polish streamlit demo navigation` adds tabbed Streamlit navigation, sidebar page control, and real `/data` offset pagination. |
| GitNexus freshness | Stale for Phase 7 code | `realtyscope-phase6-index` is indexed at `30bce998...`, while active branch is now beyond that commit. Refresh or create a Phase 7 index before relying on graph impact after new Phase 7 commits. |

## Phase 7.1 Runtime Audit Snapshot

Fresh checks from 2026-06-03 on `phase7-course-readiness-polish`:

| Check | Result | Evidence |
| --- | --- | --- |
| Docker runtime location | WSL2 Docker, not PowerShell PATH | PowerShell has no `docker` command; WSL reports Docker `29.2.1` and Compose `v5.1.0`. |
| Compose services | Running | `db`, `redis`, `api`, and `streamlit` are healthy; `mlflow` is up on port `5000`. |
| API health, docs, and prediction | HTTP 200 | `/health`, `/docs`, `/data?limit=3`, filtered `/data?limit=3&offset=0&rooms=2&min_price_rub=10000000`, `/predict`, `/model/metadata`, and `/monitoring/status` responded from localhost. The filtered data smoke returned `957` total rows; `/predict` returned `26,038,199.74` RUB for the default demo vector. |
| Redis runtime cache | Verified | Calling filtered `/data?limit=3&offset=0&rooms=2&min_price_rub=10000000` returned HTTP `200`; Redis then had key `realtyscope:listings:v1:limit=3:offset=0:min_price_rub=10000000:rooms=2`, `EXISTS=1`, TTL `22`, and payload length `1498` bytes. |
| Data status | Healthy | Runtime DB has `3019` listings, `3191` raw listings, `3` ingestion runs, `0` rejected rows, and latest run status `success`. |
| Data readiness | Improved since older docs | `3019` listings, `3989` observations, `970` listings with multiple observations, `26` price changes, coordinate coverage `1.0`, ML-ready coverage `1.0`. |
| ML artifact and MLflow | Ready | `/model/metadata` reports active model `realtyscope-price-model`, `baseline_ridge_v2_non_leaky`, `ml_features_v2_non_leaky`, 23 features, and `rows_total=3019`; MLflow run `4999892d2d92402ab78e1209203c338e` is `FINISHED`, and registered model version `3` is `READY`. |
| Streamlit browser check | Loads and renders data | Browser DOM smoke shows `RealtyScope`, Phase 7 caption, all five tabs, sidebar `Page`, `Listings 3019`, `ML-ready 3019`, `Rejected 0`, `Runs 3`, and no warning/error logs. Earlier tab click smoke also verified Data Explorer row-window caption, Visuals charts/map attribution, Prediction output, and Monitoring last-success/model insight sections. |
| Current visible UI gap | Reduced | Streamlit works for the course demo with filters, reviewer-facing charts, coordinate map slice, tabs, and a real page/offset control. Optional narrow-viewport/screenshot evidence remains useful if the reviewer asks for responsive proof. |

## Course Requirement Status

Source requirements: `E:\Магистр\2-курс\python\MISIS_2025\season_2\Описание проекта.html`, `Примерный план семестра.htm`, and repository traceability docs under `docs/course-guidance/`.

| Requirement | Current status | Evidence | Remaining Phase 7 gap |
| --- | --- | --- | --- |
| One-command Docker project | Runtime smoke green | WSL `docker compose -p realtyscope ps` shows `db`, `redis`, `api`, and `streamlit` healthy, with `mlflow` up. Phase 6 verified `docker compose -p realtyscope up --build -d`; Phase 7 re-smokes run against the same Compose project. | Re-run final Docker smoke once more after the final merge decision; safe cleanup instructions already warn before deleting containers, volumes, raw data, or model artifacts. |
| Automatic data collection | Implemented as bounded batch | Domclick Chrome/CDP capture, scheduled batch runner, Windows scheduled task, and ingestion status command exist. Current task is daily at `00:00` Moscow and last result was `0`. | Decide whether to keep daily or add a second run only after checking freshness value versus anti-abuse risk and duplicate-observation semantics. |
| PostgreSQL storage and Alembic | Implemented | SQLAlchemy 2.0 models, Alembic migrations, persisted listings, observations, OSM features, ingestion runs, and app logs. | Fresh data count check should be part of final readiness, not inferred from old docs. |
| Data volume and quality | Runtime audit green | Fresh data-readiness reports `3019` listings, `3989` observations, `970` listings with multiple observations, `26` price changes, coordinate coverage `1.0`, ML-ready coverage `1.0`, and `0` rejected rows. | Use these fresh numbers in the demo, then re-run after any new ingestion or DB reset. |
| EDA and visual conclusions | Partial but data is improving | Phase 4 EDA docs cover cross-sectional data quality; fresh runtime data now has multiple observations for `970` listings and `26` detected price changes. Phase 7.3 adds reviewer-facing price distribution and room-summary charts. | Trend conclusions can become less conservative only after validating observation freshness and repeated capture semantics. |
| ML baseline and metrics | Implemented as honest baseline | `baseline_ridge_v2_non_leaky` removes latest-price leakage and uses grouped validation; Phase 6 adds Docker-backed MLflow evidence. | The model is still a baseline appraisal model. Forecast-vs-actual and richer model trust need repeated observations and/or final UI explanation. |
| MLflow MLOps | Implemented for baseline evidence | MLflow run `4999892d2d92402ab78e1209203c338e`, registered model `realtyscope-price-model`, version `3`, and persisted artifacts. | Final demo should show MLflow URL and explain what is baseline versus final-quality claim. |
| FastAPI and Swagger | Usable, filter slice added | Runtime HTTP checks returned 200 for `/health`, `/docs`, `/data?limit=3`, filtered `/data`, `/predict`, `/model/metadata`, and `/monitoring/status`; tests cover contracts. Phase 7.2 adds `/data` and `/listings` filters for price range, area range, rooms, source, and text search. | Keep future query additions tested. Swagger is available at `/docs`; a browser click-through is optional unless the reviewer specifically asks. |
| Redis cache | Implemented and runtime-verified for filtered read path | Redis-backed `/listings` and `/data` read path is code/test-covered; Phase 7 runtime proof observed the filter-specific key `realtyscope:listings:v1:limit=3:offset=0:min_price_rub=10000000:rooms=2` after a live `/data` call. | Repeat the short Redis proof during the live demo if the reviewer asks for cache behavior evidence. |
| Streamlit dashboard | Implemented for course demo scope | Browser check confirms the app renders runtime data: `3019` listings, `3019` ML-ready rows, `0` rejected rows, `3` runs, model version `baseline_ridge_v2_non_leaky`, Data Explorer filters/page control, reviewer charts/map, prediction, monitoring, and model insights. | Optional richer metric/trend charts can be added only if they improve the defense without overstating repeated-observation maturity. |
| Monitoring/logs | Clearer last-success display, logs still partial | `/monitoring/status` reports environment `docker`, latest ingestion run success, `2000` normalized records, latest successful ingestion details, and recent errors `0`; Streamlit displays the last successful collection timestamp/source/record count. | Populate runtime `app_logs` more consistently if deeper operations evidence is needed. |
| Documentation and demo | Stronger, final smoke still required | README, course guidance docs, ML docs, operation docs, this status board, safe storage cleanup docs, and demo scripts exist. | Keep README/status current after remaining Phase 7 changes and use the demo script during final smoke. |

## Domclick Schedule Decision

Current evidence checked again on 2026-06-03:

- Scheduled task name: `RealtyScope Domclick Scheduled Batch`.
- Trigger: daily, `StartBoundary = 2026-06-02T00:00:00+03:00`, `DaysInterval = 1`.
- Last run: `03.06.2026 0:00:00`, result `0`.
- Next run: `04.06.2026 0:00:00`.

Decision for now: keep the installed schedule at once per day. A second run per day can help trend evidence only if it captures meaningfully fresh data or intentionally records a new observation timestamp without misleading the reviewer. It also increases Domclick access pressure and duplicate-report noise. If adopted later, prefer two explicit daily triggers such as `00:00` and `12:00` Moscow, not an infinite loop, and ask before changing the real scheduled task.

## Phase 7 Workstreams

Phase 7 should be split into small, independently verifiable slices. Do not batch all UI, data, docs, and ops changes into one commit.

Detailed finish plan after the latest Phase 7 runtime/UI evidence slice: `docs/superpowers/plans/2026-06-03-realtyscope-course-readiness-finish-plan.md`.

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
- [x] Add safe cleanup docs for containers, named volumes, raw snapshots, reports, and model artifacts. Explicitly warn before destructive volume/data deletion.
- [x] Add an explicit Redis runtime evidence command or demo note if the final reviewer script should prove cache behavior, not only endpoint behavior.

### Phase 7.2: Data Explorer Filters

Goal: satisfy the assignment's filter/search/table story.

- [x] Add tested API query parameters for useful filters such as price range, area range, rooms, source, and text/address search.
- [x] Update Streamlit with sidebar controls wired through the API client.
- [x] Add a clearer row-window view with a sidebar `Page` control backed by `/data` offset.
- [x] Verify with API tests, Streamlit client tests, Docker smoke, and browser check.

### Phase 7.3: Reviewer-Facing Charts And Map

Goal: make the project visually explainable during demo.

- [x] Add first reviewer-facing charts for price distribution and median price by rooms.
- [x] Add a coordinate map slice with visible OpenStreetMap attribution and no live OSM/Overpass calls.
- [ ] Add richer data-quality/model metric charts if needed for final demo flow.
- [ ] Add trend/observation visuals only with conservative wording if data still lacks meaningful repeated observations.
- [x] Verify desktop Browser DOM for tabs, data, visuals, prediction, monitoring, and no warning/error logs.
- [ ] Add narrow/mobile screenshot evidence only if final submission needs responsive proof; in-app Browser screenshot capture timed out during the Phase 7 UI slice.

### Phase 7.4: Demo Script And Course Submission Polish

Goal: make the defense path easy to follow.

- [x] Add a concise demo script: Docker start, verify data/API, open API docs, open Streamlit, run prediction, inspect MLflow, prove Redis, and stop services safely.
- [x] Add README runbook links and safe cleanup caveats.
- [x] Decide and document that Domclick remains daily for now; do not add a second daily trigger without fresh data value evidence and user approval.
- [ ] Confirm GitHub Actions, local checks, Docker smoke, and browser check are green after this final docs/evidence slice and before merge.

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
