# RealtyScope Phase 0 Design Spec

Ngày: 2026-05-31
Trạng thái: Bản đặc tả thiết kế Phase 0 đã được duyệt để ghi file, đang chờ review cuối cùng trước implementation planning.
Phạm vi: Chỉ là requirements register và design specification. Phase này không bao gồm code, scaffold project, git init, hay implementation files.

## 1. Mục tiêu

RealtyScope là dự án data-service cấp độ grade 5 theo phong cách DataPulse của môn học. Dự án sẽ thu thập dữ liệu listing căn hộ, enrich bằng dữ liệu hạ tầng địa lý, huấn luyện mô hình machine learning để ước lượng giá bán căn hộ, rồi expose kết quả qua FastAPI và Streamlit dashboard.

Mục tiêu của Phase 0 là khóa thiết kế trước khi implementation. Tài liệu này định nghĩa yêu cầu cần đạt, kiến trúc, chiến lược nguồn dữ liệu, contract nhập dữ liệu từ teammate, kỳ vọng database/Alembic, phạm vi ML/API/UI/Redis/testing/CI, tiêu chí verify, rủi ro và plan phase tiếp theo.

Không bắt đầu implementation cho tới khi file spec này được review và được user approve rõ ràng là sẵn sàng chuyển sang implementation planning.

## 2. Giả định cốt lõi

- Thị trường chính: listing bán căn hộ, không phải thuê nhà.
- Khu vực: Moscow.
- Target ML chính: `price_rub`, giá bán bằng RUB.
- Source listing chính: Domclick.
- Source enrichment chính: OpenStreetMap.
- Source của teammate: chưa biết ở Phase 0, nên hệ thống thiết kế theo contract nhập dữ liệu chung, không phụ thuộc source cụ thể.
- MVP model dùng feature có cấu trúc từ listing và vị trí. Text/raw description có thể lưu để audit hoặc thử nghiệm sau, nhưng NLP không nằm trong phạm vi model đầu tiên.

## 3. Requirements Register

### 3.1 Yêu cầu grade 4

| ID | Yêu cầu | Cam kết thiết kế của RealtyScope |
|---|---|---|
| R4-1 | Reproducibility | Project cuối cùng phải chạy local bằng `docker compose up --build`. Phase 0 chỉ định nghĩa service topology, chưa tạo compose file. |
| R4-2 | Data sources | Có ít nhất 2 nguồn: Domclick listings và OpenStreetMap enrichment. Teammate source có thể là nguồn thứ ba qua import contract. |
| R4-3 | Data volume | Mục tiêu ít nhất 1000 listing sạch, đã persist, sau validation, deduplication và cleaning. |
| R4-4 | Missing values | Lưu row thiếu dữ liệu một cách minh bạch, định nghĩa field bắt buộc cho ML-ready rows, và dùng flag imputation khi cần. |
| R4-5 | EDA | Có Jupyter notebook với visualization và kết luận: phân phối giá/diện tích, missingness, outliers, geo coverage, quan hệ feature-target. |
| R4-6 | ML baseline | Train baseline model với validation đúng và metrics tốt hơn naive baseline. |
| R4-7 | API | FastAPI phải có `/predict`; Swagger/OpenAPI phải hoạt động. |
| R4-8 | UI | Streamlit có ít nhất 3 pages. Thiết kế đề xuất 4-5 pages để grade 5 rõ hơn. |
| R4-9 | Documentation | README giải thích cách chạy local, data pipeline, model, API, Streamlit, và attribution cho OpenStreetMap. |

### 3.2 Yêu cầu grade 5

| ID | Yêu cầu | Cam kết thiết kế của RealtyScope |
|---|---|---|
| R5-1 | ML Ops | Dùng MLflow để track experiments, parameters, metrics, artifacts và selected model version. |
| R5-2 | Interpretation | Streamlit hiển thị feature importance. Dùng SHAP nếu model được chọn hỗ trợ ổn định. |
| R5-3 | Monitoring | Streamlit có source status, ingestion runs, record counts, rejected rows, recent errors/logs. |
| R5-4 | Tests | Dùng `pytest`; mục tiêu coverage ít nhất 50%. |
| R5-5 | CI/CD | GitHub Actions chạy lint và tests. |
| R5-6 | Migrations | Dùng Alembic để quản lý PostgreSQL schema migrations. |
| R5-7 | Cache | Dùng Redis cho read path thật của API/dashboard, không chỉ khai báo service rỗng trong Docker. |
| R5-8 | Code quality | Dùng ruff, ruff format, pre-commit và typing expectations. |
| R5-9 | Team scope | Teammate data import phải tách biệt, dễ giải thích, và validate qua shared contract. |

## 4. Cách tiếp cận được chọn

Cách tiếp cận được chọn là thiết kế grade-5 cân bằng cho một thành phố: dự đoán giá bán căn hộ ở Moscow.

Lý do chọn cách này:

- Đủ mạnh cho grade 5 nhưng vẫn kiểm soát được scope.
- Moscow có khả năng có đủ listing để đạt mục tiêu 1000+ records.
- Domclick cung cấp listing data chính.
- OpenStreetMap bổ sung context vị trí/hạ tầng, làm feature ML có ý nghĩa hơn.
- Teammate data có thể merge sau qua contract mà không phá core schema.

Các cách tiếp cận không chọn:

- Conservative minimum: chỉ Domclick + OSM, teammate source optional. Ít rủi ro hơn, nhưng hơi yếu cho team project.
- Ambitious multi-market: vừa sale vừa rent, hoặc nhiều thành phố. Nghe ấn tượng hơn nhưng tăng mạnh độ phức tạp ở scraping, schema, ML, UI và coordination.

## 5. Kiến trúc hệ thống

RealtyScope đi theo kiểu service split giống kiến trúc DataPulse của môn học.

| Component | Trách nhiệm |
|---|---|
| `ingestor` | Thu thập Domclick listings, import teammate data, enrich coordinates bằng OSM features, ghi raw và normalized records vào PostgreSQL. |
| `db` | PostgreSQL là source of truth cho sources, ingestion runs, raw payloads, normalized listings, features, models, predictions và logs. |
| `trainer` | Offline ML training pipeline: load cleaned data, tạo feature snapshots, train/evaluate models, log MLflow runs, save artifacts. |
| `mlflow` | Track experiment parameters, metrics, artifacts và selected model version. |
| `api` | FastAPI service expose health, data, prediction và monitoring endpoints. Dùng Redis ở những read path có thể cache. |
| `streamlit` | Dashboard cho overview, prediction, data exploration, monitoring/logs và model insights. |
| `redis` | Cache repeated dashboard/API reads và recent prediction results khi hữu ích. |
| `notebooks` | EDA và modeling evidence cho course; notebooks không phải production serving path. |

Luồng dữ liệu dự kiến:

```text
Domclick + teammate source -> raw_listings -> listings
OpenStreetMap -> osm_features -> ml_feature_snapshots
ml_feature_snapshots -> trainer -> MLflow model artifact
FastAPI -> Streamlit
ingestion/API logs -> Monitoring page
```

Ranh giới quan trọng: raw source payloads được giữ riêng khỏi canonical listing records. Việc này giúp cô lập rủi ro parser, dễ audit dữ liệu gốc, và làm teammate import dễ validate hơn mà không phá schema chính.

## 6. Chiến lược nguồn dữ liệu

### 6.1 Domclick listing strategy

Domclick là source chính cho listing bán căn hộ ở Moscow.

Hành vi mong muốn:

- Chỉ thu thập public listing/search data cần thiết cho semester project.
- Dùng custom User-Agent rõ ràng khi phù hợp.
- Có delay giữa các request và giới hạn số record/request trong mỗi run.
- Lưu `source_url`, `observed_at`, `source_listing_id` nếu có, và `raw_payload`.
- Collector phải replaceable: nếu Domclick block request hoặc đổi markup, chỉ collector thay đổi, normalized contract vẫn giữ nguyên.

Fallback strategy:

- Giảm crawl scope và request frequency.
- Dùng raw snapshots đã lưu để development và tests.
- Tạm dùng teammate/Kaggle-style imported data làm listing source, nhưng vẫn giữ cùng normalized schema.

### 6.2 OpenStreetMap enrichment strategy

OpenStreetMap là source enrichment, không phải source listing chính.

Cách ưu tiên:

- Dùng coordinates từ listing nếu Domclick hoặc teammate source cung cấp.
- Query hoặc derive nearby infrastructure features quanh coordinates.
- Lưu OSM-derived features vào normalized columns để ML/API không phụ thuộc raw OSM responses.

Candidate OSM features:

- Distance tới metro/public transport gần nhất.
- Count của public transport, schools, parks, shops, healthcare và POIs khác trong các bán kính cố định.
- District hoặc boundary metadata nếu làm được hợp lý.
- Green area hoặc park proximity.
- Road/transport density nếu dễ compute.

Quy tắc geocoding:

- Tránh bulk geocoding qua public Nominatim.
- Nếu cần geocoding, phải cache kết quả, rate-limit requests, và không chạy lặp trong test loops.
- Với enrichment lớn, ưu tiên coordinates có sẵn từ listing hoặc offline/local extract.

Attribution:

- README và UI phải hiển thị attribution cho OpenStreetMap nếu show map hoặc dữ liệu derived từ OSM.

References cho implementation planning:

- Nominatim Usage Policy: https://operations.osmfoundation.org/policies/nominatim/
- Overpass API examples: https://wiki.openstreetmap.org/wiki/Overpass_API/Overpass_API_by_Example

## 7. Teammate import contract

Teammate data sẽ đi qua contract chung, không phụ thuộc source cụ thể. Cách này giúp teammate có thể dùng source khác mà core architecture vẫn ổn.

| Field | Bắt buộc | Ghi chú |
|---|---:|---|
| `source_name` | yes | Ví dụ: `domclick`, `teammate_cian`, `teammate_file`. |
| `source_listing_id` | yes | Stable ID từ source nếu có; nếu không thì generated deterministic hash. |
| `source_url` | recommended | Dùng cho audit và deduplication. |
| `observed_at` | yes | Timestamp khi listing được fetch/observe. |
| `city` | yes | Default expected value: `Moscow`. |
| `address_text` | recommended | Hữu ích cho audit và fuzzy matching. |
| `latitude` | strongly recommended | Cần cho OSM enrichment. |
| `longitude` | strongly recommended | Cần cho OSM enrichment. |
| `price_rub` | yes | Main ML target. |
| `total_area_m2` | yes | Core model feature. |
| `rooms` | yes | Core model feature; studio/unknown phải biểu diễn rõ. |
| `floor` | recommended | Feature hữu ích; nullable với cleaning rules. |
| `floors_total` | recommended | Feature hữu ích; nullable với cleaning rules. |
| `building_year` | optional | Feature giá trị cao nếu có. |
| `property_type` | yes | Apartment/new-build/resale/etc. |
| `description` | optional | Lưu để audit hoặc thử NLP sau này. |
| `raw_payload` | yes | JSON/string snapshot để audit và reprocessing. |

Validation rules:

- Rows thiếu required fields sẽ bị reject vào import error report.
- Rejected rows không được âm thầm vào ML dataset.
- Coordinates rất nên có. Row không có coordinates vẫn có thể lưu DB, nhưng enrichment confidence thấp hơn.

Deduplication rules:

- Trước hết dedup theo `(source_name, source_listing_id)`.
- Sau đó detect cross-source duplicates bằng fuzzy matching trên coordinates, price, area, rooms và address similarity.
- Duplicate handling phải ngăn cùng một căn hộ rơi vào cả train và test splits.

## 8. Database schema và Alembic expectations

Database cần đủ normalized để trace/audit, nhưng không nên overbuild thành data warehouse phức tạp.

Proposed tables:

| Table | Mục đích |
|---|---|
| `sources` | Metadata các data sources: Domclick, OSM, teammate sources, source type, enabled flag. |
| `ingestion_runs` | Mỗi collector/import run một row: source, start/end time, status, records seen/inserted/updated/rejected, error summary. |
| `raw_listings` | Raw listing snapshots bất biến: source ID, source listing ID, URL, observed time, raw payload, payload hash. |
| `listings` | Canonical deduplicated apartment listing facts: city, address, coordinates, price, area, rooms, floor, property type, confidence, active flag. |
| `listing_source_links` | Map canonical listing IDs tới một hoặc nhiều raw/source records để dedup và audit. |
| `osm_features` | Enrichment theo listing/coordinate: POI counts/distances, transport distance, green area proximity, district metadata. |
| `ml_feature_snapshots` | Versioned feature rows dùng cho training/prediction để reproduce model results. |
| `model_registry` | Local selected model metadata: MLflow run ID, artifact URI, metrics, created time, active flag. |
| `predictions` | API prediction requests/responses, model version, input hash, predicted price, optional confidence/error bands. |
| `app_logs` | Structured application/ingestion errors và monitoring events hiển thị trong Streamlit. |

Alembic expectations:

- Mọi schema change sau initial scaffold phải đi qua Alembic migration files.
- Initial migration tạo core tables, indexes, unique constraints và foreign keys.
- Unique constraints cần ngăn duplicate raw rows theo `(source_id, source_listing_id, observed_at)` hoặc payload hash.
- Canonical duplicate handling phải explicit qua `listing_source_links`.
- Indexes cần hỗ trợ common queries: city, coordinates, price, observed time, active status, source và ingestion status.
- JSON/raw payload fields được phép lưu để audit, nhưng ML/API phải dùng normalized columns.
- Khi implementation đến DB phase, verification cần chứng minh fresh database migrate được từ empty state và hỗ trợ initial API/training queries.

Cleaning và missing-value rules:

- ML-ready row cần có `price_rub`, `total_area_m2`, `rooms` hoặc explicit studio/unknown handling, `property_type`, và coordinates hoặc documented geocoding/enrichment fallback.
- Incomplete rows vẫn lưu DB để minh bạch.
- Incomplete rows không vào `ml_feature_snapshots` cho tới khi được clean.
- Nên lưu flags quan trọng như `has_coordinates`, `is_studio`, `is_new_build`, `was_imputed_area`, `was_imputed_floor`.

## 9. Machine Learning scope

Task chính: dự đoán giá bán căn hộ ở Moscow bằng RUB.

| Item | Thiết kế |
|---|---|
| Target | `price_rub`. |
| Naive baseline | Median price hoặc median price per square meter, có thể group theo rooms/district. |
| Baseline model | Ridge/Linear Regression hoặc simple tree-based model từ scikit-learn. |
| Improved model | RandomForest, HistGradientBoosting, hoặc CatBoost-like approach nếu dependency risk chấp nhận được ở phase sau. |
| Features | Area, rooms, floor, total floors, property type, city/district, coordinates, OSM distances/counts, listing metadata. |
| Validation | Ưu tiên split theo `observed_at`; fallback holdout stratified theo price/rooms/district. Duplicates không được cross train/test. |
| Metrics | MAE, RMSE, MAPE, R2, kèm comparison với naive baseline. |
| MLflow | Log parameters, metrics, artifacts, feature set version, run ID và selected model version. |
| Interpretation | Feature importance là bắt buộc. SHAP thêm vào nếu compatible và stable. |

MVP không yêu cầu NLP trên listing descriptions. Descriptions có thể lưu cho thử nghiệm sau, nhưng model đầu tiên nên dựa vào structured features để dễ debug và bảo vệ.

## 10. API scope

FastAPI là serving boundary cho model predictions và dashboard data.

Required endpoints:

| Endpoint | Mục đích |
|---|---|
| `GET /health` | Trả API health cộng DB/Redis/model readiness nếu practical. |
| `GET /data` | Trả filtered listing data hoặc aggregate previews cho dashboard. |
| `POST /predict` | Nhận apartment features và trả predicted price, model version, basic model metadata. |
| `GET /monitoring/status` | Trả source statuses, ingestion run summaries, record counts và recent errors. |

API expectations:

- Swagger/OpenAPI phải available.
- Pydantic schemas phải validate prediction input/output.
- `/predict` không scrape và không train. Endpoint này chỉ load selected model artifact.
- API responses cần đủ metadata để Streamlit giải thích kết quả, đặc biệt là model version và metrics summary.

## 11. Streamlit scope

Streamlit là bề mặt demo/bảo vệ chính. Nó phải cho người chấm thấy project có dữ liệu thật, prediction hoạt động, monitoring và interpretability.

Proposed pages:

| Page | Nội dung |
|---|---|
| Overview | Listing count, median price, price per square meter, distributions theo rooms/district, map hoặc geo summary nếu practical. |
| Predictions | Form nhập apartment inputs, gọi API prediction, hiển thị predicted fair price và model version. |
| Data Explorer | Filterable listing table theo price, area, rooms, district/source, data quality flags. |
| Monitoring/Logs | Source status, ingestion runs, record counts, rejected rows, recent errors/logs. |
| Model Insights | Metrics, MLflow run ID, feature importance và SHAP plots nếu available. |

Yêu cầu môn học tối thiểu là Streamlit có ít nhất 3 pages. Thiết kế 5-page ở trên được khuyến nghị vì dễ thể hiện grade 5 hơn.

## 12. Redis scope

Redis phải phục vụ read path thật, không chỉ tồn tại trong Docker.

Recommended cache targets:

- Overview aggregate stats.
- Filtered data previews từ `/data`.
- Source status summaries.
- Recent prediction responses cho identical input hashes.
- Temporary OSM query results trong enrichment, còn output enrichment cuối cùng vẫn lưu PostgreSQL.

Invalidation/refresh rules:

- Refresh relevant cache entries sau successful ingestion run.
- Refresh model-related prediction cache khi active model version đổi.
- Dùng short TTL cho dashboard/API cache, ví dụ 5-30 phút trong MVP implementation.

## 13. Testing và CI scope

Testing nên tập trung vào phần rủi ro nhất: source data, import contract, cleaning, deduplication, feature generation, API schemas và ML smoke behavior.

Required test groups:

| Group | Mục tiêu test |
|---|---|
| Import contract tests | Thiếu required teammate fields thì bị reject với error report. Valid rows được accept. |
| Parser/normalizer tests | Raw listing payload normalize thành expected field types và validation states. |
| Deduplication tests | Duplicate source IDs và cross-source matching không tạo canonical duplicates sai. |
| Feature tests | OSM và ML feature snapshots có shape, nullability và flags đúng. |
| API tests | `/health`, `/data`, `/predict`, monitoring endpoint trả expected schemas/status codes. |
| ML smoke tests | Training pipeline chạy trên sample nhỏ, log MLflow và tạo artifact. |

CI expectations:

- GitHub Actions chạy `ruff` và `pytest`.
- Coverage target ít nhất 50%.
- Optional type checking bằng `mypy` hoặc `pyright` nếu không làm project chậm quá.
- Integration tests có thể dùng lightweight PostgreSQL/Redis services trong CI khi implementation tới phase đó.

## 14. Verification criteria

### 14.1 Phase 0 completion criteria

Phase 0 chỉ complete khi tất cả điều sau đúng:

- File design spec này tồn tại dưới `RealtyScope/docs/superpowers/specs/`.
- Spec có đủ requirements register, architecture, source strategy, teammate import contract, DB/Alembic expectations, ML/API/Streamlit/Redis/testing/CI scope và verification criteria.
- User review file đã ghi và approve rõ ràng rằng spec sẵn sàng cho implementation planning.
- Không có implementation files, scaffold hoặc git initialization trước spec approval gate.

### 14.2 Tiêu chí verify project cuối cùng

Các tiêu chí này thuộc phase sau, nhưng Phase 0 ghi trước để việc lập kế hoạch triển khai bám theo.

| Mảng | Bằng chứng cần có sau này |
|---|---|
| Reproducibility | `docker compose up --build` start được required services local. |
| Data | PostgreSQL có ít nhất 1000 clean listings từ Domclick cộng OSM enrichment; teammate source được include nếu available. |
| Migrations | Alembic migrate được fresh database lên current schema. |
| EDA | Notebook có plots, missingness analysis, outlier review, geo coverage và conclusions. |
| ML | Trained model thắng naive baseline trên agreed metrics. |
| MLflow | MLflow có runs, params, metrics, artifacts và selected model metadata. |
| API | Swagger mở được và `/health`, `/data`, `/predict`, monitoring endpoint hoạt động. |
| Streamlit | Dashboard hiển thị overview, prediction, data explorer, monitoring/logs và model insights. |
| Interpretability | UI hiển thị feature importance hoặc SHAP explanations. |
| Redis | Redis được dùng bởi ít nhất một API/dashboard read path thật. |
| Tests | `pytest` pass và coverage ít nhất 50%. |
| CI | GitHub Actions chạy lint và tests. |
| Code quality | Ruff, formatting, pre-commit và typing expectations được document và dùng. |

## 15. Rủi ro và cách giảm rủi ro

| Rủi ro | Cách giảm rủi ro |
|---|---|
| Domclick block scraping hoặc đổi markup | Giữ collector replaceable, lưu raw snapshots, dùng delays/caps, hỗ trợ teammate/import fallback. |
| Public OSM geocoding limits | Ưu tiên listing coordinates, cache geocoding, tránh bulk public Nominatim, cân nhắc offline extracts ở phase sau. |
| Duplicate listings gây train/test leakage | Dedup trước khi split và group duplicate source links dưới canonical listing IDs. |
| Teammate source tới muộn hoặc cột khác dự kiến | Dùng import contract và error report; teammate source optional cho core MVP nhưng đã sẵn cho grade/team scope. |
| Redis chỉ khai báo mà không dùng | Định nghĩa explicit cache paths và verify trong API/dashboard behavior. |
| SHAP không ổn định với selected model | Feature importance là baseline interpretability bắt buộc; thêm SHAP khi model hỗ trợ ổn định. |
| Scope phình quá rộng | Giữ MVP là Moscow sale-price regression; postpone rent/multi-city/NLP cho tới khi core grade-5 requirements đã đạt. |

## 16. Plan theo phase sau khi spec được approve

Toàn bộ project nên dùng các goal theo phase thay vì một goal rất lớn.

Các phase khuyến nghị sau này:

1. Phase 1: khởi tạo repo, scaffold project, Docker skeleton, tooling, CI baseline.
2. Phase 2: Domclick collector, teammate import contract, raw/normalized data path.
3. Phase 3: PostgreSQL schema, Alembic migrations, cleaning, OSM enrichment, EDA.
4. Phase 4: ML training, MLflow tracking, feature snapshots, model registry.
5. Phase 5: FastAPI, Redis cache, Streamlit dashboard, monitoring/logs.
6. Phase 6: tests, CI hardening, README, screenshots, final defense polish.

## 17. Chính sách ngôn ngữ và GitHub

Để repo nhìn tự nhiên và dễ chấm trên GitHub, dùng quy ước sau:

- `README.md`, notebook EDA, mô tả kết quả và tài liệu nộp chính nên viết bằng tiếng Nga.
- Internal planning docs trong `docs/superpowers/` có thể dùng tiếng Việt để chủ project dễ hiểu.
- Code, tên module, tên function, endpoint, table, config key và docstring ngắn nên dùng tiếng Anh kỹ thuật.
- Commit messages dùng English Conventional Commits, ví dụ `feat: add api health endpoint`, `docs: add phase 1 README`.
- Branch public nên dùng tên tự nhiên như `phase1-scaffold`, `phase2-data-ingestion`; tránh `codex/*`, `openai/*` hoặc tên làm lộ tool trên GitHub public.
- Không dùng public Codex/OpenAI PR review/comment nếu không cần cho bài nộp. Repo nên thể hiện chủ project là người sở hữu, hiểu và bảo vệ được toàn bộ nội dung.

Việc lập implementation plan chỉ bắt đầu sau khi user review file spec này và approve rõ ràng rằng nó sẵn sàng cho implementation planning.
