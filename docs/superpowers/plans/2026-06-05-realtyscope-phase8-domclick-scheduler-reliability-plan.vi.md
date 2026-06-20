# Kế Hoạch Phase 8: Độ Tin Cậy Scheduler Domclick

> **Cho agentic workers:** REQUIRED SUB-SKILL: dùng `superpowers:subagent-driven-development` (khuyến nghị) hoặc `superpowers:executing-plans` để thực hiện từng task. Các bước dùng checkbox (`- [ ]`) để tracking.

**Mục tiêu:** Làm Domclick scheduled batch có thể phục hồi phần Chrome capture hợp lệ bị dở dang mà không bịa dữ liệu ngày thiếu và không ghi observation bằng timestamp của lúc recovery.

**Kiến trúc:** Giữ shape batch có giới hạn hiện tại: Windows Task Scheduler gọi `scripts/run_domclick_scheduled_batch.ps1`, Chrome/CDP ghi raw snapshot đã gitignore, `domclick_scheduled_batch` inspect trước commit, và SQLAlchemy chỉ persist khi gate pass. Thêm recovery nhỏ cho bulk directory thiếu manifest nhưng có payload parseable, đồng thời bắt buộc có observed timestamp rõ ràng trước mọi commit recovery partial.

**Tech stack:** PowerShell 5.1, Python 3.12, Pydantic, SQLAlchemy, PostgreSQL/SQLite test DB, pytest, ruff, GitNexus, Windows Task Scheduler.

---

## Bằng Chứng Hiện Tại

- Branch: `phase8-domclick-scheduler-reliability`, tạo từ `main`/`origin/main` tại `ee1ae254eecef1b62b3824d860f24c88b1e6ca98`.
- GitNexus: index mới `realtyscope-phase8-domclick-scheduler-reliability-index`, indexed commit `ee1ae25`, status up-to-date.
- Windows task thật, chỉ đọc: `RealtyScope Domclick Scheduled Batch`, last run `2026-06-05 00:00:00`, last result `1`, next run `2026-06-06 00:00:00`.
- `data/processed/runtime_logs/domclick-scheduled-task-20260604-000026.log`: Alembic chạy xong, wrapper fail với `Domclick Chrome capture failed with exit code 1`.
- `data/processed/runtime_logs/domclick-scheduled-task-20260605-000007.log`: Docker DB start, Alembic chạy xong, wrapper fail với `Domclick Chrome capture failed with exit code 1`.
- `data/raw/domclick/2026-06-04-bulk/`: không có JSON/HTML parseable. Inspect-only fail với `Domclick snapshot directory does not contain parseable JSON or HTML files`. Không được bịa dữ liệu 2026-06-04.
- `data/raw/domclick/2026-06-05-bulk/`: có 56 JSON payload và không có `manifest.json`. Inspect-only báo `1120` records, `1120` normalized listings, `1120` ML-ready listings, `0` rejected rows.
- Report fail mới nhất `data/processed/domclick_reports/domclick-20260604T225410-279422Z.json`: fail vì `data\raw\domclick\2026-06-05-bulk` thiếu `manifest.json`.

## Root Cause

1. Chrome capture ghi payload tuần tự nhưng chỉ ghi `manifest.json` sau khi toàn bộ offsets hoàn tất. Nếu một page sau fail, payload hợp lệ trước đó vẫn còn nhưng directory thiếu audit metadata và bị batch mặc định từ chối.
2. PowerShell wrapper coi mọi `YYYY-MM-DD-bulk` directory tồn tại là source, kể cả thiếu manifest. Vì vậy partial directory làm hỏng rerun cùng ngày thay vì cho phép recapture an toàn hoặc recovery có kiểm soát.
3. Scheduled batch hiện persist với `observed_at=started_at`. Một lần manual recovery sẽ ghi thời điểm recovery, không phải thời điểm capture gốc. Điều này không an toàn cho partial data 2026-06-05.

## Phạm Vi

- Chỉ recover payload partial đang tồn tại và parseable. Test không cần live Domclick capture.
- Không recover hoặc synthesize dữ liệu 2026-06-04 vì không có payload parseable.
- Không đổi Windows scheduled task thật nếu chưa có user approval rõ ràng.
- Giữ nguyên ranh giới anti-abuse: QRATOR/CAPTCHA/login page vẫn làm fail page capture tương ứng.
- Thay đổi gọn: scheduler script, scheduled batch CLI/function, test tập trung, docs vận hành/status.

## Task 1: Recovery Partial Có Timestamp An Toàn

**Files:**
- Modify: `src/realtyscope/ingestion/domclick_scheduled_batch.py`
- Modify: `tests/test_domclick_scheduled_batch.py`

- [ ] Viết RED test cho snapshot directory thiếu manifest nhưng có payload parseable: commit phải fail nếu thiếu `observed_at` explicit.
- [ ] Viết RED test rằng `observed_at` explicit được dùng cho `ListingObservation.observed_at`, kể cả khi clock recovery muộn hơn.
- [ ] Thêm optional parameter `observed_at` và CLI flag `--observed-at`.
- [ ] Khi `commit_to_database=True`, `require_manifest=False`, và thiếu `observed_at`, fail trước persistence với lỗi rõ ràng.
- [ ] Ghi `observed_at` đã chọn vào JSON report để audit recovery.
- [ ] Chạy `pytest tests/test_domclick_scheduled_batch.py -q` và commit nếu green.

## Task 2: Wrapper Recovery Và Retry Empty Directory

**Files:**
- Modify: `scripts/run_domclick_scheduled_batch.ps1`
- Modify: `tests/test_domclick_chrome_capture.py` hoặc `tests/test_domclick_scheduled_batch.py` cho script text checks
- Modify: `src/realtyscope/ingestion/domclick_chrome_capture.py`

- [ ] Viết RED test chứng minh empty failed bulk directory không chặn Chrome capture retry sau đó.
- [ ] Viết RED script checks chứng minh partial payload recovery truyền `--allow-missing-manifest` và `--observed-at` derive từ payload timestamp sớm nhất.
- [ ] Cho Chrome capture reuse directory chỉ khi nó không có file, ví dụ empty `payloads/` từ run fail.
- [ ] Trong wrapper, phân biệt manifest-present, partial-with-payloads, và unusable-empty bulk directory.
- [ ] Nếu capture exit non-zero nhưng có payload files parseable, đi tiếp vào batch inspect/commit gate với `--allow-missing-manifest` và observed time explicit.
- [ ] Nếu không có payload files, fail rõ ràng và không fabricate batch.
- [ ] Chạy focused pytest cho test chạm tới và commit nếu green.

## Task 3: Docs, Monitoring, Runtime Smoke

**Files:**
- Modify: `docs/operations/domclick-scheduled-batch-ingestion.md`
- Modify: `docs/operations/domclick-scheduled-batch-ingestion.vi.md`
- Modify: `docs/project-status.md` nếu runtime evidence thay đổi

- [ ] Document root cause và safe recovery policy.
- [ ] Document command manual recovery 2026-06-05 theo thứ tự inspect-only trước; không ghi commit command nếu observed timestamp chưa explicit và verify.
- [ ] Ghi rõ 2026-06-04 unrecoverable vì không có payload parseable.
- [ ] Chạy `git diff --check`, `ruff check .`, `ruff format --check .`, và full `pytest -p no:cacheprovider`.
- [ ] Chạy smoke không ghi DB: scheduled batch inspect/report với partial dir 2026-06-05, explicit `--observed-at`, không `--commit`.
- [ ] Push và chờ GitHub Actions CI trước khi claim lát Phase 8 này xong.

## Verification Gate

Không claim hoàn tất nếu các lệnh này chưa pass mới trên branch active:

```powershell
git diff --check
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m ruff format --check .
.\.venv\Scripts\python.exe -m pytest -p no:cacheprovider
gitnexus status
```

Mọi claim runtime hoặc recovery phải trích output inspect/report không ghi DB tương ứng. Mọi thay đổi Windows scheduled task thật cần user approve ngay trước command thay đổi state.
