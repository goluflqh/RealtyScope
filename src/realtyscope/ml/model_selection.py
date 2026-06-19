from __future__ import annotations

import json
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class SelectedModel:
    model_version: str
    artifact_path: Path
    feature_version: str
    metrics: dict[str, float | int]
    selected_at: datetime
    previous: SelectedModel | None = None


def load_selected_model(selection_path: Path) -> SelectedModel | None:
    if not selection_path.exists():
        return None
    payload = json.loads(selection_path.read_text(encoding="utf-8"))
    return _selected_model_from_payload(payload)


def save_selected_model(selection_path: Path, selected_model: SelectedModel) -> None:
    selection_path.parent.mkdir(parents=True, exist_ok=True)
    selection_path.write_text(
        json.dumps(
            _selected_model_payload(selected_model),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def promote_selected_model(selection_path: Path, candidate: SelectedModel) -> SelectedModel:
    active = load_selected_model(selection_path)
    promoted = replace(candidate, previous=active)
    save_selected_model(selection_path, promoted)
    return promoted


def rollback_selected_model(selection_path: Path) -> SelectedModel:
    active = load_selected_model(selection_path)
    if active is None:
        raise ValueError("cannot rollback because no selected model exists")
    if active.previous is None:
        raise ValueError("cannot rollback because selected model has no previous selection")
    save_selected_model(selection_path, active.previous)
    return active.previous


def _selected_model_payload(selected_model: SelectedModel) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "artifact_path": str(selected_model.artifact_path),
        "feature_version": selected_model.feature_version,
        "metrics": dict(selected_model.metrics),
        "model_version": selected_model.model_version,
        "selected_at": _datetime_payload(selected_model.selected_at),
    }
    if selected_model.previous is not None:
        payload["previous"] = _selected_model_payload(selected_model.previous)
    return payload


def _selected_model_from_payload(payload: dict[str, Any]) -> SelectedModel:
    previous_payload = payload.get("previous")
    previous = (
        _selected_model_from_payload(previous_payload)
        if isinstance(previous_payload, dict)
        else None
    )
    return SelectedModel(
        model_version=str(payload["model_version"]),
        artifact_path=Path(str(payload["artifact_path"])),
        feature_version=str(payload["feature_version"]),
        metrics={str(key): value for key, value in dict(payload["metrics"]).items()},
        selected_at=_datetime_from_payload(str(payload["selected_at"])),
        previous=previous,
    )


def _datetime_payload(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _datetime_from_payload(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))
