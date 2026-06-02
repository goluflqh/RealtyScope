# Workflow Chuẩn Cho Agent RealtyScope

Ngày: 2026-06-02
Đối tượng đọc: agent tiếp tục RealtyScope khi user bật Superpowers/SP on.

Workflow này là bắt buộc cho các việc không-trivial trong RealtyScope. Nó ghi lại các nhắc nhở quan trọng từ Phase 3.6/3.7: plan phải được lưu vào disk, GitNexus phải fresh trước khi sửa code, và quyết định quan trọng phải lưu vào mem0.

## Gate Đầu Phiên

1. **Dùng skills phù hợp một cách rõ ràng.**
   - Nếu user nói `SP on`, `Superpowers`, `project mode`, `dự án lớn`, dùng Superpowers process skills.
   - Với feature/phase lớn, dùng `superpowers:writing-plans` trước implementation.
   - Với thay đổi behavior, dùng `superpowers:test-driven-development`.
   - Với bug, failure hoặc behavior lạ, dùng `superpowers:systematic-debugging`.
   - Trước khi claim hoàn thành/commit, dùng `superpowers:verification-before-completion`.
   - Luôn áp dụng Karpathy-style defaults: đơn giản, sửa đúng phạm vi, nói rõ assumption, verify trước khi claim.

2. **Resume mem0 trước.**

```text
resume_project(project_id="python", limit=3, include_global=true)
```

Nếu resume chưa đủ, dùng `search_memory` theo query hẹp. Không dùng broad `list_memories` nếu không thật sự cần audit memory.

3. **Kiểm tra repo state.**

```powershell
git status --short --branch
git log --oneline -5
```

Không overwrite thay đổi của user. Nếu working tree dirty, đọc diff đúng file trước khi sửa.

4. **GitNexus freshness gate.**

Không dùng GitNexus query/impact/context nếu chưa verify index fresh. Worktree ASCII ưu tiên hiện tại:

```text
C:\Users\lequa\gitnexus-worktrees\realtyscope-phase3-5-index
```

Refresh index tới commit hiện tại trước khi sửa code:

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

Kỳ vọng:

```text
Indexed commit == Current commit.
MCP list_repos thấy `realtyscope-phase3-5-index` cùng commit.
```

Sau khi GitNexus fresh, dùng GitNexus cho task:

```text
query: hiểu flow liên quan
context: đọc symbol/file quan trọng
impact: trước khi sửa persistence/API/model/shared behavior
detect_changes: trước commit nếu có sửa code
```

## Quy Tắc Planning

Mọi phase-level work phải có plan docs trong `docs/superpowers/plans/`.

- Bản kỹ thuật tiếng Anh: `docs/superpowers/plans/YYYY-MM-DD-realtyscope-<phase-or-feature>-plan.md`
- Bản tiếng Việt: `docs/superpowers/plans/YYYY-MM-DD-realtyscope-<phase-or-feature>-plan.vi.md`

Không để plan chỉ nằm trong chat. Nếu phase đã implement trước khi rule này được follow, bổ sung retrospective plan/execution record.

Plan phải có:

```text
goal
architecture
tech stack
current evidence
scope và out-of-scope
tasks kèm files/tests/commands
verification gates
commit/checkpoint expectations
```

## Quy Tắc Implementation

- Ưu tiên pattern và helper có sẵn trong repo.
- Sửa surgical, đúng phạm vi task.
- Dùng TDD cho behavior changes.
- Không gọi live network trong tests.
- Với OSM: không bulk geocode qua public Nominatim; dùng coordinates, cache, rate-limit, fixtures trong tests, và attribution.
- Với Domclick: fail closed khi gặp QRATOR/CAPTCHA/login/unusual request và giữ inspect gate trước DB commit.
- Với history/trends: phân biệt rõ canonical latest `listings` và historical `listing_observations`.

## Quy Tắc Verification

Trước khi claim hoàn thành hoặc commit, chạy checks mới. Với code changes, mặc định chạy:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m ruff format --check .
git diff --check
gitnexus status
```

Với docs-only changes, tối thiểu chạy:

```powershell
git diff --check
git status --short --branch
gitnexus status
```

Nếu readiness phụ thuộc runtime data, chạy thêm status/count command và ghi lại số liệu.

## Quy Tắc Commit Và Push

- Chỉ commit khi đã verify.
- Commit message dùng English Conventional Commits.
- Nếu phase sạch và verified, push luôn, không hỏi lại.
- Không commit raw data, database dumps, model artifacts hoặc `.env`.

## Quy Tắc Mem0 Cuối Phiên

Lưu durable mem0 facts khi có quyết định workflow hoặc project fact quan trọng. Luôn lưu checkpoint sau working session:

```text
remember_checkpoint(project_id="python", summary=..., next_step=..., blockers=...)
```

Checkpoint nên có:

```text
commit hash
branch
GitNexus index path và indexed commit
verification commands/results
live data counts nếu liên quan
next phase/task
blockers hoặc caveats
```

## Baseline Hiện Tại Sau Phase 3

Tính đến 2026-06-02:

```text
branch: phase3-5-real-data-slice
latest commit: eeeeb47 docs: standardize phase plans and workflow
GitNexus index: C:\Users\lequa\gitnexus-worktrees\realtyscope-phase3-5-index
indexed commit: eeeeb47
DB live counts: 2000 listings, 2000 raw_listings, 2000 listing_source_links, 2000 listing_observations, 0 rejected_listings
next phase: Phase 4 EDA + OSM enrichment + baseline ML
```
