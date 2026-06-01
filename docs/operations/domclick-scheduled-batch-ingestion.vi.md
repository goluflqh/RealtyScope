# Ingestion Batch Định Kỳ Cho Domclick

Ngày: 2026-06-01
Đối tượng đọc: user, người vận hành và agent tiếp tục RealtyScope sau Phase 3.5.

## Kế Hoạch Kỹ Thuật Cho User

Đây là hướng ingestion định kỳ theo từng batch, không phải scraper chạy liên tục 24/7. Mỗi lần chạy có input hữu hạn, giới hạn rõ ràng, bước inspect trước khi ghi database, bước commit tùy chọn, và một report JSON để audit.

Luồng chuẩn:

1. Chuẩn bị hoặc dùng lại một nguồn input:
   - thư mục snapshot `data/raw/domclick/YYYY-MM-DD/` đã có sẵn;
   - thư mục Chrome SSR `data/raw/domclick/YYYY-MM-DD-bulk/` đã có sẵn;
   - thư mục Chrome SSR mới được capture trong lúc chạy job; hoặc
   - file URL gồm các URL Domclick được phép truy cập để collector HTTP lấy snapshot có giới hạn.
2. Capture hoặc dùng lại snapshot. Hướng Chrome SSR dùng Chrome profile thật và ghi compact JSON vào `YYYY-MM-DD-bulk/`. Nếu capture từ URL file, job phải dùng `--max-urls`, `--delay-seconds`, `--timeout-seconds`, kiểm tra `robots.txt`, phát hiện QRATOR, và tạo `manifest.json`.
3. Chạy inspect bằng parser Pydantic hiện có của `realtyscope.database.real_data_ingestion`.
4. Nếu số record inspect được nhỏ hơn `--min-records`, hoặc số listing normalized/sạch nhỏ hơn `--min-normalized-records`, job fail trước khi ghi database. Với wrapper scheduled, ngưỡng sạch là 1000 listing normalized.
5. Chỉ ghi PostgreSQL qua SQLAlchemy khi có flag `--commit`.
6. Ghi report JSON vào `data/processed/domclick_reports/`; thư mục này đã bị git ignore.
7. Dùng subcommand `status` để xem trạng thái database hiện tại.

Entrypoint:

```powershell
.\.venv\Scripts\python.exe -m realtyscope.ingestion.domclick_scheduled_batch --help
```

## Capture Chrome SSR Hằng Ngày

Dùng lệnh này khi snapshot của hôm nay chưa có và máy Windows có thể truy cập Domclick hợp lệ bằng Chrome. Scope mặc định là căn hộ bán ở Moscow: `aids=2299` (`Москва`), offset `0..1980`, bước `20`, tối đa 100 trang search đã render và khoảng 2000 ứng viên thô. Vùng capture lớn hơn là cố ý, vì batch scheduled phải còn ít nhất 1000 listing normalized/sạch sau khi parser xử lý.

Lệnh dùng Chrome profile directory `Default`, tức directory thật của profile Chrome hiển thị là `Person 1` trên máy này. Lệnh không bypass QRATOR, CAPTCHA, login wall hoặc ranh giới truy cập khác; nếu gặp các trang đó thì job fail.

```powershell
$env:PYTHONIOENCODING="utf-8"
.\.venv\Scripts\python.exe -m realtyscope.ingestion.domclick_chrome_capture `
  --output-root data/raw/domclick `
  --collection-date 2026-06-02 `
  --profile-directory Default `
  --offset-start 0 `
  --offset-stop 1980 `
  --offset-step 20 `
  --max-pages 100 `
  --delay-seconds 3 `
  --min-records 1000 `
  --json
```

Output:

```text
data/raw/domclick/YYYY-MM-DD-bulk/
  manifest.json
  payloads/
    search-offset-000000.json
    search-offset-000020.json
```

Các file payload chứa compact JSON lấy từ `window.__SSR_STATE__`; chúng nằm trong `data/raw/` đã bị ignore và không được commit.

## Chạy Inspect-Only

Khi kiểm tra máy capture mới hoặc URL file mới, chạy inspect-only trước. Lệnh này tạo report nhưng không ghi PostgreSQL:

```powershell
$env:PYTHONIOENCODING="utf-8"
.\.venv\Scripts\python.exe -m realtyscope.ingestion.domclick_scheduled_batch run `
  --url-file data/raw/domclick-urls.txt `
  --output-root data/raw/domclick `
  --collection-date 2026-06-01 `
  --max-urls 50 `
  --delay-seconds 2 `
  --max-records 2000 `
  --min-records 1 `
  --min-normalized-records 1000 `
  --json
```

Nếu đã có thư mục snapshot do Chrome/operator capture sẵn và có `manifest.json`:

```powershell
.\.venv\Scripts\python.exe -m realtyscope.ingestion.domclick_scheduled_batch run `
  --source-path data/raw/domclick/2026-06-01-bulk `
  --max-records 2000 `
  --min-records 1 `
  --min-normalized-records 1000 `
  --json
```

## Chạy Commit Vào PostgreSQL

Trước khi job ghi database, chạy Alembic để schema đúng version mới nhất:

```powershell
$env:DATABASE_URL="postgresql+psycopg://realtyscope:realtyscope@localhost:5432/realtyscope"
.\.venv\Scripts\python.exe -m alembic upgrade head
```

Sau đó commit một batch hữu hạn:

```powershell
.\.venv\Scripts\python.exe -m realtyscope.ingestion.domclick_scheduled_batch run `
  --source-path data/raw/domclick/2026-06-01-bulk `
  --database-url $env:DATABASE_URL `
  --commit `
  --max-records 2000 `
  --min-records 1 `
  --min-normalized-records 1000 `
  --json
```

Persistence hiện tại có tính idempotent cho raw payload lặp lại. Nếu chạy lại cùng dữ liệu, report nên cho thấy raw row được reuse và listing được update, không tạo trùng canonical listing hoặc observation. Nếu Domclick trả cùng ranking search mỗi ngày, bảng canonical `listings` chủ yếu sẽ refresh cùng một lát cắt. Lịch sử `listing_observations` chỉ tăng khi raw snapshot thay đổi đủ để tạo raw row mới, ví dụ giá thay đổi cho cùng `source_listing_id`.

## Status Và Report

Xem trạng thái database:

```powershell
.\.venv\Scripts\python.exe -m realtyscope.ingestion.domclick_scheduled_batch status `
  --database-url $env:DATABASE_URL `
  --json
```

Report runtime được ghi vào:

```text
data/processed/domclick_reports/domclick-<timestamp>.json
```

Report chỉ chứa counts, path, status và lỗi tóm tắt. Report không chứa raw payload.

## Windows Task Scheduler

Dùng Windows Task Scheduler khi capture phụ thuộc vào máy Windows, Chrome profile thật, hoặc route mạng do operator quản lý.

Repo hiện có wrapper script cho Windows, tự chọn ngày theo giờ Moscow:

```powershell
.\scripts\run_domclick_scheduled_batch.ps1
```

Script chọn input theo thứ tự ưu tiên:

1. `data/raw/domclick/YYYY-MM-DD/`
2. `data/raw/domclick/YYYY-MM-DD-bulk/`
3. Nếu cả hai thư mục trên chưa có, chạy Chrome SSR capture vào `data/raw/domclick/YYYY-MM-DD-bulk/`.
4. Nếu truyền `-SkipCapture`, fallback sang `data/raw/domclick-urls.txt` khi file này tồn tại.

Script tự bật PostgreSQL bằng WSL Docker trừ khi truyền `-SkipDockerStart`, chạy Alembic, capture Chrome SSR cho hôm nay nếu snapshot chưa có, chạy bounded batch với `--commit`, và ghi log vào `data/processed/runtime_logs/`.

Thiết lập khuyến nghị:

- Trigger: chạy hằng ngày hoặc vài giờ một lần, không dùng vòng lặp vô hạn.
- Program: `powershell.exe`.
- Start in: root của repo RealtyScope.
- Chỉ cho một instance chạy tại một thời điểm.
- Stop task nếu chạy lâu hơn thời gian batch dự kiến.
- Bật task history và theo dõi exit code khác 0.

Ví dụ arguments cho job commit từ thư mục snapshot đã capture sẵn:

```powershell
-NoProfile -ExecutionPolicy Bypass -Command "$env:PYTHONIOENCODING='utf-8'; $env:DATABASE_URL='postgresql+psycopg://realtyscope:realtyscope@localhost:5432/realtyscope'; Set-Location 'E:\Магистр\2-курс\python\RealtyScope'; .\.venv\Scripts\python.exe -m alembic upgrade head; .\.venv\Scripts\python.exe -m realtyscope.ingestion.domclick_scheduled_batch run --source-path data/raw/domclick/2026-06-01-bulk --database-url $env:DATABASE_URL --commit --max-records 2000 --min-records 1 --min-normalized-records 1000 --json"
```

Nếu task capture từ URL file, truyền `-SkipCapture` và chuẩn bị `data/raw/domclick-urls.txt`; hướng này vẫn không được dùng `/search` khi `robots.txt` cấm fetch HTTP trực tiếp. Hướng scheduled mặc định chỉ capture SSR state của `/search` sau khi Chrome profile `Default` render trang, và sẽ dừng nếu Domclick trả QRATOR, CAPTCHA hoặc login wall.

Task đã được cài trên máy dev hiện có tên `RealtyScope Domclick Scheduled Batch` và chạy hằng ngày lúc 15:00 theo giờ Moscow.

## WSL Cron

Dùng WSL cron cho các job offline ingest/status khi snapshot đã có sẵn. Không dùng lại Windows `.venv` trong WSL; phải cài môi trường Linux riêng từ `uv.lock`.

Ví dụ crontab:

```cron
15 3 * * * cd /mnt/e/Магистр/2-курс/python/RealtyScope && export DATABASE_URL='postgresql+psycopg://realtyscope:realtyscope@localhost:5432/realtyscope' && uv run python -m alembic upgrade head && uv run python -m realtyscope.ingestion.domclick_scheduled_batch run --source-path data/raw/domclick/$(date +\%F) --database-url "$DATABASE_URL" --commit --max-records 2000 --min-records 1 --min-normalized-records 1000 --json >> data/processed/domclick_reports/cron.log 2>&1
```

## Systemd Timer

Trên VPS Linux, nên dùng systemd service cộng systemd timer. Secrets nên nằm trong environment file ngoài git, ví dụ `/etc/realtyscope/domclick-ingestor.env`.

Service mẫu:

```ini
[Unit]
Description=RealtyScope Domclick scheduled batch ingestion

[Service]
Type=oneshot
WorkingDirectory=/opt/realtyscope
EnvironmentFile=/etc/realtyscope/domclick-ingestor.env
ExecStart=/opt/realtyscope/.venv/bin/python -m alembic upgrade head
ExecStart=/opt/realtyscope/.venv/bin/python -m realtyscope.ingestion.domclick_scheduled_batch run --source-path data/raw/domclick/current --database-url ${DATABASE_URL} --commit --max-records 2000 --min-records 1 --min-normalized-records 1000 --json
```

Timer mẫu:

```ini
[Unit]
Description=Run RealtyScope Domclick batch daily

[Timer]
OnCalendar=*-*-* 03:15:00
Persistent=true

[Install]
WantedBy=timers.target
```

Trỏ `data/raw/domclick/current` tới thư mục ngày mới nhất đã copy về, hoặc dùng wrapper script nhỏ do deployment quản lý và đặt ngoài git nếu cần date động. Không đặt vòng lặp chạy mãi trong Python process.

## Chính Sách Fail

Scheduled job phải được xem là fail khi:

- capture bị chặn bởi `robots.txt`, QRATOR, CAPTCHA, login wall hoặc HTTP error;
- không tìm thấy Chrome, profile cấu hình bị thiếu/bị khóa, hoặc không có SSR state sau khi render;
- không có file snapshot parseable;
- inspect trả ít row hơn `--min-records`;
- inspect trả ít listing normalized/sạch hơn `--min-normalized-records`;
- Alembic hoặc SQLAlchemy commit lỗi;
- report có `"status": "failed"` hoặc process exit khác 0.

Raw snapshot vẫn nằm trong `data/raw/` và không được commit. Report runtime nằm trong `data/processed/` và cũng không commit.
