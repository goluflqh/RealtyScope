# RealtyScope Local Environment Contract

This document defines the development/runtime split for RealtyScope so the project does not depend on one developer machine's global Python packages.

## Environment Roles

- Windows is the workstation layer: Codex Desktop, a dedicated Chrome automation profile for scheduled capture, browser-assisted Domclick capture, editor, and day-to-day commands.
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

Use WSL2 for Docker commands because Docker is not available in this workstation's PowerShell PATH.

Start the full demo/runtime stack from the repository root:

```powershell
wsl -d Ubuntu -- bash -lc "cd /mnt/e/Магистр/2-курс/python/RealtyScope && docker compose -p realtyscope up --build -d"
```

Check service status:

```powershell
wsl -d Ubuntu -- bash -lc "cd /mnt/e/Магистр/2-курс/python/RealtyScope && docker compose -p realtyscope ps"
```

Run PostgreSQL only when you need the database for migrations or ingestion checks without the full app stack:

```powershell
wsl -d Ubuntu -- bash -lc "cd /mnt/e/Магистр/2-курс/python/RealtyScope && docker compose -p realtyscope up -d db"
```

Use Windows `.venv` commands against the WSL2 PostgreSQL port on `localhost:5432`:

```powershell
$env:DATABASE_URL="postgresql+psycopg://realtyscope:realtyscope@localhost:5432/realtyscope"
.\.venv\Scripts\python.exe -m alembic upgrade head
```

### Redis Cache Runtime Proof

The API caches `/data` and `/listings` payloads in Redis for a short TTL. The current cache key format for the small data preview is `realtyscope:listings:v1:limit=3:offset=0`, with a 60-second TTL.

Populate the cache by calling the API read path:

```powershell
wsl -d Ubuntu -- bash -lc "cd /mnt/e/Магистр/2-курс/python/RealtyScope && curl -sS -o /dev/null -w '%{http_code}' 'http://localhost:8000/data?limit=3&offset=0'"
```

Verify that Redis has the runtime key without dumping the full JSON payload:

```powershell
wsl -d Ubuntu -- bash -lc "cd /mnt/e/Магистр/2-курс/python/RealtyScope && docker compose -p realtyscope exec -T redis redis-cli --scan --pattern 'realtyscope:*' | sort | head -20"
wsl -d Ubuntu -- bash -lc "cd /mnt/e/Магистр/2-курс/python/RealtyScope && docker compose -p realtyscope exec -T redis redis-cli EXISTS 'realtyscope:listings:v1:limit=3:offset=0'"
wsl -d Ubuntu -- bash -lc "cd /mnt/e/Магистр/2-курс/python/RealtyScope && docker compose -p realtyscope exec -T redis redis-cli TTL 'realtyscope:listings:v1:limit=3:offset=0'"
wsl -d Ubuntu -- bash -lc "cd /mnt/e/Магистр/2-курс/python/RealtyScope && docker compose -p realtyscope exec -T redis redis-cli STRLEN 'realtyscope:listings:v1:limit=3:offset=0'"
```

Expected evidence: HTTP `200`, `EXISTS` returns `1`, `TTL` returns a value from `0` to `60`, and `STRLEN` is greater than `0`. If `TTL` returns `-2`, the short-lived key expired; call `/data?limit=3&offset=0` again and repeat the Redis checks.

## Safe Shutdown And Storage Cleanup

Use non-destructive cleanup for routine development and demos:

```powershell
wsl -d Ubuntu -- bash -lc "cd /mnt/e/Магистр/2-курс/python/RealtyScope && docker compose -p realtyscope stop"
wsl -d Ubuntu -- bash -lc "cd /mnt/e/Магистр/2-курс/python/RealtyScope && docker compose -p realtyscope down"
```

`stop` keeps containers and all named volumes. `down` removes containers and the Compose network, but keeps named volumes unless `-v` is explicitly added.

Inspect storage before deleting anything:

```powershell
wsl -d Ubuntu -- bash -lc "cd /mnt/e/Магистр/2-курс/python/RealtyScope && docker compose -p realtyscope config --volumes"
wsl -d Ubuntu -- bash -lc "docker volume ls | grep realtyscope"
```

The important Docker-managed volumes are `postgres_data`, `redis_data`, `mlflow_data`, and `model_artifacts` with the Compose project prefix applied at runtime. They hold the database rows, Redis state, MLflow metadata/artifacts, and trained model files used during demos.

Only run destructive cleanup when intentionally resetting evidence and after exporting anything you still need:

```powershell
wsl -d Ubuntu -- bash -lc "cd /mnt/e/Магистр/2-курс/python/RealtyScope && docker compose -p realtyscope down -v"
```

Do not use `docker system prune --volumes` during course-readiness work unless the goal is a full Docker storage reset. It can remove unrelated project volumes too.

Local raw snapshots and generated reports/artifacts under `data/raw/` and `data/processed/` are ignored runtime evidence. Delete them only when intentionally resetting captured data or model/report outputs.

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
