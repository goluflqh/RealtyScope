# RealtyScope

RealtyScope — учебный data-service проект уровня grade 5 для оценки стоимости квартир в Москве.

## Current Course-Readiness Status

Phase 6 and Phase 7 have been merged into `main`; the phase branches remain preserved as milestone branches. For the current readiness board, requirement checklist, Domclick schedule note, and future polish guidance, see `docs/project-status.md`.

Phase 9 non-UI readiness has been integrated into `main` through PR `#1` and squash merge commit `5a2ae2a`, with GitHub Actions `ci` run `27856530977` passing after merge. The merged scope covers scheduler validation, data/backend checks, MLOps model promotion workflow, selected-model API/monitoring, and docs/CI/demo gates. The recovered Russian UI remains a separate deferred workstream at `ui/recovered-real-data-dashboard-20260620`; do not use the rejected `ui/realtyscope-ultimate-redesign` branch as the target.

The repository currently contains a tested course-ready foundation:

- общий Python-пакет `realtyscope`;
- FastAPI-сервис с endpoint `/health`, DB-backed `/listings`, assignment-compatible `/data`, `/predict`, `/model/metadata`, `/monitoring/status` и фильтрами для data explorer;
- Streamlit dashboard slice, который читает DB-backed FastAPI endpoints и показывает tabs, KPI, filters, paginated listing preview, reviewer charts/map, prediction, monitoring и model insights;
- Docker Compose каркас для PostgreSQL, Redis, MLflow, API и Streamlit;
- lockfile `uv.lock` для воспроизводимой установки зависимостей;
- базовую настройку pytest, ruff, pre-commit и GitHub Actions CI;
- typed ingestion contracts для raw, normalized и rejected listing records;
- CSV import contract для teammate data;
- replaceable Domclick snapshot parser с безопасными лимитами;
- local JSONL path для raw, normalized и rejected ingestion artifacts;
- SQLAlchemy 2.0 models для sources, ingestion runs, raw listings, canonical listings, source links, rejected rows и app logs;
- Alembic initial migration для database foundation;
- persistence из Phase 2 `IngestionBatch` в database tables;
- sample ingestion command `python -m realtyscope.database.sample_ingestion --json` для проверки database write path;
- Phase 3.5 Domclick collector command для RU-accessible host: `python -m realtyscope.ingestion.domclick_snapshot_collector --url-file <urls.txt> --output-root data/raw/domclick --json`;
- Phase 3.6 Chrome-assisted Domclick SSR capture command для daily Moscow sale-apartment snapshots: `python -m realtyscope.ingestion.domclick_chrome_capture --output-root data/raw/domclick --capture-runtime cdp --json`;
- bounded scheduled Domclick batch command for safe inspect/commit runs: `python -m realtyscope.ingestion.domclick_scheduled_batch run --source-path <snapshot-dir> --commit --json`;
- Domclick ingestion status command: `python -m realtyscope.ingestion.domclick_scheduled_batch status --json`;
- Phase 3.5 Domclick snapshot inspect command без записи в database: `python -m realtyscope.database.real_data_ingestion --source-type domclick_snapshot_dir --source-path <snapshot-dir> --inspect-only --json`;
- Phase 3.5 Domclick snapshot ingestion command для реальных JSON/HTML snapshots или дневной папки `data/raw/domclick/YYYY-MM-DD`: `python -m realtyscope.database.real_data_ingestion --source-type domclick_snapshot_dir --source-path <snapshot-dir> --json`;
- controlled Domclick access probe, который проверяет robots rules, sitemap index и QRATOR challenge без обхода disallowed `/search`;
- первые backend read endpoints, которые читают persisted database rows, а не mock data;
- cleaning/ML-readiness flags и audit trail для rejected rows;
- Phase 3.5 EDA summary command, который читает persisted database tables и пишет markdown/JSON: `python -m realtyscope.analysis.eda_summary --database-url <url> --output docs/data/phase3_5_eda_summary.vi.md --json`;
- English technical plan и полноценный Vietnamese companion с диакритикой для Phase 3;
- Phase 4 data-readiness audit and observation-based EDA on persisted real Domclick rows: `docs/data/phase4-data-readiness.vi.md`, `docs/data/phase4-eda-observations.md`;
- OpenStreetMap enrichment foundation with local/fixture feature computation, `osm_features` persistence, and explicit OpenStreetMap attribution rules: `docs/data/osm-enrichment.md`;
- deterministic ML feature snapshot command: `python -m realtyscope.ml.features --json`;
- baseline training command with joblib artifact output: `python -m realtyscope.ml.train --output-dir data/processed/models/phase4 --json`;
- Phase 4 baseline model evidence in `docs/ml/phase4-baseline-model.md` and `docs/ml/phase4-baseline-model.vi.md`;
- FastAPI `/predict` contract with Pydantic validation and model artifact loading from `ACTIVE_MODEL_ARTIFACT_PATH`;
- Streamlit baseline prediction form that calls `/predict` and displays predicted price, model version, metrics summary, and caveat;
- Phase 7.2 API/Streamlit filters for price range, area range, rooms, source, and address search;
- Phase 7 reviewer polish: filters, tabbed navigation, paginated Data Explorer, reviewer charts/map, demo runbook, and visible last-successful-collection monitoring.

Important caveat: RealtyScope now has non-leaky baseline evidence and a real Docker-backed MLflow registration path, but the model is still a baseline appraisal model rather than a final production estimator. Forecast-vs-actual conclusions still need richer repeated observations per listing, and deeper operations evidence would benefit from more consistent runtime app logs.

Phase 7 completed the final course-readiness polish: status/docs, fresh runtime and data checks, safe Docker/storage cleanup guidance, Streamlit data explorer filters and reviewer visuals, demo script, and a documented decision to keep Domclick ingestion daily for now.

## Phase 5-6 updates

Phase 5 adds the hardening layer on top of the Phase 4 baseline:

- scheduled ingestion now stores deliberate daily observation evidence even when raw payloads are reused;
- bounded live OSM enrichment has written real `osm_features` rows for local evidence;
- `ml_features_v2_non_leaky` removes latest-price leakage and trains `baseline_ridge_v2_non_leaky` with grouped validation by `listing_id`;
- FastAPI exposes `/model/metadata` and `/monitoring/status` in addition to `/predict`, `/listings`, and `/stats/data-quality`;
- Streamlit now has overview, prediction, monitoring, and model-insight sections backed by the API client;
- default `ACTIVE_MODEL_ARTIFACT_PATH` points to `data/processed/models/phase5/baseline_ridge_v2_non_leaky.joblib`.

Phase 6 adds production-like MLOps and runtime evidence:

- Docker Compose builds from scoped in-repo contexts instead of the repository root;
- Redis backs the `/listings` and `/data` read path;
- the trainer service logs a real MLflow run and registers `realtyscope-price-model` version `3`;
- GitHub Actions is green for the Phase 6 base at `30bce998...` and for `main` after the Phase 7 merge.

Phase 7.2-7.4 adds reviewer-facing readiness polish:

- `/data` and `/listings` support filters for price range, area range, rooms, source, and address search;
- Streamlit exposes those filters in the sidebar and adds tabbed sections for overview, data explorer, visuals, prediction, and monitoring/model evidence;
- Streamlit renders reviewer visuals for price distribution, median price by rooms, and a coordinate map with OpenStreetMap attribution;
- Data Explorer has a simple `Page` control backed by real `/data` offset pagination;
- Phase 7 was fast-forward merged into `main`; current CI/runtime evidence is tracked in `docs/project-status.md`.

Generated model artifacts and runtime logs remain under ignored `data/processed/`. See `docs/ml/phase5-non-leaky-model.md`, `docs/ml/phase6-mlflow-registration.md`, and `docs/project-status.md` for metrics, MLOps evidence, and current caveats.

## Локальная установка

Проект использует явное разделение сред:

- Windows — рабочая среда для Codex Desktop, dedicated Chrome automation profile, browser-assisted Domclick capture и Python-команд через локальный `.venv`.
- WSL2 Ubuntu — Linux runtime для Docker Compose, PostgreSQL, Redis, MLflow и production-like проверок.
- VPS/production — Linux/Docker окружение, совместимое с WSL2, а не с global Python packages на Windows.

Подробные инструкции:

- English setup/runtime: `docs/development/local-environment.md`
- Tiếng Việt setup/runtime: `docs/development/local-environment.vi.md`
- Demo script: `docs/demo-script.md`
- Kịch bản demo tiếng Việt: `docs/demo-script.vi.md`
- Runtime proof and cleanup: the local environment docs include Redis cache verification plus safe Docker/storage cleanup guidance.

Создать локальный Windows `.venv` из PowerShell:

```powershell
python -m venv .venv
$env:PYTHONIOENCODING="utf-8"
$env:PIP_NO_COLOR="1"
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e ".[dev,data,api,streamlit]"
```

Запускать Python-команды только через `.venv`:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m ruff format --check .
```

Запустить PostgreSQL через WSL2 Docker Compose:

```powershell
wsl -d Ubuntu -- bash -lc "cd /mnt/e/Магистр/2-курс/python/RealtyScope && docker compose up -d db"
```

CI/Linux/VPS должны устанавливаться из `uv.lock`:

```bash
python -m pip install uv==0.11.3
UV_LINK_MODE=copy uv sync --frozen --extra dev --extra data --extra api --extra streamlit
```

Полезные локальные URL после запуска сервисов:

- FastAPI health: http://localhost:8000/health
- FastAPI Swagger: http://localhost:8000/docs
- Streamlit: http://localhost:8501
- MLflow: http://localhost:5000

## Атрибуция OpenStreetMap

В будущих страницах dashboard, где используются карты или данные, полученные из OpenStreetMap, должна быть видимая атрибуция OpenStreetMap.
