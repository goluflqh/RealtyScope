# RealtyScope Phase 4 Baseline Model

Date: 2026-06-02
Phase: 4.4 naive and scikit-learn baseline training with MLflow-ready evidence

## Scope

Phase 4.4 adds the first reproducible baseline training path for RealtyScope price prediction. It is intentionally conservative:

- Feature rows come from `realtyscope.ml.features.build_feature_rows` with feature version `ml_features_v1`.
- The naive baseline predicts the median target price from the training split.
- The scikit-learn baseline is a `StandardScaler` + `Ridge(alpha=1.0)` pipeline.
- The model artifact is written with `joblib` to an ignored processed-data directory.
- MLflow logging is optional and only runs when `MLFLOW_TRACKING_URI` or `--mlflow-tracking-uri` is configured and the `mlflow` package is installed.

This is a baseline evidence artifact, not the final valuation model.

## Command

```powershell
.\.venv\Scripts\python.exe -m realtyscope.ml.train --output-dir data/processed/models/phase4 --json
```

Feature snapshot summary from the default database:

| Field | Value |
| --- | ---: |
| Feature version | `ml_features_v1` |
| Rows | 2,000 |
| Feature count | 25 |
| OSM rows present | 0 |
| Target min RUB | 4,699,000 |
| Target max RUB | 1,905,387,907 |
| Target mean RUB | 40,136,930.41 |

Training output from the same database:

| Metric | Value |
| --- | ---: |
| Model version | `baseline_ridge_v1` |
| Rows total | 2,000 |
| Train rows | 1,600 |
| Test rows | 400 |
| Feature count | 25 |
| MAE | 48,610.18 |
| RMSE | 75,142.55 |
| MAPE | 0.001881 |
| R2 | 0.9999987 |
| Naive MAE | 23,656,479.23 |
| Naive RMSE | 66,687,651.46 |
| MLflow run ID | `null` |

Artifact path:

```text
data/processed/models/phase4/baseline_ridge_v1.joblib
```

The artifact is intentionally ignored by git because it is generated from local processed data.

## Caveats

The current metric quality must not be read as production model quality. The `ml_features_v1` snapshot still includes latest listing/observation price fields, so the Ridge baseline can learn a near-direct relationship to the target price. This is useful for proving deterministic feature generation, training, artifact writing, and future API loading, but it is not yet an independent appraisal model.

The live database also has one observation per listing and no meaningful price-change history yet. Temporal trend modeling is premature until scheduled captures accumulate repeated observations for the same listings.

OSM enrichment is wired into the feature contract but live `osm_features` rows are currently absent (`osm_rows_present=0`). Training therefore exercises the missing-feature path with `osm_missing=1` for all live rows.

## Next Step

Phase 4.5 should expose a minimal prediction contract against this artifact shape. The UI/API should label predictions as a baseline contract result and keep the caveat visible until a leakage-controlled feature set and richer observation history are available.
