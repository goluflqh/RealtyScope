from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from realtyscope.ml.model_selection import SelectedModel, load_selected_model, save_selected_model
from realtyscope.ml.promotion_cli import main


def test_dry_run_compare_writes_report_without_changing_selection(tmp_path: Path) -> None:
    selection_path = tmp_path / "selected_model.json"
    candidate_path = tmp_path / "candidate_model.json"
    report_path = tmp_path / "decision.json"
    active = _selected_model(
        tmp_path, "baseline_ridge_v2_non_leaky", mae=100.0, rmse=140.0, r2=0.50
    )
    candidate = _selected_model(
        tmp_path, "hist_gradient_boosting_v1", mae=90.0, rmse=120.0, r2=0.53
    )
    save_selected_model(selection_path, active)
    save_selected_model(candidate_path, candidate)

    exit_code = main(
        [
            "dry-run",
            "--selection-path",
            str(selection_path),
            "--candidate-path",
            str(candidate_path),
            "--decision-report",
            str(report_path),
        ]
    )

    assert exit_code == 0
    assert load_selected_model(selection_path) == active
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["decision"] == "promote"
    assert report["applied"] is False
    assert report["active_model_version"] == "baseline_ridge_v2_non_leaky"
    assert report["candidate_model_version"] == "hist_gradient_boosting_v1"


def test_promote_updates_selection_when_candidate_passes(tmp_path: Path) -> None:
    selection_path = tmp_path / "selected_model.json"
    candidate_path = tmp_path / "candidate_model.json"
    report_path = tmp_path / "decision.json"
    active = _selected_model(
        tmp_path, "baseline_ridge_v2_non_leaky", mae=100.0, rmse=140.0, r2=0.50
    )
    candidate = _selected_model(
        tmp_path, "hist_gradient_boosting_v1", mae=90.0, rmse=120.0, r2=0.53
    )
    save_selected_model(selection_path, active)
    save_selected_model(candidate_path, candidate)

    exit_code = main(
        [
            "promote",
            "--selection-path",
            str(selection_path),
            "--candidate-path",
            str(candidate_path),
            "--decision-report",
            str(report_path),
        ]
    )

    assert exit_code == 0
    selected = load_selected_model(selection_path)
    assert selected is not None
    assert selected.model_version == "hist_gradient_boosting_v1"
    assert selected.previous == active
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["decision"] == "promote"
    assert report["applied"] is True


def test_promote_rejects_worse_candidate_without_changing_selection(tmp_path: Path) -> None:
    selection_path = tmp_path / "selected_model.json"
    candidate_path = tmp_path / "candidate_model.json"
    report_path = tmp_path / "decision.json"
    active = _selected_model(
        tmp_path, "baseline_ridge_v2_non_leaky", mae=100.0, rmse=140.0, r2=0.50
    )
    candidate = _selected_model(
        tmp_path, "hist_gradient_boosting_v1", mae=105.0, rmse=150.0, r2=0.55
    )
    save_selected_model(selection_path, active)
    save_selected_model(candidate_path, candidate)

    exit_code = main(
        [
            "promote",
            "--selection-path",
            str(selection_path),
            "--candidate-path",
            str(candidate_path),
            "--decision-report",
            str(report_path),
        ]
    )

    assert exit_code == 2
    assert load_selected_model(selection_path) == active
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["decision"] == "reject"
    assert report["applied"] is False


def test_rollback_command_restores_previous_selection(tmp_path: Path) -> None:
    selection_path = tmp_path / "selected_model.json"
    candidate_path = tmp_path / "candidate_model.json"
    report_path = tmp_path / "decision.json"
    active = _selected_model(
        tmp_path, "baseline_ridge_v2_non_leaky", mae=100.0, rmse=140.0, r2=0.50
    )
    candidate = _selected_model(
        tmp_path, "hist_gradient_boosting_v1", mae=90.0, rmse=120.0, r2=0.53
    )
    save_selected_model(selection_path, active)
    save_selected_model(candidate_path, candidate)
    assert (
        main(
            [
                "promote",
                "--selection-path",
                str(selection_path),
                "--candidate-path",
                str(candidate_path),
            ]
        )
        == 0
    )

    exit_code = main(
        [
            "rollback",
            "--selection-path",
            str(selection_path),
            "--decision-report",
            str(report_path),
        ]
    )

    assert exit_code == 0
    assert load_selected_model(selection_path) == active
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["decision"] == "rollback"
    assert report["applied"] is True
    assert report["active_model_version"] == "hist_gradient_boosting_v1"
    assert report["restored_model_version"] == "baseline_ridge_v2_non_leaky"


def _selected_model(
    tmp_path: Path,
    model_version: str,
    *,
    mae: float,
    rmse: float,
    r2: float,
) -> SelectedModel:
    return SelectedModel(
        model_version=model_version,
        artifact_path=tmp_path / f"{model_version}.joblib",
        feature_version="ml_features_v2_non_leaky",
        metrics={
            "mae": mae,
            "rmse": rmse,
            "mape": mae / 1_000.0,
            "r2": r2,
            "naive_mae": 160.0,
        },
        selected_at=datetime(2026, 6, 20, 10, 0, tzinfo=UTC),
    )
