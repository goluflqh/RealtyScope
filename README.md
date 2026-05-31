# RealtyScope

RealtyScope — учебный data-service проект уровня grade 5 для оценки стоимости квартир в Москве.

## Статус Phase 1

На этом этапе репозиторий содержит только технический каркас проекта:

- общий Python-пакет `realtyscope`;
- минимальный FastAPI-сервис с endpoint `/health`;
- минимальное Streamlit-приложение;
- Docker Compose каркас для PostgreSQL, Redis, MLflow, API и Streamlit;
- базовую настройку pytest, ruff, pre-commit и GitHub Actions CI.

Полный сбор данных с Domclick, обогащение через OpenStreetMap, Alembic-схема базы данных, обучение ML-модели, реальное использование Redis cache и полноценные страницы dashboard будут реализованы в следующих phase.

## Локальная установка

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
