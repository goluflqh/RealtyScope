# RealtyScope Demo Script

Date: 2026-06-03
Branch: `phase7-course-readiness-polish`
Audience: course reviewer, project operator, and future demo sessions.

This script is the short defense path for showing RealtyScope without reloading the full project history. It assumes the repository is already cloned on the Windows workstation and that WSL2 Ubuntu has Docker available.

## 0. What To Say Up Front

RealtyScope is a grade-5-oriented data-service project for Moscow apartment price analysis. The current system demonstrates:

- bounded Domclick data collection and PostgreSQL persistence;
- data-quality and observation history evidence;
- FastAPI data, prediction, model metadata, and monitoring endpoints;
- Redis-backed `/data` and `/listings` read caching;
- a Streamlit dashboard with filters, reviewer charts, a coordinate map, baseline prediction, monitoring, and model insights;
- Docker Compose runtime with PostgreSQL, Redis, MLflow, FastAPI, and Streamlit;
- MLflow evidence for the non-leaky Ridge baseline model.

Important caveat: the model is an honest non-leaky baseline appraisal model, not a final production estimator. Forecast-vs-actual and trend claims should stay conservative until repeated observation freshness is validated further.

## 1. Start The Runtime

Run from PowerShell. Use WSL2 because Docker is not available in this workstation's PowerShell PATH.

```powershell
wsl -d Ubuntu -- bash -lc "cd /mnt/e/Магистр/2-курс/python/RealtyScope && docker compose -p realtyscope up --build -d"
```

Check service state:

```powershell
wsl -d Ubuntu -- bash -lc "cd /mnt/e/Магистр/2-курс/python/RealtyScope && docker compose -p realtyscope ps"
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
- `/monitoring/status` shows data-quality counts, latest ingestion run status, model status, and recent errors.

## 3. Prove Redis Cache Behavior

Populate a small cached read:

```powershell
wsl -d Ubuntu -- bash -lc "curl -sS -o /dev/null -w '%{http_code}' 'http://localhost:8000/data?limit=3&offset=0'"
```

Inspect cache keys without dumping payload contents:

```powershell
wsl -d Ubuntu -- bash -lc "cd /mnt/e/Магистр/2-курс/python/RealtyScope && docker compose -p realtyscope exec -T redis redis-cli --scan --pattern 'realtyscope:*' | sort | head -20"
wsl -d Ubuntu -- bash -lc "cd /mnt/e/Магистр/2-курс/python/RealtyScope && docker compose -p realtyscope exec -T redis redis-cli EXISTS 'realtyscope:listings:v1:limit=3:offset=0'"
wsl -d Ubuntu -- bash -lc "cd /mnt/e/Магистр/2-курс/python/RealtyScope && docker compose -p realtyscope exec -T redis redis-cli TTL 'realtyscope:listings:v1:limit=3:offset=0'"
wsl -d Ubuntu -- bash -lc "cd /mnt/e/Магистр/2-курс/python/RealtyScope && docker compose -p realtyscope exec -T redis redis-cli STRLEN 'realtyscope:listings:v1:limit=3:offset=0'"
```

Expected evidence:

- HTTP status is `200`;
- `EXISTS` returns `1`;
- `TTL` returns a short positive value up to `60` seconds;
- `STRLEN` is greater than `0`.

If `TTL` returns `-2`, the short-lived key expired. Call `/data?limit=3&offset=0` again and repeat the Redis checks.

## 4. Show Streamlit Dashboard

Open:

- Streamlit: http://localhost:8501

Demo path:

1. Show KPI cards: listings, ML-ready rows, rejected rows, and ingestion runs.
2. Show the latest ingestion run table and monitoring section.
3. Use sidebar filters:
   - set `Rows` to `100` or `500`;
   - set `Min price (RUB)` to `10000000`;
   - set `Rooms` to `2`;
   - optionally search a city/address fragment.
4. Show `Listing preview` updating from the filtered API query.
5. Show `Reviewer visuals`:
   - `Price distribution`;
   - `Median price by rooms`;
   - `Listing map`.
6. Point out visible OpenStreetMap attribution under the map. The map uses persisted listing coordinates and makes no live OSM/Overpass calls.
7. In `Baseline prediction`, keep default values or adjust area/rooms/floor, then press `Run baseline prediction`.
8. Show the predicted price, model version, feature version, caveat, and metrics summary.
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
wsl -d Ubuntu -- bash -lc "cd /mnt/e/Магистр/2-курс/python/RealtyScope && docker compose -p realtyscope --profile tools run --build --rm trainer"
```

After it finishes, refresh MLflow and `/model/metadata`.

## 7. Clean Stop Without Data Loss

For routine demos, stop services without deleting named volumes:

```powershell
wsl -d Ubuntu -- bash -lc "cd /mnt/e/Магистр/2-курс/python/RealtyScope && docker compose -p realtyscope stop"
```

Or remove containers and the Compose network while keeping named volumes:

```powershell
wsl -d Ubuntu -- bash -lc "cd /mnt/e/Магистр/2-курс/python/RealtyScope && docker compose -p realtyscope down"
```

Do not run these destructive cleanup commands during course-readiness work unless the goal is an intentional full reset and the data/model artifacts have been exported or are no longer needed:

```powershell
# Destructive: removes PostgreSQL, Redis, MLflow, and model artifact volumes for this Compose project.
wsl -d Ubuntu -- bash -lc "cd /mnt/e/Магистр/2-курс/python/RealtyScope && docker compose -p realtyscope down -v"

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
wsl -d Ubuntu -- bash -lc "cd /mnt/e/Магистр/2-курс/python/RealtyScope && docker compose -p realtyscope ps"
wsl -d Ubuntu -- bash -lc "curl -sS -o /dev/null -w '%{http_code}' http://localhost:8000/health"
wsl -d Ubuntu -- bash -lc "curl -sS -o /dev/null -w '%{http_code}' http://localhost:8501"
```

Then wait for GitHub Actions `ci` on the active branch, and after final merge, on `main`.
