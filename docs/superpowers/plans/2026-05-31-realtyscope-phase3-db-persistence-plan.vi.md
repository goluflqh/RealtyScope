# Kế Hoạch Triển Khai Phase 3 Cho RealtyScope

Ngày: 2026-05-31
Trạng thái: bản tiếng Việt có dấu, đi kèm bản kỹ thuật tiếng Anh cho agent.
Bản tiếng Anh: `docs/superpowers/plans/2026-05-31-realtyscope-phase3-db-persistence-plan.md`

---

## Mục tiêu

Phase 3 xây nền tảng cơ sở dữ liệu cho RealtyScope. Nói ngắn gọn: dữ liệu đã được parser/importer của Phase 2 chuẩn hóa thành `IngestionBatch` thì Phase 3 phải lưu được vào cơ sở dữ liệu một cách có kiểm soát, có lịch sử chạy ingestion, có bản ghi raw để audit, có bản ghi listing chuẩn hóa, có bảng rejected rows, và có migration Alembic để tạo schema từ database trống.

Các thuật ngữ chính:

- Database: cơ sở dữ liệu, ở project này là PostgreSQL cho môi trường thật.
- Schema: cấu trúc bảng, cột, khóa ngoại, ràng buộc unique và index trong database.
- Migration: file mô tả thay đổi schema theo thời gian. Alembic dùng file migration để nâng database từ trạng thái trống hoặc cũ lên trạng thái hiện tại.
- Persistence: lớp lưu dữ liệu bền vững vào database, thay vì chỉ giữ trong object Python hoặc file JSONL tạm.
- ORM model: class Python đại diện cho bảng database, dùng SQLAlchemy để đọc/ghi dữ liệu.
- Raw payload: dữ liệu gốc từ nguồn, giữ lại để audit và xử lý lại nếu parser thay đổi.
- Canonical listing: bản ghi listing đã chuẩn hóa, dùng làm nguồn chính cho EDA/ML/API sau này.
- Cleaning flags: các cờ trạng thái làm sạch dữ liệu, ví dụ `has_coordinates`, `is_ml_ready`, `cleaning_status`.
- ML-ready: bản ghi đủ điều kiện tối thiểu để đi vào tập dữ liệu machine learning.

## Phạm vi Phase 3 đã chọn

Phase 3 chỉ làm nền tảng database, Alembic, persistence và cleaning foundation. Phase này không mở rộng sang model machine learning, API production, Streamlit dashboard, Redis cache thật, hay enrichment OpenStreetMap chạy live.

Phase 3 gồm:

- Tạo package `realtyscope.database`.
- Tạo SQLAlchemy 2.0 models cho các bảng lõi.
- Tạo Alembic config và initial migration.
- Lưu `IngestionBatch` từ Phase 2 vào database.
- Lưu raw listings riêng khỏi canonical listings.
- Tạo source links để biết listing chuẩn hóa đến từ raw record nào.
- Lưu rejected rows để không mất dữ liệu lỗi.
- Tạo ingestion run accounting: records seen, raw count, normalized count, rejected count, inserted count, updated count.
- Tạo cleaning flags cơ bản để chuẩn bị EDA và ML.
- Verify migration trên PostgreSQL từ database trống.

Phase 3 chưa làm:

- Chưa train model.
- Chưa dùng MLflow thật.
- Chưa thêm FastAPI `/data` hoặc `/predict` production.
- Chưa làm Streamlit dashboard nhiều trang.
- Chưa dùng Redis làm cache thật.
- Chưa gọi OpenStreetMap hoặc Nominatim live.
- Chưa viết kết luận EDA hoàn chỉnh vì cần dữ liệu đã persist trước.

## Cấu trúc file chính

Các file database/Alembic:

- `src/realtyscope/database/base.py`: khai báo `Base` dùng chung cho SQLAlchemy models.
- `src/realtyscope/database/session.py`: tạo engine/session helper.
- `src/realtyscope/database/models.py`: khai báo các ORM models.
- `src/realtyscope/database/persistence.py`: lưu `IngestionBatch` vào database.
- `alembic.ini`: cấu hình Alembic.
- `alembic/env.py`: nạp metadata từ SQLAlchemy models để Alembic biết schema hiện tại.
- `alembic/versions/20260531_0001_initial_database_foundation.py`: migration đầu tiên.

Các file test:

- `tests/test_config.py`: test `DATABASE_URL` override.
- `tests/test_database_models.py`: test metadata, constraint, relationship và cleaning flags.
- `tests/test_database_persistence.py`: test lưu `IngestionBatch`, idempotency và rejected rows.
- `tests/test_alembic_config.py`: test Alembic env và migration có các bảng/ràng buộc cần thiết.

## Schema database lõi

### `sources`

Lưu metadata của nguồn dữ liệu, ví dụ `domclick`, `teammate_file`, hoặc nguồn sample fixture. Tên source là unique để tránh tạo trùng nguồn.

### `ingestion_runs`

Mỗi lần chạy import/persist tạo một record. Bảng này giúp sau này làm monitoring page: biết lần chạy nào thành công, có bao nhiêu raw rows, normalized rows, rejected rows, inserted rows, updated rows.

### `raw_listings`

Lưu raw payload bất biến từ source. Có `payload_hash` để tránh lưu lại cùng một raw payload nhiều lần cho cùng source.

### `listings`

Lưu listing chuẩn hóa. Đây là bảng chính cho EDA và ML sau này. Bảng này có các field như city, address, coordinates, price, area, rooms, floor, property type, và cleaning flags.

### `listing_source_links`

Liên kết canonical listing với raw listing. Bảng này giúp audit: từ một listing chuẩn hóa có thể truy lại raw record gốc.

### `rejected_listings`

Lưu các row bị reject cùng reason. Điều này quan trọng vì yêu cầu môn học không muốn drop dữ liệu lỗi một cách âm thầm.

### `app_logs`

Bảng log có cấu trúc để sau này phục vụ monitoring/logs trong Streamlit.

## Quy tắc cleaning ban đầu

Ở Phase 3, cleaning chỉ ở mức nền tảng, chưa phải pipeline làm sạch đầy đủ.

Một listing được đánh dấu `is_ml_ready=True` khi có:

- `price_rub` hợp lệ.
- `total_area_m2` hợp lệ.
- Có tọa độ `latitude` và `longitude`.

Nếu thiếu tọa độ thì vẫn lưu vào database, nhưng `is_ml_ready=False` và `cleaning_status="needs_coordinates"`. Cách này giữ dữ liệu minh bạch, không làm mất row, và chuẩn bị cho OSM/geocoding phase sau.

## Cách verify Phase 3

Các check cần pass trước khi nói Phase 3 foundation xong:

```powershell
python -m pytest tests/test_config.py tests/test_database_models.py tests/test_database_persistence.py tests/test_alembic_config.py -q
python -m pytest -q
python -m ruff check .
python -m ruff format --check .
```

Migration phải chạy được trên database trống:

```powershell
$env:DATABASE_URL="postgresql+psycopg://realtyscope:realtyscope@localhost:5432/realtyscope_phase3_verify"
python -m alembic upgrade head
```

Nếu chạy từ Windows PowerShell không có Docker, dùng WSL Ubuntu để start PostgreSQL qua Docker Compose.

## Slice tiếp theo trong Phase 3

Sau khi foundation đã có, bước tiếp theo vẫn thuộc Phase 3 là:

1. Tạo sample ingestion fixture có dữ liệu nhỏ nhưng đại diện cho listing hợp lệ, listing thiếu tọa độ và rejected row.
2. Tạo command/module để persist sample fixture vào database đã migrate.
3. Tạo EDA notebook skeleton đọc từ database, kiểm tra shape/types/missingness/duplicates/outliers/source stats, nhưng chưa viết kết luận giả khi chưa có dataset thật.

Các bước này giúp chứng minh database foundation không chỉ là schema đứng yên, mà có đường dữ liệu chạy được từ Phase 2 contract vào database và chuẩn bị notebook EDA cho course requirement.

## Quy tắc không vượt scope

Khi tiếp tục Phase 3, không được tự ý thêm:

- Model training.
- MLflow experiment thật.
- API `/predict`.
- Streamlit dashboard production.
- Redis caching.
- OSM/Nominatim bulk geocoding.

Những phần đó thuộc các phase sau, trừ khi user đổi scope rõ ràng.
