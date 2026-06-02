# Kế Hoạch Phase 3.7 RealtyScope: Observation / Price History

Ngày: 2026-06-02
Trạng thái: bản tiếng Việt có dấu, đi kèm bản kỹ thuật tiếng Anh cho agent.
Bản tiếng Anh: `docs/superpowers/plans/2026-06-02-realtyscope-phase3-7-observation-history-plan.md`

---

## Mục tiêu

Phase 3.7 thêm lớp lịch sử quan sát để mỗi lần capture hằng ngày không chỉ ghi đè giá mới nhất trong `listings`, mà còn lưu lại observation theo thời gian. Nhờ đó project có nền tảng cho trend dashboard, so sánh tăng/giảm giá, EDA theo thời gian và feature ML sau này.

## Kiến trúc đã chọn

- `listings` giữ vai trò canonical latest state: trạng thái mới nhất của căn hộ/listing.
- `listing_observations` giữ vai trò history: mỗi lần quan sát listing từ source, lưu snapshot giá/diện tích/phòng/tầng/status tại thời điểm đó.
- Persistence upsert canonical listing trước, rồi insert observation sau.
- Payload lặp lại y hệt được dedupe để scheduled job không spam lịch sử.

## Trạng thái

- Đã hoàn thành.
- Commit hoàn thành: `d2bb740 feat: add listing observation history`.
- Branch: `phase3-5-real-data-slice`.
- GitNexus index hiện tại: `realtyscope-phase3-5-index`, indexed đúng commit mới nhất `7a920e5` sau hardening Phase 3.

Tài liệu này là retrospective plan, vì implementation đã hoàn thành trước khi plan được ghi vào disk. Việc bổ sung này để đồng bộ lại quy trình `docs/superpowers/plans/`.

## File liên quan

- `src/realtyscope/database/models.py`: model `ListingObservation`.
- `alembic/versions/20260602_0002_listing_observations.py`: migration observation history.
- `src/realtyscope/database/persistence.py`: canonical upsert + observation insert/dedup.
- `tests/test_database_persistence.py`: test price-change và dedup observation.
- `docs/data/realtyscope-observation-history.md`: giải thích tiếng Anh.
- `docs/data/realtyscope-observation-history.vi.md`: giải thích tiếng Việt.
- `docs/course-guidance/realtyscope-user-story-traceability.md`: traceability User Stories.
- `docs/course-guidance/realtyscope-user-story-traceability.vi.md`: traceability tiếng Việt.

## Gate đã đạt

- [x] Cùng `source_listing_id` đổi giá thì canonical `listings.price_rub` được update.
- [x] Giá đổi tạo thêm observation mới.
- [x] Payload lặp y hệt không tạo observation trùng.
- [x] Observation lưu đủ snapshot fields cho trend, EDA và ML sau này.
- [x] Có Alembic migration.
- [x] Docs giải thích rõ canonical latest listing khác observation history.
- [x] Live scheduled run ngày 2026-06-02 đã insert `2000` observations.

## Bằng chứng verify

Các lệnh đã chạy trong trạng thái Phase 3 cuối:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m ruff format --check .
git diff --check
python -m realtyscope.ingestion.domclick_scheduled_batch status --database-url postgresql+psycopg://realtyscope:realtyscope@localhost:5432/realtyscope --json
```

Kết quả:

```text
pytest: 74 passed, chỉ có StarletteDeprecationWarning cũ.
ruff check: pass.
ruff format --check: pass.
git diff --check: pass, chỉ có CRLF warning.
DB counts: listings=2000, raw_listings=2000, listing_source_links=2000, listing_observations=2000, rejected_listings=0.
latest run: status=success, records_seen=2000, normalized_count=2000.
```

## Lưu ý cho Phase 4

- Trend dashboard và EDA theo thời gian phải đọc `listing_observations`, không chỉ đọc `listings`.
- API/UI nên tách rõ latest state và history state.
- Feature snapshot cho ML phải định nghĩa rõ dùng latest-only, observation-window features hay cả hai.
- Observation history là nền tảng đúng cho price-change, listing freshness, days-on-market approximation và temporal train/test split.
