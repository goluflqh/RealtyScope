from __future__ import annotations

import pytest

from realtyscope.ml.model_compare import ModelMetrics, PromotionGates, compare_candidate


def test_compare_candidate_promotes_when_core_metrics_improve() -> None:
    active = ModelMetrics(
        model_version="baseline_ridge_v2_non_leaky",
        metrics={
            "mae": 100.0,
            "rmse": 140.0,
            "mape": 0.20,
            "r2": 0.50,
            "naive_mae": 160.0,
        },
    )
    candidate = ModelMetrics(
        model_version="hist_gradient_boosting_v1",
        metrics={
            "mae": 90.0,
            "rmse": 120.0,
            "mape": 0.18,
            "r2": 0.53,
            "naive_mae": 160.0,
        },
    )

    decision = compare_candidate(active, candidate, gates=PromotionGates())

    assert decision.decision == "promote"
    assert decision.promote is True
    assert decision.active_model_version == "baseline_ridge_v2_non_leaky"
    assert decision.candidate_model_version == "hist_gradient_boosting_v1"
    assert decision.metric_deltas["mae"] == -10.0
    assert decision.metric_deltas["rmse"] == -20.0
    assert decision.metric_deltas["r2"] == pytest.approx(0.03)
    assert any("MAE improved" in reason for reason in decision.reasons)


def test_compare_candidate_rejects_when_mae_is_worse() -> None:
    active = ModelMetrics(
        model_version="baseline_ridge_v2_non_leaky",
        metrics={
            "mae": 100.0,
            "rmse": 140.0,
            "mape": 0.20,
            "r2": 0.50,
            "naive_mae": 160.0,
        },
    )
    candidate = ModelMetrics(
        model_version="hist_gradient_boosting_v1",
        metrics={
            "mae": 105.0,
            "rmse": 130.0,
            "mape": 0.21,
            "r2": 0.55,
            "naive_mae": 160.0,
        },
    )

    decision = compare_candidate(active, candidate, gates=PromotionGates())

    assert decision.decision == "reject"
    assert decision.promote is False
    assert any("MAE did not improve" in reason for reason in decision.reasons)


def test_compare_candidate_rejects_when_required_metrics_are_missing() -> None:
    active = ModelMetrics(
        model_version="baseline_ridge_v2_non_leaky",
        metrics={
            "mae": 100.0,
            "rmse": 140.0,
            "mape": 0.20,
            "r2": 0.50,
            "naive_mae": 160.0,
        },
    )
    candidate = ModelMetrics(
        model_version="hist_gradient_boosting_v1",
        metrics={
            "mae": 90.0,
            "mape": 0.18,
            "r2": 0.53,
            "naive_mae": 160.0,
        },
    )

    decision = compare_candidate(active, candidate, gates=PromotionGates())

    assert decision.decision == "reject"
    assert decision.promote is False
    assert "candidate missing required metric: rmse" in decision.reasons
