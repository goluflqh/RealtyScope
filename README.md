# RealtyScope

RealtyScope — учебный data-service проект уровня grade 5 для оценки стоимости квартир в Москве.

## Статус Phase 3

Репозиторий содержит технический каркас проекта, начальный foundation для ingestion и базовый database/persistence слой:

- общий Python-пакет `realtyscope`;
- минимальный FastAPI-сервис с endpoint `/health`;
- минимальное Streamlit-приложение;
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
- Phase 3.5 Domclick snapshot ingestion command для реальных JSON/HTML snapshots: `python -m realtyscope.database.real_data_ingestion --source-type domclick_html --source-path <snapshot> --json`;
- controlled Domclick access probe, который проверяет robots rules, sitemap index и QRATOR challenge без обхода disallowed `/search`;
- cleaning/ML-readiness flags и audit trail для rejected rows;
- Phase 3 EDA notebook skeleton, который читает persisted database tables;
- English technical plan и полноценный Vietnamese companion с диакритикой для Phase 3.

Реальный Domclick snapshot/live export, OpenStreetMap enrichment, EDA conclusions, обучение ML-модели, MLflow tracking, production FastAPI data/predict endpoints, реальное использование Redis cache и полноценные страницы dashboard будут реализованы в следующих phase.

## Локальная установка

Рекомендуемый способ для проекта — `uv` в Ubuntu/WSL2. Он использует `pyproject.toml` и
зафиксированный `uv.lock`.

Из Ubuntu/WSL2:

```bash
cd /mnt/e/Магистр/2-курс/python/RealtyScope
UV_LINK_MODE=copy uv sync --frozen --extra dev --extra data --extra api --extra streamlit
```

Или из PowerShell через WSL:

```powershell
wsl -d Ubuntu -- bash -lc "cd /mnt/e/Магистр/2-курс/python/RealtyScope && UV_LINK_MODE=copy uv sync --frozen --extra dev --extra data --extra api --extra streamlit"
```

Команды разработки через `uv`:

```bash
uv run pytest -q
uv run ruff check .
uv run ruff format --check .
```

Запасной способ через обычный Windows Python/pip, если нужно быстро проверить без WSL:

Установить зависимости для разработки:

```powershell
python -m pip install -e ".[dev,data,api,streamlit]"
```

Запустить тесты:

```powershell
python -m pytest -q
```

Проверить стиль кода:

```powershell
python -m ruff check .
python -m ruff format --check .
```

Запустить сервисы через Docker Compose:

```powershell
docker compose up --build
```

Полезные локальные URL:

- FastAPI health: http://localhost:8000/health
- FastAPI Swagger: http://localhost:8000/docs
- Streamlit: http://localhost:8501
- MLflow: http://localhost:5000

## Атрибуция OpenStreetMap

В будущих страницах dashboard, где используются карты или данные, полученные из OpenStreetMap, должна быть видимая атрибуция OpenStreetMap.
