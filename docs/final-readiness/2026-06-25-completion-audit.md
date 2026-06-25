# RealtyScope Grade-5 Completion Audit

Date: 2026-06-25
Branch: `integration/realtyscope-grade5-final-20260625`
Runtime: code-new FastAPI `127.0.0.1:8016` for the latest integration slice; Docker API `127.0.0.1:8000` and Streamlit `127.0.0.1:8501` remain earlier verified runtime evidence.

This audit checks the active goal objective requirement-by-requirement against current runtime evidence. Historical notes that mention `hist_gradient_boosting`, `candidate_count=2`, or partial OSM coverage are superseded by the current Docker retrain evidence below.

## 2026-06-25 Integration Branch Local Runtime Addendum

This addendum is the latest verification for branch `integration/realtyscope-grade5-final-20260625`. It uses code-new FastAPI on `127.0.0.1:8016`; Docker `8000/8501` should be rebuilt and rechecked separately before using it as proof for this latest manual model-selection and UI auto-refresh slice.

- `/health` on `127.0.0.1:8016` returned `status=ok`, `environment=local`.
- `/monitoring/status` returned `17,046` listings, `source_counts={'cian': 2436, 'domclick': 14610}`, `44,765` observations, `22` observation dates, `lifecycle_target_rows=0`, `inferred_lifecycle_target_rows=4,962`, `osm_features_total=17,046`, `osm_featured_listings=17,046`, `osm_coverage_pct=100.0`, `osm_local_extract_rows=4,487`, `osm_live_rows=16`, `osm_coordinate_derived_rows=12,543`, and `osm_infrastructure_coverage_source=local_extract+live_overpass+coordinate_exact_match`.
- `/predict` supports manual `model_candidate` selection. Runtime smoke returned HTTP 200 for `random_forest`, `hist_gradient_boosting`, and `ridge`; auto mode selected `random_forest`.
- The valuation UI now has `Авто` plus exactly the three trained model choices and sends `model_candidate` only for a manual choice.
- The workstation HTML now includes API-mode auto-refresh: it polls `/monitoring/status` every 60 seconds, skips hidden tabs, and reloads only when the monitoring signature changes.
- GitHub Actions now runs pytest with `--cov-fail-under=50`; fresh local coverage proof with the same gate reported total coverage `80.35%`.
- Terminal lifecycle remains honest but no longer un-actionable: `python -m realtyscope.analysis.lifecycle_verification --limit 5 --json` exports source-verification candidates from real observation gaps. A read-only probe found candidate Domclick card `HEAD=204` and browser-like `GET=401`, so terminal rows still require a Chrome/CDP or authenticated source verifier before DB write.
- Static audit against `127.0.0.1:8016` printed `api 17046 {'cian': 2436, 'domclick': 14610}`.
- CDP Grade-5 audit against `127.0.0.1:8016` passed all page gates, including model valuation, map tiles/zoom/drag/popup, district clusters with `districtComparison+boundary+osm`, monitoring selected-candidate rendering (`случайный лес`), and all seven screenshots with `clippedCount=0` / `overlapCount=0`.

## 2026-06-25 Current Docker Runtime After Retrain

- Compose status: `api`, `streamlit`, `db`, and `redis` are healthy; `mlflow` is up.
- `/health`: `status=ok`, `environment=docker`; Streamlit `/_stcore/health`: `ok`.
- `/model/metadata`: `selected_candidate=random_forest`, `candidate_count=3`, `model_selection_mode=best_metric`, `rows_total=17,046`, `train_rows=13,636`, `test_rows=3,410`, `r2=0.8653013476373554`, `mae=7,638,132.733793359`, `rmse=17,470,229.328815047`, and non-empty `feature_importance`.
- Candidate comparison from the same grouped split: `random_forest` (`r2=0.8653013476373554`, `mae=7,638,132.733793359`), `hist_gradient_boosting` (`r2=0.8483193165484304`, `mae=7,682,017.89735461`), and `ridge` (`r2=0.5885808364114331`, `mae=16,992,756.563055124`).
- `/stats/data-quality`: `17,046` listings, `source_counts={'cian': 2436, 'domclick': 14610}`, `44,765` observations, `22` observation dates, `lifecycle_target_rows=0`, `inferred_lifecycle_target_rows=4,962`, `osm_features_total=17,046`, `osm_featured_listings=17,046`, `osm_coverage_pct=100.0`, `osm_local_extract_rows=4,487`, `osm_live_rows=16`, `osm_coordinate_derived_rows=12,543`, and `osm_infrastructure_coverage_source=local_extract+live_overpass+coordinate_exact_match`.
- `/stats/exposure-forecast`: `status=ready`, `can_forecast=true`, `target_source=observation_gap_inferred_lifecycle`, `inferred_lifecycle_target_rows=4,962`, `terminal_lifecycle_target_rows=0`; this remains an inferred disappearance-from-observations forecast, not confirmed sale/removal.

## 2026-06-25 Docker OSM And District OSM-Backed Addendum

The OSM provenance reopen note below has now been closed on Docker runtime.

- Docker API/Streamlit were rebuilt and restarted from the retained branch. Compose reports `api` and `streamlit` healthy.
- Docker `/stats/data-quality` reports `osm_features_total=17,046`, `osm_featured_listings=17,046`, `osm_coverage_pct=100.0`, `osm_local_extract_rows=4,487`, `osm_live_rows=16`, `osm_coordinate_derived_rows=12,543`, and `osm_infrastructure_coverage_source=local_extract+live_overpass+coordinate_exact_match`.
- Streamlit district analytics now preserve OSM feature columns into the district matrix. Docker CDP verifies `cluster_feature_source=districtComparison+boundary+osm` and `segments.clusterUsesOsm=true`.
- Docker static audit printed `api 17046 {'cian': 2436, 'domclick': 14610}`.
- Docker CDP passed all page gates, selected model rendering, OSM local/derived provenance gates, district OSM-backed cluster gate, and seven screenshot layout gates.
- Targeted verification after this fix: `67 passed`, targeted `ruff`, targeted `py_compile`, and `node --check` for the CDP script.

## 2026-06-25 OSM Provenance Reopen Note

Historical note: after the original audit, a real local BBBike Moscow OSM extract (`data/cache/osm/Moscow.osm.geojson.xz`) was used to reach full persisted OSM feature coverage in the real PostgreSQL database. The Docker addendum above is the current runtime proof.

Current code-plus-database evidence:

- `osm_features_total=17,046`
- `osm_featured_listings=17,046`
- `osm_coverage_pct=100.0`
- `osm_local_extract_rows=4,487`
- `osm_live_rows=16`
- `osm_coordinate_derived_rows=12,543`
- `osm_infrastructure_coverage_source=local_extract+live_overpass+coordinate_exact_match`

The API/Streamlit code now exposes this provenance through `osm_local_extract_rows` and `localExtractRows`. Verification passed for the targeted OSM/API/Streamlit suite (`64 passed`), targeted `ruff`, and targeted `py_compile`.

Code-new local runtime proof passed on API `127.0.0.1:8014` and Streamlit `127.0.0.1:8512`: static audit printed `api 17046 {'cian': 2436, 'domclick': 14610}`; CDP verified `osm_rows=17046`, `osm_local_extract_rows=4487`, `osm_coordinate_derived_rows=12543`, `osm_coverage_source=local_extract+live_overpass+coordinate_exact_match`, `monitoring.rendersOsmLocalExtractRows=true`, all page gates, and all seven screenshots with `clippedCount=0` / `overlapCount=0`.

Historical caveat, now superseded by the Docker addendum above: Docker API `127.0.0.1:8000` still served the old OSM source string during this note because WSL failed with `Wsl/Service/0x8007274c` before rebuilding API/Streamlit.

## Requirements And Evidence

| Requirement | Current evidence | Status |
| --- | --- | --- |
| Continue full Grade-5 backend/data/UI goal, not only OSM | Verification covers model selection, OSM, district/clustering, exposure/trend, Dashboard, valuation, heat map, deals, segments/district, Data, Monitoring, Docker runtime, docs, and mem0 checkpoint. | Satisfied |
| Use real data only; do not fabricate counts or metrics | Docker API reports `17,046` listings, `source_counts={'cian': 2436, 'domclick': 14610}`, `44,765` observations, and all audit payloads are `mode=api`. | Satisfied |
| Expanded model candidates beyond Ridge/RandomForest | Docker `/model/metadata` reports three real candidates: `hist_gradient_boosting`, `random_forest`, and `ridge`. XGBoost is not installed or claimed. | Satisfied |
| Manual model selection in valuation UI | Code-new API and UI now support `model_candidate`; runtime smoke selected all three trained candidates, and the valuation UI renders `Авто`, `Ridge-регрессия`, `случайный лес`, and `градиентный бустинг`. | Satisfied |
| UI auto-updates when backend monitoring totals change | Workstation HTML polls `/monitoring/status` in API mode and reloads when `listings_total`, `observations_total`, latest run id, or latest run finish time changes; regression test covers this behavior. | Satisfied |
| Tests coverage threshold | GitHub Actions pytest step includes `--cov-fail-under=50`; fresh local proof with the same command reached total coverage `80.35%`. | Satisfied |
| Retrain selected model on current full dataset | Docker `/model/metadata` reports `selected_candidate=random_forest`, `candidate_count=3`, `rows_total=17,046`, `train_rows=13,636`, `test_rows=3,410`, `r2=0.8653013476373554`, `mae=7,638,132.733793359`, `rmse=17,470,229.328815047`. | Satisfied |
| Prevent train/test leakage and avoid target leakage | Metadata shows grouped split counts (`train_listing_groups=13,636`, `test_listing_groups=3,410`), and runtime feature names have 23 features without `price` or a target column. Full pytest includes grouped split and non-leaky artifact tests. | Satisfied |
| Expose selected model through API and Monitoring UI | Docker `/model/metadata` exposes candidate metrics, selected candidate, feature importance, and grouped split counts. CDP verifies `selectedCandidate=random_forest`, `expectedSelectedCandidateLabel=случайный лес`, and `rendersSelectedCandidateName=true`. | Satisfied |
| OSM strategy is real, resumable, and honest | Docker data quality reports `osm_features_total=17,046`, `osm_featured_listings=17,046`, `osm_coverage_pct=100.0`, `osm_local_extract_rows=4,487`, `osm_live_rows=16`, `osm_coordinate_derived_rows=12,543`, and `osm_infrastructure_coverage_source=local_extract+live_overpass+coordinate_exact_match`. | Satisfied with provenance caveat |
| OSM local extract/cache search | A real local BBBike Moscow extract is now used at `data/cache/osm/Moscow.osm.geojson.xz`. Public Overpass remains rate-limited, so the current full coverage should be described as local extract + live Overpass + exact-coordinate derivation. | Satisfied |
| District comparison and clustering truthfulness | CDP verifies `district_coverage_pct=84.47`, `district_extraction_source=admin_boundary_geojson+address_text`, `district_rows=12`, `cluster_rows=12`, `cluster_count=3`, `cluster_feature_source=districtComparison+boundary`, and partial caveats render. | Satisfied |
| Do not claim OSM-backed clustering unless coverage is real | Current persisted OSM feature coverage is `17,046 / 17,046` (`100.0%`) with explicit provenance. Do not describe it as all-live Overpass coverage. | Satisfied |
| Exposure/forecast truthfulness | Docker `/stats/exposure-forecast` reports `target_source=observation_gap_inferred_lifecycle`, `inferred_lifecycle_target_rows=4,962`, `terminal_lifecycle_target_rows=0`, and a Russian caveat that this is not confirmed sale/removal. | Satisfied |
| Terminal lifecycle upgrade path | Added read-only candidate selector for source verification; it returns `needs_source_verification` rows with source URLs, gap days, and exposure days. Simple HTTP probing is insufficient for Domclick because GET returns `401`, so confirmed terminal writes remain gated on a browser/authenticated verifier. | Partially satisfied; write path remains future work |
| Dashboard/Data count consistency | Static audit and CDP both report `listings_total=17,046`, `data_count_source=api`, `source_counts={'cian': 2436, 'domclick': 14610}`. | Satisfied |
| Page-level backend-to-UI evidence | CDP verifies Dashboard feed/links, valuation comparables/model calculation, map tiles/zoom/drag/popup, deals scoring columns, segment/district panels, Data pagination/export columns, and Monitoring/source/model/log panels. | Satisfied |
| Russian-only visible UI except RealtyScope | CDP verifies Russian UI state and Monitoring renders the Russian model label `градиентный бустинг`; no internal traces are rendered. | Satisfied |
| Docker runtime proof | `docker compose -p realtyscope ps` shows API and Streamlit healthy, DB and Redis healthy, MLflow up. `/health` returns Docker `status=ok`; Streamlit health returns `ok`. | Satisfied |
| Documentation and mem0 checkpoint | Updated `docs/project-status.md`, `docs/design/NEXT_GOAL_HANDOFF_2026-06-25.md`, `docs/design/NEXT_SESSION_UI_CHECKPOINT.md`, `docs/final-readiness/2026-06-24-grade5-gap-audit.md`; saved mem0 checkpoint with exact Docker model metrics and remaining caveats. | Satisfied |

## Fresh Verification Commands

- `python -m pytest -p no:cacheprovider tests -q` exited `0`; output showed all test progress complete with one known Starlette/httpx deprecation warning and no failures.
- `python -m pytest -p no:cacheprovider tests/test_streamlit_ui_payload.py::test_workstation_html_auto_refreshes_when_api_monitoring_signature_changes -q` exited `0`.
- `python -m pytest -p no:cacheprovider --cov=realtyscope --cov=services --cov-report=term-missing --cov-fail-under=50` exited `0`, ran `218 passed`, and reported total coverage `80.35%`.
- `python -m pytest -p no:cacheprovider tests/test_ci_workflow_contract.py tests/test_lifecycle_verification.py -q` exited `0`.
- `python -m ruff check src services tests` exited `0` with `All checks passed!`.
- `python -m compileall -q src services tests` exited `0`.
- `git diff --check` exited `0`; it reported only Windows LF-to-CRLF warnings, with no whitespace errors.
- `curl.exe --noproxy "*" -s http://127.0.0.1:8000/health` returned `{"service":"realtyscope-api","status":"ok","project":"RealtyScope","environment":"docker"}`.
- `curl.exe --noproxy "*" -s http://127.0.0.1:8501/_stcore/health` returned `ok`.
- `PYTHONPATH=src;. API_BASE_URL=http://127.0.0.1:8000 python output\playwright\generate_static_audit.py` exited `0` and printed `api 17046 {'cian': 2436, 'domclick': 14610}`.
- `API_BASE_URL=http://127.0.0.1:8000 STREAMLIT_URL=http://127.0.0.1:8501 node output\playwright\cdp_static_grade5_audit.mjs` exited `0` and verified all page gates, `selectedCandidate=random_forest`, `expectedSelectedCandidateLabel=случайный лес`, `loadedTiles=17/30` with minimum `8`, `rendersSelectedCandidateName=true`, and seven screenshot pages with `clippedCount=0` / `overlapCount=0`.

## Remaining Caveats

- No XGBoost result is claimed because the dependency is not installed or locked.
- Terminal confirmed sale/removal labels remain unavailable: `terminal_lifecycle_target_rows=0`.
- OSM infrastructure coverage is full for the current persisted listing table, but the provenance must stay precise: local BBBike extract + prior live Overpass + exact-coordinate derivation, not all rows independently fetched from live Overpass.
- The worktree remains intentionally dirty and uncommitted; no files were staged, committed, pushed, or PR-created.
