# RealtyScope Final Grade-5 Completion Plan

Date: 2026-06-24  
Primary branch to keep: `ui/stitch-hybrid-redesign-20260623`

## Goal

Finish RealtyScope as a truthful, production-ready course demo: real data only, professional Stitch A/B UI, working API/model/monitoring evidence, and no fabricated analytics. The UI should clearly distinguish completed capabilities from partial or missing backend analytics.

## Branch Strategy

1. Continue UI work only on `ui/stitch-hybrid-redesign-20260623`.
2. Do not continue old UI branches except as reference.
3. Preserve `output/git-archives/old-ui-branches-20260624.bundle` as rollback archive for old UI branches.
4. In the next cleanup slice, remove old UI worktrees and delete old branches only after checking:
   - branch has archive in the bundle;
   - worktree is clean or disposable artifacts are explicitly approved;
   - current branch remains untouched.

## Phase 1: Close Current UI Redesign

Success check: reviewer can use all pages without clipped values, fake labels, inert buttons, broken map controls, or hidden important table data.

Tasks:

- Re-audit Stitch A/B exports page by page and compare against current Streamlit shell.
- Restore important table columns everywhere: address/link, source, price, price per m2, rooms, area, floor/floors, observed date, district/geo fields when real.
- Add professional table controls: per-column sorting, refresh button, pagination, and export/report actions that actually use current filtered rows.
- Keep filters page-local unless a shared global filter is intentionally shown.
- Replace repeated or static KPI blocks with page-relevant KPI groups:
  - dashboard: market overview, listing count, ML-ready coverage, latest collection, source mix, trend/segment chart;
  - valuation: prediction, confidence/error metrics if model provides them, comparable objects, model caveats;
  - deals: deal score, discount, price/m2, median segment, source/address link;
  - monitoring: ingestion, DB/API/cache/model/log state from real sources.
- Keep all visible UI text in Russian except `RealtyScope`.
- Verify after each page slice with `py_compile`, `ruff`, targeted pytest, and static screenshot/DOM evidence.

## Phase 2: Map / Heatmap Stabilization

Success check: map behaves like a real analytic map, not a dragged static image.

Tasks:

- Reinspect old RealtyScope map implementation from stash/old branches and port only the useful behavior.
- Clamp coordinates to Moscow/Moscow oblast bounds and exclude invalid points from map layers while reporting excluded count.
- Improve wheel zoom, button zoom, drag/pan smoothing, and tile fallback behavior.
- Make heat and point modes explainable:
  - `Тепло`: aggregated density/intensity surface based on nearby valid points;
  - `Точки`: individual listings with exact stored coordinates;
  - `Тепло + точки`: both layers, so some points can sit outside red hotspots when they are lower intensity or isolated.
- Add compact dashboard map quick filters and full heatmap page controls: layer, radius, opacity, source, rooms, price/area range.
- Make point popups show real price, price per m2, rooms, area, address, source, and listing link when available.
- Verify with static screenshots and limited Chrome/CDP only if memory is stable. Do not use Browser MCP.

## Phase 3: Backend Analytics Needed for Missing Course Features

Success check: each advanced real-estate feature shown in UI is backed by a real algorithm, artifact, or API result.

Tasks:

- District comparison:
  - define reliable district extraction from address/geodata or OSM/admin boundaries;
  - persist normalized district field or district aggregate table;
  - expose API aggregates and UI comparison charts/table.
- Deal detection:
  - replace simple median-only rule with robust score;
  - combine model-predicted fair price, segment median, price/m2 z-score or quantile, and data quality flags;
  - document formula and caveats.
- District clustering:
  - build district feature matrix from listing aggregates and OSM infrastructure;
  - train deterministic clustering;
  - persist labels, cluster profiles, and explanation.
- Exposure forecast:
  - define target from listing observation lifecycle, for example first seen to last seen or status change;
  - train baseline model only if target semantics are trustworthy;
  - expose forecast and accuracy metrics honestly.
- Trend/forecast:
  - validate observation history and repeated-capture semantics;
  - add period filters, rolling medians, and forecast only after enough time points exist.

## Phase 4: Model Quality Upgrade

Success check: selected model is stronger than the current baseline and has reproducible evidence.

Tasks:

- Rebuild features using full current dataset and OSM/district fields where available.
- Compare Ridge baseline against stronger tabular models such as RandomForest, HistGradientBoosting, CatBoost if dependency policy allows.
- Use grouped validation and no price leakage.
- Log all runs to MLflow with metrics, feature set version, and selected model.
- Promote only the best honest model, then update `/model/metadata`, `/predict`, and Streamlit model insight blocks.

## Phase 5: Monitoring, Logs, and Demo Hardening

Success check: monitoring page shows real operational status and bounded logs, not static decorative text.

Tasks:

- Ensure ingestion, API, model, cache, and UI events populate `app_logs` consistently.
- Paginate recent logs and show severity/time/source/message without raw stack traces in UI.
- Add truthful freshness indicators with full date including year.
- Keep `© 2026 RealtyScope Analytics` and make footer/navigation/theme/sidebar controls functional.
- Refresh documentation:
  - `docs/project-status.md`;
  - demo script;
  - final readiness audit;
  - next-session checkpoint.

## Final Verification Checklist

Run before claiming completion:

- `python -m py_compile services\streamlit\app.py`
- `python -m ruff check services\streamlit\app.py`
- relevant Streamlit/API/ML pytest suites
- static audit generation
- limited Chrome headless/CDP visual and interaction audit if memory is stable
- Docker/API/Redis/MLflow smoke after backend changes
- final screenshot set for dashboard, valuation, heatmap, deals, segments, data, monitoring

## Stop Conditions

Pause and ask before continuing if:

- the full real dataset cannot be found from DB/API/snapshots/reports;
- Stitch exports are missing or unreadable;
- old map implementation cannot be located after checking branches/stash;
- requested UI output would require fabricated data or fake service status;
- verification cannot run honestly due to environment crashes.
