# Kế Hoạch Phase 3.5 Cho RealtyScope: Dữ Liệu Thật, EDA Thật, API/Dashboard Đầu Tiên

Ngày: 2026-05-31
Trạng thái: bản tiếng Việt có dấu, đi kèm bản kỹ thuật tiếng Anh cho agent.
Bản tiếng Anh: `docs/superpowers/plans/2026-05-31-realtyscope-phase3-5-real-data-plan.md`

---

## Mục tiêu

Phase 3.5 là bước nối giữa nền tảng database của Phase 3 và các phase ML/API/UI sau này. Mục tiêu không phải tạo thêm khung sườn, mà là tạo lát cắt đầu tiên có dữ liệu thật: lấy nguồn listing thật, đưa qua ingestion contract, lưu vào PostgreSQL, chạy EDA có kết luận thật, rồi mở API/dashboard đọc từ database.

Nói ngắn gọn: sau Phase 3.5, project phải bắt đầu có “thân thể dữ liệu”, không chỉ có schema và sample fixture.

## Trạng thái hiện tại đã kiểm chứng

- Branch hiện tại: `phase2-ingestion`.
- Repo sạch và đang ahead origin 1 commit: `308c8ce feat: add phase 3 database persistence foundation`.
- Phase 3 đã có SQLAlchemy models, Alembic migration, persistence từ `IngestionBatch`, sample ingestion command và notebook EDA skeleton.
- Đã kiểm tra `E:\Магистр\2-курс\python` và `E:\Магистр\2-курс\python\RealtyScope`, kể cả ignored files.
- Không tìm thấy dataset listing thật dạng CSV, JSON, JSONL, HTML snapshot, Excel, parquet hoặc feather.
- Chỉ thấy tài liệu môn học HTML, không phải dữ liệu căn hộ.
- Code hiện có thể import CSV theo teammate contract hoặc parse Domclick-like JSON payload, nhưng chưa có file input thật.

## Thuật ngữ chính

- Real data: dữ liệu thật từ nguồn bên ngoài hoặc file teammate/source thật, không phải sample fixture tự tạo trong test.
- Ingestion contract: cấu trúc Pydantic chuẩn của project gồm `RawListing`, `NormalizedListing`, `RejectedListing`, `IngestionBatch`.
- Persistence: quá trình lưu dữ liệu vào database một cách bền vững.
- EDA: phân tích khám phá dữ liệu, gồm shape, missing values, duplicates, outliers, distribution và kết luận.
- DB-backed API: endpoint FastAPI đọc dữ liệu từ database, không trả mock data hardcoded.
- Dashboard slice: phần dashboard nhỏ nhưng dùng được, hiển thị dữ liệu thật hoặc thống kê thật.
- Gate: điểm kiểm soát. Chưa qua gate trước thì không được chuyển sang gate sau.

## Quy tắc không được vi phạm

1. Không dùng sample fixture để giả làm dữ liệu thật của Phase 3.5.
2. Không viết kết luận EDA nếu chưa có dữ liệu thật đã persist.
3. Không thêm endpoint API trả mock data rồi gọi đó là backend thật.
4. Không làm dashboard trang trí nếu không đọc dữ liệu thật.
5. Không train ML trong phase này.
6. Không commit raw dumps, `.env`, database dumps, model artifacts hoặc notebook outputs.
7. Không scrape live không giới hạn. Nếu dùng collector live thì phải có limit, timeout, delay và mô tả rõ.

## Gate 1: Chọn nguồn dữ liệu thật

Hiện tại gate này chưa qua vì workspace chưa có dataset listing thật.

Có ba hướng hợp lệ, nhưng phải giữ đúng source strategy của đề bài:

1. User cung cấp snapshot thật từ Domclick trên máy: JSON, JSONL, HTML snapshot, hoặc export đã lưu từ Domclick.
2. User cho phép implement collector live có kiểm soát cho Domclick, có limit, delay và không scrape search page bị disallow.
3. User cung cấp file teammate-source thật như nguồn phụ sau khi Domclick path đã có. File teammate không thay thế Domclick làm nguồn chính.

Không dùng public dataset bất kỳ để thay thế Domclick, trừ khi user đổi yêu cầu project. Dùng dataset ngoài có thể làm project lệch khỏi câu chuyện Domclick + OSM trong Phase 0 và yêu cầu môn học.

Bằng chứng hoàn thành gate:

- Có đường dẫn snapshot Domclick thật, hoặc có permission rõ ràng cho collector live Domclick.
- Đã inspect sample nhỏ của nguồn, không dump toàn bộ file lớn.
- Đã ghi lại source name, source type, số dòng/listing dự kiến và field mapping ban đầu.

Nếu gate này chưa qua, không được chuyển sang persistence thật.

## Gate 2: Importer hoặc parser cho nguồn thật

Nếu dữ liệu là CSV đúng teammate contract thì dùng `import_teammate_csv` hiện có.

Nếu dữ liệu là Domclick-like JSON thì dùng `parse_domclick_payload` hiện có.

Nếu teammate-source có schema khác thì viết adapter nhỏ riêng cho source phụ đó, nhưng chỉ sau khi Domclick path đã có. Adapter phải trả về `IngestionBatch`.

Bằng chứng hoàn thành gate:

- Có test cho valid rows.
- Có test cho rejected rows.
- `raw_payload` giữ lại dữ liệu gốc.
- Rejected row có reason rõ ràng.
- Không drop row âm thầm.

## Gate 3: Persist dữ liệu thật vào PostgreSQL

Dữ liệu thật phải đi qua Alembic schema hiện có và persistence layer của Phase 3.

Command dự kiến:

```powershell
python -m realtyscope.database.real_data_ingestion --source-type <source-type> --source-path <source-path> --database-url <database-url> --json
```

Output cần có:

```json
{
  "source_type": "domclick_json",
  "source_path": "...",
  "records_seen": 0,
  "raw_inserted": 0,
  "raw_reused": 0,
  "listings_created": 0,
  "listings_updated": 0,
  "rejected_inserted": 0
}
```

Bằng chứng hoàn thành gate:

- Alembic upgrade chạy được trên database trống.
- Real ingestion command chạy được với nguồn thật.
- Có row counts cho các bảng:
  - `sources`
  - `ingestion_runs`
  - `raw_listings`
  - `listings`
  - `listing_source_links`
  - `rejected_listings`
- Counts khớp với JSON output của command.

## Gate 4: EDA thật

Notebook hiện tại mới là skeleton. Phase 3.5 phải biến nó thành EDA có kết luận dựa trên dữ liệu đã persist.

EDA cần có:

- số dòng và schema;
- missing values;
- duplicates hoặc duplicate-like listings;
- phân phối `price_rub`;
- phân phối diện tích;
- price per square meter;
- phân phối rooms/floor nếu có;
- coordinate coverage;
- tỷ lệ `is_ml_ready`;
- thống kê ingestion runs và rejected rows;
- kết luận tiếng Việt có dấu, nói rõ dữ liệu đã đủ hay chưa đủ để sang ML.

Bằng chứng hoàn thành gate:

- Notebook đọc từ `DATABASE_URL`.
- Có summary markdown riêng trong `docs/data/`.
- Kết luận không nói quá so với dữ liệu thật.

## Gate 5: API đầu tiên đọc database thật

Phase này chưa làm `/predict`. API đầu tiên chỉ nên là read path tối thiểu để chứng minh backend đã đọc dữ liệu thật.

Endpoint đề xuất:

- `GET /listings`: trả listing rows có `limit` và `offset` cơ bản.
- `GET /stats/data-quality`: trả counts, ML-ready count, rejected count, source/run summary.

Bằng chứng hoàn thành gate:

- Test API pass.
- Endpoint đọc từ database.
- Không có mock data hardcoded.
- Swagger vẫn hoạt động.

## Gate 6: Dashboard đầu tiên có dữ liệu thật

Dashboard không cần đẹp hoặc production-grade trong Phase 3.5, nhưng phải hữu ích.

Nội dung tối thiểu:

- tổng số listings;
- số listing ML-ready;
- số rejected rows;
- bảng preview listing;
- trạng thái source/ingestion run gần nhất.

Ưu tiên: Streamlit gọi FastAPI. Nếu cần fallback đọc database local thì phải nói rõ đó là đường development, không phải production path chính.

Bằng chứng hoàn thành gate:

- Streamlit page không còn chỉ là text placeholder.
- Có test hoặc kiểm tra chạy được.
- Không claim prediction hoặc ML readiness khi chưa có model.

## Gate 7: Verify, commit, checkpoint

Trước khi báo hoàn thành, phải chạy:

```powershell
python -m pytest -q
python -m ruff check .
python -m ruff format --check .
git diff --check
```

Nếu có PostgreSQL work, phải verify thêm:

```powershell
python -m alembic upgrade head
python -m realtyscope.database.real_data_ingestion --source-type <source-type> --source-path <source-path> --database-url <database-url> --json
```

Sau đó commit bằng Conventional Commit.

Nếu chỉ commit plan trước khi có nguồn dữ liệu thật:

```bash
git commit -m "docs: plan phase 3.5 real data slice"
```

Nếu đã hoàn thành lát cắt dữ liệu thật:

```bash
git commit -m "feat: add phase 3.5 real data slice"
```

Checkpoint mem0 cuối phiên phải ghi:

- commit hash;
- nguồn dữ liệu thật hoặc blocker nguồn dữ liệu;
- row counts;
- kết luận EDA nếu có;
- verification commands;
- bước tiếp theo.

## Định nghĩa hoàn thành Phase 3.5

Phase 3.5 chỉ được xem là hoàn thành khi tất cả điều sau đúng:

- Có nguồn Domclick thật đã chọn và dùng được.
- Dữ liệu thật được persist vào PostgreSQL qua Alembic schema.
- Có row counts thật.
- Có EDA conclusions thật.
- Có ít nhất API data endpoint đọc từ DB.
- Có dashboard slice nếu scope và chất lượng dữ liệu cho phép.
- Full verification pass.
- Có commit và checkpoint mem0.

Nếu chưa có nguồn Domclick thật, Phase 3.5 chưa hoàn thành. Trạng thái đúng lúc đó là “đang chờ Domclick source hoặc snapshot thật”, không phải “xong bằng sample data” hay “xong bằng public dataset không liên quan”.

## Câu hỏi cần user chốt

Để đi tiếp sang code thật, cần chọn một hướng:

1. Cung cấp snapshot Domclick thật trên máy.
2. Cho phép viết collector live Domclick có kiểm soát.
3. Sau khi Domclick path chạy được, cung cấp thêm teammate-source file nếu muốn tăng số nguồn.

Khuyến nghị: nếu có snapshot Domclick thật thì dùng snapshot trước. Nếu chưa có, chọn collector live có kiểm soát để câu chuyện project bám sát Domclick -> PostgreSQL -> EDA -> API/dashboard. OSM enrichment sẽ đi sau khi đã có tọa độ listing.
