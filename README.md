# RealtyScope

RealtyScope — учебный data-service проект уровня Grade 5 для анализа и оценки стоимости квартир в Москве. Проект объединяет сбор данных Domclick/CIAN, хранение в PostgreSQL, FastAPI, Redis-кэширование, MLflow-артефакты моделей и Streamlit-панель для аналитики, оценки, мониторинга и демонстрации качества модели.

Текущий релиз находится в ветке `main` и был интегрирован через PR #3: `Final Grade-5 RealtyScope integration`.

## Текущий статус

Актуальная проверенная среда на 2026-06-26:

- Docker API: `http://127.0.0.1:8000`
- Streamlit UI: `http://127.0.0.1:8501`
- MLflow: `http://127.0.0.1:5000`
- Объявлений: `17,287`
- Источники: `14,851` Domclick, `2,436` CIAN
- Наблюдений: `45,764`
- Дней наблюдений: `23`, с `2026-05-14` по `2026-06-26`
- Покрытие OSM-признаками: `17,046 / 17,287` объявлений (`98.61%`)
- Активная модель: `selected_price_model_v1_non_leaky`, кандидат `random_forest`
- Строк в обучающем срезе модели: `17,046`
- Статус свежести модели: валидированный snapshot; модель не переобучается автоматически после каждого ежедневного сбора

Важное ограничение: модель цены является валидированным учебным appraisal snapshot, а не production-grade оценщиком. Появление новых строк в базе не означает, что ежедневное переобучение обязательно улучшит качество. Переобучение должно проходить только через workflow сравнения кандидатов и promotion gate.

## Архитектура

```text
Domclick / CIAN raw data
        |
        v
Ingestion and normalization
        |
        v
PostgreSQL + SQLAlchemy + Alembic
        |
        +--> FastAPI API
        |       +--> Redis cached reads
        |       +--> /data, /predict, /model/metadata, /monitoring/status
        |
        +--> ML feature snapshots
        |       +--> model training and MLflow evidence
        |
        +--> Streamlit dashboard
                +--> overview, data, valuation, map, trends, monitoring
```

Основные сервисы:

- `db`: PostgreSQL 16
- `redis`: кэш для read-path API
- `mlflow`: evidence по экспериментам и registry
- `api`: FastAPI backend
- `streamlit`: пользовательская dashboard-панель
- `trainer`: опциональный контейнер для обучения модели

## Структура репозитория

```text
services/api/             FastAPI сервис
services/streamlit/       Streamlit dashboard и static audit HTML builder
services/trainer/         Docker trainer entrypoint
src/realtyscope/          Основной пакет: ingestion, database, enrichment, ML, analysis
alembic/                  Миграции базы данных
docs/                     Документация курса, операций, demo, readiness и design
scripts/                  Runtime и audit helper scripts
tests/                    API, ML, ingestion, UI payload и Docker contract tests
data/                     Локальные data-директории, в основном ignored/generated
```

## API

Полезные endpoint после запуска Docker Compose:

- `GET /health`: проверка сервиса
- `GET /docs`: Swagger/OpenAPI
- `GET /data`: таблица объявлений с фильтрами и пагинацией
- `GET /listings`: кэшируемый read-path
- `POST /predict`: прогноз цены через активный model artifact
- `GET /model/metadata`: версия модели, метрики кандидатов, feature importance, freshness
- `GET /stats/data-quality`: статистика данных и наблюдений
- `GET /stats/observation-trend`: тренд по наблюдениям
- `GET /stats/exposure-forecast`: inferred lifecycle forecast по observation gaps
- `GET /monitoring/status`: статус сервисов, ingestion, модели, данных и последних логов

Примеры:

```bash
curl -sS "http://localhost:8000/data?limit=3&offset=0&rooms=2" | python -m json.tool
curl -sS "http://localhost:8000/model/metadata" | python -m json.tool
curl -sS "http://localhost:8000/monitoring/status" | python -m json.tool
```

## Dashboard

Streamlit dashboard включает:

- KPI overview
- фильтры и пагинацию Data Explorer
- таблицу объявлений
- форму оценки стоимости с выбором model candidate
- comparable listings и model feature drivers
- карту и районную аналитику
- readiness для observation trend
- readiness для inferred exposure forecast
- monitoring cards, service status, model freshness и recent logs

Локальный адрес:

```text
http://localhost:8501
```

## Data Pipeline

Ежедневный Domclick pipeline ограничен по объему и учитывает состояние источника:

- Chrome/CDP capture сохраняет raw payloads в `data/raw/domclick/YYYY-MM-DD-bulk`.
- Scheduled ingestion нормализует payloads и записывает успешные runs в PostgreSQL.
- Ошибки вроде QRATOR/CAPTCHA/source blocking записываются в `app_logs` и попадают в monitoring.
- Scheduler не должен делать агрессивные retry loops; source blocking нужно сначала проверить вручную.

Основные команды:

```powershell
python -m realtyscope.ingestion.domclick_chrome_capture --output-root data/raw/domclick --capture-runtime cdp --json
python -m realtyscope.ingestion.domclick_scheduled_batch run --source-path data/raw/domclick/2026-06-26-bulk --commit --json
python -m realtyscope.ingestion.domclick_scheduled_batch status --json
```

На Windows Scheduled Task должен указывать на:

```text
scripts/run_domclick_scheduled_batch.ps1
```

## Machine Learning

Текущий активный artifact:

```text
data/processed/models/phase5/selected_price_model_v1_non_leaky.joblib
```

Текущий выбранный кандидат:

- candidate: `random_forest`
- model version: `selected_price_model_v1_non_leaky`
- feature version: `ml_features_v2_non_leaky`
- training rows: `17,046`
- validation R2: `0.8653`
- MAE: примерно `7.64M` RUB
- candidate count: `3` (`random_forest`, `hist_gradient_boosting`, `ridge`)

Границы честных утверждений:

- Результат XGBoost не заявляется.
- Модель является validated snapshot, а не ежедневно автоматически переобучаемой моделью.
- В текущей базе `17,287` объявлений, поэтому UI показывает model freshness delta.
- Подтвержденные terminal sale/removal lifecycle rows отсутствуют; exposure forecast построен по inferred observation gaps.

## Локальная разработка

Установка зависимостей через `uv`:

```bash
python -m pip install uv==0.11.3
UV_LINK_MODE=copy uv sync --frozen --extra dev --extra data --extra api --extra streamlit
```

Проверки:

```bash
uv run ruff check .
uv run ruff format --check .
uv run pytest --cov=realtyscope --cov=services --cov-report=term-missing --cov-fail-under=50
```

Эквивалентные команды, использованные при release verification на Windows:

```powershell
python -m ruff check .
python -m ruff format --check .
python -m pytest -p no:cacheprovider --cov=realtyscope --cov=services --cov-report=term-missing --cov-fail-under=50
```

## Docker Compose

Для Docker Compose рекомендуется WSL2 или Linux host. Из корня репозитория:

```bash
docker compose -p realtyscope up --build -d
docker compose -p realtyscope ps
```

Ожидаемые сервисы:

- `db` healthy
- `redis` healthy
- `api` healthy на порту `8000`
- `streamlit` healthy на порту `8501`
- `mlflow` up на порту `5000`

Быстрый smoke test:

```bash
curl -sS http://localhost:8000/health
curl -sS http://localhost:8501/_stcore/health
curl -sS http://localhost:8000/monitoring/status | python -m json.tool
```

Для static audit против live Docker API при холодной базе лучше увеличить timeout:

```powershell
$env:API_BASE_URL="http://127.0.0.1:8000"
$env:STREAMLIT_API_TIMEOUT_SECONDS="30"
python scripts\playwright\generate_static_audit.py
Remove-Item Env:API_BASE_URL
Remove-Item Env:STREAMLIT_API_TIMEOUT_SECONDS
```

## Развертывание

Проект подготовлен к VPS deployment на Linux через Docker Compose. Для production-запуска добавлены отдельные файлы:

- `docker-compose.prod.yml`: изолированный production Compose без публичных портов PostgreSQL, Redis и MLflow.
- `.env.production.example`: шаблон переменных окружения для VPS.
- `deploy/caddy/Caddyfile`: reverse proxy для `realtyscope.bond` и `api.realtyscope.bond` с HTTPS.
- `docs/deployment/vps-digitalocean-cloudflare.ru.md`: пошаговый runbook для DigitalOcean, Termius, Cloudflare и nicnames.

Базовая production-команда после настройки `.env`:

```bash
docker compose -f docker-compose.prod.yml --env-file .env up --build -d
docker compose -f docker-compose.prod.yml --env-file .env ps
```

Рекомендуемый production flow:

1. Создать VPS с Docker, Docker Compose и firewall.
2. Настроить DNS records для домена и при необходимости отдельного API subdomain.
3. Склонировать репозиторий с GitHub на сервер.
4. Создать production `.env` на основе `.env.example`.
5. Использовать persistent Docker volumes для PostgreSQL, Redis, MLflow и model/data artifacts.
6. Запустить сервисы: `docker compose -p realtyscope up --build -d`.
7. Поставить Caddy, Nginx или Traefik перед Streamlit/API для HTTPS.
8. Проверить `/health`, `/_stcore/health`, `/monitoring/status` и dashboard rendering.
9. Настроить backup базы до включения scheduled ingestion.

Ограничения deployment:

- Нельзя коммитить реальные secrets.
- Domclick collection может блокироваться QRATOR/CAPTCHA; доступ к источнику является operational dependency.
- Windows Scheduled Task не переносится на VPS; на Linux нужен cron или systemd timer.
- Переобучение модели должно запускаться отдельным promotion workflow, а не автоматически после ingestion.

## Подтверждение качества

Последняя release verification после merge PR #3:

- GitHub Actions CI: passing для PR и push.
- Local merged-main pytest: `241 passed`, coverage `80.84%`, fail-under `50%`.
- Local `ruff check .`: passed.
- Local `ruff format --check .`: passed.
- Docker/WSL runtime smoke: API, Streamlit, PostgreSQL, Redis healthy; MLflow up.
- Static audit с Docker API и `STREAMLIT_API_TIMEOUT_SECONDS=30`: `api 17287 {'cian': 2436, 'domclick': 14851}`.

Дополнительные материалы:

- `docs/project-status.md`
- `docs/demo-script.md`
- `docs/demo-script.vi.md`
- `docs/final-readiness/2026-06-25-completion-audit.md`
- `docs/course-guidance/realtyscope-user-story-traceability.md`

## Лицензия и примечание о данных

Проект является учебным. При сборе и деплое real-estate данных необходимо соблюдать условия источников, robots policies, rate limits, требования OpenStreetMap attribution и применимые правила защиты данных.
