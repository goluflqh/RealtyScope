# RealtyScope Phase 1 Scaffold Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Khởi tạo nền tảng repo cho RealtyScope: Python tooling, package skeleton, FastAPI/Streamlit minimal apps, Docker Compose skeleton, CI và docs đủ để các phase dữ liệu/ML/API/UI sau này phát triển có kiểm soát.

**Architecture:** Phase 1 tạo monorepo Python với package chung `realtyscope`, các service tách trong `services/`, tests trong `tests/`, và Docker Compose chạy Postgres, Redis, MLflow, API, Streamlit ở mức skeleton. Plan này không triển khai parser Domclick, OSM enrichment, database schema thật, ML training thật, hay dashboard thật; các phần đó nằm ở phase sau.

**Tech Stack:** Python 3.11, pytest, ruff, pre-commit, FastAPI, Uvicorn, Streamlit, Docker Compose, PostgreSQL, Redis, MLflow.

---

## Scope check

Spec Phase 0 bao phủ nhiều subsystem độc lập: data ingestion, DB/Alembic, OSM enrichment, ML/MLflow, API, Streamlit, Redis, tests/CI. Vì vậy implementation được chia theo phase. Plan này chỉ cover **Phase 1: repo/scaffold/devops nền tảng**.

## Language and GitHub policy

- `README.md` trong Phase 1 phải viết bằng tiếng Nga để giảng viên dễ đọc khi chấm trên GitHub.
- Internal files trong `docs/superpowers/` có thể dùng tiếng Việt vì đây là tài liệu làm việc giữa user và agent.
- Code, package names, module names, endpoint names, table names và config keys dùng tiếng Anh kỹ thuật.
- Commit messages dùng English Conventional Commits, ví dụ `chore: initialize repository hygiene`.
- Branch cho Phase 1 là `phase1-scaffold`. Không dùng branch public kiểu `codex/*`, `openai/*`, hoặc PR/review public có dấu Codex/OpenAI nếu không cần.

Các phase sau sẽ có plan riêng:

- Phase 2: Domclick collector, teammate import contract, raw/normalized data path.
- Phase 3: PostgreSQL schema, Alembic migrations, cleaning, OSM enrichment, EDA.
- Phase 4: ML training, MLflow tracking, feature snapshots, model registry.
- Phase 5: FastAPI production endpoints, Redis cache, Streamlit dashboard, monitoring/logs.
- Phase 6: tests hardening, CI polish, README, screenshots, defense prep.

## Repo root

All paths are relative to:

```text
E:\Магистр\2-курс\python\RealtyScope
```

## File structure for Phase 1

Create or modify these files only during Phase 1 execution:

```text
.gitignore
.env.example
.pre-commit-config.yaml
pyproject.toml
README.md
docker-compose.yml
.github/workflows/ci.yml
src/realtyscope/__init__.py
src/realtyscope/config.py
services/__init__.py
services/api/__init__.py
services/api/app/__init__.py
services/api/app/main.py
services/api/Dockerfile
services/streamlit/__init__.py
services/streamlit/app.py
services/streamlit/Dockerfile
services/mlflow/Dockerfile
tests/test_package_import.py
tests/test_config.py
tests/test_api_health.py
tests/test_streamlit_scaffold.py
```

No implementation files outside this list should be created in Phase 1.

---

### Task 1: Initialize git and base repository hygiene

**Files:**
- Create: `.gitignore`
- Create: `.env.example`

- [ ] **Step 1: Initialize git repository and Phase 1 branch**

Run from repo root:

```powershell
git init
git switch -c phase1-scaffold
```

Expected: commands succeed, create `.git/`, and switch to branch `phase1-scaffold`. Do not create a branch named `codex/*` or `openai/*`.

- [ ] **Step 1.1: Verify Git author identity**

Run:

```powershell
git config user.name
git config user.email
git config --global user.name
git config --global user.email
```

Expected: at least the local or global Git config shows the user's real Git identity. If not, stop and ask the user for the correct `user.name` and `user.email` before committing.

- [ ] **Step 2: Create `.gitignore`**

Create `.gitignore` with this content:

```gitignore
# Python
__pycache__/
*.py[cod]
*.pyo
.pytest_cache/
.ruff_cache/
.mypy_cache/
.coverage
coverage.xml
htmlcov/

# Virtual environments
.venv/
venv/
.env
.env.*
!.env.example

# Data and artifacts
data/raw/
data/processed/
data/cache/
artifacts/
mlruns/

# Jupyter
.ipynb_checkpoints/

# IDE / OS
.vscode/
.idea/
.DS_Store
Thumbs.db

# Docker / local runtime
postgres_data/
redis_data/
```

- [ ] **Step 3: Create `.env.example`**

Create `.env.example` with this content:

```dotenv
APP_ENV=local
PROJECT_NAME=RealtyScope
LOG_LEVEL=INFO

POSTGRES_USER=realtyscope
POSTGRES_PASSWORD=realtyscope
POSTGRES_DB=realtyscope
POSTGRES_HOST=db
POSTGRES_PORT=5432
DATABASE_URL=postgresql+psycopg://realtyscope:realtyscope@db:5432/realtyscope

REDIS_HOST=redis
REDIS_PORT=6379
REDIS_URL=redis://redis:6379/0

MLFLOW_TRACKING_URI=http://mlflow:5000
ACTIVE_MODEL_NAME=realtyscope-price-model
```

- [ ] **Step 4: Verify base files exist**

Run:

```powershell
Test-Path .gitignore; Test-Path .env.example; Test-Path .git
```

Expected output contains three `True` lines.

- [ ] **Step 5: Commit base repository hygiene**

Run:

```powershell
git add .gitignore .env.example
git commit -m "chore: initialize repository hygiene"
```

Expected: commit succeeds with 2 files changed.

---

### Task 2: Add Python tooling and importable package skeleton

**Files:**
- Create: `pyproject.toml`
- Create: `src/realtyscope/__init__.py`
- Create: `tests/test_package_import.py`

- [ ] **Step 1: Create `pyproject.toml`**

Create `pyproject.toml` with this content:

```toml
[build-system]
requires = ["setuptools>=69", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "realtyscope"
version = "0.1.0"
description = "RealtyScope grade-5 data service for Moscow apartment sale-price prediction"
requires-python = ">=3.11"
dependencies = [
  "pydantic>=2.7",
  "pydantic-settings>=2.2",
]

[project.optional-dependencies]
api = [
  "fastapi>=0.110",
  "uvicorn[standard]>=0.29",
  "redis>=5.0",
]
streamlit = [
  "streamlit>=1.35",
  "requests>=2.31",
]
data = [
  "sqlalchemy>=2.0",
  "psycopg[binary]>=3.1",
  "alembic>=1.13",
  "pandas>=2.2",
]
ml = [
  "scikit-learn>=1.4",
  "mlflow>=2.12",
  "joblib>=1.4",
]
dev = [
  "httpx>=0.27",
  "pytest>=8.2",
  "pytest-cov>=5.0",
  "ruff>=0.4",
  "pre-commit>=3.7",
]

[tool.setuptools.packages.find]
where = ["src"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = [".", "src"]
addopts = "-q"

[tool.ruff]
line-length = 100
target-version = "py311"
src = ["src", "services", "tests"]

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B", "SIM"]
ignore = []

[tool.ruff.format]
quote-style = "double"
indent-style = "space"
line-ending = "auto"
```

- [ ] **Step 2: Create package skeleton**

Create `src/realtyscope/__init__.py` with this content:

```python
"""Shared package for the RealtyScope project."""

__version__ = "0.1.0"
```

- [ ] **Step 3: Write import test**

Create `tests/test_package_import.py` with this content:

```python
from realtyscope import __version__


def test_package_version_is_defined() -> None:
    assert __version__ == "0.1.0"
```

- [ ] **Step 4: Install package in editable mode with dev dependencies**

Run:

```powershell
python -m pip install -e ".[dev]"
```

Expected: command succeeds and installs `realtyscope` in editable mode.

- [ ] **Step 5: Run package import test**

Run:

```powershell
python -m pytest tests/test_package_import.py -q
```

Expected output contains `1 passed`.

- [ ] **Step 6: Commit Python tooling and package skeleton**

Run:

```powershell
git add pyproject.toml src/realtyscope/__init__.py tests/test_package_import.py
git commit -m "chore: add python tooling skeleton"
```

Expected: commit succeeds with 3 files changed.

---

### Task 3: Add shared settings module

**Files:**
- Create: `src/realtyscope/config.py`
- Create: `tests/test_config.py`

- [ ] **Step 1: Write failing settings tests**

Create `tests/test_config.py` with this content:

```python
from realtyscope.config import Settings


def test_settings_have_safe_defaults() -> None:
    settings = Settings()

    assert settings.project_name == "RealtyScope"
    assert settings.app_env == "local"
    assert settings.postgres_host == "localhost"
    assert settings.redis_host == "localhost"
    assert settings.mlflow_tracking_uri == "http://localhost:5000"


def test_database_url_uses_localhost_by_default() -> None:
    settings = Settings()

    assert settings.database_url == (
        "postgresql+psycopg://realtyscope:realtyscope@localhost:5432/realtyscope"
    )
```

- [ ] **Step 2: Run tests to verify they fail before implementation**

Run:

```powershell
python -m pytest tests/test_config.py -q
```

Expected: FAIL because `realtyscope.config` does not exist.

- [ ] **Step 3: Implement `src/realtyscope/config.py`**

Create `src/realtyscope/config.py` with this content:

```python
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings shared by RealtyScope services."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = Field(default="local", alias="APP_ENV")
    project_name: str = Field(default="RealtyScope", alias="PROJECT_NAME")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    postgres_user: str = Field(default="realtyscope", alias="POSTGRES_USER")
    postgres_password: str = Field(default="realtyscope", alias="POSTGRES_PASSWORD")
    postgres_db: str = Field(default="realtyscope", alias="POSTGRES_DB")
    postgres_host: str = Field(default="localhost", alias="POSTGRES_HOST")
    postgres_port: int = Field(default=5432, alias="POSTGRES_PORT")

    redis_host: str = Field(default="localhost", alias="REDIS_HOST")
    redis_port: int = Field(default=6379, alias="REDIS_PORT")
    mlflow_tracking_uri: str = Field(
        default="http://localhost:5000",
        alias="MLFLOW_TRACKING_URI",
    )
    active_model_name: str = Field(default="realtyscope-price-model", alias="ACTIVE_MODEL_NAME")

    @property
    def database_url(self) -> str:
        return (
            "postgresql+psycopg://"
            f"{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def redis_url(self) -> str:
        return f"redis://{self.redis_host}:{self.redis_port}/0"


@lru_cache
def get_settings() -> Settings:
    return Settings()
```

- [ ] **Step 4: Run settings tests**

Run:

```powershell
python -m pytest tests/test_config.py -q
```

Expected output contains `2 passed`.

- [ ] **Step 5: Run package tests together**

Run:

```powershell
python -m pytest tests/test_package_import.py tests/test_config.py -q
```

Expected output contains `3 passed`.

- [ ] **Step 6: Commit shared settings**

Run:

```powershell
git add src/realtyscope/config.py tests/test_config.py
git commit -m "feat: add shared settings"
```

Expected: commit succeeds with 2 files changed.

---

### Task 4: Add minimal FastAPI health service

**Files:**
- Create: `services/__init__.py`
- Create: `services/api/__init__.py`
- Create: `services/api/app/__init__.py`
- Create: `services/api/app/main.py`
- Create: `tests/test_api_health.py`

- [ ] **Step 1: Create service package markers**

Create these empty files:

```text
services/__init__.py
services/api/__init__.py
services/api/app/__init__.py
```

- [ ] **Step 2: Write failing API health tests**

Create `tests/test_api_health.py` with this content:

```python
from fastapi.testclient import TestClient

from services.api.app.main import app


def test_health_endpoint_returns_service_status() -> None:
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "service": "realtyscope-api",
        "status": "ok",
        "project": "RealtyScope",
        "environment": "local",
    }
```

- [ ] **Step 3: Run API test to verify it fails before implementation**

Run:

```powershell
python -m pytest tests/test_api_health.py -q
```

Expected: FAIL because `services.api.app.main` does not exist.

- [ ] **Step 4: Implement minimal API app**

Create `services/api/app/main.py` with this content:

```python
from fastapi import FastAPI

from realtyscope.config import get_settings

app = FastAPI(
    title="RealtyScope API",
    version="0.1.0",
    description="API skeleton for the RealtyScope grade-5 real estate data service.",
)


@app.get("/health")
def health() -> dict[str, str]:
    settings = get_settings()
    return {
        "service": "realtyscope-api",
        "status": "ok",
        "project": settings.project_name,
        "environment": settings.app_env,
    }
```

- [ ] **Step 5: Run API test**

Run:

```powershell
python -m pytest tests/test_api_health.py -q
```

Expected output contains `1 passed`.

- [ ] **Step 6: Run all tests so far**

Run:

```powershell
python -m pytest -q
```

Expected output contains `4 passed`.

- [ ] **Step 7: Commit FastAPI skeleton**

Run:

```powershell
git add services tests/test_api_health.py
git commit -m "feat: add api health skeleton"
```

Expected: commit succeeds with service package files and API test.

---

### Task 5: Add minimal Streamlit skeleton

**Files:**
- Create: `services/streamlit/__init__.py`
- Create: `services/streamlit/app.py`
- Create: `tests/test_streamlit_scaffold.py`

- [ ] **Step 1: Write Streamlit scaffold test**

Create `tests/test_streamlit_scaffold.py` with this content:

```python
from pathlib import Path


STREAMLIT_APP = Path("services/streamlit/app.py")


def test_streamlit_app_file_exists() -> None:
    assert STREAMLIT_APP.exists()


def test_streamlit_app_declares_realtyscope_title() -> None:
    content = STREAMLIT_APP.read_text(encoding="utf-8")

    assert "RealtyScope" in content
    assert "st.set_page_config" in content
    assert "Phase 1 scaffold" in content
```

- [ ] **Step 2: Run test to verify it fails before app file exists**

Run:

```powershell
python -m pytest tests/test_streamlit_scaffold.py -q
```

Expected: FAIL because `services/streamlit/app.py` does not exist.

- [ ] **Step 3: Create Streamlit app skeleton**

Create `services/streamlit/__init__.py` as an empty file.

Create `services/streamlit/app.py` with this content:

```python
import streamlit as st

st.set_page_config(page_title="RealtyScope", page_icon="🏠", layout="wide")

st.title("RealtyScope")
st.caption("Phase 1 scaffold")

st.write(
    "RealtyScope will estimate Moscow apartment sale prices using Domclick listings, "
    "OpenStreetMap enrichment, FastAPI, MLflow, Redis, and PostgreSQL."
)

st.info("The full dashboard pages will be implemented after ingestion, database, and model phases.")
```

- [ ] **Step 4: Run Streamlit scaffold tests**

Run:

```powershell
python -m pytest tests/test_streamlit_scaffold.py -q
```

Expected output contains `2 passed`.

- [ ] **Step 5: Run all tests so far**

Run:

```powershell
python -m pytest -q
```

Expected output contains `6 passed`.

- [ ] **Step 6: Commit Streamlit skeleton**

Run:

```powershell
git add services/streamlit tests/test_streamlit_scaffold.py
git commit -m "feat: add streamlit scaffold"
```

Expected: commit succeeds with Streamlit scaffold and tests.

---

### Task 6: Add Docker Compose skeleton

**Files:**
- Create: `services/api/Dockerfile`
- Create: `services/streamlit/Dockerfile`
- Create: `services/mlflow/Dockerfile`
- Create: `docker-compose.yml`

- [ ] **Step 1: Create API Dockerfile**

Create `services/api/Dockerfile` with this content:

```dockerfile
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir -e ".[api]"

COPY services/api/app ./app

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 2: Create Streamlit Dockerfile**

Create `services/streamlit/Dockerfile` with this content:

```dockerfile
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir -e ".[streamlit]"

COPY services/streamlit/app.py ./app.py

EXPOSE 8501
CMD ["streamlit", "run", "app.py", "--server.address=0.0.0.0", "--server.port=8501"]
```

- [ ] **Step 3: Create MLflow Dockerfile**

Create `services/mlflow/Dockerfile` with this content:

```dockerfile
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /mlflow

RUN pip install --no-cache-dir "mlflow>=2.12,<3"

EXPOSE 5000
CMD ["mlflow", "server", "--host", "0.0.0.0", "--port", "5000", "--backend-store-uri", "sqlite:////mlflow/mlflow.db", "--default-artifact-root", "/mlflow/artifacts"]
```

- [ ] **Step 4: Create Docker Compose file**

Create `docker-compose.yml` with this content:

```yaml
services:
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: ${POSTGRES_USER:-realtyscope}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-realtyscope}
      POSTGRES_DB: ${POSTGRES_DB:-realtyscope}
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U $${POSTGRES_USER} -d $${POSTGRES_DB}"]
      interval: 10s
      timeout: 5s
      retries: 5
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
    volumes:
      - redis_data:/data

  mlflow:
    build:
      context: .
      dockerfile: services/mlflow/Dockerfile
    ports:
      - "5000:5000"
    volumes:
      - mlflow_data:/mlflow

  api:
    build:
      context: .
      dockerfile: services/api/Dockerfile
    environment:
      APP_ENV: docker
      PROJECT_NAME: RealtyScope
      POSTGRES_HOST: db
      REDIS_HOST: redis
      MLFLOW_TRACKING_URI: http://mlflow:5000
    ports:
      - "8000:8000"
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
      mlflow:
        condition: service_started
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/health').read()"]
      interval: 10s
      timeout: 5s
      retries: 5

  streamlit:
    build:
      context: .
      dockerfile: services/streamlit/Dockerfile
    environment:
      API_BASE_URL: http://api:8000
    ports:
      - "8501:8501"
    depends_on:
      api:
        condition: service_healthy

volumes:
  postgres_data:
  redis_data:
  mlflow_data:
```

- [ ] **Step 5: Verify Compose file parses**

Run:

```powershell
docker compose config
```

Expected: command exits successfully and prints normalized compose configuration.

- [ ] **Step 6: Build and start scaffold services**

Run:

```powershell
docker compose up --build -d
```

Expected: containers for `db`, `redis`, `mlflow`, `api`, and `streamlit` start.

- [ ] **Step 7: Verify API health from host**

Run:

```powershell
python -c "import urllib.request; print(urllib.request.urlopen('http://localhost:8000/health').read().decode())"
```

Expected output contains `"status":"ok"` or JSON with `status` equal to `ok`.

- [ ] **Step 8: Stop services**

Run:

```powershell
docker compose down
```

Expected: containers stop; named volumes remain.

- [ ] **Step 9: Commit Docker skeleton**

Run:

```powershell
git add docker-compose.yml services/api/Dockerfile services/streamlit/Dockerfile services/mlflow/Dockerfile
git commit -m "chore: add docker compose skeleton"
```

Expected: commit succeeds with Docker skeleton files.

---

### Task 7: Add linting, pre-commit, and CI

**Files:**
- Create: `.pre-commit-config.yaml`
- Create: `.github/workflows/ci.yml`

- [ ] **Step 1: Create pre-commit config**

Create `.pre-commit-config.yaml` with this content:

```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.4.10
    hooks:
      - id: ruff
        args: ["--fix"]
      - id: ruff-format
```

- [ ] **Step 2: Create GitHub Actions workflow**

Create `.github/workflows/ci.yml` with this content:

```yaml
name: ci

on:
  push:
  pull_request:

jobs:
  lint-test:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install dependencies
        run: python -m pip install -e ".[dev,api,streamlit]"

      - name: Ruff check
        run: python -m ruff check .

      - name: Ruff format check
        run: python -m ruff format --check .

      - name: Pytest
        run: python -m pytest --cov=realtyscope --cov=services --cov-report=term-missing
```

- [ ] **Step 3: Run ruff check locally**

Run:

```powershell
python -m ruff check .
```

Expected output contains `All checks passed!`.

- [ ] **Step 4: Run ruff format check locally**

Run:

```powershell
python -m ruff format --check .
```

Expected output indicates files are already formatted.

- [ ] **Step 5: Run tests with coverage locally**

Run:

```powershell
python -m pytest --cov=realtyscope --cov=services --cov-report=term-missing
```

Expected: tests pass and coverage report is printed.

- [ ] **Step 6: Commit linting and CI**

Run:

```powershell
git add .pre-commit-config.yaml .github/workflows/ci.yml
git commit -m "ci: add lint and test workflow"
```

Expected: commit succeeds with pre-commit and CI files.

---

### Task 8: Add Phase 1 README

**Files:**
- Create: `README.md`

- [ ] **Step 1: Create README**

Create `README.md` with this content:

```markdown
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
```

- [ ] **Step 2: Verify README mentions required Phase 1 services**

Run:

```powershell
python -c "from pathlib import Path; content = Path('README.md').read_text(encoding='utf-8'); required = ['учебный data-service', 'Статус Phase 1', 'FastAPI', 'Streamlit', 'PostgreSQL', 'Redis', 'MLflow', 'OpenStreetMap']; missing = [item for item in required if item not in content]; assert not missing, missing; print('README scaffold check passed')"
```

Expected output contains `README scaffold check passed`.

- [ ] **Step 3: Commit README**

Run:

```powershell
git add README.md
git commit -m "docs: add phase 1 README"
```

Expected: commit succeeds with README.

---

### Task 9: Final Phase 1 verification

**Files:**
- Modify: none expected.

- [ ] **Step 1: Run all local checks**

Run:

```powershell
python -m ruff check .
python -m ruff format --check .
python -m pytest --cov=realtyscope --cov=services --cov-report=term-missing
```

Expected: ruff passes, format check passes, pytest passes.

- [ ] **Step 2: Verify Docker Compose config**

Run:

```powershell
docker compose config
```

Expected: Docker Compose prints valid normalized configuration.

- [ ] **Step 3: Verify scaffold services boot**

Run:

```powershell
docker compose up --build -d
python -c "import urllib.request; print(urllib.request.urlopen('http://localhost:8000/health').read().decode())"
docker compose down
```

Expected: health response contains `status` equal to `ok`, then Compose services stop cleanly.

- [ ] **Step 4: Inspect git status**

Run:

```powershell
git status --short
```

Expected: no output, meaning the working tree is clean.

- [ ] **Step 5: Record Phase 1 completion evidence**

Add a short checkpoint in project memory with these facts:

```text
RealtyScope Phase 1 scaffold completed: git repo initialized, Python tooling/package skeleton, FastAPI health endpoint, Streamlit skeleton, Docker Compose skeleton, CI/pre-commit, README, and local verification commands passed. No data ingestion, DB schema, ML training, or production UI implemented yet.
```

Expected: memory write succeeds.

---

## Self-review notes

Spec coverage for Phase 1:

- Reproducibility groundwork: covered by Docker Compose skeleton and verification commands.
- Architecture groundwork: covered by service folders and Docker skeleton.
- API groundwork: covered by FastAPI `/health` skeleton.
- Streamlit groundwork: covered by Streamlit skeleton.
- Redis/DB/MLflow groundwork: covered by Compose services.
- Testing/CI groundwork: covered by pytest, ruff, pre-commit, GitHub Actions.
- Out of Phase 1: Domclick parser, OSM enrichment, teammate import implementation, Alembic schema, ML training, Redis cache logic, production Streamlit pages.

No Phase 1 step should implement parser, database schema, Alembic migrations, model training, prediction endpoint, or dashboard business pages. Those belong to later phase plans.
