# Kế Hoạch Phase 4 RealtyScope: EDA, OpenStreetMap Và Baseline ML

Ngày: 2026-06-02
Trạng thái: bản tiếng Việt có dấu, đi kèm bản kỹ thuật tiếng Anh cho agent.
Bản tiếng Anh: `docs/superpowers/plans/2026-06-02-realtyscope-phase4-eda-ml-osm-plan.md`

---

## Mục tiêu

Phase 4 biến nền tảng dữ liệu thật của Phase 3 thành bằng chứng phân tích và mô hình đầu tiên: EDA có kết luận, enrichment hạ tầng từ OpenStreetMap, feature snapshot cho ML, baseline model, MLflow evidence, và contract ban đầu cho prediction API/UI.

## Vì sao OpenStreetMap nên đặt ở Phase 4

OpenStreetMap không nên làm quá sớm khi dữ liệu listing chưa ổn định. Nó cần tọa độ listing, schema rõ, và data-quality gate ổn. Sau Phase 3.7, RealtyScope đã có:

- `2000` listing thật từ Domclick;
- canonical latest state trong `listings`;
- observation history trong `listing_observations`;
- PostgreSQL/Alembic/persistence ổn định;
- daily capture có report và gate.

Vì vậy Phase 4 là thời điểm hợp lý để thêm OpenStreetMap: không thay thế Domclick, mà bổ sung feature hạ tầng khu vực cho EDA và ML.

## Kiến trúc Phase 4

Phase 4 đọc dữ liệu từ PostgreSQL:

```text
listings + listing_observations + ingestion_runs + rejected_rows
        -> EDA readiness
        -> OSM infrastructure features
        -> ML feature snapshots
        -> baseline training + MLflow
        -> API/UI prediction contract
```

OpenStreetMap là enrichment source. Không dùng OSM làm listing source chính. Không bulk geocode bằng public Nominatim. Ưu tiên dùng tọa độ có sẵn trong listing; nếu cần gọi Overpass/public OSM thì phải giới hạn, cache, rate-limit và có attribution.

## Gate workflow bắt buộc

1. **Memory gate:** bắt đầu phase phải gọi `resume_project(project_id="python", limit=3, include_global=true)`.
2. **GitNexus gate:** trước khi sửa code phải chạy GitNexus preflight. Indexed commit phải bằng `git rev-parse HEAD`.
3. **Plan gate:** phase plan tiếng Anh và tiếng Việt phải nằm trong `docs/superpowers/plans/` trước khi implement.
4. **TDD gate:** thay đổi behavior phải có test fail trước.
5. **No live OSM in tests:** test dùng fixture hoặc local/mock data, không gọi public OSM trong test loop.
6. **Attribution gate:** nếu dùng dữ liệu/map từ OSM thì README/UI/docs phải ghi attribution OpenStreetMap.
7. **Verification gate:** không claim hoàn thành nếu chưa chạy verify mới.

## Thứ tự thực hiện khuyến nghị

1. Phase 4.0: GitNexus/workflow preflight và audit dữ liệu hiện tại.
2. Phase 4.1: EDA nâng cấp dựa trên `listings` và `listing_observations`.
3. Phase 4.2: OpenStreetMap infrastructure enrichment foundation.
4. Phase 4.3: ML feature snapshot generation.
5. Phase 4.4: Naive baseline và scikit-learn baseline, có MLflow.
6. Phase 4.5: Prediction API/UI contract.

## Task 0: GitNexus Và Workflow Preflight

**File cần đọc:**

- `docs/superpowers/realtyscope-agent-workflow.md`
- `docs/superpowers/realtyscope-agent-workflow.vi.md`

Chạy:

```powershell
git status --short --branch
git rev-parse HEAD
```

Sau đó verify GitNexus index:

```powershell
$IndexPath = "C:\Users\lequa\gitnexus-worktrees\realtyscope-phase3-5-index"
git -C $IndexPath checkout --detach (git rev-parse HEAD)
Push-Location $IndexPath
gitnexus analyze .
gitnexus status
Pop-Location
```

Kỳ vọng:

```text
GitNexus báo indexed commit == current commit.
MCP list_repos thấy repo realtyscope-phase3-5-index ở cùng commit.
```

Trước khi sửa code, dùng GitNexus MCP query/context/impact cho khu vực sẽ sửa.

## Task 1: Audit Data Readiness

Tạo module kiểm tra readiness:

- `src/realtyscope/analysis/data_readiness.py`
- `tests/test_data_readiness.py`
- `docs/data/phase4-data-readiness.vi.md`

Metrics cần có:

```text
listings_total
with_coordinates
without_coordinates
observations_total
listings_with_multiple_observations
price_changes_detected
ml_ready_listings
missing core fields: price, area, rooms, coordinates
```

Lý do: trước khi OSM/ML, phải biết data có đủ tọa độ, đủ target và đủ feature cơ bản chưa.

## Task 2: EDA Với Observation History

Tạo hoặc cập nhật notebook:

- `notebooks/phase4_eda_observations.ipynb`
- `docs/data/phase4-eda-observations.md`
- `docs/data/phase4-eda-observations.vi.md`
- `tests/test_phase4_eda_notebook.py`

Notebook phải có:

```text
phân phối price_rub
phân phối price_per_m2
area/rooms/floor distributions
missing values
outlier candidates
coordinate coverage
latest listing vs observation history
price-change examples nếu có
kết luận tiếng Việt dựa trên dữ liệu thật
```

## Task 3: OpenStreetMap Infrastructure Enrichment

Tạo foundation:

- `src/realtyscope/enrichment/osm.py`
- `src/realtyscope/enrichment/__init__.py`
- `tests/test_osm_enrichment.py`
- migration/model `osm_features` nếu lưu vào DB ngay trong Phase 4
- `docs/data/osm-enrichment.md`
- `docs/data/osm-enrichment.vi.md`

Feature khởi đầu nên giữ vừa đủ:

```text
transport_count_500m
transport_count_1000m
nearest_transport_m
schools_count_1000m
parks_count_1000m
shops_count_1000m
healthcare_count_1000m
osm_feature_version
```

Quy tắc quan trọng:

- Không gọi public OSM trong tests.
- Không bulk geocode qua public Nominatim.
- Dùng tọa độ listing có sẵn.
- Nếu gọi Overpass, phải limit, cache và rate-limit.
- Nếu show map hoặc dữ liệu derived từ OSM, phải ghi attribution.

## Task 4: ML Feature Snapshots

Tạo:

- `src/realtyscope/ml/features.py`
- `tests/test_ml_features.py`
- migration/model `ml_feature_snapshots` nếu Phase 4 lưu snapshot vào DB

Feature rows nên gồm:

```text
latest listing facts
selected/latest observation facts
OSM features nếu có
missingness flags
stable feature_version
target price_rub
```

Quan trọng: feature snapshot phải deterministic để model training reproducible.

## Task 5: Naive Baseline Và Baseline ML

Tạo:

- `src/realtyscope/ml/train.py`
- `tests/test_ml_training.py`
- `docs/ml/phase4-baseline-model.md`
- `docs/ml/phase4-baseline-model.vi.md`

Bắt đầu đơn giản:

```text
naive median hoặc median price_per_m2 baseline
Ridge/Linear Regression hoặc RandomForestRegressor
MAE, RMSE, MAPE, R2
joblib artifact
MLflow logging nếu tracking URI đã bật
```

Không nên nhảy thẳng vào model phức tạp nếu chưa có EDA và feature snapshot ổn.

## Task 6: Prediction API/UI Contract

Tạo hoặc cập nhật:

- `services/api/app/schemas.py`
- `services/api/app/main.py`
- `tests/test_api_prediction_contract.py`
- `services/streamlit/app.py` sau khi API contract ổn

Endpoint `/predict` tối thiểu trả:

```text
predicted_price_rub
model_version hoặc MLflow run_id
metrics_summary
validated feature metadata
```

API test không được train model trong lúc test. Dùng fake model dependency hoặc artifact nhỏ.

## Task 7: Docs, Verify, Commit, Checkpoint

Docs cần update:

- `README.md`
- `docs/course-guidance/realtyscope-user-story-traceability.md`
- `docs/course-guidance/realtyscope-user-story-traceability.vi.md`
- plan EN/VI nếu execution thay đổi

Verify cuối phase:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m ruff format --check .
git diff --check
gitnexus status
```

Checkpoint mem0 phải lưu:

```text
commit hashes
GitNexus index path và commit
row counts và data-readiness findings
OSM status
ML metrics và MLflow run ID nếu có
verification commands
next phase recommendation
```

## Tiêu chí hoàn thành Phase 4

Phase 4 chỉ được gọi là xong khi:

```text
GitNexus index fresh trước và sau implementation;
EDA kết luận dựa trên dữ liệu thật và observation history;
OSM enrichment đã implement có test/cache/rate-limit hoặc được split rõ sang subphase sau với lý do;
feature snapshot deterministic và tested;
baseline model train trên dữ liệu thật và so với naive baseline;
MLflow/artifact evidence có nếu enabled;
API/UI prediction contract tối thiểu có test hoặc defer rõ sang Phase 5;
full verification pass;
commit/push xong;
mem0 checkpoint lưu đầy đủ.
```
