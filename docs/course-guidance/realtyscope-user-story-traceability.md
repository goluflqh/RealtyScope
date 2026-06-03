# RealtyScope User Story Traceability

Date: 2026-06-03
Source: `E:\Магистр\2-курс\python\MISIS_2025\season_2\Описание проекта.html`, User Stories section.
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
| US-01 | As a user, I want to see current data for the selected object so I can understand the current situation. Acceptance: automatic daily update, last update time, KPI cards, selectable analysis object. | Domclick daily capture, scheduled batch ingestion, DB-backed `/listings` and `/stats/data-quality`, Streamlit KPI slice, Data Explorer filters, and last-successful-collection metrics. | Phase 7 / `Partial: current data, KPI, filters, and last update implemented` | `src/realtyscope/ingestion/domclick_chrome_capture.py`; `src/realtyscope/ingestion/domclick_scheduled_batch.py`; `services/api/app/main.py`; `services/streamlit/app.py`; `docs/operations/domclick-scheduled-batch-ingestion.md`; tests in `tests/test_api_data_routes.py`, `tests/test_api_monitoring.py`, and `tests/test_streamlit_scaffold.py`. | Last update is now visible through `/monitoring/status` and Streamlit. Remaining polish is not a full district/object selector: the UI currently supports row limit plus price, area, rooms, source, and address filters. |
| US-02 | As a user, I want to see history and trends so I can understand change dynamics. Acceptance: time-series charts, period selection, seasonality/trend visualization, compare objects on one chart. | Phase 3.7 Observation / Price History Layer stores normalized observations for price/area/rooms/floor snapshots over time. | Phase 3.7 / `Partial: backend implemented` | `ListingObservation` in `src/realtyscope/database/models.py`; migration `alembic/versions/20260602_0002_listing_observations.py`; persistence behavior in `src/realtyscope/database/persistence.py`; tests in `tests/test_database_models.py`, `tests/test_database_persistence.py`, and `tests/test_alembic_config.py`; docs in `docs/data/listing-observations.md`. | Backend history storage is now covered. Trend API endpoints, period filters, seasonality analysis, and Streamlit comparison charts remain future dashboard work. |
| US-03 | As a user, I want to receive a prediction from an ML model so I can make decisions. Acceptance: prediction display, model quality metrics, forecast vs actual visualization, custom parameter input. | Phase 4 baseline regression trains from deterministic snapshots, Phase 5 adds `ml_features_v2_non_leaky` plus `baseline_ridge_v2_non_leaky`, and Phase 6 records Docker-backed MLflow model registration evidence. | Phase 6 / `Partial: non-leaky baseline and MLOps evidence implemented` | `src/realtyscope/ml/features.py`; `src/realtyscope/ml/train.py`; `docs/ml/phase4-baseline-model.md`; `docs/ml/phase5-non-leaky-model.md`; `docs/ml/phase6-mlflow-registration.md`; `services/api/app/schemas.py`; `services/api/app/main.py`; `services/streamlit/app.py`; tests in `tests/test_ml_features.py`, `tests/test_ml_training.py`, `tests/test_api_prediction_contract.py`, `tests/test_streamlit_api_client.py`, and `tests/test_streamlit_scaffold.py`. | The v2 model is still a cross-sectional baseline, not final appraisal serving. Forecast-vs-actual evaluation needs repeated observations and reviewer-facing UI explanation. |
| US-04 | As a user, I want to filter and search data so I can find needed information. Acceptance: sidebar filters, raw data table with pagination, column sorting, text search. | DB-backed listing table via API and Streamlit Data Explorer tab with sidebar filters and a page/offset row-window control. | Phase 7 / `Partial: filters and basic pagination implemented` | `/data` and `/listings` support `min_price_rub`, `max_price_rub`, `min_area_m2`, `max_area_m2`, `rooms`, `source_name`, `search`, and `offset` in `services/api/app/main.py`; Streamlit sidebar controls are wired through `services/streamlit/api_client.py`; tests in `tests/test_api_data_routes.py`, `tests/test_streamlit_api_client.py`, and `tests/test_streamlit_scaffold.py`. | Filter/search and basic browsing acceptance are covered. Remaining polish is final browser verification and richer column sorting only if the reviewer explicitly requires it. |
| US-05 | As a developer, I want to use a REST API so I can integrate data into my applications. Acceptance: Swagger/OpenAPI, `/health`, `/data`, `/predict`, Pydantic validation, correct HTTP status codes. | FastAPI service with health, listing data, data-quality stats, Redis-backed filtered `/data`, `/predict`, `/model/metadata`, and `/monitoring/status`, backed by Pydantic request/response validation where needed. | Phase 7.2 / `Implemented for course API scope` | `services/api/app/main.py`; `services/api/app/schemas.py`; `tests/test_api_health.py`; `tests/test_api_data_routes.py`; `tests/test_api_prediction_contract.py`; `tests/test_api_monitoring.py`; README API URLs. FastAPI provides Swagger/OpenAPI automatically at `/docs`. | Final readiness should still browser-check Swagger and runtime endpoints after future changes, but the required API surface is now covered. |
| US-06 | As an administrator, I want to monitor system status so I can know about problems. Acceptance: source status page, latest ingestion logs, working/not-working indicator, last successful collection time. | Ingestion run accounting, data-quality stats with timestamps, model status, recent `AppLog` errors, `/monitoring/status`, and Streamlit monitoring section with last successful collection timestamp/source/record count. | Phase 7 / `Partial: status and last-success display implemented` | `IngestionRun` and `AppLog` models in `src/realtyscope/database/models.py`; `GET /stats/data-quality`, `GET /monitoring/status`, and `GET /model/metadata` in `services/api/app/main.py`; `services/streamlit/app.py`; tests in `tests/test_api_monitoring.py`, `tests/test_streamlit_api_client.py`, and `tests/test_streamlit_scaffold.py`. | App logs exist and are displayed when present, but most runtime commands still need to populate `app_logs` more consistently for deeper operations evidence. |
| US-07 | As a DevOps engineer, I want to deploy the project with one command so I can quickly start the environment. Acceptance: `docker compose up --build` starts everything, secrets in `.env`, healthchecks for each service, README run instructions. | Docker Compose runtime with DB, Redis, MLflow, API, Streamlit, trainer/model artifact path, `.env.example`, README/local environment docs, and safe cleanup guidance. | Phase 6-7.1 / `Implemented for local runtime` | `docker-compose.yml`; `.env.example`; `services/api/Dockerfile`; `services/streamlit/Dockerfile`; `services/mlflow/Dockerfile`; `services/trainer/Dockerfile`; `README.md`; `docs/development/local-environment.md`; `docs/ml/phase6-mlflow-registration.md`. | Final submission still needs one concise demo script and final Docker/browser/CI smoke after the remaining Phase 7 changes. |
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

- Current runtime readiness refreshed on 2026-06-03 shows `3019` persisted listings, `3989` observations, `970` listings with multiple observations, `26` detected price changes, full coordinate coverage, and full ML-ready coverage. Trend language still stays conservative until observation freshness and repeated-capture semantics are reviewed for the defense.
- OpenStreetMap enrichment has a local/fixture-tested feature contract, `osm_features` persistence, and a Phase 5 bounded live Overpass write path. The local PostgreSQL database now has 4 live OSM rows (`osm_rows_present=4` for the first five ML feature rows), and any UI/docs using OSM-derived data must keep visible OpenStreetMap attribution.
- ML feature snapshots are deterministic (`ml_features_v1`) and include listing facts, latest observation facts, optional OSM features, and missingness flags.
- Baseline training writes `data/processed/models/phase4/baseline_ridge_v1.joblib`, compares Ridge against a naive median baseline, and documents live metrics. The near-perfect metrics are caveated because current feature rows include latest price fields.
- `/predict` and Streamlit now provide a minimal baseline prediction contract with model version, feature version, metrics summary, input echo, and caveat. This is a Phase 4 contract scaffold, not final production appraisal serving.

## Phase 5 ML Contribution

The Phase 5 ML slice advances `US-03` and `US-08` without pretending the model is final:

- `ml_features_v2_non_leaky` removes latest-price feature leakage while preserving the deterministic feature builder and OSM missingness behavior.
- Training now defaults the v2 model version to `baseline_ridge_v2_non_leaky` and records grouped validation metadata by `listing_id`.
- Current `/model/metadata` evidence on the local PostgreSQL database reports `rows_total=3019`, MAE `22,685,629.92` versus naive MAE `28,452,175.74`, `r2=0.5317`, and 23 non-leaky features.
- Phase 5 did not claim a local `.venv` MLflow run; Phase 6 supersedes that caveat with Docker-backed MLflow evidence.

## Phase 6 MLOps And Runtime Contribution

Phase 6 advances `US-03`, `US-05`, `US-07`, and `US-08` with production-like evidence:

- Docker Compose builds from scoped in-repo contexts and starts `db`, `redis`, `mlflow`, `api`, and `streamlit` from the Windows-mounted repo.
- Redis backs the `/listings` and `/data` API read path.
- The trainer service logs MLflow run `4999892d2d92402ab78e1209203c338e` and registers `realtyscope-price-model` version `3`.
- GitHub Actions is green at `30bce998f1c3e5a6d13085d08a0b3692a52234a2` on `main`; Phase 7 is also CI-green through `83ad3e180c375215a1ff881166a803a4f9b8e7e4` on `phase7-course-readiness-polish`.
- The remaining Phase 7 user-story gaps are mainly final polish: runtime log population, final UI/browser evidence, and a fresh final Docker/browser smoke check.

## Phase 7 Contribution

Phase 7.0-7.3 advances `US-01`, `US-04`, `US-05`, `US-07`, and `US-08` with reviewer-facing evidence:

- `docs/project-status.md` now acts as the live status board for branch, CI, runtime data, requirements, and remaining work.
- Phase 7.1 documents fresh runtime/data evidence plus safe Docker/storage cleanup guidance.
- Phase 7.2 adds tested API and Streamlit filters for price, area, rooms, source, and address search.
- Phase 7.3 adds tested reviewer visuals: price distribution, median price by rooms, and a coordinate map with visible OpenStreetMap attribution.
- The latest monitoring/demo/UI slices add last-successful-collection visibility, a concise reviewer runbook, Streamlit tabs, and a simple Data Explorer page control.
- Phase 7 final evidence refresh confirms Docker services, API `/predict`, filtered `/data`, Redis cache keying, MLflow registered model version `3`, and Streamlit Browser DOM smoke against the current runtime.
