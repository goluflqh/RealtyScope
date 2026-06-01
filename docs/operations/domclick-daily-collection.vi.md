# Thu Thập Snapshot Domclick Hằng Ngày

Ngày: 2026-05-31
Đối tượng đọc: user, giảng viên và agent tiếp tục Phase 3.5.

## Mục Đích

Domclick có thể phụ thuộc vào vị trí mạng và cơ chế chống bot. Vì vậy RealtyScope tách hai việc ra riêng:

- Máy có thể truy cập Domclick bằng IP Nga chỉ làm nhiệm vụ lấy snapshot thô hằng ngày.
- Repo RealtyScope làm nhiệm vụ parse offline, validate dữ liệu, lưu PostgreSQL, chạy EDA, mở API và dashboard.

Cách này giải quyết vấn đề hiện tại: Codex không cần truy cập trực tiếp Domclick live. Chỉ cần có thư mục snapshot thật được lưu lại, pipeline trong repo vẫn có thể chạy, test và verify đầy đủ.

## Quy Tắc Không Được Vi Phạm

- Không scrape `/search` khi `robots.txt` đang cấm đường dẫn này.
- Không bypass QRATOR, CAPTCHA, login wall hoặc cơ chế chống bot.
- Collector phải có giới hạn số record, timeout và delay rõ ràng.
- Chỉ commit code và tài liệu. Không commit raw snapshot, database dump, `.env` hoặc artifact sinh ra.
- Mỗi lần thu thập phải có manifest để audit: lấy từ URL nào, lúc nào, file nào, HTTP status gì, hash nội dung là gì.

## Cấu Trúc Thư Mục Snapshot

Snapshot thật nên đặt trong vùng đã bị `.gitignore` loại khỏi git:

```text
data/raw/domclick/YYYY-MM-DD/
  manifest.json
  pages/
    listing-001.html
    listing-002.html
  payloads/
    listings-001.json
```

`manifest.json` nên có tối thiểu:

```json
{
  "source_name": "domclick",
  "collection_date": "2026-05-31",
  "collector_version": "manual-or-script-name",
  "network_note": "RU IP route used by operator",
  "entries": [
    {
      "source_url": "https://domclick.ru/...",
      "source_type": "domclick_html",
      "path": "pages/listing-001.html",
      "fetched_at": "2026-05-31T12:00:00Z",
      "http_status": 200,
      "content_sha256": "..."
    }
  ]
}
```

Ingestor hiện tại bỏ qua `manifest.json` như dữ liệu input và scan đệ quy các file `.json`, `.html`, `.htm` trong thư mục ngày.

## Quy Trình Vận Hành Hằng Ngày

1. Chuẩn bị file URL, mỗi dòng là một URL Domclick được phép truy cập. Dùng listing/detail/card hoặc URL public được phép. Không đưa `/search` vào file này.
2. Chạy collector trên máy có IP Nga:

```powershell
python -m realtyscope.ingestion.domclick_snapshot_collector `
  --url-file data/raw/domclick-urls.txt `
  --output-root data/raw/domclick `
  --collection-date 2026-05-31 `
  --delay-seconds 2 `
  --json
```

Collector sẽ kiểm tra `robots.txt`, từ chối URL bị cấm trước khi fetch, dừng nếu gặp QRATOR challenge, ghi HTML vào `pages/`, ghi JSON vào `payloads/`, và tạo `manifest.json`.

## Capture Search SSR Bằng Chrome

Với workflow hiện tại trên máy Windows, lệnh capture hằng ngày sẽ render trang search căn hộ bán ở Moscow bằng Chrome rồi lưu SSR state của trang thành compact JSON. Hướng này tách riêng với collector HTTP trực tiếp ở trên: nó không raw-fetch `/search`, và sẽ dừng nếu Chrome gặp QRATOR, CAPTCHA, login wall hoặc không thấy SSR state sau khi render.

Scope mặc định:

- Chrome profile hiển thị là `Person 1`, nhưng directory thật trên máy này là `Default`.
- Domclick Moscow area id `aids=2299` (`Москва`).
- URL template: `https://domclick.ru/search?deal_type=sale&category=living&offer_type=flat&offer_type=layout&aids=2299&offset={offset}`.
- Offset `0..1980`, bước `20`, tối đa 100 trang và khoảng 2000 ứng viên thô mỗi ngày. Phần dư này là cố ý, vì scheduled gate yêu cầu ít nhất 1000 listing normalized/sạch sau khi parser xử lý.

Lệnh chạy:

```powershell
$env:PYTHONIOENCODING="utf-8"
.\.venv\Scripts\python.exe -m realtyscope.ingestion.domclick_chrome_capture `
  --output-root data/raw/domclick `
  --collection-date 2026-06-02 `
  --profile-directory Default `
  --delay-seconds 3 `
  --json
```

Lệnh ghi `data/raw/domclick/YYYY-MM-DD-bulk/manifest.json` và compact JSON trong `payloads/`. Raw data vẫn bị git ignore và không được commit.

3. Nếu máy hiện tại không truy cập được Domclick, chạy cùng command trên host có IP Nga rồi copy nguyên thư mục ngày về máy chạy RealtyScope.
4. Inspect snapshot trước khi ghi vào PostgreSQL:

```powershell
python -m realtyscope.database.real_data_ingestion `
  --source-type domclick_snapshot_dir `
  --source-path data/raw/domclick/2026-05-31 `
  --inspect-only `
  --json
```

Bước inspect dùng cùng parser với persistence và báo `records_seen`, số row normalized, số row rejected, số row sẵn sàng cho ML. Lệnh này không cần database connection và không ghi dữ liệu.

5. Chạy Alembic để database ở đúng schema mới nhất.
6. Ingest cả thư mục snapshot:

```powershell
python -m realtyscope.database.real_data_ingestion `
  --source-type domclick_snapshot_dir `
  --source-path data/raw/domclick/2026-05-31 `
  --database-url $env:DATABASE_URL `
  --json
```

7. Tạo EDA summary từ chính database đã persist:

```powershell
python -m realtyscope.analysis.eda_summary `
  --database-url $env:DATABASE_URL `
  --output docs/data/phase3_5_eda_summary.vi.md `
  --json
```

8. Ghi lại JSON output của ingestion, row counts trong database và đường dẫn EDA summary vào checkpoint Phase 3.5.

## Cách Lên Lịch Chạy Tự Động

Hướng được ưu tiên cho vận hành định kỳ là batch runner có giới hạn, được mô tả đầy đủ trong
`docs/operations/domclick-scheduled-batch-ingestion.md` và
`docs/operations/domclick-scheduled-batch-ingestion.vi.md`:

```powershell
python -m realtyscope.ingestion.domclick_scheduled_batch run `
  --source-path data/raw/domclick/2026-06-01 `
  --database-url $env:DATABASE_URL `
  --commit `
  --max-records 2000 `
  --min-records 1 `
  --min-normalized-records 1000 `
  --json
```

Dùng `status` để xem counts trong database và trạng thái run gần nhất:

```powershell
python -m realtyscope.ingestion.domclick_scheduled_batch status `
  --database-url $env:DATABASE_URL `
  --json
```

Có thể dùng một trong các cách sau:

- Windows Task Scheduler trên máy có IP Nga.
- `cron` hoặc `systemd timer` trên VPS/Linux ở Nga.
- Docker container trên host có IP Nga, miễn là secrets và dữ liệu thô không nằm trong git.

Job hằng ngày phải báo lỗi rõ nếu lấy được 0 record, bị chặn, không ghi được snapshot parseable, hoặc inspect được ít hơn 1000 listing normalized/sạch.

## Kiểm Tra Chất Lượng Sau Mỗi Lần Chạy

Mỗi run nên ghi lại:

- số file đã thu thập;
- số records nhìn thấy;
- số raw rows inserted hoặc reused;
- số listings created hoặc updated;
- số rejected rows và lý do reject phổ biến;
- tỷ lệ có tọa độ;
- số listing sẵn sàng cho ML;
- thời điểm run thành công gần nhất.

Phase 3.5 chỉ được coi là hoàn thành khi có row Domclick thật trong PostgreSQL, có counts thật, có kết luận EDA từ dữ liệu đó, và có ít nhất một API read path đọc từ database.
