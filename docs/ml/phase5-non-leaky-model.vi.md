# Mo hinh khong leakage Phase 5 cua RealtyScope

Ngay: 2026-06-02
Phase: 5 kiem soat leakage ML va hardening MLOps

## Pham vi

Phase 5 giu feature snapshot Phase 4 de tai lap va them feature version moi:

- `ml_features_v1`: baseline cu van gom cac truong gia moi nhat tu observation.
- `ml_features_v2_non_leaky`: snapshot kiem soat leakage de doc metric model nghiem tuc hon.

Snapshot v2 loai cac feature giong target price, gom `latest_observation_price_rub` va
`latest_observation_price_per_m2`. Target van la `target_price_rub`, nhung khong feature key nao
trong v2 chua chuoi `price`.

Training cung ghi metadata validation theo nhom. Split duoc thuc hien theo `listing_id`, nen neu
sau nay co nhieu observation rows cho cung mot listing thi cac row do khong bi roi vao ca train va
test.

## Lenh chay

Tom tat feature:

```powershell
$env:DATABASE_URL='postgresql+psycopg://realtyscope:realtyscope@localhost:5432/realtyscope'
.\.venv\Scripts\python.exe -m realtyscope.ml.features `
  --database-url $env:DATABASE_URL `
  --limit 10 `
  --feature-version ml_features_v2_non_leaky `
  --json
```

Huan luyen:

```powershell
$env:DATABASE_URL='postgresql+psycopg://realtyscope:realtyscope@localhost:5432/realtyscope'
.\.venv\Scripts\python.exe -m realtyscope.ml.train `
  --database-url $env:DATABASE_URL `
  --output-dir data/processed/models/phase5 `
  --feature-version ml_features_v2_non_leaky `
  --json
```

Neu can log MLflow run that, cai optional ML dependencies va truyen tracking URI:

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[ml]"
.\.venv\Scripts\python.exe -m realtyscope.ml.train `
  --database-url $env:DATABASE_URL `
  --output-dir data/processed/models/phase5 `
  --feature-version ml_features_v2_non_leaky `
  --mlflow-tracking-uri file:///$((Resolve-Path data/processed/mlruns).Path.Replace('\\','/')) `
  --json
```

## Evidence runtime

Local PostgreSQL co 2,000 listing san sang cho ML va 4 dong `osm_features` that tu slice OSM Phase 5
co gioi han.

Probe feature tren 10 dong dau:

| Truong | Gia tri |
| --- | ---: |
| Feature version | `ml_features_v2_non_leaky` |
| So dong | 10 |
| So feature | 23 |
| Dong OSM hien co | 4 |
| Target min RUB | 11,356,930 |
| Target max RUB | 49,000,000 |
| Target mean RUB | 25,552,575.90 |

Ket qua train tren 2,000 dong local:

| Metric | Gia tri |
| --- | ---: |
| Model version | `baseline_ridge_v2_non_leaky` |
| Tong so dong | 2,000 |
| Train rows | 1,600 |
| Test rows | 400 |
| Train listing groups | 1,600 |
| Test listing groups | 400 |
| So feature | 23 |
| MAE | 21,189,758.79 |
| RMSE | 45,610,641.85 |
| MAPE | 0.665177 |
| R2 | 0.507154 |
| Naive MAE | 23,656,479.23 |
| Naive RMSE | 66,687,651.46 |
| MLflow run ID | `null` trong venv nay |

Duong dan artifact:

```text
data/processed/models/phase5/baseline_ridge_v2_non_leaky.joblib
```

Artifact la evidence sinh tu local data va van nam trong `data/processed/`, duoc git ignore.

## Trang thai MLflow

Code se log feature version, model version, metrics va artifact vao MLflow khi co
`--mlflow-tracking-uri` va import duoc package `mlflow`. Unit test cover duong nay bang fake MLflow
module de CI khong can MLflow service that.

Trong runtime local lan nay, `.venv` chua cai `mlflow`. Mot lan thu cai optional dependencies da bi
dung lai sau khi pip im lang qua lau trong luc download/install dependency set lon, vi vay khong claim
MLflow run ID that trong evidence nay.

## Luu y

Mo hinh v2 trung thuc hon artifact v1, nhung van la baseline cross-sectional dau tien. OSM coverage
moi co 4 dong, va local database hien moi co mot observation co y nghia cho moi listing. Forecast vs
actual nen doi den khi scheduled capture hang ngay tich luy lich su observation day hon.
