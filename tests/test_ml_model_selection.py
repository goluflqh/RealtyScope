from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from realtyscope.ml.model_selection import (
    SelectedModel,
    load_selected_model,
    promote_selected_model,
    rollback_selected_model,
    save_selected_model,
)


def test_load_selected_model_reads_json_state(tmp_path: Path) -> None:
    selection_path = tmp_path / "selected_model.json"
    active = SelectedModel(
        model_version="baseline_ridge_v2_non_leaky",
        artifact_path=tmp_path / "baseline.joblib",
        feature_version="ml_features_v2_non_leaky",
        metrics={"mae": 100.0, "rmse": 140.0, "r2": 0.5},
        selected_at=datetime(2026, 6, 20, 9, 0, tzinfo=UTC),
    )
    save_selected_model(selection_path, active)

    loaded = load_selected_model(selection_path)

    assert loaded == active


def test_promote_selected_model_writes_previous_without_deleting_old_artifact(
    tmp_path: Path,
) -> None:
    selection_path = tmp_path / "selected_model.json"
    old_artifact = tmp_path / "baseline.joblib"
    old_artifact.write_text("old model", encoding="utf-8")
    active = SelectedModel(
        model_version="baseline_ridge_v2_non_leaky",
        artifact_path=old_artifact,
        feature_version="ml_features_v2_non_leaky",
        metrics={"mae": 100.0, "rmse": 140.0, "r2": 0.5},
        selected_at=datetime(2026, 6, 20, 9, 0, tzinfo=UTC),
    )
    candidate = SelectedModel(
        model_version="hist_gradient_boosting_v1",
        artifact_path=tmp_path / "candidate.joblib",
        feature_version="ml_features_v2_non_leaky",
        metrics={"mae": 90.0, "rmse": 120.0, "r2": 0.53},
        selected_at=datetime(2026, 6, 20, 10, 0, tzinfo=UTC),
    )
    save_selected_model(selection_path, active)

    promoted = promote_selected_model(selection_path, candidate)

    assert promoted.model_version == "hist_gradient_boosting_v1"
    assert promoted.previous == active
    assert old_artifact.exists()
    assert load_selected_model(selection_path) == promoted


def test_rollback_selected_model_restores_previous_selection(tmp_path: Path) -> None:
    selection_path = tmp_path / "selected_model.json"
    active = SelectedModel(
        model_version="baseline_ridge_v2_non_leaky",
        artifact_path=tmp_path / "baseline.joblib",
        feature_version="ml_features_v2_non_leaky",
        metrics={"mae": 100.0, "rmse": 140.0, "r2": 0.5},
        selected_at=datetime(2026, 6, 20, 9, 0, tzinfo=UTC),
    )
    candidate = SelectedModel(
        model_version="hist_gradient_boosting_v1",
        artifact_path=tmp_path / "candidate.joblib",
        feature_version="ml_features_v2_non_leaky",
        metrics={"mae": 90.0, "rmse": 120.0, "r2": 0.53},
        selected_at=datetime(2026, 6, 20, 10, 0, tzinfo=UTC),
    )
    save_selected_model(selection_path, active)
    promote_selected_model(selection_path, candidate)

    restored = rollback_selected_model(selection_path)

    assert restored == active
    assert load_selected_model(selection_path) == active
