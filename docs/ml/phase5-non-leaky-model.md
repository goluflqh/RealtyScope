# RealtyScope Non-Leaky Price Model

Updated: 2026-06-27
Artifact: `data/processed/models/phase5/selected_price_model_v1_non_leaky.joblib`
Feature version: `ml_features_v2_non_leaky`
Model version: `selected_price_model_v1_non_leaky`

## Scope

This report describes the final non-leaky apartment price model used by the RealtyScope demo and API. The model predicts `price_per_m2`; the API/UI multiply that prediction by the user-supplied `total_area_m2` to return `predicted_price_rub`.

The old UI default of `60 m²` is only an initial form value. It is not a fixed model assumption.

## Data

Verified local PostgreSQL runtime:

| Item | Value |
| --- | ---: |
| Listings | 17,287 |
| ML-ready listings | 17,287 |
| Observations | 45,764 |
| Observation days | 23 |
| Date range | 2026-05-14 to 2026-06-26 |
| Distinct listings with OSM features | 17,046 |

## Non-leaky feature contract

The `ml_features_v2_non_leaky` feature set has 23 fields:

- apartment structure: `total_area_m2`, `rooms`, `floor`, `floors_total`, `building_year`;
- missingness flags: floor, floors total, building year, coordinates, transport, observation, OSM;
- location: `latitude`, `longitude`;
- OSM infrastructure: nearest transport, transport counts, schools, parks, shops, healthcare;
- safe metadata: `observation_count`, `property_type_apartment`.

The v2 feature set excludes direct price leakage fields:

- `latest_observation_price_rub`;
- `latest_observation_price_per_m2`.

## Final selected model

The selected candidate is regularized `HistGradientBoostingRegressor`:

- `learning_rate=0.06`;
- `max_iter=240`;
- `max_leaf_nodes=31`;
- `min_samples_leaf=20`;
- `l2_regularization=0.10`.

The larger leaf size replaced the older `min_samples_leaf=2` HGB configuration to reduce generalization gap.

## Artifact metrics

Grouped random holdout from the final artifact:

| Metric | Value |
| --- | ---: |
| Rows total | 17,287 |
| Train rows | 13,829 |
| Test rows | 3,458 |
| Candidate count | 3 |
| Target variable | `price_per_m2` |
| Selected candidate | `hist_gradient_boosting` |
| Validation R² | 0.9314 |
| Train R² | 0.9595 |
| R² generalization gap | 0.0281 |
| MAE | 4.81M RUB |
| RMSE | 14.94M RUB |
| MAPE | 11.04% |

Candidate comparison:

| Candidate | R² | MAE | MAPE | Train R² | Gap |
| --- | ---: | ---: | ---: | ---: | ---: |
| HistGradientBoosting | 0.9314 | 4.81M | 11.04% | 0.9595 | 0.0281 |
| RandomForest | 0.8936 | 6.76M | 16.00% | 0.9372 | 0.0437 |
| Ridge | -0.9874 | 12.71M | 27.74% | 0.5157 | 1.5032 |

Top permutation-importance features:

1. `latitude`
2. `longitude`
3. `shops_count_1000m`
4. `building_year`
5. `total_area_m2`
6. `schools_count_1000m`
7. `floors_total`
8. `parks_count_1000m`

## Overfitting audit

The final conclusion is intentionally conservative:

- The model does not show direct target leakage because the feature set removes price-like observation fields.
- The grouped random R² around `0.93` is optimistic for real estate, where nearby listings and same-period listings are correlated.
- The model should be described as a validated educational appraisal snapshot, not a fully production-grade automatic appraiser.

Stress validation:

| Split | Test R² | MAE | MAPE | Meaning |
| --- | ---: | ---: | ---: | --- |
| Random listing holdout | 0.9345 | 4.87M | 11.10% | Headline validation, optimistic |
| Spatial grid holdout | 0.8882 | 6.94M | 17.94% | Neighborhood generalization check |
| Latest-20% temporal holdout | 0.8503 | 7.04M | 12.83% | Recent-period drift check |

## Runtime contract

`POST /predict` returns:

- `predicted_price_rub`;
- `input_features_echo`;
- `target_variable`;
- `selected_candidate`;
- `metrics_summary`;
- `feature_importance`.

For `target_variable == "price_per_m2"`, the backend scales the raw model output by `features.total_area_m2`.

The Streamlit valuation UI now exposes editable controls for all material feature groups, including area, rooms `0..20`, floors, building year, coordinates, nearest transport, schools, parks, shops, and transport counts. Unknown coordinates/OSM surroundings are represented with missing flags.

## Reproduction command

```powershell
$env:PYTHONPATH = (Resolve-Path .\src).Path
python -m realtyscope.ml.train `
  --database-url postgresql+psycopg://realtyscope:realtyscope@localhost:5432/realtyscope `
  --output-dir data/processed/models/phase5 `
  --feature-version ml_features_v2_non_leaky `
  --trainer selected `
  --target-variable price_per_m2 `
  --json
```

## Caveats

- No XGBoost result is claimed.
- Automatic retraining is intentionally not enabled.
- Spatial and temporal validation should be promoted into hard gates before any real production release.
- Exposure forecasting remains observation-gap inferred, not confirmed sale/removal labeling.
