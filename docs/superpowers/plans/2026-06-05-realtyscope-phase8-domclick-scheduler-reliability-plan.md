# RealtyScope Phase 8 Domclick Scheduler Reliability Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the Domclick scheduled batch recover valid partial Chrome capture data without inventing missing days or persisting observations at a misleading recovery timestamp.

**Architecture:** Keep the existing bounded batch shape: Windows Task Scheduler calls `scripts/run_domclick_scheduled_batch.ps1`, Chrome/CDP writes ignored raw snapshots, `domclick_scheduled_batch` inspects before commit, and SQLAlchemy persists only after gates pass. Add a small recovery path for missing-manifest bulk directories that contain parseable payload files, while requiring an explicit observed timestamp for any committed partial recovery.

**Tech Stack:** PowerShell 5.1, Python 3.12, Pydantic, SQLAlchemy, PostgreSQL/SQLite test DBs, pytest, ruff, GitNexus, Windows Task Scheduler.

---

## Current Evidence

- Branch: `phase8-domclick-scheduler-reliability`, created from `main`/`origin/main` at `ee1ae254eecef1b62b3824d860f24c88b1e6ca98`.
- GitNexus: fresh index `realtyscope-phase8-domclick-scheduler-reliability-index`, indexed commit `ee1ae25`, status up-to-date.
- Installed Windows task, read-only check: `RealtyScope Domclick Scheduled Batch`, last run `2026-06-05 00:00:00`, last result `1`, next run `2026-06-06 00:00:00`.
- `data/processed/runtime_logs/domclick-scheduled-task-20260604-000026.log`: Alembic ran, then wrapper failed with `Domclick Chrome capture failed with exit code 1`.
- `data/processed/runtime_logs/domclick-scheduled-task-20260605-000007.log`: Docker DB started, Alembic ran, then wrapper failed with `Domclick Chrome capture failed with exit code 1`.
- `data/raw/domclick/2026-06-04-bulk/`: contains no parseable JSON/HTML payloads. Inspect-only fails with `Domclick snapshot directory does not contain parseable JSON or HTML files`. Do not fake 2026-06-04 data.
- `data/raw/domclick/2026-06-05-bulk/`: contains 56 JSON payloads and no `manifest.json`. Inspect-only reports `1120` records, `1120` normalized listings, `1120` ML-ready listings, and `0` rejected rows.
- Latest failed report `data/processed/domclick_reports/domclick-20260604T225410-279422Z.json`: failed because `data\raw\domclick\2026-06-05-bulk` was missing `manifest.json`.

## Root Cause

1. Chrome capture writes payload files incrementally but writes `manifest.json` only after all offsets finish. If a later page fails, valid earlier payloads remain but the directory is unaudited and rejected by the scheduled batch default.
2. The PowerShell wrapper treats any existing `YYYY-MM-DD-bulk` directory as the input source, even if it has no manifest. That makes partial directories poison same-day reruns instead of allowing a safe recapture or recovery decision.
3. The scheduled batch currently persists with `observed_at=started_at`. A manual recovery run would therefore record the recovery time, not the original capture time. This is unsafe for the 2026-06-05 partial data.

## Scope

- Recover only existing, parseable partial payloads. No live Domclick capture is required for tests.
- Do not recover or synthesize 2026-06-04 data because no parseable payloads exist.
- Do not change the installed Windows scheduled task without explicit user approval.
- Keep anti-abuse boundaries intact: QRATOR/CAPTCHA/login pages still fail the capture page that hits them.
- Keep changes surgical: scheduler script, scheduled batch CLI/function, focused tests, and operation docs/status.

## Task 1: Safe Timestamped Partial Recovery

**Files:**
- Modify: `src/realtyscope/ingestion/domclick_scheduled_batch.py`
- Modify: `tests/test_domclick_scheduled_batch.py`

- [ ] Write RED tests for a missing-manifest snapshot directory with parseable payloads: commit must fail unless `observed_at` is explicit.
- [ ] Write RED test that explicit `observed_at` is used for `ListingObservation.observed_at`, even when the recovery clock is later.
- [ ] Add an optional `observed_at` parameter and `--observed-at` CLI flag.
- [ ] When `commit_to_database=True`, `require_manifest=False`, and `observed_at` is absent, fail before persistence with a clear error.
- [ ] Include the chosen `observed_at` in the JSON report so recovery can be audited.
- [ ] Run `pytest tests/test_domclick_scheduled_batch.py -q` and commit the slice if green.

## Task 2: Wrapper Recovery And Empty-Directory Retry

**Files:**
- Modify: `scripts/run_domclick_scheduled_batch.ps1`
- Modify: `tests/test_domclick_chrome_capture.py` or `tests/test_domclick_scheduled_batch.py` for script text checks
- Modify: `src/realtyscope/ingestion/domclick_chrome_capture.py`

- [ ] Write RED tests showing an empty failed bulk directory does not block a later Chrome capture retry.
- [ ] Write RED script checks showing partial payload recovery passes `--allow-missing-manifest` and an `--observed-at` derived from the earliest payload timestamp.
- [ ] Let Chrome capture reuse an existing directory only when it has no files, such as an empty `payloads/` directory left by a failed run.
- [ ] In the wrapper, distinguish manifest-present, partial-with-payloads, and unusable-empty bulk directories.
- [ ] If capture exits non-zero but parseable payload files exist, proceed to the batch inspect/commit gate with `--allow-missing-manifest` and explicit observed time.
- [ ] If no payload files exist, fail clearly and do not fabricate a batch.
- [ ] Run focused pytest for the touched tests and commit the slice if green.

## Task 3: Documentation, Monitoring, And Runtime Smoke

**Files:**
- Modify: `docs/operations/domclick-scheduled-batch-ingestion.md`
- Modify: `docs/operations/domclick-scheduled-batch-ingestion.vi.md`
- Modify: `docs/project-status.md` if runtime evidence changes

- [ ] Document the root cause and the safe recovery policy.
- [ ] Document the exact manual 2026-06-05 recovery command as inspect-only first; do not include a commit command unless the observed timestamp is explicit and verified.
- [ ] Keep 2026-06-04 documented as unrecoverable because no parseable payloads exist.
- [ ] Run `git diff --check`, `ruff check .`, `ruff format --check .`, and full `pytest -p no:cacheprovider`.
- [ ] Run a no-write smoke: scheduled batch inspect/report against the 2026-06-05 partial directory with explicit `--observed-at` and no `--commit`.
- [ ] Push and wait for GitHub Actions CI before claiming this Phase 8 slice is complete.

## Verification Gate

Do not claim completion until these pass freshly on the active branch:

```powershell
git diff --check
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m ruff format --check .
.\.venv\Scripts\python.exe -m pytest -p no:cacheprovider
gitnexus status
```

Runtime or recovery claims also require quoting the relevant no-write inspect/report output. Any real Windows scheduled task change requires user approval immediately before the state-changing command.
