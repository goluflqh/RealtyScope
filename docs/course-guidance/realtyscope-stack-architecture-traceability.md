# RealtyScope Tech Stack and Architecture Traceability

Date: 2026-06-02
Source: `E:\Магистр\2-курс\python\Описание проекта.html`, sections `Как это устроено` and `Технологический стек`.
Audience: course reviewer, implementation agents, and phase planning.

This document maps the teacher's recommended DataPulse architecture and stack guidance to RealtyScope. The stack list is treated as strong course guidance, not a blind checklist. RealtyScope adopts the technologies that fit the current phase, documents deliberate substitutions, and marks future-course requirements honestly when they are not implemented yet.

## Status Legend

- `Implemented`: working code/config/docs exist in the repository.
- `Partial`: the foundation exists, but acceptance-grade behavior is incomplete.
- `Planned`: intentionally deferred to a later phase.
- `Substituted`: the same responsibility is covered by a different, documented approach.
- `Not used`: not needed for RealtyScope's current scope.

## Architecture Traceability

| Assignment Architecture Item | RealtyScope Mapping | Status | Evidence | Notes / Gap |
| --- | --- | --- | --- | --- |
| Data Layer: External APIs, Web Scraping, Ingestor Service | Domclick snapshot collector, Chrome-assisted SSR capture, parser contracts, teammate CSV import, scheduled batch runner. | `Implemented` for Phase 3 | `src/realtyscope/ingestion/domclick_snapshot_collector.py`; `src/realtyscope/ingestion/domclick_chrome_capture.py`; `src/realtyscope/ingestion/domclick_scheduled_batch.py`; `src/realtyscope/ingestion/contracts.py`; `src/realtyscope/ingestion/teammate_import.py`; `scripts/run_domclick_scheduled_batch.ps1`. | Implemented as bounded batch ingestion, not a long-running scraper. This is safer for Domclick access and easier to test. |
| Storage: PostgreSQL, Redis Cache, Model Artifacts | PostgreSQL via Docker Compose, SQLAlchemy models, Alembic migrations, Redis service, MLflow volume/model-artifact placeholder. | PostgreSQL/Alembic `Implemented`; Redis/model artifacts `Partial` | `docker-compose.yml`; `src/realtyscope/database/models.py`; `alembic/versions/*.py`; `services/mlflow/Dockerfile`; `.env.example`. | Redis is running-ready but not used in a real read path yet. Model artifacts belong to Phase 4. |
| ML Pipeline: Feature Engineering, Model Training, MLflow Registry | Deterministic v1/v2 feature snapshots, non-leaky Ridge baseline, grouped validation, ignored joblib artifacts, and MLflow logging path when configured. | `Partial` | `src/realtyscope/ml/features.py`; `src/realtyscope/ml/train.py`; `docs/ml/phase5-non-leaky-model.md`; `tests/test_ml_features.py`; `tests/test_ml_training.py`; `services/mlflow/Dockerfile`. | Local runtime evidence did not produce a real MLflow run ID because `.venv` lacked `mlflow`; package/service setup still needs production-like verification. |
| Backend: FastAPI, `/data` endpoints, `/predict` endpoint | FastAPI app has `/health`, `/listings`, `/stats/data-quality`, `/predict`, `/model/metadata`, and `/monitoring/status`; Swagger is available through FastAPI. | `Partial` | `services/api/app/main.py`; `tests/test_api_health.py`; `tests/test_api_data_routes.py`; `tests/test_api_prediction_contract.py`; `tests/test_api_monitoring.py`. | Assignment-compatible `/data` is still represented by `/listings`; Redis cache is not yet used by a real read path. |
| Frontend: Streamlit Dashboard, Plotly charts, Interactive Filters | Streamlit reads API data and displays KPI cards, latest run, listing preview, prediction, monitoring status, recent errors, metrics, and feature importance. | `Partial` | `services/streamlit/app.py`; `services/streamlit/api_client.py`; `tests/test_streamlit_api_client.py`; `tests/test_streamlit_scaffold.py`. | Plotly charts, map views, richer filters, and true multipage layout remain future polish. |
| Docker Compose one-command local environment | Compose defines `db`, `redis`, `mlflow`, `api`, and `streamlit` with healthchecks for db/redis/api/streamlit. | `Partial` | `docker-compose.yml`; `services/api/Dockerfile`; `services/streamlit/Dockerfile`; `services/mlflow/Dockerfile`; `docs/development/local-environment.md`. | Compose structure is aligned. Full final `docker compose up --build` acceptance should be verified after ML/API/UI are feature-complete. |
| Recommended project structure: services, alembic, CI, dashboard, ML area | Monorepo uses shared `src/realtyscope`, service folders for API/Streamlit/MLflow, Alembic, CI, notebooks, scripts, and docs. | `Implemented` with pragmatic layout | `.github/workflows/ci.yml`; `alembic/`; `services/`; `src/realtyscope/`; `notebooks/`; `docs/`; `scripts/`. | Ingestor code lives in shared package plus scripts instead of a separate `services/ingestor` image. This is acceptable for Phase 3 and keeps reuse/tests simpler. |

## Tech Stack Traceability

| Course Stack Area | Teacher Guidance | RealtyScope Choice | Status | Evidence | Rationale / Gap |
| --- | --- | --- | --- | --- | --- |
| HTTP requests | Required: `requests`; advanced: `httpx`, `aiohttp`. | `urllib.request` for low-dependency collector; `requests` for Streamlit API client. | `Implemented` / `Substituted` | `src/realtyscope/ingestion/domclick_snapshot_collector.py`; `services/streamlit/api_client.py`; `pyproject.toml`. | For collector internals, stdlib is enough and reduces dependencies. `requests` is used where ergonomic for API calls. |
| HTML parsing | Required: BeautifulSoup4; advanced: `lxml`, Scrapy, parsel. | Current Domclick path primarily parses JSON/SSR state, not arbitrary HTML. | `Substituted` | `src/realtyscope/ingestion/domclick_chrome_capture.py`; `src/realtyscope/ingestion/domclick.py`. | Domclick exposes usable SSR JSON after render; extracting structured JSON is less brittle than HTML scraping. BeautifulSoup can be added only if a future source needs it. |
| Browser automation | Suggested: Selenium; advanced: Playwright/Puppeteer. | Chrome DevTools/CDP-assisted SSR capture with the real `Default` profile; legacy `--dump-dom` remains a one-off fallback. | `Substituted` | `src/realtyscope/ingestion/domclick_chrome_capture.py`; `docs/operations/domclick-scheduled-batch-ingestion.md`; `tests/test_domclick_chrome_capture.py`. | This avoids a Selenium/Playwright dependency while making scheduled capture independent from a manually opened Codex Chrome tab. It is bounded, tested, and operationally documented. |
| Task scheduler | Required: APScheduler; alternatives: Celery Beat, cron, Airflow. | Windows Task Scheduler for local capture; cron/systemd examples for Linux. | `Substituted` | `scripts/run_domclick_scheduled_batch.ps1`; `docs/operations/domclick-scheduled-batch-ingestion.md`; scheduled task `RealtyScope Domclick Scheduled Batch`. | External OS scheduler is better for a daily bounded batch than a permanently running Python process in this phase. APScheduler can be reconsidered if an ingestor service becomes long-running. |
| Relational DB | PostgreSQL; SQLite for development only. | PostgreSQL for real runtime; SQLite for narrow tests/Alembic smoke checks. | `Implemented` | `docker-compose.yml`; `src/realtyscope/config.py`; `tests/*database*`. | Aligned with course guidance. |
| ORM | SQLAlchemy 2.0. | SQLAlchemy 2.0 typed models. | `Implemented` | `src/realtyscope/database/base.py`; `src/realtyscope/database/models.py`; `pyproject.toml`. | Aligned with course guidance. |
| Migrations | Alembic. | Alembic with initial DB foundation and Phase 3.7 observations migration. | `Implemented` | `alembic/env.py`; `alembic/versions/20260531_0001_initial_database_foundation.py`; `alembic/versions/20260602_0002_listing_observations.py`; `tests/test_alembic_config.py`. | Aligned with grade-5 migration expectations. |
| Cache | Redis. | Redis service exists; real API/dashboard cache path is not implemented yet. | `Partial` | `docker-compose.yml`; `.env.example`; `pyproject.toml`. | Keep Redis for Phase 5 read-path optimization. Do not claim grade-5 cache credit until a real cached path exists. |
| File storage | Local filesystem; advanced: MinIO/S3. | Local ignored `data/raw/` and `data/processed/` for snapshots/reports; model artifacts later through MLflow volume. | `Implemented` for Phase 3 | `docs/operations/domclick-daily-collection.md`; `.gitignore`; `services/mlflow/Dockerfile`. | MinIO/S3 is unnecessary for the semester MVP unless deployment grows. |
| Data processing / EDA | pandas, numpy, scipy, Jupyter. | pandas and Jupyter notebook skeleton/summary command exist; deeper EDA remains next work. | `Partial` | `pyproject.toml`; `notebooks/phase3_eda_skeleton.ipynb`; `src/realtyscope/analysis/eda_summary.py`; `tests/test_eda_summary.py`. | Phase 3 has persisted real data and summary; Phase 4 should add fuller EDA conclusions before ML. |
| Machine Learning | scikit-learn, CatBoost, joblib, metrics, optional time-series/NLP/interpretable methods. | scikit-learn Ridge baseline and joblib artifacts exist for v1 and Phase 5 v2; CatBoost/SHAP are deferred. | `Partial` | `src/realtyscope/ml/train.py`; `docs/ml/phase5-non-leaky-model.md`; `tests/test_ml_training.py`. | v2 is non-leaky but still a first cross-sectional baseline. Time-series/forecast evaluation needs repeated observations. |
| Experiment tracking | File logs required; MLflow advanced/grade-5. | MLflow service/Dockerfile and training log path exist; unit tests verify params/metrics/artifact logging when configured. | `Partial` | `src/realtyscope/ml/train.py`; `tests/test_ml_training.py`; `services/mlflow/Dockerfile`; `pyproject.toml`. | Do not claim a real MLflow run ID until optional ML dependencies/service are verified in the target runtime. |
| Backend API | FastAPI, Pydantic, uvicorn, Swagger. | FastAPI + Pydantic stack is tested with data, prediction, model metadata, and monitoring endpoints. | `Partial` | `services/api/app/main.py`; `services/api/Dockerfile`; `tests/test_api_health.py`; `tests/test_api_data_routes.py`; `tests/test_api_prediction_contract.py`; `tests/test_api_monitoring.py`. | Assignment-style `/data` alias and Redis-backed cache path remain future hardening. |
| Frontend and visualization | Streamlit, Plotly, maps via `streamlit.map` or advanced mapping libs. | Streamlit dashboard includes overview, prediction, monitoring, and model-insight sections backed by FastAPI. | `Partial` | `services/streamlit/app.py`; `services/streamlit/Dockerfile`; `tests/test_streamlit_api_client.py`; `tests/test_streamlit_scaffold.py`. | Plotly/time-series charts and map views can follow after richer observations and OSM coverage. |
| DevOps and infrastructure | Docker/docker-compose, GitHub Actions, ruff, ruff format, pre-commit, pytest, dependency management. | Docker Compose, service Dockerfiles, CI, ruff, ruff format, pytest, pytest-cov, pre-commit dependency, and `uv.lock`. | `Implemented` foundation | `docker-compose.yml`; `.github/workflows/ci.yml`; `pyproject.toml`; `uv.lock`; `README.md`. | `uv` replaces `requirements.txt` because lockfile-based installs are more reproducible for this repo. Pre-commit config file can still be added later if required by grading. |

## Deliberate Substitutions

RealtyScope currently substitutes a few teacher-suggested technologies because the replacement is simpler or more operationally suitable:

- Chrome DevTools/CDP SSR capture instead of Selenium/Playwright: fewer dependencies, uses the real local Chrome profile, and is more reliable than raw `--dump-dom` for Domclick SSR capture.
- Windows Task Scheduler / cron / systemd instead of APScheduler: better for a daily bounded batch that should start, fail loudly, and exit.
- `uv.lock` instead of `requirements.txt`: stronger reproducibility while still compatible with pip/uv workflows.
- SSR JSON parsing instead of BeautifulSoup HTML scraping: more structured and less brittle for the current Domclick source.

These substitutions should remain documented. If a future phase adds a continuously running ingestor service or a source that requires rich DOM interactions beyond SSR extraction, APScheduler or Playwright/Selenium can be reconsidered.

## Phase 3 Readiness Signal

For Phase 3, the architecture and stack foundation is mostly in place:

- data capture and persistence are real and bounded;
- PostgreSQL schema is managed through Alembic;
- canonical listings and observation history support latest reads plus future trends;
- FastAPI and Streamlit have DB-backed slices;
- Docker/CI/ruff/pytest foundations exist.

Phase 4 should not wait for perfect UI/cache/MLflow polish. It should start once today's real capture is verified, because the remaining major gaps are exactly Phase 4+ responsibilities: EDA refinement, baseline ML, MLflow runs, model artifacts, and `/predict`.
