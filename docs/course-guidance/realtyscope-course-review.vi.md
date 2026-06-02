# Tổng Hợp Hướng Dẫn Môn Học Cho RealtyScope

Ngày: 2026-05-31
Trạng thái: tài liệu tham chiếu dùng chung cho Phase 3 trở đi.
Mục tiêu: để bạn và các session/agent sau không phải nhắc lại việc đọc tài liệu môn học từ đầu.

Khi làm việc hằng ngày, dùng [Playbook vận hành theo bài giảng cho RealtyScope](realtyscope-course-operating-playbook.vi.md) như checklist đứng cho mọi phase tiếp theo. Tài liệu đó chuyển yêu cầu môn học thành quy tắc cụ thể về branch, ingestion, database, EDA, ML, API, Streamlit, Docker, CI và evidence.

---

## 1. Đã đọc và tổng hợp từ đâu

Tài liệu trong `E:\Магистр\2-курс\python\MISIS_2025\season_2`:

- `Описание проекта.html`
- `Примерный план семестра.htm`
- `S2_L1_parsing_cli_docker.ipynb`
- `S2_L2_DB.ipynb`
- `S2_L3_EDA.ipynb`
- `S2_L2_ML_part1.ipynb`
- `S2_L2_ML_part2.ipynb`
- `S2_L4_ML_classic (1).ipynb`
- `S2_L5_ML_NN_LLM_CV_GUI (1).ipynb`
- `S2_L6_GUI_RL_BACKEND (1).ipynb`
- `S2_L7_BEND2_Streamlit_BigData.ipynb`
- `L1_Start_Drum_Base.ipynb`
- `bai_giang_so_1_tom_tat_day_du.ipynb`

Docs chính thức đã đối chiếu hoặc đánh dấu làm nguồn chuẩn cho các phase sau:

- SQLAlchemy 2.0: https://docs.sqlalchemy.org/en/20/
- Alembic: https://alembic.sqlalchemy.org/en/latest/
- Pydantic v2: https://docs.pydantic.dev/
- FastAPI lifespan: https://fastapi.tiangolo.com/advanced/events/
- Nominatim policy: https://operations.osmfoundation.org/policies/nominatim/
- Overpass API examples: https://wiki.openstreetmap.org/wiki/Overpass_API/Overpass_API_by_Example
- pandas: https://pandas.pydata.org/docs/user_guide/
- scikit-learn model selection: https://scikit-learn.org/stable/model_selection.html
- MLflow tracking: https://mlflow.org/docs/latest/ml/tracking/
- Streamlit: https://docs.streamlit.io/
- Docker Compose: https://docs.docker.com/compose/

Google Developer Knowledge hiện chưa phải nguồn chính vì RealtyScope chưa dùng Google Cloud/Maps/Firebase/Gemini. Nếu sau này có thêm Google product thì mới dùng MCP đó.

---

## 2. Điều kiện chấm điểm cần giữ chắc

Dự án RealtyScope phải đi theo kiểu DataPulse: từ thu thập dữ liệu đến DB, EDA, ML, API, dashboard, Docker và CI.

Muốn đạt mức 4 cần có:

- `docker compose up --build` chạy được project.
- Ít nhất 2 nguồn dữ liệu.
- Ít nhất 1000 records trong database.
- Có xử lý missing values rõ ràng.
- Có Jupyter notebook EDA với biểu đồ và kết luận.
- Có baseline ML model, validation đúng, metric tốt hơn naive baseline.
- FastAPI có `/predict`, Swagger chạy được.
- Streamlit có ít nhất 3 pages.
- README có hướng dẫn chạy.

Muốn đạt mức 5 cần thêm:

- MLflow để track experiments, params, metrics, artifacts.
- SHAP hoặc feature importance hiển thị trong UI.
- Monitoring/logs page: trạng thái source, ingestion, lỗi/logs.
- pytest coverage mục tiêu >= 50%.
- GitHub Actions chạy lint + tests.
- Alembic quản lý schema DB.
- Redis được dùng thật cho cache/read path, không chỉ khai báo service rỗng.
- Code quality: ruff, pre-commit, type hints.

Các điểm dễ mất:

- Không có Alembic migration files: dễ mất điểm grade 5 phần migrations.
- `docker-compose.yml` không nằm ở root hoặc không chạy được: mất điểm reproducibility.
- Commit `.env`, raw dumps, DB dumps, model artifacts: sai hygiene.
- ML chỉ nằm trong notebook, không được API serve: chưa đạt yêu cầu service.
- API/UI crash khi click thử: code có cũng chưa đủ.
- Redis/MLflow/monitoring chỉ khai báo nhưng không có behavior thật: có thể bị xem là incomplete.

---

## 3. Bài giảng nói gì, áp vào RealtyScope như thế nào

### `Описание проекта.html`

Đây là file mô tả project DataPulse chính. Nó yêu cầu kiến trúc chung:

```text
External APIs / Web Scraping
  -> Ingestor Service
  -> PostgreSQL + Redis + Model Artifacts
  -> ML Pipeline + MLflow
  -> FastAPI
  -> Streamlit
  -> Docker Compose
```

Áp vào RealtyScope:

- Source listing chính: Domclick.
- Source enrichment: OpenStreetMap.
- Optional source: teammate CSV/import.
- DB chính: PostgreSQL.
- ML task: dự đoán giá bán căn hộ Moscow, target `price_rub`.
- API: health/data/predict/monitoring.
- UI: overview, prediction, data explorer, monitoring/logs, model insights.

### `Примерный план семестра.htm`

File này cho roadmap môn học. Các phần liên quan trực tiếp:

- EDA và visualization.
- Classic ML và validation/metrics.
- Data Engineering: scraping, API, PostgreSQL, SQLAlchemy, Alembic.
- Backend: FastAPI, Pydantic, pytest, TDD, type hints.
- DevOps/MLOps: Docker, GitHub Actions, MLflow.

Ý nghĩa: mỗi phase của RealtyScope nên bám theo roadmap này, không làm kiểu rời rạc.

### `S2_L1_parsing_cli_docker.ipynb`

Điểm quan trọng:

- Nếu có API thì ưu tiên API; nếu không có API thì scrape.
- Scraping phải có headers/User-Agent, timeout, session, rate-limit awareness.
- Không gọi website thật liên tục khi đang debug parser.
- Nên lưu snapshot/fixture rồi test parser trên đó.
- Phải tôn trọng `robots.txt` và đạo đức scraping.
- Docker Compose dùng để tách service và tái lập môi trường.

Ý nghĩa với Phase 2: việc mình mới làm parser snapshot Domclick, chưa live scrape, là đúng hướng an toàn. Nhưng live collector thật vẫn chưa có.

### `S2_L2_DB.ipynb`

Đây là tài liệu cực quan trọng cho Phase 3.

Điểm chính:

- `docker-compose.yml` phải ở repo root.
- PostgreSQL phải dùng volume, vì container có thể bị xóa.
- Dữ liệu external phải qua Pydantic trước khi vào DB.
- SQLAlchemy nên dùng style 2.0: `DeclarativeBase`, `Mapped`, `mapped_column`.
- Có session/transaction rõ ràng, commit/rollback đúng.
- Không nên dùng `Base.metadata.create_all()` làm schema path chính khi đã có Alembic.
- Alembic là bắt buộc cho grade 5; có thể bị kiểm tra thư mục `alembic/versions`.
- Cần link nhiều nguồn dữ liệu bằng quan hệ rõ ràng, tránh duplicate lộn xộn.

Ý nghĩa cho Phase 3:

- Phải tạo SQLAlchemy models.
- Phải tạo Alembic setup + initial migration.
- Phải verify migrate từ DB trống lên schema hiện tại.
- Phải lưu raw payload riêng với canonical listing.
- Phải có bảng ingestion runs / source status / rejected rows hoặc app logs để phục vụ monitoring sau này.

### `S2_L3_EDA.ipynb`

Điểm chính:

- EDA không phải trang trí, mà là bằng chứng phân tích.
- Cần kiểm tra shape, types, missing values, duplicates, outliers, distribution, correlation, conclusions.
- Không được âm thầm drop row lỗi mà không giải thích.
- Biểu đồ phải phục vụ quyết định ML/cleaning.

Áp vào RealtyScope:

EDA nên có:

- phân phối giá `price_rub`
- phân phối diện tích
- price per m2
- rooms/floor/floors_total
- missingness
- outliers
- coordinate coverage
- source/rejection stats
- bản đồ hoặc geo coverage nếu có tọa độ

### Các notebook ML

Điểm chính:

- Bắt đầu bằng model classic dễ giải thích.
- Phải có naive baseline.
- Phải có validation đúng, tránh leakage.
- Metrics nên có MAE/RMSE/R2 hoặc tương đương.
- Feature importance hoặc SHAP cần cho điểm 5.
- Model artifact không commit vào Git.
- MLflow dùng để track model experiments.

Áp vào RealtyScope:

- Không nên nhảy ngay sang NLP/deep learning.
- Nên bắt đầu từ Linear/Ridge/RandomForest/CatBoost hoặc tương đương.
- Nếu có duplicate listing cross-source, split train/test phải tránh leakage.

### `S2_L6_GUI_RL_BACKEND (1).ipynb`

Điểm chính:

- FastAPI dùng Pydantic schemas làm contract.
- Resource nặng như model/DB/Redis nên load một lần qua lifespan/app.state.
- Không nên load model mỗi request.
- Test API phải cover health, success case, validation error.

Áp vào RealtyScope:

- API phase sau nên dùng lifespan.
- `/predict` phải dùng đúng feature order của model đã train.
- Swagger phải phản ánh request/response schemas rõ ràng.

### `S2_L7_BEND2_Streamlit_BigData.ipynb`

Điểm chính:

- Streamlit nên là multipage dashboard.
- Nên có Analytics/Overview, Predict, Monitoring, Data table/explorer.
- `st.cache_data` cho data, `st.cache_resource` cho reusable clients/resources.
- Redis cache ở API + Streamlit cache ở UI tạo double-cache.
- Monitoring page cần API health, source status, last update, logs/errors.

Áp vào RealtyScope:

- Redis sau này phải cache đường đọc thật, ví dụ stats/source status/prediction result.
- Streamlit nên gọi FastAPI, không bypass backend cho đường production chính.

---

## 4. Kết luận cho Phase 3

Phase 3 không nên bắt đầu bằng code ngẫu nhiên. Phase 3 nên là:

1. Database foundation.
2. SQLAlchemy models.
3. Alembic initial migration.
4. Persistence từ Phase 2 `IngestionBatch` vào PostgreSQL.
5. Cleaning/ML-ready flags cơ bản.
6. Ingestion run accounting.
7. Chuẩn bị dữ liệu cho EDA.

Phase 3 chưa nên làm:

- model training hoàn chỉnh
- MLflow tracking thật
- API `/data`/`/predict` production
- Streamlit dashboard thật
- Redis cache thật
- OSM enrichment lớn/live nhiều request

Các phần đó nên sang Phase 4/5, trừ khi bạn đổi scope.

---

## 5. Checklist chống mất điểm cho các phase sau

Trước khi báo xong một phase, phải kiểm tra:

- `docker-compose.yml` vẫn ở root.
- Lệnh chạy/verify tương ứng pass.
- Không commit `.env`, raw dumps, DB dumps, model artifacts.
- DB schema changes đi qua Alembic.
- Fresh database migrate được bằng `alembic upgrade head`.
- Có tests cho validation, persistence, failure paths.
- README nói đúng trạng thái hiện tại, không phóng đại.
- Feature grade 5 nào đã claim thì phải có behavior thật.
- Tests không gọi live external services.
- Scraping/geocoding tuân thủ policy/rate limits.

---

## 6. Cách dùng tài liệu này về sau

Trước Phase 3 trở đi:

1. Đọc file này trước.
2. Đọc Phase 0 design spec: `docs/superpowers/specs/2026-05-31-realtyscope-design.md`.
3. Đọc plan phase hiện tại nếu đã có.
4. Nếu viết plan mới: viết bản kỹ thuật English + tóm tắt tiếng Việt.
5. Khi dùng thư viện nhạy version như SQLAlchemy/Alembic/FastAPI/Pydantic, kiểm tra Context7/official docs.
6. Nếu rút ra rule mới từ course/doc, lưu lại vào mem0 và cập nhật file này.
