from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

REQUIRED_METRICS = ("mae", "rmse", "mape", "r2", "naive_mae")


@dataclass(frozen=True)
class ModelMetrics:
    model_version: str
    metrics: Mapping[str, float | int]

    def metric(self, name: str) -> float:
        return float(self.metrics[name])


@dataclass(frozen=True)
class PromotionGates:
    min_mae_improvement_fraction: float = 0.01
    min_rmse_improvement_fraction: float = 0.01
    max_r2_drop: float = 0.01
    required_metrics: Sequence[str] = REQUIRED_METRICS


@dataclass(frozen=True)
class PromotionDecision:
    decision: str
    active_model_version: str
    candidate_model_version: str
    reasons: tuple[str, ...]
    metric_deltas: dict[str, float] = field(default_factory=dict)

    @property
    def promote(self) -> bool:
        return self.decision == "promote"


def compare_candidate(
    active: ModelMetrics,
    candidate: ModelMetrics,
    *,
    gates: PromotionGates,
) -> PromotionDecision:
    missing_reasons = _missing_metric_reasons(active, candidate, gates.required_metrics)
    if missing_reasons:
        return PromotionDecision(
            decision="reject",
            active_model_version=active.model_version,
            candidate_model_version=candidate.model_version,
            reasons=tuple(missing_reasons),
        )

    metric_deltas = {
        metric_name: candidate.metric(metric_name) - active.metric(metric_name)
        for metric_name in gates.required_metrics
    }
    reasons: list[str] = []
    promote = True

    mae_improvement = _relative_improvement(
        active_value=active.metric("mae"),
        candidate_value=candidate.metric("mae"),
    )
    if mae_improvement >= gates.min_mae_improvement_fraction:
        reasons.append(f"MAE improved by {mae_improvement:.2%}.")
    else:
        promote = False
        reasons.append(
            "MAE did not improve enough: "
            f"required {gates.min_mae_improvement_fraction:.2%}, "
            f"actual {mae_improvement:.2%}."
        )

    rmse_improvement = _relative_improvement(
        active_value=active.metric("rmse"),
        candidate_value=candidate.metric("rmse"),
    )
    if rmse_improvement >= gates.min_rmse_improvement_fraction:
        reasons.append(f"RMSE improved by {rmse_improvement:.2%}.")
    else:
        promote = False
        reasons.append(
            "RMSE did not improve enough: "
            f"required {gates.min_rmse_improvement_fraction:.2%}, "
            f"actual {rmse_improvement:.2%}."
        )

    r2_delta = metric_deltas["r2"]
    if r2_delta >= -gates.max_r2_drop:
        reasons.append(f"R2 delta {r2_delta:.4f} is within tolerance.")
    else:
        promote = False
        reasons.append(
            f"R2 dropped too much: allowed {-gates.max_r2_drop:.4f}, actual {r2_delta:.4f}."
        )

    return PromotionDecision(
        decision="promote" if promote else "reject",
        active_model_version=active.model_version,
        candidate_model_version=candidate.model_version,
        reasons=tuple(reasons),
        metric_deltas=metric_deltas,
    )


def _missing_metric_reasons(
    active: ModelMetrics,
    candidate: ModelMetrics,
    required_metrics: Sequence[str],
) -> list[str]:
    reasons: list[str] = []
    for metric_name in required_metrics:
        if metric_name not in active.metrics:
            reasons.append(f"active missing required metric: {metric_name}")
        if metric_name not in candidate.metrics:
            reasons.append(f"candidate missing required metric: {metric_name}")
    return reasons


def _relative_improvement(*, active_value: float, candidate_value: float) -> float:
    if active_value == 0:
        return 0.0 if candidate_value == 0 else -1.0
    return (active_value - candidate_value) / abs(active_value)
