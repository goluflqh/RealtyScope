# Mo hinh baseline Phase 4 cua RealtyScope

Ngay: 2026-06-02
Phase: 4.4 huan luyen baseline naive va scikit-learn, san sang ghi evidence MLflow

## Pham vi

Phase 4.4 them duong huan luyen baseline dau tien co the lap lai cho bai toan du doan gia RealtyScope. Cach lam duoc giu co y don gian:

- Feature rows lay tu `realtyscope.ml.features.build_feature_rows` voi feature version `ml_features_v1`.
- Baseline naive du doan median target price cua training split.
- Baseline scikit-learn la pipeline `StandardScaler` + `Ridge(alpha=1.0)`.
- Model artifact duoc ghi bang `joblib` vao thu muc processed data da bi git ignore.
- MLflow chi duoc ghi khi co `MLFLOW_TRACKING_URI` hoac `--mlflow-tracking-uri` va package `mlflow` da duoc cai.

Day la artifact baseline/evidence, chua phai mo hinh dinh gia cuoi cung.

## Lenh chay

```powershell
.\.venv\Scripts\python.exe -m realtyscope.ml.train --output-dir data/processed/models/phase4 --json
```

Tom tat feature snapshot tu database mac dinh:

| Truong | Gia tri |
| --- | ---: |
| Feature version | `ml_features_v1` |
| So dong | 2,000 |
| So feature | 25 |
| Dong OSM hien co | 0 |
| Target min RUB | 4,699,000 |
| Target max RUB | 1,905,387,907 |
| Target mean RUB | 40,136,930.41 |

Ket qua huan luyen tren cung database:

| Metric | Gia tri |
| --- | ---: |
| Model version | `baseline_ridge_v1` |
| Tong so dong | 2,000 |
| Train rows | 1,600 |
| Test rows | 400 |
| So feature | 25 |
| MAE | 48,610.18 |
| RMSE | 75,142.55 |
| MAPE | 0.001881 |
| R2 | 0.9999987 |
| Naive MAE | 23,656,479.23 |
| Naive RMSE | 66,687,651.46 |
| MLflow run ID | `null` |

Duong dan artifact:

```text
data/processed/models/phase4/baseline_ridge_v1.joblib
```

Artifact nay duoc git ignore vi duoc sinh tu processed data cuc bo.

## Luu y

Khong nen doc metric hien tai nhu chat luong production. Snapshot `ml_features_v1` van gom cac truong gia moi nhat tu listing/observation, nen Ridge baseline co the hoc quan he gan truc tiep voi target price. Ket qua nay huu ich de chung minh feature generation, training, artifact writing va API loading co the lap lai, nhung chua phai mo hinh dinh gia doc lap.

Database live hien cung chi co mot observation cho moi listing va chua co lich su thay doi gia co y nghia. Trend/temporal modeling van qua som cho den khi scheduled capture tich luy nhieu observation tren cung listing.

OSM enrichment da co trong feature contract, nhung bang live `osm_features` hien chua co dong nao (`osm_rows_present=0`). Training vi the dang kiem thu duong missing-feature voi `osm_missing=1` cho toan bo live rows.

## Buoc tiep theo

Phase 4.5 nen expose prediction contract toi thieu dua tren shape artifact nay. API/UI can gan nhan ket qua la baseline contract result va giu caveat hien ro cho den khi co feature set khong leakage va observation history phong phu hon.
