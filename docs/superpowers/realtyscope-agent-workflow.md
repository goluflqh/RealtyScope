# RealtyScope Agent Workflow

Date: 2026-06-02
Audience: agents continuing RealtyScope work with Superpowers enabled.

This workflow is mandatory for non-trivial RealtyScope work. It records user corrections from Phase 3.6/3.7: plan docs must be saved to disk, GitNexus must be fresh before code changes, and important workflow decisions must be saved in mem0.

## Start-Of-Session Gates

1. **Use relevant skills visibly.**
   - If the user says `SP on`, `Superpowers`, `project mode`, `dự án lớn`, or similar, use Superpowers process skills.
   - For large features or phase work, use `superpowers:writing-plans` before implementation.
   - For behavior changes, use `superpowers:test-driven-development`.
   - For bugs, failures, or unexpected behavior, use `superpowers:systematic-debugging`.
   - Before completion/commit, use `superpowers:verification-before-completion`.
   - Apply Karpathy-style defaults: simple, surgical, explicit assumptions, verified success checks.

2. **Resume project memory first.**

```text
resume_project(project_id="python", limit=3, include_global=true)
```

If the task mentions a remembered topic but resume is insufficient, use targeted `search_memory`, not broad `list_memories`.

3. **Inspect local state.**

```powershell
git status --short --branch
git log --oneline -5
```

Do not overwrite user changes. If the tree is dirty, inspect targeted diffs before editing.

4. **GitNexus freshness gate.**

Do not rely on GitNexus graph/query/impact until freshness is verified. Current preferred ASCII index worktree:

```text
C:\Users\lequa\gitnexus-worktrees\realtyscope-phase3-5-index
```

Refresh it to the current repo commit before code changes:

```powershell
$CurrentSha = git rev-parse HEAD
$IndexPath = "C:\Users\lequa\gitnexus-worktrees\realtyscope-phase3-5-index"
if (-not (Test-Path -LiteralPath $IndexPath)) {
  git worktree add --detach $IndexPath $CurrentSha
} else {
  git -C $IndexPath checkout --detach $CurrentSha
}
Push-Location $IndexPath
gitnexus analyze .
gitnexus status
Pop-Location
```

Expected:

```text
Indexed commit == Current commit.
MCP list_repos shows `realtyscope-phase3-5-index` with the same commit.
```

After freshness is verified, use GitNexus for the task:

```text
query: understand relevant flows
context: inspect key symbols/files
impact: before changing shared persistence/API/model behavior
detect_changes: before commit when code changed
```

## Planning Rules

All phase-level work must have plan docs under `docs/superpowers/plans/`.

- English technical plan: `docs/superpowers/plans/YYYY-MM-DD-realtyscope-<phase-or-feature>-plan.md`
- Vietnamese companion: `docs/superpowers/plans/YYYY-MM-DD-realtyscope-<phase-or-feature>-plan.vi.md`

Do not leave phase plans only in chat. If a phase was implemented before this rule was followed, add a retrospective plan/execution record.

Plans must include:

```text
goal
architecture
tech stack
current evidence
scope and non-scope
tasks with files/tests/commands
verification gates
commit/checkpoint expectations
```

## Implementation Rules

- Prefer existing repo patterns and helpers.
- Keep changes surgical and scoped to the task.
- Use TDD for behavior changes.
- Use no live network calls in tests.
- For OSM: do not bulk geocode via public Nominatim; use coordinates, cache, rate-limit, fixtures in tests, and attribution.
- For Domclick: fail closed on QRATOR/CAPTCHA/login/unusual-request boundaries and preserve inspect gates before DB commit.
- For history/trends: distinguish canonical latest `listings` from historical `listing_observations`.

## Verification Rules

Before claiming completion or committing, run fresh relevant checks. For code changes, default to:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m ruff format --check .
git diff --check
gitnexus status
```

For docs-only changes, at minimum run:

```powershell
git diff --check
git status --short --branch
gitnexus status
```

If phase-readiness depends on runtime data, also run the relevant status/count command and quote the numbers.

## Commit And Push Rules

- Commit only clean, verified work.
- Use English Conventional Commits.
- If the phase is clean and verified, push without asking again.
- Keep raw data, database dumps, model artifacts, and `.env` files uncommitted.

## End-Of-Session Memory Rules

Save durable mem0 facts when a workflow decision or project fact was confirmed. Always save a checkpoint after a working session:

```text
remember_checkpoint(project_id="python", summary=..., next_step=..., blockers=...)
```

Checkpoint should include:

```text
commit hash
branch
GitNexus index path and indexed commit
verification commands/results
live data counts if relevant
next phase/task
blockers or caveats
```

## Current Phase 3 Baseline

As of 2026-06-02:

```text
branch: phase3-5-real-data-slice
latest commit: 7a920e5 fix: harden domclick chrome capture automation
GitNexus index: C:\Users\lequa\gitnexus-worktrees\realtyscope-phase3-5-index
indexed commit: 7a920e5
DB live counts: 2000 listings, 2000 raw_listings, 2000 listing_source_links, 2000 listing_observations, 0 rejected_listings
next phase: Phase 4 EDA + OSM enrichment + baseline ML
```
