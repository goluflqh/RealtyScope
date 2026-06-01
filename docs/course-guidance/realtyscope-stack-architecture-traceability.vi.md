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
| ML Pipeline: Feature Engineering, Model Training, MLflow Registry | EDA summary và ML-ready flags đã có; MLflow service đã có; training/model registry thật nằm ở phase sau. | `Đã lên kế hoạch` cho Phase 4 | `src/realtyscope/analysis/eda_summary.py`; `docs/data/phase3_5_eda_summary.domclick-postgres.vi.md`; `pyproject.toml` optional `ml`; `services/mlflow/Dockerfile`. | Phase 3 chuẩn bị data thật và history. Phase 4 nên train baseline ML, log MLflow runs, lưu artifacts, và định nghĩa feature snapshots. |
| Backend: FastAPI, `/data` endpoints, `/predict` endpoint | FastAPI app có `/health`, `/listings`, `/stats/data-quality`; Swagger có sẵn qua FastAPI. | `Một phần` | `services/api/app/main.py`; `tests/test_api_health.py`; `tests/test_api_data_routes.py`. | Chưa có `/data` đúng tên đề bài và `/predict`. Đây là việc Phase 4/5 sau khi có model. |
| Frontend: Streamlit Dashboard, Plotly charts, Interactive Filters | Streamlit đọc API data và hiển thị KPI cards, latest run, listing preview. | `Một phần` | `services/streamlit/app.py`; `services/streamlit/api_client.py`; `tests/test_streamlit_api_client.py`; `tests/test_streamlit_scaffold.py`. | Plotly charts, multipage layout, filters, prediction page, monitoring page, model insights là UI phase sau. |
| Docker Compose one-command local environment | Compose định nghĩa `db`, `redis`, `mlflow`, `api`, `streamlit`, có healthcheck cho db/redis/api/streamlit. | `Một phần` | `docker-compose.yml`; `services/api/Dockerfile`; `services/streamlit/Dockerfile`; `services/mlflow/Dockerfile`; `docs/development/local-environment.md`. | Structure đã đúng hướng. Acceptance cuối cùng `docker compose up --build` nên verify lại sau khi ML/API/UI đủ chức năng. |
| Project structure đề xuất: services, alembic, CI, dashboard, ML area | Monorepo dùng shared `src/realtyscope`, service folders cho API/Streamlit/MLflow, Alembic, CI, notebooks, scripts, docs. | `Đã có` theo layout thực dụng | `.github/workflows/ci.yml`; `alembic/`; `services/`; `src/realtyscope/`; `notebooks/`; `docs/`; `scripts/`. | Ingestor code nằm trong shared package + scripts thay vì image `services/ingestor` riêng. Với Phase 3, cách này dễ reuse/test và chưa làm phức tạp Compose. |

## Traceability tech stack

| Nhóm stack | Hướng dẫn của thầy | RealtyScope chọn | Trạng thái | Evidence | Lý do / Gap |
| --- | --- | --- | --- | --- | --- |
| HTTP requests | Bắt buộc: `requests`; nâng cao: `httpx`, `aiohttp`. | `urllib.request` cho collector ít dependency; `requests` cho Streamlit API client. | `Đã có` / `Thay thế có chủ đích` | `src/realtyscope/ingestion/domclick_snapshot_collector.py`; `services/streamlit/api_client.py`; `pyproject.toml`. | Collector chỉ cần HTTP cơ bản nên stdlib đủ và ít dependency hơn. `requests` vẫn dùng ở client API nơi tiện hơn. |
| HTML parsing | Bắt buộc: BeautifulSoup4; nâng cao: `lxml`, Scrapy, parsel. | Luồng Domclick hiện parse JSON/SSR state, không scrape HTML tự do. | `Thay thế có chủ đích` | `src/realtyscope/ingestion/domclick_chrome_capture.py`; `src/realtyscope/ingestion/domclick.py`. | Domclick có SSR JSON sau render; lấy dữ liệu có cấu trúc này ổn định hơn parse HTML. BeautifulSoup chỉ nên thêm nếu source sau thật sự cần. |
| Browser automation | Gợi ý: Selenium; nâng cao: Playwright/Puppeteer. | Chrome headless DOM dump trực tiếp với profile thật `Default`. | `Thay thế có chủ đích` | `src/realtyscope/ingestion/domclick_chrome_capture.py`; `docs/operations/domclick-scheduled-batch-ingestion.md`; `tests/test_domclick_chrome_capture.py`. | Ít dependency hơn Selenium/Playwright nhưng vẫn capture được rendered public search state qua Chrome. Có giới hạn, có test, có docs vận hành. |
| Task scheduler | Bắt buộc: APScheduler; thay thế: Celery Beat, cron, Airflow. | Windows Task Scheduler cho máy local; cron/systemd examples cho Linux. | `Thay thế có chủ đích` | `scripts/run_domclick_scheduled_batch.ps1`; `docs/operations/domclick-scheduled-batch-ingestion.md`; scheduled task `RealtyScope Domclick Scheduled Batch`. | OS scheduler hợp hơn cho daily bounded batch: chạy, fail rõ, rồi thoát. APScheduler có thể xét lại nếu sau này có ingestor service chạy liên tục. |
| Relational DB | PostgreSQL; SQLite chỉ để dev. | PostgreSQL cho runtime thật; SQLite cho test/Alembic smoke check hẹp. | `Đã có` | `docker-compose.yml`; `src/realtyscope/config.py`; `tests/*database*`. | Đúng hướng dẫn. |
| ORM | SQLAlchemy 2.0. | SQLAlchemy 2.0 typed models. | `Đã có` | `src/realtyscope/database/base.py`; `src/realtyscope/database/models.py`; `pyproject.toml`. | Đúng hướng dẫn. |
| Migrations | Alembic. | Alembic có initial DB foundation và migration observations Phase 3.7. | `Đã có` | `alembic/env.py`; `alembic/versions/20260531_0001_initial_database_foundation.py`; `alembic/versions/20260602_0002_listing_observations.py`; `tests/test_alembic_config.py`. | Đáp ứng kỳ vọng grade-5 về migrations. |
| Cache | Redis. | Redis service đã có; chưa có API/dashboard cache path thật. | `Một phần` | `docker-compose.yml`; `.env.example`; `pyproject.toml`. | Giữ Redis cho Phase 5 read-path optimization. Chưa nên claim điểm cache grade-5 khi chưa có behavior thật. |
| File storage | Local filesystem; nâng cao: MinIO/S3. | Local ignored `data/raw/` và `data/processed/` cho snapshots/reports; model artifacts sau qua MLflow volume. | `Đã có` cho Phase 3 | `docs/operations/domclick-daily-collection.md`; `.gitignore`; `services/mlflow/Dockerfile`. | MinIO/S3 chưa cần cho semester MVP trừ khi deployment lớn hơn. |
| Data processing / EDA | pandas, numpy, scipy, Jupyter. | pandas và notebook skeleton/summary command đã có; EDA sâu hơn còn thiếu. | `Một phần` | `pyproject.toml`; `notebooks/phase3_eda_skeleton.ipynb`; `src/realtyscope/analysis/eda_summary.py`; `tests/test_eda_summary.py`. | Phase 3 đã có data thật và summary; Phase 4 nên thêm EDA kết luận đầy đủ trước ML. |
| Machine Learning | scikit-learn, CatBoost, joblib, metrics, optional time-series/NLP/interpretable methods. | Optional `ml` deps có scikit-learn, MLflow, joblib; chưa train model. | `Đã lên kế hoạch` | `pyproject.toml`; `docs/superpowers/specs/2026-05-31-realtyscope-design.md`. | Phase 4 nên bắt đầu bằng scikit-learn baseline đơn giản trước khi thêm CatBoost/SHAP. NLP chưa cần cho model đầu tiên. |
| Experiment tracking | File logs bắt buộc; MLflow nâng cao/grade-5. | MLflow service/Dockerfile đã có; real runs chưa có. | `Một phần` | `docker-compose.yml`; `services/mlflow/Dockerfile`; `pyproject.toml`. | Chỉ claim MLflow sau khi Phase 4 log training runs thật. |
| Backend API | FastAPI, Pydantic, uvicorn, Swagger. | FastAPI + Pydantic stack đã cài và test; có DB-backed read endpoints. | `Một phần` | `services/api/app/main.py`; `services/api/Dockerfile`; `tests/test_api_health.py`; `tests/test_api_data_routes.py`. | `/predict` và `/data` đúng tên đề bài còn thiếu tới khi ML sẵn sàng. |
| Frontend and visualization | Streamlit, Plotly, maps qua `streamlit.map` hoặc mapping libs. | Streamlit dashboard slice đã có; chưa có Plotly/maps. | `Một phần` | `services/streamlit/app.py`; `services/streamlit/Dockerfile`; `tests/test_streamlit_scaffold.py`. | Thêm Plotly/time-series charts sau observations Phase 3.7 và model outputs Phase 4. |
| DevOps and infrastructure | Docker/docker-compose, GitHub Actions, ruff, ruff format, pre-commit, pytest, dependency management. | Docker Compose, service Dockerfiles, CI, ruff, ruff format, pytest, pytest-cov, pre-commit dependency, `uv.lock`. | Nền tảng `Đã có` | `docker-compose.yml`; `.github/workflows/ci.yml`; `pyproject.toml`; `uv.lock`; `README.md`. | `uv` thay `requirements.txt` vì lockfile reproducible hơn cho repo này. Có thể thêm pre-commit config nếu grading yêu cầu file cụ thể. |

## Các thay thế có chủ đích

RealtyScope hiện thay một vài công nghệ thầy gợi ý vì cách thay thế đơn giản hơn hoặc hợp vận hành hơn:

- Chrome headless DOM dump thay Selenium/Playwright: ít dependency hơn, dùng Chrome profile local thật, đủ cho Domclick SSR capture.
- Windows Task Scheduler / cron / systemd thay APScheduler: hợp hơn cho daily bounded batch cần chạy, fail rõ, rồi thoát.
- `uv.lock` thay `requirements.txt`: reproducibility tốt hơn, vẫn phù hợp pip/uv workflow.
- Parse SSR JSON thay BeautifulSoup HTML scraping: có cấu trúc hơn và ít brittle hơn với source Domclick hiện tại.

Những thay thế này nên tiếp tục được document. Nếu phase sau có ingestor service chạy liên tục hoặc source mới cần interaction DOM phức tạp hơn `--dump-dom`, có thể xét lại APScheduler hoặc Playwright/Selenium.

## Tín hiệu sẵn sàng của Phase 3

Với Phase 3, nền tảng kiến trúc và stack đã khá ổn:

- data capture và persistence là thật, bounded, có gate;
- PostgreSQL schema đi qua Alembic;
- canonical listings và observation history hỗ trợ cả latest reads và trend future;
- FastAPI và Streamlit đã có slice đọc DB;
- Docker/CI/ruff/pytest foundation đã có.

Phase 4 không cần chờ UI/cache/MLflow hoàn hảo. Phase 4 nên bắt đầu sau khi capture thật hôm nay được verify, vì các gap lớn còn lại chính là trách nhiệm Phase 4+: EDA chi tiết hơn, baseline ML, MLflow runs, model artifacts, và `/predict`.
