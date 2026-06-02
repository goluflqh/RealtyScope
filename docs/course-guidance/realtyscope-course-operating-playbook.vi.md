# Playbook vận hành theo bài giảng cho RealtyScope

Ngày: 2026-06-02
Phạm vi: nguyên tắc dùng cho mọi phase tiếp theo của RealtyScope.
Nguồn: đọc lại kỹ các notebook và HTML trong `E:\Магистр\2-курс\python\MISIS_2025\season_2`, cộng với các tài liệu `docs/course-guidance` hiện có.

Tài liệu này là lớp hành động thực tế phía trên bản course review. Dùng nó khi lập plan, triển khai, review và quyết định một phase đã đủ sạch hay chưa. Không chỉ dùng cho Phase 5.

## Cách hiểu cốt lõi

Bài giảng yêu cầu một sản phẩm kiểu DataPulse, không phải vài script hoặc notebook rời rạc. Mỗi phase nên đưa RealtyScope tiến gần hơn tới chuỗi này:

```text
Nguồn dữ liệu ngoài
  -> ingestor có giới hạn, có lịch, có report
  -> PostgreSQL + audit trail + cache/artifacts
  -> EDA và feature engineering có evidence
  -> ML experiments có validation + MLflow
  -> FastAPI data/prediction/monitoring contracts
  -> Streamlit dashboard pages
  -> Docker Compose, CI, tests, docs
```

Một phần chỉ nên được xem là “có” khi có hành vi thật, đã verify, và được đặt đúng layer. Khai báo Redis/MLflow/API route/monitoring/dashboard mà chưa có behavior thật thì vẫn là incomplete.

## Quy tắc phase

1. Giữ branch phase cũ như milestone.
   - Không rename hoặc xóa branch phase đã hoàn tất khi bắt đầu phase mới.
   - Tạo branch phase mới từ branch phase trước.
   - Nếu cả hai phase còn cần tham chiếu, giữ GitNexus index riêng cho từng phase.

2. Mỗi phase phải đẩy chuỗi sản phẩm tiến lên.
   - Tránh thêm code không làm data, ML, API, UI hoặc operations tốt hơn.
   - Ưu tiên slice end-to-end nhỏ hơn là nhiều phần rời rạc.

3. Evidence phải đi cùng implementation.
   - Đổi code: có test.
   - Đổi dữ liệu: có counts, quality checks, kết luận mẫu.
   - Đổi ML: có naive baseline, validation split, metrics, artifact path, caveat.
   - Đổi ops: có lịch, log, report, cách kiểm tra lần chạy kế tiếp.

## Quy tắc ingestion dữ liệu

Bài giảng nhấn mạnh thu thập dữ liệu phải reproducible, có đạo đức, có giới hạn.

- Ưu tiên API chính thức nếu có; scraping/browser automation chỉ dùng khi có lý do rõ.
- Tôn trọng `robots.txt` và boundary chống abuse.
- Unit tests dùng snapshot/fixture, không gọi live website.
- Có timeout, rate limit, user-agent/operator metadata, report fail rõ.
- Raw data là generated artifact, không phải source code.
- Scheduled run phải tạo evidence observation mới, không chỉ chạy lại file cũ.

Hệ quả cho RealtyScope: task Domclick nên chạy lúc 00:00 Moscow time và cần được sửa để daily run tạo fresh snapshot directory hoặc chủ động ghi observation timestamp mới. Reuse cùng folder `YYYY-MM-DD-bulk` mà không insert observation thì không xây được trend data.

## Quy tắc database

PostgreSQL và Alembic là lõi của project, không phải phụ kiện.

- PostgreSQL là source of truth; JSON/HTML local chỉ là raw artifacts.
- Dữ liệu ngoài phải qua Pydantic validation trước khi ghi DB.
- Giữ style SQLAlchemy 2.0 typed models và relationships rõ ràng.
- Alembic là schema path chính; `create_all()` chỉ dùng cho tests/fixtures.
- Ingestion cần giữ raw payloads, canonical latest rows, source links, rejected rows, ingestion runs.
- Duplicate handling phải có chủ ý và được document.

Hệ quả cho RealtyScope: observation history cần semantics tốt hơn uniqueness theo `raw_listing_id` nếu muốn trend modeling. Một listing không đổi giá vẫn có thể là observation hợp lệ tại thời điểm capture mới.

## Quy tắc EDA

EDA là evidence chấm điểm, không phải trang trí.

Mỗi phase EDA nên có:

- row counts và schema/types;
- missing values và cách xử lý rõ ràng;
- duplicates và logic deduplication;
- outliers và quyết định clip/flag/keep;
- target distribution và diễn giải nghiệp vụ;
- quan hệ/correlation giữa features;
- kết luận data quality dẫn tới bước engineering hoặc ML tiếp theo.

Hệ quả cho RealtyScope: EDA cross-sectional hiện đã hợp lý, nhưng kết luận trend/price-change phải đợi tới khi có nhiều observation cho cùng listing.

## Quy tắc ML

Bài giảng ưu tiên validation đúng trước khi model phức tạp.

- Bắt đầu từ naive baseline và classic ML baseline.
- Chỉ claim model tốt hơn khi validation không leakage.
- Không tin metric nếu feature có target-like fields.
- Artifact không commit vào git; MLflow dùng để track nếu claim MLOps.
- Grade 5 cần feature importance hoặc SHAP và hiển thị model metadata trong UI.
- Không nhảy sang deep learning nếu dữ liệu và bài toán chưa cần.

Hệ quả cho RealtyScope: `baseline_ridge_v1` chứng minh pipeline, nhưng metric hiện bị inflated vì `ml_features_v1` chứa price fields rất gần target. Phase ML tiếp theo phải tạo feature version không leakage trước khi claim chất lượng dự báo.

## Quy tắc API

API là ranh giới sản phẩm.

- FastAPI routes dùng Pydantic request/response schemas.
- Resource nặng như DB engine, Redis client, model nên load một lần qua lifespan/app state, không load mỗi request.
- Test cả success case và validation/error case.
- Swagger/OpenAPI phải đủ rõ để reviewer thử mà không cần đọc source.

Hệ quả cho RealtyScope: `/predict` đã có ở mức Phase 4 contract, nhưng phase sau nên harden bằng lifespan/app state và thêm model health/metadata endpoints.

## Quy tắc Streamlit

Streamlit không phải ảnh minh họa; nó là sản phẩm reviewer nhìn thấy.

Các page tối thiểu nên hướng tới:

- Overview/analytics: KPI và data quality.
- Data explorer: filters/search/table.
- Prediction: input, result, model version, caveat.
- Monitoring/logs: ingestion/source status.
- Model insights: metrics, feature importance/SHAP cho grade 5.

Dùng `st.cache_data` cho API/data results và `st.cache_resource` cho reusable clients/resources khi phù hợp.

## Quy tắc Docker, CI, MLOps

- `docker-compose.yml` ở repo root và phải trở thành launch path tái lập chính.
- Container nói chuyện bằng service name như `db`, `redis`, `api`, `mlflow`, không dùng `localhost` nội bộ.
- Không commit `.env`, raw dumps, DB dumps, model artifacts.
- CI chạy lint và tests.
- Redis nếu giữ để đạt grade 5 thì phải có cache/read-path thật.
- MLflow nếu claim thì phải track experiment, params, metrics, artifacts thật.

## Checklist review cho mọi phase sau

Trước khi gọi phase sau là complete, phải trả lời được:

1. User story hoặc grading requirement nào tiến lên?
2. Dữ liệu nào đi vào hoặc thay đổi?
3. Persistent DB state nào thay đổi?
4. Test nào chứng minh behavior?
5. EDA/ML evidence nào được tạo?
6. API/UI behavior nào reviewer có thể thử?
7. Command/log vận hành nào chứng minh nó chạy?
8. Caveat còn lại là gì, phase nào xử lý?

Nếu thiếu câu trả lời, phần đó có thể vẫn hữu ích, nhưng chưa nên xem là phase sạch.
