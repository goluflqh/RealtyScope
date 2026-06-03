# Kịch Bản Demo RealtyScope

Ngày: 2026-06-03
Branch: `phase7-course-readiness-polish`
Đối tượng: reviewer môn học, người vận hành project, và các phiên demo sau.

Tài liệu này là đường đi demo ngắn để trình bày RealtyScope mà không cần đọc lại toàn bộ lịch sử project. Giả định repo đã có trên Windows workstation và WSL2 Ubuntu có Docker.

## 0. Nói Gì Trước Khi Demo

RealtyScope là data-service project hướng grade 5 cho bài toán phân tích và dự đoán giá căn hộ Moscow. Hệ thống hiện chứng minh được:

- thu thập dữ liệu Domclick theo batch có giới hạn và lưu PostgreSQL;
- bằng chứng data-quality và observation history;
- FastAPI endpoints cho data, prediction, model metadata và monitoring;
- Redis cache cho read path `/data` và `/listings`;
- Streamlit dashboard có filters, reviewer charts, coordinate map, baseline prediction, monitoring và model insights;
- Docker Compose runtime với PostgreSQL, Redis, MLflow, FastAPI và Streamlit;
- MLflow evidence cho non-leaky Ridge baseline model.

Caveat quan trọng: model hiện là baseline appraisal model trung thực, không phải estimator production cuối cùng. Không nên nói quá về forecast-vs-actual hoặc trend cho tới khi freshness của repeated observations được kiểm tra thêm.

## 1. Khởi Động Runtime

Chạy từ PowerShell. Dùng WSL2 vì Docker không có trong PowerShell PATH trên máy này.

```powershell
wsl -d Ubuntu -- bash -lc "cd /mnt/e/Магистр/2-курс/python/RealtyScope && docker compose -p realtyscope up --build -d"
```

Kiểm tra trạng thái service:

```powershell
wsl -d Ubuntu -- bash -lc "cd /mnt/e/Магистр/2-курс/python/RealtyScope && docker compose -p realtyscope ps"
```

Evidence mong đợi:

- `db`, `redis`, `api`, và `streamlit` healthy;
- `mlflow` chạy trên port `5000`;
- local ports `8000`, `8501`, và `5000` được publish.

## 2. Trình Bày FastAPI Và Swagger

Mở trong browser:

- FastAPI health: http://localhost:8000/health
- FastAPI Swagger/OpenAPI: http://localhost:8000/docs

Smoke checks nhanh bằng terminal:

```powershell
wsl -d Ubuntu -- bash -lc "curl -sS http://localhost:8000/health | python3 -m json.tool"
wsl -d Ubuntu -- bash -lc "curl -sS 'http://localhost:8000/data?limit=3&offset=0' | python3 -m json.tool"
wsl -d Ubuntu -- bash -lc "curl -sS 'http://localhost:8000/data?limit=3&offset=0&rooms=2&min_price_rub=10000000' | python3 -m json.tool"
wsl -d Ubuntu -- bash -lc "curl -sS http://localhost:8000/model/metadata | python3 -m json.tool"
wsl -d Ubuntu -- bash -lc "curl -sS http://localhost:8000/monitoring/status | python3 -m json.tool"
```

Điểm cần chỉ ra:

- `/data` phù hợp yêu cầu bài và đọc từ persisted PostgreSQL rows;
- filters có price range, area range, rooms, source, address/city search;
- `/model/metadata` trả `realtyscope-price-model`, model version `baseline_ridge_v2_non_leaky`, feature version `ml_features_v2_non_leaky`, 23 features và validation metrics;
- `/monitoring/status` hiển thị data-quality counts, latest ingestion run status, model status và recent errors.

## 3. Chứng Minh Redis Cache

Gọi read path nhỏ để populate cache:

```powershell
wsl -d Ubuntu -- bash -lc "curl -sS -o /dev/null -w '%{http_code}' 'http://localhost:8000/data?limit=3&offset=0'"
```

Kiểm tra Redis key mà không dump payload đầy đủ:

```powershell
wsl -d Ubuntu -- bash -lc "cd /mnt/e/Магистр/2-курс/python/RealtyScope && docker compose -p realtyscope exec -T redis redis-cli --scan --pattern 'realtyscope:*' | sort | head -20"
wsl -d Ubuntu -- bash -lc "cd /mnt/e/Магистр/2-курс/python/RealtyScope && docker compose -p realtyscope exec -T redis redis-cli EXISTS 'realtyscope:listings:v1:limit=3:offset=0'"
wsl -d Ubuntu -- bash -lc "cd /mnt/e/Магистр/2-курс/python/RealtyScope && docker compose -p realtyscope exec -T redis redis-cli TTL 'realtyscope:listings:v1:limit=3:offset=0'"
wsl -d Ubuntu -- bash -lc "cd /mnt/e/Магистр/2-курс/python/RealtyScope && docker compose -p realtyscope exec -T redis redis-cli STRLEN 'realtyscope:listings:v1:limit=3:offset=0'"
```

Evidence mong đợi:

- HTTP status là `200`;
- `EXISTS` trả `1`;
- `TTL` là số dương ngắn, tối đa `60` giây;
- `STRLEN` lớn hơn `0`.

Nếu `TTL` trả `-2`, key ngắn hạn đã hết hạn. Gọi lại `/data?limit=3&offset=0` rồi kiểm tra Redis lần nữa.

## 4. Trình Bày Streamlit Dashboard

Mở:

- Streamlit: http://localhost:8501

Đường đi demo:

1. Chỉ KPI cards: listings, ML-ready rows, rejected rows, ingestion runs.
2. Chỉ bảng latest ingestion run và monitoring section.
3. Dùng sidebar filters:
   - đặt `Rows` là `100` hoặc `500`;
   - đặt `Min price (RUB)` là `10000000`;
   - đặt `Rooms` là `2`;
   - có thể search một đoạn city/address.
4. Chỉ `Listing preview` thay đổi theo filtered API query.
5. Chỉ `Reviewer visuals`:
   - `Price distribution`;
   - `Median price by rooms`;
   - `Listing map`.
6. Chỉ attribution OpenStreetMap nằm dưới map. Map dùng persisted listing coordinates và không gọi live OSM/Overpass.
7. Trong `Baseline prediction`, giữ default values hoặc chỉnh area/rooms/floor, rồi bấm `Run baseline prediction`.
8. Chỉ predicted price, model version, feature version, caveat và metrics summary.
9. Chỉ `Model insights` với feature importance.

## 5. Trình Bày MLflow Evidence

Mở:

- MLflow: http://localhost:5000

Điểm cần chỉ ra:

- registered model: `realtyscope-price-model`;
- verified model version: `3`;
- run ID: `4999892d2d92402ab78e1209203c338e`;
- model URI: `runs:/4999892d2d92402ab78e1209203c338e/model`;
- artifact path: `data/processed/models/phase5/baseline_ridge_v2_non_leaky.joblib`.

REST checks tùy chọn:

```powershell
wsl -d Ubuntu -- bash -lc "python3 -c \"import json, urllib.request; run_id='4999892d2d92402ab78e1209203c338e'; data=json.load(urllib.request.urlopen(f'http://localhost:5000/api/2.0/mlflow/runs/get?run_id={run_id}')); print(data['run']['info']['status'])\""
wsl -d Ubuntu -- bash -lc "python3 -c \"import json, urllib.parse, urllib.request; name=urllib.parse.quote('realtyscope-price-model'); data=json.load(urllib.request.urlopen(f'http://localhost:5000/api/2.0/mlflow/registered-models/get?name={name}')); print([(v['version'], v['run_id']) for v in data['registered_model'].get('latest_versions', [])])\""
```

## 6. Tái Chạy Trainer Nếu Reviewer Hỏi

Chỉ chạy bước này nếu reviewer muốn reproduce MLflow training evidence. Bước này lâu hơn demo API/dashboard.

```powershell
wsl -d Ubuntu -- bash -lc "cd /mnt/e/Магистр/2-курс/python/RealtyScope && docker compose -p realtyscope --profile tools run --build --rm trainer"
```

Sau khi chạy xong, refresh MLflow và `/model/metadata`.

## 7. Dừng Sạch Không Mất Dữ Liệu

Với demo thường ngày, dừng service nhưng giữ named volumes:

```powershell
wsl -d Ubuntu -- bash -lc "cd /mnt/e/Магистр/2-курс/python/RealtyScope && docker compose -p realtyscope stop"
```

Hoặc xóa containers và Compose network nhưng vẫn giữ named volumes:

```powershell
wsl -d Ubuntu -- bash -lc "cd /mnt/e/Магистр/2-курс/python/RealtyScope && docker compose -p realtyscope down"
```

Không chạy các lệnh phá dữ liệu dưới đây trong lúc chuẩn bị nộp, trừ khi mục tiêu là reset toàn bộ và đã export dữ liệu/artifacts cần giữ:

```powershell
# Phá dữ liệu: xóa PostgreSQL, Redis, MLflow, và model artifact volumes của Compose project này.
wsl -d Ubuntu -- bash -lc "cd /mnt/e/Магистр/2-курс/python/RealtyScope && docker compose -p realtyscope down -v"

# Phá rộng hơn: có thể xóa Docker volumes của project khác.
wsl -d Ubuntu -- bash -lc "docker system prune --volumes"
```

## 8. Final Verification Commands

Chạy các lệnh này trước khi claim final readiness:

```powershell
git diff --check
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m ruff format --check .
.\.venv\Scripts\python.exe -m pytest -p no:cacheprovider
wsl -d Ubuntu -- bash -lc "cd /mnt/e/Магистр/2-курс/python/RealtyScope && docker compose -p realtyscope ps"
wsl -d Ubuntu -- bash -lc "curl -sS -o /dev/null -w '%{http_code}' http://localhost:8000/health"
wsl -d Ubuntu -- bash -lc "curl -sS -o /dev/null -w '%{http_code}' http://localhost:8501"
```

Sau đó đợi GitHub Actions `ci` trên active branch, và sau merge cuối thì đợi `ci` trên `main`.
