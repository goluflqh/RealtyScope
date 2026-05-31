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

1. Chạy collector hoặc lưu snapshot bằng browser trên máy có IP Nga.
2. Đặt file vào `data/raw/domclick/YYYY-MM-DD/` theo cấu trúc ở trên.
3. Nếu collector chạy trên máy khác, copy nguyên thư mục ngày về máy chạy RealtyScope.
4. Chạy Alembic để database ở đúng schema mới nhất.
5. Ingest cả thư mục snapshot:

```powershell
python -m realtyscope.database.real_data_ingestion `
  --source-type domclick_snapshot_dir `
  --source-path data/raw/domclick/2026-05-31 `
  --database-url $env:DATABASE_URL `
  --json
```

6. Ghi lại JSON output và row counts vào checkpoint Phase 3.5.

## Cách Lên Lịch Chạy Tự Động

Có thể dùng một trong các cách sau:

- Windows Task Scheduler trên máy có IP Nga.
- `cron` hoặc `systemd timer` trên VPS/Linux ở Nga.
- Docker container trên host có IP Nga, miễn là secrets và dữ liệu thô không nằm trong git.

Job hằng ngày phải báo lỗi rõ nếu lấy được 0 record, bị chặn, hoặc không ghi được snapshot parseable.

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
