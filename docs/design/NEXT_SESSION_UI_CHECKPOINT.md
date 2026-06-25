# RealtyScope UI Next Session Checkpoint

## 2026-06-25 Current Docker Runtime After Retrain

- Compose reports `api`, `streamlit`, `db`, and `redis` healthy, with `mlflow` up.
- Docker `/model/metadata` now selects `random_forest` with `candidate_count=3`, `rows_total=17,046`, `train_rows=13,636`, `test_rows=3,410`, `r2=0.8653013476373554`, `mae=7,638,132.733793359`, `rmse=17,470,229.328815047`, and non-empty `feature_importance`.
- Training candidates are `random_forest`, `hist_gradient_boosting`, and `ridge`, evaluated on the same grouped split.
- Docker `/stats/data-quality` now reports full persisted OSM feature coverage: `osm_features_total=17,046`, `osm_featured_listings=17,046`, `osm_coverage_pct=100.0`, `osm_local_extract_rows=4,487`, `osm_live_rows=16`, `osm_coordinate_derived_rows=12,543`, `osm_infrastructure_coverage_source=local_extract+live_overpass+coordinate_exact_match`.
- Docker `/stats/exposure-forecast` remains `status=ready` for `observation_gap_inferred_lifecycle`, with `inferred_lifecycle_target_rows=4,962` and `terminal_lifecycle_target_rows=0`; do not call this confirmed sale/removal.
- This section supersedes older same-day notes below that mention `hist_gradient_boosting` as the current Docker-selected model or partial OSM coverage as the current state.

## 2026-06-25 Docker OSM And District OSM-Backed Checkpoint

- Docker API/Streamlit were rebuilt after the OSM provenance and district OSM feature fixes. Compose reports `api` and `streamlit` healthy.
- Docker `/stats/data-quality`: `osm_features_total=17,046`, `osm_featured_listings=17,046`, `osm_coverage_pct=100.0`, `osm_local_extract_rows=4,487`, `osm_live_rows=16`, `osm_coordinate_derived_rows=12,543`, `osm_infrastructure_coverage_source=local_extract+live_overpass+coordinate_exact_match`.
- Docker CDP now verifies `cluster_feature_source=districtComparison+boundary+osm` and `segments.clusterUsesOsm=true`, so district clustering is boundary-backed and OSM-feature-backed from persisted OSM rows.
- Docker static audit printed `api 17046 {'cian': 2436, 'domclick': 14610}`; Docker CDP passed all page gates, OSM provenance gates, district OSM-backed gate, and all seven screenshots with `clippedCount=0` / `overlapCount=0`.
- Targeted verification: `67 passed` for OSM/API/Streamlit/static-audit tests, targeted `ruff`, targeted `py_compile`, and `node --check` for the CDP script.
- Remaining caveats: no XGBoost result is claimed; terminal confirmed sale/removal rows remain `0`.

## 2026-06-25 OSM Local Extract Provenance Update

- Current code plus real PostgreSQL evidence now supersedes the older `448 / 17,046` OSM checkpoint: `osm_features_total=17,046`, `osm_featured_listings=17,046`, `osm_coverage_pct=100.0`.
- Provenance is now split honestly: `osm_local_extract_rows=4,487`, `osm_live_rows=16`, `osm_coordinate_derived_rows=12,543`, `osm_infrastructure_coverage_source=local_extract+live_overpass+coordinate_exact_match`.
- Source: real local BBBike Moscow OpenStreetMap extract at `data/cache/osm/Moscow.osm.geojson.xz`, with `source_summary.source=bbbike_geojson_extract` and `OpenStreetMap contributors` attribution.
- Streamlit payload now carries `localExtractRows`; the infrastructure panel distinguishes local extract, Overpass, and exact-coordinate-derived rows with Russian labels.
- Verification: `python -m pytest -p no:cacheprovider tests/test_osm_enrichment.py tests/test_api_data_routes.py tests/test_streamlit_ui_payload.py -q` passed with `64 passed`; targeted `ruff` and `py_compile` passed.
- Code-new local runtime proof passed on API `127.0.0.1:8014` and Streamlit `127.0.0.1:8512`: static audit printed `api 17046 {'cian': 2436, 'domclick': 14610}`; CDP verified `osm_rows=17046`, `osm_local_extract_rows=4487`, `osm_coordinate_derived_rows=12543`, `osm_coverage_source=local_extract+live_overpass+coordinate_exact_match`, `monitoring.rendersOsmLocalExtractRows=true`, all page gates, and all seven screenshots with `clippedCount=0` / `overlapCount=0`.
- Runtime caveat: Docker `127.0.0.1:8000` still showed the old source string during this update because WSL failed with `Wsl/Service/0x8007274c` before rebuild. Rebuild Docker API/Streamlit and rerun static/CDP audits before treating `8000/8501` as final Docker runtime evidence for this OSM provenance change.

## 2026-06-25 Historical Docker Runtime Reloaded To HistGradientBoosting

Historical note: this block is superseded by "2026-06-25 Current Docker Runtime After Retrain" above. It is kept as provenance for an earlier same-day artifact that selected `hist_gradient_boosting` and still had partial OSM coverage.

- Docker API/Streamlit have now been rebuilt and restarted from `ui/stitch-hybrid-redesign-20260623` with `docker compose -p realtyscope up -d --build api streamlit` via WSL.
- Compose reports `api` and `streamlit` healthy, `db` and `redis` healthy, and `mlflow` up.
- Docker `/model/metadata` now matches the latest selected artifact: `selected_candidate=hist_gradient_boosting`, `candidate_count=3`, `rows_total=17,046`, `train_rows=13,636`, `test_rows=3,410`, `r2=0.8994355561733502`, `mae=6,188,596.253660057`, `rmse=15,095,211.71856097`.
- Same-split candidate metrics in Docker metadata: `random_forest r2=0.8505952988269576, mae=7,989,464.3271694975`; `ridge r2=0.556166053792913, mae=16,651,213.37086019`.
- Leakage guardrails remain confirmed: grouped train/test listing IDs are disjoint by construction (`listing_id_grouped_random`), and runtime feature names do not include `price`.
- Docker `/stats/data-quality`: `listings_total=17,046`, `source_counts={'cian': 2436, 'domclick': 14610}`, `observations_total=44,765`, `observation_date_count=22`, `lifecycle_target_rows=0`, `inferred_lifecycle_target_rows=4,962`, `osm_features_total=448`, `osm_featured_listings=448`, `osm_coverage_pct=2.63`, `osm_live_rows=16`, `osm_coordinate_derived_rows=432`.
- Docker `/stats/exposure-forecast`: `target_source=observation_gap_inferred_lifecycle`, `inferred_lifecycle_target_rows=4,962`, `terminal_lifecycle_target_rows=0`; keep wording honest that this is disappearance from observations, not confirmed sale/removal.
- Static audit against Docker passed with `api 17046 {'cian': 2436, 'domclick': 14610}`.
- CDP Grade-5 audit against Docker passed and verified Monitoring renders `hist_gradient_boosting` as `градиентный бустинг`, map `loadedTiles=30/30`, district comparison remains `admin_boundary_geojson+address_text`, clusters remain `districtComparison+boundary`, and all seven screenshots are clean (`clippedCount=0`, `overlapCount=0`).
- Remaining caveats: no XGBoost result is claimed; OSM coverage is still partial at `448 / 17,046` (`2.63%`), so district clustering is still boundary-backed, not broadly OSM-backed.

## 2026-06-25 Historical Expanded Model, OSM Rate Limit, And Verification Caveat

- Selected-model training now has three real candidates: `ridge`, `random_forest`, and `hist_gradient_boosting`.
- Current selected artifact: `data/processed/models/phase5/selected_price_model_v1_non_leaky.joblib`, feature version `ml_features_v2_non_leaky`, `selected_candidate=hist_gradient_boosting`, `candidate_count=3`, `rows_total=17,046`, `train_rows=13,636`, `test_rows=3,410`, `r2=0.8994355561733502`, `mae=6,188,596.253660057`, `rmse=15,095,211.71856097`.
- Candidate metrics from the same grouped split: `random_forest r2=0.8496374735904109, mae=8,008,821.77078574`; `ridge r2=0.5562438473500875, mae=16,654,440.34608464`.
- `xgboost` is not installed or locked in `pyproject.toml` / `uv.lock`; no XGBoost result is claimed.
- Split/leakage guardrail: selected training uses `listing_id_grouped_random`, duplicate listing rows stay on only one side of train/test, and selected non-leaky artifacts exclude feature names containing `price`.
- Fresh code-new API `127.0.0.1:8013/model/metadata` proved the new artifact while that temporary process was running. Docker API `127.0.0.1:8000` stayed healthy but still held the previous in-memory `random_forest` model because Docker CLI is unavailable in Windows PATH for restart/rebuild.
- After stopping stale local API/Streamlit Python processes, static audit and CDP were refreshed against API `127.0.0.1:8013`. Static audit printed `api 17046 {'cian': 2436, 'domclick': 14610}`. CDP passed all page/layout gates and explicitly verified `monitoring.selectedCandidate=hist_gradient_boosting`, `expectedSelectedCandidateLabel=градиентный бустинг`, and `rendersSelectedCandidateName=true`.
- OSM search still found no usable local extract/cache. A logged live Overpass batch with `limit=10` inserted `4` rows but hit `HTTP 429 Too Many Requests` for `6` rows; exact-coordinate derivation inserted `8` rows.
- API `/stats/data-quality` after this OSM slice: `osm_features_total=448`, `osm_featured_listings=448`, `osm_coverage_pct=2.63`, `osm_live_rows=16`, `osm_coordinate_derived_rows=432`, `rows_available=4,487` missing distinct coordinates.
- Stop live Overpass for now because rate limiting is proven. District clustering remains `districtComparison+boundary`, not OSM-backed.
- Verification passed in this slice: `tests/test_ml_training.py` (`11 passed`), `tests/test_api_monitoring.py tests/test_config.py` (`13 passed`), targeted Streamlit model/fallback tests (`2 passed`), `tests/test_osm_enrichment.py` (`13 passed`), `py_compile`, and `ruff`.

## 2026-06-25 OSM Logged Batch And Coverage Slice

- Added `--progress-log` support to `python -m realtyscope.enrichment.osm`. The CLI now appends one JSONL evidence row after successful dry-run/write/derive commands with operation, limit, radius, delay, timeout, selected listing IDs, row counts, errors, and result payload.
- No real local OSM extract/cache was found in the repo root, parent project folder, or top-level Downloads scan. This slice used a controlled live Overpass batch instead of fabricating coverage.
- Logged dry-run evidence in `output/osm-enrichment/overpass-batches-20260625.jsonl`: `rows_available=4,493`, `rows_selected=2`, `selected_listing_ids=[7, 8]`.
- Logged live Overpass batch used `--limit 2`, `--radius-m 1000`, `--delay-seconds 2`, `--timeout-seconds 25`; it inserted `2` real OSM rows with `rows_failed=0`.
- Logged exact-coordinate derivation inserted `17` rows with `rows_failed=0` and no live OSM call.
- Selector after the batch reports `rows_available=4,491`, `rows_selected=5`, first selected IDs `[10, 11, 13, 15, 16]`.
- Docker API `/stats/data-quality` now reports `osm_features_total=436`, `osm_featured_listings=436`, `osm_coverage_pct=2.56`, `osm_live_rows=12`, `osm_coordinate_derived_rows=424`, and `osm_infrastructure_coverage_source=live_overpass+coordinate_exact_match`.
- Static audit with Docker API passed: `api 17046 {'cian': 2436, 'domclick': 14610}`.
- CDP Grade-5 audit with Docker API/Streamlit passed with `osm_rows=436`, `osm_coverage_pct=2.56`, `osm_coordinate_derived_rows=424`, `cluster_feature_source=districtComparison+boundary`, real map zoom/drag/popup, and all seven screenshots at `clippedCount=0` / `overlapCount=0`.
- Verification for touched OSM code passed: `tests/test_osm_enrichment.py` (`13` tests), `py_compile`, and `ruff`.
- Remaining caveat: district clustering is still boundary-backed, not broadly OSM-backed. Confirmed OSM infrastructure coverage is only `436 / 17,046` listings (`2.56%`).
- GitNexus mirror `realtyscope-stitch-hybrid-redesign-20260625-dirty-worktree` was not used after this CLI change; refresh/check freshness before using GitNexus for `src/realtyscope/enrichment/osm.py`.

## 2026-06-25 Inferred Lifecycle Exposure Forecast Slice

- Added a real exposure forecast path from repeated observation gaps without fabricating terminal sale/removal events. Terminal confirmed lifecycle rows remain `0`.
- New API semantics on code-new runtime `127.0.0.1:8012`:
  - `/stats/exposure-forecast`: `status=ready`, `can_forecast=true`, `target_source=observation_gap_inferred_lifecycle`, `method=gap_inferred_lifecycle_median_v1`.
  - `terminal_lifecycle_target_rows=0`, `terminal_lifecycle_can_forecast=false`.
  - `inferred_lifecycle_target_rows=4,962`, `inferred_lifecycle_min_gap_days=3`, `inferred_lifecycle_median_days=6`, `inferred_lifecycle_max_days=19`.
  - Observed lower-bound remains separate: `observed_exposure_target_rows=7,766`, median `7`, max `22`.
- Streamlit Monitoring now renders inferred disappearance target rows and the minimum observation gap. The visible UI wording stays Russian and distinguishes inferred disappearance from confirmed sale/removal.
- Runtime started for inspection: API `http://127.0.0.1:8012`, Streamlit `http://127.0.0.1:8510`. Docker/WSL `8000/8501` remains unstable: WSL returned `Wsl/Service/0x8007274c`, `8501` is held by `wslrelay.exe`, and Docker model metadata on `8000` is still older than the code-new selected artifact.
- Verification:
  - `python -m pytest -p no:cacheprovider tests/test_api_data_routes.py tests/test_api_monitoring.py tests/test_streamlit_api_client.py tests/test_streamlit_ui_payload.py -q`: `69 passed`.
  - Broad sweep after the CDP fix also passed: `python -m pytest -p no:cacheprovider tests -q`, `python -m ruff check src services tests`, and `python -m compileall -q src services tests`.
  - `python -m ruff check services/api/app/main.py services/streamlit/app.py tests/test_api_data_routes.py tests/test_api_monitoring.py tests/test_streamlit_ui_payload.py`: passed.
  - `python -m py_compile services/api/app/main.py services/streamlit/app.py tests/test_api_data_routes.py tests/test_api_monitoring.py tests/test_streamlit_ui_payload.py`: passed.
  - `PYTHONPATH=src;. API_BASE_URL=http://127.0.0.1:8012 python output\playwright\generate_static_audit.py`: passed with `api 17046 {'cian': 2436, 'domclick': 14610}`.
  - CDP visual audit was updated for the new exposure semantics and passed after diagnostic timeout hardening. Latest evidence includes `exposure_status=ready`, `exposure_inferred_target_rows=4962`, `exposure_target_source=observation_gap_inferred_lifecycle`, `map.loadedTiles=30/30`, real popup fields/link, and all seven screenshots at `clippedCount=0` / `overlapCount=0`.
- GitNexus dirty mirror was force re-indexed after this slice at `C:\Users\lequa\gitnexus-worktrees\realtyscope-stitch-hybrid-redesign-20260625-dirty-worktree`: `3,143` nodes, `6,257` edges, `87` clusters, `200` flows. Impact for `_inferred_lifecycle_exposure_stats` is high through `data_quality_stats`, `exposure_forecast_stats`, and `monitoring_status`, which are covered by the targeted tests above.

## 2026-06-25 Broad Verification And Dirty GitNexus Mirror

- Full local verification passed after the latest backend/UI slices: `python -m pytest -p no:cacheprovider tests -q`, `python -m ruff check src services tests`, and `python -m compileall -q src services tests`.
- Runtime code-new API/Streamlit ports are healthy: API `127.0.0.1:8011` reports `status=ok`, Streamlit `127.0.0.1:8509/_stcore/health` reports `ok`.
- Current runtime data evidence on API `8011`: `17,046` listings, `source_counts={'cian': 2436, 'domclick': 14610}`, `44,765` observations, `22` observation dates, `lifecycle_target_rows=0`, and `observed_exposure_target_rows=7,766`.
- Current selected model evidence: `selected_price_model_v1_non_leaky`, `selected_candidate=random_forest`, `feature_version=ml_features_v2_non_leaky`, `r2=0.850303822452758`, `mae=8,001,983.659500307`, and `rows_total=17,046`.
- Static audit regenerated from API `8011`: `api 17046 {'cian': 2436, 'domclick': 14610}`.
- CDP Grade-5 audit passed: map tiles/zoom/drag/popup, valuation comparables, data/deals tables, district comparison/clustering caveats, monitoring/model/source panels, and all seven screenshots were clean with `clippedCount=0` and `overlapCount=0`.
- GitNexus in the Cyrillic repo path still fails to analyze directly on `.gitnexus\lbu/lbug`. A dirty-worktree ASCII mirror was created at `C:\Users\lequa\gitnexus-worktrees\realtyscope-stitch-hybrid-redesign-20260625-dirty-worktree` and indexed successfully with `3,130` nodes, `6,239` edges, `86` clusters, and `202` flows. Use this repo name in GitNexus for current dirty-source relationship checks.
- Do not claim the goal fully complete yet: terminal lifecycle exposure target rows remain `0`, and OSM infrastructure coverage remains partial at `436 / 17,046` listings (`2.56%`).

## 2026-06-25 OSM Exact-Coordinate Coverage Slice

- Added backend support to derive OSM feature rows for listings that share the exact same coordinates as an already persisted live Overpass OSM row. This does not invent infrastructure: copied rows are marked with `source_summary.derivation=coordinate_exact_match`, `derived_from_listing_id`, `source_live_osm_called`, and `live_osm_called=false`.
- CLI support: `python -m realtyscope.enrichment.osm --derive-coordinate-matches --write --limit 10000 --json`.
- Live DB write evidence: first run inserted `380` derived rows with `rows_failed=0`; second run was idempotent with `rows_inserted=0`.
- At that slice, the API reported `osm_features_total=417`, `osm_featured_listings=417`, `osm_coverage_pct=2.45`, `osm_live_rows=10`, `osm_coordinate_derived_rows=407`, and `osm_infrastructure_coverage_source=live_overpass+coordinate_exact_match`.
- Streamlit `osmCoverage` now carries `coordinateDerivedRows` and `coverageSource`; Monitoring renders `Строк по точным координатам` in the infrastructure panel.
- CDP audit now records `osm_coordinate_derived_rows=380`, `osm_coverage_source=live_overpass+coordinate_exact_match`, and verifies `monitoring.rendersOsmCoordinateDerivedRows=true`.
- Verification: `54 passed` for OSM/API/Streamlit payload tests; `py_compile` passed for touched Python files; `ruff` passed; static audit and CDP audit passed against `API_BASE_URL=http://127.0.0.1:8011`.
- Remaining caveat: this improves honest OSM coverage from `9` rows / `0.05%` to `417` rows / `2.45%`, but it is still partial and not broad OSM-infrastructure backing for all districts.

## 2026-06-25 Boundary-Backed District Analytics Slice

- District comparison and district clustering are no longer only address-text analytics. The current branch now uses real Moscow district boundary polygons from `data/external/moscow_district_boundaries.geojson`, with provenance in `data/external/moscow_district_boundaries.metadata.json`: `GIS-Lab/OpenStreetMap`, `http://gis-lab.info/qa/osm-adm.html`.
- Added `src/realtyscope/analysis/district_boundaries.py` for GeoJSON `Polygon` / `MultiPolygon` lookup, bbox prefiltering, point-in-polygon with holes, district-name normalization, and UTF-8-BOM-tolerant metadata loading.
- Streamlit district assignment now prefers boundary GeoJSON matches from real `latitude` / `longitude`, then structured district fields, then address-text fallback.
- Fresh payload evidence: `listings_total=17,046`, `boundary_matched_rows=14,386`, `boundary_coverage_pct=84.4`, `listings_with_district=14,399`, `coverage_pct=84.47`, `district_count=125`, `districtComparison=12`, `districtClusters=12`, `active_field=boundary_geojson`, `extraction_source=admin_boundary_geojson+address_text`, and `cluster_feature_source=districtComparison+boundary`.
- GitNexus mirror `C:\\Users\\lequa\\gitnexus-worktrees\\realtyscope-stitch-hybrid-redesign-20260625-index` was refreshed after this slice and indexed with `3,068` nodes, `6,093` edges, `85` clusters, and `198` flows. Impact for `_district_assignment_series` is high through district readiness/comparison payload builders and `main`.
- Verification: `38 passed` for `tests/test_district_boundaries.py`, `tests/test_streamlit_ui_payload.py`, and `tests/test_static_audit_requirements.py`; `py_compile` passed for touched Python files; `ruff` passed for touched source/tests; static audit printed `api 17046 {'cian': 2436, 'domclick': 14610}`; CDP passed with `loadedTiles=16/30`, boundary-backed district evidence, real map zoom/drag/popup checks, and all seven screenshots at `clippedCount=0` / `overlapCount=0`.
- Remaining caveat after that slice: OSM infrastructure coverage was still sparse (`417` featured listings / `2.45%`, mostly exact-coordinate derived), so district clustering remained boundary-backed but not broadly OSM-backed.

## 2026-06-25 Selected Model, GitNexus Mirror, And Map Tile Update

- Code-new API `127.0.0.1:8011` now exposes the refreshed selected artifact `selected_price_model_v1_non_leaky.joblib` with `selected_candidate=random_forest`, `feature_version=ml_features_v2_non_leaky`, `rows_total=17,046`, `r2=0.850303822452758`, and `mae=8,001,983.659500307`.
- The CLI trainer default is now the selected non-leaky path (`--trainer selected`, `--feature-version ml_features_v2_non_leaky`), and `Settings.active_model_artifact_path` points at the selected non-leaky artifact.
- Direct GitNexus analysis on the Cyrillic worktree still failed, so a mirror index was created at `C:\Users\lequa\gitnexus-worktrees\realtyscope-stitch-hybrid-redesign-20260625-index` and successfully indexed with `2,958` nodes, `5,883` edges, `80` clusters, `193` flows. It was later refreshed after boundary work to `3,068` nodes, `6,093` edges, `85` clusters, and `198` flows.
- Map tile rendering now uses real OpenStreetMap tiles first, with CARTO/HOT as fallbacks. The CDP audit passed after increasing the tile wait window in the harness; this slice had `loadedTiles=8` of `30`, and the later boundary slice passed with `loadedTiles=16/30`. Popup links were real, zoom and drag changed state, and all seven screenshots stayed unclipped/overlap-free.
- Fresh API evidence on `8011` still shows `17,046` listings, `44,765` observations, `22` observation dates, `lifecycle_target_rows=0`, and observed-exposure lower-bound evidence (`observed_exposure_target_rows=7,766`, `observed_exposure_can_forecast=true`, `target_source=observed_history_lower_bound`) while terminal exposure `can_forecast=false`.

## 2026-06-25 Live Data Refresh And Docker Caveat

- WSL/Compose rebuild is still not verified. Existing localhost Docker endpoints stayed reachable, but new WSL command startup returned `Wsl/Service/0x8007274c`; Docker CLI is not available in Windows PATH. Do not claim Docker `8000` has the new endpoint/model code until WSL is stable enough to rebuild and verify it.
- Docker API `127.0.0.1:8000` is still an older image for code shape: `/model/metadata` reports `baseline_ridge_v2_non_leaky`, and `/stats/exposure-forecast` returns `404`.
- The live DB behind Docker has refreshed real data. Docker/API `/stats/data-quality` and code-new API `8010` both show the fresher dataset direction.
- Code-new API was run on `127.0.0.1:8010` with `PYTHONPATH=src;.` against live DB/Redis ports. Fresh evidence:
  - `listings_total=17,046`
  - `source_counts={'cian': 2436, 'domclick': 14610}`
  - `observations_total=44,765`
  - `observation_date_count=22`
  - observed dates `2026-05-14` through `2026-06-24`
  - `listings_with_observation_history=7,766`
  - `max_observation_dates_per_listing=20`
  - `listing_price_change_count=1,415`
  - `lifecycle_target_rows=0`
  - `observed_exposure_target_rows=7,766`
  - latest successful Domclick run id `25`, started `2026-06-24T21:13:03.741795+00:00`, `records_seen=2,000`, `inserted_count=3,612`, `updated_count=1,466`, `rejected_count=0`
- `/stats/exposure-forecast` on code-new API returned `status=ready`, `can_forecast=true`, `target_source=observed_history_lower_bound`, terminal lifecycle target `0`, observed target rows `7,766`, median observed exposure `7` days, max `22` days.
- `/model/metadata` on code-new API returned `selected_price_model_v1_non_leaky`, `selected_candidate=random_forest`, `r2=0.8801698812234392`, `rows_total=16,512`. This selected model artifact has not been retrained on the refreshed 17,046-row DB yet.
- Static audit regenerated against code-new API: `api 17046 {'cian': 2436, 'domclick': 14610}`.
- CDP audit passed with the refreshed payload: observed-history lower-bound exposure evidence was present, terminal lifecycle target still `0`, trend series rows `22`, district coverage `13.8%` address-text only at that time, OSM coverage still `9` rows / `0.05%`, selected model provenance, map/tables working, and all seven screenshots at `clippedCount=0` / `overlapCount=0`. The district and exposure wording from this earlier slice is superseded by the later boundary-backed and terminal-forecast semantics slices above.

## 2026-06-24 Exposure Forecast Endpoint And Client Wiring Slice

- Added dedicated FastAPI endpoint `GET /stats/exposure-forecast` for exposure forecast/readiness.
- The endpoint keeps terminal lifecycle evidence honest and separate: current real DB evidence still has `terminal_lifecycle_target_rows=0` and `terminal_lifecycle_can_forecast=false`.
- The endpoint exposes the real observed-history lower-bound forecast from persisted repeated observations: `target_source=observed_history_lower_bound`, `observed_exposure_target_rows=7,456`, median observed exposure `7` days, max `21` days, and room-segment medians. This is a lower-bound forecast from first to last observed date, not confirmed sale/removal exposure.
- Streamlit `DashboardData` now carries `exposure_forecast`; `fetch_dashboard_data()` requests `/stats/exposure-forecast`; `_build_payload()` passes it into `exposureReadiness` and prefers it over stale/missing embedded data-quality fields when the endpoint is available.
- Code-new API on `127.0.0.1:8010` was run with `PYTHONPATH=src;.` because plain Python imports `realtyscope` from the older sibling worktree otherwise.
- Code-new API evidence: `/stats/data-quality` stayed at `16,512` listings with `source_counts={'cian': 2436, 'domclick': 14076}`; `/stats/exposure-forecast` returned `status=ready`, `can_forecast=true`, `target_source=observed_history_lower_bound`, terminal lifecycle target `0`, observed target rows `7,456`; `/model/metadata` returned selected local artifact `selected_price_model_v1_non_leaky`, `selected_candidate=random_forest`, `r2=0.8801698812234392`, `rows_total=16,512`.
- Verification: targeted API/client/UI payload pytest passed with `49 passed`; `py_compile` passed; `ruff` passed; static audit against code-new API `8010` printed `api 16512 {'cian': 2436, 'domclick': 14076}`; CDP passed with observed-history lower-bound exposure evidence, selected model provenance, terminal lifecycle target still `0`, and all seven screenshots at `clippedCount=0` / `overlapCount=0`. Later semantics correction keeps terminal exposure `can_forecast=false`.
- Caveat: Docker API `127.0.0.1:8000` was not rebuilt in this slice and still reports the older baseline model/runtime. Do not use Docker `8000` as proof of selected model or `/stats/exposure-forecast` until Compose is rebuilt/restarted and endpoints on `8000` prove it.

## 2026-06-24 Selected Model And Observed Exposure Forecast Slice

- Finished the Streamlit metric-priority fix: UI model-quality/provenance blocks now prefer live API model metrics (`data.model.metrics`) over the local Ridge fallback. The local model remains only an honest offline/static fallback for valuation calculation when `/predict` is unavailable.
- `services/trainer/Dockerfile` now defaults to `--trainer selected`, so the Docker trainer path will train the candidate selector instead of silently producing only the Ridge baseline.
- Local selected artifact evidence: `data/processed/models/phase5/selected_price_model_v1_non_leaky.joblib` is chosen by the API selector with `selected_candidate=random_forest`, validation `r2=0.8801698812234392`, `mae=7,933,891.650272489`, and `rows_total=16,512`.
- Temporary code-new API on `127.0.0.1:8010` exposed that selected artifact in `/model/metadata`. The already-running Docker API on `127.0.0.1:8000` still reports the older baseline until Docker/WSL can rebuild/retrain and `/model/metadata` from `8000` proves promotion.
- A Docker trainer run was attempted with `--trainer selected`, but WSL/Docker transport hung during image build and follow-up WSL calls returned `Wsl/Service/0x8007274c`. The hung process was cleaned up; localhost Docker API `8000` stayed healthy.
- Added real observed-exposure lower-bound forecast support. API data-quality stats now compute `observed_exposure_target_rows` from repeated persisted observations using first observed date to last observed date per stable source listing. This does not change the terminal lifecycle truth: current `lifecycle_target_rows=0`.
- Code-new API evidence: `observed_exposure_target_rows=7,456`, `observed_exposure_can_forecast=true`, `observed_exposure_median_days=7`, `observed_exposure_max_days=21`, `observed_exposure_target_source=observed_history_lower_bound`.
- Monitoring UI now renders `Наблюдаемая экспозиция`, `Источник прогноза`, and a `Прогноз по комнатности` table from real segment medians. Present this as observed-exposure/lower-bound forecast only, not confirmed sale/removal exposure.
- Historical note: district/admin-boundary coverage was blocked in this earlier slice. The later 2026-06-25 boundary-backed slice supersedes this with a usable Moscow boundary GeoJSON and verified `84.47%` district coverage.
- Verification after this slice: `47 passed` for targeted ML/API/Streamlit tests, `py_compile` passed, `ruff` passed, static audit against code-new API `8010` printed `api 16512 {'cian': 2436, 'domclick': 14076}`, and CDP passed with selected model provenance, observed exposure forecast readiness, terminal lifecycle target still `0`, and all seven screenshots `clippedCount=0` / `overlapCount=0`.

## 2026-06-24 OSM Coverage And District Matrix Slice

- Added backend OSM coverage evidence to `/stats/data-quality`: `osm_features_total`, `osm_featured_listings`, `osm_coverage_pct`, `osm_feature_version`, `osm_attribution`, and `osm_live_rows`.
- `/data` / `/listings` now include persisted OSM feature fields for listings that have `osm_features`: `osm_feature_version`, `osm_attribution`, `transport_count_500m`, `transport_count_1000m`, `nearest_transport_m`, `schools_count_1000m`, `parks_count_1000m`, `shops_count_1000m`, and `healthcare_count_1000m`.
- Streamlit `osmCoverage` now carries backend coverage rows, featured listing count, coverage percent, feature version, attribution, and live-row count. The monitoring infrastructure panel renders these values instead of leaving coverage as unknown when the API has real rows.
- District comparison aggregates OSM feature medians per district when OSM columns are present. District clustering includes those OSM columns in its deterministic feature matrix and marks `feature_source=districtComparison+osm` when the matrix actually has OSM features. In this earlier slice, address-text-only clusters remained marked `districtComparison`; the later boundary slice supersedes the district source with `districtComparison+boundary`.
- Live Overpass enrichment was attempted with a small bounded batch (`limit=20`, `delay=0.5s`, `timeout=20s`) to avoid fabricated infrastructure data. Result: `rows_inserted=5`, `rows_updated=2`, `rows_failed=13` due Overpass `429 Too Many Requests` and `504 Gateway Timeout`. No further batch was run to avoid abusive retry pressure.
- Latest live API evidence after the batch: `osm_features_total=9`, `osm_featured_listings=9`, `osm_coverage_pct=0.05`, `osm_feature_version=osm_local_v1`, `osm_attribution=OpenStreetMap contributors`, `osm_live_rows=9`; `/data?limit=25` returned 9 rows with OSM fields.
- Static/CDP evidence: static payload has `osmCoverage.coverageRows=9`, `coveragePct=0.05`, `attribution=OpenStreetMap contributors`; CDP now fails `payload.hasOsmCoverageEvidence` if this disappears. At that time district clusters still showed `cluster_feature_source=districtComparison` because 9 OSM rows were not enough to make the district aggregate matrix OSM-backed; the later boundary slice changes the district source to `districtComparison+boundary`, while OSM coverage remains sparse.
- Verification after this slice: targeted pytest grew to `52 passed`; `py_compile` passed; `ruff` passed; Docker `api` and `streamlit` rebuilt healthy; static audit printed `api 16512 {'cian': 2436, 'domclick': 14076}`; CDP passed with `osm_rows=9`, `trend_series_rows=21`, and all seven screenshots at `clippedCount=0` / `overlapCount=0`.
- Caveat: OSM support now works end-to-end for persisted rows, but full OSM-backed district clustering is not complete until enrichment coverage is expanded with a reliable non-rate-limited data source or a scheduled/bounded enrichment strategy.

## 2026-06-24 Observation Trend Series Slice

- Added backend-backed descriptive observation trend support. FastAPI now exposes `/stats/observation-trend?limit=60`, computed from persisted `listing_observations` rows by observed date. It returns daily observation count, listing count, median price, and median price per m2 with `can_forecast=false`.
- Streamlit API mode now reads that endpoint into `DashboardData.observation_trend`; the dashboard price trend chart prefers `observationTrendSeries` from the API and falls back to listing preview rows only when the backend trend series is missing.
- Fixed the live PostgreSQL date-type regression in the trend query: the recent-date filter now keeps SQL date scalars instead of stringifying them before `IN (...)`.
- Latest live Docker/API evidence: `GET http://localhost:8000/stats/observation-trend?limit=5` returned HTTP 200 with `status=partial`, `metric=median_price_per_m2`, `can_forecast=false`, 5 rows from `2026-06-19` through `2026-06-23`; `GET /stats/data-quality` still reports `16,512` listings, `42,765` observations, `21` observed dates from `2026-05-14` through `2026-06-23`, `1,300` listing IDs with price changes, and `lifecycle_target_rows=0`.
- Static audit now embeds `observationTrendSeries=21`, first date `2026-05-14`, last date `2026-06-23`, and keeps `observationTrend.can_forecast=false`.
- CDP audit hardening: `output/playwright/cdp_static_grade5_audit.mjs` now fails if the payload has observation trend readiness but `observationTrendSeries` is empty, has a row count different from `observation_date_count`, or has a date range different from `first_observed_date` / `last_observed_date`.
- Verification after this slice: targeted pytest and the related suite passed with `48 passed`; `py_compile` passed for API/Streamlit/static audit files; `ruff` passed; Docker `api` and `streamlit` rebuilt healthy; static audit printed `api 16512 {'cian': 2436, 'domclick': 14076}`; CDP passed with `trend_series_rows=21`, `trend_series_first_date=2026-05-14`, `trend_series_last_date=2026-06-23`, all seven screenshots still at `clippedCount=0` and `overlapCount=0`.
- Caveat: this is an honest descriptive trend series, not a time-series forecast. Do not claim trend forecasting until repeated-observation semantics are validated and a separate verified forecasting model exists.

## 2026-06-24 Analytic Table Visibility Slice

- Valuation model fallback slice: `services/streamlit/app.py` now embeds the saved local Ridge artifact payload whenever it can be loaded, even when `/model/metadata` is available. API metadata remains the provenance source, while the static/file audit can still compute a real local model result if browser fetch to `/predict` is unavailable.
- CDP audit hardening for this valuation slice: `output/playwright/cdp_static_grade5_audit.mjs` now fails `valuation.calculationUsesModelWhenAvailable` when the payload has real model support but the UI falls back to `Ориентир по базе`.
- Verification after this valuation slice: the new unit test and CDP gate first failed on the previous payload behavior, then passed after the local-model fallback change. Latest verification passed `py_compile`, `ruff`, targeted pytest with `25 passed`, static audit `api 16512 {'cian': 2436, 'domclick': 14076}`, and CDP with `valuation.calculationUsesModelWhenAvailable=true`, `rowCount=6`, all seven screenshots `clippedCount=0`, and `overlapCount=0`.
- Data date-format slice: the main `Данные` table now uses a dedicated two-line date renderer without a comma between date and time, so narrow columns no longer show an orphan comma before the time. The CDP audit now fails `data.hasCleanDateFormatting` if rendered date cells contain comma-formatted timestamps.
- Verification after this date-format slice: the new CDP gate first failed on the previous comma-formatted date cells, then passed after the `tableDate()` renderer change. Latest static audit again used API payload `api 16512 {'cian': 2436, 'domclick': 14076}`; CDP passed with `data.hasCleanDateFormatting=true`, `data.defaultSortedByObservationDate=true`, and all screenshot pages still at `clippedCount=0` / `overlapCount=0`.

- Dashboard recent-listings slice: dashboard `Новые поступления` now sorts real listing rows by `observed_at` / `created_at` / `updated_at` before taking the top rows, instead of showing the first rows in API payload order.
- CDP audit hardening for this slice: `output/playwright/cdp_static_grade5_audit.mjs` now fails if the dashboard recent-listings feed disappears, has no real external listing link, or stops matching the top real source links sorted by observation date.
- Verification after this dashboard slice: the new CDP gates first failed on the previous markup, then passed after the `recentListingRows()` dashboard change. Latest CDP evidence: `dashboard.hasRecentListingsFeed=true`, `dashboard.recentListingsHaveRealLinks=true`, and `dashboard.recentListingsSortedByObservationDate=true`.
- Data table default-order slice: `Данные` now defaults to latest-first ordering by real `observed_at` / `created_at` / `updated_at` timestamps when the user has not selected a column sort. Header sorting still overrides this default.
- CDP audit hardening for this data slice: `output/playwright/cdp_static_grade5_audit.mjs` now fails `data.defaultSortedByObservationDate` if the first table links do not match the API-backed listings sorted by observation timestamp.
- Observation-day monitoring slice: current API/static evidence has `42,765` observations across `21` observed dates, and the monitoring UI now has CDP gates `monitoring.rendersExposureObservationDateCount`, `monitoring.rendersTrendObservationDateCount`, `monitoring.rendersObservationRowCounts`, and `monitoring.doesNotCollapseObservationDatesToFixture`. The `limit=3` Redis/docs preview is only a listing-row cache proof and must not be read as an observation-day count.
- District analytics pagination slice: `fetch_dashboard_data()` keeps the UI preview at `1,000` listings but can fetch bounded full analytics pages (`analytics_limit=2000`, `analytics_max_listings=20000`) for district comparison. This earlier slice had `district_extraction_source=address_text` and `coverage_pct=14.21`; the later boundary-backed slice supersedes it with `extraction_source=admin_boundary_geojson+address_text` and `coverage_pct=84.47`.

- Tightened the analytic table CSS in `services/streamlit/app.py` so the main `Данные` table and `Выгодные предложения` table keep important money/date/source/room/area/floor columns visible inside the desktop card instead of pushing right-side columns outside the screenshot viewport.
- Added compact Russian table labels with full Russian `title` tooltips while preserving existing `data-sort` keys and real row values.
- Hardened `output/playwright/cdp_static_grade5_audit.mjs` with semantic table checks: `data.importantColumnsVisible`, `deals.importantColumnsVisible`, and key-based checks for restored table fields instead of only checking header text in the DOM.
- Map popup link follow-up: `services/streamlit/app.py` now renders an explicit `Открыть объявление` action in map popups only when a real `source_url` is present, and `output/playwright/cdp_static_grade5_audit.mjs` fails on `map.popupHasExplicitListingLink` if that real external link disappears.
- Static audit hardening: `output/playwright/generate_static_audit.py` now requires API mode, real `source_counts`, and at least 10,000 listings by default; set `STATIC_AUDIT_ALLOW_OFFLINE=1` only for explicit offline/snapshot debugging.
- Map tile audit hardening: the CDP audit now waits for at least 8 real tile images before screenshot capture and fails `map.loadedTiles` below that threshold.
- Map drag/pan audit hardening: `output/playwright/cdp_static_grade5_audit.mjs` now simulates pointer drag on the map surface and fails `map.dragPanChanged` if the stored map center does not move.
- Earlier map interaction evidence: CDP passed with `loadedTiles=8 >= 8`, `map.dragPanChanged=true`, and center movement from `{lon: 37.618423, lat: 55.751244}` to `{lon: 37.82441665234373, lat: 55.664199153470705}`.
- Verification after this earlier slice: `py_compile` passed, `ruff` passed, targeted pytest passed with `25 passed`, static audit used Docker API payload `api 16512 {'cian': 2436, 'domclick': 14076}`, and CDP passed with both table visibility gates true, `valuation.initialPromptHonest=true`, `map.popupHasExplicitListingLink=true`, `loadedTiles=8 >= 8`, and all screenshot `clippedCount=0` / `overlapCount=0`.

Дата: 2026-06-24  
Ветка: `ui/stitch-hybrid-redesign-20260623`  
Рабочая папка: `E:\Магистр\2-курс\python\RealtyScope-stitch-hybrid-redesign-20260623`

## Current Truth

- Keep this branch as the new UI line.
- Do not use Browser MCP; it has repeatedly crashed Codex. Use terminal checks, static screenshots, pytest, `py_compile`, `ruff`, and limited Chrome/CDP only when memory is stable.
- Reply to the user in Vietnamese. Visible UI text must remain Russian only except `RealtyScope`.
- Do not stage, commit, push, or force-delete branches unless the user explicitly asks in the active session.
- The current UI payload/static audit uses `16,512` real listings from the Docker API:
  - `Домклик`: `14,076`
  - `ЦИАН`: `2,436`
- Latest known Domclick run from local evidence:
  - run id `domclick-20260623T222510-140967Z`
  - `records_seen/raw/normalized/ml_ready = 2000`
  - `created = 541`
  - `updated = 1459`
  - `observations_inserted = 1997`
  - `rejected = 0`
- Address/listing links are restored through `source_url`.
- OSM infrastructure is present only as a partial model feature contract in the current UI payload; broad infrastructure coverage must not be claimed until real rows/coverage are confirmed.

## Latest Verification

After the latest monitoring/service-contour slice:

- `python -m py_compile services\streamlit\app.py services\api\app\main.py`: passed.
- `python -m ruff check services\streamlit\app.py services\api\app\main.py tests\test_streamlit_ui_payload.py tests\test_api_monitoring.py`: passed.
- `python -m pytest -p no:cacheprovider tests\test_streamlit_api_client.py tests\test_streamlit_scaffold.py tests\test_streamlit_dashboard_charts.py tests\test_streamlit_ui_payload.py tests\test_api_monitoring.py -q`: `42 passed` after the API lifecycle-stat and trend-readiness corrections.
- `python output\playwright\generate_static_audit.py`: passed with API payload `16512 {'cian': 2436, 'domclick': 14076}`.
- Static HTML evidence now contains the restored data-table fields `Этаж` and `Дата`, map popup field `Площадь`, real coordinate-quality fields `valid_moscow_points` / `excluded_coordinate_rows`, and deal scoring fields `deal_score` / `segment_sample_size`.
- `node output\playwright\cdp_static_grade5_audit.mjs`: passed in cautious Chrome headless/CDP mode. Evidence: `16,512` real listings, `14,076` Домклик, `2,436` ЦИАН, valuation comparable table with real rows and real links, `30` map tile nodes loaded, zoom changed `10 -> 11 -> 12`, popup showed real price/price per м²/rooms/area/floor/source, data table pagination worked, deal table scoring columns were present, `Сегменты и районы` showed real segment comparison without fake район ranking, district comparison missing state, and district-clustering readiness panel with no fake clusters, monitoring had true source/service status, `Контур модели` with model/feature versions and baseline caveat, bounded logs, exposure readiness reported `21` real DB observation dates, trend readiness rendered as descriptive-only with forecast not built, and no internal trace/error text was visible. The CDP script now fails if required segments/monitoring/layout checks such as district missing state, cluster missing panel, model provenance, trend panel, exposure panel, bounded logs, or `clippedCount=0` regress.

- Monitoring now has real service-contour evidence. `/monitoring/status` returns API/PostgreSQL/Redis/model/ingestion service rows; static snapshot UI renders `Статус контуров` with API unavailable, local vitrine/model/ingestion available, and PostgreSQL/Redis marked `НЕ ПРОВЕРЕНО` instead of online.
- Live Docker runtime smoke was refreshed on `2026-06-24` for this branch. After a cold build, `docker compose -p realtyscope ps` showed `db`, `redis`, `api`, and `streamlit` healthy and `mlflow` up. Localhost checks returned 200 for API `/health`, filtered `/data`, `/model/metadata`, `/monitoring/status`, Streamlit `/_stcore/health`, and MLflow root. Runtime monitoring reported `16,512` listings, `42,765` observations, `21` observation dates, `1,300` listing IDs with price changes, `lifecycle_target_rows=0`, and service rows `api/database/cache/model/ingestion=ok`. `/predict` returned `27,115,216.38` RUB for the full 23-feature vector with `baseline_ridge_v2_non_leaky`, `ml_features_v2_non_leaky`, `rows_total=8,366`, and `r2=0.6231827045433119`; MLflow registry returned `realtyscope-price-model` version `4` status `READY`. Redis scan observed `realtyscope:listings:v2:limit=1:offset=0:min_price_rub=10000000:rooms=2`, then the key expired on the short TTL path.
- Caveat for next session: after the long Docker build, a few new WSL launch attempts returned `Wsl/Service/0x8007274c` while containers and localhost endpoints still responded. Re-check WSL/Compose before relying on interactive Docker commands in a live demo.

## Important Files

- UI app: `services/streamlit/app.py`
- Final gap audit: `docs/final-readiness/2026-06-24-grade5-gap-audit.md`
- Final implementation plan: `docs/superpowers/plans/2026-06-24-realtyscope-final-grade5-completion-plan.md`
- Design system: `docs/design/DESIGN.md`
- Static audit output: `output/playwright/realtyscope-static-audit.html`
- Old UI branch archive: `output/git-archives/old-ui-branches-20260624.bundle`

## What Is Still Not Complete

- The UI is improved but still needs a final page-by-page pass against Stitch A/B.
- Map/heatmap has real tile math, wheel zoom, drag/pan, Moscow coordinate filtering, point popups, and coordinate-quality reporting. A cautious Chrome/CDP static interaction audit passed; keep future audits bounded to avoid the earlier Codex memory crash pattern.
- Оценка квартиры now includes real comparable listings selected from the current payload by room count, area distance, and price per m² distance. The model remains an honest baseline, not a final production appraisal model.
- `Сегменты и районы` keeps completed segment analytics and now renders boundary-backed district comparison/clustering. Current boundary evidence has `districtComparison=12`, `districtClusters=12`, `coverage_pct=84.47`, and `cluster_feature_source=districtComparison+boundary`; do not present it as broadly OSM-backed while OSM feature coverage is still `2.56%`.
- Monitoring now includes `Готовность прогноза экспозиции`. Current Docker API evidence reports `42,765` persisted observations across `21` observed dates from `2026-05-14` to `2026-06-23`, `7,456` listings with observation history, max `19` dates per listing, `1,300` listing IDs with price changes, `exposure_target_rows=0`, and `canForecast=false`. This is an honest readiness block, not a forecast model.
- Runtime PostgreSQL DB evidence from `realtyscope-db-1` confirms the same direction at the persisted-observation layer: `42,765` observations, `21` observed dates (`2026-05-14` through `2026-06-23`), `7,456` source listing IDs with multiple observed dates, max `19` dates per listing, and `1,300` listing IDs with price changes. All persisted observation rows are still `status=observed` and `active=true`, so `lifecycle_target_rows=0` and no exposure forecast should be shown.
- Monitoring now also includes `Готовность тренда`. Current PostgreSQL/API trend evidence reports `trend_status=partial`, `trend_observations=42,765`, `trend_observation_dates=21`, `trend_price_changes=1,300`, and `trend_can_forecast=false`. This is descriptive trend readiness only, not a true forecast.
- Data tables now restore address/link, source, rooms, area, floor, observed date, price, and price per m² in the main data view; remaining table work is visual density review and any extra reviewer-requested columns.
- Per-column sort, refresh, and page-local filters exist; continue checking page-by-page behavior against Stitch A/B.
- Monitoring/logs now have bounded UI pagination and service-contour status verified by CDP. Snapshot mode truthfully marks PostgreSQL/Redis as not verified; deeper real `app_logs` population is still a backend/ops improvement.
- The following course real-estate analytics are not yet complete backend features:
  - `Сравнение районов` now has real boundary-backed district aggregates (`coverage_pct=84.47`), but coverage/provenance must stay visible
  - `Кластеризация районов по характеристикам` now has deterministic clustering over boundary-backed district aggregates, but not broad OSM-backed clustering because persisted OSM feature coverage is still `2.56%`
  - `Прогноз срока экспозиции` as a trained model; monitoring now only measures readiness and reports that current lifecycle target rows are `0`
  - model-based `Детекция выгодных предложений` if a stronger promoted model is later available
  - true forecast/trend beyond descriptive observation trend; current trend readiness is partial and `can_forecast=false`
- Current model quality is baseline-level; backend model improvement is a later phase.

## Git Cleanup Status

Created verified archive:

`output/git-archives/old-ui-branches-20260624.bundle`

It contains complete history for:

- `ui/phase9d-russian-dashboard-redesign-20260620`
- `ui/realtyscope-dashboard-redesign`
- `ui/realtyscope-review-workbench`
- `ui/realtyscope-ultimate-redesign`
- `ui/recovered-real-data-dashboard-20260620`
- `ui/stitch-final-redesign-20260622`
- `ui/stitch-precise-b`

Do not force-delete yet. `ui/stitch-precise-b` is checked out in `E:\Магистр\2-курс\python\RealtyScope` and has untracked files:

- `DESIGN (1).md`
- `dashboard_b.html`
- `fetch_project_b_finals.py`
- `fetch_stitch.py`
- `pytest_temp/`
- `stitch_data/`
- `stitch_html/`
- `tmp_pytest/`

Next cleanup slice should confirm these files are disposable or archive them separately, then remove old worktrees and delete old UI branches from the verified bundle.

## Next Session Plan

1. Read mem0 project `python` latest checkpoint and this file.
2. Read `docs/final-readiness/2026-06-24-grade5-gap-audit.md`.
3. Read `docs/superpowers/plans/2026-06-24-realtyscope-final-grade5-completion-plan.md`.
4. Continue with Phase 1 of the plan: close UI redesign page by page.
5. Run targeted verification after each major page or map/data change.
6. Only after UI is stable, move to backend analytics phases for district comparison, clustering, exposure prediction, and model improvement. Deal scoring is now backed by a real robust segment rule, but not yet by a promoted stronger model.

## 2026-06-24 Count Discrepancy And Model Selection Slice

- Investigated the reported local/API listing-count discrepancy. Live API endpoints are internally consistent: `/stats/data-quality`, `/data?limit=1`, `/listings?limit=1`, and `/monitoring/status` all report `16,512` listings with `source_counts={'cian': 2436, 'domclick': 14076}`.
- The lower local count came from the offline/snapshot UI cache at `output/cache/streamlit_ui_payload.json`: `mode=snapshot`, `listings_total=15,765`, `loaded_snapshot_listings=15,765`, `source_counts={'domclick': 13324, 'cian': 2441}`. Treat this as a real but stale local snapshot fallback, not the current API/DB total.
- Regenerated static audit after the UI/backend changes; it stayed in API mode and printed `api 16512 {'cian': 2436, 'domclick': 14076}`.
- Added backend model-selection support in code/tests:
  - `src/realtyscope/ml/train.py` now has `train_selected_model()` that trains multiple real candidates (`ridge`, `random_forest`) on the same grouped validation split, records candidate metrics, writes `selected_candidate`, and keeps the historical Ridge baseline path intact.
  - CLI now accepts `--trainer baseline|selected`; default remains `baseline` for compatibility, while `--trainer selected` writes a selected-model artifact.
  - API startup now supports `MODEL_SELECTION_MODE=best_metric` and `MODEL_ARTIFACT_DIR`; it scans real `.joblib` artifacts, ranks by validation `r2` then `mae`, and falls back to `MODEL_SELECTION_MODE=explicit` when a deployment must pin one artifact.
  - `/model/metadata` now exposes `model_selection_mode`, `model_selection_reason`, `model_candidates`, `selected_candidate`, and `training_candidates` when available.
  - Monitoring UI renders model-selection provenance in Russian (`Выбор модели`, `Кандидатов`, `Выбранный алгоритм`) and translates `random_forest` to `случайный лес`.
- Verification for this slice:
  - `python -m pytest -p no:cacheprovider tests/test_ml_training.py tests/test_api_monitoring.py tests/test_config.py tests/test_streamlit_ui_payload.py::test_workstation_html_renders_model_provenance_and_baseline_caveat tests/test_streamlit_ui_payload.py::test_build_payload_keeps_local_model_fallback_with_api_model_metadata -q`: `19 passed`.
  - `python -m py_compile src\realtyscope\config.py src\realtyscope\ml\train.py services\api\app\main.py services\streamlit\app.py tests\test_ml_training.py tests\test_api_monitoring.py tests\test_config.py tests\test_streamlit_ui_payload.py`: passed.
  - `python -m ruff check src\realtyscope\config.py src\realtyscope\ml\train.py services\api\app\main.py services\streamlit\app.py tests\test_ml_training.py tests\test_api_monitoring.py tests\test_config.py tests\test_streamlit_ui_payload.py`: passed.
  - `python output\playwright\generate_static_audit.py`: passed with `api 16512 {'cian': 2436, 'domclick': 14076}`.
  - `node output\playwright\cdp_static_grade5_audit.mjs`: passed; payload stayed in API mode with `16,512` listings, `trend_series_rows=21`, `osm_rows=9`, map tile/zoom/drag/popup checks passed, and all seven page screenshots reported `clippedCount=0` and `overlapCount=0`.
- Runtime caveat: the already-running Docker API still needs rebuild/restart before `/model/metadata` on `127.0.0.1:8000` can show the new selection fields. The currently promoted live artifact is still `baseline_ridge_v2_non_leaky` until a selected model is trained, verified, and promoted.

## 2026-06-24 Source Metadata And CDP Stability Slice

- Fixed the API code path for `/data` / `/listings`: listing payloads now include real `source_name`, `source_label`, `source_listing_id`, `source_url`, and latest `observed_at` from `ListingSourceLink`, `Source`, `RawListingRecord`, and `ListingObservation`.
- Bumped the `/data` Redis cache key to `realtyscope:listings:v2:*` so old cached rows without source metadata are not reused.
- Added real `source_counts` to `/stats/data-quality` from distinct `ListingSourceLink.listing_id` grouped by `Source.name`.
- Increased Streamlit API timeout default from `0.5s` to `5.0s`; the previous default caused static audit/UI fallback to offline mode while the live API was merely cold.
- Verified code-new API with temporary local uvicorn on `127.0.0.1:8010` against the real PostgreSQL/Redis ports. Evidence: `16,512` listings, `source_counts={'cian': 2436, 'domclick': 14076}`, source links restored in listing rows, and static audit `api 16512 {'cian': 2436, 'domclick': 14076}`.
- Re-ran cautious Chrome/CDP against the static audit generated from API `8010`: valuation comparables have real rows and real links, data table source rows are real, map popup shows `Домклик`, tile nodes load, district readiness is shown honestly as missing when comparison rows are `0`, exposure forecast remains missing with `lifecycle_target_rows=0`, trend remains descriptive-only, and `remaining_audit_chrome=0`.
- Hardened `output/playwright/cdp_static_grade5_audit.mjs`: dynamic DevTools port, CDP command timeout, required monitoring/layout gates, and profile-based Chrome cleanup. This prevents the previous runaway `chrome-static-profile-*` process buildup.
- Current Docker API on `127.0.0.1:8000` is healthy and has the model ready, but it is still the old container image for `/data` and `/stats`: source metadata fields are null and `source_counts` is absent. Rebuild/restart Docker API/Streamlit before using Docker `8000/8501` as final demo evidence. Docker CLI is not available in Windows PATH in this session and WSL returns `Wsl/Service/0x8007274c`.

### 2026-06-24 Docker Runtime Refresh

- WSL recovered long enough to rebuild/restart Docker `api` and `streamlit` from this branch with `docker compose -p realtyscope up -d --build api streamlit`.
- Compose evidence after rebuild: `db`, `redis`, `api`, and `streamlit` healthy; `mlflow` up.
- Docker API `127.0.0.1:8000` now serves the source-metadata slice:
  - `/data?limit=1` returns `source_name=domclick`, `source_label=Домклик`, `source_listing_id=2069068416`, `source_url=https://domclick.ru/card/sale__new_flat__2069068416`, `observed_at=2026-06-02T00:36:56.568203+00:00`.
  - `/stats/data-quality` returns `listings_total=16,512`, `observations_total=42,765`, `source_counts={'cian': 2436, 'domclick': 14076}`, `lifecycle_target_rows=0`.
  - `/model/metadata` returns `status=ready`, `model_version=baseline_ridge_v2_non_leaky`, `feature_count=23`.
  - `/monitoring/status` returns environment `docker`, service rows `api/database/cache/model/ingestion=ok`, source counts, and model status ready.
  - `/predict` returns `27,115,216.38317985` RUB for the full 23-feature demo vector with baseline caveat and `r2=0.6231827045433119`.
  - Streamlit `/_stcore/health` returns `200 ok`.
  - Redis proof via localhost Python client after a filtered `/data` request: `realtyscope:listings:v2:limit=1:offset=0:min_price_rub=10000000:rooms=2`.
- Static audit without API override now uses Docker `8000`: `api 16512 {'cian': 2436, 'domclick': 14076}`.
- CDP audit against that static HTML passed: real comparable links, map popup source, data-table source rows, service contour with model ready, missing exposure forecast, descriptive-only trend, `clippedCount=0`, and `remaining_audit_chrome=0`.
- WSL is still intermittent: one later Redis proof through `wsl docker exec` returned `Wsl/Service/0x8007274c`, so prefer localhost HTTP/Python Redis checks when WSL transport is unstable.

## 2026-06-25 Runtime Promotion And Trend Forecast Checkpoint

- Docker `api` and `streamlit` containers on the retained branch were hot-updated from the current source and restarted successfully.
- Current Docker API `127.0.0.1:8000` evidence:
  - `/stats/data-quality`: `17,046` listings, `source_counts={'cian': 2436, 'domclick': 14610}`, `44,765` observations, `22` observation dates from `2026-05-14` to `2026-06-24`, `7,766` listings with observation history, max `20` dates per listing, `1,415` listing IDs with price changes, `lifecycle_target_rows=0`.
  - `/model/metadata`: selected model artifact `selected_price_model_v1_non_leaky`, selected algorithm `random_forest`, validation `r2=0.8801698812234392`, `mae=7,933,891.650272489`, `rows_total=16,512`.
  - `/stats/exposure-forecast`: observed-history lower-bound forecast is `ready` with `observed_exposure_target_rows=7,766`, median `7` days, max `22` days, while terminal lifecycle target rows remain `0`.
  - `/stats/observation-trend`: trend forecast is `ready`, `can_forecast=true`, `forecast_method=linear_median_price_per_m2_v1`, horizon `7` days, history points `22`, forecast dates `2026-06-25` through `2026-07-01`.
- Monitoring UI now renders `forecast_rows` in a table titled `Прогноз медианы за м²`; CDP has a `monitoring.rendersTrendForecastRows` gate.
- Current verification:
  - `python -m pytest -p no:cacheprovider tests/test_api_monitoring.py tests/test_streamlit_ui_payload.py -q`: `39 passed`.
  - `python -m pytest -p no:cacheprovider tests/test_api_monitoring.py tests/test_streamlit_api_client.py tests/test_district_boundaries.py tests/test_streamlit_ui_payload.py tests/test_static_audit_requirements.py tests/test_docker_build_contract.py -q`: `58 passed`.
  - `python output\playwright\generate_static_audit.py`: `api 17046 {'cian': 2436, 'domclick': 14610}`.
  - `node output\playwright\cdp_static_grade5_audit.mjs`: passed; map tiles/zoom/drag/popup, selected model, exposure forecast, trend forecast, and all seven screenshots are clean.
- A clean Streamlit image rebuild was attempted but stopped after `uv sync` ran long on heavy dependencies; no build process remains active. Runtime containers remain hot-updated and health-verified, but immutable image rebuild is still a separate packaging task.
- Next highest-value work:
  1. Refresh GitNexus after these doc/code updates and use it before deeper backend changes.
  2. Keep OSM provenance precise after the local-extract slice: current persisted feature coverage is full, but it is local extract + live Overpass + exact-coordinate derivation, not all-live Overpass.
  3. Run a broader final verification pass only after the next backend slice, because the current slice already has targeted tests plus static/CDP evidence.

## 2026-06-25 Historical Docker Runtime Rebuild Checkpoint

Docker `8000/8501` is no longer stale for the retained Stitch hybrid branch.

- The latest Docker trainer completed and produced a selected `random_forest` model on the current `17,046`-listing DB with `r2=0.8653013476373554`, `mae=7,638,132.733793359`, and `candidate_count=3`.
- `docker compose -p realtyscope up -d --build api streamlit` rebuilt/restarted API and Streamlit. Compose reports API and Streamlit healthy.
- Verified Docker API evidence:
  - `/model/metadata`: `status=ready`, `selected_candidate=random_forest`, `model_selection_mode=best_metric`, `rows_total=17,046`, `candidate_count=3`, and non-empty `feature_importance`.
  - `/stats/exposure-forecast`: `status=ready`, `can_forecast=true`, `target_source=observation_gap_inferred_lifecycle`, `inferred_lifecycle_target_rows=4,962`, `terminal_lifecycle_target_rows=0`.
  - Static audit with `API_BASE_URL=http://127.0.0.1:8000`: `api 17046 {'cian': 2436, 'domclick': 14610}`.
  - CDP Grade-5 audit with Docker API/Streamlit passed: real map tiles/zoom/drag/popup, selected-model valuation, data/deals/district/monitoring checks, and all seven screenshots at `clippedCount=0` / `overlapCount=0`.
- Caveat: PowerShell `Invoke-RestMethod` timed out once against Docker localhost, but `curl.exe --noproxy "*"` and WSL/container requests were fast. Use `curl.exe` or the audit scripts for Docker HTTP proof.
- Next highest-value work is final verification/git hygiene/docs consistency. OSM/district scope now has full persisted feature coverage for the current listing table; keep the provenance caveat that this is local extract + live Overpass + exact-coordinate derivation.

## 2026-06-25 OSM Backend Selector Checkpoint

The OSM enrichment backend was improved after the Docker rebuild:

- `persist_osm_features(..., fetch_elements=...)` now uses one representative listing per missing distinct coordinate and skips coordinates that already have OSM features. This prevents live Overpass batches from refetching existing coordinates or duplicate listings.
- Dry-run supports the same selector with `--live-overpass --dry-run --json` and returns `selection_mode=live_overpass_missing_distinct_coordinates`.
- At that selector slice, DB dry-run evidence with current worktree code reported `rows_available=4,493`, `rows_selected=5`, first selected IDs `[7, 8, 10, 11, 13]`.
- A live smoke with `limit=1` inserted one real Overpass row for listing `5`; `--derive-coordinate-matches` inserted `27` exact-coordinate rows from it.
- At that slice, Docker API `/stats/data-quality` reported `osm_features_total=417`, `osm_featured_listings=417`, `osm_coverage_pct=2.45`, `osm_live_rows=10`, and `osm_coordinate_derived_rows=407`.
- Static audit and CDP Grade-5 audit passed after this DB update, with CDP reporting `osm_rows=417`, `osm_coverage_pct=2.45`, and clean screenshots.
- Remaining caveat: district clusters still show `feature_source=districtComparison+boundary`, not `districtComparison+osm`, because OSM coverage is still sparse. Full OSM-backed clustering needs a real long batch or local extract/cache.

## 2026-06-25 Exposure Semantics Correction Checkpoint

Supersedes older checkpoint lines that called observed-history lower-bound exposure `ready` or
set exposure `can_forecast=true`.

- Current verified runtime for this slice is local FastAPI `http://127.0.0.1:8011` and Streamlit
  `http://127.0.0.1:8509`. Docker port `8000` was not freshly verified because Docker CLI is not
  available in Windows PATH here.
- `/stats/exposure-forecast` now reports terminal lifecycle forecast readiness only:
  `status=partial`, `can_forecast=false`, `terminal_lifecycle_target_rows=0`,
  `terminal_lifecycle_can_forecast=false`.
- Observed lower-bound evidence remains visible and real but separate:
  `target_source=observed_history_lower_bound`, `observed_exposure_target_rows=7,766`,
  `observed_exposure_can_forecast=true`, median observed exposure `7` days, max `22` days.
- Monitoring UI now labels this as lower-bound evidence rather than a true forecast:
  `Нижняя граница по комнатности`, `Строк наблюдений`, `Источник расчета`,
  `Медиана нижней границы`.
- Current data evidence: `17,046` listings, source mix `cian=2,436` and `domclick=14,610`,
  `44,765` observations across `22` dates from `2026-05-14` through `2026-06-24`,
  `7,766` listings with history, max `20` dates per listing, `1,415` price-change listing IDs.
- Current model evidence: selected model `selected_price_model_v1_non_leaky`,
  `selected_candidate=random_forest`, feature version `ml_features_v2_non_leaky`,
  `r2=0.850303822452758`, `mae=8,001,983.659500307`, `rows_total=17,046`.
- Verification passed: `65` targeted pytest tests, `py_compile`, `ruff`, static audit generated
  from API `8011`, and CDP Grade-5 audit with clean map/table/monitoring/layout screenshots.

### 2026-06-24 Final Screenshot Set

- `output/playwright/cdp_static_grade5_audit.mjs` now captures a screenshot for each main UI page and fails if any page has clipped checked controls/text or overlapping `.card` blocks.
- Earlier map interaction addendum: the same CDP audit verifies real tile loading and pointer-drag pan together; earlier evidence was `loadedTiles=8`, `minimumLoadedTiles=8`, and `map.dragPanChanged=true`. The later boundary slice passed with `loadedTiles=16/30`.
- Current Docker-backed screenshot set:
  - `output/playwright/realtyscope-static-grade5-dashboard.png`
  - `output/playwright/realtyscope-static-grade5-valuation.png`
  - `output/playwright/realtyscope-static-grade5-map.png`
  - `output/playwright/realtyscope-static-grade5-deals.png`
  - `output/playwright/realtyscope-static-grade5-segments.png`
  - `output/playwright/realtyscope-static-grade5-data.png`
  - `output/playwright/realtyscope-static-grade5-monitoring.png`
- Latest CDP evidence: all seven pages have `clippedCount=0` and `overlapCount=0`; map loaded `16` real tile images, zoom changed `10 -> 11 -> 12`, and listing popup showed real price/price per m²/rooms/area/floor/source.
