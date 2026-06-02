# RealtyScope Phase 3.6 Daily Domclick Capture Automation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Automate the daily Domclick real-data capture so Phase 3 has a repeatable, inspect-gated path from rendered Domclick search state into PostgreSQL.

**Architecture:** Phase 3.6 extends Phase 3.5 real-data ingestion with a bounded daily capture runner. The capture layer produces ignored raw snapshots under `data/raw/domclick/YYYY-MM-DD-bulk/`; scheduled ingestion inspects and validates the snapshot before committing to PostgreSQL. Runtime capture now uses Chrome DevTools/CDP with a dedicated automation Chrome profile and no longer depends on an already-open Codex `@chrome` tab or the workstation's interactive `Default` profile.

**Tech Stack:** Python 3.12, Chrome DevTools/CDP, PowerShell, Windows Task Scheduler, SQLAlchemy 2.0, Alembic, PostgreSQL, pytest, ruff, GitNexus, mem0.

---

## Status

- Execution status: `Completed`.
- Primary completion commit: `dca3f60 feat: automate domclick daily capture`.
- Hardening commit: `7a920e5 fix: harden domclick chrome capture automation`.
- Branch: `phase3-5-real-data-slice`.
- Current GitNexus index: `realtyscope-phase3-5-index`, refreshed after Phase 3 docs at commit `eeeeb47`.

This document is retrospective because the implementation was completed before the plan was written to disk. It exists to keep `docs/superpowers/plans/` aligned with the actual phase history.

## Implemented Scope

- Daily Domclick Chrome SSR capture for Moscow sale apartments with offsets `0..1980`, step `20`, max `100` pages.
- Compact JSON snapshot output under `data/raw/domclick/YYYY-MM-DD-bulk/payloads/` plus `manifest.json`.
- Scheduled batch wrapper that starts PostgreSQL, runs Alembic, captures/reuses snapshot input, inspects data quality, commits only when gates pass, and writes a JSON report.
- Clean-data gate of at least `1000` normalized listings before DB commit.
- Live run on 2026-06-02 produced `100` payload files and `2000` normalized clean listings.
- CDP hardening for empty `--dump-dom` stdout, unusual-request/403 boundary detection, and one persistent Chrome session reuse.

## Files Changed By The Phase

- `src/realtyscope/ingestion/domclick_chrome_capture.py`: Chrome-assisted SSR capture CLI and CDP hardening.
- `src/realtyscope/ingestion/domclick_scheduled_batch.py`: inspect/commit/report orchestration.
- `scripts/run_domclick_scheduled_batch.ps1`: Windows scheduled wrapper.
- `docs/operations/domclick-scheduled-batch-ingestion.md`: operator docs.
- `docs/operations/domclick-scheduled-batch-ingestion.vi.md`: Vietnamese operator docs.
- `docs/operations/domclick-daily-collection.md`: daily collection docs.
- `docs/operations/domclick-daily-collection.vi.md`: Vietnamese daily collection docs.
- `tests/test_domclick_chrome_capture.py`: capture behavior tests.
- `tests/test_domclick_scheduled_batch.py`: scheduled batch tests.
- `pyproject.toml` and `uv.lock`: explicit `websockets>=12` for CDP fallback.

## Acceptance Gates

- [x] Capture is bounded by offset/page limits and delay.
- [x] Snapshot raw data remains ignored and uncommitted.
- [x] Capture stops on QRATOR, CAPTCHA, login wall, or unusual-request boundaries.
- [x] Scheduled batch fails before DB commit when inspect counts are below thresholds.
- [x] Scheduled batch records report JSON under `data/processed/domclick_reports/`.
- [x] Tests cover capture URL bounds, snapshot writing, access-boundary detection, scheduled batch inspect/commit behavior, and CDP session reuse.
- [x] Live 2026-06-02 run inserted `2000` canonical listings and `2000` raw records.
- [x] GitNexus current-branch index created after user correction: `C:\Users\lequa\gitnexus-worktrees\realtyscope-phase3-5-index`.

## Verification Evidence

Commands run after the hardening commit:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m ruff format --check .
git diff --check
gitnexus status
```

Observed results:

```text
pytest: 74 passed, one existing StarletteDeprecationWarning.
ruff check: All checks passed.
ruff format --check: 52 files already formatted.
git diff --check: passed with Git CRLF warnings only.
GitNexus: indexed commit 7a920e5, current commit 7a920e5, up-to-date.
```

Live capture/report evidence:

```text
report: data/processed/domclick_reports/domclick-20260602T003654-228437Z.json
files_written: 100
records_seen: 2000
normalized_listings: 2000
ml_ready_listings: 2000
rejected_listings: 0
raw_inserted: 2000
observations_inserted: 2000
```

## Follow-Up Notes

- The capture producer is workstation-assisted, not fully Docker-portable yet. The persisted snapshot ingestion path is portable; if cross-machine live capture becomes required, add a deployment-owned Playwright/CDP browser sidecar while keeping the same snapshot manifest contract.
- Phase 4.0a moved the scheduled CDP runtime to a dedicated automation profile by default. Use the real interactive Chrome `Default` profile only as an explicit operator override.
- If Domclick removes `window.__SSR_STATE__`, Phase 4+ should add extractor drift detection and a fallback extractor rather than silently lowering data-quality gates.
