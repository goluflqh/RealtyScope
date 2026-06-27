from __future__ import annotations

import argparse
import json
import math
import os
import sys
from collections.abc import Sequence
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import joblib
from pydantic import BaseModel, ConfigDict, Field
from sklearn.ensemble import HistGradientBoostingRegressor, RandomForestRegressor
from sklearn.inspection import permutation_importance
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from realtyscope.database.session import create_database_engine
from realtyscope.ml.features import (
    FEATURE_VERSIONS,
    NON_LEAKY_FEATURE_VERSION,
    FeatureRow,
    build_feature_rows,
)

MODEL_VERSION = "baseline_ridge_v1"
NON_LEAKY_MODEL_VERSION = "baseline_ridge_v2_non_leaky"
SELECTED_MODEL_VERSION = "selected_price_model_v1"
NON_LEAKY_SELECTED_MODEL_VERSION = "selected_price_model_v1_non_leaky"
DEFAULT_OUTPUT_DIR = Path("data/processed/models/phase4")
RANDOM_STATE = 42


@dataclass(frozen=True)
class MlflowLoggingResult:
    run_id: str | None = None
    registered_model_name: str | None = None
    model_uri: str | None = None


class TrainingResult(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    artifact_path: Path
    feature_version: str
    model_version: str
    metrics: dict[str, float | int]
    mlflow_run_id: str | None = None
    mlflow_registered_model_name: str | None = None
    mlflow_model_uri: str | None = None
    split: dict[str, Any]
    candidate_metrics: list[dict[str, Any]] = Field(default_factory=list)
    feature_importance: list[dict[str, Any]] = Field(default_factory=list)
    target_variable: str = "price_rub"


def train_baseline_model(
    *,
    feature_rows: Sequence[FeatureRow],
    output_dir: Path,
    model_version: str | None = None,
    mlflow_tracking_uri: str | None = None,
    mlflow_registered_model_name: str | None = None,
    target_variable: str = "price_rub",
) -> TrainingResult:
    if len(feature_rows) < 4:
        raise ValueError("at least 4 feature rows are required for baseline training")

    output_dir.mkdir(parents=True, exist_ok=True)
    feature_version = _single_feature_version(feature_rows)
    if model_version is None:
        model_version = _default_model_version(feature_version)
    feature_names = sorted(feature_rows[0].features)
    train_rows, test_rows, split = _split_feature_rows(feature_rows)
    x_train = [[row.features[name] for name in feature_names] for row in train_rows]
    x_test = [[row.features[name] for name in feature_names] for row in test_rows]

    if target_variable == "price_per_m2":
        y_train = [row.target_price_rub / row.features["total_area_m2"] for row in train_rows]
        y_test = [row.target_price_rub / row.features["total_area_m2"] for row in test_rows]
    else:
        y_train = [row.target_price_rub for row in train_rows]
        y_test = [row.target_price_rub for row in test_rows]

    model = Pipeline(
        [
            ("scaler", StandardScaler()),
            ("regressor", Ridge(alpha=1.0)),
        ]
    )
    model.fit(x_train, y_train)

    predictions = model.predict(x_test)
    naive_prediction = _median([row.target_price_rub for row in train_rows])
    naive_predictions = [naive_prediction for _ in y_test]

    if target_variable == "price_per_m2":
        areas_test = [row.features["total_area_m2"] for row in test_rows]
        pred_price = [float(val) * area for val, area in zip(predictions, areas_test, strict=True)]
        actual_price = [row.target_price_rub for row in test_rows]
        metrics = _metrics(
            y_true=actual_price,
            y_pred=pred_price,
            naive_pred=naive_predictions,
            rows_total=len(feature_rows),
            train_rows=len(y_train),
            test_rows=len(y_test),
            feature_count=len(feature_names),
            train_listing_groups=len(split["train_listing_ids"]),
            test_listing_groups=len(split["test_listing_ids"]),
        )
    else:
        metrics = _metrics(
            y_true=y_test,
            y_pred=[float(value) for value in predictions],
            naive_pred=naive_predictions,
            rows_total=len(feature_rows),
            train_rows=len(y_train),
            test_rows=len(y_test),
            feature_count=len(feature_names),
            train_listing_groups=len(split["train_listing_ids"]),
            test_listing_groups=len(split["test_listing_ids"]),
        )

    artifact_path = output_dir / f"{model_version}.joblib"
    artifact = {
        "feature_names": feature_names,
        "feature_version": feature_version,
        "metrics": metrics,
        "model": model,
        "model_version": model_version,
        "split": split,
        "target_variable": target_variable,
    }
    joblib.dump(artifact, artifact_path)
    mlflow_result = _log_mlflow_if_enabled(
        artifact_path=artifact_path,
        feature_version=feature_version,
        metrics=metrics,
        model=model,
        model_version=model_version,
        registered_model_name=mlflow_registered_model_name,
        tracking_uri=mlflow_tracking_uri,
    )
    return TrainingResult(
        artifact_path=artifact_path,
        feature_version=feature_version,
        model_version=model_version,
        metrics=metrics,
        mlflow_run_id=mlflow_result.run_id,
        mlflow_registered_model_name=mlflow_result.registered_model_name,
        mlflow_model_uri=mlflow_result.model_uri,
        split=split,
        target_variable=target_variable,
    )


def train_selected_model(
    *,
    feature_rows: Sequence[FeatureRow],
    output_dir: Path,
    candidate_names: Sequence[str] = ("ridge", "random_forest", "hist_gradient_boosting"),
    model_version: str | None = None,
    mlflow_tracking_uri: str | None = None,
    mlflow_registered_model_name: str | None = None,
    target_variable: str = "price_rub",
) -> TrainingResult:
    if len(feature_rows) < 4:
        raise ValueError("at least 4 feature rows are required for selected model training")
    if not candidate_names:
        raise ValueError("at least one model candidate is required")

    output_dir.mkdir(parents=True, exist_ok=True)
    feature_version = _single_feature_version(feature_rows)
    if model_version is None:
        model_version = _default_selected_model_version(feature_version)
    feature_names = sorted(feature_rows[0].features)
    train_rows, test_rows, split = _split_feature_rows(feature_rows)
    x_train = [[row.features[name] for name in feature_names] for row in train_rows]
    x_test = [[row.features[name] for name in feature_names] for row in test_rows]

    if target_variable == "price_per_m2":
        y_train = [row.target_price_rub / row.features["total_area_m2"] for row in train_rows]
        y_test = [row.target_price_rub / row.features["total_area_m2"] for row in test_rows]
    else:
        y_train = [row.target_price_rub for row in train_rows]
        y_test = [row.target_price_rub for row in test_rows]

    naive_prediction = _median([row.target_price_rub for row in train_rows])
    naive_predictions = [naive_prediction for _ in y_test]

    trained_candidates: list[dict[str, Any]] = []
    for candidate_name in candidate_names:
        model = _candidate_model(candidate_name)
        model.fit(x_train, y_train)
        predictions = model.predict(x_test)
        train_predictions = model.predict(x_train)

        if target_variable == "price_per_m2":
            areas_test = [row.features["total_area_m2"] for row in test_rows]
            pred_price = [
                float(val) * area for val, area in zip(predictions, areas_test, strict=True)
            ]
            actual_price = [row.target_price_rub for row in test_rows]
            metrics = _metrics(
                y_true=actual_price,
                y_pred=pred_price,
                naive_pred=naive_predictions,
                rows_total=len(feature_rows),
                train_rows=len(y_train),
                test_rows=len(y_test),
                feature_count=len(feature_names),
                train_listing_groups=len(split["train_listing_ids"]),
                test_listing_groups=len(split["test_listing_ids"]),
            )
            areas_train = [row.features["total_area_m2"] for row in train_rows]
            train_pred_price = [
                float(val) * area for val, area in zip(train_predictions, areas_train, strict=True)
            ]
            train_eval_metrics = _quality_metrics(
                y_true=[row.target_price_rub for row in train_rows],
                y_pred=train_pred_price,
            )
        else:
            metrics = _metrics(
                y_true=y_test,
                y_pred=[float(value) for value in predictions],
                naive_pred=naive_predictions,
                rows_total=len(feature_rows),
                train_rows=len(y_train),
                test_rows=len(y_test),
                feature_count=len(feature_names),
                train_listing_groups=len(split["train_listing_ids"]),
                test_listing_groups=len(split["test_listing_ids"]),
            )
            train_eval_metrics = _quality_metrics(
                y_true=y_train,
                y_pred=[float(value) for value in train_predictions],
            )
        metrics.update(
            {
                "train_mae": train_eval_metrics["mae"],
                "train_mape": train_eval_metrics["mape"],
                "train_r2": train_eval_metrics["r2"],
                "train_rmse": train_eval_metrics["rmse"],
                "r2_generalization_gap": train_eval_metrics["r2"] - float(metrics["r2"]),
            }
        )

        trained_candidates.append(
            {
                "candidate_name": candidate_name,
                "model": model,
                "metrics": metrics,
            }
        )

    selected = max(trained_candidates, key=_candidate_rank)
    candidate_metrics = [
        {"candidate_name": row["candidate_name"], **row["metrics"]}
        for row in sorted(trained_candidates, key=_candidate_rank, reverse=True)
    ]
    for row in candidate_metrics:
        row["candidate_artifact_path"] = str(
            _candidate_artifact_path(output_dir, model_version, str(row["candidate_name"]))
        )
    selected_candidate = str(selected["candidate_name"])
    metrics = {
        **selected["metrics"],
        "candidate_count": len(candidate_metrics),
    }
    feature_importance = _model_feature_importance(
        selected["model"],
        feature_names=feature_names,
        x_test=x_test,
        y_test=y_test,
    )
    artifact_path = output_dir / f"{model_version}.joblib"
    artifact = {
        "candidate_metrics": candidate_metrics,
        "feature_importance": feature_importance,
        "feature_names": feature_names,
        "feature_version": feature_version,
        "metrics": metrics,
        "model": selected["model"],
        "model_version": model_version,
        "selected_candidate": selected_candidate,
        "split": split,
        "target_variable": target_variable,
    }
    for candidate in trained_candidates:
        candidate_name = str(candidate["candidate_name"])
        candidate_artifact_path = _candidate_artifact_path(
            output_dir,
            model_version,
            candidate_name,
        )
        candidate_feature_importance = _model_feature_importance(
            candidate["model"],
            feature_names=feature_names,
            x_test=x_test,
            y_test=y_test,
        )
        candidate_artifact = {
            "candidate_metrics": candidate_metrics,
            "feature_importance": candidate_feature_importance,
            "feature_names": feature_names,
            "feature_version": feature_version,
            "metrics": {
                **candidate["metrics"],
                "candidate_count": len(candidate_metrics),
            },
            "model": candidate["model"],
            "model_version": model_version,
            "selected_candidate": candidate_name,
            "split": split,
            "target_variable": target_variable,
        }
        joblib.dump(candidate_artifact, candidate_artifact_path)
    joblib.dump(artifact, artifact_path)
    mlflow_result = _log_mlflow_if_enabled(
        artifact_path=artifact_path,
        feature_version=feature_version,
        metrics={key: value for key, value in metrics.items() if isinstance(value, int | float)},
        model=selected["model"],
        model_version=model_version,
        registered_model_name=mlflow_registered_model_name,
        tracking_uri=mlflow_tracking_uri,
    )
    return TrainingResult(
        artifact_path=artifact_path,
        feature_version=feature_version,
        model_version=model_version,
        metrics=metrics,
        mlflow_run_id=mlflow_result.run_id,
        mlflow_registered_model_name=mlflow_result.registered_model_name,
        mlflow_model_uri=mlflow_result.model_uri,
        split=split,
        candidate_metrics=candidate_metrics,
        feature_importance=feature_importance,
        target_variable=target_variable,
    )


def train_from_database(
    *,
    database_url: str | None = None,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    limit: int | None = None,
    feature_version: str = NON_LEAKY_FEATURE_VERSION,
    model_version: str | None = None,
    trainer: str = "selected",
    mlflow_tracking_uri: str | None = None,
    mlflow_registered_model_name: str | None = None,
    target_variable: str = "price_per_m2",
) -> TrainingResult:
    engine = create_database_engine(database_url)
    from sqlalchemy.orm import Session

    with Session(engine) as session:
        feature_rows = build_feature_rows(
            session,
            limit=limit,
            feature_version=feature_version,
        )
    if trainer == "selected":
        return train_selected_model(
            feature_rows=feature_rows,
            output_dir=output_dir,
            model_version=model_version,
            mlflow_tracking_uri=mlflow_tracking_uri,
            mlflow_registered_model_name=mlflow_registered_model_name,
            target_variable=target_variable,
        )
    if trainer == "baseline":
        return train_baseline_model(
            feature_rows=feature_rows,
            output_dir=output_dir,
            model_version=model_version,
            mlflow_tracking_uri=mlflow_tracking_uri,
            mlflow_registered_model_name=mlflow_registered_model_name,
            target_variable=target_variable,
        )
    raise ValueError(f"unsupported trainer: {trainer}")


def _candidate_model(candidate_name: str) -> Any:
    if candidate_name == "ridge":
        return Pipeline(
            [
                ("scaler", StandardScaler()),
                ("regressor", Ridge(alpha=1.0)),
            ]
        )
    if candidate_name == "random_forest":
        return RandomForestRegressor(
            max_depth=8,
            min_samples_leaf=2,
            n_estimators=80,
            random_state=RANDOM_STATE,
        )
    if candidate_name == "hist_gradient_boosting":
        return HistGradientBoostingRegressor(
            l2_regularization=0.10,
            learning_rate=0.06,
            max_iter=240,
            max_leaf_nodes=31,
            min_samples_leaf=20,
            random_state=RANDOM_STATE,
        )
    raise ValueError(f"unsupported model candidate: {candidate_name}")


def _candidate_artifact_path(output_dir: Path, model_version: str, candidate_name: str) -> Path:
    safe_candidate = candidate_name.replace("/", "_").replace("\\", "_")
    return output_dir / f"{model_version}__{safe_candidate}.joblib"


def _model_feature_importance(
    model: Any,
    *,
    feature_names: Sequence[str],
    x_test: Sequence[Sequence[float]],
    y_test: Sequence[float],
) -> list[dict[str, Any]]:
    regressor = _regressor_step(model)
    coefficients = getattr(regressor, "coef_", None)
    if coefficients is not None:
        return _sorted_feature_importance(
            feature_names,
            [float(value) for value in coefficients],
            source="coefficient",
            coefficient_values=[float(value) for value in coefficients],
        )

    tree_importance = getattr(regressor, "feature_importances_", None)
    if tree_importance is not None:
        return _sorted_feature_importance(
            feature_names,
            [float(value) for value in tree_importance],
            source="model_feature_importance",
        )

    if not x_test or not y_test:
        return []
    result = permutation_importance(
        model,
        x_test,
        y_test,
        n_repeats=5,
        random_state=RANDOM_STATE,
        scoring="neg_mean_absolute_error",
    )
    return _sorted_feature_importance(
        feature_names,
        [float(value) for value in result.importances_mean],
        source="permutation_importance",
    )


def _regressor_step(model: Any) -> Any:
    named_steps = getattr(model, "named_steps", {})
    if isinstance(named_steps, dict) and "regressor" in named_steps:
        return named_steps["regressor"]
    return model


def _sorted_feature_importance(
    feature_names: Sequence[str],
    importance_values: Sequence[float],
    *,
    source: str,
    coefficient_values: Sequence[float] | None = None,
) -> list[dict[str, Any]]:
    rows = [
        {
            "feature": feature_name,
            "importance": abs(float(importance)),
            "coefficient": float(coefficient_values[index])
            if coefficient_values is not None
            else 0.0,
            "source": source,
        }
        for index, (feature_name, importance) in enumerate(
            zip(feature_names, importance_values, strict=True)
        )
    ]
    return sorted(rows, key=lambda item: item["importance"], reverse=True)


def _candidate_rank(candidate: dict[str, Any]) -> tuple[float, float]:
    metrics = candidate["metrics"]
    return (float(metrics["r2"]), -float(metrics["mae"]))


def main(argv: Sequence[str] | None = None) -> int:
    with suppress(AttributeError):
        sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description="Train RealtyScope baseline price model.")
    parser.add_argument("--database-url", default=None, help="Override database URL.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--limit", type=int, default=None, help="Optional feature row limit.")
    parser.add_argument(
        "--feature-version",
        choices=FEATURE_VERSIONS,
        default=NON_LEAKY_FEATURE_VERSION,
        help="Feature snapshot version to train on.",
    )
    parser.add_argument(
        "--model-version",
        default=None,
        help="Optional model version override. Defaults from the feature version.",
    )
    parser.add_argument(
        "--trainer",
        choices=("baseline", "selected"),
        default="selected",
        help="Use the historical Ridge baseline or train/select the best candidate model.",
    )
    parser.add_argument(
        "--mlflow-tracking-uri",
        default=os.environ.get("MLFLOW_TRACKING_URI"),
        help="Optional MLflow tracking URI. Logging is skipped if MLflow is unavailable.",
    )
    parser.add_argument(
        "--mlflow-registered-model-name",
        default=os.environ.get("ACTIVE_MODEL_NAME"),
        help="Optional MLflow registered model name for sklearn model registration.",
    )
    parser.add_argument(
        "--target-variable",
        choices=("price_rub", "price_per_m2"),
        default="price_per_m2",
        help="Target variable to train on (price_rub or price_per_m2).",
    )
    parser.add_argument("--json", action="store_true", help="Print JSON output.")
    args = parser.parse_args(argv)

    if args.limit is not None and args.limit < 4:
        parser.error("--limit must be at least 4")

    result = train_from_database(
        database_url=args.database_url,
        output_dir=args.output_dir,
        limit=args.limit,
        feature_version=args.feature_version,
        model_version=args.model_version,
        trainer=args.trainer,
        mlflow_tracking_uri=args.mlflow_tracking_uri,
        mlflow_registered_model_name=args.mlflow_registered_model_name,
        target_variable=args.target_variable,
    )
    payload = _result_payload(result)
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    else:
        print(
            f"Trained {result.model_version}: MAE={result.metrics['mae']:.2f}, "
            f"naive_MAE={result.metrics['naive_mae']:.2f}."
        )
    return 0


def _metrics(
    *,
    y_true: Sequence[int],
    y_pred: Sequence[float],
    naive_pred: Sequence[float],
    rows_total: int,
    train_rows: int,
    test_rows: int,
    feature_count: int,
    train_listing_groups: int,
    test_listing_groups: int,
) -> dict[str, float | int]:
    mae = mean_absolute_error(y_true, y_pred)
    naive_mae = mean_absolute_error(y_true, naive_pred)
    rmse = math.sqrt(mean_squared_error(y_true, y_pred))
    naive_rmse = math.sqrt(mean_squared_error(y_true, naive_pred))
    return {
        "feature_count": feature_count,
        "mae": float(mae),
        "mape": _mape(y_true, y_pred),
        "naive_mae": float(naive_mae),
        "naive_rmse": float(naive_rmse),
        "r2": float(r2_score(y_true, y_pred)) if len(y_true) > 1 else 0.0,
        "rmse": float(rmse),
        "rows_total": rows_total,
        "test_listing_groups": test_listing_groups,
        "test_rows": test_rows,
        "train_listing_groups": train_listing_groups,
        "train_rows": train_rows,
    }


def _quality_metrics(
    *,
    y_true: Sequence[int | float],
    y_pred: Sequence[float],
) -> dict[str, float]:
    mae = mean_absolute_error(y_true, y_pred)
    rmse = math.sqrt(mean_squared_error(y_true, y_pred))
    return {
        "mae": float(mae),
        "mape": _mape(y_true, y_pred),
        "r2": float(r2_score(y_true, y_pred)) if len(y_true) > 1 else 0.0,
        "rmse": float(rmse),
    }


def _mape(y_true: Sequence[int | float], y_pred: Sequence[float]) -> float:
    values = [
        abs(actual - predicted) / actual
        for actual, predicted in zip(y_true, y_pred, strict=True)
        if actual
    ]
    if not values:
        return 0.0
    return float(sum(values) / len(values))


def _median(values: Sequence[int]) -> float:
    ordered = sorted(values)
    midpoint = len(ordered) // 2
    if len(ordered) % 2:
        return float(ordered[midpoint])
    return (ordered[midpoint - 1] + ordered[midpoint]) / 2


def _test_size(row_count: int) -> float:
    if row_count < 10:
        return 0.25
    return 0.2


def _single_feature_version(feature_rows: Sequence[FeatureRow]) -> str:
    versions = {row.feature_version for row in feature_rows}
    if len(versions) != 1:
        ordered = ", ".join(sorted(versions))
        raise ValueError(f"feature rows must use exactly one feature version; got {ordered}")
    return next(iter(versions))


def _default_model_version(feature_version: str) -> str:
    if feature_version == NON_LEAKY_FEATURE_VERSION:
        return NON_LEAKY_MODEL_VERSION
    return MODEL_VERSION


def _default_selected_model_version(feature_version: str) -> str:
    if feature_version == NON_LEAKY_FEATURE_VERSION:
        return NON_LEAKY_SELECTED_MODEL_VERSION
    return SELECTED_MODEL_VERSION


def _split_feature_rows(
    feature_rows: Sequence[FeatureRow],
) -> tuple[list[FeatureRow], list[FeatureRow], dict[str, Any]]:
    listing_ids = sorted({row.listing_id for row in feature_rows})
    if len(listing_ids) < 4:
        raise ValueError("at least 4 unique listing ids are required for grouped validation")

    train_listing_ids, test_listing_ids = train_test_split(
        listing_ids,
        test_size=_test_size(len(listing_ids)),
        random_state=RANDOM_STATE,
    )
    train_listing_id_set = set(train_listing_ids)
    test_listing_id_set = set(test_listing_ids)
    train_rows = [row for row in feature_rows if row.listing_id in train_listing_id_set]
    test_rows = [row for row in feature_rows if row.listing_id in test_listing_id_set]
    split = {
        "strategy": "listing_id_grouped_random",
        "random_state": RANDOM_STATE,
        "train_listing_ids": sorted(train_listing_id_set),
        "test_listing_ids": sorted(test_listing_id_set),
    }
    return train_rows, test_rows, split


def _log_mlflow_if_enabled(
    *,
    artifact_path: Path,
    feature_version: str,
    metrics: dict[str, float | int],
    model: Any,
    model_version: str,
    registered_model_name: str | None,
    tracking_uri: str | None,
) -> MlflowLoggingResult:
    if not tracking_uri:
        return MlflowLoggingResult()
    try:
        import mlflow
    except ImportError:
        return MlflowLoggingResult()

    mlflow.set_tracking_uri(tracking_uri)
    with mlflow.start_run(run_name=model_version) as run:
        mlflow.log_params(
            {
                "feature_version": feature_version,
                "model_version": model_version,
            }
        )
        mlflow.log_metrics({key: float(value) for key, value in metrics.items()})
        mlflow.log_artifact(str(artifact_path))
        model_uri = None
        if registered_model_name:
            mlflow_sklearn = _mlflow_sklearn_module(mlflow)
            if mlflow_sklearn is not None:
                model_info = mlflow_sklearn.log_model(
                    sk_model=model,
                    artifact_path="model",
                    registered_model_name=registered_model_name,
                )
                model_uri = getattr(model_info, "model_uri", None)
        return MlflowLoggingResult(
            run_id=run.info.run_id,
            registered_model_name=registered_model_name if model_uri else None,
            model_uri=model_uri,
        )


def _mlflow_sklearn_module(mlflow_module: Any) -> Any | None:
    try:
        import mlflow.sklearn as mlflow_sklearn
    except ImportError:
        return getattr(mlflow_module, "sklearn", None)
    return mlflow_sklearn


def _result_payload(result: TrainingResult) -> dict[str, Any]:
    return {
        "artifact_path": str(result.artifact_path),
        "feature_version": result.feature_version,
        "metrics": result.metrics,
        "mlflow_run_id": result.mlflow_run_id,
        "mlflow_registered_model_name": result.mlflow_registered_model_name,
        "mlflow_model_uri": result.mlflow_model_uri,
        "model_version": result.model_version,
        "split": result.split,
        "candidate_metrics": result.candidate_metrics,
        "target_variable": result.target_variable,
    }


if __name__ == "__main__":
    raise SystemExit(main())
