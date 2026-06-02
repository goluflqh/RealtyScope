# RealtyScope

RealtyScope — учебный data-service проект уровня grade 5 для оценки стоимости квартир в Москве.

## Статус Phase 4

Репозиторий содержит технический каркас проекта, начальный foundation для ingestion и базовый database/persistence слой:

- общий Python-пакет `realtyscope`;
- FastAPI-сервис с endpoint `/health`, DB-backed `/listings` и `/stats/data-quality`;
- Streamlit dashboard slice, который читает DB-backed FastAPI endpoints;
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
- Streamlit baseline prediction form that calls `/predict` and displays predicted price, model version, metrics summary, and caveat.

Текущие Phase 4 ограничения зафиксированы явно: live `osm_features` rows пока отсутствуют (`osm_rows_present=0`), observation history содержит один observation на listing, а baseline `baseline_ridge_v1` использует текущие listing/observation price fields, поэтому его почти идеальные метрики являются evidence для training/API contract, а не доказательством независимой production-оценки. MLflow logging поддержан, но live run ID равен `null`, если tracking URI/package не включены в локальном запуске.

Следующие phase должны убрать target-leakage из feature set, накопить повторные daily observations для trend/actual-vs-predicted анализа, добавить feature importance/SHAP, production model serving, реальное использование Redis cache и полноценные многостраничные dashboard views.

## Локальная установка

Проект использует явное разделение сред:

- Windows — рабочая среда для Codex Desktop, dedicated Chrome automation profile, browser-assisted Domclick capture и Python-команд через локальный `.venv`.
- WSL2 Ubuntu — Linux runtime для Docker Compose, PostgreSQL, Redis, MLflow и production-like проверок.
- VPS/production — Linux/Docker окружение, совместимое с WSL2, а не с global Python packages на Windows.

Подробные инструкции:

- English: `docs/development/local-environment.md`
- Tiếng Việt: `docs/development/local-environment.vi.md`

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
