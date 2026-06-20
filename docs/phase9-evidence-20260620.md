# RealtyScope Phase 9 Evidence Snapshot

Date: 2026-06-20
Branch: `integration/phase9-non-ui-readiness-20260620`
Purpose: record current Phase 9 branch/runtime evidence and the controlled non-UI integration branch without touching mixed local `main`.

This snapshot is intentionally conservative. It records what was verified locally and what still needs remote CI, PR review, or merge approval. It does not replace the clean workstream plan in `docs/superpowers/plans/2026-06-20-realtyscope-phase9-clean-workstreams-plan.md`.

## Current Git Policy

- Local `main` is clean but ahead of `origin/main` by 5 mixed commits. Do not push that mixed `main`.
- Phase 9 source work remains split across dedicated branches/worktrees; the non-UI source branches have also been assembled into `integration/phase9-non-ui-readiness-20260620` for review.
- No branch has been merged into `main`, deleted, or rewritten in this Phase 9 snapshot.
- No live Domclick capture was run and no scheduler trigger was changed during these checks.
- GitNexus impact evidence was used only after branch-specific index freshness was verified.

## Phase 9 Integration / PR Governance Gate

This snapshot records an integration/PR order only. It does not authorize pushing, opening PRs, merging, deleting branches, dropping stashes, repointing `main`, running live Domclick capture, or changing scheduler triggers.

Non-UI workstreams must be completed, freshly verified, and professionally reviewable before any push/PR/merge proposal. Push or merge is allowed to be discussed only after the relevant branch has completed its own acceptance checks, the integration order still makes sense, and the user explicitly approves that action. The recovered UI branch can remain deferred until the data/backend/MLOps/API/docs path is correct and approved.

User update after this snapshot: controlled integration, push, and PR work is approved when the local branch is clean and the relevant acceptance checks pass. This approval does not authorize deleting branches/stashes, rewriting history, resetting/repointing `main`, changing scheduler triggers, running live Domclick capture, or merging broken/unchecked work.

Recommended PR order after explicit approval:

1. `ops/domclick-scheduler-validated-20260619` at `e62b068` for Phase 8 scheduler publication/readiness.
2. `data/teammate-json-import-20260618` at `5db4a44` for teammate JSON import readiness.
3. `ops/postgres-guardrails-20260618` at `f5464c1` for PostgreSQL storage/volume guardrails.
4. `ml/model-promotion-workflow` at `ebd89ec` for Phase 9B MLOps dry-run compare, gated promote/reject, rollback/selection behavior, CLI, and tests.
5. `api/phase9-selected-model-monitoring-20260620` at `7e9c65a` for Phase 9C selected-model metadata in API/monitoring. This must follow Phase 9B because it depends on the model-selection code.
6. `docs/phase9-final-readiness-20260620` for final evidence/status/demo-readiness docs after the non-UI code branches are settled. This docs branch had evidence through `94dc368` before the follow-up hygiene slice; later commits on the same branch supersede that local head.
7. `ui/recovered-real-data-dashboard-20260620` at `b6922b7`, deferred until non-UI work is integrated or explicitly prioritized. Continue UI only from this recovered real-data branch, not from `ui/realtyscope-ultimate-redesign`.

Pre-push/PR gate for each non-UI branch:

- Branch is clean, on the intended worktree, and diff scope matches the workstream.
- Targeted tests and formatting/lint checks are rerun fresh from that branch.
- `git diff --check` is clean against the intended base.
- For non-trivial code, branch-specific GitNexus index freshness is rechecked against `git rev-parse HEAD`, then `detect_changes` is summarized.
- API route or response-shape changes also require `api_impact`, `route_map`, and/or `shape_check` as applicable after index freshness is confirmed.
- CI expectations are written before PR; GitHub Actions must be green before any merge.
- Push/merge remains blocked for any branch whose workstream requirements are incomplete, even if its position in the PR order is known.
- No fake/sample UI data is used as production evidence.
- No mixed local `main` is pushed.

Integration branch gate, if the user later approves assembling one:

- Build it only after the PR order is chosen.
- Rerun full `ruff check .`, `ruff format --check .`, and `pytest -q -p no:cacheprovider`.
- Rerun Docker/API/PostgreSQL/Redis runtime smoke, selected-model API smoke, and read-only scheduler evidence check.
- Update docs from fresh evidence only.
- Recheck GitNexus freshness after every non-trivial commit or branch switch before impact analysis.

## Continuation Readiness Audit: 2026-06-20

This continuation audit was performed after docs commit `59f5c21` and still did not push, open PRs, merge, delete branches, change scheduler triggers, or run live Domclick capture.

Branch/worktree checks:

- Main checkout stayed clean at `50097db`, ahead of `origin/main` by 5 mixed commits. It remains unsuitable for publishing Phase 9.
- Worktree heads matched the recorded split branches: scheduler `e62b068`, teammate import `5db4a44`, PostgreSQL guardrails `f5464c1`, MLOps `ebd89ec`, API/monitoring `7e9c65a`, docs `59f5c21`, and recovered UI `b6922b7`.
- `git diff --check` exited 0 for scheduler, teammate import, PostgreSQL guardrails, MLOps, API/monitoring, and docs branch comparisons used in the PR order.

Fresh targeted checks:

- Phase 8 scheduler: `ruff check` passed; `ruff format --check` reported 11 files already formatted; `pytest tests/test_domclick_chrome_capture.py tests/test_domclick_scheduled_batch.py -q -p no:cacheprovider` passed 22 tests.
- Phase 9A teammate import: `ruff check` passed; `ruff format --check` reported 2 files already formatted; `pytest tests/test_teammate_import.py -q -p no:cacheprovider` passed 4 tests.
- Phase 9B MLOps: `ruff check` passed; `ruff format --check` reported 10 files already formatted; `pytest tests/test_ml_model_compare.py tests/test_ml_model_selection.py tests/test_ml_promotion_cli.py tests/test_ml_training.py -q -p no:cacheprovider` passed 17 tests.
- Phase 9C API/monitoring: `ruff check` passed; `ruff format --check` reported 13 files already formatted; `pytest tests/test_api_monitoring.py tests/test_api_prediction_contract.py tests/test_config.py tests/test_ml_model_selection.py tests/test_ml_promotion_cli.py -q -p no:cacheprovider` passed 18 tests with the known Starlette/httpx deprecation warning.

Fresh GitNexus freshness and impact evidence:

- Branch-specific GitNexus worktree heads matched their branch heads for scheduler, MLOps, API/monitoring, and recovered UI. The rejected `realtyscope-ui-ultimate-redesign-index` was not used for the recovered UI branch.
- `detect_changes` rerun on `realtyscope-ops-domclick-scheduler-validated-20260619-index` reported risk `critical`, changed files 9, changed symbols 105, affected processes 26, in Domclick capture/scheduled-batch extraction paths.
- `detect_changes` rerun on `realtyscope-ml-model-promotion-workflow-index` reported risk `critical`, changed files 7, changed symbols 110, affected processes 18, in MLOps compare/selection/promote/rollback/report-writing paths.
- `detect_changes` rerun on `realtyscope-api-phase9-selected-model-monitoring-20260620-index` reported risk `critical`, changed files 4, changed symbols 13, affected processes 25, focused on `model_metadata`, `monitoring_status`, and additive `Settings.active_model_selection_path` flows.

Fresh read-only runtime evidence:

- Windows Task Scheduler read-only check still reported `LastTaskResult=0`, `NumberOfMissedRuns=0`, and the next run scheduled for 2026-06-21 00:00 Moscow.
- The two newest scheduler transcripts, `domclick-scheduled-task-20260619-000001.log` and `domclick-scheduled-task-20260620-000002.log`, both end with `status=success` and `records_seen=2000`.
- Existing API runtime on `127.0.0.1:8000` returned `/health` ok, `/data?limit=1&offset=0` with real PostgreSQL `total=14755`, `/monitoring/status` with `status=ok`, `listings_total=14755`, `ml_ready_listings=14755`, latest successful ingestion finished `2026-06-19T21:15:54.106449+00:00`, model ready, and active model `baseline_ridge_v2_non_leaky`. The current runtime does not expose Phase 9C `selected_model`; that remains covered by the isolated API branch smoke above.
- Filtered `/data?limit=3&offset=0&rooms=2&min_price_rub=10000000` returned `total=4676` and 3 rows. Redis key `realtyscope:listings:v1:limit=3:offset=0:min_price_rub=10000000:rooms=2` had `EXISTS=1`, `TTL=58`, and `STRLEN=1499`.

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

## Non-UI Integration Branch Audit: 2026-06-20

Controlled integration branch: `integration/phase9-non-ui-readiness-20260620`.
Worktree: `C:\Users\lequa\.config\superpowers\worktrees\RealtyScope\phase9-non-ui-readiness-20260620`.
Integration head before this docs refresh: `0f7bac0a30a696bd86333d0e95bb80cf8fc3741e`.
Base: `origin/main` at `ee1ae254eecef1b62b3824d860f24c88b1e6ca98`.

Merged non-UI workstreams in order:

1. `ops/domclick-scheduler-validated-20260619` at `e62b068`.
2. `data/teammate-json-import-20260618` at `5db4a44`.
3. `ops/postgres-guardrails-20260618` at `f5464c1`.
4. `ml/model-promotion-workflow` at `ebd89ec`.
5. `api/phase9-selected-model-monitoring-20260620` at `7e9c65a`.
6. `docs/phase9-final-readiness-20260620` at `23fa1d3`.

Integration branch shape:

- The merge sequence completed without conflicts.
- Diff versus `origin/main` before this docs refresh: 29 files changed, 2560 insertions, 75 deletions.
- No Streamlit/UI files were included; Phase 9D remains deferred to `ui/recovered-real-data-dashboard-20260620`.
- `main` stayed clean and was not pushed.

Fresh integration checks before this docs refresh:

- `git diff --check origin/main..HEAD` exited 0.
- `python -m ruff check .` exited 0.
- `python -m ruff format --check .` exited 0 and reported 77 files already formatted.
- `python -m pytest -q -p no:cacheprovider` exited 0 with the known Starlette/httpx deprecation warning.
- `wsl -d Ubuntu -- bash -lc "cd /mnt/c/Users/lequa/.config/superpowers/worktrees/RealtyScope/phase9-non-ui-readiness-20260620 && docker compose -p realtyscope config --quiet"` exited 0.

Integration GitNexus evidence:

- Branch-specific GitNexus worktree: `C:\Users\lequa\gitnexus-worktrees\realtyscope-integration-phase9-non-ui-readiness-20260620-index`.
- `gitnexus status` matched indexed commit `0f7bac0` to current commit `0f7bac0`.
- The index contained 2533 nodes, 5053 edges, 70 clusters, and 180 flows.
- MCP repo `realtyscope-integration-phase9-non-ui-readiness-20260620-index` was available at last commit `0f7bac0a30a696bd86333d0e95bb80cf8fc3741e`.
- `detect_changes` versus `origin/main` reported risk `critical`, 29 changed files, 249 changed symbols, and 74 affected processes. Affected flows covered scheduler capture/batch, teammate import, MLOps compare/selection/promote/rollback/report-writing, and API model metadata/monitoring/settings.

Integration runtime smoke on temporary port `127.0.0.1:8012`:

- The API was started with `PYTHONPATH` pointing at the integration `src` directory, `ACTIVE_MODEL_ARTIFACT_PATH` pointing at the existing baseline artifact, and `ACTIVE_MODEL_SELECTION_PATH` pointing at a temporary selected-model JSON.
- `/health` returned ok.
- `/model/metadata` returned `status=ready`, active `model_version=baseline_ridge_v2_non_leaky`, `feature_count=23`, `selected_model.model_version=hist_gradient_boosting_candidate_v1`, `rollback_available=true`, and `previous_model_version=baseline_ridge_v2_non_leaky`.
- `/monitoring/status` returned ok and the same selected-model payload.
- `/data?limit=1&offset=0` returned real PostgreSQL `total=14755`.
- Startup stderr included the known scikit-learn `InconsistentVersionWarning` because the artifact was saved with scikit-learn 1.8.0 and the local runtime used 1.6.1; requests still returned HTTP 200.
- The temporary API process was stopped and port `8012` was clear after shutdown.

Integration Redis/cache and scheduler evidence:

- Filtered integration API request `/data?limit=4&offset=0&rooms=2&min_price_rub=10000000` returned `total=4676` and 4 rows.
- Redis key `realtyscope:listings:v1:limit=4:offset=0:min_price_rub=10000000:rooms=2` had `EXISTS=1`, `TTL=59`, and `STRLEN=2119`.
- Windows Task Scheduler read-only check reported `LastTaskResult=0`, `NumberOfMissedRuns=0`, and `NextRunTime=2026-06-21 00:00` Moscow.

Integration status after this audit:

- The non-UI integration branch is locally assembled and locally verified, but it still needs this docs refresh committed, final gates rerun, branch push, PR creation, and GitHub Actions CI evidence before any merge decision.
- UI remains deliberately outside this non-UI integration branch.
- No live Domclick capture or scheduler trigger change was performed.

## Final Pre-Push Verification: 2026-06-20

After docs refresh commit `ebd4390`, the integration branch was verified again before any push/PR step:

- Worktree: `C:\Users\lequa\.config\superpowers\worktrees\RealtyScope\phase9-non-ui-readiness-20260620`.
- Branch: `integration/phase9-non-ui-readiness-20260620`.
- Head under test: `ebd43907d54a2b9681bf2db4153c2537912b9b1c`.
- `git diff --check origin/main..HEAD` exited 0.
- `python -m ruff check .` exited 0.
- `python -m ruff format --check .` exited 0 and reported 77 files already formatted.
- `python -m pytest -q -p no:cacheprovider` exited 0 with the known Starlette/httpx deprecation warning.
- Docker Compose config check through WSL exited 0.
- GitNexus integration index was refreshed after the docs commit: indexed commit `ebd4390`, current commit `ebd4390`, 2543 nodes, 5063 edges, 68 clusters, 180 flows.
- GitNexus MCP `detect_changes` versus `origin/main` reported risk `critical`, 29 changed files, 249 changed symbols, and 74 affected processes. The affected flows remained the expected scheduler capture/batch, teammate import, MLOps compare/selection/promote/rollback/report-writing, and API model metadata/monitoring/settings paths.
- Windows Task Scheduler read-only check still reported `LastTaskResult=0`, `NumberOfMissedRuns=0`, and next run `2026-06-21 00:00` Moscow.

Final selected-model API smoke on temporary port `127.0.0.1:8012`:

- The first smoke script attempt did not create the selected-model JSON because of a PowerShell `python -c` quoting issue, so it intentionally was not accepted as selected-model evidence.
- The corrected smoke wrote a temporary UTF-8 no-BOM selected-model JSON and asserted that both API payloads contained `hist_gradient_boosting_candidate_v1`.
- `/health` returned ok.
- `/model/metadata` returned `status=ready`, active `model_version=baseline_ridge_v2_non_leaky`, `feature_count=23`, `selected_model.model_version=hist_gradient_boosting_candidate_v1`, `rollback_available=true`, and `previous_model_version=baseline_ridge_v2_non_leaky`.
- `/monitoring/status` returned ok and the same selected-model payload.
- `/data?limit=1&offset=0` returned real PostgreSQL `total=14755`.
- Filtered `/data?limit=4&offset=0&rooms=2&min_price_rub=10000000` returned `total=4676` and 4 rows.
- Redis key `realtyscope:listings:v1:limit=4:offset=0:min_price_rub=10000000:rooms=2` had `EXISTS=1`, `TTL=59`, and `STRLEN=2119`.
- The temporary API process was stopped and port `8012` was clear after shutdown.
- Startup stderr still included the known scikit-learn `InconsistentVersionWarning` for artifact version 1.8.0 versus local runtime 1.6.1.

Remaining before merge:

- Commit this final evidence note and rerun final gates on the resulting HEAD.
- Push/open PR only from the clean integration branch.
- Wait for GitHub Actions CI before any merge decision.

## Verified Workstreams

| Workstream | Branch / commit | Fresh evidence | Remaining action |
| --- | --- | --- | --- |
| Phase 8 scheduler readiness | `ops/domclick-scheduler-validated-20260619` at `e62b068` | Branch clean; diff limited to scheduler docs/script/capture/scheduled-batch/tests; `ruff check` passed; `ruff format --check` passed; `pytest tests/test_domclick_chrome_capture.py tests/test_domclick_scheduled_batch.py -q -p no:cacheprovider` passed 22 tests. Windows Task Scheduler read-only check on 2026-06-20: `LastRunTime=2026-06-20 00:00:00`, `LastTaskResult=0`, `NextRunTime=2026-06-21 00:00:00`, `NumberOfMissedRuns=0`. Logs for 2026-06-19 and 2026-06-20 both show automatic batch success with 100 payload files and 2000 records seen. Fresh GitNexus index `realtyscope-ops-domclick-scheduler-validated-20260619-index` matched `e62b068`; `detect_changes` reported affected flows confined to Domclick capture/scheduled-batch extraction paths. | Ready for a reviewed push/PR decision only after explicit approval. |
| Phase 9A data/backend readiness | Existing split branches plus current runtime | `data/teammate-json-import-20260618` clean; diff limited to teammate import code/tests; `pytest tests/test_teammate_import.py -q -p no:cacheprovider` passed 4 tests. `ops/postgres-guardrails-20260618` clean; diff limited to `docker-compose.yml`; `git diff --check origin/main..HEAD` passed. Runtime API on `127.0.0.1:8000` returned `/health` ok and `/data?limit=3&offset=0` with real PostgreSQL `total=14755`. After starting Redis and restarting only local Uvicorn so FastAPI lifespan could create a Redis client, filtered `/data?limit=3&offset=0&rooms=2&min_price_rub=10000000` returned `total=4676`; Redis key `realtyscope:listings:v1:limit=3:offset=0:min_price_rub=10000000:rooms=2` had `EXISTS=1`, `TTL=49`, `STRLEN=1499`. `/monitoring/status` reported `listings_total=14755`, `ml_ready=14755`, latest successful ingestion finished `2026-06-19T21:15:54.106449+00:00`, model ready, feature count 23, recent errors 0. | Decide whether data/import and guardrail branches need separate PRs. Runtime proof depends on API being started after Redis is healthy. |
| Phase 9B MLOps promotion workflow | `ml/model-promotion-workflow` at `ebd89ec` | Branch clean; `pytest tests/test_ml_model_compare.py tests/test_ml_model_selection.py tests/test_ml_promotion_cli.py tests/test_ml_training.py -q -p no:cacheprovider` passed 17 tests; `ruff check src/realtyscope/ml ...` passed; `ruff format --check src/realtyscope/ml ...` passed. Fresh GitNexus index `realtyscope-ml-model-promotion-workflow-index` matched `ebd89ec`; `detect_changes` reported affected flows in MLOps CLI/compare/selection/rollback paths, including `main -> _compare_command -> compare_candidate`, `promote_selected_model`, `rollback_selected_model`, and `_write_report`. | Needs push/PR approval and integration decision. It is local MLOps control logic, not automatic production retraining. |
| Phase 9C API/monitoring selected model metadata | `api/phase9-selected-model-monitoring-20260620` at `7e9c65a` | Branch clean; `pytest tests/test_api_monitoring.py tests/test_api_prediction_contract.py tests/test_config.py tests/test_ml_model_selection.py tests/test_ml_promotion_cli.py -q -p no:cacheprovider` passed 18 tests with one Starlette/httpx deprecation warning; `ruff check` passed; `ruff format --check` passed. GitNexus index `realtyscope-api-phase9-selected-model-monitoring-20260620-index` was up to date at `7e9c65a`; `detect_changes` versus `ebd89ec` reported changed API/model metadata/settings flows for `model_metadata`, `monitoring_status`, and additive `Settings.active_model_selection_path`. Isolated runtime smoke on `127.0.0.1:8011` loaded a real branch-contract selected-model JSON and returned active model metadata plus `selected_model` rollback payload from `/model/metadata` and `/monitoring/status`. | Needs integration decision because it is based on the Phase 9B branch. Re-run the selected-model runtime smoke fresh before PR/merge if this branch is selected for publication. |
| Phase 9E docs/evidence readiness | `docs/phase9-final-readiness-20260620` | Docs record split-branch evidence, non-UI-first integration/PR order, no-push/no-merge governance, demo caveats, and CI/runtime gates. The branch is docs-only and does not change runtime behavior. | Keep as a docs/evidence branch until non-UI code branches are settled. Refresh docs again from fresh verification before any push/PR/merge proposal. |
| Phase 9D recovered Russian UI baseline | `ui/recovered-real-data-dashboard-20260620` at `b6922b7` | Branch clean; diff limited to Streamlit UI/chart/test files; `pytest tests/test_streamlit_dashboard_charts.py tests/test_streamlit_scaffold.py tests/test_streamlit_api_client.py -q -p no:cacheprovider` passed 25 tests; `ruff check` passed; `ruff format --check` passed. Started recovered Streamlit on `http://127.0.0.1:8504` with `API_BASE_URL=http://127.0.0.1:8000`. Playwright MCP browser check confirmed title `RealtyScope - Оценка квартир`, required Russian and real-data markers present (`Дашборд`, `Оценка квартиры`, `Тепловая карта`, `Сравнение сегментов`, `О данных`, `14 755`, `2026-06-19 21:15`), forbidden mock literals absent (`273 680`, `12.46`, `Хамовники`, `Смотреть все предложения`), API status `API доступен`, model metadata `baseline_ridge_v2_non_leaky` / `ml_features_v2_non_leaky`, 0 console errors, and 12 non-blocking Streamlit/Vega/DeckGL warnings. | Continue UI polish from this recovered branch only. The rejected `ui/realtyscope-ultimate-redesign` branch remains out of scope. |

## Current Runtime Notes

- API smoke process: local Uvicorn on `127.0.0.1:8000`.
- Recovered Streamlit smoke process: `127.0.0.1:8504`.
- Compose project `realtyscope` had PostgreSQL and Redis healthy after Redis was started for the cache proof.
- Redis proof failed before API restart because the previous API process had started before Redis and FastAPI creates the Redis client in lifespan. Restarting API after Redis was healthy made the cache proof pass.
- Streamlit stderr showed a non-blocking `use_container_width` deprecation warning and a browser disconnect `ConnectionResetError` after the browser tab was closed.

## Phase 9 Completion Audit Matrix

This matrix audits the active goal against current evidence. It is intentionally stricter than local branch readiness: an item is complete only when the evidence covers the requested scope, not merely when a related branch exists.

| Requirement | Current evidence | Audit status | Next controlled action |
| --- | --- | --- | --- |
| Written Phase 9 plan with concrete acceptance checks | `docs/superpowers/plans/2026-06-20-realtyscope-phase9-clean-workstreams-plan.md` and `.vi.md` exist on the docs workstream and define acceptance checks per phase. | Proved locally. | Carry plan into integration branch. |
| Separate clean workstreams | Scheduler, data import, PostgreSQL guardrails, MLOps, API, docs, and recovered UI branches/worktrees are separate and clean in the latest audits. | Proved locally. | Preserve branch separation during integration and PR description. |
| Phase 8 scheduler success preserved as two consecutive automatic passes | 2026-06-19 and 2026-06-20 scheduled-task evidence: `LastTaskResult=0`, logs end with `status=success`, `records_seen=2000`. | Proved locally. | Re-run read-only scheduler evidence on integration branch before PR. |
| Phase 9A data/backend readiness | Teammate import and PostgreSQL guardrail branches pass focused checks; current API/PostgreSQL/Redis runtime evidence shows `/data total=14755`, filtered total `4676`, Redis `EXISTS=1`. | Proved locally for split branches/runtime. | Merge into integration branch and rerun API/Redis smoke. |
| Phase 9B MLOps retrain/compare/promote workflow | `ml/model-promotion-workflow` at `ebd89ec` has dry-run compare, gated promote/reject, rollback/selection behavior, reports, and tests passing. | Proved locally. | Merge before API branch, rerun focused and full tests. |
| Phase 9C API/monitoring gaps | API branch at `7e9c65a` exposes selected-model state in `/model/metadata` and `/monitoring/status`; isolated port `8011` smoke passed. Current baseline runtime on `8000` does not expose `selected_model`. | Proved locally on API branch; not integrated. | Merge after MLOps and rerun selected-model smoke from integration branch. |
| Phase 9D recovered Russian UI | Recovered UI branch at `b6922b7` restarts against real API/PostgreSQL and browser smoke shows Russian UI, real `14 755`, no known mock literals, 0 console errors. | Baseline proved locally; final redesign/polish deferred. | Keep out of non-UI integration unless explicitly included later; continue only from recovered branch. |
| Phase 9E docs/CI/demo readiness | Docs branch records evidence, integration/PR order, demo caveats, and this audit. | Proved locally as docs evidence; final integrated docs pending. | Merge docs into integration branch after non-UI code and refresh from final checks. |
| GitNexus freshness before impact analysis | Branch-specific indexes were fresh for scheduler, MLOps, API, and recovered UI before `detect_changes`. | Proved locally for split branches. | Create/refresh an integration-branch GitNexus index if tooling is available; otherwise state unavailable and rely on tests/runtime evidence. |
| Push/PR only from clean verified branches with CI expectations | Controlled push/PR approval has now been given. The non-UI integration branch exists locally at `0f7bac0` and passed local gates before this docs refresh. | Partly proved locally; remote step pending. | Commit this docs refresh, rerun final gates, push/open PR only if clean. |
| Final integration/CI evidence | Non-UI integration branch exists locally and has pre-doc-refresh local verification. No GitHub Actions CI run, PR, or merge exists yet for this branch. | Incomplete. | Push the verified integration branch, open PR, and wait for CI evidence before any merge. |

## Not Yet Complete

- Controlled approval has been given for integration/push/PR, but no Phase 9 branch has been pushed or merged yet.
- A non-UI integration branch has been assembled locally and verified through the final pre-push checks recorded above.
- No GitHub Actions CI has run for the Phase 9 integration branch yet.
- README and demo scripts now have Phase 9 local split-branch caveats/addenda, but final integrated-branch docs still need a last update after the user chooses and approves a PR/merge strategy.
- Full-project `pytest`, `ruff check .`, `ruff format --check .`, Docker Compose rebuild, API/runtime smoke, recovered UI check, and GitHub Actions CI should be rerun on the chosen integration branch before any final readiness claim.
