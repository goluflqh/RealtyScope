from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from realtyscope.ml.model_compare import ModelMetrics, PromotionGates, compare_candidate
from realtyscope.ml.model_selection import (
    SelectedModel,
    load_selected_model,
    promote_selected_model,
    rollback_selected_model,
)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Compare, promote, or rollback RealtyScope model selection."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    dry_run_parser = subparsers.add_parser("dry-run", help="Compare without applying.")
    _add_compare_args(dry_run_parser)

    promote_parser = subparsers.add_parser("promote", help="Promote when gates pass.")
    _add_compare_args(promote_parser)

    rollback_parser = subparsers.add_parser("rollback", help="Restore previous selection.")
    rollback_parser.add_argument("--selection-path", type=Path, required=True)
    rollback_parser.add_argument("--decision-report", type=Path, default=None)

    args = parser.parse_args(argv)
    if args.command == "dry-run":
        return _compare_command(args, apply=False)
    if args.command == "promote":
        return _compare_command(args, apply=True)
    if args.command == "rollback":
        return _rollback_command(args)
    parser.error(f"unsupported command: {args.command}")
    return 1


def _add_compare_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--selection-path", type=Path, required=True)
    parser.add_argument("--candidate-path", type=Path, required=True)
    parser.add_argument("--decision-report", type=Path, default=None)


def _compare_command(args: argparse.Namespace, *, apply: bool) -> int:
    active = load_selected_model(args.selection_path)
    if active is None:
        raise SystemExit(f"No selected model found at {args.selection_path}")
    candidate = load_selected_model(args.candidate_path)
    if candidate is None:
        raise SystemExit(f"No candidate model found at {args.candidate_path}")

    decision = compare_candidate(
        ModelMetrics(model_version=active.model_version, metrics=active.metrics),
        ModelMetrics(model_version=candidate.model_version, metrics=candidate.metrics),
        gates=PromotionGates(),
    )
    applied = False
    if apply and decision.promote:
        promote_selected_model(args.selection_path, candidate)
        applied = True

    _write_report(
        args.decision_report,
        {
            "active_model_version": decision.active_model_version,
            "applied": applied,
            "candidate_model_version": decision.candidate_model_version,
            "decision": decision.decision,
            "metric_deltas": decision.metric_deltas,
            "reasons": list(decision.reasons),
        },
    )
    if apply and not decision.promote:
        return 2
    return 0


def _rollback_command(args: argparse.Namespace) -> int:
    active = load_selected_model(args.selection_path)
    if active is None:
        raise SystemExit(f"No selected model found at {args.selection_path}")
    restored = rollback_selected_model(args.selection_path)
    _write_report(
        args.decision_report,
        {
            "active_model_version": active.model_version,
            "applied": True,
            "decision": "rollback",
            "restored_model_version": restored.model_version,
        },
    )
    return 0


def _write_report(report_path: Path | None, payload: dict[str, Any]) -> None:
    if report_path is None:
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
        return
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


__all__ = ["SelectedModel", "main"]
