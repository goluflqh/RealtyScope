# RealtyScope Phase 5 Non-Leaky Model

Date: 2026-06-02
Phase: 5 ML leakage control and MLOps hardening

## Scope

Phase 5 keeps the Phase 4 feature snapshot for reproducibility and adds a new feature version:

- `ml_features_v1`: legacy baseline contract that still includes latest observation price fields.
- `ml_features_v2_non_leaky`: leakage-controlled snapshot for model-quality evidence.

The v2 snapshot removes target-like price features from the model input, including
`latest_observation_price_rub` and `latest_observation_price_per_m2`. The target remains
`target_price_rub`, but no feature key in v2 contains `price`.

Training now also stores grouped validation metadata. Rows are split by `listing_id`, so future
duplicate observation rows for the same listing cannot land in both train and test sets.

## Commands

Feature summary:

```powershell
$env:DATABASE_URL='postgresql+psycopg://realtyscope:realtyscope@localhost:5432/realtyscope'
.\.venv\Scripts\python.exe -m realtyscope.ml.features `
  --database-url $env:DATABASE_URL `
  --limit 10 `
  --feature-version ml_features_v2_non_leaky `
  --json
```

Training:

```powershell
$env:DATABASE_URL='postgresql+psycopg://realtyscope:realtyscope@localhost:5432/realtyscope'
.\.venv\Scripts\python.exe -m realtyscope.ml.train `
  --database-url $env:DATABASE_URL `
  --output-dir data/processed/models/phase5 `
  --feature-version ml_features_v2_non_leaky `
  --json
```

To log a real MLflow run, install the optional ML dependencies and pass a tracking URI:

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[ml]"
.\.venv\Scripts\python.exe -m realtyscope.ml.train `
  --database-url $env:DATABASE_URL `
  --output-dir data/processed/models/phase5 `
  --feature-version ml_features_v2_non_leaky `
  --mlflow-tracking-uri file:///$((Resolve-Path data/processed/mlruns).Path.Replace('\\','/')) `
  --json
```

## Runtime Evidence

The local PostgreSQL database had 2,000 ML-ready listings and 4 live `osm_features` rows from the
bounded Phase 5 OSM slice.

Feature probe over the first 10 rows:

| Field | Value |
| --- | ---: |
| Feature version | `ml_features_v2_non_leaky` |
| Rows | 10 |
| Feature count | 23 |
| OSM rows present | 4 |
| Target min RUB | 11,356,930 |
| Target max RUB | 49,000,000 |
| Target mean RUB | 25,552,575.90 |

Training output on the full 2,000-row local database:

| Metric | Value |
| --- | ---: |
| Model version | `baseline_ridge_v2_non_leaky` |
| Rows total | 2,000 |
| Train rows | 1,600 |
| Test rows | 400 |
| Train listing groups | 1,600 |
| Test listing groups | 400 |
| Feature count | 23 |
| MAE | 21,189,758.79 |
| RMSE | 45,610,641.85 |
| MAPE | 0.665177 |
| R2 | 0.507154 |
| Naive MAE | 23,656,479.23 |
| Naive RMSE | 66,687,651.46 |
| MLflow run ID | `null` in this venv |

Artifact path:

```text
data/processed/models/phase5/baseline_ridge_v2_non_leaky.joblib
```

The artifact is generated local evidence and remains git-ignored under `data/processed/`.

## MLflow Status

The code logs feature version, model version, metrics, and the artifact to MLflow when
`--mlflow-tracking-uri` is configured and `mlflow` is importable. Unit tests cover this path with a
fake MLflow module so CI does not need a live MLflow service.

During the Phase 5 local runtime pass, `mlflow` was not installed in `.venv`, so no real MLflow run
ID was claimed at that time. Phase 6 supersedes that caveat with a real Docker-backed MLflow run and
registered model version; see [Phase 6 MLflow Registration Evidence](phase6-mlflow-registration.md).

## Caveats

The v2 model is more honest than the v1 artifact, but it is still a first cross-sectional baseline.
OSM coverage is only 4 rows, and the local database currently has one meaningful observation per
listing. Forecast-vs-actual evaluation should wait until daily scheduled captures accumulate richer
observation history.
