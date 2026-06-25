# Quy Ước Môi Trường Local Cho RealtyScope

Tài liệu này chốt cách chia môi trường để RealtyScope không phụ thuộc vào package global chỉ có trên máy của một người.

## Vai Trò Từng Môi Trường

- Windows là lớp làm việc: Codex Desktop, Chrome profile riêng cho automation scheduled capture, capture Domclick bằng trình duyệt, editor và lệnh phát triển hằng ngày.
- Python trên Windows phải dùng `.venv` riêng của repo; không dựa vào `C:\Program Files\Python312\Lib\site-packages` hoặc Anaconda cho lệnh dự án.
- WSL2 Ubuntu là lớp runtime Linux local: Docker, PostgreSQL, Redis, MLflow và các kiểm chứng giống môi trường production.
- VPS/production sau này phải đi theo giả định Linux/Docker giống WSL2, không phụ thuộc vào package global trên Windows.

## Nguồn Sự Thật Của Dependency

- `pyproject.toml` khai báo dependency trực tiếp và các nhóm optional extras.
- `uv.lock` khóa dependency graph để CI/Linux/agent có thể cài tái lập.
- `.venv/` là local, phụ thuộc hệ điều hành, bị git ignore và phải tạo lại trên từng máy.
- Raw snapshot, database dump, `.env` và artifact runtime không được commit.

## Cài Môi Trường Làm Việc Trên Windows

Chạy từ root của repo trong PowerShell:

```powershell
python -m venv .venv
$env:PYTHONIOENCODING="utf-8"
$env:PIP_NO_COLOR="1"
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e ".[dev,data,api,streamlit]"
```

Dùng `.venv` cho lệnh Python:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m ruff format --check .
```

Biến `PYTHONIOENCODING=utf-8` giúp tránh lỗi encoding trên Windows khi đường dẫn repo có ký tự Cyrillic.

## Runtime PostgreSQL/Docker Trong WSL2

Dùng WSL2 cho lệnh Docker vì Docker không có trong PowerShell PATH của máy này.

Khởi động toàn bộ stack demo/runtime từ root của repo:

```powershell
wsl -d Ubuntu -- bash -lc "cd /mnt/e/Магистр/2-курс/python/RealtyScope-stitch-hybrid-redesign-20260623 && docker compose -p realtyscope up --build -d"
```

Kiểm tra trạng thái service:

```powershell
wsl -d Ubuntu -- bash -lc "cd /mnt/e/Магистр/2-курс/python/RealtyScope-stitch-hybrid-redesign-20260623 && docker compose -p realtyscope ps"
```

Chỉ chạy PostgreSQL khi cần database cho migration hoặc ingestion check mà không cần toàn bộ app stack:

```powershell
wsl -d Ubuntu -- bash -lc "cd /mnt/e/Магистр/2-курс/python/RealtyScope-stitch-hybrid-redesign-20260623 && docker compose -p realtyscope up -d db"
```

Các lệnh Python trong Windows `.venv` kết nối tới PostgreSQL trong WSL2 qua `localhost:5432`:

```powershell
$env:DATABASE_URL="postgresql+psycopg://realtyscope:realtyscope@localhost:5432/realtyscope"
.\.venv\Scripts\python.exe -m alembic upgrade head
```

### Bằng Chứng Runtime Cho Redis Cache

API cache payload của `/data` và `/listings` vào Redis với TTL ngắn. Key hiện tại cho preview nhỏ là `realtyscope:listings:v2:limit=3:offset=0`, TTL 60 giây. Ở đây `limit=3` nghĩa là ba dòng listing để kiểm chứng cache nhẹ, không phải số ngày quan sát.

Gọi API read path để populate cache:

```powershell
wsl -d Ubuntu -- bash -lc "cd /mnt/e/Магистр/2-курс/python/RealtyScope-stitch-hybrid-redesign-20260623 && curl -sS -o /dev/null -w '%{http_code}' 'http://localhost:8000/data?limit=3&offset=0'"
```

Kiểm tra Redis có key runtime mà không dump toàn bộ JSON payload:

```powershell
wsl -d Ubuntu -- bash -lc "cd /mnt/e/Магистр/2-курс/python/RealtyScope-stitch-hybrid-redesign-20260623 && docker compose -p realtyscope exec -T redis redis-cli --scan --pattern 'realtyscope:*' | sort | head -20"
wsl -d Ubuntu -- bash -lc "cd /mnt/e/Магистр/2-курс/python/RealtyScope-stitch-hybrid-redesign-20260623 && docker compose -p realtyscope exec -T redis redis-cli EXISTS 'realtyscope:listings:v2:limit=3:offset=0'"
wsl -d Ubuntu -- bash -lc "cd /mnt/e/Магистр/2-курс/python/RealtyScope-stitch-hybrid-redesign-20260623 && docker compose -p realtyscope exec -T redis redis-cli TTL 'realtyscope:listings:v2:limit=3:offset=0'"
wsl -d Ubuntu -- bash -lc "cd /mnt/e/Магистр/2-курс/python/RealtyScope-stitch-hybrid-redesign-20260623 && docker compose -p realtyscope exec -T redis redis-cli STRLEN 'realtyscope:listings:v2:limit=3:offset=0'"
```

Bằng chứng kỳ vọng: HTTP `200`, `EXISTS` trả `1`, `TTL` trả giá trị từ `0` đến `60`, và `STRLEN` lớn hơn `0`. Nếu `TTL` trả `-2`, key TTL ngắn đã hết hạn; gọi lại `/data?limit=3&offset=0` rồi kiểm tra Redis lần nữa.

## Dừng Runtime Và Cleanup Storage An Toàn

Dùng cleanup không phá hủy dữ liệu cho phát triển thường ngày và demo:

```powershell
wsl -d Ubuntu -- bash -lc "cd /mnt/e/Магистр/2-курс/python/RealtyScope-stitch-hybrid-redesign-20260623 && docker compose -p realtyscope stop"
wsl -d Ubuntu -- bash -lc "cd /mnt/e/Магистр/2-курс/python/RealtyScope-stitch-hybrid-redesign-20260623 && docker compose -p realtyscope down"
```

`stop` giữ container và toàn bộ named volume. `down` xóa container và Compose network, nhưng vẫn giữ named volume nếu không thêm `-v`.

Luôn kiểm tra storage trước khi xóa:

```powershell
wsl -d Ubuntu -- bash -lc "cd /mnt/e/Магистр/2-курс/python/RealtyScope-stitch-hybrid-redesign-20260623 && docker compose -p realtyscope config --volumes"
wsl -d Ubuntu -- bash -lc "docker volume ls | grep realtyscope"
```

Các Docker-managed volume quan trọng là `postgres_data`, `redis_data`, `mlflow_data`, và `model_artifacts`, với Compose project prefix được thêm khi runtime chạy. Chúng chứa database rows, Redis state, MLflow metadata/artifacts, và file model đã train dùng trong demo.

Chỉ chạy cleanup phá hủy khi thật sự muốn reset evidence và đã export mọi thứ cần giữ:

```powershell
wsl -d Ubuntu -- bash -lc "cd /mnt/e/Магистр/2-курс/python/RealtyScope-stitch-hybrid-redesign-20260623 && docker compose -p realtyscope down -v"
```

Không dùng `docker system prune --volumes` trong lúc course-readiness trừ khi mục tiêu là reset toàn bộ Docker storage. Lệnh đó có thể xóa cả volume của dự án khác.

Raw snapshots và reports/artifacts sinh ra dưới `data/raw/` và `data/processed/` là runtime evidence bị git ignore. Chỉ xóa chúng khi cố ý reset captured data hoặc model/report outputs.

## Cài Đặt Khóa Dependency Cho CI/Linux

CI và môi trường Linux/VPS nên cài theo `uv.lock`:

```bash
python -m pip install uv==0.11.3
UV_LINK_MODE=copy uv sync --frozen --extra dev --extra data --extra api --extra streamlit
uv run pytest -q
uv run ruff check .
uv run ruff format --check .
```

Không dùng chung `.venv` của Windows trong WSL hoặc Linux. Mỗi hệ điều hành phải tạo environment riêng.

## Mẫu Kiểm Chứng Phase 3.5

```powershell
$env:DATABASE_URL="postgresql+psycopg://realtyscope:realtyscope@localhost:5432/realtyscope_phase35_verify"
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m realtyscope.database.real_data_ingestion --source-type domclick_snapshot_dir --source-path data/raw/domclick/2026-06-01 --inspect-only --json
.\.venv\Scripts\python.exe -m realtyscope.database.real_data_ingestion --source-type domclick_snapshot_dir --source-path data/raw/domclick/2026-06-01 --database-url $env:DATABASE_URL --json
.\.venv\Scripts\python.exe -m realtyscope.analysis.eda_summary --database-url $env:DATABASE_URL --output docs/data/phase3_5_eda_summary.vi.md --json
```
