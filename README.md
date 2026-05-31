# RealtyScope

RealtyScope — учебный data-service проект уровня grade 5 для оценки стоимости квартир в Москве.

## Статус Phase 1

На этом этапе репозиторий содержит только технический каркас проекта:

- общий Python-пакет `realtyscope`;
- минимальный FastAPI-сервис с endpoint `/health`;
- минимальное Streamlit-приложение;
- Docker Compose каркас для PostgreSQL, Redis, MLflow, API и Streamlit;
- lockfile `uv.lock` для воспроизводимой установки зависимостей;
- базовую настройку pytest, ruff, pre-commit и GitHub Actions CI.

Полный сбор данных с Domclick, обогащение через OpenStreetMap, Alembic-схема базы данных, обучение ML-модели, реальное использование Redis cache и полноценные страницы dashboard будут реализованы в следующих phase.

## Локальная установка

Рекомендуемый способ для проекта — `uv` в Ubuntu/WSL2. Он использует `pyproject.toml` и
зафиксированный `uv.lock`.

Из Ubuntu/WSL2:

```bash
cd /mnt/e/Магистр/2-курс/python/RealtyScope
UV_LINK_MODE=copy uv sync --frozen --extra dev --extra api --extra streamlit
```

Или из PowerShell через WSL:

```powershell
wsl -d Ubuntu -- bash -lc "cd /mnt/e/Магистр/2-курс/python/RealtyScope && UV_LINK_MODE=copy uv sync --frozen --extra dev --extra api --extra streamlit"
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
python -m pip install -e ".[dev,api,streamlit]"
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
