# RealtyScope Phase 6 MLflow Registration Evidence

Date: 2026-06-03
Phase: 6 MLflow production-like evidence and model registration

## Scope

Phase 6 extends the Phase 5 non-leaky baseline evidence with a real MLflow run, a
registered MLflow model version, and persisted model artifacts in Docker-managed volumes.

The training command still uses `ml_features_v2_non_leaky` and grouped validation by
`listing_id`. This evidence does not claim the baseline is a final appraisal model; it proves
the MLOps path is real and reproducible from the Docker runtime.

## Reproducible Docker Path

The committed Compose path is:

```bash
docker compose -p realtyscope up --build -d
docker compose -p realtyscope --profile tools run --build --rm trainer
```

Compose builds the app images from scoped in-repo contexts (`docker/build/deps`, `src`, and
`services`) instead of using the repository root as the Docker build context. That keeps the
one-command Docker path independent from local generated cache directories. The `trainer`
service installs the `data` and `ml` extras, writes the joblib artifact to the shared
`model_artifacts` volume, logs params/metrics/artifacts to MLflow, and registers the sklearn
model as `realtyscope-price-model`.

## Runtime Evidence

The verified runtime stack was the Docker Compose project `realtyscope`, rebuilt directly
from the Windows-mounted repository with `docker compose -p realtyscope up --build -d`.
The training run used the same mounted volumes as the committed `trainer` service:

- `realtyscope_model_artifacts:/app/data/processed/models`
- `realtyscope_mlflow_data:/mlflow`

MLflow run and registry evidence:

| Field | Value |
| --- | --- |
| MLflow run ID | `4999892d2d92402ab78e1209203c338e` |
| Run status | `FINISHED` |
| Registered model | `realtyscope-price-model` |
| Registered version | `3` |
| Model URI | `runs:/4999892d2d92402ab78e1209203c338e/model` |
| Artifact path | `data/processed/models/phase5/baseline_ridge_v2_non_leaky.joblib` |

Training metrics from the run:

| Metric | Value |
| --- | ---: |
| Rows total | 3,019 |
| Train rows | 2,415 |
| Test rows | 604 |
| Feature count | 23 |
| MAE | 22,685,629.92 |
| RMSE | 54,318,379.07 |
| MAPE | 0.586170 |
| R2 | 0.531749 |
| Naive MAE | 28,452,175.74 |
| Naive RMSE | 81,881,302.72 |

## Verification Commands

Run status and metrics were verified via MLflow REST:

```bash
python3 -c "import json, urllib.request; run_id='4999892d2d92402ab78e1209203c338e'; data=json.load(urllib.request.urlopen(f'http://localhost:5000/api/2.0/mlflow/runs/get?run_id={run_id}')); print(data['run']['info']['status'])"
```

Registered model version was verified via MLflow REST:

```bash
python3 -c "import json, urllib.parse, urllib.request; name=urllib.parse.quote('realtyscope-price-model'); data=json.load(urllib.request.urlopen(f'http://localhost:5000/api/2.0/mlflow/registered-models/get?name={name}')); print([(v['version'], v['run_id'], v['source']) for v in data['registered_model'].get('latest_versions', [])])"
```

Artifact presence was verified through MLflow artifacts API and filesystem-backed volume:

```bash
python3 -c "import json, urllib.request; run_id='4999892d2d92402ab78e1209203c338e'; print(json.load(urllib.request.urlopen(f'http://localhost:5000/api/2.0/mlflow/artifacts/list?run_id={run_id}')))"
docker exec realtyscope-mlflow-1 sh -c 'find /mlflow/artifacts/0/4999892d2d92402ab78e1209203c338e/artifacts -maxdepth 3 -type f | sort'
```

The verified artifact files included:

- `baseline_ridge_v2_non_leaky.joblib`
- `model/MLmodel`
- `model/model.pkl`
- `model/conda.yaml`
- `model/python_env.yaml`
- `model/requirements.txt`

## Caveats

The local Windows repository still contains a permission-broken generated `.pytest_cache`
directory. Compose no longer uses the repository root as a build context, so the verified
`up --build` and `trainer` commands above do not require deleting that local cache and do not
use the old temp build context workaround.
