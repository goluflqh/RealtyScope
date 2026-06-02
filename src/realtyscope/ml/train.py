from __future__ import annotations

import argparse
import json
import math
import os
import sys
from collections.abc import Sequence
from contextlib import suppress
from pathlib import Path
from typing import Any

import joblib
from pydantic import BaseModel, ConfigDict
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from realtyscope.database.session import create_database_engine
from realtyscope.ml.features import (
    FEATURE_VERSION,
    FEATURE_VERSIONS,
    NON_LEAKY_FEATURE_VERSION,
    FeatureRow,
    build_feature_rows,
)

MODEL_VERSION = "baseline_ridge_v1"
NON_LEAKY_MODEL_VERSION = "baseline_ridge_v2_non_leaky"
DEFAULT_OUTPUT_DIR = Path("data/processed/models/phase4")
RANDOM_STATE = 42


class TrainingResult(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, frozen=True)

    artifact_path: Path
    feature_version: str
    model_version: str
    metrics: dict[str, float | int]
    mlflow_run_id: str | None = None
    split: dict[str, Any]


def train_baseline_model(
    *,
    feature_rows: Sequence[FeatureRow],
    output_dir: Path,
    model_version: str | None = None,
    mlflow_tracking_uri: str | None = None,
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
    naive_prediction = _median(y_train)
    naive_predictions = [naive_prediction for _ in y_test]
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
    }
    joblib.dump(artifact, artifact_path)
    mlflow_run_id = _log_mlflow_if_enabled(
        artifact_path=artifact_path,
        feature_version=feature_version,
        metrics=metrics,
        model_version=model_version,
        tracking_uri=mlflow_tracking_uri,
    )
    return TrainingResult(
        artifact_path=artifact_path,
        feature_version=feature_version,
        model_version=model_version,
        metrics=metrics,
        mlflow_run_id=mlflow_run_id,
        split=split,
    )


def train_from_database(
    *,
    database_url: str | None = None,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    limit: int | None = None,
    feature_version: str = FEATURE_VERSION,
    model_version: str | None = None,
    mlflow_tracking_uri: str | None = None,
) -> TrainingResult:
    engine = create_database_engine(database_url)
    from sqlalchemy.orm import Session

    with Session(engine) as session:
        feature_rows = build_feature_rows(
            session,
            limit=limit,
            feature_version=feature_version,
        )
    return train_baseline_model(
        feature_rows=feature_rows,
        output_dir=output_dir,
        model_version=model_version,
        mlflow_tracking_uri=mlflow_tracking_uri,
    )


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
        default=FEATURE_VERSION,
        help="Feature snapshot version to train on.",
    )
    parser.add_argument(
        "--model-version",
        default=None,
        help="Optional model version override. Defaults from the feature version.",
    )
    parser.add_argument(
        "--mlflow-tracking-uri",
        default=os.environ.get("MLFLOW_TRACKING_URI"),
        help="Optional MLflow tracking URI. Logging is skipped if MLflow is unavailable.",
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
        mlflow_tracking_uri=args.mlflow_tracking_uri,
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


def _mape(y_true: Sequence[int], y_pred: Sequence[float]) -> float:
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
    model_version: str,
    tracking_uri: str | None,
) -> str | None:
    if not tracking_uri:
        return None
    try:
        import mlflow
    except ImportError:
        return None

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
        return run.info.run_id


def _result_payload(result: TrainingResult) -> dict[str, Any]:
    return {
        "artifact_path": str(result.artifact_path),
        "feature_version": result.feature_version,
        "metrics": result.metrics,
        "mlflow_run_id": result.mlflow_run_id,
        "model_version": result.model_version,
        "split": result.split,
    }


if __name__ == "__main__":
    raise SystemExit(main())
