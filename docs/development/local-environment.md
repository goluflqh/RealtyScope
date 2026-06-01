# RealtyScope Local Environment Contract

This document defines the development/runtime split for RealtyScope so the project does not depend on one developer machine's global Python packages.

## Environment Roles

- Windows is the workstation layer: Codex Desktop, Chrome profile, browser-assisted Domclick capture, editor, and day-to-day commands.
- Windows Python must use the project-local `.venv`; do not rely on `C:\Program Files\Python312\Lib\site-packages` or Anaconda for project commands.
- WSL2 Ubuntu is the local Linux runtime layer: Docker, PostgreSQL, Redis, MLflow, and production-like service checks.
- VPS/production should run from the same Linux/Docker assumptions as WSL2, not from Windows-specific global packages.

## Dependency Source Of Truth

- `pyproject.toml` declares direct project dependencies and optional extras.
- `uv.lock` locks the dependency graph for reproducible CI/Linux/agent installs.
- `.venv/` is local, OS-specific, ignored by git, and must be recreated per machine.
- Raw snapshots, DB dumps, `.env`, and generated runtime artifacts must not be committed.

## Windows Workstation Setup

Run from the repository root in PowerShell:

```powershell
python -m venv .venv
$env:PYTHONIOENCODING="utf-8"
$env:PIP_NO_COLOR="1"
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e ".[dev,data,api,streamlit]"
```

Use the local venv for Python commands:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m ruff format --check .
```

The `PYTHONIOENCODING=utf-8` setting avoids Windows console encoding failures when the repository path contains Cyrillic characters.

## WSL2 Docker Runtime

Run PostgreSQL through WSL2 Docker Compose:

```powershell
wsl -d Ubuntu -- bash -lc "cd /mnt/e/Магистр/2-курс/python/RealtyScope && docker compose up -d db"
```

Verify the database container:

```powershell
wsl -d Ubuntu -- bash -lc "cd /mnt/e/Магистр/2-курс/python/RealtyScope && docker compose ps db"
```

Use Windows `.venv` commands against the WSL2 PostgreSQL port on `localhost:5432`:

```powershell
$env:DATABASE_URL="postgresql+psycopg://realtyscope:realtyscope@localhost:5432/realtyscope"
.\.venv\Scripts\python.exe -m alembic upgrade head
```

## Locked CI/Linux Setup

CI and Linux/VPS environments should install from `uv.lock`:

```bash
python -m pip install uv==0.11.3
UV_LINK_MODE=copy uv sync --frozen --extra dev --extra data --extra api --extra streamlit
uv run pytest -q
uv run ruff check .
uv run ruff format --check .
```

Do not reuse a Windows `.venv` from WSL or Linux. Create a separate environment on each OS.

## Phase 3.5 Verification Pattern

```powershell
$env:DATABASE_URL="postgresql+psycopg://realtyscope:realtyscope@localhost:5432/realtyscope_phase35_verify"
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m realtyscope.database.real_data_ingestion --source-type domclick_snapshot_dir --source-path data/raw/domclick/2026-06-01 --inspect-only --json
.\.venv\Scripts\python.exe -m realtyscope.database.real_data_ingestion --source-type domclick_snapshot_dir --source-path data/raw/domclick/2026-06-01 --database-url $env:DATABASE_URL --json
.\.venv\Scripts\python.exe -m realtyscope.analysis.eda_summary --database-url $env:DATABASE_URL --output docs/data/phase3_5_eda_summary.vi.md --json
```
