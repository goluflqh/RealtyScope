from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class PredictionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    features: dict[str, float] = Field(min_length=1)
    model_candidate: str | None = Field(default=None, min_length=1)


class PredictionResponse(BaseModel):
    predicted_price_rub: float
    model_version: str
    feature_version: str | None
    metrics_summary: dict[str, float | int]
    input_features_echo: dict[str, float]
    feature_names: list[str]
    selected_candidate: str | None = None
    feature_importance: list[dict[str, float | str]] = Field(default_factory=list)
    caveat: str
