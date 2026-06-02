# Domclick Scheduled Batch Ingestion

Date: 2026-06-01
Audience: coding agents and operators maintaining RealtyScope after Phase 3.5.

## Technical Plan For Agents

This path is a scheduled batch ingestor, not a continuously running scraper. Each run has a bounded input, a bounded output, an inspect gate, an optional PostgreSQL commit, and a JSON report.

Flow:

1. Prepare or reuse one input source: an existing `data/raw/domclick/YYYY-MM-DD/` snapshot directory, an existing `data/raw/domclick/YYYY-MM-DD-bulk/` Chrome SSR directory, a newly captured Chrome SSR directory, or a URL file with allowed Domclick URLs for the bounded HTTP collector.
2. Capture or reuse snapshots. The Chrome SSR path starts a bounded Chrome DevTools/CDP session with a dedicated automation Chrome profile and writes compact JSON under `YYYY-MM-DD-bulk/`. URL-file capture uses explicit `--max-urls`, `--delay-seconds`, `--timeout-seconds`, robots.txt checks, QRATOR detection, and `manifest.json`.
3. Run the Pydantic inspect gate through `realtyscope.database.real_data_ingestion` parser functions.
4. Fail before any database write when `records_seen < --min-records` or `normalized_listings < --min-normalized-records`. For the scheduled wrapper, the clean-data gate is 1000 normalized listings.
5. Commit through SQLAlchemy only when `--commit` is present.
6. Write a JSON report under `data/processed/domclick_reports/`, which is ignored by git.
7. Query database status with the `status` subcommand.

Entrypoint:

```powershell
.\.venv\Scripts\python.exe -m realtyscope.ingestion.domclick_scheduled_batch --help
```

## Daily Chrome SSR Capture

Use this command when today's raw snapshot is missing and the Windows workstation can legitimately render Domclick with Chrome. The default scope is Moscow sale apartments: `aids=2299` (`Москва`), offsets `0..1980`, step `20`, up to 100 rendered search pages and roughly 2000 raw candidates. The larger capture window is intentional because the scheduled ingest must finish with at least 1000 normalized clean listings after parsing.

The command uses the `cdp` capture runtime by default. It starts its own Chrome DevTools/CDP browser process with a dedicated automation user-data directory, so it does not depend on a Codex `@chrome` tab or a normal interactive Chrome window already being open. On Windows, the default automation user-data directory is `%LOCALAPPDATA%\RealtyScope\ChromeAutomation\User Data` with profile directory `Default`; this is separate from the real workstation Chrome `Default` profile unless an operator explicitly points `REALTYSCOPE_CHROME_USER_DATA_DIR` at that profile. The command does not bypass QRATOR, CAPTCHA, login walls, or other access boundaries; those pages are treated as failures.

```powershell
$env:PYTHONIOENCODING="utf-8"
.\.venv\Scripts\python.exe -m realtyscope.ingestion.domclick_chrome_capture `
  --output-root data/raw/domclick `
  --collection-date 2026-06-02 `
  --capture-runtime cdp `
  --offset-start 0 `
  --offset-stop 1980 `
  --offset-step 20 `
  --max-pages 100 `
  --delay-seconds 3 `
  --min-records 1000 `
  --json
```

Runtime configuration is explicit and can be provided through environment variables or CLI flags:

| Environment variable | CLI flag | Purpose |
| --- | --- | --- |
| `REALTYSCOPE_CAPTURE_RUNTIME` | `--capture-runtime` | Currently supported value: `cdp`. A Playwright/browser sidecar is documented as a future option, not implemented in Phase 4.0a. |
| `REALTYSCOPE_CHROME_BINARY` | `--chrome-binary` | Optional Chrome executable path. Legacy `REALTYSCOPE_CHROME_PATH` remains a fallback. |
| `REALTYSCOPE_CHROME_USER_DATA_DIR` | `--chrome-user-data-dir` | Optional automation Chrome user-data directory. Defaults to the dedicated RealtyScope path above. |
| `REALTYSCOPE_CHROME_PROFILE_DIRECTORY` | `--profile-directory` | Optional profile directory inside the user-data directory. Defaults to `Default` inside the dedicated automation directory. |
| `REALTYSCOPE_CHROME_REMOTE_DEBUGGING_PORT` | `--remote-debugging-port` | Optional fixed CDP port. If unset, the capture process reserves a local free port. |

Output layout:

```text
data/raw/domclick/YYYY-MM-DD-bulk/
  manifest.json
  payloads/
    search-offset-000000.json
    search-offset-000020.json
```

The payload files contain compact JSON extracted from `window.__SSR_STATE__`; they are intentionally stored under ignored `data/raw/` and must not be committed.

## Inspect-Only Run

Use inspect-only mode first when validating a new capture host or URL file. This writes a report but does not write to PostgreSQL:

```powershell
$env:PYTHONIOENCODING="utf-8"
.\.venv\Scripts\python.exe -m realtyscope.ingestion.domclick_scheduled_batch run `
  --url-file data/raw/domclick-urls.txt `
  --output-root data/raw/domclick `
  --collection-date 2026-06-01 `
  --max-urls 50 `
  --delay-seconds 2 `
  --max-records 2000 `
  --min-records 1 `
  --min-normalized-records 1000 `
  --json
```

For a Chrome-assisted or manually copied snapshot directory that already has `manifest.json`:

```powershell
.\.venv\Scripts\python.exe -m realtyscope.ingestion.domclick_scheduled_batch run `
  --source-path data/raw/domclick/2026-06-01-bulk `
  --max-records 2000 `
  --min-records 1 `
  --min-normalized-records 1000 `
  --json
```

## Commit Run

Run Alembic before the scheduled job writes to PostgreSQL:

```powershell
$env:DATABASE_URL="postgresql+psycopg://realtyscope:realtyscope@localhost:5432/realtyscope"
.\.venv\Scripts\python.exe -m alembic upgrade head
```

Then commit one bounded batch:

```powershell
.\.venv\Scripts\python.exe -m realtyscope.ingestion.domclick_scheduled_batch run `
  --source-path data/raw/domclick/2026-06-01-bulk `
  --database-url $env:DATABASE_URL `
  --commit `
  --max-records 2000 `
  --min-records 1 `
  --min-normalized-records 1000 `
  --json
```

The persistence layer is idempotent for repeated raw payloads. A repeat run should show reused raw rows and updated listings rather than duplicating canonical listings or observations. If Domclick returns the same ranked search pages every day, the canonical `listings` table will mostly refresh the same slice. The `listing_observations` history grows only when a material raw snapshot changes enough to create a new raw row, for example a price change for the same `source_listing_id`.

## Status And Reports

Check database status:

```powershell
.\.venv\Scripts\python.exe -m realtyscope.ingestion.domclick_scheduled_batch status `
  --database-url $env:DATABASE_URL `
  --json
```

Reports are written to:

```text
data/processed/domclick_reports/domclick-<timestamp>.json
```

Reports contain counts, paths, status, and error summaries. They do not contain raw payloads.

## Windows Task Scheduler

Use Windows Task Scheduler when capture depends on a Windows workstation, a dedicated automation Chrome profile, or an operator-managed network route.

The repo includes a Windows wrapper script that auto-selects the Moscow collection date:

```powershell
.\scripts\run_domclick_scheduled_batch.ps1
```

The script uses this input priority:

1. `data/raw/domclick/YYYY-MM-DD/`
2. `data/raw/domclick/YYYY-MM-DD-bulk/`
3. If neither directory exists, run the Chrome SSR capture into `data/raw/domclick/YYYY-MM-DD-bulk/`.
4. If `-SkipCapture` is passed, fall back to `data/raw/domclick-urls.txt` when present.

It starts the WSL Docker PostgreSQL service unless `-SkipDockerStart` is passed, runs Alembic, captures today's missing Chrome SSR snapshot when needed, runs the bounded batch with `--commit`, and writes logs under `data/processed/runtime_logs/`. The script accepts the same runtime environment variables listed above and passes them through to `realtyscope.ingestion.domclick_chrome_capture`.

Dry-run the scheduled command without Docker, Alembic, Chrome capture, batch ingestion, or database writes:

```powershell
.\scripts\run_domclick_scheduled_batch.ps1 -DryRun -SkipDockerStart -CollectionDate 2099-01-01
```

Recommended task settings:

- Trigger: daily or every few hours, never an infinite loop.
- Program: `powershell.exe`.
- Start in: the RealtyScope repository root.
- Run only one instance at a time.
- Stop the task if it runs longer than the expected batch window.
- Keep task history enabled and monitor non-zero exit codes.

Example arguments for a commit job using an existing Chrome-assisted day directory:

```powershell
-NoProfile -ExecutionPolicy Bypass -Command "$env:PYTHONIOENCODING='utf-8'; $env:DATABASE_URL='postgresql+psycopg://realtyscope:realtyscope@localhost:5432/realtyscope'; Set-Location 'E:\Магистр\2-курс\python\RealtyScope'; .\.venv\Scripts\python.exe -m alembic upgrade head; .\.venv\Scripts\python.exe -m realtyscope.ingestion.domclick_scheduled_batch run --source-path data/raw/domclick/2026-06-01-bulk --database-url $env:DATABASE_URL --commit --max-records 2000 --min-records 1 --min-normalized-records 1000 --json"
```

If the task performs URL-file capture, pass `-SkipCapture` and provide `data/raw/domclick-urls.txt`; that path must still avoid `/search` while robots.txt disallows direct HTTP fetching. The default scheduled path captures rendered `/search` SSR state only through a dedicated CDP automation profile and stops if Domclick presents QRATOR, CAPTCHA, or a login wall.

The task currently installed on the development machine is named `RealtyScope Domclick Scheduled Batch` and runs daily at 00:00 Moscow time.

## WSL Cron

Use WSL cron for offline ingest/status jobs when snapshots are already present. Do not reuse the Windows `.venv` from WSL; install a Linux environment from `uv.lock` first.

Chrome/CDP capture is not Docker-portable by default because it depends on a desktop Chrome binary, a writable browser user-data directory, and a reachable CDP port. For WSL, Docker, or VPS runs, prefer copying a completed `YYYY-MM-DD-bulk/` snapshot into `data/raw/domclick/` and running only the offline ingest path. If live capture must move into Docker/Linux later, add a deployment-owned Playwright or browser sidecar process and keep the same snapshot manifest contract.

Example crontab entry:

```cron
0 0 * * * cd /mnt/e/Магистр/2-курс/python/RealtyScope && export DATABASE_URL='postgresql+psycopg://realtyscope:realtyscope@localhost:5432/realtyscope' && uv run python -m alembic upgrade head && uv run python -m realtyscope.ingestion.domclick_scheduled_batch run --source-path data/raw/domclick/$(date +\%F) --database-url "$DATABASE_URL" --commit --max-records 2000 --min-records 1 --min-normalized-records 1000 --json >> data/processed/domclick_reports/cron.log 2>&1
```

## Systemd Timer

For a Linux VPS, prefer a systemd service plus timer. Keep secrets in an environment file outside git, for example `/etc/realtyscope/domclick-ingestor.env`.

Service sketch:

```ini
[Unit]
Description=RealtyScope Domclick scheduled batch ingestion

[Service]
Type=oneshot
WorkingDirectory=/opt/realtyscope
EnvironmentFile=/etc/realtyscope/domclick-ingestor.env
ExecStart=/opt/realtyscope/.venv/bin/python -m alembic upgrade head
ExecStart=/opt/realtyscope/.venv/bin/python -m realtyscope.ingestion.domclick_scheduled_batch run --source-path data/raw/domclick/current --database-url ${DATABASE_URL} --commit --max-records 2000 --min-records 1 --min-normalized-records 1000 --json
```

Timer sketch:

```ini
[Unit]
Description=Run RealtyScope Domclick batch daily

[Timer]
OnCalendar=*-*-* 00:00:00
Persistent=true

[Install]
WantedBy=timers.target
```

Point `data/raw/domclick/current` at the latest copied day directory, or use a small wrapper script stored outside git for dynamic dates. Do not put an infinite loop inside the Python process.

## Failure Policy

The scheduled job should be treated as failed when:

- capture is blocked by robots.txt, QRATOR, CAPTCHA, login wall, or HTTP errors;
- Chrome cannot be found, the configured profile is missing or locked, or rendered SSR state is unavailable;
- no parseable snapshot files are present;
- inspect returns fewer rows than `--min-records`;
- inspect returns fewer normalized clean listings than `--min-normalized-records`;
- Alembic or SQLAlchemy commit fails;
- the report has `"status": "failed"` or the process exits non-zero.

Raw snapshots remain under `data/raw/` and must not be committed. Runtime reports remain under `data/processed/` and also stay out of git.
