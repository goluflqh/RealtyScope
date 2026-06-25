# RealtyScope Grade-5 Final Gap Audit

Date: 2026-06-24  
Branch: `ui/stitch-hybrid-redesign-20260623`  
Workspace: `E:\Магистр\2-курс\python\RealtyScope-stitch-hybrid-redesign-20260623`

## 2026-06-25 Current Docker Runtime After Retrain

This addendum supersedes older same-day notes below that mention `hist_gradient_boosting`, `candidate_count=2`, or partial OSM coverage as current.

- Compose reports `api`, `streamlit`, `db`, and `redis` healthy, with `mlflow` up.
- Docker `/model/metadata`: `selected_candidate=random_forest`, `candidate_count=3`, `model_selection_mode=best_metric`, `rows_total=17,046`, `train_rows=13,636`, `test_rows=3,410`, `r2=0.8653013476373554`, `mae=7,638,132.733793359`, `rmse=17,470,229.328815047`, and non-empty `feature_importance`.
- Candidate comparison from the same grouped split: `random_forest` (`r2=0.8653013476373554`, `mae=7,638,132.733793359`), `hist_gradient_boosting` (`r2=0.8483193165484304`, `mae=7,682,017.89735461`), and `ridge` (`r2=0.5885808364114331`, `mae=16,992,756.563055124`).
- Docker `/stats/data-quality`: `17,046` listings, `source_counts={'cian': 2436, 'domclick': 14610}`, `44,765` observations, `22` observation dates, `lifecycle_target_rows=0`, `inferred_lifecycle_target_rows=4,962`, `osm_features_total=17,046`, `osm_featured_listings=17,046`, `osm_coverage_pct=100.0`, `osm_local_extract_rows=4,487`, `osm_live_rows=16`, `osm_coordinate_derived_rows=12,543`.
- Docker `/stats/exposure-forecast`: `status=ready`, `can_forecast=true`, `target_source=observation_gap_inferred_lifecycle`, `inferred_lifecycle_target_rows=4,962`, `terminal_lifecycle_target_rows=0`; still not confirmed sale/removal.

## 2026-06-25 Historical Docker HistGradientBoosting Runtime Addendum

Historical note: this addendum is superseded by the current Docker retrain above.

- Rebuilt/restarted Docker API and Streamlit from the retained branch via WSL Compose: `docker compose -p realtyscope up -d --build api streamlit`.
- Compose after rebuild: `realtyscope-api-1` and `realtyscope-streamlit-1` are healthy; `db` and `redis` are healthy; `mlflow` is up.
- Runtime health: Docker `/health` returns `status=ok`, `environment=docker`; Streamlit `/_stcore/health` returns `ok`.
- Docker `/model/metadata` now reports `selected_candidate=hist_gradient_boosting`, `candidate_count=3`, `model_selection_mode=best_metric`, `rows_total=17,046`, `train_rows=13,636`, `test_rows=3,410`, validation `r2=0.8994355561733502`, `mae=6,188,596.253660057`, and `rmse=15,095,211.71856097`.
- Candidate comparison is real and uses the same grouped split: `hist_gradient_boosting` beat `random_forest` (`r2=0.8505952988269576`, `mae=7,989,464.3271694975`) and `ridge` (`r2=0.556166053792913`, `mae=16,651,213.37086019`). XGBoost is still not installed or claimed.
- Train/test leakage guardrails: metadata reports `train_listing_groups=13,636`, `test_listing_groups=3,410`, and the 23 runtime features exclude target/price columns.
- Docker `/stats/data-quality`: `17,046` listings, `source_counts={'cian': 2436, 'domclick': 14610}`, `44,765` observations, `22` observation dates, `lifecycle_target_rows=0`, `inferred_lifecycle_target_rows=4,962`, `osm_features_total=448`, `osm_featured_listings=448`, `osm_coverage_pct=2.63`, `osm_live_rows=16`, and `osm_coordinate_derived_rows=432`.
- Docker `/stats/exposure-forecast`: `status=ready`, `can_forecast=true`, `target_source=observation_gap_inferred_lifecycle`, `inferred_lifecycle_target_rows=4,962`, `terminal_lifecycle_target_rows=0`; this remains a forecast of disappearance from observations, not confirmed sale/removal.
- Static audit against Docker passed: `API_BASE_URL=http://127.0.0.1:8000 python output\playwright\generate_static_audit.py` printed `api 17046 {'cian': 2436, 'domclick': 14610}`.
- CDP Grade-5 audit against Docker passed: `selectedCandidate=hist_gradient_boosting`, `expectedSelectedCandidateLabel=градиентный бустинг`, `rendersSelectedCandidateName=true`, `loadedTiles=30/30`, map zoom/drag/popup checks passed, district comparison is boundary-backed with `district_coverage_pct=84.47`, and all seven screenshots had `clippedCount=0` and `overlapCount=0`.
- Remaining honest gaps: terminal confirmed sale/removal target rows are still `0`, and district clustering is not broadly OSM-backed while OSM infrastructure coverage is only `448 / 17,046` (`2.63%`).

## 2026-06-25 Historical Expanded Model And OSM Rate-Limit Addendum

- Selected-model training now includes `hist_gradient_boosting` in addition to `ridge` and `random_forest`, using the same `listing_id_grouped_random` validation split and non-leaky feature version `ml_features_v2_non_leaky`.
- Retrained artifact evidence from `data/processed/models/phase5/selected_price_model_v1_non_leaky.joblib`: `selected_candidate=hist_gradient_boosting`, `candidate_count=3`, `rows_total=17,046`, `train_rows=13,636`, `test_rows=3,410`, validation `r2=0.8994355561733502`, `mae=6,188,596.253660057`, `rmse=15,095,211.71856097`, and `mape=0.16183106164323535`.
- Candidate comparison from the same split: `random_forest` `r2=0.8496374735904109`, `mae=8,008,821.77078574`; `ridge` `r2=0.5562438473500875`, `mae=16,654,440.34608464`.
- `xgboost` is not present in `pyproject.toml` or `uv.lock`; no XGBoost metric is claimed.
- Fresh code-new API proof on `127.0.0.1:8013/model/metadata` matched the artifact and reported `selected_candidate=hist_gradient_boosting`, `candidate_count=3`, and `rows_total=17,046`. Docker `127.0.0.1:8000` is still an older in-memory model process until Docker can be restarted/rebuilt.
- Leakage/overfit guard evidence: added selected-model grouped-split test, confirmed train/test listing ID sets are disjoint for duplicated listing rows, and confirmed selected non-leaky artifacts do not contain feature names with `price`.
- Verification passed: `tests/test_ml_training.py` (`11 passed`), `tests/test_api_monitoring.py tests/test_config.py` (`13 passed`), targeted Streamlit model/fallback tests (`2 passed`), `py_compile`, and `ruff`.
- After stopping stale local API/Streamlit Python processes, static audit and CDP visual proof were refreshed against API `127.0.0.1:8013`. Static audit printed `api 17046 {'cian': 2436, 'domclick': 14610}` and regenerated `output/playwright/realtyscope-static-audit.html`. CDP passed all page/layout gates and explicitly verified `monitoring.selectedCandidate=hist_gradient_boosting`, `expectedSelectedCandidateLabel=градиентный бустинг`, and `rendersSelectedCandidateName=true`.
- No real local OSM extract/cache was found after a repeated repo/parent-tree search. A logged live Overpass batch with `limit=10` inserted `4` rows but returned `HTTP 429 Too Many Requests` for `6` rows; exact-coordinate derivation inserted `8` more rows without live OSM.
- API data-quality evidence after the batch: `osm_features_total=448`, `osm_featured_listings=448`, `osm_coverage_pct=2.63`, `osm_live_rows=16`, `osm_coordinate_derived_rows=432`, `rows_available=4,487` missing distinct coordinates. Because public Overpass rate-limited the run and coverage remains sparse, district clustering remains boundary-backed rather than OSM-infrastructure-backed.

## 2026-06-25 Historical Docker Runtime Rebuild And Audit Addendum

Docker `127.0.0.1:8000` / `127.0.0.1:8501` is now freshly verified from the retained Stitch hybrid branch. This supersedes older Docker caveats in this audit that said port `8000` still had stale selected-model or exposure semantics.

- Docker trainer completed against the current DB and produced selected-model evidence with `rows_total=17,046`, selected candidate `random_forest`, candidate count `2`, validation `r2=0.8507863494880132`, `mae=7,987,846.5447418345`, and `rmse=18,387,439.565866258`.
- Docker `/model/metadata` now reports `status=ready`, `model_selection_mode=best_metric`, `selected_candidate=random_forest`, `rows_total=17,046`, and `candidate_count=2`.
- Docker `/stats/exposure-forecast` now reports `status=ready`, `can_forecast=true`, `target_source=observation_gap_inferred_lifecycle`, `method=gap_inferred_lifecycle_median_v1`, `inferred_lifecycle_target_rows=4,962`, `terminal_lifecycle_target_rows=0`, and `observed_exposure_target_rows=7,766`.
- Static audit against Docker `API_BASE_URL=http://127.0.0.1:8000` passed with `api 17046 {'cian': 2436, 'domclick': 14610}`.
- CDP Grade-5 audit against Docker `API_BASE_URL=http://127.0.0.1:8000` and `STREAMLIT_URL=http://127.0.0.1:8501` passed. Latest evidence includes `listings_total=17046`, `map.loadedTiles=29/30`, real popup fields/link, selected-model valuation, `district_coverage_pct=84.47`, `cluster_feature_source=districtComparison+boundary`, `osm_coverage_pct=2.56`, `exposure_inferred_target_rows=4962`, and all seven screenshots with `clippedCount=0` / `overlapCount=0`.
- PowerShell `Invoke-RestMethod` timed out during one localhost check, while `curl.exe --noproxy "*"` and WSL/container requests succeeded quickly. This is recorded as a local transport/tooling quirk, not as API failure.

Still incomplete or partial:

- Terminal sale/removal exposure is still unavailable because `terminal_lifecycle_target_rows=0`; the real working exposure target is inferred disappearance from observations.
- District comparison/clustering are boundary-backed plus address fallback, not broadly OSM-infrastructure-backed while confirmed OSM feature coverage remains `436 / 17,046` (`2.56%`).

## 2026-06-25 OSM Logged Batch Addendum

The OSM coverage strategy is now resumable with explicit batch evidence:

- Added CLI `--progress-log` support. The log appends one JSONL row per dry-run/write/derive command with operation name, limit, radius, delay, timeout, selected listing IDs, row counts, errors, and the result payload.
- No real local OSM extract/cache was found in the repo root, parent project folder, or top-level Downloads scan, so this slice used a bounded live Overpass batch.
- Dry-run evidence written to `output/osm-enrichment/overpass-batches-20260625.jsonl`: `rows_available=4,493`, `rows_selected=2`, `selected_listing_ids=[7, 8]`.
- Controlled live Overpass batch used `--limit 2`, `--radius-m 1000`, `--delay-seconds 2`, `--timeout-seconds 25`, and inserted `2` real rows with `rows_failed=0`.
- Exact-coordinate derivation then inserted `17` additional rows with `rows_failed=0` and no live OSM call.
- Selector after the batch reports `rows_available=4,491`, with first selected IDs `[10, 11, 13, 15, 16]`.
- Docker API now reports `osm_features_total=436`, `osm_featured_listings=436`, `osm_coverage_pct=2.56`, `osm_live_rows=12`, `osm_coordinate_derived_rows=424`, and `osm_infrastructure_coverage_source=live_overpass+coordinate_exact_match`.
- Verification passed: `tests/test_osm_enrichment.py` (`13` tests), `py_compile`, `ruff`, static audit against Docker API (`api 17046 {'cian': 2436, 'domclick': 14610}`), and CDP Grade-5 audit with `osm_rows=436`, `osm_coverage_pct=2.56`, `osm_coordinate_derived_rows=424`, real map interaction, and all screenshots clean.

Still incomplete or partial:

- OSM infrastructure coverage is still only `436 / 17,046` (`2.56%`), so district clustering must still be described as boundary-backed rather than full OSM-backed.
- Full OSM-backed district clustering still needs a controlled long-running Overpass batch over the remaining `4,491` distinct coordinates or a real local OSM extract/cache.

## 2026-06-25 OSM Selector And Coverage Smoke Addendum

The OSM backend now has a safer real-enrichment path for continuing toward broader infrastructure coverage:

- Live Overpass persistence skips coordinates that already have an OSM feature and selects one representative listing per missing distinct coordinate.
- `--live-overpass --dry-run --json` reports `selection_mode=live_overpass_missing_distinct_coordinates` and, after the smoke below, `rows_available=4,493` remaining missing distinct coordinates.
- A bounded live smoke inserted one real Overpass feature row with `rows_inserted=1`, `rows_failed=0`, `selected_listing_ids=[5]`.
- Exact-coordinate derivation then inserted `27` rows from that real feature.
- At that point, Docker API reported `osm_features_total=417`, `osm_featured_listings=417`, `osm_coverage_pct=2.45`, `osm_live_rows=10`, `osm_coordinate_derived_rows=407`, and `osm_infrastructure_coverage_source=live_overpass+coordinate_exact_match`.
- Verification passed for the code slice: `tests/test_osm_enrichment.py` (`12` tests), `py_compile`, and `ruff`.
- Static audit and CDP Grade-5 audit passed after the DB update; CDP evidence includes `osm_rows=417`, `osm_coverage_pct=2.45`, `osm_coordinate_derived_rows=407`, real map interactions, and all screenshots clean.

Still incomplete or partial:

- OSM infrastructure coverage was still only `417 / 17,046` (`2.45%`) at that point, so district clustering had to remain boundary-backed rather than full OSM-backed.
- At that point, full OSM-backed district clustering needed either a controlled long-running Overpass batch over the remaining `4,493` distinct coordinates or a real local OSM extract/cache.

## 2026-06-25 Inferred Lifecycle Forecast Addendum

The previous exposure gap has been narrowed without inventing terminal sale/removal outcomes:

- Confirmed terminal lifecycle remains unavailable: `terminal_lifecycle_target_rows=0`, `terminal_lifecycle_can_forecast=false`.
- A real inferred lifecycle target is now available from repeated source observations:
  - listing-source pair observed on at least two dates;
  - absent for at least `3` days before the latest observation date of the same source.
- Code-new API `127.0.0.1:8012` now reports `/stats/exposure-forecast` as `status=ready`, `can_forecast=true`, `target_source=observation_gap_inferred_lifecycle`, `method=gap_inferred_lifecycle_median_v1`.
- Fresh evidence: `inferred_lifecycle_target_rows=4,962`, `inferred_lifecycle_median_days=6`, `inferred_lifecycle_max_days=19`, while observed lower-bound remains `7,766` rows with median `7` and max `22`.
- This is a working forecast of disappearance from observations, not a confirmed sale/removal forecast. Demo text must keep that distinction.

Verification for this addendum:

- `python -m pytest -p no:cacheprovider tests/test_api_data_routes.py tests/test_api_monitoring.py tests/test_streamlit_api_client.py tests/test_streamlit_ui_payload.py -q`: `69 passed`.
- Broad sweep after the CDP fix also passed: `python -m pytest -p no:cacheprovider tests -q`, `python -m ruff check src services tests`, and `python -m compileall -q src services tests`.
- `python -m ruff check services/api/app/main.py services/streamlit/app.py tests/test_api_data_routes.py tests/test_api_monitoring.py tests/test_streamlit_ui_payload.py`: passed.
- `python -m py_compile services/api/app/main.py services/streamlit/app.py tests/test_api_data_routes.py tests/test_api_monitoring.py tests/test_streamlit_ui_payload.py`: passed.
- `PYTHONPATH=src;. API_BASE_URL=http://127.0.0.1:8012 python output\playwright\generate_static_audit.py`: passed with `api 17046 {'cian': 2436, 'domclick': 14610}`.
- CDP visual audit was updated for this semantic change and passed after diagnostic timeout hardening. Latest evidence includes `exposure_status=ready`, `exposure_inferred_target_rows=4962`, `exposure_target_source=observation_gap_inferred_lifecycle`, `map.loadedTiles=30/30`, real popup fields/link, and all seven screenshots at `clippedCount=0` / `overlapCount=0`.
- GitNexus dirty mirror was force re-indexed and used after this change: `3,143` nodes, `6,257` edges, `87` clusters, `200` flows. Impact for `_inferred_lifecycle_exposure_stats` reaches `/stats/data-quality`, `/stats/exposure-forecast`, and `/monitoring/status`.

## 2026-06-25 Broad Verification And Remaining Honest Gaps

Fresh verification against the current retained branch and code-new local runtime:

- `python -m pytest -p no:cacheprovider tests -q`: passed.
- `python -m ruff check src services tests`: passed.
- `python -m compileall -q src services tests`: passed.
- API `127.0.0.1:8011` and Streamlit `127.0.0.1:8509` health checks passed.
- Static audit regenerated from API `8011` and printed `api 17046 {'cian': 2436, 'domclick': 14610}`.
- CDP Grade-5 static audit passed with real API payload, map tile/zoom/drag/popup checks, data/deals/district/monitoring checks, and all seven screenshots reporting `clippedCount=0` and `overlapCount=0`.

Current evidence to keep in the demo:

- Full data count from API/DB: `17,046` listings, not the older stale local snapshot count.
- Observations: `44,765` rows across `22` observation dates.
- Model: `selected_price_model_v1_non_leaky`, `random_forest`, `r2=0.850303822452758`, `mae=8,001,983.659500307`, `rows_total=17,046`.
- District comparison/clustering: boundary-backed with `district_coverage_pct=84.47`, `district_extraction_source=admin_boundary_geojson+address_text`, `cluster_feature_source=districtComparison+boundary`.
- OSM infrastructure: `389` covered listings, `2.28%` coverage, `live_overpass+coordinate_exact_match` provenance.

Remaining honest gaps:

- Terminal exposure forecast is still unavailable because `lifecycle_target_rows=0`; observed-history lower-bound evidence must remain separate and must not be labelled as confirmed sale/removal forecast.
- District clustering is not broadly OSM-infrastructure-backed while OSM feature coverage is only `2.28%`.
- Docker image rebuild/runtime proof remains separate if Docker/WSL is unavailable; the code-new local runtime is the current verified runtime.
- Direct GitNexus analysis on the Cyrillic worktree path still fails, so current dirty-source graph checks should use `realtyscope-stitch-hybrid-redesign-20260625-dirty-worktree`, the ASCII mirror indexed with `3,130` nodes, `6,239` edges, `86` clusters, and `202` flows.

## 2026-06-25 OSM Exact-Coordinate Coverage Addendum

OSM infrastructure coverage has been expanded honestly from the previous 9-row live Overpass slice:

- Added a backend derivation path for exact coordinate matches: existing persisted OSM features can be copied only to listings with the identical `latitude` / `longitude`.
- The derived rows are explicitly marked in `source_summary` with `derivation=coordinate_exact_match`, `derived_from_listing_id`, `source_feature_version`, `source_live_osm_called`, and `live_osm_called=false`.
- CLI command used against the live DB: `python -m realtyscope.enrichment.osm --derive-coordinate-matches --write --limit 10000 --json`.
- First run result: `rows_inserted=380`, `rows_failed=0`; second run result: `rows_inserted=0`, proving idempotence.
- Code-new API `127.0.0.1:8011` now reports `osm_features_total=389`, `osm_featured_listings=389`, `osm_coverage_pct=2.28`, `osm_live_rows=9`, `osm_coordinate_derived_rows=380`, and `osm_infrastructure_coverage_source=live_overpass+coordinate_exact_match`.
- `/data?limit=5` shows persisted OSM feature columns for covered listings and blank OSM fields for uncovered rows; coverage is not fabricated for missing rows.
- Monitoring now renders the exact-coordinate derived row count, and CDP audit fails if this provenance disappears.

Verification:

- `python -m pytest -p no:cacheprovider tests/test_osm_enrichment.py tests/test_api_data_routes.py tests/test_streamlit_ui_payload.py -q`: `54 passed`.
- `py_compile` passed for touched API, Streamlit, OSM, and test files.
- `ruff` passed for touched API, Streamlit, OSM, and test files.
- Static audit against `API_BASE_URL=http://127.0.0.1:8011` passed with `17,046` listings.
- CDP audit passed with `osm_rows=389`, `osm_coordinate_derived_rows=380`, `osm_coverage_source=live_overpass+coordinate_exact_match`, and all seven screenshots at `clippedCount=0` / `overlapCount=0`.

Remaining caveat: this is still only `2.28%` OSM infrastructure coverage. It is stronger and traceable, but district comparison/clustering should still be described as boundary-backed, not full OSM-infrastructure-backed.

## 2026-06-25 Boundary-Backed District Analytics Addendum

District comparison and district clustering are no longer only address-text analytics. The current branch now has a real Moscow administrative-boundary lookup backed by listing coordinates:

- Added `data/external/moscow_district_boundaries.geojson` with `125` Moscow district features.
- Boundary provenance is recorded in `data/external/moscow_district_boundaries.metadata.json`: `GIS-Lab/OpenStreetMap`, `http://gis-lab.info/qa/osm-adm.html`.
- Added `src/realtyscope/analysis/district_boundaries.py` for `Polygon` / `MultiPolygon` lookup, bbox prefiltering, point-in-polygon with holes, district-name normalization, and UTF-8-BOM-tolerant metadata loading.
- Streamlit district assignment now prefers real boundary matches from `latitude` / `longitude`, then structured district fields, then address-text fallback.

Fresh payload evidence:

- `listings_total=17,046`.
- `boundary_matched_rows=14,386`.
- `boundary_coverage_pct=84.4`.
- `listings_with_district=14,399`.
- `coverage_pct=84.47`.
- `district_count=125`.
- `districtComparison=12`.
- `districtClusters=12`.
- `active_field=boundary_geojson`.
- `extraction_source=admin_boundary_geojson+address_text`.
- `cluster_feature_source=districtComparison+boundary`.

Fresh verification:

- GitNexus mirror refreshed at `C:\Users\lequa\gitnexus-worktrees\realtyscope-stitch-hybrid-redesign-20260625-index` with `3,068` nodes, `6,093` edges, `85` clusters, and `198` flows.
- GitNexus impact shows `_district_assignment_series` is a high-impact Streamlit payload path through district readiness, district values, comparison rows, `_build_payload`, and `main`.
- `python -m pytest -p no:cacheprovider tests/test_district_boundaries.py tests/test_streamlit_ui_payload.py tests/test_static_audit_requirements.py -q`: `38 passed`.
- `py_compile` passed for the boundary module, Streamlit app, touched tests, and static audit generator.
- `ruff` passed for the boundary module, Streamlit app, and touched tests.
- Static audit against the live API printed `api 17046 {'cian': 2436, 'domclick': 14610}`.
- CDP passed with `loadedTiles=16/30`, real map zoom/drag/popup evidence, boundary-backed district readiness, boundary-backed district clusters, and all seven screenshots at `clippedCount=0` / `overlapCount=0`.

Remaining caveats:

- District comparison is now boundary-backed, but OSM infrastructure coverage is still sparse (`389` featured listings / `2.28%`, mostly exact-coordinate derived), so district clustering is not broadly OSM-backed.
- Exposure is still observed-history lower-bound only; terminal sale/removal lifecycle target rows remain `0`.
- Trend remains descriptive only until a verified time-series forecast model exists.
- Docker API `127.0.0.1:8000` still needs rebuild/restart before it can prove the selected model and `/stats/exposure-forecast` in the Docker image.

## 2026-06-25 Selected Model And Verification Addendum

The selected-model path has been refreshed against the current 17,046-row live DB evidence:

- Code-new API on `127.0.0.1:8011` selects `data\processed\models\phase5\selected_price_model_v1_non_leaky.joblib`.
- The selected candidate is `random_forest`; feature version is `ml_features_v2_non_leaky`.
- Validation evidence in `/model/metadata`: `rows_total=17,046`, `train_rows=13,636`, `test_rows=3,410`, `r2=0.850303822452758`, `mae=8,001,983.659500307`, `rmse=18,417,146.2157716`, `mape=0.20497256239106884`.
- Candidate comparison is real and visible: `random_forest` beats Ridge; Ridge validation has `r2=0.5555901689314586` and `mae=16,640,622.08709979`.
- Trainer and runtime defaults were corrected so new manual training and fallback loading prefer selected non-leaky artifacts rather than the older baseline/leakage-prone defaults.

GitNexus was refreshed for this workstream:

- Direct indexing in the Cyrillic worktree still failed on `.gitnexus\lbug`.
- A current ASCII mirror was indexed at `C:\Users\lequa\gitnexus-worktrees\realtyscope-stitch-hybrid-redesign-20260625-index` with `2,958` nodes, `5,883` edges, `80` clusters, and `193` flows.
- GitNexus impact confirmed `Settings` is the broad-risk symbol for this change because API health/model metadata/monitoring/model loading depend on it; targeted API monitoring tests were therefore included.

Fresh UI/runtime verification:

- `API_BASE_URL=http://127.0.0.1:8011 python output\playwright\generate_static_audit.py`: `api 17046 {'cian': 2436, 'domclick': 14610}`.
- `node output\playwright\cdp_static_grade5_audit.mjs`: passed with API mode, `17,046` listings, `44,765` observations, `22` trend rows, selected-model provenance, real map tile/zoom/drag/popup checks, and all seven screenshot pages at `clippedCount=0` / `overlapCount=0`.
- Map tile loading now uses OpenStreetMap first with CARTO/HOT real-tile fallbacks; latest CDP evidence loaded `8` real tiles out of `30`.

Remaining readiness caveats for this earlier slice, superseded where noted by the boundary addendum above:

- Docker API `127.0.0.1:8000` still needs rebuild/restart before it can be used as final live evidence for the selected model or `/stats/exposure-forecast`.
- Exposure is ready only as observed-history lower-bound evidence; confirmed terminal sale/removal lifecycle target rows remain `0`.
- District comparison and clustering were address-text-only at this point; the later 2026-06-25 boundary addendum now verifies `admin_boundary_geojson+address_text` coverage at `84.47%`.
- OSM coverage remains sparse; this earlier slice had `9` featured listings / `0.05%`, superseded by the later exact-coordinate slice at `389` featured listings / `2.28%`.

## 2026-06-25 Live Data Refresh Addendum

The live dataset refreshed after the previous 16,512-row audit:

- Code-new API on `127.0.0.1:8010` with `PYTHONPATH=src;.` reported `17,046` listings against the live DB.
- Source counts are `cian=2,436` and `domclick=14,610`.
- Persisted observations are now `44,765` across `22` observed dates from `2026-05-14` through `2026-06-24`.
- Listings with observation history: `7,766`; max dates per listing: `20`; listing IDs with price changes: `1,415`.
- Terminal lifecycle target remains `0`, so sale/removal exposure is still not available.
- Observed-history lower-bound target rows are now `7,766`; `/stats/exposure-forecast` reports `status=ready`, `can_forecast=true`, `target_source=observed_history_lower_bound`, median observed exposure `7` days, max `22` days.
- Latest successful Domclick ingestion run is id `25`, started `2026-06-24T21:13:03.741795+00:00`, finished `2026-06-24T21:13:07.260925+00:00`, `records_seen=2,000`, `inserted_count=3,612`, `updated_count=1,466`, `rejected_count=0`.

Model caveat after the refresh:

- Code-new `/model/metadata` still selects local artifact `selected_price_model_v1_non_leaky` with `selected_candidate=random_forest`, validation `r2=0.8801698812234392`, `mae=7,933,891.650272489`, `rows_total=16,512`.
- This proves the selected-model code path and artifact selection, but it is not a retrain on the refreshed 17,046-row DB.
- Docker API `127.0.0.1:8000` was not rebuilt because WSL command startup failed with `Wsl/Service/0x8007274c`; it still reports the old baseline image and `/stats/exposure-forecast` returns `404`.

Fresh verification after data refresh:

- `API_BASE_URL=http://127.0.0.1:8010 python output\playwright\generate_static_audit.py`: `api 17046 {'cian': 2436, 'domclick': 14610}`.
- `node output\playwright\cdp_static_grade5_audit.mjs`: passed with `17,046` listings, `44,765` observations, `22` trend series rows, observed-history lower-bound exposure evidence, terminal lifecycle target `0`, district comparison still address-text partial with `13.8%` coverage at that time, OSM coverage still `9` rows / `0.05%`, and all seven screenshots at `clippedCount=0` / `overlapCount=0`. The district and exposure wording from this earlier slice is superseded by the later boundary-backed and terminal-forecast semantics addenda.

## 2026-06-24 Exposure Forecast Endpoint Addendum

Exposure forecast is now backed by a dedicated API contract, with honest target semantics:

- FastAPI exposes `GET /stats/exposure-forecast`.
- The endpoint returns terminal lifecycle target evidence separately (`terminal_lifecycle_target_rows`, `terminal_lifecycle_can_forecast`) and keeps current terminal lifecycle truth visible: `0` target rows.
- It returns observed-history lower-bound forecast evidence from persisted repeated observations (`observed_exposure_target_rows`, `median_observed_exposure_days`, `max_observed_exposure_days`, `forecast_segments`, `target_source=observed_history_lower_bound`) with a caveat that this is first-to-last observed date, not confirmed sale/removal exposure.
- Streamlit now fetches this endpoint separately and uses it in `exposureReadiness`, so the monitoring panel is not dependent on stale embedded data-quality fields.

Fresh code-new API evidence from `127.0.0.1:8010`:

- `/stats/exposure-forecast`: `status=ready`, `can_forecast=true`, `target_source=observed_history_lower_bound`, `terminal_lifecycle_target_rows=0`, `observed_exposure_target_rows=7,456`, median observed exposure `7`, max observed exposure `21`.
- `/stats/data-quality`: `16,512` listings, `42,765` observations, `21` observed dates from `2026-05-14` to `2026-06-23`, source counts `cian=2,436`, `domclick=14,076`.
- `/model/metadata`: selected local artifact `selected_price_model_v1_non_leaky`, selected algorithm `random_forest`, validation `r2=0.8801698812234392`, `rows_total=16,512`.

Fresh verification for this addendum:

- `python -m pytest -p no:cacheprovider tests/test_api_monitoring.py tests/test_streamlit_api_client.py tests/test_streamlit_ui_payload.py -q`: `49 passed`.
- `py_compile` passed for touched API/Streamlit/test files.
- `ruff` passed for touched API/Streamlit/test files.
- Static audit against code-new API `8010` printed `api 16512 {'cian': 2436, 'domclick': 14076}`.
- CDP passed with exposure `ready` through observed lower-bound, terminal lifecycle target still `0`, selected model provenance, real map interaction checks, and all seven screenshot pages at `clippedCount=0` / `overlapCount=0`.

Runtime caveat: Docker API `127.0.0.1:8000` still needs rebuild/restart before it can be used as final evidence for this endpoint and the selected model. During this slice it still reported the old baseline model image.

## 2026-06-25 Docker Runtime And Trend Forecast Superseding Addendum

The Docker runtime caveat above is superseded for the retained Stitch hybrid branch. Docker `api` and `streamlit` were hot-updated from the current branch, restarted, and verified on published localhost ports.

Current Docker-port evidence:

- `/health`: `status=ok`, `environment=docker`.
- Streamlit `/_stcore/health`: `ok`.
- `/stats/data-quality`: `listings_total=17,046`, `source_counts={'cian': 2436, 'domclick': 14610}`, `observations_total=44,765`, `observation_date_count=22`, first observed date `2026-05-14`, last observed date `2026-06-24`, `listings_with_observation_history=7,766`, max `20` dates per listing, `listing_price_change_count=1,415`, `lifecycle_target_rows=0`.
- `/model/metadata`: selected artifact `selected_price_model_v1_non_leaky`, selected algorithm `random_forest`, `model_selection_reason=best_validation_metric`, validation `r2=0.8801698812234392`, `mae=7,933,891.650272489`, `rows_total=16,512`, `feature_count=23`.
- `/stats/exposure-forecast`: `status=ready`, `can_forecast=true`, `target_source=observed_history_lower_bound`, `terminal_lifecycle_target_rows=0`, `terminal_lifecycle_can_forecast=false`, `observed_exposure_target_rows=7,766`, median observed exposure `7`, max observed exposure `22`.
- `/stats/observation-trend`: `status=ready`, `can_forecast=true`, `forecast_method=linear_median_price_per_m2_v1`, `forecast_horizon_days=7`, `history_points=22`, `trend_slope_per_day=-1648.29`, forecast rows `2026-06-25` through `2026-07-01`.
- Monitoring UI renders those trend `forecast_rows` as a visible `Прогноз медианы за м²` table, and the CDP audit now fails if a payload with trend forecast rows does not render that table.

Trend forecast scope: this is a simple, test-covered linear forecast over persisted daily median price per m2. It is now a real backend/API/UI feature, but it is not a forecast-vs-actual validation result and should not be presented as a production-grade market forecast.

Verification after this update:

- `python -m py_compile services\api\app\main.py services\streamlit\app.py tests\test_api_monitoring.py tests\test_streamlit_ui_payload.py`: passed.
- `python -m ruff check services/api/app/main.py services/streamlit/app.py tests/test_api_monitoring.py tests/test_streamlit_ui_payload.py`: passed.
- `python -m pytest -p no:cacheprovider tests/test_api_monitoring.py tests/test_streamlit_ui_payload.py -q`: `39 passed`.
- `python output\playwright\generate_static_audit.py`: passed with API payload `17046 {'cian': 2436, 'domclick': 14610}`.
- `node output\playwright\cdp_static_grade5_audit.mjs`: passed with selected model, exposure lower-bound forecast, trend `can_forecast=true`, real map interactions, and seven clean screenshots.
- A clean `docker compose -p realtyscope build streamlit` packaging smoke was attempted after the UI update, but `uv sync --frozen --no-dev --extra streamlit --no-install-project` again ran long on heavy dependencies. The build was terminated cleanly and runtime health remained green; final immutable image rebuild remains a packaging task, not current runtime evidence.

Still incomplete or partial:

- Terminal sale/removal exposure remains unavailable because `lifecycle_target_rows=0`.
- District comparison and clustering are boundary-backed (`admin_boundary_geojson+address_text`) but not broadly OSM-infrastructure-backed because OSM feature coverage remains `389` listings / `2.28%`.

## 2026-06-24 Selected Model / Observed Exposure Addendum

Model-selection status improved, with one runtime caveat:

- The code path now supports selected model artifacts end to end, and the trainer Dockerfile now defaults to `--trainer selected`.
- Local artifact selector chooses `selected_price_model_v1_non_leaky.joblib` with `selected_candidate=random_forest`, validation `r2=0.8801698812234392`, `mae=7,933,891.650272489`, and `rows_total=16,512`.
- A temporary code-new FastAPI server on `127.0.0.1:8010` verified `/model/metadata` for the selected artifact and generated the latest static/CDP audit.
- The already-running Docker API on `127.0.0.1:8000` remains baseline until WSL/Compose can retrain/rebuild and `GET /model/metadata` from port `8000` proves the selected artifact is in the Docker model volume. A Docker trainer attempt hung during image build and WSL returned `Wsl/Service/0x8007274c`.

Exposure forecasting status is no longer simply missing, but its target semantics are narrower than terminal sale/removal exposure:

- Terminal lifecycle evidence is unchanged and honest: `lifecycle_target_rows=0`.
- API data-quality now computes an observed-exposure lower-bound target from persisted repeated observations: first observed date to last observed date for each stable source listing.
- Code-new API evidence reports `observed_exposure_target_rows=7,456`, `observed_exposure_can_forecast=true`, median observed exposure `7` days, max `21` days, and source `observed_history_lower_bound`.
- Monitoring UI renders this as `Наблюдаемая экспозиция`, `Источник прогноза`, and a `Прогноз по комнатности` table. This should be presented as a real lower-bound observed-exposure forecast, not as a confirmed sale/removal forecast.

Historical district comparison/clustering note from this earlier slice:

- No usable local Moscow admin-boundary GeoJSON/shapefile was found.
- GIS-Lab/data.mos `617_shp.7z` was downloaded and inspected, but it has tiny/old geometry and is not enough for full district coverage.
- A bounded Overpass administrative-boundary query returned `504 Gateway Timeout`; do not retry aggressively or fabricate polygons.
- Current district rows/clusters were still real address-text analytics (`coverage_pct=14.21`) at this point. The later 2026-06-25 boundary addendum supersedes this with real boundary coverage; OSM feature coverage remains sparse.

Fresh verification for this addendum: targeted tests passed with `47 passed`; `py_compile` passed; `ruff` passed; `API_BASE_URL=http://127.0.0.1:8010 python output\playwright\generate_static_audit.py` printed `api 16512 {'cian': 2436, 'domclick': 14076}`; `node output\playwright\cdp_static_grade5_audit.mjs` passed with selected model provenance, observed exposure lower-bound readiness, terminal lifecycle target still `0`, and no clipped/overlapping screenshots.

## 2026-06-24 Analytic Table Visibility Addendum

Valuation model fallback addendum: `_build_payload()` now includes the saved local Ridge model payload when the real artifact is loadable, even if live `/model/metadata` is already present. This keeps the static audit and file-based reviewer flow on a real model path instead of silently dropping to the median estimate when browser fetch to `/predict` is unavailable. The CDP audit now checks `valuation.calculationUsesModelWhenAvailable`, so a payload with model support may pass with `Расчет сервиса` or `Расчет модели`, but not with only `Ориентир по базе`.

Verification after this valuation addendum: the new pytest expectation first failed because `payload["localModel"]` was `None` with API metadata present; the new CDP gate also failed on `valuation.calculationUsesModelWhenAvailable`. After the fix, `py_compile`, `ruff`, targeted pytest (`25 passed`), static audit (`api 16512 {'cian': 2436, 'domclick': 14076}`), and CDP passed. Latest CDP evidence includes `valuation.calculationUsesModelWhenAvailable=true`, `valuation.rowCount=6`, real comparable links, and all seven screenshot pages with `clippedCount=0` / `overlapCount=0`.

Data date-format addendum: visual review found the `Данные` date column wrapping locale timestamps as `24.06.2026` followed by a second line beginning with `, 01:25`. `services/streamlit/app.py` now uses a table-specific date renderer that keeps the full date and time but removes the comma, and `output/playwright/cdp_static_grade5_audit.mjs` now checks `data.hasCleanDateFormatting` on rendered date cells. The gate failed before the formatter change and passed after it; the regenerated screenshot shows clean two-line date/time cells without an orphan comma.

Dashboard recent-listings addendum: the dashboard `Новые поступления` feed now uses `recentListingRows()` to sort real listings by `observed_at` / `created_at` / `updated_at` before rendering the first rows. The CDP audit now checks `dashboard.hasRecentListingsFeed`, `dashboard.recentListingsHaveRealLinks`, and `dashboard.recentListingsSortedByObservationDate` so this dashboard card cannot regress to arbitrary payload order or synthetic links.

Data table default-order addendum: the `Данные` page now uses latest-first default ordering by real observation timestamp until the user explicitly clicks a sortable column. The CDP audit now checks `data.defaultSortedByObservationDate` against the API-backed source links sorted by `observed_at` / `created_at` / `updated_at`.

Observation-day UI addendum: the CDP audit now checks that the `Мониторинг` exposure and trend panels render observation-day and observation-row counts from the real API payload, not from a small fixture or `limit=3` preview. Latest evidence passed with `observation_date_count=21`, `raw_observation_rows=42,765`, and `doesNotCollapseObservationDatesToFixture=true`.

Observation trend series addendum: `/stats/observation-trend?limit=60` now returns a real descriptive daily median series from persisted `listing_observations`. Latest Docker API evidence returned HTTP 200; the static payload embeds `observationTrendSeries=21` from `2026-05-14` to `2026-06-23`, and CDP now fails if this series is empty, date-count mismatched, or date-range mismatched. This is still not a forecast: `can_forecast=false`.

OSM coverage addendum: `/stats/data-quality` now exposes persisted OSM feature coverage and `/data` includes OSM feature columns for listings that have `osm_features`. A bounded live Overpass attempt inserted 5 rows and updated 2 rows, but 13 of 20 selected listings failed with `429`/`504`, so the current verified coverage is still small: `osm_features_total=9`, `osm_featured_listings=9`, `osm_coverage_pct=0.05`, `osm_feature_version=osm_local_v1`, `osm_attribution=OpenStreetMap contributors`. The district clustering code can use OSM columns and marks `feature_source=districtComparison+osm` when those columns are present in the district matrix; at that time the live payload still showed `cluster_feature_source=districtComparison`. The later boundary addendum supersedes the district source with `districtComparison+boundary`, while OSM coverage remains sparse.

District analytics addendum: the static/API payload now fetches bounded full analytics pages for district comparison while keeping the visible listing preview small. Earlier API/static/CDP evidence verified `16,512` listings, `districtComparison=12`, `districtClusters=12`, `cluster_count=3`, `district_extraction_source=address_text`, `listings_with_district=2,346`, `district_count=120`, and `coverage_pct=14.21`. These rows were real source-address district names; the later boundary addendum supersedes them with `district_extraction_source=admin_boundary_geojson+address_text` and `coverage_pct=84.47`.

Count discrepancy and model-selection addendum: direct runtime checks showed the API/DB total is consistent at `16,512` across `/stats/data-quality`, `/data`, `/listings`, and `/monitoring/status`. The lower local count was traced to `output/cache/streamlit_ui_payload.json`, a stale but real snapshot fallback with `mode=snapshot`, `listings_total=15,765`, and `source_counts={'domclick': 13324, 'cian': 2441}`. Static audit regenerated after this investigation stayed in API mode with `api 16512 {'cian': 2436, 'domclick': 14076}`. Backend code now supports real model selection: `train_selected_model()` trains `ridge` and `random_forest` candidates on the same grouped split and records `selected_candidate` plus candidate metrics; API startup can choose the best `.joblib` artifact by validation `r2`/`mae` via `MODEL_SELECTION_MODE=best_metric`; `/model/metadata` exposes selection provenance; Monitoring renders it in Russian. This is code/test-ready, not yet promoted live: Docker API must be rebuilt and a selected artifact must be trained/promoted before claiming the live model is no longer the current `baseline_ridge_v2_non_leaky`.

The latest UI slice fixed hidden right-side table columns in `Данные` and `Выгодные предложения`. `services/streamlit/app.py` now uses compact analytic-table layouts, compact Russian labels with full Russian tooltips, and fixed semantic columns so money/date/source/room/area/floor values stay inside the desktop card. `output/playwright/cdp_static_grade5_audit.mjs` now fails if `data.importantColumnsVisible` or `deals.importantColumnsVisible` regresses, and it checks restored fields by `data-sort` keys rather than only by DOM text.

Verification after this addendum: `py_compile` passed, `ruff` passed, targeted pytest passed with `25 passed`, static audit used Docker API payload `api 16512 {'cian': 2436, 'domclick': 14076}`, and CDP passed with both table visibility gates true, `valuation.initialPromptHonest=true`, `map.popupHasExplicitListingLink=true`, `loadedTiles=8 >= 8`, plus all screenshot `clippedCount=0` and `overlapCount=0`.

Map popup follow-up: map popups now render an explicit `Открыть объявление` action only from real `source_url` values; no synthetic links are shown when the source URL is absent.

Map drag/pan follow-up: the CDP audit now checks `map.dragPanChanged` by simulating pointer drag on the map surface. Latest evidence passed with `loadedTiles=8 >= 8`; the map center changed from `{lon: 37.618423, lat: 55.751244}` to `{lon: 37.82441665234373, lat: 55.664199153470705}` after drag.

Audit hardening follow-up: `output/playwright/generate_static_audit.py` now requires API mode, real `source_counts`, and at least 10,000 listings by default. It retries briefly for cold API responses and exits non-zero instead of silently accepting an offline payload. `STATIC_AUDIT_ALLOW_OFFLINE=1` is reserved for explicit offline/snapshot debugging.

## Sources Reviewed

- Original assignment: `E:\Магистр\2-курс\python\MISIS_2025\season_2\Описание проекта.html`.
- Project spec: `docs/superpowers/specs/2026-05-31-realtyscope-design.md`.
- Course traceability: `docs/course-guidance/realtyscope-user-story-traceability.md`.
- Stack traceability: `docs/course-guidance/realtyscope-stack-architecture-traceability.md`.
- Project status: `docs/project-status.md`.
- UI design system: `docs/design/DESIGN.md`.
- UI continuation checkpoint: `docs/design/NEXT_SESSION_UI_CHECKPOINT.md`.
- Recent mem0 checkpoints for project `python`.

## Executive Finding

The current UI branch is now the correct branch to keep for further UI work. It uses the compact real Streamlit UI payload with `16,512` listings in the static audit: `14,076` from `Домклик` and `2,436` from `ЦИАН`. The old problem where the dashboard only showed a much smaller subset has been fixed.

However, the project must not yet be described as fully finished for all assignment and real-estate-topic analytics. The base grade-5 stack is largely present, but several advanced real-estate analytics from the topic card and earlier plans are still partial or missing as real backend algorithms. The UI should continue to show these honestly as planned or partial until the data/model layer exists.

## Requirement Audit

| Requirement / planned capability | Status | Evidence now | Gap / next action |
| --- | --- | --- | --- |
| Automatic real data collection | Implemented, needs final refresh evidence | Domclick daily/scheduled batch docs and latest local payload. Latest known run loaded `2,000` raw/normalized/ml-ready Domclick rows, `541` created, `1,459` updated, `1,997` observations inserted. | In next session, refresh today's ingestion report from DB/reports and update UI/doc counts only from real files or API. |
| Multiple data sources | Implemented for UI payload | Static audit reports `Домклик: 14,076`, `ЦИАН: 2,436`. | Keep source labels truthful. Do not show Avito/Yandex unless real rows exist. |
| PostgreSQL + Alembic persistence | Implemented in base project | SQLAlchemy models, Alembic migrations, persisted listings/observations/OSM feature tables in prior docs/tests. | Re-run Docker/DB smoke after final backend changes. |
| OpenStreetMap infrastructure | Partial, backend path working for persisted rows | OSM feature contract is present in the model/payload. `/stats/data-quality` now reports real persisted OSM coverage; `/data` exposes OSM feature fields for enriched listings; latest live evidence has `osm_features_total=436`, `osm_featured_listings=436`, `osm_coverage_pct=2.56`, `osm_live_rows=12`, `osm_coordinate_derived_rows=424`, attribution `OpenStreetMap contributors`, and provenance `live_overpass+coordinate_exact_match`. | Expand enrichment coverage with a reliable bounded data source or scheduled Overpass strategy. Do not claim full OSM coverage while live coverage is `2.56%`. |
| EDA and charts | Partial | Dashboard has segment median and volume charts from real payload; static audit passes. | Add complete, non-clipped charts for distribution, price/m2 by rooms, source split, trend over observations, district comparison when district data exists. |
| ML price prediction | Partial but functional baseline, selected-trainer path added | `/predict` and local model fallback exist; UI returns a real API/local model result and now shows comparable listings selected from real payload rows by room count, area distance, and price per m² distance. Code/tests now include `train_selected_model()` and API artifact selection by real validation metrics, but the currently promoted live model remains `baseline_ridge_v2_non_leaky`. | Train selected model on the full real DB, verify metrics/MLflow, rebuild/restart API, and only then claim the live estimator is selected rather than baseline. |
| MLflow / MLOps | Implemented for baseline evidence | Prior project docs record MLflow run and registered model version. | Re-run final MLflow evidence after model improvement, not from stale docs. |
| FastAPI + Swagger | Implemented for base scope | `/health`, `/data`, `/predict`, `/model/metadata`, `/monitoring/status` are documented/tested in prior phases. | Re-run live API smoke after final backend/UI merge. |
| Redis read cache | Implemented for `/data` / `/listings` path | Prior status docs record real Redis key proof. | Re-run short Redis proof in final demo. |
| Streamlit pages >= 3 | Implemented | Current custom Streamlit shell includes dashboard, valuation, heatmap, deals, segment comparison, data, monitoring. | Continue page-level polish against Stitch A/B and user feedback. |
| Monitoring/logs | Partial, improved | UI shows last collection, source status, model quality, bounded log pagination, and no raw internal/API trace text in the Chrome/CDP audit. | Populate `app_logs` consistently from runtime operations for deeper backend evidence. |
| Feature importance / model insight | Partial | Baseline model insight exists; UI shows model quality cards. | Add clearer feature descriptions and SHAP/permutation only if produced by real model artifacts. |
| Data table search/filter/pagination | Partial, improved | Filters, linked addresses, source links, refresh buttons, pagination, per-column sort hooks, and page-local filter state exist. Main data table now restores address/link, source, rooms, area, floor, observed date, price, and price per m². | Continue visual density review against Stitch A/B and add any reviewer-required columns only when real data exists. |
| Map / heatmap | Partial, improved | OSM/CARTO tile grid, heat/point controls, point layers, wheel zoom, drag/pan, Moscow coordinate filtering, popup details, and coordinate-quality stats exist in UI code. Static audit confirms real Moscow coordinate rows and source-linked popups; current real API payload has `16,512` listings. Chrome/CDP audit loaded `30` tile nodes, changed zoom `10 -> 11 -> 12`, and opened a real listing popup with price, price per m², rooms, area, floor, and source. | Keep tile fallback behavior under review and keep future visual audits bounded because Browser MCP is unstable in this workspace. |
| Детекция "выгодных" предложений | Partial, improved | Deal page now uses a defensible real score based on discount to room-segment median price/m², MAD-based robust deviation, quantile within the current filtered segment, and minimum segment sample size. Static audit contains `deal_score` and `segment_sample_size`. | If a stronger promoted model becomes available later, upgrade to model-predicted fair-price discount and document model metrics. |
| Сравнение районов | Implemented with real boundary-backed assignment, still not broadly OSM-backed | Latest boundary payload matches `14,386` listings to Moscow district polygons, covers `84.47%` overall with boundary plus address fallback, identifies `125` districts, and renders `12` comparison rows from real price/source data. Source: `GIS-Lab/OpenStreetMap`. | Keep coverage/provenance visible. Do not claim OSM infrastructure completeness while OSM feature coverage is `2.56%`. |
| Кластеризация районов по характеристикам | Implemented over real boundary-backed district aggregates; OSM matrix still sparse | CDP verifies `districtClusters=12`, `cluster_count=3`, and current live `feature_source=districtComparison+boundary`. The cluster matrix is backed by real district aggregates; OSM feature columns remain limited because only `9` listings have persisted OSM infrastructure rows. | Expand OSM enrichment before calling clusters broadly OSM-backed. Keep `feature_source` visible. |
| Прогноз срока экспозиции | Missing, readiness measured | Monitoring now measures exposure forecast readiness from real observations. Current Docker API evidence reports `42,765` persisted observations across `21` observed dates from `2026-05-14` to `2026-06-23`, `7,456` listings with observation history, max `19` dates per listing, `1,300` listing IDs with price changes, `exposure_target_rows=0`, and `canForecast=false`. | Define target from listing first/last seen or terminal status data, train model only after target rows exist, then expose API/UI with caveats. |
| Trend / forecast | Partial, descriptive only | Monitoring now shows `Готовность тренда` from real observation evidence, and `/stats/observation-trend?limit=60` now exposes a real daily median series from persisted observations. Current PostgreSQL/API/static/CDP evidence reports `42,765` persisted observations across `21` observed dates from `2026-05-14` to `2026-06-23`, `7,456` listings with observation history, `1,300` listing IDs with price changes, and `observationTrendSeries=21`. | Add period filters and forecast only after repeated observation semantics are validated and a verified time-series model exists. Current `can_forecast=false`. |

## UI Branch Status

- Keep: `ui/stitch-hybrid-redesign-20260623`.
- Main changed files: `services/streamlit/app.py`, `services/api/app/main.py`.
- The dashboard chart clipping report was addressed by increasing chart height/top padding, reducing max trend bar height, and switching top value labels to short horizontal `тыс.` labels.
- The latest UI slices restored main data-table floor/date fields, made map point payload self-contained for real popups, reports Moscow coordinate filtering quality, replaced median-only deal display with robust real segment scoring, added real valuation comparables, added the district-comparison path, and added a monitoring service-contour card. The current boundary addendum supersedes earlier address-text-only district evidence with `admin_boundary_geojson+address_text` coverage.
- `/monitoring/status` now exposes service rows for API, PostgreSQL, Redis cache, model, and ingestion. The snapshot UI uses those semantics conservatively: API is unavailable, the prepared local vitrine/model/ingestion evidence is available, and PostgreSQL/Redis are marked `Не проверено` rather than online.
- Verification after this slice:
  - `python -m py_compile services\streamlit\app.py services\api\app\main.py`: passed.
  - `python -m ruff check services\streamlit\app.py services\api\app\main.py tests\test_streamlit_ui_payload.py tests\test_api_monitoring.py`: passed.
  - `python -m pytest -p no:cacheprovider tests\test_streamlit_api_client.py tests\test_streamlit_scaffold.py tests\test_streamlit_dashboard_charts.py tests\test_streamlit_ui_payload.py tests\test_api_monitoring.py -q`: `42 passed`.
  - `python output\playwright\generate_static_audit.py`: passed with API payload `16512 {'cian': 2436, 'domclick': 14076}`.
  - `node output\playwright\cdp_static_grade5_audit.mjs`: passed; verified real payload counts, valuation comparable listings with real links, map tiles/zoom/popup, restored data-table columns and pagination/export, clean data-date formatting, deal scoring columns and explanation, `Сегменты и районы` segment comparison plus district/clustering missing-state panels without fake ranking, monitoring bounded logs, explicit partial/missing analytics labels, exposure readiness without fake forecast, trend readiness without fake forecast, and no internal trace/error text.

  - Latest API/static monitoring evidence verifies the `Статус контуров` rows with live Docker API mode, `16,512` rows, service rows `api/database/cache/model/ingestion=ok`, model provenance card `Контур модели` with `baseline_ridge_v2_non_leaky` / `ml_features_v2_non_leaky` and an explicit baseline caveat, and latest ingestion successful for `domclick`.

  - Earlier API/static/CDP district payload evidence verified `district_rows=12`, `district_coverage_pct=14.21`, `district_extraction_source=address_text`, `listings_with_district=2,346`, and `district_count=120`; this is superseded by the 2026-06-25 boundary addendum with `coverage_pct=84.47` and `extraction_source=admin_boundary_geojson+address_text`.

  - Earlier API/CDP cluster evidence verified `cluster_rows=12`, `cluster_count=3`, and `cluster_feature_source=districtComparison`; this is superseded by `cluster_feature_source=districtComparison+boundary`. The remaining caveat is sparse OSM feature coverage, not missing boundary assignment.

  - Latest API exposure payload evidence verifies `exposure_status=missing`, `exposure_raw_observation_rows=42,765`, `exposure_history_listings=7,456`, `exposure_max_dates_per_listing=19`, `exposure_target_rows=0`, `exposure_observation_dates=21`, `observation_span_days=21`, and `canForecast=false`.

  - Runtime PostgreSQL lifecycle evidence from `realtyscope-db-1` verifies repeated observations but no terminal exposure target: `observations_total=42,765`, `observation_date_count=21`, first date `2026-05-14`, last date `2026-06-23`, `listings_with_observation_history=7,456`, max `19` dates per listing, `1,300` listing IDs with price changes, `observation_status_counts={'observed': 42,765}`, `inactive_observations_total=0`, and `lifecycle_target_rows=0`.

  - Latest API trend payload evidence verifies `trend_status=partial`, `trend_observations=42,765`, `trend_observation_dates=21`, `trend_price_changes=1,300`, and `trend_can_forecast=false`. The live `/stats/observation-trend?limit=5` smoke returned 5 rows from `2026-06-19` through `2026-06-23`; the static payload contains `observationTrendSeries=21` from `2026-05-14` through `2026-06-23`. The Chrome/CDP audit now fails if the monitoring page does not render the `Готовность тренда` panel, if that panel stops marking the forecast as not built, or if the backend trend series disappears/mismatches the observation date range.

  - Latest live Docker/API/Redis/MLflow smoke on `2026-06-24` built and started `redis`, `mlflow`, `api`, and `streamlit` from this branch. Compose showed `db`, `redis`, `api`, and `streamlit` healthy and `mlflow` up. HTTP checks returned 200 for API `/health`, filtered `/data`, `/model/metadata`, `/monitoring/status`, Streamlit `/_stcore/health`, and MLflow root. Runtime `/monitoring/status` reported environment `docker`, `16,512` listings, `42,765` observations, service rows `api/database/cache/model/ingestion=ok`, and `lifecycle_target_rows=0`. `/predict` returned `27,115,216.38` RUB for the full 23-feature demo vector with `baseline_ridge_v2_non_leaky`, `ml_features_v2_non_leaky`, `rows_total=8,366`, and `r2=0.6231827045433119`. MLflow registry returned `realtyscope-price-model` version `4` status `READY`. Redis scan observed `realtyscope:listings:v2:limit=1:offset=0:min_price_rub=10000000:rooms=2`; a later `DBSIZE=0` is consistent with the short TTL expiring.

  - Runtime caveat: after the long cold Docker build, several fresh WSL launch attempts returned `Wsl/Service/0x8007274c` while already-running containers and localhost endpoints still responded. Re-run short WSL/Compose checks before the live defense and avoid claiming WSL itself was stable for the whole slice.

## Git Cleanup Audit

An archive bundle was created before deleting anything:

`output/git-archives/old-ui-branches-20260624.bundle`

`git bundle verify` reports that the bundle contains complete history for these old UI refs:

- `ui/phase9d-russian-dashboard-redesign-20260620`
- `ui/realtyscope-dashboard-redesign`
- `ui/realtyscope-review-workbench`
- `ui/realtyscope-ultimate-redesign`
- `ui/recovered-real-data-dashboard-20260620`
- `ui/stitch-final-redesign-20260622`
- `ui/stitch-precise-b`

No old UI branch was force-deleted in this session because:

- Several old UI branches are not merged into the current UI branch.
- Some branches are checked out in separate worktrees.
- `ui/stitch-precise-b` has untracked Stitch/export/temp files in `E:\Магистр\2-курс\python\RealtyScope`.

Safe next step: after user confirms that the untracked files in the old `ui/stitch-precise-b` worktree are disposable or archived elsewhere, remove old worktrees and then delete old branches from the verified bundle.

## 2026-06-25 Exposure Semantics Correction Addendum

This addendum supersedes older evidence in this audit that treated observed-history lower-bound
rows as full exposure forecast readiness.

- Verified runtime in this slice: FastAPI `http://127.0.0.1:8011`, Streamlit
  `http://127.0.0.1:8509`. Docker `8000` was not freshly verified in this slice.
- Data evidence from `/stats/data-quality`: `17,046` listings, `cian=2,436`,
  `domclick=14,610`, `44,765` observations, `22` observation dates from `2026-05-14`
  through `2026-06-24`, `7,766` listings with observation history, max `20` dates per listing,
  `1,415` price-change listing IDs, and `lifecycle_target_rows=0`.
- Correct exposure contract from `/stats/exposure-forecast`: `status=partial`,
  `can_forecast=false`, `terminal_lifecycle_target_rows=0`,
  `terminal_lifecycle_can_forecast=false`, `target_source=observed_history_lower_bound`,
  `observed_exposure_target_rows=7,766`, `observed_exposure_can_forecast=true`,
  median observed exposure `7` days, max `22` days. This is real lower-bound evidence only,
  not a confirmed sale/removal exposure model.
- Monitoring UI wording now avoids fake forecast wording for observed-only exposure evidence:
  it renders lower-bound labels and keeps terminal lifecycle target rows visible as `0`.
- The CDP audit now fails if terminal lifecycle rows are `0` but the app sets exposure
  `can_forecast=true`; it accepts observed lower-bound evidence only when
  `observed_exposure_can_forecast=true` is separate from terminal `can_forecast=false`.
- Verification passed: `65` targeted tests, `py_compile`, `ruff`, API static audit, and
  CDP Grade-5 audit with all seven screenshots clean and map interaction checks passing.

## 2026-06-24 Source Metadata And Runtime Caveat Addendum

- The API code now restores real source metadata in `/data` and `/listings`: `source_name`, `source_label`, `source_listing_id`, `source_url`, and latest `observed_at` are derived from persisted source-link/raw/observation tables, not fabricated in the UI.
- `/stats/data-quality` now returns real source mix counts from DB links. Local audit against the real runtime DB through temporary API `127.0.0.1:8010` reported `16,512` listings with `source_counts={'cian': 2436, 'domclick': 14076}`.
- Static/CDP audit generated through API `8010` verified real source labels/links in valuation comparables and the data table, real map popup source, source mix in payload, partial address-text district comparison/clustering when district rows exist, exposure forecast still missing with `lifecycle_target_rows=0`, trend still descriptive-only, and `remaining_audit_chrome=0`. The district part of this older audit is superseded by the boundary-backed addendum.
- The already-running Docker API on `127.0.0.1:8000` is healthy and model-ready, but it is still the older image for this source-metadata slice: `/data?limit=1` returns null source fields and `/stats/data-quality` has no `source_counts`. Rebuild/restart Docker API and Streamlit from this branch before using Docker `8000/8501` as final demo evidence.
- Docker CLI was unavailable in the Windows PATH and WSL returned `Wsl/Service/0x8007274c` during this slice, so Docker rebuild could not be verified honestly in this session.

## 2026-06-24 Docker Runtime Refresh Addendum

- WSL later recovered enough to rebuild/restart Docker `api` and `streamlit` from this branch. Compose then reported `db`, `redis`, `api`, and `streamlit` healthy, with `mlflow` up.
- Docker `127.0.0.1:8000` now reflects the source-metadata code:
  - `/data?limit=1` includes real source metadata: `source_name=domclick`, `source_label=Домклик`, `source_listing_id=2069068416`, `source_url=https://domclick.ru/card/sale__new_flat__2069068416`, `observed_at=2026-06-02T00:36:56.568203+00:00`.
  - `/stats/data-quality` includes `source_counts={'cian': 2436, 'domclick': 14076}`, `listings_total=16,512`, `observations_total=42,765`, and `lifecycle_target_rows=0`.
  - `/model/metadata` reports `status=ready`, `model_version=baseline_ridge_v2_non_leaky`, and `feature_count=23`.
  - `/monitoring/status` reports environment `docker`, service rows `api/database/cache/model/ingestion=ok`, source counts, and ready model status.
  - `/predict` returns `27,115,216.38317985` RUB for the full 23-feature demo vector, with the baseline caveat and `r2=0.6231827045433119`.
  - Streamlit `/_stcore/health` returns `200 ok`.
- Redis cache proof after a filtered `/data` request: `realtyscope:listings:v2:limit=1:offset=0:min_price_rub=10000000:rooms=2`.
- Static audit without `API_BASE_URL` override now uses Docker `8000` and prints `api 16512 {'cian': 2436, 'domclick': 14076}`.
- Chrome/CDP audit against the Docker-backed static HTML passed and ended with `remaining_audit_chrome=0`. It verified real comparable links, restored data-table source rows, map popup source, service contour with model ready, missing exposure forecast, descriptive-only trend, and no clipped layout offenders.
- WSL remains intermittent: a later `wsl docker exec` Redis proof hit `Wsl/Service/0x8007274c`, so final demo checks should prefer already-published localhost endpoints or retry WSL before Compose commands.

## 2026-06-24 Per-Page Screenshot Evidence

- The CDP audit now captures one current screenshot per main page:
  - Dashboard: `output/playwright/realtyscope-static-grade5-dashboard.png`
  - Оценка квартиры: `output/playwright/realtyscope-static-grade5-valuation.png`
  - Тепловая карта: `output/playwright/realtyscope-static-grade5-map.png`
  - Выгодные предложения: `output/playwright/realtyscope-static-grade5-deals.png`
  - Сравнение сегментов/районов: `output/playwright/realtyscope-static-grade5-segments.png`
  - Данные: `output/playwright/realtyscope-static-grade5-data.png`
  - Мониторинг/model insights: `output/playwright/realtyscope-static-grade5-monitoring.png`
- Latest Docker-backed CDP run verified all seven screenshot pages with `clippedCount=0` and `overlapCount=0`.
- The map gate now waits for real tile images and fails if none load. Latest evidence: `tileCount=30`, `loadedTiles=16`, zoom changed `10 -> 11 -> 12`, and popup showed real listing fields and source.
- Latest map interaction evidence also verifies `map.dragPanChanged=true` with `loadedTiles=8 >= 8`; pointer drag changed the stored Moscow map center instead of leaving the map as a static image.
