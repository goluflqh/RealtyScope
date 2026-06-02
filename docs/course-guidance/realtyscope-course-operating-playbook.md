# RealtyScope Course Operating Playbook

Date: 2026-06-02
Scope: standing operating rules for all future RealtyScope phases.
Source: reread of `E:\Магистр\2-курс\python\MISIS_2025\season_2` lecture notebooks and project HTML, plus existing course-guidance docs.

This is the practical layer on top of the course review. Use it when planning and reviewing every phase, not only Phase 5.

## Core Interpretation

The course expects a DataPulse-style data product, not isolated scripts or notebooks. Every phase should move RealtyScope closer to this chain:

```text
External data sources
  -> bounded ingestor
  -> PostgreSQL + audit trails + cache/artifacts
  -> EDA and feature engineering evidence
  -> validated ML experiments + MLflow
  -> FastAPI data/prediction/monitoring contracts
  -> Streamlit dashboard pages
  -> Docker Compose, CI, tests, docs
```

A feature counts only when it is usable, verified, and visible in the appropriate layer. Declared services such as Redis, MLflow, API routes, monitoring, or dashboards are not enough if they do not have real behavior.

## Phase Rules

1. Keep phase branches as milestones.
   - Do not rename or delete a completed phase branch when starting the next phase.
   - Create a new phase branch from the previous phase branch.
   - Keep GitNexus indexes phase-specific when both phases matter.

2. Every phase must improve the product chain.
   - Avoid work that only adds code without moving data, ML, API, UI, or operations forward.
   - Prefer small end-to-end slices over broad disconnected internals.

3. Keep evidence with the implementation.
   - Code change: test it.
   - Data change: record counts, quality checks, and sample conclusions.
   - ML change: record baseline, validation split, metrics, artifact path, and caveats.
   - Ops change: record schedule, logs, reports, and how to verify the next run.

## Data Ingestion Rules

Lecture guidance emphasizes reproducible, ethical, bounded collection.

- Prefer official APIs when available; use scraping/browser automation only when justified.
- Respect robots.txt and anti-abuse boundaries.
- Use saved snapshots/fixtures for parser tests; do not hit live sites in unit tests.
- Add timeouts, rate limits, clear user-agent/operator metadata, and fail-loud reports.
- Raw data is local/generated artifact, not source code.
- Scheduled runs must create new observation evidence, not only rerun old files.

RealtyScope consequence: the Domclick scheduled task should run at 00:00 Moscow time and must be fixed so a daily run either captures a fresh snapshot directory or records a new observation timestamp deliberately. Reusing a same-day bulk folder without inserting observations does not build trend data.

## Database Rules

Lecture guidance treats PostgreSQL and Alembic as central, not optional.

- PostgreSQL is the source of truth; local JSON/HTML files are raw artifacts.
- Pydantic validates external data before database writes.
- SQLAlchemy 2.0 typed models and explicit relationships should remain the style.
- Alembic migrations are the production schema path; `create_all()` is only for tests or local fixtures.
- Ingestion should preserve raw payloads, canonical latest rows, source links, rejected rows, and ingestion runs.
- Duplicate handling must be intentional and documented.

RealtyScope consequence: observation history needs semantics beyond `raw_listing_id` uniqueness if daily trend modeling is required. A repeated unchanged listing can still be a valid observation at a new collection time.

## EDA Rules

EDA is grading evidence, not decoration.

Each EDA phase should cover:

- row counts and schema/types;
- missing values and explicit handling choices;
- duplicates and deduplication logic;
- outliers and whether they are clipped, flagged, or kept;
- target distribution and business interpretation;
- feature relationships/correlations;
- data quality conclusions that drive the next engineering or ML step.

RealtyScope consequence: cross-sectional EDA is acceptable now, but trend/price-change conclusions must wait until there are multiple observations per listing.

## ML Rules

Lecture guidance favors correct validation before model complexity.

- Start with naive and classic ML baselines.
- Beat the naive baseline with a non-leaky validation setup.
- Do not trust metrics if target-like fields leak into features.
- Save artifacts outside git and log experiments to MLflow when enabled.
- For grade 5, add feature importance or SHAP and expose model metadata in UI.
- Do not jump to deep learning unless the data volume and problem justify it.

RealtyScope consequence: `baseline_ridge_v1` proves the pipeline, but its current metrics are inflated because `ml_features_v1` includes latest price fields. The next ML phase must build a leakage-controlled feature version before making quality claims.

## API Rules

API is the product boundary.

- FastAPI routes must use Pydantic request/response schemas.
- Heavy resources such as DB engines, Redis clients, and models should be loaded once, ideally through lifespan/app state, not per request.
- Test success and validation/error cases.
- Swagger/OpenAPI should be useful to a reviewer without reading source code.

RealtyScope consequence: `/predict` exists as a Phase 4 contract, but future hardening should move artifact loading toward lifespan/app state and add model health/metadata endpoints.

## Streamlit Rules

Streamlit is not a screenshot layer; it is the reviewer-facing product.

Minimum useful pages for the course direction:

- Overview/analytics with KPIs and data quality.
- Data explorer with filters/search/table.
- Prediction page with inputs, result, model version, and caveats.
- Monitoring/logs page with ingestion/source status.
- Model insights page with metrics and feature importance/SHAP for grade 5.

Use `st.cache_data` for API/data results and `st.cache_resource` for reusable clients/resources where appropriate.

## Docker, CI, And MLOps Rules

- `docker-compose.yml` stays at repo root and should become the main reproducible launch path.
- Containers talk through service names such as `db`, `redis`, `api`, and `mlflow`, not `localhost`.
- `.env`, raw dumps, DB dumps, and model artifacts must not be committed.
- CI should run lint and tests.
- Redis must eventually have a real cache/read-path use case if kept for grade 5.
- MLflow must track real experiments, params, metrics, and artifacts if claimed.

## Review Checklist For Future Phases

Before calling any future phase complete, answer these in docs or final notes:

1. What user story or grading requirement moved forward?
2. What data entered or changed?
3. What persistent DB state changed?
4. What tests prove the behavior?
5. What EDA/ML evidence was produced?
6. What API/UI behavior can a reviewer try?
7. What operational command/log proves it runs?
8. What caveat remains and what phase owns it?

If an answer is missing, the phase may still be useful, but it is not yet cleanly complete.
