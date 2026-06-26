# RealtyScope Next Goal Handoff

Date: 2026-06-25
Branch: `ui/stitch-hybrid-redesign-20260623`
Workspace: `E:\Магистр\2-курс\python\RealtyScope-stitch-hybrid-redesign-20260623`

Use this handoff to start a fresh session/goal. The previous goal ran for a long time and had multiple context compactions, so the next session should resume from current repo/runtime evidence, not from memory alone.

## Current Integration Branch Local Runtime After Manual Model Selection

Current branch: `integration/realtyscope-grade5-final-20260625`.

This is the latest code-new evidence. Treat Docker `8000/8501` as earlier evidence until it is rebuilt/rechecked for this exact slice.

- FastAPI was started from this integration worktree on `127.0.0.1:8016` with `MODEL_SELECTION_MODE=best_metric`; `/health` returned `status=ok`, `environment=local`.
- `/monitoring/status`: `17,046` listings, `source_counts={'cian': 2436, 'domclick': 14610}`, `44,765` observations, `22` observation dates, `lifecycle_target_rows=0`, `inferred_lifecycle_target_rows=4,962`, `osm_features_total=17,046`, `osm_featured_listings=17,046`, `osm_coverage_pct=100.0`, `osm_local_extract_rows=4,487`, `osm_live_rows=16`, `osm_coordinate_derived_rows=12,543`.
- `/predict` now supports manual `model_candidate` selection for the three trained artifacts: `random_forest`, `hist_gradient_boosting`, and `ridge`. Runtime smoke returned HTTP 200 for all three; unknown candidates return HTTP 422 with `available_candidates`.
- Valuation UI renders `Авто` plus `Ridge-регрессия`, `случайный лес`, and `градиентный бустинг`, and sends `model_candidate` only when the user chooses a manual model.
- Workstation HTML auto-refreshes in API mode by polling `/monitoring/status` every 60 seconds and reloading only when the monitoring signature changes.
- GitHub Actions pytest now enforces `--cov-fail-under=50`; fresh local coverage proof with that threshold reported total coverage `80.35%`.
- Terminal lifecycle source-verification candidate workflow now exists as a read-only CLI: `python -m realtyscope.analysis.lifecycle_verification --limit 5 --json`. It found real candidates from observation gaps, but simple Domclick HTTP probing is not enough to confirm terminal status (`HEAD=204`, browser-like `GET=401`), so DB terminal writes still require a Chrome/CDP or authenticated verifier with provenance.
- Static audit against API `127.0.0.1:8016` printed `api 17046 {'cian': 2436, 'domclick': 14610}`.
- CDP Grade-5 audit against API `127.0.0.1:8016` passed all page gates, real map interactions, selected-model valuation, monitoring model rendering, district OSM-backed cluster checks, and seven screenshot layout gates.
- Fresh verification: full pytest exited `0` with only the known Starlette/httpx warning; `ruff`, `compileall`, and `git diff --check` exited `0`.
- Remaining truth caveats: no XGBoost claim; terminal confirmed sale/removal rows remain `0`; lifecycle forecast remains `observation_gap_inferred_lifecycle`.

## Current Docker Runtime After Retrain

This is the current evidence as of the latest Docker retrain/restart. It supersedes older same-day notes in this file that mention `hist_gradient_boosting`, `candidate_count=2`, or partial OSM coverage as current.

- Compose reports `api`, `streamlit`, `db`, and `redis` healthy, with `mlflow` up.
- Docker `/model/metadata`: `selected_candidate=random_forest`, `candidate_count=3`, `model_selection_mode=best_metric`, `rows_total=17,046`, `train_rows=13,636`, `test_rows=3,410`, `r2=0.8653013476373554`, `mae=7,638,132.733793359`, `rmse=17,470,229.328815047`, and non-empty `feature_importance`.
- Candidate comparison from the same grouped split: `random_forest` (`r2=0.8653013476373554`, `mae=7,638,132.733793359`), `hist_gradient_boosting` (`r2=0.8483193165484304`, `mae=7,682,017.89735461`), and `ridge` (`r2=0.5885808364114331`, `mae=16,992,756.563055124`).
- Docker `/stats/data-quality`: `17,046` listings, `source_counts={'cian': 2436, 'domclick': 14610}`, `44,765` observations, `22` observation dates, `lifecycle_target_rows=0`, `inferred_lifecycle_target_rows=4,962`, `osm_features_total=17,046`, `osm_featured_listings=17,046`, `osm_coverage_pct=100.0`, `osm_local_extract_rows=4,487`, `osm_live_rows=16`, `osm_coordinate_derived_rows=12,543`.
- Docker `/stats/exposure-forecast`: `status=ready`, `can_forecast=true`, `target_source=observation_gap_inferred_lifecycle`, `inferred_lifecycle_target_rows=4,962`, `terminal_lifecycle_target_rows=0`.
- Caveats: no XGBoost result is claimed; terminal confirmed sale/removal lifecycle rows remain `0`; OSM coverage provenance is local extract + live Overpass + exact-coordinate derivation.

## Latest Docker OSM And District Runtime Addendum

- Docker API/Streamlit were rebuilt after the OSM provenance and district OSM feature fixes. Compose reports `api` and `streamlit` healthy.
- Docker `/stats/data-quality`: `osm_features_total=17,046`, `osm_featured_listings=17,046`, `osm_coverage_pct=100.0`, `osm_local_extract_rows=4,487`, `osm_live_rows=16`, `osm_coordinate_derived_rows=12,543`, `osm_infrastructure_coverage_source=local_extract+live_overpass+coordinate_exact_match`.
- Docker CDP from that OSM slice verified `cluster_feature_source=districtComparison+boundary+osm`, `segments.clusterUsesOsm=true`, `osm_rows=17,046`, `osm_local_extract_rows=4,487`, `monitoring.rendersOsmLocalExtractRows=true`, real map checks, all page gates, and all seven screenshots with `clippedCount=0` / `overlapCount=0`. The selected-model label from that CDP run is historical after the latest retrain; current `/model/metadata` selects `random_forest`.
- Docker static audit printed `api 17046 {'cian': 2436, 'domclick': 14610}`.
- Verification after the district OSM-backed fix: `67 passed` for targeted tests, targeted `ruff`, targeted `py_compile`, and `node --check output\playwright\cdp_static_grade5_audit.mjs`.
- Remaining caveats: no XGBoost result is claimed; terminal confirmed sale/removal lifecycle rows remain `0`.

## Latest OSM Provenance Addendum

This addendum supersedes the older `448 / 17,046` OSM caveat for current code and database evidence.

- Current code against the real PostgreSQL database reports `osm_features_total=17,046`, `osm_featured_listings=17,046`, `osm_coverage_pct=100.0`.
- Provenance: `osm_local_extract_rows=4,487`, `osm_live_rows=16`, `osm_coordinate_derived_rows=12,543`, `osm_infrastructure_coverage_source=local_extract+live_overpass+coordinate_exact_match`.
- The bulk source is a real local BBBike Moscow OpenStreetMap GeoJSON extract: `data/cache/osm/Moscow.osm.geojson.xz`.
- Exact-coordinate derivation is still marked honestly with `source_summary.derivation=coordinate_exact_match`; do not describe all 17,046 rows as independent live Overpass fetches.
- API/Streamlit code was updated so `/stats/data-quality` exposes `osm_local_extract_rows` and Streamlit payload exposes `localExtractRows`.
- Verification passed: `python -m pytest -p no:cacheprovider tests/test_osm_enrichment.py tests/test_api_data_routes.py tests/test_streamlit_ui_payload.py -q` (`64 passed`), targeted `ruff`, and targeted `py_compile`.
- Code-new local runtime proof passed on API `127.0.0.1:8014` and Streamlit `127.0.0.1:8512`: static audit printed `api 17046 {'cian': 2436, 'domclick': 14610}`; CDP verified `osm_rows=17046`, `osm_local_extract_rows=4487`, `osm_coordinate_derived_rows=12543`, `osm_coverage_source=local_extract+live_overpass+coordinate_exact_match`, `monitoring.rendersOsmLocalExtractRows=true`, all page gates, and all seven screenshots with `clippedCount=0` / `overlapCount=0`.
- Runtime caveat: Docker API `127.0.0.1:8000` still served the old provenance string during this update because WSL failed with `Wsl/Service/0x8007274c` before rebuilding `api`/`streamlit`. Rebuild Docker and rerun static/CDP audits before treating Docker `8000/8501` as final runtime proof for this specific change.

## Historical Runtime Addendum

Historical note: this block is superseded by "Current Docker Runtime After Retrain" above. It is kept as provenance for an earlier same-day artifact that selected `hist_gradient_boosting` and still had partial OSM coverage.

- Rebuild/restart command: `docker compose -p realtyscope up -d --build api streamlit` via WSL from this worktree.
- Compose status: `api` and `streamlit` healthy, `db` and `redis` healthy, `mlflow` up.
- `/model/metadata`: `selected_candidate=hist_gradient_boosting`, `candidate_count=3`, `rows_total=17,046`, `train_rows=13,636`, `test_rows=3,410`, `r2=0.8994355561733502`, `mae=6,188,596.253660057`, `rmse=15,095,211.71856097`.
- Candidate comparison from the same grouped split: `random_forest r2=0.8505952988269576, mae=7,989,464.3271694975`; `ridge r2=0.556166053792913, mae=16,651,213.37086019`.
- `/stats/data-quality`: `17,046` listings, `source_counts={'cian': 2436, 'domclick': 14610}`, `44,765` observations, `22` observation dates, `lifecycle_target_rows=0`, `inferred_lifecycle_target_rows=4,962`, `osm_features_total=448`, `osm_featured_listings=448`, `osm_coverage_pct=2.63`, `osm_live_rows=16`, `osm_coordinate_derived_rows=432`.
- `/stats/exposure-forecast`: `target_source=observation_gap_inferred_lifecycle`, `inferred_lifecycle_target_rows=4,962`, `terminal_lifecycle_target_rows=0`.
- Static audit against Docker passed: `api 17046 {'cian': 2436, 'domclick': 14610}`.
- CDP Grade-5 audit against Docker passed: Monitoring renders `hist_gradient_boosting` as `градиентный бустинг`, map loaded `30/30` tiles and passed zoom/drag/popup checks, district coverage is `84.47`, cluster source is `districtComparison+boundary`, and all seven screenshots have `clippedCount=0` / `overlapCount=0`.
- Caveats: no XGBoost result is claimed, terminal sale/removal rows remain `0`, and district clustering is boundary-backed while OSM coverage remains partial at `448 / 17,046` (`2.63%`).

## Start Prompt

```text
/goal Continue RealtyScope Grade-5 backend/data completion from the saved mem0 checkpoint for project `python`.

Work in `E:\Магистр\2-курс\python\RealtyScope-stitch-hybrid-redesign-20260623` on branch `ui/stitch-hybrid-redesign-20260623`. Keep this as the retained Stitch hybrid UI branch. Reply in Vietnamese. Visible UI text must remain Russian only except brand `RealtyScope`. Do not stage, commit, or push unless explicitly asked. Do not use Browser MCP.

First resume mem0 project `python` with global context. Read:
- `docs/design/NEXT_SESSION_UI_CHECKPOINT.md`
- `docs/design/NEXT_GOAL_HANDOFF_2026-06-25.md`
- `docs/final-readiness/2026-06-24-grade5-gap-audit.md`
- `docs/project-status.md`
- `docs/data/osm-enrichment.md`
- `docs/superpowers/plans/2026-06-24-realtyscope-final-grade5-completion-plan.md`

Current verified state:
- Docker API/Streamlit `127.0.0.1:8000/8501` are freshly verified from the retained branch.
- `/model/metadata`: current Docker runtime now reports `selected_candidate=random_forest`, `model_selection_mode=best_metric`, `candidate_count=3`, `rows_total=17,046`, `train_rows=13,636`, `test_rows=3,410`, `r2=0.8653013476373554`, `mae=7,638,132.733793359`, `rmse=17,470,229.328815047`, and non-empty `feature_importance`.
- `/stats/exposure-forecast`: `status=ready`, `can_forecast=true`, `target_source=observation_gap_inferred_lifecycle`, `inferred_lifecycle_target_rows=4,962`, `terminal_lifecycle_target_rows=0`.
- Static audit with Docker API passed: `api 17046 {'cian': 2436, 'domclick': 14610}`.
- CDP Grade-5 audit with Docker API/Streamlit passed: real map tiles/zoom/drag/popup, selected-model valuation, data/deals/district/monitoring gates, all seven screenshots with `clippedCount=0` and `overlapCount=0`.
- District analytics are real boundary-backed with address fallback and now have persisted OSM feature coverage available for every current listing.
- OSM infrastructure is full persisted coverage with honest provenance: `osm_features_total=17,046`, `osm_featured_listings=17,046`, `osm_coverage_pct=100.0`, `osm_local_extract_rows=4,487`, `osm_live_rows=16`, `osm_coordinate_derived_rows=12,543`.
- OSM backend selector supports `--live-overpass --dry-run --json` with `selection_mode=live_overpass_missing_distinct_coordinates`; current missing distinct coordinate count is `4,487`.
- `--progress-log output/osm-enrichment/overpass-batches-20260625.jsonl` records dry-run/write/derive batch evidence. Latest logged live batch with `limit=10` inserted `4` real Overpass rows and hit `HTTP 429 Too Many Requests` for `6` rows; exact-coordinate derivation inserted `8` rows.
- GitNexus dirty mirror `realtyscope-stitch-hybrid-redesign-20260625-dirty-worktree` was current before the `--progress-log` OSM CLI change. Refresh/check freshness before using GitNexus for this file again.

Main remaining backend tasks:
1. Continue real OSM infrastructure coverage:
   - Prefer a real local OSM extract/cache if available.
   - Otherwise run controlled, resumable Overpass batches over missing distinct coordinates with small limits, delays, timeouts, logging, and `--derive-coordinate-matches` after each batch.
   - Never fabricate OSM coverage or district infrastructure features.
2. Make district clustering OSM-backed only if real OSM feature coverage reaches district comparison rows. Otherwise keep the UI caveat that clusters are boundary-backed, not full OSM-backed.
3. Keep terminal sale/removal exposure caveat: `terminal_lifecycle_target_rows=0`. The working exposure forecast is inferred disappearance from observations, not confirmed sale/removal.
4. After each backend/data slice, verify with targeted tests, static audit, and CDP if stable.

Suggested checks:
- `python -m pytest -p no:cacheprovider tests/test_osm_enrichment.py tests/test_streamlit_ui_payload.py -q`
- `python -m py_compile src\realtyscope\enrichment\osm.py tests\test_osm_enrichment.py services\streamlit\app.py tests\test_streamlit_ui_payload.py`
- `python -m ruff check src/realtyscope/enrichment/osm.py tests/test_osm_enrichment.py services/streamlit/app.py tests/test_streamlit_ui_payload.py`
- `$env:PYTHONPATH='src;.'; $env:API_BASE_URL='http://127.0.0.1:8000'; python output\playwright\generate_static_audit.py`
- `$env:API_BASE_URL='http://127.0.0.1:8000'; $env:STREAMLIT_URL='http://127.0.0.1:8501'; node output\playwright\cdp_static_grade5_audit.mjs`

Pause if no real OSM source/cache/batch can be verified, Overpass becomes rate-limited/unstable, Docker/CDP cannot run honestly, or any requirement would require fake data/results.
```

## Why The Goal Should Continue In A Fresh Session

- The previous goal ran for more than 14 hours and compacted context repeatedly.
- The remaining work is mostly verification, git hygiene, docs consistency, and any UI/CDP rerun needed after the latest retrain.
- OSM coverage is no longer low for the current listing table, but provenance must stay precise: local extract + live Overpass + exact-coordinate derivation.
- Full OSM coverage should not be described as all-live Overpass coverage.

## Current Truth Caveats

- Terminal confirmed sale/removal exposure is still unavailable: `terminal_lifecycle_target_rows=0`.
- District comparison/clustering are boundary-backed plus address fallback, with full persisted OSM feature coverage now available for the current listing table.
- OSM infrastructure coverage is full persisted coverage: `17,046 / 17,046` listings (`100.0%`), sourced from local extract + live Overpass + exact-coordinate derivation.
- A long Overpass batch should be treated as data acquisition work with retries, delays, and verifiable checkpoints, not as a quick UI fix.
