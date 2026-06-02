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
| US-03 | As a user, I want to receive a prediction from an ML model so I can make decisions. Acceptance: prediction display, model quality metrics, forecast vs actual visualization, custom parameter input. | Phase 4 baseline regression trains from deterministic snapshots and Phase 5 adds `ml_features_v2_non_leaky` plus `baseline_ridge_v2_non_leaky` for leakage-controlled evidence. | Phase 5 / `Partial: non-leaky baseline evidence implemented` | `src/realtyscope/ml/features.py`; `src/realtyscope/ml/train.py`; `docs/ml/phase4-baseline-model.md`; `docs/ml/phase5-non-leaky-model.md`; `services/api/app/schemas.py`; `services/api/app/main.py`; `services/streamlit/app.py`; tests in `tests/test_ml_features.py`, `tests/test_ml_training.py`, `tests/test_api_prediction_contract.py`, `tests/test_streamlit_api_client.py`, and `tests/test_streamlit_scaffold.py`. | The v2 model is still a cross-sectional baseline, not final appraisal serving. MLflow logging is code/test-covered when tracking is configured, but this local venv did not produce a real MLflow run ID. Forecast-vs-actual evaluation needs repeated observations. |
| US-04 | As a user, I want to filter and search data so I can find needed information. Acceptance: sidebar filters, raw data table with pagination, column sorting, text search. | DB-backed listing table via API and Streamlit listing preview. | Phase 3.5 / `Partial` | `GET /listings` supports `limit` and `offset` in `services/api/app/main.py`; Streamlit shows a listing dataframe in `services/streamlit/app.py`; tests in `tests/test_api_data_routes.py` and `tests/test_streamlit_api_client.py`. | There are no API filters for price/area/rooms/source/text yet, and Streamlit has only row-limit selection. Add filter/query parameters and UI controls in a future Data Explorer phase. |
| US-05 | As a developer, I want to use a REST API so I can integrate data into my applications. Acceptance: Swagger/OpenAPI, `/health`, `/data`, `/predict`, Pydantic validation, correct HTTP status codes. | FastAPI service with health, listing data, data-quality stats, `/predict`, `/model/metadata`, and `/monitoring/status`, backed by Pydantic request/response validation where needed. | Phase 5 / `Partial: service contracts implemented` | `services/api/app/main.py`; `services/api/app/schemas.py`; `tests/test_api_health.py`; `tests/test_api_data_routes.py`; `tests/test_api_prediction_contract.py`; `tests/test_api_monitoring.py`; README API URLs. FastAPI provides Swagger/OpenAPI automatically at `/docs`. | Assignment-compatible `/data` is still represented by `/listings`, and Redis caching is not yet used by a real read path. |
| US-06 | As an administrator, I want to monitor system status so I can know about problems. Acceptance: source status page, latest ingestion logs, working/not-working indicator, last successful collection time. | Ingestion run accounting, data-quality stats with timestamps, model status, recent `AppLog` errors, `/monitoring/status`, and Streamlit monitoring section. | Phase 5 / `Partial: monitoring contract implemented` | `IngestionRun` and `AppLog` models in `src/realtyscope/database/models.py`; `GET /stats/data-quality`, `GET /monitoring/status`, and `GET /model/metadata` in `services/api/app/main.py`; `services/streamlit/app.py`; `tests/test_api_monitoring.py`; `tests/test_streamlit_api_client.py`. | App logs exist and are displayed when present, but most runtime commands still need to populate `app_logs` more consistently. |
| US-07 | As a DevOps engineer, I want to deploy the project with one command so I can quickly start the environment. Acceptance: `docker compose up --build` starts everything, secrets in `.env`, healthchecks for each service, README run instructions. | Docker Compose project skeleton with DB, Redis, MLflow, API, Streamlit; `.env.example`; README/local environment docs. | Phase 1-3.6 / `Partial` | `docker-compose.yml`; `.env.example`; `services/api/Dockerfile`; `services/streamlit/Dockerfile`; `services/mlflow/Dockerfile`; `README.md`; `docs/development/local-environment.md`. | Compose exists, but full final service readiness, per-service healthchecks, ML serving, and production-like all-in-one verification remain future integration work. |
| US-08 | As a data analyst, I want to understand model logic so I can trust predictions. Acceptance: feature importance, feature descriptions, model version, optional SHAP charts. | Phase 5 documents feature versions, leakage caveats, grouped validation metadata, model version, metrics, API model metadata, and Streamlit model insights for the v2 artifact. | Phase 5 / `Partial: model insights available` | `docs/ml/phase5-non-leaky-model.md`; `docs/ml/phase5-non-leaky-model.vi.md`; `src/realtyscope/ml/features.py`; `src/realtyscope/ml/train.py`; `/model/metadata` and `/predict` in `services/api/app/main.py`; `services/streamlit/app.py`; `tests/test_api_monitoring.py`; `tests/test_streamlit_scaffold.py`. | SHAP and richer feature descriptions are still optional future polish; current insight is coefficient-based feature importance from the Ridge artifact. |

## Phase 3.7 Contribution

Phase 3.7 directly advances `US-02` and indirectly supports `US-03`, `US-04`, and `US-08`:

- `US-02`: observations make time-series price and price-per-m2 trends possible.
- `US-03`: historical observations help future train/validation splits and actual-vs-predicted evaluation.
- `US-04`: observations provide source/time filters for future Data Explorer work.
- `US-08`: model explanations can cite stable feature snapshots instead of only mutable latest listing rows.

The key boundary is that `listings` remains the canonical latest listing table, while `listing_observations` records the observed normalized state over time.

## Phase 4 Contribution

Phase 4 advances `US-02`, `US-03`, `US-05`, and `US-08` with tested, repo-backed evidence:

- Data readiness and observation EDA show 2,000 persisted listings/observations with strong coordinate and ML-ready coverage, but only one observation per listing and no meaningful price-change history yet.
- OpenStreetMap enrichment has a local/fixture-tested feature contract, `osm_features` persistence, and a Phase 5 bounded live Overpass write path. The local PostgreSQL database now has 4 live OSM rows (`osm_rows_present=4` for the first five ML feature rows), and any UI/docs using OSM-derived data must keep visible OpenStreetMap attribution.
- ML feature snapshots are deterministic (`ml_features_v1`) and include listing facts, latest observation facts, optional OSM features, and missingness flags.
- Baseline training writes `data/processed/models/phase4/baseline_ridge_v1.joblib`, compares Ridge against a naive median baseline, and documents live metrics. The near-perfect metrics are caveated because current feature rows include latest price fields.
- `/predict` and Streamlit now provide a minimal baseline prediction contract with model version, feature version, metrics summary, input echo, and caveat. This is a Phase 4 contract scaffold, not final production appraisal serving.

## Phase 5 ML Contribution

The Phase 5 ML slice advances `US-03` and `US-08` without pretending the model is final:

- `ml_features_v2_non_leaky` removes latest-price feature leakage while preserving the deterministic feature builder and OSM missingness behavior.
- Training now defaults the v2 model version to `baseline_ridge_v2_non_leaky` and records grouped validation metadata by `listing_id`.
- Runtime evidence on the local 2,000-row PostgreSQL database produced MAE `21,189,758.79` versus naive MAE `23,656,479.23` with 23 non-leaky features.
- MLflow logging is covered when configured; a real local MLflow run ID is not claimed because the active `.venv` did not have `mlflow` installed during runtime evidence.
