# RealtyScope Demo Script

Date: 2026-06-03
Branch: `main` after the Phase 7 merge
Audience: course reviewer, project operator, and future demo sessions.

This script is the short defense path for showing RealtyScope without reloading the full project history. It assumes the repository is already cloned on the Windows workstation and that WSL2 Ubuntu has Docker available.

## Current UI Branch Note

For the retained 2026-06-24 Stitch hybrid UI branch, use workspace `E:\Магистр\2-курс\python\RealtyScope-stitch-hybrid-redesign-20260623` and branch `ui/stitch-hybrid-redesign-20260623`. The latest static/UI evidence is no longer the older `3,019`-row Phase 7 runtime snapshot: `python output\playwright\generate_static_audit.py` verifies the real live API payload with `17,046` listings (`14,610` Домклик, `2,436` ЦИАН), valuation comparable listings with real source links, real map coordinates/popups, restored data-table columns, robust real deal scoring, boundary-backed district analytics, and monitoring with bounded logs.

2026-06-25 latest runtime note: Docker `127.0.0.1:8000` and Streamlit `127.0.0.1:8501` are freshly verified from the retained Stitch hybrid branch. `/model/metadata` reports `selected_price_model_v1_non_leaky` with `selected_candidate=random_forest`, `model_selection_mode=best_metric`, `candidate_count=3`, `r2=0.8653013476373554`, `mae=7,638,132.733793359`, `rows_total=17,046`, and non-empty `feature_importance`. `/stats/data-quality` reports full persisted OSM feature coverage: `osm_features_total=17,046`, `osm_featured_listings=17,046`, `osm_coverage_pct=100.0`, with provenance `local_extract+live_overpass+coordinate_exact_match`. `/stats/exposure-forecast` reports `status=ready`, `can_forecast=true`, `target_source=observation_gap_inferred_lifecycle`, and `inferred_lifecycle_target_rows=4,962`; terminal sale/removal lifecycle remains unavailable with `terminal_lifecycle_target_rows=0`. `/stats/observation-trend` remains a separate analytic trend forecast with `can_forecast=true`, `forecast_method=linear_median_price_per_m2_v1`, `history_points=22`, and forecast dates `2026-06-25` through `2026-07-01`. Older lines below that call observed lower-bound exposure the primary forecast, name `hist_gradient_boosting`, or describe partial OSM coverage are historical.

Monitoring note for this branch: the static snapshot UI now includes `Статус контуров`. In local snapshot mode it explicitly marks PostgreSQL and Redis as `НЕ ПРОВЕРЕНО`; prove live DB/cache only with the Docker/API/Redis checks below.

Latest live runtime smoke for this branch on `2026-06-24`: after building and starting Redis, MLflow, API, and Streamlit from this workspace, Compose showed `db`, `redis`, `api`, and `streamlit` healthy and `mlflow` up. Runtime `/monitoring/status` reported `16,512` listings, `42,765` observations, `21` observation dates, `1,300` listing IDs with price changes, `lifecycle_target_rows=0`, and service rows `api/database/cache/model/ingestion=ok`. `/predict` returned `27,115,216.38` RUB for the full 23-feature demo vector with `baseline_ridge_v2_non_leaky`, `rows_total=8,366`, and `r2=0.6231827045433119`. MLflow registry showed `realtyscope-price-model` version `4` status `READY`. Redis scan observed a filtered `/data` cache key, but it expires quickly on the short TTL path; call the filtered `/data` URL immediately before scanning.

Runtime caveat: after the long cold Docker build, a few new WSL launch attempts returned `Wsl/Service/0x8007274c` while already-running containers and localhost endpoints still responded. Before a live defense, re-run a short `docker compose ps` and endpoint smoke rather than assuming the WSL shell remains stable.

District note for this branch: `Сегменты и районы` now uses real Moscow district boundary polygons from `GIS-Lab/OpenStreetMap` plus address fallback, and the current persisted OSM feature table covers all `17,046` listings. Present it as real boundary-backed district analytics with OSM feature coverage, while keeping provenance precise: local BBBike extract rows, earlier live Overpass rows, and exact-coordinate-derived rows.

Keep the caveat explicit during a defense: OSM feature coverage is full persisted coverage for the current listing table, not a claim that every row was independently fetched from live Overpass. Exposure-duration forecast is not a confirmed sale/removal model: monitoring uses observation-gap inferred lifecycle evidence, but terminal lifecycle target rows remain `0`. If asked about observation days, use the current persisted API/DB direction from the latest evidence: `22` distinct observed dates from `2026-05-14` to `2026-06-24`, `44,765` observations, `7,766` listings observed on multiple dates, max `20` dates for one listing, and `1,415` listing IDs with price changes.

If the reviewer asks whether repeated observations exist in PostgreSQL, use the latest DB evidence rather than guessing: `listing_observations` has `42,765` persisted observations across `21` dates, `7,456` source listing IDs with multiple observed dates, max `19` dates per listing, and `1,300` listing IDs with price changes. The reason exposure forecast is still absent is not lack of repeated observations; it is that every persisted observation is still `status=observed` and `active=true`, so there are `0` terminal lifecycle target rows.

Trend readiness is also partial, not missing. The monitoring page now shows `Готовность тренда`: latest API/static evidence has `44,765` persisted observations across `22` dates, `7,766` listings with observation history, and `1,415` listing IDs with price changes. Present this as descriptive trend evidence only. Do not call it a forecast because `can_forecast=false` and no verified time-series model is promoted.

The dashboard trend chart is now backed by `/stats/observation-trend`, not by the 1,000-row listing preview. Latest static/CDP evidence has `observationTrendSeries=22`, first date `2026-05-14`, last date `2026-06-24`, with daily median `price_per_m2` values from persisted `listing_observations`. Say "descriptive trend series"; do not say "forecast".

Selected model / exposure update for the retained branch: Docker API evidence on `127.0.0.1:8000` now selects `selected_price_model_v1_non_leaky` with `random_forest`, `candidate_count=3`, validation `r2=0.8653013476373554`, `mae=7,638,132.733793359`, and `17,046` training rows. Exposure now has a real inferred lifecycle forecast from repeated observation gaps: `inferred_lifecycle_target_rows=4,962`, median inferred exposure `6` days, max `19` days, and `target_source=observation_gap_inferred_lifecycle`; keep saying terminal sale/removal lifecycle remains `0`, so this is not a confirmed sale/removal exposure model.

## 0. What To Say Up Front

RealtyScope is a grade-5-oriented data-service project for Moscow apartment price analysis. The current system demonstrates:

- bounded Domclick data collection and PostgreSQL persistence;
- data-quality and observation history evidence;
- FastAPI data, prediction, model metadata, and monitoring endpoints;
- Redis-backed `/data` and `/listings` read caching;
- a Streamlit dashboard with tabs, filters, paginated listing preview, reviewer charts, a coordinate map, baseline prediction, monitoring, and model insights;
- Docker Compose runtime with PostgreSQL, Redis, MLflow, FastAPI, and Streamlit;
- MLflow evidence for the non-leaky Ridge baseline model.

Important caveat: the model is an honest non-leaky baseline appraisal model, not a final production estimator. Forecast-vs-actual and trend claims should stay conservative until repeated observation freshness is validated further.

## 1. Start The Runtime

Run from PowerShell. Use WSL2 because Docker is not available in this workstation's PowerShell PATH.

```powershell
wsl -d Ubuntu -- bash -lc "cd /mnt/e/Магистр/2-курс/python/RealtyScope-stitch-hybrid-redesign-20260623 && docker compose -p realtyscope up --build -d"
```

Check service state:

```powershell
wsl -d Ubuntu -- bash -lc "cd /mnt/e/Магистр/2-курс/python/RealtyScope-stitch-hybrid-redesign-20260623 && docker compose -p realtyscope ps"
```

Expected demo evidence:

- `db`, `redis`, `api`, and `streamlit` are healthy;
- `mlflow` is up on port `5000`;
- ports `8000`, `8501`, and `5000` are published locally.

## 2. Show FastAPI And Swagger

Open these in the browser:

- FastAPI health: http://localhost:8000/health
- FastAPI Swagger/OpenAPI: http://localhost:8000/docs

Quick terminal smoke checks:

```powershell
wsl -d Ubuntu -- bash -lc "curl -sS http://localhost:8000/health | python3 -m json.tool"
wsl -d Ubuntu -- bash -lc "curl -sS 'http://localhost:8000/data?limit=3&offset=0' | python3 -m json.tool"
wsl -d Ubuntu -- bash -lc "curl -sS 'http://localhost:8000/data?limit=3&offset=0&rooms=2&min_price_rub=10000000' | python3 -m json.tool"
wsl -d Ubuntu -- bash -lc "curl -sS http://localhost:8000/model/metadata | python3 -m json.tool"
wsl -d Ubuntu -- bash -lc "curl -sS http://localhost:8000/monitoring/status | python3 -m json.tool"
```

What to point out:

- `/data` is assignment-compatible and backed by persisted PostgreSQL rows;
- filters cover price range, area range, rooms, source, and address/city search;
- `/model/metadata` reports `realtyscope-price-model`, model version `baseline_ridge_v2_non_leaky`, feature version `ml_features_v2_non_leaky`, 23 features, and validation metrics;
- `/monitoring/status` shows data-quality counts, latest ingestion run status, model status, recent errors, and service rows for API/PostgreSQL/Redis/model/ingestion.

## 3. Prove Redis Cache Behavior

Populate a small filtered cached read so the demo proves filter-specific cache keys, not only the unfiltered path:

```powershell
wsl -d Ubuntu -- bash -lc "curl -sS -o /dev/null -w '%{http_code}' 'http://localhost:8000/data?limit=3&offset=0&rooms=2&min_price_rub=10000000'"
```

Inspect cache keys without dumping payload contents:

```powershell
wsl -d Ubuntu -- bash -lc "cd /mnt/e/Магистр/2-курс/python/RealtyScope-stitch-hybrid-redesign-20260623 && docker compose -p realtyscope exec -T redis redis-cli --scan --pattern 'realtyscope:*' | sort | head -20"
wsl -d Ubuntu -- bash -lc "cd /mnt/e/Магистр/2-курс/python/RealtyScope-stitch-hybrid-redesign-20260623 && docker compose -p realtyscope exec -T redis redis-cli EXISTS 'realtyscope:listings:v2:limit=1:offset=0:min_price_rub=10000000:rooms=2'"
wsl -d Ubuntu -- bash -lc "cd /mnt/e/Магистр/2-курс/python/RealtyScope-stitch-hybrid-redesign-20260623 && docker compose -p realtyscope exec -T redis redis-cli TTL 'realtyscope:listings:v2:limit=1:offset=0:min_price_rub=10000000:rooms=2'"
wsl -d Ubuntu -- bash -lc "cd /mnt/e/Магистр/2-курс/python/RealtyScope-stitch-hybrid-redesign-20260623 && docker compose -p realtyscope exec -T redis redis-cli STRLEN 'realtyscope:listings:v2:limit=1:offset=0:min_price_rub=10000000:rooms=2'"
```

Expected evidence:

- HTTP status is `200`;
- `EXISTS` returns `1`;
- `TTL` returns a short positive value up to `60` seconds;
- `STRLEN` is greater than `0`.

If `TTL` returns `-2`, the short-lived key expired. Call the same filtered `/data` URL again and repeat the Redis checks.

## 4. Show Streamlit Dashboard

Open:

- Streamlit: http://localhost:8501

Demo path:

1. In `Overview`, show KPI cards: listings, ML-ready rows, rejected rows, and ingestion runs.
2. In `Data Explorer`, use sidebar filters:
   - set `Rows` to `100` or `500`;
   - set `Page` to `1` or `2`;
   - set `Min price (RUB)` to `10000000`;
   - set `Rooms` to `2`;
   - optionally search a city/address fragment.
3. Show `Listing preview` updating from the filtered API query and the row-window caption.
4. In `Visuals`, show reviewer charts:
   - `Price distribution`;
   - `Median price by rooms`;
   - `Listing map`.
5. Point out visible OpenStreetMap attribution under the map. The map uses persisted listing coordinates and makes no live OSM/Overpass calls.
6. In `Prediction`, keep default values or adjust area/rooms/floor, then press `Run baseline prediction`.
7. Show the predicted price, model version, feature version, caveat, and metrics summary.
8. In `Monitoring & Model`, show the monitoring section, including the `Last successful collection` timestamp/source/record count and service-contour status.
9. Show `Model insights` with feature importance.

## 5. Show MLflow Evidence

Open:

- MLflow: http://localhost:5000

What to point out:

- registered model: `realtyscope-price-model`;
- verified model version: `3`;
- run ID: `4999892d2d92402ab78e1209203c338e`;
- model URI: `runs:/4999892d2d92402ab78e1209203c338e/model`;
- artifact path: `data/processed/models/phase5/baseline_ridge_v2_non_leaky.joblib`.

Optional REST checks:

```powershell
wsl -d Ubuntu -- bash -lc "python3 -c \"import json, urllib.request; run_id='4999892d2d92402ab78e1209203c338e'; data=json.load(urllib.request.urlopen(f'http://localhost:5000/api/2.0/mlflow/runs/get?run_id={run_id}')); print(data['run']['info']['status'])\""
wsl -d Ubuntu -- bash -lc "python3 -c \"import json, urllib.parse, urllib.request; name=urllib.parse.quote('realtyscope-price-model'); data=json.load(urllib.request.urlopen(f'http://localhost:5000/api/2.0/mlflow/registered-models/get?name={name}')); print([(v['version'], v['run_id']) for v in data['registered_model'].get('latest_versions', [])])\""
```

## 6. Optional Trainer Reproduction

Only run this if the reviewer asks to reproduce MLflow training evidence. It may take longer than the dashboard/API demo.

```powershell
wsl -d Ubuntu -- bash -lc "cd /mnt/e/Магистр/2-курс/python/RealtyScope-stitch-hybrid-redesign-20260623 && docker compose -p realtyscope --profile tools run --build --rm trainer"
```

After it finishes, refresh MLflow and `/model/metadata`.

Optional selected-model training path for the retained Stitch branch:

```powershell
wsl -d Ubuntu -- bash -lc "cd /mnt/e/Магистр/2-курс/python/RealtyScope-stitch-hybrid-redesign-20260623 && PYTHONPATH=src python -m realtyscope.ml.train --feature-version ml_features_v2_non_leaky --trainer selected --output-dir data/processed/models/phase5 --mlflow-tracking-uri http://localhost:5000 --mlflow-registered-model-name realtyscope-price-model --json"
```

Use this only when you will verify the resulting artifact and rebuild/restart API/Streamlit. Until that is done, live `/model/metadata` still represents the currently promoted `baseline_ridge_v2_non_leaky` model.

## 7. Clean Stop Without Data Loss

For routine demos, stop services without deleting named volumes:

```powershell
wsl -d Ubuntu -- bash -lc "cd /mnt/e/Магистр/2-курс/python/RealtyScope-stitch-hybrid-redesign-20260623 && docker compose -p realtyscope stop"
```

Or remove containers and the Compose network while keeping named volumes:

```powershell
wsl -d Ubuntu -- bash -lc "cd /mnt/e/Магистр/2-курс/python/RealtyScope-stitch-hybrid-redesign-20260623 && docker compose -p realtyscope down"
```

Do not run these destructive cleanup commands during course-readiness work unless the goal is an intentional full reset and the data/model artifacts have been exported or are no longer needed:

```powershell
# Destructive: removes PostgreSQL, Redis, MLflow, and model artifact volumes for this Compose project.
wsl -d Ubuntu -- bash -lc "cd /mnt/e/Магистр/2-курс/python/RealtyScope-stitch-hybrid-redesign-20260623 && docker compose -p realtyscope down -v"

# Destructive and broader: can remove unrelated Docker volumes from other projects.
wsl -d Ubuntu -- bash -lc "docker system prune --volumes"
```

## 8. Final Verification Commands

Use these before making a final readiness claim:

```powershell
git diff --check
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m ruff format --check .
.\.venv\Scripts\python.exe -m pytest -p no:cacheprovider
wsl -d Ubuntu -- bash -lc "cd /mnt/e/Магистр/2-курс/python/RealtyScope-stitch-hybrid-redesign-20260623 && docker compose -p realtyscope ps"
wsl -d Ubuntu -- bash -lc "curl -sS -o /dev/null -w '%{http_code}' http://localhost:8000/health"
wsl -d Ubuntu -- bash -lc "curl -sS -o /dev/null -w '%{http_code}' http://localhost:8501"
```

Then wait for GitHub Actions `ci` on the active branch, and after final merge, on `main`.

## 9. Current UI Branch Caveat

On 2026-06-24 the Stitch hybrid branch restored backend source metadata and real source mix stats in code. Verification through a temporary local API on `127.0.0.1:8010` against the real database showed:

- `/data` rows include source name, source label, source listing id, source URL, and observed timestamp.
- `/stats/data-quality` includes `source_counts`: `cian=2,436`, `domclick=14,076`.
- Static/CDP audit generated from that API reported `api 16512 {'cian': 2436, 'domclick': 14076}` and ended with `remaining_audit_chrome=0`.

The already-running Docker API on `127.0.0.1:8000` was still the older image in that same session: health/model endpoints responded, but `/data` did not yet include source fields. Before a final live demo from Docker ports `8000/8501`, rebuild/restart the API and Streamlit containers from this branch once Docker/WSL is available.

### Update After Docker Rebuild

WSL later recovered and Docker `api` / `streamlit` were rebuilt from this branch. Current Docker-port evidence:

- `/data?limit=1` includes source metadata and a real listing URL.
- `/stats/data-quality` includes `source_counts`: `cian=2,436`, `domclick=14,076`.
- `/model/metadata` reports `baseline_ridge_v2_non_leaky`, `23` features, ready status.
- `/monitoring/status` reports environment `docker` and service rows for API, PostgreSQL, Redis, model, and ingestion.
- `/predict` returns `27,115,216.38317985` RUB for the full 23-feature demo vector and includes the baseline caveat.
- Streamlit health returns `200 ok`.
- Static/CDP audit from Docker `8000` reports `api 16512 {'cian': 2436, 'domclick': 14076}` and `remaining_audit_chrome=0`.

WSL still intermittently returns `Wsl/Service/0x8007274c`. If WSL fails during a live check, verify already-published localhost endpoints first, then retry WSL/Compose after the transport recovers.

## 10. Screenshot Evidence

The current CDP audit writes a reviewer screenshot set under `output/playwright/`:

- `realtyscope-static-grade5-dashboard.png`
- `realtyscope-static-grade5-valuation.png`
- `realtyscope-static-grade5-map.png`
- `realtyscope-static-grade5-deals.png`
- `realtyscope-static-grade5-segments.png`
- `realtyscope-static-grade5-data.png`
- `realtyscope-static-grade5-monitoring.png`

The same audit fails if checked UI controls/card titles are clipped or if visible page cards overlap. Latest run: all seven pages reported `clippedCount=0` and `overlapCount=0`; the map loaded real tiles and verified zoom plus a real listing popup.
