# Kế Hoạch Phase 3.6 RealtyScope: Tự Động Capture Domclick Hằng Ngày

Ngày: 2026-06-02
Trạng thái: bản tiếng Việt có dấu, đi kèm bản kỹ thuật tiếng Anh cho agent.
Bản tiếng Anh: `docs/superpowers/plans/2026-06-02-realtyscope-phase3-6-daily-domclick-capture-plan.md`

---

## Mục tiêu

Phase 3.6 tự động hóa việc lấy dữ liệu thật hằng ngày từ Domclick. Mục tiêu là có một đường chạy lặp lại được: Chrome render dữ liệu public search state, lưu snapshot thô có manifest, inspect chất lượng dữ liệu, rồi chỉ commit vào PostgreSQL khi đủ ngưỡng sạch.

## Kiến trúc đã chọn

Phase này không biến RealtyScope thành scraper chạy liên tục. Nó là batch có giới hạn:

1. Capture hoặc reuse snapshot trong `data/raw/domclick/YYYY-MM-DD-bulk/`.
2. Inspect bằng parser hiện có.
3. Fail trước khi ghi DB nếu số row hoặc số listing normalized sạch quá thấp.
4. Commit PostgreSQL chỉ khi có `--commit` và gate pass.
5. Ghi report JSON để audit.

Ban đầu Phase 3.6 dùng Chrome `--dump-dom`. Sau hardening và Phase 4.0a, capture chính dùng Chrome DevTools/CDP với profile riêng cho automation, nên scheduled job không còn phụ thuộc tab `@chrome` trong Codex hoặc profile Chrome thật `Default` của workstation.

## Trạng thái

- Đã hoàn thành.
- Commit chính: `dca3f60 feat: automate domclick daily capture`.
- Commit hardening: `7a920e5 fix: harden domclick chrome capture automation`.
- Branch: `phase3-5-real-data-slice`.
- GitNexus index hiện tại: `realtyscope-phase3-5-index`, đã refresh sau docs Phase 3 ở commit `eeeeb47`.

Tài liệu này là retrospective plan, vì implementation đã hoàn thành trước khi plan được ghi vào disk. Việc bổ sung này để đồng bộ lại quy trình `docs/superpowers/plans/`.

## File liên quan

- `src/realtyscope/ingestion/domclick_chrome_capture.py`: capture SSR bằng Chrome/CDP.
- `src/realtyscope/ingestion/domclick_scheduled_batch.py`: orchestrate inspect, commit, report.
- `scripts/run_domclick_scheduled_batch.ps1`: wrapper cho Windows Task Scheduler.
- `docs/operations/domclick-scheduled-batch-ingestion.md`: docs vận hành tiếng Anh.
- `docs/operations/domclick-scheduled-batch-ingestion.vi.md`: docs vận hành tiếng Việt.
- `tests/test_domclick_chrome_capture.py`: test capture.
- `tests/test_domclick_scheduled_batch.py`: test scheduled batch.
- `pyproject.toml`, `uv.lock`: khai báo `websockets>=12` cho CDP.

## Gate đã đạt

- [x] Capture có giới hạn offset/page/delay.
- [x] Raw snapshot bị ignore, không commit vào git.
- [x] Dừng khi gặp QRATOR, CAPTCHA, login wall hoặc unusual request.
- [x] Scheduled batch fail trước commit nếu inspect count dưới ngưỡng.
- [x] Ngưỡng clean-data của wrapper là ít nhất `1000` listing normalized.
- [x] Có report JSON dưới `data/processed/domclick_reports/`.
- [x] Có test cho snapshot writing, boundary detection, scheduled batch, CDP fallback và reuse một DevTools session.
- [x] Live capture ngày 2026-06-02 thành công với `2000` listing sạch.

## Bằng chứng verify

Các lệnh đã chạy sau commit hardening:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m ruff format --check .
git diff --check
gitnexus status
```

Kết quả:

```text
pytest: 74 passed, chỉ có StarletteDeprecationWarning cũ.
ruff check: pass.
ruff format --check: pass.
git diff --check: pass, chỉ có CRLF warning của Git trên Windows.
GitNexus: indexed commit 7a920e5, current commit 7a920e5, up-to-date.
```

Live run ngày 2026-06-02:

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

## Lưu ý cho phase sau

- Ingestion từ snapshot đã portable hơn capture live. Capture live vẫn phụ thuộc Chrome desktop, user-data directory ghi được, CDP port và IP của máy, nên chưa nên claim là Docker-portable hoàn toàn.
- Phase 4.0a đã chuyển scheduled CDP runtime sang dedicated automation profile mặc định. Nếu cần chạy live capture trên máy khác hoặc trong Docker/Linux, hướng tiếp theo là Playwright/CDP browser sidecar do deployment quản lý.
- Nếu Domclick đổi `window.__SSR_STATE__`, phase sau phải có drift detection và fallback extractor, không được giảm ngưỡng dữ liệu để che lỗi.
