# Ma trận truy vết Tech Stack và Architecture của RealtyScope

Ngày: 2026-06-02
Nguồn: `E:\Магистр\2-курс\python\Описание проекта.html`, các phần `Как это устроено` và `Технологический стек`.
Đối tượng đọc: người chấm môn học, agent triển khai, và planning các phase sau.

Tài liệu này map phần kiến trúc DataPulse và stack công nghệ thầy tổng kết sang RealtyScope. Mình xem danh sách stack là hướng dẫn rất đáng tham khảo, không phải checklist phải dùng mù quáng. RealtyScope dùng công nghệ phù hợp với phase hiện tại, ghi rõ chỗ thay thế có chủ đích, và đánh dấu trung thực các phần chưa làm.

## Chú giải trạng thái

- `Đã có`: đã có code/config/docs chạy được trong repo.
- `Một phần`: đã có nền tảng, nhưng chưa đủ acceptance-grade behavior.
- `Đã lên kế hoạch`: cố ý để phase sau.
- `Thay thế có chủ đích`: cùng trách nhiệm nhưng dùng cách khác, có lý do.
- `Không dùng`: hiện chưa cần cho scope RealtyScope.

## Traceability kiến trúc

| Mục kiến trúc trong đề bài | Mapping sang RealtyScope | Trạng thái | Evidence | Ghi chú / Gap |
| --- | --- | --- | --- | --- |
| Data Layer: External APIs, Web Scraping, Ingestor Service | Domclick snapshot collector, Chrome-assisted SSR capture, parser contracts, teammate CSV import, scheduled batch runner. | `Đã có` cho Phase 3 | `src/realtyscope/ingestion/domclick_snapshot_collector.py`; `src/realtyscope/ingestion/domclick_chrome_capture.py`; `src/realtyscope/ingestion/domclick_scheduled_batch.py`; `src/realtyscope/ingestion/contracts.py`; `src/realtyscope/ingestion/teammate_import.py`; `scripts/run_domclick_scheduled_batch.ps1`. | Đang làm bounded batch ingestion, không phải scraper chạy mãi. Cách này an toàn hơn với Domclick và dễ test hơn. |
| Storage: PostgreSQL, Redis Cache, Model Artifacts | PostgreSQL qua Docker Compose, SQLAlchemy models, Alembic migrations, Redis service, MLflow volume/model-artifact placeholder. | PostgreSQL/Alembic `Đã có`; Redis/model artifacts `Một phần` | `docker-compose.yml`; `src/realtyscope/database/models.py`; `alembic/versions/*.py`; `services/mlflow/Dockerfile`; `.env.example`. | Redis đã sẵn sàng để chạy nhưng chưa có read path thật. Model artifacts thuộc Phase 4. |
| ML Pipeline: Feature Engineering, Model Training, MLflow Registry | Feature snapshots v1/v2 deterministic, Ridge baseline không leakage, grouped validation, joblib artifacts bị ignore, và MLflow logging path khi cấu hình. | `Một phần` | `src/realtyscope/ml/features.py`; `src/realtyscope/ml/train.py`; `docs/ml/phase5-non-leaky-model.vi.md`; `tests/test_ml_features.py`; `tests/test_ml_training.py`; `services/mlflow/Dockerfile`. | Runtime local chưa có MLflow run ID thật vì `.venv` thiếu `mlflow`; package/service setup vẫn cần verify kiểu production-like. |
| Backend: FastAPI, `/data` endpoints, `/predict` endpoint | FastAPI app có `/health`, `/listings`, `/stats/data-quality`, `/predict`, `/model/metadata`, và `/monitoring/status`; Swagger có sẵn qua FastAPI. | `Một phần` | `services/api/app/main.py`; `tests/test_api_health.py`; `tests/test_api_data_routes.py`; `tests/test_api_prediction_contract.py`; `tests/test_api_monitoring.py`. | `/data` đúng tên đề bài vẫn đang được đại diện bằng `/listings`; Redis cache chưa dùng ở read path thật. |
| Frontend: Streamlit Dashboard, Plotly charts, Interactive Filters | Streamlit đọc API data và hiển thị KPI cards, latest run, listing preview, prediction, monitoring status, recent errors, metrics, và feature importance. | `Một phần` | `services/streamlit/app.py`; `services/streamlit/api_client.py`; `tests/test_streamlit_api_client.py`; `tests/test_streamlit_scaffold.py`. | Plotly charts, map views, filters giàu hơn, và multipage layout thật vẫn là polish sau. |
| Docker Compose one-command local environment | Compose định nghĩa `db`, `redis`, `mlflow`, `api`, `streamlit`, có healthcheck cho db/redis/api/streamlit. | `Một phần` | `docker-compose.yml`; `services/api/Dockerfile`; `services/streamlit/Dockerfile`; `services/mlflow/Dockerfile`; `docs/development/local-environment.md`. | Structure đã đúng hướng. Acceptance cuối cùng `docker compose up --build` nên verify lại sau khi ML/API/UI đủ chức năng. |
| Project structure đề xuất: services, alembic, CI, dashboard, ML area | Monorepo dùng shared `src/realtyscope`, service folders cho API/Streamlit/MLflow, Alembic, CI, notebooks, scripts, docs. | `Đã có` theo layout thực dụng | `.github/workflows/ci.yml`; `alembic/`; `services/`; `src/realtyscope/`; `notebooks/`; `docs/`; `scripts/`. | Ingestor code nằm trong shared package + scripts thay vì image `services/ingestor` riêng. Với Phase 3, cách này dễ reuse/test và chưa làm phức tạp Compose. |

## Traceability tech stack

| Nhóm stack | Hướng dẫn của thầy | RealtyScope chọn | Trạng thái | Evidence | Lý do / Gap |
| --- | --- | --- | --- | --- | --- |
| HTTP requests | Bắt buộc: `requests`; nâng cao: `httpx`, `aiohttp`. | `urllib.request` cho collector ít dependency; `requests` cho Streamlit API client. | `Đã có` / `Thay thế có chủ đích` | `src/realtyscope/ingestion/domclick_snapshot_collector.py`; `services/streamlit/api_client.py`; `pyproject.toml`. | Collector chỉ cần HTTP cơ bản nên stdlib đủ và ít dependency hơn. `requests` vẫn dùng ở client API nơi tiện hơn. |
| HTML parsing | Bắt buộc: BeautifulSoup4; nâng cao: `lxml`, Scrapy, parsel. | Luồng Domclick hiện parse JSON/SSR state, không scrape HTML tự do. | `Thay thế có chủ đích` | `src/realtyscope/ingestion/domclick_chrome_capture.py`; `src/realtyscope/ingestion/domclick.py`. | Domclick có SSR JSON sau render; lấy dữ liệu có cấu trúc này ổn định hơn parse HTML. BeautifulSoup chỉ nên thêm nếu source sau thật sự cần. |
| Browser automation | Gợi ý: Selenium; nâng cao: Playwright/Puppeteer. | Chrome DevTools/CDP-assisted SSR capture với profile thật `Default`; `--dump-dom` chỉ còn là fallback một lần. | `Thay thế có chủ đích` | `src/realtyscope/ingestion/domclick_chrome_capture.py`; `docs/operations/domclick-scheduled-batch-ingestion.md`; `tests/test_domclick_chrome_capture.py`. | Ít dependency hơn Selenium/Playwright, đồng thời không phụ thuộc việc user mở sẵn tab Chrome trong Codex. Có giới hạn, có test, có docs vận hành. |
| Task scheduler | Bắt buộc: APScheduler; thay thế: Celery Beat, cron, Airflow. | Windows Task Scheduler cho máy local; cron/systemd examples cho Linux. | `Thay thế có chủ đích` | `scripts/run_domclick_scheduled_batch.ps1`; `docs/operations/domclick-scheduled-batch-ingestion.md`; scheduled task `RealtyScope Domclick Scheduled Batch`. | OS scheduler hợp hơn cho daily bounded batch: chạy, fail rõ, rồi thoát. APScheduler có thể xét lại nếu sau này có ingestor service chạy liên tục. |
| Relational DB | PostgreSQL; SQLite chỉ để dev. | PostgreSQL cho runtime thật; SQLite cho test/Alembic smoke check hẹp. | `Đã có` | `docker-compose.yml`; `src/realtyscope/config.py`; `tests/*database*`. | Đúng hướng dẫn. |
| ORM | SQLAlchemy 2.0. | SQLAlchemy 2.0 typed models. | `Đã có` | `src/realtyscope/database/base.py`; `src/realtyscope/database/models.py`; `pyproject.toml`. | Đúng hướng dẫn. |
| Migrations | Alembic. | Alembic có initial DB foundation và migration observations Phase 3.7. | `Đã có` | `alembic/env.py`; `alembic/versions/20260531_0001_initial_database_foundation.py`; `alembic/versions/20260602_0002_listing_observations.py`; `tests/test_alembic_config.py`. | Đáp ứng kỳ vọng grade-5 về migrations. |
| Cache | Redis. | Redis service đã có; chưa có API/dashboard cache path thật. | `Một phần` | `docker-compose.yml`; `.env.example`; `pyproject.toml`. | Giữ Redis cho Phase 5 read-path optimization. Chưa nên claim điểm cache grade-5 khi chưa có behavior thật. |
| File storage | Local filesystem; nâng cao: MinIO/S3. | Local ignored `data/raw/` và `data/processed/` cho snapshots/reports; model artifacts sau qua MLflow volume. | `Đã có` cho Phase 3 | `docs/operations/domclick-daily-collection.md`; `.gitignore`; `services/mlflow/Dockerfile`. | MinIO/S3 chưa cần cho semester MVP trừ khi deployment lớn hơn. |
| Data processing / EDA | pandas, numpy, scipy, Jupyter. | pandas và notebook skeleton/summary command đã có; EDA sâu hơn còn thiếu. | `Một phần` | `pyproject.toml`; `notebooks/phase3_eda_skeleton.ipynb`; `src/realtyscope/analysis/eda_summary.py`; `tests/test_eda_summary.py`. | Phase 3 đã có data thật và summary; Phase 4 nên thêm EDA kết luận đầy đủ trước ML. |
| Machine Learning | scikit-learn, CatBoost, joblib, metrics, optional time-series/NLP/interpretable methods. | Ridge baseline scikit-learn và joblib artifacts đã có cho v1 và v2 Phase 5; CatBoost/SHAP defer. | `Một phần` | `src/realtyscope/ml/train.py`; `docs/ml/phase5-non-leaky-model.vi.md`; `tests/test_ml_training.py`. | v2 không leakage nhưng vẫn là baseline cross-sectional đầu tiên. Time-series/forecast evaluation cần repeated observations. |
| Experiment tracking | File logs bắt buộc; MLflow nâng cao/grade-5. | MLflow service/Dockerfile và training log path đã có; unit tests verify params/metrics/artifact logging khi cấu hình. | `Một phần` | `src/realtyscope/ml/train.py`; `tests/test_ml_training.py`; `services/mlflow/Dockerfile`; `pyproject.toml`. | Chưa claim real MLflow run ID cho tới khi optional ML dependencies/service được verify trong target runtime. |
| Backend API | FastAPI, Pydantic, uvicorn, Swagger. | FastAPI + Pydantic đã test với data, prediction, model metadata, và monitoring endpoints. | `Một phần` | `services/api/app/main.py`; `services/api/Dockerfile`; `tests/test_api_health.py`; `tests/test_api_data_routes.py`; `tests/test_api_prediction_contract.py`; `tests/test_api_monitoring.py`. | `/data` alias đúng đề bài và Redis-backed cache path vẫn là hardening sau. |
| Frontend and visualization | Streamlit, Plotly, maps qua `streamlit.map` hoặc mapping libs. | Streamlit dashboard có overview, prediction, monitoring, và model-insight sections backed by FastAPI. | `Một phần` | `services/streamlit/app.py`; `services/streamlit/Dockerfile`; `tests/test_streamlit_api_client.py`; `tests/test_streamlit_scaffold.py`. | Plotly/time-series charts và map views có thể làm sau khi observation history và OSM coverage giàu hơn. |
| DevOps and infrastructure | Docker/docker-compose, GitHub Actions, ruff, ruff format, pre-commit, pytest, dependency management. | Docker Compose, service Dockerfiles, CI, ruff, ruff format, pytest, pytest-cov, pre-commit dependency, `uv.lock`. | Nền tảng `Đã có` | `docker-compose.yml`; `.github/workflows/ci.yml`; `pyproject.toml`; `uv.lock`; `README.md`. | `uv` thay `requirements.txt` vì lockfile reproducible hơn cho repo này. Có thể thêm pre-commit config nếu grading yêu cầu file cụ thể. |

## Các thay thế có chủ đích

RealtyScope hiện thay một vài công nghệ thầy gợi ý vì cách thay thế đơn giản hơn hoặc hợp vận hành hơn:

- Chrome DevTools/CDP SSR capture thay Selenium/Playwright: ít dependency hơn, dùng Chrome profile local thật, và ổn định hơn `--dump-dom` thuần cho Domclick SSR capture.
- Windows Task Scheduler / cron / systemd thay APScheduler: hợp hơn cho daily bounded batch cần chạy, fail rõ, rồi thoát.
- `uv.lock` thay `requirements.txt`: reproducibility tốt hơn, vẫn phù hợp pip/uv workflow.
- Parse SSR JSON thay BeautifulSoup HTML scraping: có cấu trúc hơn và ít brittle hơn với source Domclick hiện tại.

Những thay thế này nên tiếp tục được document. Nếu phase sau có ingestor service chạy liên tục hoặc source mới cần interaction DOM phức tạp hơn việc trích SSR, có thể xét lại APScheduler hoặc Playwright/Selenium.

## Tín hiệu sẵn sàng của Phase 3

Với Phase 3, nền tảng kiến trúc và stack đã khá ổn:

- data capture và persistence là thật, bounded, có gate;
- PostgreSQL schema đi qua Alembic;
- canonical listings và observation history hỗ trợ cả latest reads và trend future;
- FastAPI và Streamlit đã có slice đọc DB;
- Docker/CI/ruff/pytest foundation đã có.

Phase 4 không cần chờ UI/cache/MLflow hoàn hảo. Phase 4 nên bắt đầu sau khi capture thật hôm nay được verify, vì các gap lớn còn lại chính là trách nhiệm Phase 4+: EDA chi tiết hơn, baseline ML, MLflow runs, model artifacts, và `/predict`.
