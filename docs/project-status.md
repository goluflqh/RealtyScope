# RealtyScope Project Status

Date: 2026-06-03
Branch: `main`
Phase 6 milestone commit: `30bce998f1c3e5a6d13085d08a0b3692a52234a2`
Phase 7 merge evidence commit: `05f9b0cac3e77d55b93820be5d2b3db442d5295c`

This document is the operating status board for the final course-readiness work. It consolidates the assignment requirements, implemented phase evidence, current gaps, and the next smaller workstreams so future sessions do not have to reload the full history.

## 2026-06-26 Controlled Domclick Refresh And Scheduler Monitoring Fix

Current branch: `integration/realtyscope-grade5-final-20260625`.

This addendum supersedes older runtime notes that list `17,046` listings, `44,765` observations, or last observed date `2026-06-24` as the freshest Docker database evidence.

- Root cause of the missed 2026-06-26 scheduled refresh was source access, not UI polling: the scheduled Chrome capture hit a Domclick QRATOR challenge before the Python scheduled batch could record DB state.
- The scheduler now records pre-batch failures into `app_logs`: `scripts/run_domclick_scheduled_batch.ps1` captures the native command output tail and calls `python -m realtyscope.ingestion.domclick_scheduled_batch log-error`; the CLI writes a `domclick_scheduled_task_failed` warning for `/monitoring/status` recent errors while still rethrowing the original failure.
- `/monitoring/status` now also exposes bounded UI-safe `recent_logs` alongside compatibility `recent_errors`; log messages are whitespace-normalized/truncated before reaching the UI, while `recent_errors` still carries context for debugging.
- A controlled Chrome/CDP preflight using `%LOCALAPPDATA%\RealtyScope\ChromeAutomation\User Data\Default` succeeded on offset `0` with `20` records. The evidence folder was preserved as `data/raw/domclick/2026-06-26-bulk-preflight-20records`.
- A bounded 50-page capture then wrote `data/raw/domclick/2026-06-26-bulk` with `50` payload files and `1,000` records.
- The safe ingest command committed run id `26` from `data/raw/domclick/2026-06-26-bulk`: `records_seen=1,000`, `normalized_count=1,000`, `rejected_count=0`, `listings_created=241`, `listings_updated=759`, `observations_inserted=999`, report `data/processed/domclick_reports/domclick-20260626T012727-535110Z.json`.
- Docker API `127.0.0.1:8000/monitoring/status` now reports `17,287` listings, `source_counts={'cian': 2436, 'domclick': 14851}`, `45,764` observations, `23` observation dates, `first_observed_date=2026-05-14`, `last_observed_date=2026-06-26`, `listings_with_observation_history=7,956`, `max_observation_dates_per_listing=21`, `listing_price_change_count=1,470`, and `inferred_lifecycle_target_rows=6,105`.
- OSM caveat after the refresh: persisted OSM feature rows remain `17,046`; against the refreshed `17,287` listing table this is `98.61%` coverage, not a fresh all-rows live Overpass claim.
- Model caveat: Docker `/model/metadata` still serves the selected `random_forest` artifact trained before this data refresh with `rows_total=17,046`; do not imply the model was retrained on `17,287` rows until trainer/model-selection is rerun and verified.
- Model freshness gate: Docker `/monitoring/status` now exposes `model.data_freshness.status=validated_snapshot`, `model_rows_total=17,046`, `current_listings_total=17,287`, `row_delta=241`, and `requires_retrain=false`; keep serving the current validated artifact until a retrain candidate passes promotion validation.
- Static audit is now freshness-gated: `scripts/playwright/generate_static_audit.py` bootstraps `src` for direct CLI execution and fails API-mode audits unless the UI payload includes a known `model.data_freshness` status.
- Streamlit Monitoring now prefers `recent_logs` for the system journal, so scheduler/API operational events can render their real event type, timestamp, and sanitized message instead of a generic placeholder.
- Fresh Docker static audit with `API_BASE_URL=http://127.0.0.1:8000` passed and printed `api 17287 {'cian': 2436, 'domclick': 14851}`.
- Fresh Docker CDP audit with `API_BASE_URL=http://127.0.0.1:8000` and `STREAMLIT_URL=http://127.0.0.1:8501` passed with `listings_total=17287`, `exposure_inferred_target_rows=6105`, trend series through `2026-06-26`, selected candidate `random_forest`, and all seven screenshots at `clippedCount=0` / `overlapCount=0`.
- Fresh WSL Compose smoke: `wsl -d Ubuntu -- bash -lc "cd '/mnt/e/Магистр/2-курс/python/RealtyScope-stitch-hybrid-redesign-20260623' && docker compose -p realtyscope ps"` showed `api`, `streamlit`, `db`, and `redis` healthy, with `mlflow` up; `curl.exe --noproxy "*"` returned Docker API `/health` status `ok`, Streamlit health `ok`, and `/monitoring/status` with `listings_total=17287`.
- Full Docker rebuild was not rerun in this slice; the evidence above is a WSL Compose/runtime smoke against already-running rebuilt containers.
- Fresh verification after the `recent_logs` hardening: `tests/test_api_monitoring.py tests/test_streamlit_ui_payload.py tests/test_static_audit_requirements.py` passed with `59 passed`; targeted `py_compile`, `ruff`, static audit, and Docker CDP audit all passed.
- Operational caveat resolved: Windows Scheduled Task previously pointed at `E:\Магистр\2-курс\python\RealtyScope\scripts\run_domclick_scheduled_batch.ps1`; the scheduler-monitoring fix was also ported to that old repo branch, but the active scheduled task now targets the Stitch hybrid worktree below.
- Scheduler target correction: the Windows Scheduled Task `\RealtyScope Domclick Scheduled Batch` was updated to run `E:\Магистр\2-курс\python\RealtyScope-stitch-hybrid-redesign-20260623\scripts\run_domclick_scheduled_batch.ps1`. The previous XML was backed up at `output/scheduler/realtyscope-domclick-scheduled-batch-before-20260626.xml`.
- Safe scheduler dry-run proof: `powershell.exe -NoProfile -ExecutionPolicy Bypass -File ...\RealtyScope-stitch-hybrid-redesign-20260623\scripts\run_domclick_scheduled_batch.ps1 -DryRun -SkipCapture -SkipDockerStart -CollectionDate 2026-06-26` resolved the new repo and printed the expected batch command against `data\raw\domclick\2026-06-26-bulk` without Docker, Chrome, ingestion, or DB commit.

## 2026-06-25 Current Integration Branch Local Runtime After Manual Model Selection

Current branch: `integration/realtyscope-grade5-final-20260625`.

This addendum records the latest code-new verification from the integration worktree. It does not replace the earlier Docker evidence unless Docker is rebuilt and rechecked separately.

- FastAPI was started from this worktree on `127.0.0.1:8016` with `MODEL_SELECTION_MODE=best_metric`; `/health` returned `status=ok`, `environment=local`.
- `/monitoring/status` returned `17,046` listings, `source_counts={'cian': 2436, 'domclick': 14610}`, `44,765` observations, `22` observation dates, `lifecycle_target_rows=0`, `inferred_lifecycle_target_rows=4,962`, `osm_features_total=17,046`, `osm_featured_listings=17,046`, `osm_coverage_pct=100.0`, `osm_local_extract_rows=4,487`, `osm_live_rows=16`, `osm_coordinate_derived_rows=12,543`, and `osm_infrastructure_coverage_source=local_extract+live_overpass+coordinate_exact_match`.
- The selected model artifact now writes and serves three real candidate artifacts: `random_forest`, `hist_gradient_boosting`, and `ridge`. Manual `/predict` requests with `model_candidate` returned HTTP 200 for all three candidates; unknown candidates return HTTP 422 with available candidates.
- The Streamlit valuation UI now renders `Авто` plus the three real model choices (`Ridge-регрессия`, `случайный лес`, `градиентный бустинг`) and sends `model_candidate` only when a manual model is selected.
- The Streamlit workstation now polls `/monitoring/status` in API mode and reloads when the monitoring signature changes (`listings_total`, `observations_total`, latest run id, latest run finished time). It skips polling while the document is hidden.
- GitHub Actions now enforces the course coverage threshold with `--cov-fail-under=50` on the pytest step. Fresh local proof with the same threshold reported total coverage `80.35%`.
- A read-only terminal lifecycle verification candidate CLI was added: `python -m realtyscope.analysis.lifecycle_verification --limit 5 --json`. It exports listings that disappeared from repeated observations and still need source verification before they can become terminal lifecycle rows.
- Read-only source probing showed why the terminal lifecycle rows cannot be safely raised by a simple HTTP job: candidate Domclick card `HEAD` requests returned `204`, while browser-like `GET` requests returned `401 Unauthorized`. The next safe step is a Chrome/CDP or authenticated source verifier that records provenance, not converting observation gaps into confirmed sale/removal.
- Static audit against API `127.0.0.1:8016` printed `api 17046 {'cian': 2436, 'domclick': 14610}` and regenerated `output/playwright/realtyscope-static-audit.html`.
- CDP static Grade-5 audit against API `127.0.0.1:8016` passed all page gates, model valuation, map tiles/zoom/drag/popup, district/cluster checks with `cluster_feature_source=districtComparison+boundary+osm`, monitoring selected-candidate rendering (`random_forest` as `случайный лес`), and all seven screenshots with `clippedCount=0` and `overlapCount=0`.
- Fresh verification from this slice: `python -m pytest -p no:cacheprovider --cov=realtyscope --cov=services --cov-report=term-missing --cov-fail-under=50` exited `0` with `218 passed`, one known Starlette/httpx deprecation warning, and total coverage `80.35%`; `python -m ruff check src services tests` exited `0`; `python -m compileall -q src services tests` exited `0`; `git diff --check` exited `0` with only LF-to-CRLF warnings.
- Remaining truth caveats are unchanged: no XGBoost result is claimed, terminal confirmed sale/removal rows remain `0`, and the lifecycle forecast is inferred disappearance from observations rather than confirmed sale/removal.

## 2026-06-25 Current Docker Runtime After Retrain

Current branch: `ui/stitch-hybrid-redesign-20260623`.

This addendum supersedes older same-day runtime notes that name `hist_gradient_boosting` as the active Docker-selected model, report `candidate_count=2`, or describe OSM infrastructure coverage as partial.

- Docker Compose via WSL reports `api`, `streamlit`, `db`, and `redis` healthy, with `mlflow` up.
- Docker `/health` returns `status=ok`, `environment=docker`; Streamlit `/_stcore/health` returns `ok`.
- Docker `/model/metadata` now reports `selected_candidate=random_forest`, `candidate_count=3`, `model_selection_mode=best_metric`, `rows_total=17,046`, `train_rows=13,636`, `test_rows=3,410`, `r2=0.8653013476373554`, `mae=7,638,132.733793359`, `rmse=17,470,229.328815047`, and non-empty `feature_importance` rows from `model_feature_importance`.
- Training candidates in Docker metadata are real and evaluated on the same grouped split: `random_forest` (`r2=0.8653013476373554`, `mae=7,638,132.733793359`), `hist_gradient_boosting` (`r2=0.8483193165484304`, `mae=7,682,017.89735461`), and `ridge` (`r2=0.5885808364114331`, `mae=16,992,756.563055124`).
- Docker `/stats/data-quality` reports `17,046` listings, `source_counts={'cian': 2436, 'domclick': 14610}`, `44,765` observations, `22` observation dates, `lifecycle_target_rows=0`, `inferred_lifecycle_target_rows=4,962`, `osm_features_total=17,046`, `osm_featured_listings=17,046`, `osm_coverage_pct=100.0`, `osm_local_extract_rows=4,487`, `osm_live_rows=16`, `osm_coordinate_derived_rows=12,543`, and `osm_infrastructure_coverage_source=local_extract+live_overpass+coordinate_exact_match`.
- Docker `/stats/exposure-forecast` remains truthful: `status=ready`, `can_forecast=true`, `target_source=observation_gap_inferred_lifecycle`, `inferred_lifecycle_target_rows=4,962`, `terminal_lifecycle_target_rows=0`, and the caveat says this is not a confirmed sale/removal fact.
- Remaining truth caveats: no XGBoost result is claimed because the dependency is not installed/locked, terminal confirmed sale/removal rows remain `0`, and full OSM coverage is persisted coverage from local extract + live Overpass + exact-coordinate derivation rather than a claim that all rows were independently fetched live.

## 2026-06-25 Docker OSM And District OSM-Backed Runtime Evidence

Current branch: `ui/stitch-hybrid-redesign-20260623`.

This addendum supersedes the temporary Docker caveat in the OSM local extract section below.

- Rebuilt/restarted Docker `api` and `streamlit` from the retained branch via WSL Compose. Compose reports `api` and `streamlit` healthy, with `db` and `redis` healthy and `mlflow` up.
- Docker `/stats/data-quality` now reports `osm_features_total=17,046`, `osm_featured_listings=17,046`, `osm_coverage_pct=100.0`, `osm_local_extract_rows=4,487`, `osm_live_rows=16`, `osm_coordinate_derived_rows=12,543`, and `osm_infrastructure_coverage_source=local_extract+live_overpass+coordinate_exact_match`.
- Streamlit analytics now preserves OSM feature columns from `/data` rows into the district matrix. Docker CDP verifies `cluster_feature_source=districtComparison+boundary+osm`, `segments.clusterUsesOsm=true`, `osm_rows=17,046`, and `monitoring.rendersOsmLocalExtractRows=true`.
- Docker static audit on `API_BASE_URL=http://127.0.0.1:8000` printed `api 17046 {'cian': 2436, 'domclick': 14610}`.
- Docker CDP audit on `API_BASE_URL=http://127.0.0.1:8000`, `STREAMLIT_URL=http://127.0.0.1:8501` passed all page gates, real map checks, selected model rendering, OSM local/derived provenance gates, district OSM-backed cluster gate, and all seven screenshots with `clippedCount=0` / `overlapCount=0`.
- Verification after the district OSM-backed fix: `python -m pytest -p no:cacheprovider tests/test_osm_enrichment.py tests/test_api_data_routes.py tests/test_streamlit_ui_payload.py tests/test_static_audit_requirements.py -q` (`67 passed`), targeted `ruff`, targeted `py_compile`, and `node --check output\playwright\cdp_static_grade5_audit.mjs`.
- Remaining truth caveats: no XGBoost result is claimed because the dependency is not installed/locked, and terminal confirmed sale/removal lifecycle rows remain `0`; the exposure model is still `observation_gap_inferred_lifecycle`.

## 2026-06-25 OSM Local Extract Full-Coverage Code Evidence

Current branch: `ui/stitch-hybrid-redesign-20260623`.

This addendum supersedes older OSM notes that still describe `448 / 17,046` (`2.63%`) as the current database coverage.

- A real local BBBike Moscow OpenStreetMap GeoJSON extract was used: `data/cache/osm/Moscow.osm.geojson.xz`.
- Offline enrichment from the extract wrote direct representative-coordinate feature rows with `source_summary.source=bbbike_geojson_extract`, `live_osm_called=false`, and `source_file=Moscow.osm.geojson.xz`.
- Exact-coordinate derivation then copied persisted feature rows only to listings with identical `latitude` / `longitude`; these rows are marked with `source_summary.derivation=coordinate_exact_match`.
- Current code against the real PostgreSQL database reports `listings_total=17,046`, `osm_features_total=17,046`, `osm_featured_listings=17,046`, `osm_coverage_pct=100.0`, `osm_local_extract_rows=4,487`, `osm_live_rows=16`, `osm_coordinate_derived_rows=12,543`, and `osm_infrastructure_coverage_source=local_extract+live_overpass+coordinate_exact_match`.
- API and Streamlit provenance were corrected so `/stats/data-quality` exposes `osm_local_extract_rows`, and the Streamlit payload exposes `localExtractRows`. The Monitoring UI source label now distinguishes local extract rows, Overpass rows, and exact-coordinate-derived rows.
- Verification passed: `python -m pytest -p no:cacheprovider tests/test_osm_enrichment.py tests/test_api_data_routes.py tests/test_streamlit_ui_payload.py -q` (`64 passed`), targeted `ruff`, and targeted `py_compile`.
- Code-new local runtime proof passed on API `127.0.0.1:8014` and Streamlit `127.0.0.1:8512`: static audit printed `api 17046 {'cian': 2436, 'domclick': 14610}`; CDP verified `osm_rows=17046`, `osm_local_extract_rows=4487`, `osm_coordinate_derived_rows=12543`, `osm_coverage_source=local_extract+live_overpass+coordinate_exact_match`, `monitoring.rendersOsmLocalExtractRows=true`, all page gates, and all seven screenshots with `clippedCount=0` / `overlapCount=0`.
- Runtime caveat: Docker API `127.0.0.1:8000` still served the old provenance field during this slice because WSL failed with `Wsl/Service/0x8007274c` before `api`/`streamlit` could be rebuilt. Rebuild Docker API/Streamlit when WSL is stable, then rerun static/CDP audits before treating `8000/8501` as final Docker proof for this provenance change.
- Accuracy caveat: this is full persisted OSM feature coverage for the current listing table, not a claim that all 17,046 rows were independently fetched from live Overpass. The rows are a mix of local extract direct rows, earlier live Overpass rows, and exact-coordinate-derived rows.

## 2026-06-25 Historical Docker Runtime HistGradientBoosting Reload Evidence

Current branch: `ui/stitch-hybrid-redesign-20260623`.

Historical note: this addendum has been superseded by the current Docker retrain above. Keep it only as provenance for an earlier same-day artifact that selected `hist_gradient_boosting`.

- Rebuilt and restarted Docker API/Streamlit from the retained branch with `wsl.exe bash -lc 'cd "/mnt/e/Магистр/2-курс/python/RealtyScope-stitch-hybrid-redesign-20260623" && docker compose -p realtyscope up -d --build api streamlit'`.
- Compose status after the rebuild: `api` and `streamlit` are healthy, `db` and `redis` remain healthy, and `mlflow` is up.
- Docker `/health` reports `status=ok`, `environment=docker`; Streamlit `/_stcore/health` returns `ok`.
- Docker `/model/metadata` now reports the current selected artifact: `selected_candidate=hist_gradient_boosting`, `candidate_count=3`, `model_selection_mode=best_metric`, `rows_total=17,046`, `train_rows=13,636`, `test_rows=3,410`, `r2=0.8994355561733502`, `mae=6,188,596.253660057`, and `rmse=15,095,211.71856097`.
- Training candidates in Docker metadata are real and evaluated on the same grouped split: `hist_gradient_boosting` (`r2=0.8994355561733502`, `mae=6,188,596.253660057`), `random_forest` (`r2=0.8505952988269576`, `mae=7,989,464.3271694975`), and `ridge` (`r2=0.556166053792913`, `mae=16,651,213.37086019`).
- Leakage guardrails remain visible in the metadata: grouped split counts match listing groups (`train_listing_groups=13,636`, `test_listing_groups=3,410`), and the 23-feature list does not include a target/price feature.
- Docker `/stats/data-quality` reports `17,046` listings, `source_counts={'cian': 2436, 'domclick': 14610}`, `44,765` observations, `22` observation dates, `lifecycle_target_rows=0`, `inferred_lifecycle_target_rows=4,962`, `osm_features_total=448`, `osm_featured_listings=448`, `osm_coverage_pct=2.63`, `osm_live_rows=16`, and `osm_coordinate_derived_rows=432`.
- Docker `/stats/exposure-forecast` remains truthful: `target_source=observation_gap_inferred_lifecycle`, `inferred_lifecycle_target_rows=4,962`, `terminal_lifecycle_target_rows=0`, and the caveat says this is not a confirmed sale/removal fact.
- Static audit against Docker passed with `API_BASE_URL=http://127.0.0.1:8000`: `api 17046 {'cian': 2436, 'domclick': 14610}`.
- CDP Grade-5 audit against Docker API/Streamlit passed with `selectedCandidate=hist_gradient_boosting`, `expectedSelectedCandidateLabel=градиентный бустинг`, `rendersSelectedCandidateName=true`, real map interaction (`loadedTiles=30/30`, zoom and drag changed), `district_coverage_pct=84.47`, `cluster_feature_source=districtComparison+boundary`, and all seven screenshots at `clippedCount=0` / `overlapCount=0`.
- Remaining truth caveats are unchanged: no XGBoost result is claimed, terminal confirmed sale/removal rows remain `0`, and district clustering remains boundary-backed rather than broadly OSM-backed while OSM coverage is only `448 / 17,046` (`2.63%`).

## 2026-06-25 Historical Expanded Model Candidate And OSM Rate-Limit Update

Current branch: `ui/stitch-hybrid-redesign-20260623`.

- Expanded selected-model training now evaluates three real scikit-learn candidates on the same grouped validation split: `ridge`, `random_forest`, and `hist_gradient_boosting`.
- No `xgboost` dependency exists in `pyproject.toml` or `uv.lock`, so no XGBoost result is claimed. Do not say RandomForest or HistGradientBoosting beat XGBoost until XGBoost is added to the dependency/Docker contract and trained.
- The selected artifact `data/processed/models/phase5/selected_price_model_v1_non_leaky.joblib` was retrained on `17,046` rows with feature version `ml_features_v2_non_leaky`. It selected `hist_gradient_boosting` with validation `r2=0.8994355561733502`, `mae=6,188,596.253660057`, `rmse=15,095,211.71856097`, `mape=0.16183106164323535`, `train_rows=13,636`, `test_rows=3,410`, and `candidate_count=3`.
- Candidate metrics from the same grouped split: `random_forest` `r2=0.8496374735904109`, `mae=8,008,821.77078574`; `ridge` `r2=0.5562438473500875`, `mae=16,654,440.34608464`.
- A fresh code-new API process on `127.0.0.1:8013` reloaded the artifact and `/model/metadata` reported `selected_candidate=hist_gradient_boosting`, `candidate_count=3`, `rows_total=17,046`. Docker API `127.0.0.1:8000` remained healthy but still held the older in-memory `random_forest` artifact because Docker CLI is not available in Windows PATH to restart/rebuild the container.
- Leakage guardrails were verified: selected training uses `strategy=listing_id_grouped_random`, train/test listing ID sets are disjoint, and `ml_features_v2_non_leaky` artifacts do not include feature names containing `price`. Added/ran `test_train_selected_model_groups_duplicate_listings_before_split`.
- Verification passed: `python -m pytest -p no:cacheprovider tests/test_ml_training.py -q` (`11 passed`), `python -m pytest -p no:cacheprovider tests/test_api_monitoring.py tests/test_config.py -q` (`13 passed`), targeted Streamlit fallback/model UI tests (`2 passed`), `py_compile`, and `ruff`.
- After stopping stale local API/Streamlit Python processes, static audit and CDP visual proof were refreshed against API `127.0.0.1:8013`. Static audit printed `api 17046 {'cian': 2436, 'domclick': 14610}` and regenerated `output/playwright/realtyscope-static-audit.html`. CDP passed all page/layout gates and now explicitly verifies `monitoring.selectedCandidate=hist_gradient_boosting`, `expectedSelectedCandidateLabel=градиентный бустинг`, and `rendersSelectedCandidateName=true`.
- OSM local extract/cache search was repeated in the repo and parent project tree; no usable `.pbf`, `.osm`, `.osm.bz2`, `.mbtiles`, or Overpass cache was found. The live selector still uses `selection_mode=live_overpass_missing_distinct_coordinates`.
- A logged Overpass batch with `--limit 10 --radius-m 1000 --delay-seconds 2 --timeout-seconds 25` inserted `4` live rows but hit `HTTP 429 Too Many Requests` for `6` selected listing IDs. Exact-coordinate derivation then inserted `8` additional rows with no live OSM call.
- API `/stats/data-quality` after derivation reports `osm_features_total=448`, `osm_featured_listings=448`, `osm_coverage_pct=2.63`, `osm_live_rows=16`, `osm_coordinate_derived_rows=432`, and `osm_infrastructure_coverage_source=live_overpass+coordinate_exact_match`. Remaining selector count is `rows_available=4,487`.
- Because Overpass returned 429 and confirmed coverage is still only `448 / 17,046`, stop live Overpass for now and keep district clustering described as boundary-backed, not broadly OSM-infrastructure-backed.

## 2026-06-25 Historical Docker Runtime Final Rebuild Evidence

Current branch: `ui/stitch-hybrid-redesign-20260623`.

This addendum supersedes older notes that said Docker `127.0.0.1:8000` was stale, still served a `16,512`-row selected artifact, or still used observed-history-only exposure semantics.

- Docker trainer completed on the current database and logged a new selected model artifact:
  - selected candidate: `random_forest`
  - model version: `selected_price_model_v1_non_leaky`
  - feature version: `ml_features_v2_non_leaky`
  - `rows_total=17,046`, `train_rows=13,636`, `test_rows=3,410`
  - validation `r2=0.8507863494880132`, `mae=7,987,846.5447418345`, `rmse=18,387,439.565866258`, `mape=0.2046773403637898`
  - candidate comparison was real: `random_forest` beat `ridge` (`ridge r2=0.5560968329555391`, `mae=16,645,128.21808997`) on the same grouped split.
- `docker compose -p realtyscope up -d --build api streamlit` rebuilt and restarted the Docker `api` and `streamlit` images. Compose reports `api`, `streamlit`, `db`, and `redis` healthy, with MLflow up.
- Docker runtime evidence on `127.0.0.1:8000` / `127.0.0.1:8501`:
  - `/health`: `status=ok`, `environment=docker`.
  - Streamlit `/_stcore/health`: `ok`.
  - `/model/metadata`: `status=ready`, `selected_candidate=random_forest`, `model_selection_mode=best_metric`, `candidate_count=2`, `rows_total=17,046`.
  - `/stats/exposure-forecast`: `status=ready`, `can_forecast=true`, `target_source=observation_gap_inferred_lifecycle`, `method=gap_inferred_lifecycle_median_v1`, `inferred_lifecycle_target_rows=4,962`, `terminal_lifecycle_target_rows=0`, `observed_exposure_target_rows=7,766`.
- Docker static audit passed with `API_BASE_URL=http://127.0.0.1:8000` and printed `api 17046 {'cian': 2436, 'domclick': 14610}`.
- Docker CDP Grade-5 audit passed with `API_BASE_URL=http://127.0.0.1:8000` and `STREAMLIT_URL=http://127.0.0.1:8501`. It verified API mode with `17,046` listings, selected model provenance, inferred lifecycle exposure readiness, trend readiness, real map tiles/zoom/drag/popup, data/deals/district/monitoring gates, and all seven page screenshots with `clippedCount=0` and `overlapCount=0`.
- Windows `Invoke-RestMethod` timed out against Docker localhost during this check, but `curl.exe --noproxy "*"` and WSL/container requests returned immediately. Treat that as a PowerShell/WebRequest transport issue, not an application failure.
- Remaining truth caveat: terminal sale/removal exposure rows remain `0`; the working exposure model is observation-gap inferred lifecycle, not confirmed sale/removal. District comparison/clustering remain boundary-backed (`admin_boundary_geojson+address_text`) and not broadly OSM-infrastructure-backed while OSM feature coverage remains `436 / 17,046` (`2.56%`).

## 2026-06-25 OSM Logged Batch And Coverage Update

Current branch: `ui/stitch-hybrid-redesign-20260623`.

This slice made the OSM live-enrichment strategy resumable and auditable without fabricating coverage:

- Added CLI `--progress-log` support to append one JSONL evidence row after each successful dry-run/write/derive command. Each row records `operation`, `limit`, `radius_m`, `delay_seconds`, `timeout_seconds`, selected listing IDs, row counts, errors, and the result payload.
- No local OSM extract/cache was found in the repo root, parent project folder, or top-level Downloads scan; this slice therefore used a controlled live Overpass batch.
- Dry-run before the batch wrote evidence to `output/osm-enrichment/overpass-batches-20260625.jsonl`: `rows_available=4,493`, `rows_selected=2`, `selected_listing_ids=[7, 8]`.
- Live Overpass batch command used `--limit 2`, `--radius-m 1000`, `--delay-seconds 2`, and `--timeout-seconds 25`. It inserted `2` real OSM rows with `rows_failed=0` for listing IDs `[7, 8]`.
- Exact-coordinate derivation then inserted `17` derived rows with `rows_failed=0` and no live OSM call.
- Selector after the batch reports `rows_available=4,491`, `rows_selected=5`, first selected IDs `[10, 11, 13, 15, 16]`.
- Docker API `/stats/data-quality` now reports `osm_features_total=436`, `osm_featured_listings=436`, `osm_coverage_pct=2.56`, `osm_live_rows=12`, `osm_coordinate_derived_rows=424`, and `osm_infrastructure_coverage_source=live_overpass+coordinate_exact_match`.
- Verification passed: `tests/test_osm_enrichment.py` (`13` tests), `py_compile` for OSM source/test files, `ruff` for OSM source/test files, static audit against Docker API (`api 17046 {'cian': 2436, 'domclick': 14610}`), and CDP Grade-5 audit against Docker API/Streamlit with `osm_rows=436`, `osm_coverage_pct=2.56`, `osm_coordinate_derived_rows=424`, `cluster_feature_source=districtComparison+boundary`, and all seven screenshots at `clippedCount=0` / `overlapCount=0`.

Remaining truth caveat: this is still partial OSM infrastructure coverage (`436 / 17,046`, `2.56%`). District clustering remains boundary-backed, not broadly OSM-backed.

## 2026-06-25 OSM Live Selector And Coverage Smoke

The OSM enrichment backend now avoids wasting live Overpass calls:

- Live Overpass persistence selects one representative listing per missing distinct coordinate and skips coordinates that already have an OSM feature for the active feature version.
- Dry-run with `--live-overpass --dry-run --json` now reports `selection_mode=live_overpass_missing_distinct_coordinates`.
- At that selector slice, DB dry-run evidence with `PYTHONPATH=src;.` reported `rows_available=4,493` missing distinct coordinates after the smoke below, instead of the full `17,046` listing count.
- A bounded live smoke wrote one real Overpass feature row: `rows_inserted=1`, `rows_failed=0`, `selected_listing_ids=[5]`.
- `--derive-coordinate-matches --write --limit 10000 --json` then inserted `27` exact-coordinate-derived rows from that real feature.
- At that point, Docker API `/stats/data-quality` reported `osm_features_total=417`, `osm_featured_listings=417`, `osm_coverage_pct=2.45`, `osm_live_rows=10`, `osm_coordinate_derived_rows=407`, and `osm_infrastructure_coverage_source=live_overpass+coordinate_exact_match`.
- Static audit against Docker API still prints `api 17046 {'cian': 2436, 'domclick': 14610}`.
- CDP Grade-5 audit passed after the OSM DB update with `osm_rows=417`, `osm_coverage_pct=2.45`, `osm_coordinate_derived_rows=407`, real map interactions, and all seven screenshots clean.

Historical truth caveat for that slice: this was still partial OSM infrastructure coverage (`417 / 17,046`, `2.45%`), not full OSM-backed district clustering. The selector makes future real batches efficient, but full coverage still requires a long controlled Overpass run or a local OSM extract/cache.

## 2026-06-25 Inferred Lifecycle Exposure Forecast Update

Current branch: `ui/stitch-hybrid-redesign-20260623`.

Exposure forecast is no longer limited to `can_forecast=false` observed-history readiness. The backend now derives a real inferred lifecycle target from repeated observation gaps:

- Rule: a listing-source pair must be observed on at least two distinct dates and then be absent for at least `3` days before the latest observation date for that same source.
- This is not a fabricated sale/removal label. It is an honest `observation_gap_inferred_lifecycle` forecast target for disappearance from observations; confirmed terminal rows remain separate.
- Runtime evidence on code-new API `127.0.0.1:8012`:
  - `/stats/exposure-forecast`: `status=ready`, `can_forecast=true`, `target_source=observation_gap_inferred_lifecycle`, `method=gap_inferred_lifecycle_median_v1`.
  - `terminal_lifecycle_target_rows=0`, `terminal_lifecycle_can_forecast=false`.
  - `inferred_lifecycle_target_rows=4,962`, `inferred_lifecycle_min_gap_days=3`, `inferred_lifecycle_median_days=6`, `inferred_lifecycle_max_days=19`.
  - Observed lower-bound remains separate: `observed_exposure_target_rows=7,766`, median `7`, max `22`.
- Streamlit Monitoring renders the inferred target rows and minimum gap in Russian UI. The demo wording should say this forecasts disappearance from observed source snapshots, not confirmed sale or removal.
- Code-new inspection runtime is currently API `http://127.0.0.1:8012` and Streamlit `http://127.0.0.1:8510`.
- Docker/WSL caveat remains: WSL returned `Wsl/Service/0x8007274c`, Docker Streamlit `8501` is held by `wslrelay.exe` and timed out, and Docker model metadata on `8000` still shows an older model artifact than the code-new `17,046` row selected artifact.

Verification:

- `python -m pytest -p no:cacheprovider tests/test_api_data_routes.py tests/test_api_monitoring.py tests/test_streamlit_api_client.py tests/test_streamlit_ui_payload.py -q`: `69 passed`.
- Broad sweep after the CDP fix also passed: `python -m pytest -p no:cacheprovider tests -q`, `python -m ruff check src services tests`, and `python -m compileall -q src services tests`.
- `python -m ruff check services/api/app/main.py services/streamlit/app.py tests/test_api_data_routes.py tests/test_api_monitoring.py tests/test_streamlit_ui_payload.py`: passed.
- `python -m py_compile services/api/app/main.py services/streamlit/app.py tests/test_api_data_routes.py tests/test_api_monitoring.py tests/test_streamlit_ui_payload.py`: passed.
- `PYTHONPATH=src;. API_BASE_URL=http://127.0.0.1:8012 python output\playwright\generate_static_audit.py`: passed with `api 17046 {'cian': 2436, 'domclick': 14610}`.
- CDP audit script was updated for the new exposure semantics and passed after diagnostic timeout hardening. Latest evidence includes `exposure_status=ready`, `exposure_inferred_target_rows=4962`, `exposure_target_source=observation_gap_inferred_lifecycle`, `map.loadedTiles=30/30`, real popup fields/link, and all seven screenshots at `clippedCount=0` / `overlapCount=0`.
- GitNexus dirty mirror was force re-indexed after this change at `C:\Users\lequa\gitnexus-worktrees\realtyscope-stitch-hybrid-redesign-20260625-dirty-worktree`: `3,143` nodes, `6,257` edges, `87` clusters, `200` flows. Impact for `_inferred_lifecycle_exposure_stats` reaches `data_quality_stats`, `exposure_forecast_stats`, and `monitoring_status`.

## 2026-06-25 Broad Verification And GitNexus Dirty-Worktree Index

Current branch: `ui/stitch-hybrid-redesign-20260623`.

This slice was a verification and tooling-readiness pass after the exposure semantics, data-count provenance, district caveat, and OSM exact-coordinate work:

- Full local verification passed: `python -m pytest -p no:cacheprovider tests -q`, `python -m ruff check src services tests`, and `python -m compileall -q src services tests`.
- Runtime API/Streamlit evidence on the code-new local ports is healthy: `http://127.0.0.1:8011/health` reports `status=ok`, and `http://127.0.0.1:8509/_stcore/health` reports `ok`.
- `/stats/data-quality` on `8011` reports `17,046` listings, `source_counts={'cian': 2436, 'domclick': 14610}`, `44,765` observations, `22` observation dates, `lifecycle_target_rows=0`, and `observed_exposure_target_rows=7,766`.
- `/model/metadata` on `8011` reports `selected_price_model_v1_non_leaky`, `selected_candidate=random_forest`, `feature_version=ml_features_v2_non_leaky`, validation `r2=0.850303822452758`, `mae=8,001,983.659500307`, and `rows_total=17,046`.
- `/stats/exposure-forecast` stays honest: `status=partial`, `can_forecast=false`, `terminal_lifecycle_target_rows=0`, while observed-history lower-bound evidence remains separate with `observed_exposure_can_forecast=true`.
- Static audit was regenerated with `API_BASE_URL=http://127.0.0.1:8011` and printed `api 17046 {'cian': 2436, 'domclick': 14610}`.
- CDP static Grade-5 audit passed with API mode, real map tiles, zoom, drag, listing popup fields/link, data/deals tables, monitoring panels, `district_coverage_pct=84.47`, `cluster_feature_source=districtComparison+boundary`, `osm_rows=389`, `osm_coverage_pct=2.28`, and all seven screenshots at `clippedCount=0` / `overlapCount=0`.
- Direct `gitnexus analyze` in the Cyrillic worktree still fails on `.gitnexus\lbu/lbug`, so that failed index is not used as current truth.
- To satisfy the GitNexus freshness rule for the dirty worktree, an ASCII mirror was refreshed at `C:\Users\lequa\gitnexus-worktrees\realtyscope-stitch-hybrid-redesign-20260625-dirty-worktree`, excluding generated/cache/output/data folders. `gitnexus analyze ... --skip-git --skip-agents-md --no-stats` succeeded with `3,130` nodes, `6,239` edges, `86` clusters, and `202` flows.
- GitNexus impact from the dirty mirror was used for `_district_comparison_rows` and `_exposure_forecast_stats_payload`; both are low direct blast-radius paths, with district comparison feeding `_build_payload` and `main`.

Current caveats remain unchanged: terminal sale/removal exposure forecast cannot be claimed because lifecycle target rows are still `0`; district clustering is boundary-backed, not broadly OSM-infrastructure-backed, because confirmed OSM infrastructure coverage is still only `389 / 17,046` listings (`2.28%`).

## 2026-06-25 OSM Exact-Coordinate Coverage Update

Current branch: `ui/stitch-hybrid-redesign-20260623`.

The OSM infrastructure slice was expanded without new bulk Overpass pressure and without fabricated coverage:

- Added `persist_osm_features_for_matching_coordinates()` and CLI support via `python -m realtyscope.enrichment.osm --derive-coordinate-matches --write --limit 10000 --json`.
- The command copies an existing persisted OSM feature row only to listings with the exact same `latitude` / `longitude`, preserving attribution and marking `source_summary.derivation=coordinate_exact_match`, `derived_from_listing_id`, and `source_live_osm_called`.
- Live DB result: `rows_inserted=380`, `rows_failed=0`; a second run was idempotent with `rows_inserted=0`.
- `/stats/data-quality` on code-new API `127.0.0.1:8011` now reports `osm_features_total=389`, `osm_featured_listings=389`, `osm_coverage_pct=2.28`, `osm_live_rows=9`, `osm_coordinate_derived_rows=380`, and `osm_infrastructure_coverage_source=live_overpass+coordinate_exact_match`.
- Streamlit `osmCoverage` and the Monitoring infrastructure panel now preserve and render the live-vs-derived provenance, including `Строк по точным координатам`.
- CDP static audit now records `osm_coordinate_derived_rows=380`, `osm_coverage_source=live_overpass+coordinate_exact_match`, and verifies `monitoring.rendersOsmCoordinateDerivedRows=true`.

Verification for this slice:

- `python -m pytest -p no:cacheprovider tests/test_osm_enrichment.py tests/test_api_data_routes.py tests/test_streamlit_ui_payload.py -q`: `54 passed`.
- `python -m py_compile services\api\app\main.py services\streamlit\app.py src\realtyscope\enrichment\osm.py tests\test_osm_enrichment.py tests\test_api_data_routes.py tests\test_streamlit_ui_payload.py`: passed.
- `python -m ruff check services/api/app/main.py services/streamlit/app.py src/realtyscope/enrichment/osm.py tests/test_osm_enrichment.py tests/test_api_data_routes.py tests/test_streamlit_ui_payload.py`: passed.
- `API_BASE_URL=http://127.0.0.1:8011 python output\playwright\generate_static_audit.py`: passed with `api 17046 {'cian': 2436, 'domclick': 14610}`.
- `API_BASE_URL=http://127.0.0.1:8011 node output\playwright\cdp_static_grade5_audit.mjs`: passed with `osm_rows=389`, `osm_coordinate_derived_rows=380`, real map tile/zoom/drag/popup checks, and all seven screenshots at `clippedCount=0` / `overlapCount=0`.

Current caveat: this is still partial OSM infrastructure coverage (`2.28%`), not full Moscow OSM-backed coverage. District comparison/clustering remain boundary-backed with address fallback; do not describe them as broadly OSM-infrastructure-backed until a reliable extract/cache or sustainable enrichment run covers the district matrix.

## 2026-06-25 Boundary-Backed District Analytics Update

Current branch: `ui/stitch-hybrid-redesign-20260623`.

District comparison and clustering were upgraded from the earlier address-text-only path to a real administrative-boundary join:

- Added `data/external/moscow_district_boundaries.geojson` with `125` Moscow district features and sibling provenance metadata from `GIS-Lab/OpenStreetMap` (`http://gis-lab.info/qa/osm-adm.html`).
- Added `src/realtyscope/analysis/district_boundaries.py` for GeoJSON `Polygon` / `MultiPolygon` lookup, bbox prefiltering, point-in-polygon with holes, UTF-8-BOM-tolerant metadata reads, and district-name normalization.
- Streamlit payload now prefers boundary matching by real listing `latitude` / `longitude`, then falls back to structured district fields, then to address text only for remaining rows.
- Fresh static payload evidence from the live API: `listings_total=17,046`, `boundary_matched_rows=14,386`, `boundary_coverage_pct=84.4`, `listings_with_district=14,399`, overall `coverage_pct=84.47`, `district_count=125`, `districtComparison=12`, and `districtClusters=12`.
- District readiness now reports `active_field=boundary_geojson`, `extraction_source=admin_boundary_geojson+address_text`, `boundary_source_title=GIS-Lab/OpenStreetMap`, and `boundary_source_url=http://gis-lab.info/qa/osm-adm.html`.
- District clusters now carry `feature_source=districtComparison+boundary` when the live matrix is boundary-backed.

Fresh GitNexus and verification evidence:

- The ASCII GitNexus mirror `C:\Users\lequa\gitnexus-worktrees\realtyscope-stitch-hybrid-redesign-20260625-index` was refreshed after the boundary work and indexed with `3,068` nodes, `6,093` edges, `85` clusters, and `198` flows.
- GitNexus upstream impact for `_district_assignment_series` is high through `_district_readiness_payload`, `_district_value_series`, `_district_comparison_rows`, `_build_payload`, and `main`, so targeted Streamlit payload/static audit checks were included.
- `python -m pytest -p no:cacheprovider tests/test_district_boundaries.py tests/test_streamlit_ui_payload.py tests/test_static_audit_requirements.py -q`: `38 passed`.
- `python -m py_compile src\realtyscope\analysis\district_boundaries.py services\streamlit\app.py tests\test_district_boundaries.py tests\test_streamlit_ui_payload.py output\playwright\generate_static_audit.py`: passed.
- `python -m ruff check src\realtyscope\analysis\district_boundaries.py services\streamlit\app.py tests\test_district_boundaries.py tests\test_streamlit_ui_payload.py`: passed.
- `python output\playwright\generate_static_audit.py` against the live API printed `api 17046 {'cian': 2436, 'domclick': 14610}`.
- `node output\playwright\cdp_static_grade5_audit.mjs`: passed with `loadedTiles=16/30`, real zoom/drag/popup checks, `district_coverage_pct=84.47`, `district_extraction_source=admin_boundary_geojson+address_text`, `cluster_feature_source=districtComparison+boundary`, and all seven screenshots at `clippedCount=0` / `overlapCount=0`.

Remaining caveats after this update:

- OSM infrastructure coverage is still sparse (`389` featured listings, `2.28%`, mostly exact-coordinate derived), so district clustering is boundary-backed but not broadly OSM-backed.
- Exposure remains an observed-history lower-bound forecast only; terminal sale/removal lifecycle target rows remain `0`.
- Trend remains descriptive (`can_forecast=false`) until a separate verified time-series model exists.
- Docker API `127.0.0.1:8000` still needs rebuild/restart before it can be used as proof of the selected model or `/stats/exposure-forecast`.

## 2026-06-25 Selected Model Refresh, GitNexus Index, And Tile Audit Update

Current branch: `ui/stitch-hybrid-redesign-20260623`.

This slice refreshed the current local/code-new evidence after the live DB moved to 17,046 listings:

- Code-new API was run on `127.0.0.1:8011` with `PYTHONPATH=src;.` and `MODEL_SELECTION_MODE=best_metric`.
- `/model/metadata` now selects `data\processed\models\phase5\selected_price_model_v1_non_leaky.joblib` with `selected_candidate=random_forest`, `feature_version=ml_features_v2_non_leaky`, `rows_total=17,046`, validation `r2=0.850303822452758`, `mae=8,001,983.659500307`, `rmse=18,417,146.2157716`, and `mape=0.20497256239106884`.
- Candidate evidence is preserved: `random_forest` beats `ridge` on the same grouped split; Ridge has `r2=0.5555901689314586` and `mae=16,640,622.08709979`.
- CLI trainer defaults now use the selected non-leaky path (`--trainer selected`, `--feature-version ml_features_v2_non_leaky`) so a manual train command no longer silently creates the leakage-prone `ml_features_v1` artifact.
- Runtime config fallback now points at `data/processed/models/phase5/selected_price_model_v1_non_leaky.joblib`.

GitNexus evidence:

- Direct `gitnexus analyze` in the Cyrillic worktree still failed on `.gitnexus\lbug`, so that index was not treated as current truth.
- A branch/workstream mirror was created at `C:\Users\lequa\gitnexus-worktrees\realtyscope-stitch-hybrid-redesign-20260625-index`, excluding generated/cache/output folders.
- `gitnexus analyze --force --skip-git --skip-agents-md --no-stats` succeeded on that mirror with `2,958` nodes, `5,883` edges, `80` clusters, and `193` flows.
- GitNexus impact was used for the model-default change: `train_from_database` has low direct blast radius through `main` and ML tests; `Settings` has critical blast radius through API health, model metadata, monitoring, migrations, and database/session consumers, so API/model monitoring tests were included.

Fresh data and UI evidence from code-new API `8011`:

- `/stats/data-quality`: `listings_total=17,046`, `source_counts={'cian': 2436, 'domclick': 14610}`, `observations_total=44,765`, `observation_date_count=22`, observed dates `2026-05-14` through `2026-06-24`, `listings_with_observation_history=7,766`, `listing_price_change_count=1,415`, `lifecycle_target_rows=0`, and `observed_exposure_target_rows=7,766`.
- `/stats/exposure-forecast`: `status=ready`, `can_forecast=true`, `target_source=observed_history_lower_bound`, terminal lifecycle target `0`, observed median exposure `7` days, max `22` days. This remains an observed-history lower-bound forecast, not confirmed sale/removal exposure.
- Static audit regenerated with `API_BASE_URL=http://127.0.0.1:8011` and printed `api 17046 {'cian': 2436, 'domclick': 14610}`.
- CDP audit passed after making map tile loading more robust: OpenStreetMap is now the primary real tile source with CARTO/HOT real-tile fallbacks, tile wait was increased in the audit harness, and this slice had `loadedTiles=8` of `30`, zoom/pan changed, popup showed real price/rooms/area/address/source/link, and all seven screenshots had `clippedCount=0` and `overlapCount=0`. The later boundary slice passed with `loadedTiles=16/30`.

Verification for this slice:

- `python -m pytest -p no:cacheprovider tests/test_api_monitoring.py tests/test_streamlit_api_client.py tests/test_streamlit_ui_payload.py tests/test_ml_training.py tests/test_config.py -q`: `63 passed`.
- `python -m py_compile src\realtyscope\ml\train.py src\realtyscope\config.py services\streamlit\app.py tests\test_api_monitoring.py`: passed.
- `python -m ruff check src\realtyscope\ml\train.py src\realtyscope\config.py tests\test_api_monitoring.py tests\test_ml_training.py tests\test_config.py tests\test_streamlit_api_client.py tests\test_streamlit_ui_payload.py services\streamlit\app.py`: passed.
- `python output\playwright\generate_static_audit.py` against API `8011`: passed with 17,046 API rows.
- `node output\playwright\cdp_static_grade5_audit.mjs`: passed.

Remaining caveats for this earlier slice, superseded where noted by the boundary update above:

- Docker API `127.0.0.1:8000` is still not rebuilt from this branch because WSL/Compose remains unreliable in this environment; do not use port `8000` as proof of the selected model or `/stats/exposure-forecast` until it is rebuilt and verified.
- District comparison/clustering were partial address-text analytics at this point; the later 2026-06-25 boundary update now verifies `admin_boundary_geojson+address_text` coverage at `84.47%`.
- OSM coverage remains sparse; this earlier slice had `9` featured listings / `0.05%`, superseded by the later exact-coordinate slice at `389` featured listings / `2.28%`.
- Trend remains descriptive (`can_forecast=false`) until a separate verified time-series model exists.

## 2026-06-25 Live Data Refresh And Static Audit Update

Current branch: `ui/stitch-hybrid-redesign-20260623`.

Docker/WSL status for this slice:

- Existing Docker services on localhost stayed reachable, but WSL command startup regressed again with `Wsl/Service/0x8007274c`.
- Because Docker CLI is not available in Windows PATH, API/Streamlit image rebuild was not attempted after WSL failed a lightweight `date` command.
- Docker API `127.0.0.1:8000` is therefore still an older image for code shape: `/model/metadata` reports `baseline_ridge_v2_non_leaky` and `/stats/exposure-forecast` returns `404`.
- The same Docker API is connected to the live DB and now reports a fresher real dataset from the latest Domclick ingestion.

Fresh code-new API evidence was collected on `127.0.0.1:8010` with `PYTHONPATH=src;.` against the live PostgreSQL/Redis ports:

- `/stats/data-quality`: `listings_total=17,046`, `source_counts={'cian': 2436, 'domclick': 14610}`, `observations_total=44,765`, `observation_date_count=22`, first observed date `2026-05-14`, last observed date `2026-06-24`, `listings_with_observation_history=7,766`, `max_observation_dates_per_listing=20`, `listing_price_change_count=1,415`, `lifecycle_target_rows=0`, and `observed_exposure_target_rows=7,766`.
- Latest successful ingestion run: Domclick run id `25`, started `2026-06-24T21:13:03.741795+00:00`, finished `2026-06-24T21:13:07.260925+00:00`, `records_seen=2,000`, `raw_count=2,000`, `normalized_count=2,000`, `rejected_count=0`, `inserted_count=3,612`, `updated_count=1,466`.
- `/stats/exposure-forecast`: `status=ready`, `can_forecast=true`, `target_source=observed_history_lower_bound`, `terminal_lifecycle_target_rows=0`, `observed_exposure_target_rows=7,766`, median observed exposure `7` days, max observed exposure `22` days.
- `/model/metadata`: selected local artifact `selected_price_model_v1_non_leaky`, selected algorithm `random_forest`, `model_selection_reason=best_validation_metric`, validation `r2=0.8801698812234392`, `mae=7,933,891.650272489`, `rows_total=16,512`. This model evidence is still the selected artifact trained before the latest DB refresh; do not imply it was retrained on 17,046 rows.

Fresh static/CDP evidence:

- `API_BASE_URL=http://127.0.0.1:8010 python output\playwright\generate_static_audit.py`: passed with `api 17046 {'cian': 2436, 'domclick': 14610}`.
- `node output\playwright\cdp_static_grade5_audit.mjs`: passed. Historical evidence included `17,046` real listings, `44,765` observations, `22` observation dates through `2026-06-24`, `districtComparison=12`, district coverage `13.8%` from address text at that time, `districtClusters=12`, observed-history lower-bound exposure evidence with terminal lifecycle target still `0`, trend series rows `22`, OSM coverage still `9` featured listings / `0.05%`, selected model provenance, real map tile/zoom/drag/popup behavior, and all seven screenshot pages with `clippedCount=0` and `overlapCount=0`. The district and exposure wording from this earlier slice is superseded by the later boundary-backed and terminal-forecast semantics updates above.

## 2026-06-24 Exposure Forecast Endpoint And UI Wiring Update

Current branch: `ui/stitch-hybrid-redesign-20260623`.

This slice added a dedicated backend endpoint for the exposure forecast/readiness contract:

- FastAPI now exposes `GET /stats/exposure-forecast`.
- The endpoint keeps terminal sale/removal lifecycle evidence separate as `terminal_lifecycle_target_rows` and `terminal_lifecycle_can_forecast`.
- It exposes the real observed-history lower-bound forecast fields from persisted repeated observations: `observed_exposure_target_rows`, `median_observed_exposure_days`, `max_observed_exposure_days`, `forecast_segments`, `target_source=observed_history_lower_bound`, and a Russian caveat explaining that this is a lower bound from first to last observed date, not a confirmed sale/removal date.
- Streamlit `fetch_dashboard_data()` now fetches `/stats/exposure-forecast` separately, and `_build_payload()` passes it into `exposureReadiness`; this lets the UI prefer the endpoint even when an older `/stats/data-quality` payload lacks the new fields.

Fresh code-new API evidence on `127.0.0.1:8010` with `PYTHONPATH=src;.`:

- `/stats/data-quality`: `listings_total=16,512`, `source_counts={'cian': 2436, 'domclick': 14076}`, `observations_total=42,765`, `observation_date_count=21`, `lifecycle_target_rows=0`, `observed_exposure_target_rows=7,456`.
- `/stats/exposure-forecast`: `status=ready`, `can_forecast=true`, `target_source=observed_history_lower_bound`, `terminal_lifecycle_target_rows=0`, `observed_exposure_target_rows=7,456`, median observed exposure `7` days, max `21` days, and room-segment medians.
- `/model/metadata`: selected local artifact `selected_price_model_v1_non_leaky`, `selected_candidate=random_forest`, `model_selection_reason=best_validation_metric`, `rows_total=16,512`, `r2=0.8801698812234392`.

Fresh verification for this slice:

- `python -m pytest -p no:cacheprovider tests/test_api_monitoring.py tests/test_streamlit_api_client.py tests/test_streamlit_ui_payload.py -q`: `49 passed`.
- `python -m py_compile services\api\app\main.py services\streamlit\api_client.py services\streamlit\app.py tests\test_api_monitoring.py tests\test_streamlit_api_client.py tests\test_streamlit_ui_payload.py`: passed.
- `python -m ruff check services\api\app\main.py services\streamlit\api_client.py services\streamlit\app.py tests\test_api_monitoring.py tests\test_streamlit_api_client.py tests\test_streamlit_ui_payload.py`: passed.
- `API_BASE_URL=http://127.0.0.1:8010 python output\playwright\generate_static_audit.py`: passed with `api 16512 {'cian': 2436, 'domclick': 14076}`.
- `node output\playwright\cdp_static_grade5_audit.mjs`: passed. Evidence included exposure `status=ready`, `target_source=observed_history_lower_bound`, terminal lifecycle target still `0`, selected model provenance, real map tiles/zoom/drag/popup, and all seven screenshots with `clippedCount=0` and `overlapCount=0`.

Runtime caveat: Docker API `127.0.0.1:8000` still responded from the older running image during this slice and reported the baseline Ridge model plus no `/stats/exposure-forecast` evidence. Do not claim Docker `8000` is promoted to the selected model or endpoint until Compose is rebuilt/restarted and `/model/metadata` plus `/stats/exposure-forecast` on port `8000` prove it.

## 2026-06-24 Selected Model And Observed Exposure Update

Current branch: `ui/stitch-hybrid-redesign-20260623`.

Code now supports and verifies selected-model training/promotion readiness:

- `services/trainer/Dockerfile` defaults to `--trainer selected` so the trainer image no longer creates only the historical Ridge baseline by default.
- Local selector evidence from this workspace chooses `data/processed/models/phase5/selected_price_model_v1_non_leaky.joblib`.
- Temporary code-new API smoke on `127.0.0.1:8010` reported `model_version=selected_price_model_v1_non_leaky`, `selected_candidate=random_forest`, `model_selection_reason=best_validation_metric`, `rows_total=16,512`, and `r2=0.8801698812234392`.
- Docker API on `127.0.0.1:8000` is still the already-running baseline image until WSL/Compose can rebuild/retrain successfully. A Compose trainer run was attempted, but WSL transport hung and returned `Wsl/Service/0x8007274c`; do not claim Docker `8000` is promoted until `/model/metadata` from `8000` proves it.

Exposure forecast now has a real backend-backed lower-bound target:

- Terminal lifecycle remains separate and honest: current real DB/API evidence still has `lifecycle_target_rows=0`.
- API code now computes `observed_exposure_target_rows` from persisted repeated observations grouped by stable `(source_id, source_listing_id)` and using first observed date to last observed date.
- Temporary code-new API smoke on `127.0.0.1:8010` reported `observed_exposure_target_rows=7,456`, `observed_exposure_can_forecast=true`, median observed exposure `7` days, max `21` days, and `observed_exposure_target_source=observed_history_lower_bound`.
- Monitoring UI renders this as observed exposure/lower-bound provenance and includes segment median rows by rooms. This must be described as a forecast of observed exposure in the vitrine, not as confirmed sale/removal exposure.

Latest verification for this slice:

- `python -m pytest -p no:cacheprovider tests/test_ml_training.py tests/test_api_monitoring.py tests/test_config.py tests/test_streamlit_ui_payload.py -q`: `47 passed`.
- `python -m py_compile ...`: passed for touched Python files.
- `python -m ruff check ...`: passed for touched Python files.
- `API_BASE_URL=http://127.0.0.1:8010 python output\playwright\generate_static_audit.py`: passed with `api 16512 {'cian': 2436, 'domclick': 14076}`.
- `node output\playwright\cdp_static_grade5_audit.mjs`: passed against the static audit generated from code-new API `8010`; evidence included selected model provenance, exposure lower-bound readiness, terminal lifecycle target still `0`, real map tiles/popup/drag, and all seven screenshots with `clippedCount=0` and `overlapCount=0`.

Historical district comparison/clustering note from this earlier slice: local search had not yet found usable Moscow district boundary GeoJSON/shapefile. The later 2026-06-25 boundary update supersedes this with real `GIS-Lab/OpenStreetMap` district polygons and `84.47%` coverage. OSM feature support remains sparse and should not be overstated.

## 2026-06-24 Stitch Hybrid UI Update

The retained final UI branch is now `ui/stitch-hybrid-redesign-20260623` in workspace `E:\Магистр\2-курс\python\RealtyScope-stitch-hybrid-redesign-20260623`.

Current UI/static-audit evidence uses the real Docker API payload with `16,512` listings: `14,076` from `Домклик` and `2,436` from `ЦИАН`. The cautious Chrome headless/CDP audit `node output\playwright\cdp_static_grade5_audit.mjs` passed for the custom Stitch hybrid shell: valuation showed real comparable listings with source links, map tiles loaded, map zoom changed through button/wheel interaction, a listing popup showed real price/price per m²/rooms/area/floor/source, the data table kept address/source/rooms/area/floor/date/price/price per m², deal scoring used the real segment median/MAD/quantile rule, `Сегменты и районы` showed real segment analytics, no fake район ranking, and monitoring showed bounded logs without raw internal API trace text.

Analytic table polish update for this branch: `Данные` and `Выгодные предложения` now use compact analytic-table layouts so the important money/date/source/room/area/floor columns remain visible inside the desktop card. The valuation initial state also now says the default parameters are ready for calculation instead of telling the user to fill already-populated fields. Map popups now show an explicit `Открыть объявление` action only when the listing has a real `source_url`. The CDP audit now has explicit `data.importantColumnsVisible`, `deals.importantColumnsVisible`, `valuation.initialPromptHonest`, and `map.popupHasExplicitListingLink` gates, checks table fields by `data-sort` keys, waits for at least 8 loaded map tiles before screenshot capture, and the latest run passed with all screenshot `clippedCount=0` and `overlapCount=0` against Docker API payload `api 16512 {'cian': 2436, 'domclick': 14076}`.

Static audit hardening update for this branch: `output/playwright/generate_static_audit.py` now requires API mode, real `source_counts`, and at least 10,000 listings by default, with brief retries for cold API responses. It exits non-zero on offline/snapshot fallback unless `STATIC_AUDIT_ALLOW_OFFLINE=1` is set intentionally for debugging.

Map interaction hardening update for this branch: `output/playwright/cdp_static_grade5_audit.mjs` now includes the `map.dragPanChanged` gate. Earlier evidence passed with `loadedTiles=8`, `minimumLoadedTiles=8`, and pointer drag moving the stored map center from `{lon: 37.618423, lat: 55.751244}` to `{lon: 37.82441665234373, lat: 55.664199153470705}`. The later boundary slice passed with `loadedTiles=16/30`.

Dashboard recent-listings update for this branch: the dashboard `Новые поступления` card now renders the most recent real listings by observation timestamp, not the first arbitrary API payload rows. The CDP audit verifies `dashboard.hasRecentListingsFeed=true`, real external links in the feed, and `dashboard.recentListingsSortedByObservationDate=true` against the API-backed payload.

Data table order update for this branch: the `Данные` table now defaults to latest-first listing order by real observation timestamp while preserving per-column header sorting. The CDP audit verifies `data.defaultSortedByObservationDate=true` against the API-backed source links.

Data table date-format update for this branch: the `Данные` table now renders observation date and time as a clean two-line value without the locale comma, avoiding the earlier narrow-column wrap where the second line began with `, 01:25`. The CDP audit verifies `data.hasCleanDateFormatting=true` against rendered date cells.

Valuation update for this branch: the static UI payload now keeps a real local Ridge model fallback alongside live `/model/metadata`, so `Оценка квартиры` can return `Расчет модели` from the saved artifact when `/predict` is not reachable from the static/file audit context. The CDP audit now verifies `valuation.calculationUsesModelWhenAvailable=true`; a model-ready payload is no longer allowed to pass with only the median `Ориентир по базе` fallback. Comparable listings remain selected from real payload rows and the latest CDP run rendered `6` comparable rows with real external links.

Monitoring update for this branch: `/monitoring/status` now includes service rows for API, PostgreSQL, Redis cache, model, and ingestion. The Stitch hybrid monitoring page shows a `Статус контуров` card; in snapshot mode it marks API unavailable, the local UI vitrine/model/ingestion evidence available, and PostgreSQL/Redis as not verified rather than live. The CDP audit verifies those labels and still reports no raw internal/API trace text.

Historical district comparison update for this branch: this earlier slice used bounded full API analytics pages for partial district comparison extracted from explicit district text in source addresses. It had `districtComparison=12`, `listings_with_district=2,346`, `district_count=120`, and `coverage_pct=14.21`. The later boundary-backed update supersedes it with `coverage_pct=84.47`.

Historical district clustering update for this branch: the deterministic clustering UI was present only when real district comparison rows existed. Earlier CDP evidence had `districtClusters=12`, `cluster_count=3`, and `feature_source=districtComparison`; the later boundary-backed update supersedes it with `feature_source=districtComparison+boundary`. The remaining caveat is sparse OSM infrastructure coverage.

Exposure forecast update for this branch: monitoring now includes `Готовность прогноза экспозиции` from real payload evidence. Current Docker API evidence reports `42,765` persisted observations across `21` observed dates from `2026-05-14` to `2026-06-23`, `7,456` listing IDs with observation history, max `19` observed dates per listing, and `1,300` listing IDs with price changes. The current data still has `exposure_target_rows=0` and `canForecast=false`, so the UI does not show a fake exposure forecast.

Runtime PostgreSQL lifecycle check for this branch: the API data-quality helper now exposes observation lifecycle aggregates. Direct DB evidence from the running `realtyscope-db-1` container reports `42,765` observations, `21` observed dates from `2026-05-14` to `2026-06-23`, `7,456` source listing IDs with multiple observed dates, max `19` dates per listing, and `1,300` listing IDs with price changes. The same DB check reports `status=observed` and `active=true` for all `42,765` observation rows, so `lifecycle_target_rows=0`; this confirms repeated observation history exists, but no trustworthy terminal exposure target exists yet.

Observation trend update for this branch: monitoring now also includes `Готовность тренда`. Runtime PostgreSQL/API evidence reports `42,765` persisted observations across `21` observed dates, `7,456` listing IDs with history, and `1,300` listing IDs with price changes. This supports an honest descriptive trend/readiness panel, but `can_forecast=false`; there is still no verified time-series forecast model.

Observation trend series update for this branch: FastAPI now exposes `/stats/observation-trend?limit=60`, a backend-backed descriptive daily median series computed from persisted `listing_observations`. Latest live Docker evidence returned HTTP 200 for `/stats/observation-trend?limit=5` with `status=partial`, `metric=median_price_per_m2`, `can_forecast=false`, and rows from `2026-06-19` through `2026-06-23`. Static/CDP evidence now verifies `observationTrendSeries=21`, first date `2026-05-14`, last date `2026-06-23`, and CDP fails if the series disappears or no longer matches `observation_date_count`.

Model insight update for this branch: monitoring now includes `Контур модели` from real `/model/metadata` evidence. It displays the active model name, `baseline_ridge_v2_non_leaky`, `ml_features_v2_non_leaky`, train/test group counts when present, and a Russian caveat that this is a базовая Ridge-модель for the appraisal demo, not a final industrial estimator.

Live Docker runtime smoke for this branch was refreshed on `2026-06-24` after building `redis`, `mlflow`, `api`, and `streamlit` from this workspace. `docker compose -p realtyscope ps` showed `db`, `redis`, `api`, and `streamlit` healthy, with `mlflow` up on port `5000`. Localhost checks returned HTTP 200 for `/health`, filtered `/data?limit=3&offset=0&rooms=2&min_price_rub=10000000`, `/model/metadata`, `/monitoring/status`, Streamlit `/_stcore/health`, and MLflow root. Runtime `/monitoring/status` reported environment `docker`, `16,512` listings, `42,765` observations, `21` observation dates, `1,300` listing IDs with price changes, `lifecycle_target_rows=0`, and service rows `api/database/cache/model/ingestion=ok`. `/predict` returned `27,115,216.38` RUB for the full 23-feature demo vector with model `baseline_ridge_v2_non_leaky`, feature version `ml_features_v2_non_leaky`, metrics `rows_total=8,366` and `r2=0.6231827045433119`, plus the baseline caveat. MLflow registry responded with `realtyscope-price-model` version `4` status `READY`. Redis proof observed the filter-specific key `realtyscope:listings:v2:limit=1:offset=0:min_price_rub=10000000:rooms=2`; it expired quickly as expected for the short TTL path.

Operational caveat from the same smoke: after the long cold Docker build, a few new WSL launch attempts returned `Wsl/Service/0x8007274c`, while already-running localhost endpoints and containers continued responding. Treat this as an environment/transport flake, not as proof of an application failure; rerun short WSL checks before a live defense.

Do not overstate district clustering, exposure-duration forecast, or trend forecast on this branch. District comparison/clustering now have real boundary-backed evidence (`districtComparison=12`, `districtClusters=12`, `coverage_pct=84.47`, `feature_source=districtComparison+boundary`), but richer OSM infrastructure support is still sparse. Exposure forecasting is observed-history lower-bound only and still lacks terminal sale/removal lifecycle target rows. Trend forecasting now exists as a simple backend linear forecast over daily median price per m2; present it as an analytic forecast slice, not as production forecast-vs-actual validation.

## Branch And CI State

| Item | Status | Evidence |
| --- | --- | --- |
| Phase 6 branch | Preserved as milestone | `phase6-mlflow-redis-readiness` remains on local and remote at `30bce998...`. |
| Phase 7 branch | Preserved as milestone | `phase7-course-readiness-polish` remains on local and remote at `05f9b0c...`; it was fast-forward merged into `main`. |
| GitHub Actions on `main` | Passing after Phase 7 merge | `ci` run `26907933692`, SHA `05f9b0c...`, conclusion `success`. |
| GitHub Actions on Phase 7 | Passing before merge | Latest Phase 7 `ci` evidence is run `26907391574`, SHA `05f9b0c...`, conclusion `success`; earlier Phase 7 runs for `6cb103b`, `66bb5be`, `a5e2583`, and `83ad3e1` also passed. |
| Local verification after merge | Passing | On `main`, `git diff --check`, `ruff check .`, `ruff format --check .`, and full pytest `137 passed` with `-p no:cacheprovider` passed after the Phase 7 merge. |
| Latest runtime/UI evidence commit | Merged to `main` and CI-green | `05f9b0c docs: record final runtime evidence` records Docker/API/Redis/MLflow/Browser evidence after the tabbed Streamlit, filters, charts, and map slices. |
| GitNexus freshness | Stale for final `main` | `realtyscope-phase6-index` is indexed at `30bce998...`, while `main` is now beyond that commit. Refresh or create a Phase 7/final index before relying on graph impact after new Phase 7 commits. |

## Phase 7.1 Runtime Audit Snapshot

This section is historical evidence from the earlier `main` / Phase 7 runtime before the retained Stitch hybrid branch. It is kept for provenance only. Use the 2026-06-24 Stitch hybrid section above for current counts: `16,512` listings, `42,765` observations, and model version `4` in MLflow.

Fresh checks from 2026-06-03 on `main` after the Phase 7 merge:

| Check | Result | Evidence |
| --- | --- | --- |
| Docker runtime location | WSL2 Docker, not PowerShell PATH | PowerShell has no `docker` command; WSL reports Docker `29.2.1` and Compose `v5.1.0`. |
| Compose services | Running | `db`, `redis`, `api`, and `streamlit` are healthy; `mlflow` is up on port `5000`. |
| API health, docs, and prediction | HTTP 200 | `/health`, `/docs`, `/data?limit=3`, filtered `/data?limit=3&offset=0&rooms=2&min_price_rub=10000000`, `/predict`, `/model/metadata`, and `/monitoring/status` responded from localhost. The filtered data smoke returned `957` total rows; `/predict` returned `26,038,199.74` RUB for the default demo vector. |
| Redis runtime cache | Verified | Calling filtered `/data?limit=1&offset=0&rooms=2&min_price_rub=10000000` returned HTTP `200`; Redis then had key `realtyscope:listings:v2:limit=1:offset=0:min_price_rub=10000000:rooms=2`. |
| Data status | Healthy | Runtime DB has `3019` listings, `3191` raw listings, `3` ingestion runs, `0` rejected rows, and latest run status `success`. |
| Data readiness | Improved since older docs | `3019` listings, `3989` observations, `970` listings with multiple observations, `26` price changes, coordinate coverage `1.0`, ML-ready coverage `1.0`. |
| ML artifact and MLflow | Ready | `/model/metadata` reports active model `realtyscope-price-model`, `baseline_ridge_v2_non_leaky`, `ml_features_v2_non_leaky`, 23 features, and `rows_total=3019`; MLflow run `4999892d2d92402ab78e1209203c338e` is `FINISHED`, and registered model version `3` is `READY`. |
| Streamlit browser check | Loads and renders data | Browser DOM smoke shows `RealtyScope`, Phase 7 caption, all five tabs, sidebar `Page`, `Listings 3019`, `ML-ready 3019`, `Rejected 0`, `Runs 3`, and no warning/error logs. Earlier tab click smoke also verified Data Explorer row-window caption, Visuals charts/map attribution, Prediction output, and Monitoring last-success/model insight sections. |
| Current visible UI gap | Reduced | Streamlit works for the course demo with filters, reviewer-facing charts, coordinate map slice, tabs, and a real page/offset control. Optional narrow-viewport/screenshot evidence remains useful if the reviewer asks for responsive proof. |

## Course Requirement Status

Source requirements: `E:\Магистр\2-курс\python\MISIS_2025\season_2\Описание проекта.html`, `Примерный план семестра.htm`, and repository traceability docs under `docs/course-guidance/`.

| Requirement | Current status | Evidence | Remaining gap / future polish |
| --- | --- | --- | --- |
| One-command Docker project | Runtime smoke green | WSL `docker compose -p realtyscope ps` shows `db`, `redis`, `api`, and `streamlit` healthy, with `mlflow` up. Phase 6 verified `docker compose -p realtyscope up --build -d`; Phase 7 post-merge re-smokes run against the same Compose project. | Repeat the smoke after future code/runtime changes; safe cleanup instructions already warn before deleting containers, volumes, raw data, or model artifacts. |
| Automatic data collection | Implemented as bounded batch | Domclick Chrome/CDP capture, scheduled batch runner, Windows scheduled task, and ingestion status command exist. Current task is daily at `00:00` Moscow and last result was `0`. | Decide whether to keep daily or add a second run only after checking freshness value versus anti-abuse risk and duplicate-observation semantics. |
| PostgreSQL storage and Alembic | Implemented | SQLAlchemy 2.0 models, Alembic migrations, persisted listings, observations, OSM features, ingestion runs, and app logs. | Refresh data counts after any DB reset or new ingestion, not from old docs. |
| Data volume and quality | Runtime audit green | Current 2026-06-24 Stitch hybrid API/static audit reports `16,512` listings, `42,765` observations, `21` observed dates from `2026-05-14` to `2026-06-23`, `7,456` listings with observation history, `1,300` listing IDs with price changes, `16,512` ML-ready listings, and `5` rejected rows. | Use these current numbers in the demo, then re-run after any new ingestion or DB reset. |
| EDA and visual conclusions | Partial but data is improving | Phase 4 EDA docs cover cross-sectional data quality; fresh runtime data now has multiple observations for `970` listings and `26` detected price changes. Phase 7.3 adds reviewer-facing price distribution and room-summary charts. | Trend conclusions can become less conservative only after validating observation freshness and repeated capture semantics. |
| ML baseline and metrics | Implemented as honest baseline | `baseline_ridge_v2_non_leaky` removes latest-price leakage and uses grouped validation; Phase 6 adds Docker-backed MLflow evidence. | The model is still a baseline appraisal model. Forecast-vs-actual and richer model trust need repeated observations and/or final UI explanation. |
| MLflow MLOps | Implemented for baseline evidence | Current 2026-06-24 runtime evidence reports registered model `realtyscope-price-model` version `4` as `READY`; `/model/metadata` reports `baseline_ridge_v2_non_leaky`, `ml_features_v2_non_leaky`, 23 features, `rows_total=8,366`, and `r2=0.6231827045433119`. | Final demo should show MLflow URL and explain what is baseline versus final-quality claim. |
| FastAPI and Swagger | Usable, filter slice added | Runtime HTTP checks returned 200 for `/health`, `/docs`, `/data?limit=3`, filtered `/data`, `/predict`, `/model/metadata`, and `/monitoring/status`; tests cover contracts. Phase 7.2 adds `/data` and `/listings` filters for price range, area range, rooms, source, and text search. | Keep future query additions tested. Swagger is available at `/docs`; a browser click-through is optional unless the reviewer specifically asks. |
| Redis cache | Implemented and runtime-verified for filtered read path | Redis-backed `/listings` and `/data` read path is code/test-covered; latest runtime proof observed the filter-specific key `realtyscope:listings:v2:limit=1:offset=0:min_price_rub=10000000:rooms=2` after a live `/data` call. | Repeat the short Redis proof during the live demo if the reviewer asks for cache behavior evidence. |
| Streamlit dashboard | Implemented for course demo scope | Current Stitch hybrid CDP/static audit confirms the app renders runtime data: `16,512` listings, `16,512` ML-ready rows, `42,765` observations, `21` observed dates, source counts `Домклик=14,076` and `ЦИАН=2,436`, model-backed valuation, Data page sorting/pagination/export, real map tiles/popups, monitoring, model insights, and a real descriptive `observationTrendSeries=21` for the dashboard trend chart. | Optional richer metric/trend charts can be added only if they improve the defense without overstating repeated-observation maturity. Forecast wording must remain disabled until a verified time-series model exists. |
| Monitoring/logs | Clearer last-success display, bounded logs | `/monitoring/status` reports environment `docker`, current source/API/DB/cache/model/ingestion status, latest ingestion run success, `2,000` normalized records, and current data-quality counters. Streamlit displays bounded log pagination and hides raw internal traces. | Populate runtime `app_logs` more consistently if deeper operations evidence is needed. |
| Documentation and demo | Ready for Phase 7 course demo | README, course guidance docs, ML docs, operation docs, this status board, safe storage cleanup docs, and demo scripts exist. | Keep README/status current after future changes and use the demo script for any live defense smoke. |

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
- [x] Add a descriptive observation trend visual from persisted observation dates with conservative wording and `can_forecast=false`.
- [x] Verify desktop Browser DOM for tabs, data, visuals, prediction, monitoring, and no warning/error logs.
- [ ] Add narrow/mobile screenshot evidence only if final submission needs responsive proof; in-app Browser screenshot capture timed out during the Phase 7 UI slice.

### Phase 7.4: Demo Script And Course Submission Polish

Goal: make the defense path easy to follow.

- [x] Add a concise demo script: Docker start, verify data/API, open API docs, open Streamlit, run prediction, inspect MLflow, prove Redis, and stop services safely.
- [x] Add README runbook links and safe cleanup caveats.
- [x] Decide and document that Domclick remains daily for now; do not add a second daily trigger without fresh data value evidence and user approval.
- [x] Confirm GitHub Actions, local checks, Docker smoke, and browser check are green after this final docs/evidence slice and merge.

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

## 2026-06-24 Stitch Hybrid Source Metadata Update

- API code now restores real source metadata for `/data` and `/listings`: `source_name`, `source_label`, `source_listing_id`, `source_url`, and latest `observed_at`.
- API stats now expose real `source_counts` from DB source links. Local audit against the real runtime DB through temporary API `127.0.0.1:8010` reported `16,512` listings with `cian=2,436` and `domclick=14,076`.
- Streamlit static audit now uses a `5.0s` default API timeout instead of `0.5s`, preventing cold but healthy API calls from dropping to offline mode.
- Chrome/CDP audit was hardened with dynamic port selection, CDP command timeouts, and profile cleanup. Latest audit exited cleanly with `remaining_audit_chrome=0`.
- Docker runtime caveat: already-running API `127.0.0.1:8000` is healthy and model-ready but still uses the old image for this source-metadata slice. Rebuild/restart Docker API and Streamlit when Docker/WSL is available; Windows PATH had no Docker CLI and WSL returned `Wsl/Service/0x8007274c` in this session.

### Docker Runtime Refresh

- WSL later recovered enough to rebuild/restart Docker `api` and `streamlit` from this branch.
- After rebuild, Docker `127.0.0.1:8000` returns source metadata in `/data`, real `source_counts` in `/stats/data-quality`, ready model metadata, and monitoring service rows `api/database/cache/model/ingestion=ok`.
- Current Docker data evidence: `16,512` listings, `42,765` observations, `source_counts={'cian': 2436, 'domclick': 14076}`, `lifecycle_target_rows=0`.
- Current prediction evidence: `27,115,216.38317985` RUB for the full 23-feature demo vector, model `baseline_ridge_v2_non_leaky`, feature version `ml_features_v2_non_leaky`, `r2=0.6231827045433119`, baseline caveat present.
- Streamlit `/_stcore/health` returns `200 ok`; static audit without API override reports `api 16512 {'cian': 2436, 'domclick': 14076}`; CDP audit passed and ended with `remaining_audit_chrome=0`.
- Redis cache proof uses the new key namespace: `realtyscope:listings:v2:limit=1:offset=0:min_price_rub=10000000:rooms=2`.
- WSL is still intermittent after the rebuild; use localhost HTTP/Python Redis checks when WSL transport returns `Wsl/Service/0x8007274c`.

### Per-Page Visual Evidence

- Current Docker-backed CDP audit captures screenshots for dashboard, valuation, heatmap, deals, segments, data, and monitoring in `output/playwright/realtyscope-static-grade5-*.png`.
- Latest visual gate verifies `clippedCount=0` and `overlapCount=0` for all seven main pages.
- The map visual gate now requires at least one real tile image to load; latest run loaded `16` tiles and verified zoom/popup behavior.
- The latest map interaction gate requires at least 8 loaded tiles and verifies pointer-drag pan: earlier evidence used `loadedTiles=8`, `minimumLoadedTiles=8`, and `map.dragPanChanged=true`; the later boundary slice passed with `loadedTiles=16/30`.

## 2026-06-24 Count Discrepancy And Model Selection Update

- Runtime count investigation: current live API/DB endpoints agree on `16,512` listings. Verified `/stats/data-quality`, `/data?limit=1`, `/listings?limit=1`, and `/monitoring/status`; source mix is `cian=2,436`, `domclick=14,076`.
- The lower local count came from `output/cache/streamlit_ui_payload.json`, which is a stale but real snapshot fallback: `mode=snapshot`, `listings_total=15,765`, `loaded_snapshot_listings=15,765`, `source_counts={'domclick': 13324, 'cian': 2441}`. This explains the UI/API mismatch if Streamlit falls back to local snapshot mode while the API is unavailable or cold.
- Static audit regenerated after this investigation stayed on API data and printed `api 16512 {'cian': 2436, 'domclick': 14076}`.
- Model selection code is now present but not yet promoted live:
  - `train_selected_model()` trains multiple real candidates (`ridge`, `random_forest`) on one grouped validation split and writes `candidate_metrics` plus `selected_candidate` into the artifact.
  - CLI supports `--trainer baseline|selected`; default remains `baseline` to preserve the existing demo and tests.
  - API supports `MODEL_SELECTION_MODE=best_metric`, `MODEL_SELECTION_MODE=explicit`, and `MODEL_ARTIFACT_DIR`; `/model/metadata` exposes model selection provenance and training-candidate evidence.
  - Monitoring renders the model selection rows in Russian: `Выбор модели`, `Кандидатов`, `Выбранный алгоритм`.
- Verification for this code slice: `19 passed` for the targeted ML/API/config/UI tests, `py_compile` passed, `ruff` passed, and static audit passed with the full API count.
- Do not claim the live Docker model has changed yet. Current live evidence is still `baseline_ridge_v2_non_leaky` until a selected artifact is trained on the full DB, MLflow evidence is refreshed, and API/Streamlit are rebuilt/restarted from this branch.

## 2026-06-25 Docker Runtime Promotion And Trend Forecast Update

This addendum supersedes older notes in this document that said Docker `127.0.0.1:8000` still served the baseline image, that `/stats/exposure-forecast` returned `404`, or that trend `can_forecast=false`.

- Docker `api` and `streamlit` containers were hot-updated from the current branch source, package-installed where needed, and restarted with `docker compose -p realtyscope restart api streamlit`.
- Runtime health checks now pass on Docker ports:
  - `/health`: `status=ok`, `environment=docker`.
  - Streamlit `/_stcore/health`: `ok`.
  - `/stats/data-quality`: `listings_total=17,046`, `source_counts={'cian': 2436, 'domclick': 14610}`, `observations_total=44,765`, `observation_date_count=22`, `first_observed_date=2026-05-14`, `last_observed_date=2026-06-24`, `listings_with_observation_history=7,766`, `max_observation_dates_per_listing=20`, `listing_price_change_count=1,415`, `lifecycle_target_rows=0`, `observed_exposure_target_rows=7,766`.
  - `/model/metadata`: selected artifact `data/processed/models/phase5/selected_price_model_v1_non_leaky.joblib`, `model_version=selected_price_model_v1_non_leaky`, `selected_candidate=random_forest`, `model_selection_reason=best_validation_metric`, validation `r2=0.8801698812234392`, `mae=7,933,891.650272489`, `rows_total=16,512`. Do not imply this artifact was retrained on the latest `17,046` listing DB.
  - `/stats/exposure-forecast`: `status=ready`, `can_forecast=true`, `target_source=observed_history_lower_bound`, `terminal_lifecycle_target_rows=0`, `terminal_lifecycle_can_forecast=false`, `observed_exposure_target_rows=7,766`, median observed exposure `7` days, max observed exposure `22` days.
  - `/stats/observation-trend`: `status=ready`, `can_forecast=true`, `forecast_method=linear_median_price_per_m2_v1`, `forecast_horizon_days=7`, `history_points=22`, `trend_slope_per_day=-1648.29`, and forecast rows from `2026-06-25` through `2026-07-01`. This is a short-term analytic trend forecast over daily median price per m2, not forecast-vs-actual validation.
- Monitoring UI now renders those `forecast_rows` as a real table titled `Прогноз медианы за м²` instead of only showing the readiness flag.
- Verification:
  - `python -m py_compile services\api\app\main.py services\streamlit\app.py tests\test_api_monitoring.py tests\test_streamlit_ui_payload.py`: passed.
  - `python -m ruff check services/api/app/main.py services/streamlit/app.py tests/test_api_monitoring.py tests/test_streamlit_ui_payload.py`: passed.
  - `python -m pytest -p no:cacheprovider tests/test_api_monitoring.py tests/test_streamlit_ui_payload.py -q`: `39 passed`.
  - Earlier same-session targeted runtime slice: `python -m pytest -p no:cacheprovider tests/test_api_monitoring.py tests/test_streamlit_api_client.py tests/test_district_boundaries.py tests/test_streamlit_ui_payload.py tests/test_static_audit_requirements.py tests/test_docker_build_contract.py -q`: `58 passed`.
  - `python output\playwright\generate_static_audit.py`: passed in API mode with `api 17046 {'cian': 2436, 'domclick': 14610}`.
  - `node output\playwright\cdp_static_grade5_audit.mjs`: passed with `trend_status=ready`, `trend_can_forecast=true`, `exposure_status=ready`, selected-model provenance, real map tiles/zoom/drag/popup, and all seven screenshots at `clippedCount=0` / `overlapCount=0`.
- A later clean-image `docker compose -p realtyscope build streamlit` smoke was attempted, but it again spent more than 90 seconds inside `uv sync --frozen --no-dev --extra streamlit --no-install-project` downloading/installing heavy dependencies. The build process was terminated cleanly; no build process remained running, and runtime `/health` plus Streamlit `/_stcore/health` still passed. Treat final immutable image rebuild as a separate packaging task.
- Remaining truth caveats for the current runtime: terminal sale/removal exposure remains unavailable because `lifecycle_target_rows=0`; after the 2026-06-26 refresh, OSM infrastructure coverage is `17,046 / 17,287` (`98.61%`), with provenance from local extract + live Overpass + exact-coordinate derivation rather than all-live Overpass.

## 2026-06-25 Exposure Forecast Semantics Correction

This addendum supersedes older lines in this document that described `/stats/exposure-forecast`
as `status=ready` or `can_forecast=true` when only observed-history lower-bound rows were
available.

- Current verified local runtime for this branch is `http://127.0.0.1:8011` for FastAPI and
  `http://127.0.0.1:8509` for Streamlit. Docker CLI was not available in Windows PATH in this
  slice, so do not treat Docker port `8000` as freshly verified here.
- `/stats/data-quality` reports `listings_total=17,046`, `source_counts={'cian': 2436, 'domclick': 14610}`,
  `observations_total=44,765`, `observation_date_count=22`, observed dates `2026-05-14` through
  `2026-06-24`, `listings_with_observation_history=7,766`, max `20` dates per listing,
  `listing_price_change_count=1,415`, and `lifecycle_target_rows=0`.
- `/stats/exposure-forecast` now uses terminal lifecycle semantics for `can_forecast`: it returns
  `status=partial`, `can_forecast=false`, `terminal_lifecycle_target_rows=0`,
  `terminal_lifecycle_can_forecast=false`, `target_source=observed_history_lower_bound`,
  `observed_exposure_target_rows=7,766`, `observed_exposure_can_forecast=true`, median observed
  exposure `7` days, and max observed exposure `22` days. The lower-bound segment medians remain
  real diagnostics, but they are not a confirmed sale/removal exposure forecast.
- Monitoring UI wording was corrected from forecast wording to lower-bound wording:
  `Нижняя граница по комнатности`, `Строк наблюдений`, `Источник расчета`, and
  `Медиана нижней границы`.
- `/model/metadata` on the same runtime reports `model_version=selected_price_model_v1_non_leaky`,
  `selected_candidate=random_forest`, `feature_version=ml_features_v2_non_leaky`, `r2=0.850303822452758`,
  `mae=8,001,983.659500307`, and `rows_total=17,046`.
- `/stats/observation-trend?limit=60` remains a separate analytic trend forecast:
  `status=ready`, `can_forecast=true`, `forecast_method=linear_median_price_per_m2_v1`,
  horizon `7` days, `history_points=22`, and `forecast_rows=7`.
- Verification for this correction:
  - `python -m pytest -p no:cacheprovider tests/test_api_monitoring.py tests/test_streamlit_ui_payload.py tests/test_streamlit_api_client.py tests/test_api_data_routes.py -q`: `65 passed`.
  - `python -m py_compile services\api\app\main.py services\streamlit\app.py tests\test_api_monitoring.py tests\test_streamlit_ui_payload.py tests\test_streamlit_api_client.py output\playwright\generate_static_audit.py`: passed.
  - `python -m ruff check services/api/app/main.py services/streamlit/app.py tests/test_api_monitoring.py tests/test_streamlit_ui_payload.py tests/test_streamlit_api_client.py output/playwright/generate_static_audit.py`: passed.
  - `PYTHONPATH=src;. API_BASE_URL=http://127.0.0.1:8011 python output\playwright\generate_static_audit.py`: passed with `api 17046 {'cian': 2436, 'domclick': 14610}`.
  - `API_BASE_URL=http://127.0.0.1:8011 node output\playwright\cdp_static_grade5_audit.mjs`: passed with `exposure_status=partial`, `exposure_target_rows=0`, `marksExposureTargetMissing=true`, real map tile/zoom/drag/popup checks, and all seven screenshots at `clippedCount=0` / `overlapCount=0`.

## 2026-06-25 Data Count Provenance Update

- The UI payload now includes `dataCountProvenance` so the listing count is explicitly attributed
  to the live API, local snapshot fallback, or offline mode.
- Dashboard and Monitoring now render the count provenance in Russian. In API mode the visible
  detail is `API: 17 046 объявлений`; in snapshot fallback mode it uses `Локальный снимок: ...;
  API недоступен`.
- This addresses the 15k/17k confusion without pretending local snapshots are the current API/DB.
  Current verified API mode remains `17,046` listings; the older local snapshot cache was a real
  fallback artifact, not current API evidence.
- Verification:
  - `python -m pytest -p no:cacheprovider tests/test_streamlit_ui_payload.py tests/test_streamlit_api_client.py tests/test_api_data_routes.py tests/test_api_monitoring.py -q`: `67 passed`.
  - `python -m py_compile services\streamlit\app.py tests\test_streamlit_ui_payload.py`: passed.
  - `python -m ruff check services/streamlit/app.py tests/test_streamlit_ui_payload.py`: passed.
  - `PYTHONPATH=src;. API_BASE_URL=http://127.0.0.1:8011 python output\playwright\generate_static_audit.py`: passed with `api 17046 {'cian': 2436, 'domclick': 14610}`.
  - `API_BASE_URL=http://127.0.0.1:8011 node output\playwright\cdp_static_grade5_audit.mjs`: passed with `data_count_source=api`, `data_count=17046`, and `monitoring.rendersDataCountProvenance=true`.

## 2026-06-25 District Cluster OSM Caveat Update

- The district cluster panel now renders the cluster feature source and a direct OSM caveat.
  Current API evidence has `cluster_feature_source=districtComparison+boundary`, not
  `districtComparison+osm`, so the panel says the clusters are not claimed as
  OSM-infrastructure clusters and shows the confirmed OSM coverage.
- Current runtime evidence remains: district comparison coverage `84.47%` from
  `admin_boundary_geojson+address_text`, `districtComparison=12`, `districtClusters=12`,
  `cluster_count=3`, OSM coverage `436` rows / `2.56%`, and coverage source
  `live_overpass+coordinate_exact_match`.
- CDP Grade-5 audit now requires the no-overclaim caveat when district cluster rows exist but
  their feature source does not include `osm`.
- Verification:
  - `python -m pytest -p no:cacheprovider tests/test_streamlit_ui_payload.py -q`: `35 passed`.
  - `python -m py_compile services\streamlit\app.py tests\test_streamlit_ui_payload.py`: passed.
  - `python -m ruff check services/streamlit/app.py tests/test_streamlit_ui_payload.py`: passed.
  - `PYTHONPATH=src;. API_BASE_URL=http://127.0.0.1:8011 python output\playwright\generate_static_audit.py`: passed with `api 17046 {'cian': 2436, 'domclick': 14610}`.
  - `API_BASE_URL=http://127.0.0.1:8000 node output\playwright\cdp_static_grade5_audit.mjs`: passed with `cluster_feature_source=districtComparison+boundary`, `osm_rows=436`, `osm_coverage_pct=2.56`, and all screenshots clean.
