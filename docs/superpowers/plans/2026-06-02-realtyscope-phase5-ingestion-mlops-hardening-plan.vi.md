# Kế hoạch Phase 5: hardening ingestion và MLOps cho RealtyScope

> **Cho agentic workers:** REQUIRED SUB-SKILL: dùng `superpowers:executing-plans` để triển khai từng task. User đã yêu cầu chạy inline, verify, commit và push, không dừng ở bước lập plan.

**Mục tiêu:** Làm RealtyScope đáng tin end-to-end bằng cách sửa evidence observation hằng ngày, thêm OSM rows thật, xây lại ML không leakage, và harden MLflow/API/Streamlit/monitoring.

**Kiến trúc:** Phase 5 bắt đầu từ code Phase 4 tại `36b41bc` cộng với branch docs/ops `ops-midnight-ingestor-guidance`. Slice đầu giữ dedupe raw payload, nhưng đổi semantics observation để một `observed_at` mới có chủ ý có thể tạo observation mới ngay cả khi raw content được reuse. Các slice sau giữ cùng nhịp: test RED, implementation nhỏ, verify, commit, push.

**Tech stack:** Python 3.12, SQLAlchemy 2.0, Alembic, PostgreSQL/SQLite tests, pandas, scikit-learn, MLflow, FastAPI, Streamlit, Redis, pytest, ruff, GitNexus, mem0.

---

## Trạng thái bắt đầu

- Branch: `phase5-ingestion-mlops-hardening`, tạo từ `ops-midnight-ingestor-guidance`.
- GitNexus code index: `realtyscope-phase4-index` tại `36b41bc91ad4465be088ad88794b1c133a54df29`.
- Code freshness gate: `git diff --quiet phase4-eda-ml-osm..HEAD -- src services tests scripts alembic` đã pass trước khi sửa code.
- Caveat ưu tiên từ checkpoint: scheduled run 2026-06-02 thành công nhưng reuse raw snapshot cùng ngày và không insert observation mới.

## Gate bắt buộc

- [x] Resume mem0 bằng `resume_project(project_id="python", limit=3, include_global=true)`.
- [x] Xác nhận branch/base và GitNexus code freshness trước khi sửa code.
- [x] Behavior change phải đi theo TDD: viết RED test, xác nhận fail đúng lý do, rồi mới implement.
- [x] Unit tests không gọi live Domclick hoặc live OSM.
- [x] Mỗi slice chạy focused tests trước commit.
- [ ] Trước khi claim Phase 5 complete phải chạy mới `pytest`, `ruff check`, `ruff format`, `git diff --check`.
- [ ] Commit và push từng slice sạch.
- [ ] Lưu mem0 checkpoint cuối phiên với kết quả, caveat, next step.

## Slice 1: Semantics observation cho scheduled run

**Files:**
- Sửa: `src/realtyscope/database/models.py`
- Sửa: `src/realtyscope/database/persistence.py`
- Tạo: `alembic/versions/20260602_0004_listing_observation_semantics.py`
- Sửa: `tests/test_database_persistence.py`
- Sửa: `tests/test_domclick_scheduled_batch.py`
- Sửa: `tests/test_alembic_config.py`
- Sau khi verify behavior, sửa docs: `docs/operations/domclick-scheduled-batch-ingestion.md` và `.vi.md`

- [x] Thêm regression test persistence: cùng raw payload, `observed_at` muộn hơn, cùng listing, tạo observation thứ hai nhưng reuse raw row.
- [x] Thêm regression test scheduled batch qua `run_domclick_scheduled_batch` bằng offline snapshots.
- [x] Đổi uniqueness observation từ raw-row-only sang source/listing/observed timestamp có chủ ý.
- [x] Giữ idempotency khi reprocess cùng run/cùng timestamp.
- [x] Update Alembic expectation và docs vận hành.
- [x] Verify bằng `pytest tests/test_database_persistence.py tests/test_domclick_scheduled_batch.py tests/test_alembic_config.py -q`.
- [x] Commit và push slice.

## Slice 2: OSM rows thật

- [x] Viết fixture/local persistence tests trước.
- [x] Populate DB rows từ coordinates persisted bằng execution bounded/cached, không nằm trong unit tests.
- [x] Ghi counts và OpenStreetMap attribution.
- [x] Commit và push slice.

## Slice 3: ML không leakage và MLflow evidence

- [x] RED tests cho `ml_features_v2_non_leaky`, loại target-like/latest price fields khỏi features.
- [x] Train/evaluate với naive baseline và validation không leak duplicate observations qua train/test.
- [x] Log params, metrics, artifact metadata vào MLflow khi được cấu hình.
- [ ] Commit và push slice.

## Slice 4: API, Streamlit, monitoring hardening

- [ ] Harden model/resource loading qua app state/lifespan khi practical.
- [ ] Thêm model health/metadata và monitoring payloads có tests.
- [ ] Thêm Streamlit monitoring/model insight behavior qua API client tests.
- [ ] Verify focused tests và browser/runtime checks khi service local chạy được.
- [ ] Commit và push slice.

## Verify cuối Phase 5

- [ ] `pytest`
- [ ] `ruff check .`
- [ ] `ruff format .`
- [ ] `git diff --check`
- [ ] Push trạng thái branch cuối.
- [ ] Lưu mem0 checkpoint với outcome, caveat, next step.
