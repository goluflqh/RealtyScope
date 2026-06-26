# Kịch Bản Demo RealtyScope

Ngày: 2026-06-03
Branch: `main` sau khi merge Phase 7
Đối tượng: reviewer môn học, người vận hành project, và các phiên demo sau.

Tài liệu này là đường đi demo ngắn để trình bày RealtyScope mà không cần đọc lại toàn bộ lịch sử project. Giả định repo đã có trên Windows workstation và WSL2 Ubuntu có Docker.

## Ghi Chú Nhánh UI Hiện Tại

Update 2026-06-26: scheduled run luc 00:00 gap Domclick QRATOR challenge, sau do controlled Chrome/CDP preflight thanh cong va bounded 50-page capture ghi `data/raw/domclick/2026-06-26-bulk` voi `1,000` records. Ingest report `data/processed/domclick_reports/domclick-20260626T012727-535110Z.json` commit run id `26`: `1,000` normalized records, `241` listings created, `759` updated, `999` observations inserted. Docker `/monitoring/status` hien bao `17,287` listings (`14,851` Domclick, `2,436` CIAN), `45,764` observations, `23` observation dates, va `last_observed_date=2026-06-26`. Caveat model: `/model/metadata` van serve selected `random_forest` artifact train truoc refresh voi `rows_total=17,046`; monitoring/UI hien `model.data_freshness.status=validated_snapshot`, `row_delta=241`, `requires_retrain=false`. Khong tu retrain chi vi co data moi; retrain chi qua promotion gate.

Với nhánh Stitch hybrid giữ lại, dùng workspace `E:\Магистр\2-курс\python\RealtyScope-stitch-hybrid-redesign-20260623` và branch `ui/stitch-hybrid-redesign-20260623`. Audit tĩnh/CDP mới nhất dùng payload API thật với `17,046` listings (`14,610` Домклик, `2,436` ЦИАН), `44,765` observations và `22` ngày quan sát từ `2026-05-14` đến `2026-06-24`.

Dong tren la branch context lich su. Khi defense hien tai, dung worktree `E:\Магистр\2-курс\python\RealtyScope-stitch-hybrid-redesign-20260623` tren branch `integration/realtyscope-grade5-final-20260625` va dung evidence Docker 2026-06-26 o tren.

Ghi chú runtime mới ngày 2026-06-25: runtime đang được xác minh trong lát cắt này là FastAPI `127.0.0.1:8011` và Streamlit `127.0.0.1:8509`; chỉ dùng Docker `8000` làm bằng chứng nếu kiểm tra lại riêng. Khi demo, dùng evidence hiện tại: `/model/metadata` trả `selected_price_model_v1_non_leaky` với `selected_candidate=random_forest`, `r2=0.850303822452758`, `rows_total=17,046`. `/stats/exposure-forecast` hiện trả đúng semantic terminal lifecycle: `status=partial`, `can_forecast=false`, `terminal_lifecycle_target_rows=0`; phần observed-history lower-bound vẫn có thật nhưng tách riêng với `observed_exposure_target_rows=7,766`, `observed_exposure_can_forecast=true`, median `7` ngày, max `22` ngày. `/stats/observation-trend` là forecast trend riêng với `can_forecast=true`, `forecast_method=linear_median_price_per_m2_v1`, `history_points=22`, forecast từ `2026-06-25` đến `2026-07-01`. Các dòng cũ bên dưới gọi observed lower-bound exposure là `ready` là lịch sử.

Trang `Сегменты и районы` hiện dùng polygon район thật của Moscow từ `GIS-Lab/OpenStreetMap`, cộng với fallback từ address. Evidence hiện có: `districtComparison=12`, `districtClusters=12`, `cluster_count=3`, `boundary_matched_rows=14,386`, `listings_with_district=14,399`, `district_count=125`, `coverage_pct=84.47`, `cluster_feature_source=districtComparison+boundary`. Đây là district analytics thật theo boundary, không phải chỉ address-text nữa. OSM hạ tầng đã tăng lên `417` featured listings / `2.45%`, gồm `10` live Overpass rows và `407` exact-coordinate-derived rows, nhưng vẫn chưa được nói là OSM-backed hoàn chỉnh.

Update model/exposure cho nhánh giữ lại: code-new API tạm ở `127.0.0.1:8010` chọn `selected_price_model_v1_non_leaky` với `random_forest`, validation `r2=0.8801698812234392`, và `16,512` training rows. Docker API ở `127.0.0.1:8000` vẫn cần WSL/Compose retrain/rebuild ổn định trước khi được nói là đã promote selected model. Exposure hiện có forecast lower-bound thật theo observed history: `observed_exposure_target_rows=7,766`, median `7` ngày, max `22` ngày, target source `observed_history_lower_bound`; vẫn phải nói rõ terminal lifecycle còn `0`, nên đây không phải confirmed sale/removal exposure model.

## Current Docker Runtime Note - 2026-06-26

Ghi chu hien hanh nay supersede cac dong cu ben tren/ben duoi ve `17,046` listings la DB moi nhat, Docker stale, `hist_gradient_boosting`, `candidate_count=2`, hoac OSM partial.

- Docker `127.0.0.1:8000` va Streamlit `127.0.0.1:8501` da duoc static/CDP audit lai sau controlled Domclick refresh.
- `/monitoring/status`: `listings_total=17,287`, `source_counts={'cian': 2436, 'domclick': 14851}`, `observations_total=45,764`, `observation_date_count=23`, `last_observed_date=2026-06-26`, `inferred_lifecycle_target_rows=6,105`.
- OSM coverage sau refresh la `17,046 / 17,287` (`98.61%`), khong con la `100.0%` cua current refreshed table.
- `/model/metadata`: selected artifact van la `random_forest`, `rows_total=17,046`. Day la validated snapshot; khong claim model da train tren `17,287` listings.
- UI Monitoring hien bounded `recent_logs`, compatibility `recent_errors`, va `model.data_freshness.status=validated_snapshot`.
- Docker proof nen chay qua WSL/Docker Compose; khong gia dinh Docker CLI co san trong Windows PowerShell PATH.

## Historical Docker Runtime Note - 2026-06-25

Ghi chu hien hanh nay supersede cac dong cu ben tren/ben duoi ve Docker chua promote selected model, `hist_gradient_boosting`, `candidate_count=2`, hoac OSM partial.

- Docker `127.0.0.1:8000` va Streamlit `127.0.0.1:8501` da duoc kiem tra lai sau retrain/restart.
- `/model/metadata`: `selected_candidate=random_forest`, `candidate_count=3`, `model_selection_mode=best_metric`, `rows_total=17,046`, `train_rows=13,636`, `test_rows=3,410`, `r2=0.8653013476373554`, `mae=7,638,132.733793359`, `rmse=17,470,229.328815047`, va `feature_importance` khong rong.
- `/stats/data-quality`: `osm_features_total=17,046`, `osm_featured_listings=17,046`, `osm_coverage_pct=100.0`, `osm_local_extract_rows=4,487`, `osm_live_rows=16`, `osm_coordinate_derived_rows=12,543`, provenance `local_extract+live_overpass+coordinate_exact_match`.
- `/stats/exposure-forecast`: `status=ready`, `can_forecast=true`, `target_source=observation_gap_inferred_lifecycle`, `inferred_lifecycle_target_rows=4,962`, `terminal_lifecycle_target_rows=0`. Day la du bao bien mat khoi observation, khong phai confirmed sale/removal.
- Caveat can noi khi demo: OSM coverage la persisted full coverage tu local BBBike extract + live Overpass cu + exact-coordinate derivation, khong phai tat ca row deu duoc fetch live tu Overpass.

## 0. Nói Gì Trước Khi Demo

RealtyScope là data-service project hướng grade 5 cho bài toán phân tích và dự đoán giá căn hộ Moscow. Hệ thống hiện chứng minh được:

- thu thập dữ liệu Domclick theo batch có giới hạn và lưu PostgreSQL;
- bằng chứng data-quality và observation history;
- FastAPI endpoints cho data, prediction, model metadata và monitoring;
- Redis cache cho read path `/data` và `/listings`;
- Streamlit dashboard có tabs, filters, paginated listing preview, reviewer charts, coordinate map, baseline prediction, monitoring và model insights;
- Docker Compose runtime với PostgreSQL, Redis, MLflow, FastAPI và Streamlit;
- MLflow evidence cho non-leaky Ridge baseline model.

Caveat quan trọng: model hiện là selected appraisal snapshot trung thực, không phải estimator production cuối cùng. Model đang serve train trên `17,046` rows, còn DB đã refresh lên `17,287` listings; không tự retrain nếu chưa qua promotion gate. Trend hiện là descriptive daily median series qua `2026-06-26`; không nên nói quá thành forecast-vs-actual hoặc model chuỗi thời gian thật.

## 1. Khởi Động Runtime

Chạy từ PowerShell. Dùng WSL2 vì Docker không có trong PowerShell PATH trên máy này.

```powershell
wsl -d Ubuntu -- bash -lc "cd /mnt/e/Магистр/2-курс/python/RealtyScope-stitch-hybrid-redesign-20260623 && docker compose -p realtyscope up --build -d"
```

Kiểm tra trạng thái service:

```powershell
wsl -d Ubuntu -- bash -lc "cd /mnt/e/Магистр/2-курс/python/RealtyScope-stitch-hybrid-redesign-20260623 && docker compose -p realtyscope ps"
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
- `/model/metadata` trả promoted selected model artifact, hiện là `selected_price_model_v1_non_leaky` / `random_forest`, feature version `ml_features_v2_non_leaky`, validation metrics, và freshness caveat rằng model train trên `17,046` rows trong khi DB hiện có `17,287` listings;
- `/monitoring/status` hiển thị data-quality counts, latest ingestion run status, model status, bounded sanitized `recent_logs`, compatibility `recent_errors`, va service rows.

## 3. Chứng Minh Redis Cache

Gọi read path nhỏ có filter để chứng minh cache key theo filter, không chỉ unfiltered path:

```powershell
wsl -d Ubuntu -- bash -lc "curl -sS -o /dev/null -w '%{http_code}' 'http://localhost:8000/data?limit=3&offset=0&rooms=2&min_price_rub=10000000'"
```

Kiểm tra Redis key mà không dump payload đầy đủ:

```powershell
wsl -d Ubuntu -- bash -lc "cd /mnt/e/Магистр/2-курс/python/RealtyScope-stitch-hybrid-redesign-20260623 && docker compose -p realtyscope exec -T redis redis-cli --scan --pattern 'realtyscope:*' | sort | head -20"
wsl -d Ubuntu -- bash -lc "cd /mnt/e/Магистр/2-курс/python/RealtyScope-stitch-hybrid-redesign-20260623 && docker compose -p realtyscope exec -T redis redis-cli EXISTS 'realtyscope:listings:v2:limit=1:offset=0:min_price_rub=10000000:rooms=2'"
wsl -d Ubuntu -- bash -lc "cd /mnt/e/Магистр/2-курс/python/RealtyScope-stitch-hybrid-redesign-20260623 && docker compose -p realtyscope exec -T redis redis-cli TTL 'realtyscope:listings:v2:limit=1:offset=0:min_price_rub=10000000:rooms=2'"
wsl -d Ubuntu -- bash -lc "cd /mnt/e/Магистр/2-курс/python/RealtyScope-stitch-hybrid-redesign-20260623 && docker compose -p realtyscope exec -T redis redis-cli STRLEN 'realtyscope:listings:v2:limit=1:offset=0:min_price_rub=10000000:rooms=2'"
```

Evidence mong đợi:

- HTTP status là `200`;
- `EXISTS` trả `1`;
- `TTL` là số dương ngắn, tối đa `60` giây;
- `STRLEN` lớn hơn `0`.

Nếu `TTL` trả `-2`, key ngắn hạn đã hết hạn. Gọi lại URL `/data` có filter y như trên rồi kiểm tra Redis lần nữa.

## 4. Trình Bày Streamlit Dashboard

Mở:

- Streamlit: http://localhost:8501

Đường đi demo:

1. Trong `Overview`, chỉ KPI cards: listings, ML-ready rows, rejected rows, ingestion runs.
2. Trong `Data Explorer`, dùng sidebar filters:
   - đặt `Rows` là `100` hoặc `500`;
   - đặt `Page` là `1` hoặc `2`;
   - đặt `Min price (RUB)` là `10000000`;
   - đặt `Rooms` là `2`;
   - có thể search một đoạn city/address.
3. Chỉ `Listing preview` thay đổi theo filtered API query và row-window caption.
4. Trong `Visuals`, chỉ reviewer charts:
   - `Price distribution`;
   - `Median price by rooms`;
   - `Listing map`.
5. Chỉ attribution OpenStreetMap nằm dưới map. Map dùng persisted listing coordinates và không gọi live OSM/Overpass.
6. Trong `Prediction`, giữ default values hoặc chỉnh area/rooms/floor, rồi bấm `Run baseline prediction`.
7. Chỉ predicted price, model version, feature version, caveat và metrics summary.
8. Trong `Monitoring & Model`, chỉ monitoring section, gồm timestamp/source/record count của `Last successful collection`.
9. Chỉ `Model insights` với feature importance.

## 5. Trình Bày MLflow Evidence

Mở:

- MLflow: http://localhost:5000

Điểm cần chỉ ra:

- registered model: `realtyscope-price-model`;
- verified model version: `3`;
- run ID: `4999892d2d92402ab78e1209203c338e`;
- model URI: `runs:/4999892d2d92402ab78e1209203c338e/model`;
- artifact path: `data/processed/models/phase5/selected_price_model_v1_non_leaky.joblib`.

REST checks tùy chọn:

```powershell
wsl -d Ubuntu -- bash -lc "python3 -c \"import json, urllib.request; run_id='4999892d2d92402ab78e1209203c338e'; data=json.load(urllib.request.urlopen(f'http://localhost:5000/api/2.0/mlflow/runs/get?run_id={run_id}')); print(data['run']['info']['status'])\""
wsl -d Ubuntu -- bash -lc "python3 -c \"import json, urllib.parse, urllib.request; name=urllib.parse.quote('realtyscope-price-model'); data=json.load(urllib.request.urlopen(f'http://localhost:5000/api/2.0/mlflow/registered-models/get?name={name}')); print([(v['version'], v['run_id']) for v in data['registered_model'].get('latest_versions', [])])\""
```

## 6. Tái Chạy Trainer Nếu Reviewer Hỏi

Chỉ chạy bước này nếu reviewer muốn reproduce MLflow training evidence. Bước này lâu hơn demo API/dashboard.

```powershell
wsl -d Ubuntu -- bash -lc "cd /mnt/e/Магистр/2-курс/python/RealtyScope-stitch-hybrid-redesign-20260623 && docker compose -p realtyscope --profile tools run --build --rm trainer"
```

Sau khi chạy xong, refresh MLflow và `/model/metadata`.

Đường train selected-model tùy chọn cho Stitch branch đang giữ:

```powershell
wsl -d Ubuntu -- bash -lc "cd /mnt/e/Магистр/2-курс/python/RealtyScope-stitch-hybrid-redesign-20260623 && PYTHONPATH=src python -m realtyscope.ml.train --feature-version ml_features_v2_non_leaky --trainer selected --output-dir data/processed/models/phase5 --mlflow-tracking-uri http://localhost:5000 --mlflow-registered-model-name realtyscope-price-model --json"
```

Chỉ dùng bước này nếu sẽ kiểm tra artifact kết quả và rebuild/restart API/Streamlit. Cho đến lúc đó, live `/model/metadata` vẫn là selected-model snapshot đang được promote, không phải model mới train trên DB `17,287` listings.

## 7. Dừng Sạch Không Mất Dữ Liệu

Với demo thường ngày, dừng service nhưng giữ named volumes:

```powershell
wsl -d Ubuntu -- bash -lc "cd /mnt/e/Магистр/2-курс/python/RealtyScope-stitch-hybrid-redesign-20260623 && docker compose -p realtyscope stop"
```

Hoặc xóa containers và Compose network nhưng vẫn giữ named volumes:

```powershell
wsl -d Ubuntu -- bash -lc "cd /mnt/e/Магистр/2-курс/python/RealtyScope-stitch-hybrid-redesign-20260623 && docker compose -p realtyscope down"
```

Không chạy các lệnh phá dữ liệu dưới đây trong lúc chuẩn bị nộp, trừ khi mục tiêu là reset toàn bộ và đã export dữ liệu/artifacts cần giữ:

```powershell
# Phá dữ liệu: xóa PostgreSQL, Redis, MLflow, và model artifact volumes của Compose project này.
wsl -d Ubuntu -- bash -lc "cd /mnt/e/Магистр/2-курс/python/RealtyScope-stitch-hybrid-redesign-20260623 && docker compose -p realtyscope down -v"

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
wsl -d Ubuntu -- bash -lc "cd /mnt/e/Магистр/2-курс/python/RealtyScope-stitch-hybrid-redesign-20260623 && docker compose -p realtyscope ps"
wsl -d Ubuntu -- bash -lc "curl -sS -o /dev/null -w '%{http_code}' http://localhost:8000/health"
wsl -d Ubuntu -- bash -lc "curl -sS -o /dev/null -w '%{http_code}' http://localhost:8501"
```

Sau đó đợi GitHub Actions `ci` trên active branch, và sau merge cuối thì đợi `ci` trên `main`.
# Superseding Note 2026-06-25

Docker `127.0.0.1:8000` and Streamlit `127.0.0.1:8501` are freshly verified from the retained Stitch hybrid branch. `/model/metadata` reports `selected_price_model_v1_non_leaky`, `selected_candidate=random_forest`, `model_selection_mode=best_metric`, `candidate_count=3`, `r2=0.8653013476373554`, `mae=7,638,132.733793359`, `rows_total=17,046`, and non-empty `feature_importance`. `/stats/data-quality` reports `osm_features_total=17,046`, `osm_featured_listings=17,046`, `osm_coverage_pct=100.0`, provenance `local_extract+live_overpass+coordinate_exact_match`. `/stats/exposure-forecast` reports `status=ready`, `can_forecast=true`, `target_source=observation_gap_inferred_lifecycle`, and `inferred_lifecycle_target_rows=4,962`; terminal sale/removal lifecycle remains unavailable with `terminal_lifecycle_target_rows=0`.
