# RealtyScope

RealtyScope is a course-ready real-estate data service for Moscow apartment analytics. It combines bounded Domclick/CIAN data ingestion, PostgreSQL persistence, FastAPI, Redis caching, MLflow-backed model artifacts, and a Streamlit dashboard for data exploration, valuation, monitoring, and model evidence.

The current release is merged into `main` through PR #3, `Final Grade-5 RealtyScope integration`.

## Current Status

Latest verified runtime evidence as of 2026-06-26:

- Docker API: `http://127.0.0.1:8000`
- Streamlit UI: `http://127.0.0.1:8501`
- MLflow: `http://127.0.0.1:5000`
- Listings: `17,287`
- Sources: `14,851` Domclick, `2,436` CIAN
- Observations: `45,764`
- Observation dates: `23`, from `2026-05-14` through `2026-06-26`
- OSM feature coverage: `17,046 / 17,287` listings (`98.61%`)
- Selected model: `selected_price_model_v1_non_leaky`, `random_forest`
- Model training rows: `17,046`
- Model freshness: validated snapshot; the model is not automatically retrained on every new daily ingest

Important caveat: the price model is a validated academic appraisal snapshot, not a production-grade estimator. Fresh data does not automatically imply a better model. Retraining should happen only through the model candidate and promotion workflow.

## Architecture

```text
Domclick / CIAN raw data
        |
        v
Ingestion and normalization
        |
        v
PostgreSQL + SQLAlchemy + Alembic
        |
        +--> FastAPI API
        |       +--> Redis cached reads
        |       +--> /data, /predict, /model/metadata, /monitoring/status
        |
        +--> ML feature snapshots
        |       +--> model training and MLflow evidence
        |
        +--> Streamlit dashboard
                +--> overview, data, valuation, map, trends, monitoring
```

Main services:

- `db`: PostgreSQL 16
- `redis`: read-path cache
- `mlflow`: experiment and registry evidence
- `api`: FastAPI backend
- `streamlit`: reviewer-facing dashboard
- `trainer`: optional model training container

## Repository Layout

```text
services/api/             FastAPI service
services/streamlit/       Streamlit dashboard and static audit HTML builder
services/trainer/         Docker trainer entrypoint
src/realtyscope/          Core package: ingestion, database, enrichment, ML, analysis
alembic/                  Database migrations
docs/                     Course, operations, demo, readiness, and design docs
scripts/                  Runtime and audit helper scripts
tests/                    API, ML, ingestion, UI-payload, Docker-contract tests
data/                     Local data folders, mostly ignored/generated
```

## API

Useful local endpoints after Docker Compose is running:

- `GET /health`: service health
- `GET /docs`: FastAPI Swagger UI
- `GET /data`: assignment-compatible listings table with filters and pagination
- `GET /listings`: cached listings read path
- `POST /predict`: price prediction from the promoted model artifact
- `GET /model/metadata`: model version, candidate metrics, feature importance, freshness
- `GET /stats/data-quality`: persisted data and observation statistics
- `GET /stats/observation-trend`: observation-based trend payload
- `GET /stats/exposure-forecast`: observation-gap inferred lifecycle forecast
- `GET /monitoring/status`: service, ingestion, model, data, and recent log status

Example:

```bash
curl -sS "http://localhost:8000/data?limit=3&offset=0&rooms=2" | python -m json.tool
curl -sS "http://localhost:8000/model/metadata" | python -m json.tool
curl -sS "http://localhost:8000/monitoring/status" | python -m json.tool
```

## Dashboard

The Streamlit dashboard exposes:

- overview KPIs
- data explorer filters and pagination
- listing preview and exportable table
- valuation form with model candidate selection
- comparable listings and model feature drivers
- map and district analytics
- observation trend readiness
- inferred exposure forecast readiness
- monitoring cards, service status, model freshness, and recent logs

Open it locally at:

```text
http://localhost:8501
```

## Data Pipeline

The Domclick daily batch is intentionally bounded and source-aware:

- Chrome/CDP capture writes raw payloads under `data/raw/domclick/YYYY-MM-DD-bulk`.
- Scheduled ingestion normalizes payloads and commits successful runs to PostgreSQL.
- Failures such as QRATOR/CAPTCHA/source blocking are recorded through `app_logs` for monitoring.
- The scheduler avoids aggressive retry loops; source blocking should be inspected before reruns.

Common commands:

```powershell
python -m realtyscope.ingestion.domclick_chrome_capture --output-root data/raw/domclick --capture-runtime cdp --json
python -m realtyscope.ingestion.domclick_scheduled_batch run --source-path data/raw/domclick/2026-06-26-bulk --commit --json
python -m realtyscope.ingestion.domclick_scheduled_batch status --json
```

On the Windows workstation, the scheduled task should point at:

```text
scripts/run_domclick_scheduled_batch.ps1
```

## Machine Learning

The current selected artifact is:

```text
data/processed/models/phase5/selected_price_model_v1_non_leaky.joblib
```

Current selected candidate:

- candidate: `random_forest`
- model version: `selected_price_model_v1_non_leaky`
- feature version: `ml_features_v2_non_leaky`
- training rows: `17,046`
- validation R2: `0.8653`
- MAE: about `7.64M` RUB
- candidate count: `3` (`random_forest`, `hist_gradient_boosting`, `ridge`)

Truth boundaries:

- No XGBoost result is claimed.
- The model is a validated snapshot, not an automatically retrained daily model.
- The current database has `17,287` listings, so the dashboard shows a model freshness delta.
- Confirmed terminal sale/removal lifecycle rows remain unavailable; exposure forecasting is inferred from observation gaps.

## Local Development

Install Python dependencies with `uv`:

```bash
python -m pip install uv==0.11.3
UV_LINK_MODE=copy uv sync --frozen --extra dev --extra data --extra api --extra streamlit
```

Run checks:

```bash
uv run ruff check .
uv run ruff format --check .
uv run pytest --cov=realtyscope --cov=services --cov-report=term-missing --cov-fail-under=50
```

On Windows without `uv` in the current shell, the equivalent local commands used for release verification were:

```powershell
python -m ruff check .
python -m ruff format --check .
python -m pytest -p no:cacheprovider --cov=realtyscope --cov=services --cov-report=term-missing --cov-fail-under=50
```

## Docker Compose

Use WSL2 or a Linux host for Docker Compose. From the repository root:

```bash
docker compose -p realtyscope up --build -d
docker compose -p realtyscope ps
```

Expected services:

- `db` healthy
- `redis` healthy
- `api` healthy on port `8000`
- `streamlit` healthy on port `8501`
- `mlflow` up on port `5000`

Quick smoke:

```bash
curl -sS http://localhost:8000/health
curl -sS http://localhost:8501/_stcore/health
curl -sS http://localhost:8000/monitoring/status | python -m json.tool
```

For the static audit against a live Docker API, use a longer timeout when the database is cold:

```powershell
$env:API_BASE_URL="http://127.0.0.1:8000"
$env:STREAMLIT_API_TIMEOUT_SECONDS="30"
python scripts\playwright\generate_static_audit.py
Remove-Item Env:API_BASE_URL
Remove-Item Env:STREAMLIT_API_TIMEOUT_SECONDS
```

## Deployment Notes

The project is designed for a Linux VPS deployment with Docker Compose.

Recommended production steps:

1. Provision a VPS with Docker, Docker Compose, and a firewall.
2. Create DNS records for the domain and optional API subdomain.
3. Copy the repository to the server or deploy from GitHub.
4. Create a production `.env` from `.env.example`.
5. Use persistent Docker volumes for PostgreSQL, Redis, MLflow, and model/data artifacts.
6. Start services with `docker compose -p realtyscope up --build -d`.
7. Put Caddy, Nginx, or Traefik in front of Streamlit/API for HTTPS.
8. Verify `/health`, `/_stcore/health`, `/monitoring/status`, and dashboard rendering.
9. Configure database backups before enabling scheduled ingestion.

Deployment caveats:

- Do not commit real secrets.
- Domclick collection can be blocked by QRATOR/CAPTCHA; treat source access as an operational dependency.
- The Windows Scheduled Task is not portable to VPS; use cron or a systemd timer on Linux.
- Run model retraining as an explicit promotion workflow, not as an automatic side effect of ingestion.

## Verification Evidence

Latest release verification after PR #3 merge:

- GitHub Actions CI: passing for PR and push.
- Local merged-main pytest: `241 passed`, coverage `80.84%`, fail-under `50%`.
- Local `ruff check .`: passed.
- Local `ruff format --check .`: passed.
- Docker/WSL runtime smoke: API, Streamlit, PostgreSQL, Redis healthy; MLflow up.
- Static audit with Docker API and `STREAMLIT_API_TIMEOUT_SECONDS=30`: `api 17287 {'cian': 2436, 'domclick': 14851}`.

See also:

- `docs/project-status.md`
- `docs/demo-script.md`
- `docs/demo-script.vi.md`
- `docs/final-readiness/2026-06-25-completion-audit.md`
- `docs/course-guidance/realtyscope-user-story-traceability.md`

## License And Data Notice

This is an academic project. Respect source-site terms, robots policies, rate limits, OpenStreetMap attribution requirements, and local data protection rules when collecting or deploying real estate data.
