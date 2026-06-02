# RealtyScope Course Guidance Review

Date: 2026-05-31
Status: Shared reference for Phase 3+ planning and implementation.
Audience: agentic implementation workers and future project sessions.

This document consolidates the course project requirements, lecture notebook guidance, and official documentation checks that should guide RealtyScope after Phase 2. Keep this file as the durable bridge between the course materials and implementation plans.

For day-to-day execution, use [RealtyScope Course Operating Playbook](realtyscope-course-operating-playbook.md) as the standing checklist for every future phase. It translates these course requirements into branch hygiene, ingestion, database, EDA, ML, API, Streamlit, Docker, CI, and evidence rules.

---

## 1. Sources Reviewed

Local course/reference materials from `E:\Магистр\2-курс\python\MISIS_2025\season_2`:

- `Описание проекта.html`
- `Примерный план семестра.htm`
- `S2_L1_parsing_cli_docker.ipynb`
- `S2_L2_DB.ipynb`
- `S2_L3_EDA.ipynb`
- `S2_L2_ML_part1.ipynb`
- `S2_L2_ML_part2.ipynb`
- `S2_L4_ML_classic (1).ipynb`
- `S2_L5_ML_NN_LLM_CV_GUI (1).ipynb`
- `S2_L6_GUI_RL_BACKEND (1).ipynb`
- `S2_L7_BEND2_Streamlit_BigData.ipynb`
- `L1_Start_Drum_Base.ipynb`
- `bai_giang_so_1_tom_tat_day_du.ipynb`

Official/current documentation consulted or earmarked for implementation decisions:

- SQLAlchemy 2.0 docs: https://docs.sqlalchemy.org/en/20/
- SQLAlchemy ORM declarative mapping: https://docs.sqlalchemy.org/en/20/orm/declarative_tables.html
- Alembic docs: https://alembic.sqlalchemy.org/en/latest/
- Alembic autogenerate docs: https://alembic.sqlalchemy.org/en/latest/autogenerate.html
- Pydantic v2 docs: https://docs.pydantic.dev/
- FastAPI lifespan docs: https://fastapi.tiangolo.com/advanced/events/
- OpenStreetMap Nominatim policy: https://operations.osmfoundation.org/policies/nominatim/
- Overpass API examples: https://wiki.openstreetmap.org/wiki/Overpass_API/Overpass_API_by_Example
- pandas user guide: https://pandas.pydata.org/docs/user_guide/
- scikit-learn model selection docs: https://scikit-learn.org/stable/model_selection.html
- MLflow tracking docs: https://mlflow.org/docs/latest/ml/tracking/
- Streamlit docs: https://docs.streamlit.io/
- Docker Compose docs: https://docs.docker.com/compose/

Google Developer Knowledge is not a primary source for RealtyScope right now because Phase 3+ does not use Google developer products. Use it only if a future scope introduces Google Cloud, Maps Platform, Gemini, Firebase, etc.

---

## 2. Non-Negotiable Grading Contract

The course project is DataPulse-style: each student/team chooses a domain but follows a common architecture and grading rubric.

For RealtyScope, the required final system must be a data-driven web service that can be launched locally through Docker Compose and demonstrates the full path:

1. Collect data from API/web sources.
2. Persist and update data in PostgreSQL.
3. Analyze/clean/feature-engineer data in notebooks.
4. Train a useful ML model.
5. Serve data and predictions through FastAPI.
6. Show analysis/prediction/monitoring in Streamlit.
7. Package and verify everything with Docker, tests, CI, and documentation.

Grade 4 minimum:

- `docker compose up --build` launches the project.
- At least 2 data sources.
- At least 1000 database records.
- Missing values are explicitly handled.
- EDA notebook includes visualizations and conclusions.
- Baseline ML model uses correct validation and beats a naive baseline.
- FastAPI has `/predict`; Swagger/OpenAPI works.
- Streamlit has at least 3 pages.
- README explains how to run the project.

Grade 5 additions:

- MLflow tracks experiments, parameters, metrics, and artifacts.
- SHAP or feature importance appears in the UI.
- Monitoring/logs page shows source status, ingestion status, errors, or logs.
- `pytest` coverage target is at least 50%.
- GitHub Actions runs lint and tests.
- Alembic manages database migrations.
- Redis is used for real caching/optimization, not merely declared in Compose.
- Code quality uses ruff, pre-commit, and type hints.

Point-loss risks found in course notes:

- No Alembic migration directory/version files: costs grade-5 migration credit.
- `docker-compose.yml` not at repo root or not reproducible: directly harms reproducibility score.
- `.env`, raw dumps, database dumps, and model artifacts committed to Git: bad hygiene and possible security/data-quality issue.
- Model only inside notebook and not served by API: does not satisfy service requirement.
- API/UI crashes on first click: fails acceptance expectations even if code exists.
- Redis/MLflow/monitoring declared but unused: likely counted as incomplete.

---

## 3. Course Architecture Mapped to RealtyScope

The course reference architecture is:

```text
External APIs / Web Scraping
        -> Ingestor Service
        -> PostgreSQL + Redis + Model Artifacts
        -> ML Pipeline + MLflow
        -> FastAPI (/data, /predict)
        -> Streamlit Dashboard
        -> Docker Compose
```

RealtyScope mapping:

- External listing source: Domclick, with possible teammate source import.
- Enrichment source: OpenStreetMap-derived features.
- Ingestor: collectors/parsers/importers plus validation and persistence.
- Storage: PostgreSQL as source of truth; JSONL snapshots only as local/raw artifacts.
- ML: Moscow apartment sale-price regression, target `price_rub`.
- API: FastAPI endpoints for health, data, prediction, and monitoring.
- UI: Streamlit pages for overview, prediction, data exploration, monitoring/logs, and model insights.
- Ops: Docker Compose, CI, tests, ruff, pre-commit, README.

---

## 4. Lecture Guidance by File

### `Описание проекта.html`

Key requirements:

- Data collection can use API or web scraping, but data must be stored in PostgreSQL and updated automatically or reproducibly.
- Project structure should expose separate responsibilities: ingestor, API, dashboard, ML, tests, migrations.
- Required stack includes PostgreSQL, SQLAlchemy 2.0, Alembic, Redis, pandas, scikit-learn, FastAPI, Pydantic, Streamlit, Docker Compose, GitHub Actions, ruff, pre-commit, pytest.
- RealtyScope is listed as a valid real-estate domain: ЦИАН, Домклик, Яндекс.Недвижимость; ML tasks include market-price prediction and bargain detection.
- Suggested timeline expects 1000+ first records early, then DB/ingestor, then EDA/feature engineering, then ML, then API, then Streamlit, then integration/polish.

Implementation consequences:

- The project should remain a service, not only notebooks/scripts.
- RealtyScope should keep source strategy explainable: Domclick plus OSM, optional teammate source.
- Grade-5 proof needs screenshots/logs/tests, not just code existence.

### `Примерный план семестра.htm`

Key guidance:

- The course builds DataPulse gradually through EDA, ML, Data Engineering, Backend, DevOps/MLOps, and Cloud/Big Data topics.
- Data Engineering topics explicitly include requests, BeautifulSoup, Selenium, API integration, PostgreSQL, SQLAlchemy, and Alembic.
- Backend topics include FastAPI, Pydantic, lifespan, pytest, TDD, refactoring, type hints.
- DevOps/MLOps topics include Docker, Docker Compose, Git/GitHub, MLflow, GitHub Actions, and CI/CD.

Implementation consequences:

- Phase 3 should not just create tables; it should establish the data-engineering layer in a way later API/ML/UI can reuse.
- TDD and narrow verification remain aligned with the course.
- Type hints and clean boundaries matter for grade-5 code quality.

### `S2_L1_parsing_cli_docker.ipynb`

Key guidance:

- DataPulse data layer should parse websites or call APIs, then persist data into PostgreSQL.
- Prefer API if available; use scraping when no API exists or API is insufficient.
- Use custom headers/User-Agent, timeouts, sessions, pagination handling, and rate-limit awareness.
- Respect `robots.txt` and ethical scraping boundaries.
- Debug parsers from cached/saved HTML/JSON snapshots; do not hit the real website on every parser edit.
- Use Docker Compose to separate services and make the project reproducible.
- `.gitignore` must exclude virtual envs, `.env`, caches, raw data dumps, model artifacts.

Implementation consequences for RealtyScope:

- Phase 2 correctly avoided live Domclick calls in tests and used snapshot parsing.
- A future live collector should be rate-limited, timeout-protected, cache/snapshot-friendly, and clearly replaceable.
- If Domclick exposes usable JSON in the page/API responses, parse that; if not, use HTML parsing or browser automation only as a controlled fallback.
- Tests should mock or replay source responses rather than call real external services.

### `bai_giang_so_1_tom_tat_day_du.ipynb`

Key guidance:

- Docker solves environment drift; all final services should start consistently.
- Use separate images/services instead of one huge image: scraper/ingestor, backend, frontend, DB, Redis, MLflow have different commands/dependencies.
- Dockerfile build cache should copy dependency files before source code to avoid slow rebuilds.
- Docker Compose internal DNS uses service names, not `localhost`, between containers.
- Data collection section covers API, REST/JSON, authentication, pagination, rate limits, HTML scraping, Selenium/dynamic content, robots.txt, and scraping ethics.

Implementation consequences:

- Keep service boundaries explainable even if code is in a monorepo package.
- Container-to-container settings must use service hostnames (`db`, `redis`, `api`, `mlflow`).
- Local dev can use `localhost`; Docker env must override hosts.

### `S2_L2_DB.ipynb`

Key guidance:

- `docker-compose.yml` belongs in repo root and is the launch heart of the system.
- PostgreSQL data must live in a named volume; containers are ephemeral.
- Pydantic validates dirty external data before DB writes.
- API/source payloads can lie or drift; use aliases, constraints, validators, and timestamps.
- SQLAlchemy 2.0 should use typed declarative models: `DeclarativeBase`, `Mapped`, `mapped_column`, relationships, indexes, foreign keys.
- Use sessions and transactions with explicit commit/rollback; context managers avoid connection leaks.
- Do not rely on `Base.metadata.create_all()` as the production schema path; use Alembic migrations.
- Alembic is obligatory for grade 5; instructor may check `alembic/versions`.
- Merge multiple sources transactionally and maintain relational links rather than duplicating uncontrolled rows.

Implementation consequences for Phase 3:

- Add SQLAlchemy models for sources, ingestion runs, raw listings, listings, listing-source links, and possibly app logs.
- Configure Alembic with `target_metadata = Base.metadata` and an initial migration.
- Verify `alembic upgrade head` on a fresh DB.
- Add DB tests around constraints, inserts, transaction handling, and duplicate behavior.
- Keep raw payloads/audit records separate from canonical listings.

### `S2_L3_EDA.ipynb`

Key guidance:

- EDA is not optional decoration; it is evidence for the project story.
- Required EDA dimensions: data shape, types, missing values, duplicates, outliers, distributions, correlations/relationships, and conclusions.
- Cleaning must be explicit and justified; do not silently drop inconvenient rows.
- Visualizations should support decisions: target distribution, feature-target relationship, missingness, outliers, geographic coverage where relevant.
- Feature engineering should follow observed data patterns and ML needs.

Implementation consequences:

- Store enough raw and normalized data to support reproducible EDA.
- Build an EDA notebook after DB ingestion exists, not before data is persistent.
- For RealtyScope, EDA should include price, area, price per m2, rooms, floor, location coverage, coordinate availability, and source/rejection stats.

### ML notebooks: `S2_L2_ML_part1.ipynb`, `S2_L2_ML_part2.ipynb`, `S2_L4_ML_classic (1).ipynb`, `S2_L5_ML_NN_LLM_CV_GUI (1).ipynb`

Key guidance:

- Start with simple, defensible classical ML.
- Regression metrics should include MAE/RMSE/R2 or domain-appropriate equivalents.
- Compare against naive baselines.
- Use correct validation; avoid leakage.
- Feature importance or SHAP is needed for grade 5 interpretability.
- Save trained artifacts outside Git, then expose the selected model through API later.
- MLflow is the expected tracking tool for grade 5.

Implementation consequences:

- RealtyScope should start with classical regression models before complex NLP/time-series/deep learning.
- Use grouped or careful split if duplicate/cross-source listing links exist.
- Use `price_rub` target and consider log transforms or price per m2 analysis during EDA.
- Text/NLP can remain optional unless core requirements are already satisfied.

### `S2_L6_GUI_RL_BACKEND (1).ipynb`

Key guidance:

- FastAPI should use Pydantic schemas as contracts.
- Load expensive resources once using FastAPI lifespan and `app.state`, not repeated per request.
- `@app.on_event` startup/shutdown is deprecated in newer FastAPI guidance; lifespan is the preferred pattern.
- Prediction service should preserve exact feature order/names used during training.
- Tests should exercise health, success cases, and validation errors.

Implementation consequences:

- Later API phase should use lifespan for DB/Redis/model resources.
- `/predict` must not reconstruct/load the model on every request.
- Pydantic request/response schemas should be stable and documented through Swagger.

### `S2_L7_BEND2_Streamlit_BigData.ipynb`

Key guidance:

- Streamlit dashboard should be multipage and API-driven.
- Recommended pages: Analytics/Overview, Predict, Monitoring; course project also expects Data table/explorer.
- Use `st.cache_data` for data and `st.cache_resource` for reusable clients/resources.
- Double cache pattern: Streamlit cache on UI side plus Redis cache on API side.
- Monitoring page should show API health, source statuses, last update, and logs/errors.
- Pandas is enough for typical DataPulse sizes; DuckDB/Polars can be considered if data grows.

Implementation consequences:

- Redis needs a real read path later, e.g. data stats, source status, or prediction cache.
- Streamlit should call FastAPI, not bypass backend for core production paths.
- Monitoring/log data should be persisted during DB/API phases so the UI can display it.

### `L1_Start_Drum_Base.ipynb`

Key guidance:

- Mostly environment and Python basics. It reinforces using notebooks as a lab journal and documenting reasoning.

Implementation consequences:

- Keep notebooks readable and explanatory for defense, not just code dumps.

---

## 5. Official Documentation Decisions

### SQLAlchemy 2.0

Use modern typed mappings:

- `class Base(DeclarativeBase): ...`
- `Mapped[T]`
- `mapped_column(...)`
- `relationship(...)` with explicit `back_populates` where relationships are useful.

Use explicit transaction boundaries:

- `with SessionLocal() as session:` plus `commit`/`rollback`, or `with session.begin()` for atomic blocks.
- Avoid global sessions.
- Avoid string-built SQL for normal ORM work.

Do not use `Base.metadata.create_all()` as the main schema-management path once Alembic exists. It is acceptable only for narrow throwaway tests if justified; Phase 3 should verify migrations instead.

### Alembic

Required Phase 3 patterns:

- Initialize `alembic/` in repo root or a clearly documented project location.
- Configure `alembic.ini` and `alembic/env.py` to use project settings/database URL.
- Import SQLAlchemy model metadata into `env.py` as `target_metadata = Base.metadata`.
- Generate an initial migration with `alembic revision --autogenerate` after models exist, then review/edit the migration manually.
- Verify from an empty database with `alembic upgrade head`.
- Keep `alembic/versions/*.py` committed.

### Pydantic v2

Continue Phase 2 direction:

- Use `BaseModel`, `Field` constraints, validators, aliases/alias paths where source data is messy.
- Use `model_validate(...)` for external dictionaries.
- Use `computed_field` where derived values should appear in dumps.
- Use `model_dump(mode="json")` for JSON-safe persistence artifacts.

### FastAPI

Later API phase should:

- Use Pydantic request/response schemas.
- Use lifespan for model/DB/Redis setup and shutdown.
- Keep `/health`, `/data`, `/predict`, and monitoring endpoints testable through `TestClient` or equivalent.

### OSM / Nominatim / Overpass

For OSM enrichment:

- Prefer listing coordinates already provided by Domclick/teammate source.
- Avoid public Nominatim bulk geocoding.
- Cache geocoding results if geocoding is unavoidable.
- Rate-limit all public OSM/Overpass calls.
- Use saved snapshots/fixtures for tests.
- Add OSM attribution in README and UI if derived OSM data or maps are shown.

---

## 6. Phase 3 Implementation Guidance

Phase 3 should focus on database and data-quality foundation, not API/ML/UI expansion.

Recommended Phase 3 scope:

1. Add SQLAlchemy database package:
   - engine/session helpers
   - typed ORM base
   - source, run, raw listing, canonical listing, source-link, and app-log models
2. Add Alembic setup and initial migration.
3. Add persistence functions that save Phase 2 `IngestionBatch` objects into PostgreSQL.
4. Add dedup/audit rules at the DB level:
   - unique source records
   - payload hash
   - source-to-canonical links
5. Add cleaning eligibility flags for ML-ready rows:
   - has required target/features
   - has coordinates or documented fallback
   - reject/incomplete rows remain auditable
6. Add basic DB-backed ingestion run accounting:
   - records seen
   - inserted/updated/rejected
   - status/error summary
7. Add a first EDA notebook skeleton only after persisted sample data exists, or create the notebook with clear placeholder cells that are not claimed complete.

Phase 3 should not yet implement:

- full model training
- MLflow experiment tracking
- FastAPI production endpoints beyond existing health
- Streamlit full dashboard pages
- Redis production caching
- live heavy OSM enrichment at scale

These belong to later phases unless the user explicitly changes scope.

---

## 7. RealtyScope Anti-Point-Loss Checklist

Before each future phase completion claim, verify these items against current state:

- Is `docker-compose.yml` still at repo root?
- Can relevant services launch from a clean checkout?
- Are `.env`, raw data dumps, DB dumps, model artifacts, and notebooks outputs/artifacts handled safely?
- Are Alembic migrations present for every DB schema change?
- Does the DB migrate from empty state?
- Are there tests for validation, persistence, and failure paths?
- Does the README explain how to run the current phase honestly?
- Does each declared grade-5 feature have real behavior, not just a placeholder?
- Are external-source tests using fixtures/snapshots, not live services?
- Are official-source policies respected for scraping/geocoding?

---

## 8. How Future Agents Should Use This File

Before Phase 3+ work:

1. Read this file first.
2. Read the Phase 0 design spec next: `docs/superpowers/specs/2026-05-31-realtyscope-design.md`.
3. Read the current phase plan, if present.
4. If writing a new plan, write the technical plan in English and include a Vietnamese companion summary.
5. Use Context7/official docs when implementing libraries with version-sensitive APIs.
6. Save any durable updates back to mem0 and this guidance file if course interpretation changes.
