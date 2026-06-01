# RealtyScope User Story Traceability

Date: 2026-06-02
Source: `E:\Магистр\2-курс\python\Описание проекта.html`, User Stories section.
Audience: course reviewer, implementation agents, and future phase planning.

This document maps the assignment User Stories to the current RealtyScope implementation. It is intentionally conservative: a story is marked complete only when the repository contains working, tested behavior or a concrete operational path.

## Status Legend

- `Implemented`: working behavior exists and has direct repo evidence.
- `Partial`: part of the story works, but one or more acceptance criteria remain missing.
- `Planned`: documented in the project design/phase plan, but not implemented yet.
- `Current gap`: not yet covered by working code or a near-term implementation task.

## Traceability Matrix

| ID | Assignment User Story | RealtyScope Feature Mapping | Phase / Status | Evidence | Current Gap / Next Step |
| --- | --- | --- | --- | --- | --- |
| US-01 | As a user, I want to see current data for the selected object so I can understand the current situation. Acceptance: automatic daily update, last update time, KPI cards, selectable analysis object. | Domclick daily capture, scheduled batch ingestion, DB-backed `/listings` and `/stats/data-quality`, Streamlit KPI slice. | Phase 3.5-3.6 / `Partial` | `src/realtyscope/ingestion/domclick_chrome_capture.py`; `src/realtyscope/ingestion/domclick_scheduled_batch.py`; `services/api/app/main.py`; `services/streamlit/app.py`; `docs/operations/domclick-scheduled-batch-ingestion.md`. | API/Streamlit expose latest ingestion run counts, but the payload/UI do not yet show `started_at`/`finished_at` as a clear last update timestamp. Streamlit currently has row-limit selection, not full object selection by district/source/category. |
| US-02 | As a user, I want to see history and trends so I can understand change dynamics. Acceptance: time-series charts, period selection, seasonality/trend visualization, compare objects on one chart. | Phase 3.7 Observation / Price History Layer stores normalized observations for price/area/rooms/floor snapshots over time. | Phase 3.7 / `Partial: backend implemented` | `ListingObservation` in `src/realtyscope/database/models.py`; migration `alembic/versions/20260602_0002_listing_observations.py`; persistence behavior in `src/realtyscope/database/persistence.py`; tests in `tests/test_database_models.py`, `tests/test_database_persistence.py`, and `tests/test_alembic_config.py`; docs in `docs/data/listing-observations.md`. | Backend history storage is now covered. Trend API endpoints, period filters, seasonality analysis, and Streamlit comparison charts remain future dashboard work. |
| US-03 | As a user, I want to receive a prediction from an ML model so I can make decisions. Acceptance: prediction display, model quality metrics, forecast vs actual visualization, custom parameter input. | Moscow apartment sale-price regression, MLflow tracking, future `/predict`, Streamlit Predictions page. | Phase 4+ / `Planned` | `docs/superpowers/specs/2026-05-31-realtyscope-design.md` sections on ML, API, Streamlit; `pyproject.toml` optional `ml` dependencies; `services/mlflow/Dockerfile`. | No trained model, model registry, prediction API, or predictions UI yet. Future work must train a baseline, save artifacts, expose `/predict`, and show metrics. |
| US-04 | As a user, I want to filter and search data so I can find needed information. Acceptance: sidebar filters, raw data table with pagination, column sorting, text search. | DB-backed listing table via API and Streamlit listing preview. | Phase 3.5 / `Partial` | `GET /listings` supports `limit` and `offset` in `services/api/app/main.py`; Streamlit shows a listing dataframe in `services/streamlit/app.py`; tests in `tests/test_api_data_routes.py` and `tests/test_streamlit_api_client.py`. | There are no API filters for price/area/rooms/source/text yet, and Streamlit has only row-limit selection. Add filter/query parameters and UI controls in a future Data Explorer phase. |
| US-05 | As a developer, I want to use a REST API so I can integrate data into my applications. Acceptance: Swagger/OpenAPI, `/health`, `/data`, `/predict`, Pydantic validation, correct HTTP status codes. | FastAPI service with health, listing data, and data-quality stats. | Phase 3.5 / `Partial` | `services/api/app/main.py`; `tests/test_api_health.py`; `tests/test_api_data_routes.py`; README API URLs. FastAPI provides Swagger/OpenAPI automatically at `/docs`. | Current routes are `/health`, `/listings`, and `/stats/data-quality`; assignment-compatible `/data` and `/predict` are not implemented. Prediction schemas and validation belong to the ML/API phase. |
| US-06 | As an administrator, I want to monitor system status so I can know about problems. Acceptance: source status page, latest ingestion logs, working/not-working indicator, last successful collection time. | Ingestion run accounting, data-quality stats, Domclick status command, app log table foundation. | Phase 3.5-3.6 / `Partial` | `IngestionRun` and `AppLog` models in `src/realtyscope/database/models.py`; `GET /stats/data-quality` in `services/api/app/main.py`; `domclick_scheduled_batch status` in `src/realtyscope/ingestion/domclick_scheduled_batch.py`; operations docs. | No dedicated monitoring Streamlit page yet, latest run payload omits timestamps, and app logs are not yet populated/displayed through API/UI. |
| US-07 | As a DevOps engineer, I want to deploy the project with one command so I can quickly start the environment. Acceptance: `docker compose up --build` starts everything, secrets in `.env`, healthchecks for each service, README run instructions. | Docker Compose project skeleton with DB, Redis, MLflow, API, Streamlit; `.env.example`; README/local environment docs. | Phase 1-3.6 / `Partial` | `docker-compose.yml`; `.env.example`; `services/api/Dockerfile`; `services/streamlit/Dockerfile`; `services/mlflow/Dockerfile`; `README.md`; `docs/development/local-environment.md`. | Compose exists, but full final service readiness, per-service healthchecks, ML serving, and production-like all-in-one verification remain future integration work. |
| US-08 | As a data analyst, I want to understand model logic so I can trust predictions. Acceptance: feature importance, feature descriptions, model version, optional SHAP charts. | Future Model Insights page and MLflow-backed model metadata. | Phase 5+ / `Planned` | `docs/superpowers/specs/2026-05-31-realtyscope-design.md` requires feature importance/SHAP for grade 5; `pyproject.toml` includes `mlflow` and scikit-learn optional dependencies. | No model exists yet, so interpretability cannot be shown. Add feature importance and model version only after model training and selection are implemented. |

## Phase 3.7 Contribution

Phase 3.7 directly advances `US-02` and indirectly supports `US-03`, `US-04`, and `US-08`:

- `US-02`: observations make time-series price and price-per-m2 trends possible.
- `US-03`: historical observations help future train/validation splits and actual-vs-predicted evaluation.
- `US-04`: observations provide source/time filters for future Data Explorer work.
- `US-08`: model explanations can cite stable feature snapshots instead of only mutable latest listing rows.

The key boundary is that `listings` remains the canonical latest listing table, while `listing_observations` records the observed normalized state over time.
