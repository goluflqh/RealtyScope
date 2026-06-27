# RealtyScope

RealtyScope is a Grade-5 educational data-service project for Moscow apartment analytics and sale-price prediction. It combines real estate ingestion data, PostgreSQL storage, OSM-derived infrastructure features, FastAPI, Redis, MLflow-compatible model artifacts, Docker Compose, and a Streamlit dashboard.

Current validated release date: 2026-06-27.

## What the project does

- Collects and normalizes apartment listings from Domclick/CIAN-derived data.
- Stores listings, observations, data-quality evidence, logs, and OSM features in PostgreSQL.
- Serves operational and analytic APIs through FastAPI.
- Runs a Streamlit dashboard for market overview, data exploration, maps, deal candidates, districts, monitoring, and price valuation.
- Predicts apartment price from a full feature vector, not from a fixed demo default.

## Current verified runtime

The local Docker/PostgreSQL runtime used for the final model contains:

| Item | Value |
| --- | ---: |
| Listings | 17,287 |
| ML-ready listings | 17,287 |
| Listing observations | 45,764 |
| Observation days | 23 |
| Date range | 2026-05-14 to 2026-06-26 |
| OSM feature rows | 17,046 |
| Active model artifact | `selected_price_model_v1_non_leaky.joblib` |
| Selected candidate | `hist_gradient_boosting` |
| Target variable | `price_per_m2` |
| Runtime price output | predicted `price_per_m2 × user total_area_m2` |

## Architecture

```text
Raw listing data
    |
    v
Normalization / ingestion
    |
    v
PostgreSQL + SQLAlchemy + Alembic
    |
    +--> FastAPI
    |       +--> /health
    |       +--> /data, /listings
    |       +--> /predict
    |       +--> /model/metadata
    |       +--> /monitoring/status
    |
    +--> ML feature snapshot
    |       +--> non-leaky model artifacts
    |
    +--> Streamlit dashboard
            +--> overview, data, valuation, map, deals, districts, monitoring
```

## Price prediction model

The current model is trained on `ml_features_v2_non_leaky`. This feature version intentionally excludes direct price-observation leakage fields such as `latest_observation_price_rub` and `latest_observation_price_per_m2`.

Feature inputs include:

- apartment parameters: area, rooms, floor, floors total, building year;
- missing-value flags: floor/building/coordinates/OSM/transport flags;
- coordinates: latitude and longitude;
- OSM infrastructure: nearest transport distance, transport counts, schools, parks, shops, healthcare;
- observation metadata: observation count and availability flag;
- property type flag.

The model target is `price_per_m2`; the API and UI multiply the predicted per-square-meter value by the user-provided `total_area_m2`. Therefore `60 m²` is only an initial form value, not a fixed model assumption.

### Final model metrics

Final selected artifact:

```text
data/processed/models/phase5/selected_price_model_v1_non_leaky.joblib
```

Grouped random holdout metrics from the artifact:

| Metric | Value |
| --- | ---: |
| Rows | 17,287 |
| Train rows | 13,829 |
| Test rows | 3,458 |
| Candidate count | 3 |
| Selected candidate | `hist_gradient_boosting` |
| Validation R² | 0.9314 |
| Train R² | 0.9595 |
| R² generalization gap | 0.0281 |
| MAE | 4.81M RUB |
| RMSE | 14.94M RUB |
| MAPE | 11.04% |

Candidate comparison on the same grouped split:

| Candidate | R² | MAE | MAPE | Train R² | Gap |
| --- | ---: | ---: | ---: | ---: | ---: |
| HistGradientBoosting | 0.9314 | 4.81M | 11.04% | 0.9595 | 0.0281 |
| RandomForest | 0.8936 | 6.76M | 16.00% | 0.9372 | 0.0437 |
| Ridge | -0.9874 | 12.71M | 27.74% | 0.5157 | 1.5032 |

### Overfitting audit conclusion

The old HGB result around R² `0.9295` was not evidence of target leakage, because the non-leaky feature set has no direct price fields. However, a random listing split is optimistic for real estate because nearby properties and same-period listings are correlated.

The final regularized HGB model was therefore audited with stricter holdouts:

| Audit split | Test R² | MAE | MAPE | Interpretation |
| --- | ---: | ---: | ---: | --- |
| Random listing holdout | 0.9345 | 4.87M | 11.10% | Best headline validation, but optimistic |
| Spatial grid holdout | 0.8882 | 6.94M | 17.94% | Stronger test of neighborhood generalization |
| Latest-20% temporal holdout | 0.8503 | 7.04M | 12.83% | Stronger test of recency drift |

Conclusion for defense: the model is acceptable as a validated educational appraisal snapshot, but the honest quality claim is not only “R² 0.93”. The professional claim is: non-leaky HGB reaches R² `0.9314` on grouped random validation, while stress validation remains positive at about `0.85–0.89`; production-grade deployment would add temporal/spatial promotion gates before automatic retraining.

## Valuation UI behavior

The valuation page sends the same canonical feature vector to `/predict` that the model was trained on. The UI exposes editable controls for:

- area from 10 to 1200 m²;
- rooms from 0 to 20;
- floor and total floors;
- building year and known/missing flag;
- coordinates and known/missing flag;
- nearest transport distance;
- schools, parks, shops, and transport counts at 500 m / 1000 m.

When coordinates or OSM surroundings are unknown, the UI sets explicit missing flags instead of pretending default infrastructure values are known.

## Local development

Install dependencies:

```powershell
python -m pip install -e ".[dev,data,api,streamlit,ml]"
```

Run checks:

```powershell
python -m ruff check .
python -m pytest -p no:cacheprovider --basetemp=output/pytest-tmp
```

Train the selected model against a local PostgreSQL database:

```powershell
$env:PYTHONPATH = (Resolve-Path .\src).Path
python -m realtyscope.ml.train `
  --database-url postgresql+psycopg://realtyscope:realtyscope@localhost:5432/realtyscope `
  --output-dir data/processed/models/phase5 `
  --feature-version ml_features_v2_non_leaky `
  --trainer selected `
  --target-variable price_per_m2 `
  --json
```

Run API locally:

```powershell
$env:PYTHONPATH = (Resolve-Path .\src).Path
$env:DATABASE_URL = "postgresql+psycopg://realtyscope:realtyscope@localhost:5432/realtyscope"
python -m uvicorn services.api.app.main:app --host 127.0.0.1 --port 8000
```

Run Streamlit locally:

```powershell
$env:PYTHONPATH = (Resolve-Path .\src).Path
$env:API_BASE_URL = "http://127.0.0.1:8000"
streamlit run services/streamlit/app.py --server.port 8501
```

## Docker Compose

Docker is expected to run from WSL2/Linux:

```bash
docker compose -p realtyscope up -d --build
docker compose -p realtyscope ps
```

Service URLs:

- FastAPI: `http://localhost:8000`
- Streamlit: `http://localhost:8501`
- MLflow: `http://localhost:5000`

Smoke checks:

```bash
curl -fsS http://localhost:8000/health
curl -fsS http://localhost:8501/_stcore/health
curl -fsS http://localhost:8000/model/metadata | python -m json.tool
curl -fsS http://localhost:8000/monitoring/status | python -m json.tool
```

## VPS deployment

Production deployment uses:

- `docker-compose.prod.yml`;
- Caddy reverse proxy;
- `model_artifacts` Docker volume for trained artifacts;
- PostgreSQL volume restored from the local runtime bundle;
- tracked static assets such as `data/external/moscow_district_boundaries.geojson`.

Export local runtime artifacts:

```bash
bash scripts/deployment/export_local_runtime_bundle.sh ../realtyscope-vps-transfer
```

Restore on VPS:

```bash
cd /opt/realtyscope
bash scripts/deployment/restore_vps_runtime_bundle.sh
```

See [VPS deployment runbook](docs/deployment/vps-digitalocean-cloudflare.ru.md) for the full server procedure.

## Important honesty boundaries

- No XGBoost result is claimed; XGBoost is not part of the locked runtime.
- The price model is a validated snapshot, not an always-on automatic retraining system.
- Temporal and spatial validation are reported because random listing validation is optimistic.
- Exposure/lifecycle forecast remains inferred from observation gaps, not confirmed sale/removal events.
- PostgreSQL, Redis, and MLflow must not be exposed directly to the public internet.
