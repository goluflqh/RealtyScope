# Ma trận truy vết User Stories của RealtyScope

Ngày: 2026-06-02
Nguồn: `E:\Магистр\2-курс\python\Описание проекта.html`, phần User Stories.
Đối tượng đọc: người chấm môn học, agent triển khai, và các phiên làm việc sau.

Tài liệu này đối chiếu từng User Story trong đề bài với trạng thái thật của RealtyScope. Mình cố ý đánh dấu thận trọng: chỉ xem là hoàn tất khi trong repo đã có hành vi chạy được, test được, hoặc có quy trình vận hành cụ thể.

## Chú giải trạng thái

- `Đã có`: đã có hành vi chạy được và evidence trực tiếp trong repo.
- `Một phần`: đã có một phần chức năng, nhưng vẫn thiếu một hoặc nhiều tiêu chí nghiệm thu.
- `Đã lên kế hoạch`: đã nằm trong thiết kế/kế hoạch phase, nhưng chưa có code chạy được.
- `Khoảng trống hiện tại`: chưa có code hoặc task gần hạn để chứng minh.

## Ma trận truy vết

| ID | User Story trong đề bài | Mapping sang RealtyScope | Phase / Trạng thái | Evidence | Khoảng trống / Bước tiếp theo |
| --- | --- | --- | --- | --- | --- |
| US-01 | Người dùng muốn xem dữ liệu hiện tại của đối tượng đã chọn để hiểu tình hình hiện tại. Tiêu chí: tự động cập nhật hằng ngày, hiển thị thời gian cập nhật cuối, KPI cards, chọn được đối tượng phân tích. | Daily Domclick capture, scheduled batch ingestion, API đọc DB qua `/listings` và `/stats/data-quality`, Streamlit KPI slice. | Phase 3.5-3.6 / `Một phần` | `src/realtyscope/ingestion/domclick_chrome_capture.py`; `src/realtyscope/ingestion/domclick_scheduled_batch.py`; `services/api/app/main.py`; `services/streamlit/app.py`; `docs/operations/domclick-scheduled-batch-ingestion.md`. | API/Streamlit đã có count và latest ingestion run, nhưng payload/UI chưa hiển thị rõ `started_at`/`finished_at` như thời gian cập nhật cuối. Streamlit hiện chỉ chọn số dòng, chưa chọn đối tượng phân tích theo district/source/category. |
| US-02 | Người dùng muốn xem lịch sử và xu hướng để hiểu động thái thay đổi. Tiêu chí: biểu đồ chuỗi thời gian, chọn period, seasonality/trend, so sánh nhiều đối tượng trên một biểu đồ. | Phase 3.7 thêm Observation / Price History Layer để lưu snapshot normalized theo thời gian: giá, giá/m2, diện tích, số phòng, tầng. | Phase 3.7 / `Một phần: backend đã có` | `ListingObservation` trong `src/realtyscope/database/models.py`; migration `alembic/versions/20260602_0002_listing_observations.py`; persistence behavior trong `src/realtyscope/database/persistence.py`; tests ở `tests/test_database_models.py`, `tests/test_database_persistence.py`, `tests/test_alembic_config.py`; docs ở `docs/data/listing-observations.vi.md`. | Backend history storage đã được cover. Trend API, filter theo period, seasonality analysis, và biểu đồ so sánh trong Streamlit vẫn là việc dashboard sau. |
| US-03 | Người dùng muốn nhận dự đoán từ ML model để ra quyết định. Tiêu chí: hiển thị prediction, metrics model, forecast vs actual, nhập tham số tùy chỉnh. | Bài toán regression giá bán căn hộ Moscow, MLflow tracking, `/predict` tương lai, Streamlit Predictions page. | Phase 4+ / `Đã lên kế hoạch` | `docs/superpowers/specs/2026-05-31-realtyscope-design.md` phần ML/API/Streamlit; `pyproject.toml` optional dependencies `ml`; `services/mlflow/Dockerfile`. | Chưa có model đã train, model registry, prediction API, hay UI dự đoán. Cần train baseline, lưu artifact, expose `/predict`, và hiển thị metrics. |
| US-04 | Người dùng muốn lọc và tìm kiếm dữ liệu để tìm thông tin cần thiết. Tiêu chí: sidebar filters, bảng dữ liệu raw có pagination, sort cột, search text. | Listing table đọc từ DB qua API và Streamlit listing preview. | Phase 3.5 / `Một phần` | `GET /listings` có `limit` và `offset` trong `services/api/app/main.py`; Streamlit hiển thị dataframe trong `services/streamlit/app.py`; tests ở `tests/test_api_data_routes.py` và `tests/test_streamlit_api_client.py`. | Chưa có API filters cho price/area/rooms/source/text; Streamlit mới có chọn số dòng. Cần thêm query parameters và UI controls trong phase Data Explorer. |
| US-05 | Developer muốn dùng REST API để tích hợp dữ liệu vào ứng dụng khác. Tiêu chí: Swagger/OpenAPI, `/health`, `/data`, `/predict`, Pydantic validation, HTTP status đúng. | FastAPI service có health, listing data, và data-quality stats. | Phase 3.5 / `Một phần` | `services/api/app/main.py`; `tests/test_api_health.py`; `tests/test_api_data_routes.py`; README API URLs. FastAPI tự cung cấp Swagger/OpenAPI tại `/docs`. | Route hiện tại là `/health`, `/listings`, `/stats/data-quality`; chưa có route đúng tên `/data` và chưa có `/predict`. Prediction schemas và validation thuộc phase ML/API sau. |
| US-06 | Admin muốn monitor trạng thái hệ thống để biết vấn đề. Tiêu chí: trang trạng thái nguồn dữ liệu, logs các lần chạy collector gần nhất, indicator nguồn hoạt động/không hoạt động, thời gian lần collect thành công cuối. | Ingestion run accounting, data-quality stats, Domclick status command, nền tảng bảng app logs. | Phase 3.5-3.6 / `Một phần` | `IngestionRun` và `AppLog` trong `src/realtyscope/database/models.py`; `GET /stats/data-quality` trong `services/api/app/main.py`; command `domclick_scheduled_batch status` trong `src/realtyscope/ingestion/domclick_scheduled_batch.py`; operations docs. | Chưa có Streamlit monitoring page riêng, latest run payload chưa trả timestamp, và app logs chưa được populate/display qua API/UI. |
| US-07 | DevOps muốn deploy project bằng một lệnh để dựng môi trường nhanh. Tiêu chí: `docker compose up --build` chạy mọi thứ, secrets trong `.env`, healthcheck cho từng service, README hướng dẫn chạy. | Docker Compose skeleton gồm DB, Redis, MLflow, API, Streamlit; `.env.example`; README và local environment docs. | Phase 1-3.6 / `Một phần` | `docker-compose.yml`; `.env.example`; `services/api/Dockerfile`; `services/streamlit/Dockerfile`; `services/mlflow/Dockerfile`; `README.md`; `docs/development/local-environment.md`. | Compose đã có, nhưng final readiness, healthcheck cho từng service, ML serving, và verification một lệnh kiểu production-like vẫn là việc integration sau. |
| US-08 | Data analyst muốn hiểu logic model để tin tưởng dự đoán. Tiêu chí: feature importance, mô tả features, version model, bonus SHAP charts. | Future Model Insights page và model metadata từ MLflow. | Phase 5+ / `Đã lên kế hoạch` | `docs/superpowers/specs/2026-05-31-realtyscope-design.md` yêu cầu feature importance/SHAP cho grade 5; `pyproject.toml` có optional dependencies `mlflow` và scikit-learn. | Chưa có model nên chưa thể có interpretability. Chỉ thêm feature importance/model version sau khi đã train và chọn model. |

## Phase 3.7 đóng góp gì?

Phase 3.7 trực tiếp đẩy `US-02` và gián tiếp hỗ trợ `US-03`, `US-04`, `US-08`:

- `US-02`: observations giúp vẽ chuỗi thời gian giá và giá/m2.
- `US-03`: lịch sử quan sát giúp validation theo thời gian và so sánh predicted vs actual sau này.
- `US-04`: observations tạo nền để lọc theo nguồn/thời gian trong Data Explorer.
- `US-08`: model explanations sau này có thể dựa trên feature snapshots ổn định, không chỉ dòng latest luôn bị overwrite.

Ranh giới quan trọng: `listings` vẫn là bảng canonical/latest của mỗi căn hộ, còn `listing_observations` lưu trạng thái normalized được quan sát qua thời gian.
