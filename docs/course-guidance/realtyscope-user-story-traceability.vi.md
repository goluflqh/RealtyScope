# Ma trận truy vết User Stories của RealtyScope

Ngày: 2026-06-03
Nguồn: `E:\Магистр\2-курс\python\Описание проекта.html`, phần User Stories.
Đối tượng đọc: người chấm môn học, agent triển khai, và các phiên làm việc sau.

Tài liệu này đối chiếu từng User Story trong đề bài với trạng thái thật của RealtyScope. Mình cố ý đánh dấu thận trọng: chỉ xem là hoàn tất khi trong repo đã có hành vi chạy được, test được, hoặc có quy trình vận hành cụ thể.

## Current Evidence Addendum - 2026-06-26

Ghi chu nay supersede cac dong cu ben duoi neu chung van noi `17,046` listings hoac `2026-06-24` la evidence runtime moi nhat.

- `US-01`: Docker `/monitoring/status` hien bao `17,287` listings, `45,764` observations, `23` observation dates, va `last_observed_date=2026-06-26` sau controlled Domclick refresh tu `data/raw/domclick/2026-06-26-bulk`.
- `US-02`: descriptive trend da co qua `/stats/observation-trend` va UI/static audit thay history den `2026-06-26`; period selector, seasonality, va multi-object comparison van la upgrade analytics tiep theo, khong overclaim.
- `US-03` va `US-08`: selected model dang serve van la validated `random_forest` snapshot train tren `17,046` rows. DB co `17,287` listings khong dong nghia model se tot hon neu retrain ngay; chi retrain qua candidate/promotion workflow.
- `US-06`: monitoring hien co bounded `recent_logs` va compatibility `recent_errors`; Domclick scheduler wrapper ghi pre-batch source failure nhu QRATOR vao `app_logs`.
- `US-07`: final Docker proof nen duoc ghi bang WSL/Docker Compose; khong gia dinh Windows PowerShell co san Docker CLI.

## Chú giải trạng thái

- `Đã có`: đã có hành vi chạy được và evidence trực tiếp trong repo.
- `Một phần`: đã có một phần chức năng, nhưng vẫn thiếu một hoặc nhiều tiêu chí nghiệm thu.
- `Đã lên kế hoạch`: đã nằm trong thiết kế/kế hoạch phase, nhưng chưa có code chạy được.
- `Khoảng trống hiện tại`: chưa có code hoặc task gần hạn để chứng minh.

## Ma trận truy vết

| ID | User Story trong đề bài | Mapping sang RealtyScope | Phase / Trạng thái | Evidence | Khoảng trống / Bước tiếp theo |
| --- | --- | --- | --- | --- | --- |
| US-01 | Người dùng muốn xem dữ liệu hiện tại của đối tượng đã chọn để hiểu tình hình hiện tại. Tiêu chí: tự động cập nhật hằng ngày, hiển thị thời gian cập nhật cuối, KPI cards, chọn được đối tượng phân tích. | Daily Domclick capture, scheduled batch ingestion, API đọc DB qua `/listings`, `/data`, `/stats/data-quality`, Streamlit KPI slice, Data Explorer filters, và metric lần collection thành công gần nhất. | Phase 7 / `Một phần: dữ liệu hiện tại, KPI, filters, và last update đã có` | `src/realtyscope/ingestion/domclick_chrome_capture.py`; `src/realtyscope/ingestion/domclick_scheduled_batch.py`; `services/api/app/main.py`; `services/streamlit/app.py`; `docs/operations/domclick-scheduled-batch-ingestion.md`; tests ở `tests/test_api_data_routes.py`, `tests/test_api_monitoring.py`, và `tests/test_streamlit_scaffold.py`. | Last update đã hiển thị qua `/monitoring/status` và Streamlit. Phần còn lại không phải selector district/object đầy đủ; UI hiện hỗ trợ row limit, page, price, area, rooms, source, và address filters. |
| US-02 | Người dùng muốn xem lịch sử và xu hướng để hiểu động thái thay đổi. Tiêu chí: biểu đồ chuỗi thời gian, chọn period, seasonality/trend, so sánh nhiều đối tượng trên một biểu đồ. | Phase 3.7 thêm Observation / Price History Layer để lưu snapshot normalized theo thời gian: giá, giá/m2, diện tích, số phòng, tầng. | Phase 3.7 / `Một phần: backend đã có` | `ListingObservation` trong `src/realtyscope/database/models.py`; migration `alembic/versions/20260602_0002_listing_observations.py`; persistence behavior trong `src/realtyscope/database/persistence.py`; tests ở `tests/test_database_models.py`, `tests/test_database_persistence.py`, `tests/test_alembic_config.py`; docs ở `docs/data/listing-observations.vi.md`. | Backend history storage đã được cover. Trend API, filter theo period, seasonality analysis, và biểu đồ so sánh trong Streamlit vẫn là việc dashboard sau. |
| US-03 | Người dùng muốn nhận dự đoán từ ML model để ra quyết định. Tiêu chí: hiển thị prediction, metrics model, forecast vs actual, nhập tham số tùy chỉnh. | Phase 4 có baseline regression từ deterministic snapshots; Phase 5 thêm `ml_features_v2_non_leaky` và `baseline_ridge_v2_non_leaky`; Phase 6 có MLflow Docker evidence; Streamlit Prediction tab gọi `/predict`. | Phase 6-7 / `Một phần: baseline không leakage và MLOps evidence đã có` | `src/realtyscope/ml/features.py`; `src/realtyscope/ml/train.py`; `docs/ml/phase4-baseline-model.vi.md`; `docs/ml/phase5-non-leaky-model.vi.md`; `docs/ml/phase6-mlflow-registration.md`; `services/api/app/schemas.py`; `services/api/app/main.py`; `services/streamlit/app.py`; tests ở `tests/test_ml_features.py`, `tests/test_ml_training.py`, `tests/test_api_prediction_contract.py`, `tests/test_streamlit_api_client.py`, và `tests/test_streamlit_scaffold.py`. | Model v2 vẫn là baseline cross-sectional, chưa phải production appraisal serving. Forecast-vs-actual vẫn cần repeated observations và reviewer-facing explanation. |
| US-04 | Người dùng muốn lọc và tìm kiếm dữ liệu để tìm thông tin cần thiết. Tiêu chí: sidebar filters, bảng dữ liệu raw có pagination, sort cột, search text. | Listing table đọc từ DB qua API và Streamlit Data Explorer tab với sidebar filters và page/offset row-window control. | Phase 7 / `Một phần: filters và pagination cơ bản đã có` | `/data` và `/listings` hỗ trợ `min_price_rub`, `max_price_rub`, `min_area_m2`, `max_area_m2`, `rooms`, `source_name`, `search`, và `offset` trong `services/api/app/main.py`; Streamlit controls đi qua `services/streamlit/api_client.py`; tests ở `tests/test_api_data_routes.py`, `tests/test_streamlit_api_client.py`, và `tests/test_streamlit_scaffold.py`. | Filter/search và browsing cơ bản đã đáp ứng scope course. Phần còn lại là column sorting giàu hơn nếu reviewer yêu cầu rõ. |
| US-05 | Developer muốn dùng REST API để tích hợp dữ liệu vào ứng dụng khác. Tiêu chí: Swagger/OpenAPI, `/health`, `/data`, `/predict`, Pydantic validation, HTTP status đúng. | FastAPI service có health, listing data, data-quality stats, Redis-backed filtered `/data`, `/predict`, `/model/metadata`, và `/monitoring/status`, với Pydantic validation ở request/response cần thiết. | Phase 7.2 / `Đã có cho scope API course` | `services/api/app/main.py`; `services/api/app/schemas.py`; `tests/test_api_health.py`; `tests/test_api_data_routes.py`; `tests/test_api_prediction_contract.py`; `tests/test_api_monitoring.py`; README API URLs. FastAPI tự cung cấp Swagger/OpenAPI tại `/docs`. | Runtime smoke mới đã trả 200 cho `/health`, `/docs`, `/data`, `/predict`, `/model/metadata`, và `/monitoring/status`; query mới phải tiếp tục có test. |
| US-06 | Admin muốn monitor trạng thái hệ thống để biết vấn đề. Tiêu chí: trang trạng thái nguồn dữ liệu, logs các lần chạy collector gần nhất, indicator nguồn hoạt động/không hoạt động, thời gian lần collect thành công cuối. | Ingestion run accounting, data-quality stats có timestamps, model status, bounded `recent_logs` va compatibility `recent_errors`, `/monitoring/status`, và Streamlit Monitoring & Model tab hiển thị last successful collection timestamp/source/record count. | Phase 7 / `Một phần: status, last-success, sanitized logs, va Domclick scheduler failure logging da co` | `IngestionRun` và `AppLog` trong `src/realtyscope/database/models.py`; `GET /stats/data-quality`, `GET /monitoring/status`, và `GET /model/metadata` trong `services/api/app/main.py`; `services/streamlit/app.py`; Domclick scheduler `log-error` CLI trong `src/realtyscope/ingestion/domclick_scheduled_batch.py`; tests ở `tests/test_api_monitoring.py`, `tests/test_streamlit_api_client.py`, `tests/test_streamlit_scaffold.py`, `tests/test_streamlit_ui_payload.py`, và `tests/test_domclick_scheduled_batch.py`. | Scheduler/source failures hien co DB-backed `app_logs` path khi PowerShell wrapper fail truoc batch ingestion. Monitoring logs da bounded va UI-safe; phan con lai la optional alerting va log coverage rong hon cho runtime commands khac. |
| US-07 | DevOps muốn deploy project bằng một lệnh để dựng môi trường nhanh. Tiêu chí: `docker compose up --build` chạy mọi thứ, secrets trong `.env`, healthcheck cho từng service, README hướng dẫn chạy. | Docker Compose runtime có DB, Redis, MLflow, API, Streamlit, trainer/model artifact path, `.env.example`, README/local environment docs, demo script, và safe cleanup guidance. | Phase 6-7.1 / `Đã có cho local runtime` | `docker-compose.yml`; `.env.example`; `services/api/Dockerfile`; `services/streamlit/Dockerfile`; `services/mlflow/Dockerfile`; `services/trainer/Dockerfile`; `README.md`; `docs/development/local-environment.md`; `docs/demo-script.md`; `docs/ml/phase6-mlflow-registration.md`. | Runtime smoke sau merge cho thấy `db`, `redis`, `api`, `streamlit` healthy và `mlflow` up. Lặp lại smoke sau thay đổi code/runtime hoặc reset DB. |
| US-08 | Data analyst muốn hiểu logic model để tin tưởng dự đoán. Tiêu chí: feature importance, mô tả features, version model, bonus SHAP charts. | Phase 5 document feature versions, leakage caveats, grouped validation metadata, model version, metrics, API model metadata, và Streamlit model insights cho artifact v2. | Phase 5 / `Một phần: đã có model insights` | `docs/ml/phase5-non-leaky-model.vi.md`; `docs/ml/phase5-non-leaky-model.md`; `src/realtyscope/ml/features.py`; `src/realtyscope/ml/train.py`; `/model/metadata` và `/predict` trong `services/api/app/main.py`; `services/streamlit/app.py`; `tests/test_api_monitoring.py`; `tests/test_streamlit_scaffold.py`. | SHAP và mô tả feature giàu hơn vẫn là optional polish; insight hiện tại là coefficient-based feature importance từ Ridge artifact. |

## Phase 3.7 đóng góp gì?

Phase 3.7 trực tiếp đẩy `US-02` và gián tiếp hỗ trợ `US-03`, `US-04`, `US-08`:

- `US-02`: observations giúp vẽ chuỗi thời gian giá và giá/m2.
- `US-03`: lịch sử quan sát giúp validation theo thời gian và so sánh predicted vs actual sau này.
- `US-04`: observations tạo nền để lọc theo nguồn/thời gian trong Data Explorer.
- `US-08`: model explanations sau này có thể dựa trên feature snapshots ổn định, không chỉ dòng latest luôn bị overwrite.

Ranh giới quan trọng: `listings` vẫn là bảng canonical/latest của mỗi căn hộ, còn `listing_observations` lưu trạng thái normalized được quan sát qua thời gian.

## Phase 4 đóng góp gì?

Phase 4 đẩy `US-02`, `US-03`, `US-05`, và `US-08` bằng evidence đã test trong repo:

- Runtime readiness mới ngày 2026-06-03 cho thấy `3019` persisted listings, `3989` observations, `970` listings có nhiều observation, `26` price changes, coordinate coverage đầy đủ, và ML-ready coverage đầy đủ. Ngôn ngữ về trend vẫn giữ conservative cho tới khi freshness và repeated-capture semantics được review trong defense.
- OpenStreetMap enrichment đã có local/fixture-tested feature contract, persistence bảng `osm_features`, và Phase 5 bounded live Overpass write path. Local PostgreSQL database hiện có 4 live OSM rows (`osm_rows_present=4` trên năm ML feature rows đầu), và mọi UI/docs dùng dữ liệu OSM-derived phải giữ attribution rõ cho OpenStreetMap.
- ML feature snapshots deterministic (`ml_features_v1`) gồm listing facts, latest observation facts, optional OSM features, và missingness flags.
- Baseline training ghi `data/processed/models/phase4/baseline_ridge_v1.joblib`, so sánh Ridge với naive median baseline, và document live metrics. Metrics gần như hoàn hảo đã được caveat vì feature rows hiện có các trường giá mới nhất.
- `/predict` và Streamlit hiện có minimal baseline prediction contract với model version, feature version, metrics summary, input echo, và caveat. Đây là Phase 4 contract scaffold, chưa phải production appraisal serving cuối cùng.

## Phase 5 ML đóng góp gì?

Slice ML Phase 5 đẩy `US-03` và `US-08` nhưng không gọi model là final:

- `ml_features_v2_non_leaky` loại leakage từ latest-price features nhưng vẫn giữ feature builder deterministic và OSM missingness behavior.
- Training mặc định model version v2 là `baseline_ridge_v2_non_leaky` và ghi grouped validation metadata theo `listing_id`.
- Evidence `/model/metadata` hiện tại trên PostgreSQL local báo `rows_total=3019`, MAE `22,685,629.92` so với naive MAE `28,452,175.74`, `r2=0.5317`, với 23 feature không leakage.
- MLflow evidence thật đã được Phase 6 cover bằng Docker: run `4999892d2d92402ab78e1209203c338e`, registered model `realtyscope-price-model` version `3`, trạng thái `READY`.

## Phase 6 MLOps và runtime đóng góp gì?

Phase 6 đẩy `US-03`, `US-05`, `US-07`, và `US-08` bằng evidence production-like:

- Docker Compose build từ scoped in-repo contexts và start `db`, `redis`, `mlflow`, `api`, `streamlit` từ repo mount trên Windows.
- Redis backing cho read path `/listings` và `/data`.
- Trainer service ghi MLflow run `4999892d2d92402ab78e1209203c338e` và register `realtyscope-price-model` version `3`.
- GitHub Actions xanh tại milestone Phase 6 `30bce998f1c3e5a6d13085d08a0b3692a52234a2` và xanh trên `main` sau khi merge Phase 7 tại `05f9b0cac3e77d55b93820be5d2b3db442d5295c`.

## Phase 7 đóng góp gì?

Phase 7.0-7.4 đẩy `US-01`, `US-04`, `US-05`, `US-07`, và `US-08` theo hướng reviewer-facing:

- `docs/project-status.md` là status board sống cho branch, CI, runtime data, requirements, và remaining work.
- Phase 7.1 document runtime/data evidence mới cùng safe Docker/storage cleanup guidance.
- Phase 7.2 thêm API và Streamlit filters cho price, area, rooms, source, và address search.
- Phase 7.3 thêm reviewer visuals: price distribution, median price by rooms, coordinate map với OpenStreetMap attribution rõ.
- Các slice monitoring/demo/UI mới thêm last-successful-collection visibility, concise reviewer runbook, Streamlit tabs, và Data Explorer page control.
- Phase 7 final evidence refresh xác nhận Docker services, API `/predict`, filtered `/data`, Redis cache keying, MLflow registered model version `3`, và Streamlit Browser DOM smoke trên runtime hiện tại.
