# RealtyScope Phase 9 Evidence Snapshot

Date: 2026-06-20
Branch: `docs/phase9-final-readiness-20260620`
Purpose: record current Phase 9 branch/runtime evidence without merging or pushing any workstream.

This snapshot is intentionally conservative. It records what was verified locally and what still needs integration, CI, push, PR, or merge approval. It does not replace the clean workstream plan in `docs/superpowers/plans/2026-06-20-realtyscope-phase9-clean-workstreams-plan.md`.

## Current Git Policy

- Local `main` is clean but ahead of `origin/main` by 5 mixed commits. Do not push that mixed `main`.
- Phase 9 work remains split across dedicated branches/worktrees.
- No branch has been pushed, merged, deleted, or rewritten in this Phase 9 snapshot.
- No live Domclick capture was run and no scheduler trigger was changed during these checks.
- GitNexus impact evidence was used only after branch-specific index freshness was verified.

## Phase 9 Integration / PR Governance Gate

This snapshot records an order of operations only. It does not authorize pushing, opening PRs, merging, deleting branches, dropping stashes, repointing `main`, running live Domclick capture, or changing scheduler triggers.

Non-UI workstreams must be completed, freshly verified, and professionally reviewable before any push/PR/merge proposal. The recovered UI branch can remain deferred until the data/backend/MLOps/API/docs path is correct and approved.

Recommended PR order after explicit approval:

1. `ops/domclick-scheduler-validated-20260619` at `e62b068` for Phase 8 scheduler publication/readiness.
2. `data/teammate-json-import-20260618` at `5db4a44` for teammate JSON import readiness.
3. `ops/postgres-guardrails-20260618` at `f5464c1` for PostgreSQL storage/volume guardrails.
4. `ml/model-promotion-workflow` at `ebd89ec` for Phase 9B MLOps dry-run compare, gated promote/reject, rollback/selection behavior, CLI, and tests.
5. `api/phase9-selected-model-monitoring-20260620` at `7e9c65a` for Phase 9C selected-model metadata in API/monitoring. This must follow Phase 9B because it depends on the model-selection code.
6. `docs/phase9-final-readiness-20260620` for final evidence/status/demo-readiness docs after the non-UI code branches are settled.
7. `ui/recovered-real-data-dashboard-20260620` at `b6922b7`, deferred until non-UI work is integrated or explicitly prioritized. Continue UI only from this recovered real-data branch, not from `ui/realtyscope-ultimate-redesign`.

Pre-push/PR gate for each non-UI branch:

- Branch is clean, on the intended worktree, and diff scope matches the workstream.
- Targeted tests and formatting/lint checks are rerun fresh from that branch.
- `git diff --check` is clean against the intended base.
- For non-trivial code, branch-specific GitNexus index freshness is rechecked against `git rev-parse HEAD`, then `detect_changes` is summarized.
- API route or response-shape changes also require `api_impact`, `route_map`, and/or `shape_check` as applicable after index freshness is confirmed.
- CI expectations are written before PR; GitHub Actions must be green before any merge.
- No fake/sample UI data is used as production evidence.
- No mixed local `main` is pushed.

Integration branch gate, if the user later approves assembling one:

- Build it only after the PR order is chosen.
- Rerun full `ruff check .`, `ruff format --check .`, and `pytest -q -p no:cacheprovider`.
- Rerun Docker/API/PostgreSQL/Redis runtime smoke, selected-model API smoke, and read-only scheduler evidence check.
- Update docs from fresh evidence only.
- Recheck GitNexus freshness after every non-trivial commit or branch switch before impact analysis.

## Latest Non-UI Pre-PR Audit: 2026-06-20

This audit refreshed evidence for the non-UI branches only. It did not push, open PRs, merge, delete branches, change scheduler triggers, or run live Domclick capture.

Branch shape and whitespace checks:

- `ops/domclick-scheduler-validated-20260619` remained clean/ahead 3; diff scope stayed limited to scheduler docs/script/capture/scheduled-batch/tests; `git diff --check origin/main..HEAD` exited 0.
- `data/teammate-json-import-20260618` remained clean/ahead 1; diff scope stayed limited to `teammate_import.py` and `tests/test_teammate_import.py`; `git diff --check origin/main..HEAD` exited 0.
- `ops/postgres-guardrails-20260618` remained clean/ahead 1; diff scope stayed limited to `docker-compose.yml`; `git diff --check origin/main..HEAD` exited 0; `wsl docker compose -f /mnt/c/Users/lequa/.config/superpowers/worktrees/RealtyScope/postgres-guardrails-20260618/docker-compose.yml config --quiet` exited 0.
- `ml/model-promotion-workflow` remained clean/ahead 4; diff scope stayed limited to MLOps docs/code/tests; `git diff --check origin/main..HEAD` exited 0.
- `api/phase9-selected-model-monitoring-20260620` remained clean; diff vs `ebd89ec` stayed limited to API metadata/settings/tests; `git diff --check ebd89ec..HEAD` exited 0.

Fresh local checks:

- Phase 8 scheduler: `python -m ruff check src/realtyscope/ingestion tests/test_domclick_chrome_capture.py tests/test_domclick_scheduled_batch.py` passed; `python -m ruff format --check src/realtyscope/ingestion tests/test_domclick_chrome_capture.py tests/test_domclick_scheduled_batch.py` reported 11 files already formatted; `python -m pytest tests/test_domclick_chrome_capture.py tests/test_domclick_scheduled_batch.py -q -p no:cacheprovider` passed 22 tests.
- Phase 9A teammate import: `python -m ruff check src/realtyscope/ingestion/teammate_import.py tests/test_teammate_import.py` passed; `python -m ruff format --check src/realtyscope/ingestion/teammate_import.py tests/test_teammate_import.py` reported 2 files already formatted; `python -m pytest tests/test_teammate_import.py -q -p no:cacheprovider` passed 4 tests.
- Phase 9B MLOps: `python -m ruff check src/realtyscope/ml tests/test_ml_model_compare.py tests/test_ml_model_selection.py tests/test_ml_promotion_cli.py tests/test_ml_training.py` passed; `python -m ruff format --check src/realtyscope/ml tests/test_ml_model_compare.py tests/test_ml_model_selection.py tests/test_ml_promotion_cli.py tests/test_ml_training.py` reported 10 files already formatted; `python -m pytest tests/test_ml_model_compare.py tests/test_ml_model_selection.py tests/test_ml_promotion_cli.py tests/test_ml_training.py -q -p no:cacheprovider` passed 17 tests.
- Phase 9C API/monitoring: `python -m ruff check services/api/app/main.py src/realtyscope/config.py src/realtyscope/ml tests/test_api_monitoring.py tests/test_api_prediction_contract.py tests/test_config.py tests/test_ml_model_selection.py tests/test_ml_promotion_cli.py` passed; `python -m ruff format --check services/api/app/main.py src/realtyscope/config.py src/realtyscope/ml tests/test_api_monitoring.py tests/test_api_prediction_contract.py tests/test_config.py tests/test_ml_model_selection.py tests/test_ml_promotion_cli.py` reported 13 files already formatted; `python -m pytest tests/test_api_monitoring.py tests/test_api_prediction_contract.py tests/test_config.py tests/test_ml_model_selection.py tests/test_ml_promotion_cli.py -q -p no:cacheprovider` passed 18 tests with the known Starlette/httpx deprecation warning.

Fresh GitNexus impact evidence after explicit index freshness checks:

- `realtyscope-ops-domclick-scheduler-validated-20260619-index` matched branch head `e62b068697ba965ecfb6ae8976fb04ae6359bc96`; `detect_changes` reported risk `critical`, changed files 9, changed symbols 105, affected processes 26, with affected flows in Domclick capture/scheduled-batch extraction paths.
- `realtyscope-ml-model-promotion-workflow-index` matched branch head `ebd89ec2870160c71c64cd7db4ef12eec8777482`; `detect_changes` reported risk `critical`, changed files 7, changed symbols 110, affected processes 18, with affected flows in MLOps CLI compare, selection, promote, rollback, and report-writing paths.
- `realtyscope-api-phase9-selected-model-monitoring-20260620-index` matched branch head `7e9c65acec820f9bd1c778c05f6767e7802b3c06`; `detect_changes` reported risk `critical`, changed files 4, changed symbols 13, affected processes 25, focused on model metadata, monitoring status, and additive `Settings.active_model_selection_path` flows.
- For `/model/metadata` and `/monitoring/status`, `route_map` found no direct consumers, `api_impact` reported `directConsumers=0` and route risk `LOW`, and `shape_check` reported no routes with both response shapes and consumers.

Fresh read-only runtime evidence:

- Windows Task Scheduler read-only check: `LastRunTime=2026-06-20 00:00:00`, `LastTaskResult=0`, `NextRunTime=2026-06-21 00:00:00`, `NumberOfMissedRuns=0`.
- Scheduler runtime artifacts are in the main checkout runtime data directory, not the scheduler worktree. `data/processed/runtime_logs/domclick-scheduled-task-20260619-000001.log` and `domclick-scheduled-task-20260620-000002.log` exist under the main checkout and show automatic batch success with `records_seen=2000`; the 2026-06-20 report `data/processed/domclick_reports/domclick-20260619T211550-280768Z.json` records `status=success`, `normalized_count=2000`, `raw_count=2000`, and `records_seen=2000`.
- Existing local API runtime on `127.0.0.1:8000` returned `/health` ok, `/data?limit=3&offset=0` with real PostgreSQL `total=14755`, `/monitoring/status` with `listings_total=14755`, `ml_ready_listings=14755`, latest successful ingestion `2026-06-19T21:15:54.106449+00:00`, model ready, feature count 23, and no recent errors. This is the current runtime service, not a new proof that the Phase 9C branch is running.
- Filtered `/data?limit=3&offset=0&rooms=2&min_price_rub=10000000` returned `total=4676`; Compose project `realtyscope` had healthy `db` and `redis`; Redis key `realtyscope:listings:v1:limit=3:offset=0:min_price_rub=10000000:rooms=2` had `EXISTS=1`, `TTL=47`, `STRLEN=1499`.

## Phase 9C Isolated Runtime Smoke: 2026-06-20

This smoke ran from worktree `C:\Users\lequa\.config\superpowers\worktrees\RealtyScope\api-phase9-selected-model-monitoring-20260620`, branch `api/phase9-selected-model-monitoring-20260620`, commit `7e9c65a`, on temporary port `127.0.0.1:8011`. It did not modify repository files, production model selection, scheduler triggers, or the existing API on `127.0.0.1:8000`.

Setup:

- Created `%TEMP%\realtyscope-phase9c-selected-model-smoke-fresh.json` with `realtyscope.ml.model_selection.save_selected_model`, so the JSON used the branch contract and UTF-8 without BOM.
- The selected model was `hist_gradient_boosting_candidate_v1`, feature version `ml_features_v2_non_leaky`, metrics `mae=19876543.21`, `rmse=42000000.0`, `r2=0.56`, with previous model `baseline_ridge_v2_non_leaky` and rollback available.
- First run proved selected-model loading but returned model `status=unavailable` because the default relative `ACTIVE_MODEL_ARTIFACT_PATH` did not resolve from the API worktree. The API process was stopped before the rerun.
- Second run set `ACTIVE_MODEL_ARTIFACT_PATH=E:\Магистр\2-курс\python\RealtyScope\data\processed\models\phase5\baseline_ridge_v2_non_leaky.joblib` and kept `ACTIVE_MODEL_SELECTION_PATH` pointed at the temp selected-model JSON.

Evidence from the second run:

- `/health` returned `status=ok` for `realtyscope-api` on port `8011`.
- `/model/metadata` returned `status=ready`, active `model_version=baseline_ridge_v2_non_leaky`, `feature_version=ml_features_v2_non_leaky`, `feature_count=23`, `error=null`, and `selected_model.model_version=hist_gradient_boosting_candidate_v1` with `rollback_available=true` and `previous_model_version=baseline_ridge_v2_non_leaky`.
- `/monitoring/status` returned `status=ok`, `data_quality.listings_total=14755`, `ml_ready_listings=14755`, latest successful ingestion finished `2026-06-19T21:15:54.106449+00:00`, and the same ready model plus selected-model payload.
- `/data?limit=1&offset=0` returned real PostgreSQL `total=14755`.
- Startup stderr contained scikit-learn `InconsistentVersionWarning` while unpickling the baseline artifact with local scikit-learn 1.6.1 versus artifact 1.8.0, but startup completed and requests returned HTTP 200.
- The temporary API process was stopped; no process with the temporary PIDs remained, and port `8011` had no listener after shutdown. The API branch remained clean.

## Verified Workstreams

| Workstream | Branch / commit | Fresh evidence | Remaining action |
| --- | --- | --- | --- |
| Phase 8 scheduler readiness | `ops/domclick-scheduler-validated-20260619` at `e62b068` | Branch clean; diff limited to scheduler docs/script/capture/scheduled-batch/tests; `ruff check` passed; `ruff format --check` passed; `pytest tests/test_domclick_chrome_capture.py tests/test_domclick_scheduled_batch.py -q -p no:cacheprovider` passed 22 tests. Windows Task Scheduler read-only check on 2026-06-20: `LastRunTime=2026-06-20 00:00:00`, `LastTaskResult=0`, `NextRunTime=2026-06-21 00:00:00`, `NumberOfMissedRuns=0`. Logs for 2026-06-19 and 2026-06-20 both show automatic batch success with 100 payload files and 2000 records seen. Fresh GitNexus index `realtyscope-ops-domclick-scheduler-validated-20260619-index` matched `e62b068`; `detect_changes` reported affected flows confined to Domclick capture/scheduled-batch extraction paths. | Ready for a reviewed push/PR decision only after explicit approval. |
| Phase 9A data/backend readiness | Existing split branches plus current runtime | `data/teammate-json-import-20260618` clean; diff limited to teammate import code/tests; `pytest tests/test_teammate_import.py -q -p no:cacheprovider` passed 4 tests. `ops/postgres-guardrails-20260618` clean; diff limited to `docker-compose.yml`; `git diff --check origin/main..HEAD` passed. Runtime API on `127.0.0.1:8000` returned `/health` ok and `/data?limit=3&offset=0` with real PostgreSQL `total=14755`. After starting Redis and restarting only local Uvicorn so FastAPI lifespan could create a Redis client, filtered `/data?limit=3&offset=0&rooms=2&min_price_rub=10000000` returned `total=4676`; Redis key `realtyscope:listings:v1:limit=3:offset=0:min_price_rub=10000000:rooms=2` had `EXISTS=1`, `TTL=49`, `STRLEN=1499`. `/monitoring/status` reported `listings_total=14755`, `ml_ready=14755`, latest successful ingestion finished `2026-06-19T21:15:54.106449+00:00`, model ready, feature count 23, recent errors 0. | Decide whether data/import and guardrail branches need separate PRs. Runtime proof depends on API being started after Redis is healthy. |
| Phase 9B MLOps promotion workflow | `ml/model-promotion-workflow` at `ebd89ec` | Branch clean; `pytest tests/test_ml_model_compare.py tests/test_ml_model_selection.py tests/test_ml_promotion_cli.py tests/test_ml_training.py -q -p no:cacheprovider` passed 17 tests; `ruff check src/realtyscope/ml ...` passed; `ruff format --check src/realtyscope/ml ...` passed. Fresh GitNexus index `realtyscope-ml-model-promotion-workflow-index` matched `ebd89ec`; `detect_changes` reported affected flows in MLOps CLI/compare/selection/rollback paths, including `main -> _compare_command -> compare_candidate`, `promote_selected_model`, `rollback_selected_model`, and `_write_report`. | Needs push/PR approval and integration decision. It is local MLOps control logic, not automatic production retraining. |
| Phase 9C API/monitoring selected model metadata | `api/phase9-selected-model-monitoring-20260620` at `7e9c65a` | Branch clean; `pytest tests/test_api_monitoring.py tests/test_api_prediction_contract.py tests/test_config.py tests/test_ml_model_selection.py tests/test_ml_promotion_cli.py -q -p no:cacheprovider` passed 18 tests with one Starlette/httpx deprecation warning; `ruff check` passed; `ruff format --check` passed. GitNexus index `realtyscope-api-phase9-selected-model-monitoring-20260620-index` was up to date at `7e9c65a`; `detect_changes` versus `ebd89ec` reported changed API/model metadata/settings flows for `model_metadata`, `monitoring_status`, and additive `Settings.active_model_selection_path`. | Needs integration decision because it is based on the Phase 9B branch. Runtime smoke for a real `selected_model.json` can be added before PR if desired. |
| Phase 9D recovered Russian UI baseline | `ui/recovered-real-data-dashboard-20260620` at `b6922b7` | Branch clean; diff limited to Streamlit UI/chart/test files; `pytest tests/test_streamlit_dashboard_charts.py tests/test_streamlit_scaffold.py tests/test_streamlit_api_client.py -q -p no:cacheprovider` passed 25 tests; `ruff check` passed; `ruff format --check` passed. Started recovered Streamlit on `http://127.0.0.1:8504` with `API_BASE_URL=http://127.0.0.1:8000`. Playwright MCP browser check confirmed title `RealtyScope - Оценка квартир`, required Russian and real-data markers present (`Дашборд`, `Оценка квартиры`, `Тепловая карта`, `Сравнение сегментов`, `О данных`, `14 755`, `2026-06-19 21:15`), forbidden mock literals absent (`273 680`, `12.46`, `Хамовники`, `Смотреть все предложения`), API status `API доступен`, model metadata `baseline_ridge_v2_non_leaky` / `ml_features_v2_non_leaky`, 0 console errors, and 12 non-blocking Streamlit/Vega/DeckGL warnings. | Continue UI polish from this recovered branch only. The rejected `ui/realtyscope-ultimate-redesign` branch remains out of scope. |

## Current Runtime Notes

- API smoke process: local Uvicorn on `127.0.0.1:8000`.
- Recovered Streamlit smoke process: `127.0.0.1:8504`.
- Compose project `realtyscope` had PostgreSQL and Redis healthy after Redis was started for the cache proof.
- Redis proof failed before API restart because the previous API process had started before Redis and FastAPI creates the Redis client in lifespan. Restarting API after Redis was healthy made the cache proof pass.
- Streamlit stderr showed a non-blocking `use_container_width` deprecation warning and a browser disconnect `ConnectionResetError` after the browser tab was closed.

## Not Yet Complete

- No Phase 9 branch has been pushed or merged.
- No final integrated branch has been assembled.
- No GitHub Actions CI has run for the Phase 9 local branches.
- README and demo scripts now have Phase 9 local split-branch caveats/addenda, but final integrated-branch docs still need a last update after the user chooses and approves a PR/merge strategy.
- Full-project `pytest`, `ruff check .`, `ruff format --check .`, Docker Compose rebuild, API/runtime smoke, recovered UI check, and GitHub Actions CI should be rerun on the chosen integration branch before any final readiness claim.
