from collections.abc import Iterator
from decimal import Decimal
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Any

import joblib
from fastapi import Depends, FastAPI, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from realtyscope.config import get_settings
from realtyscope.database.models import (
    IngestionRun,
    Listing,
    RawListingRecord,
    RejectedListingRecord,
    Source,
)
from realtyscope.database.session import create_database_engine, create_session_factory
from services.api.app.schemas import PredictionRequest, PredictionResponse

app = FastAPI(
    title="RealtyScope API",
    version="0.1.0",
    description="API skeleton for the RealtyScope grade-5 real estate data service.",
)

BASELINE_PREDICTION_CAVEAT = (
    "Phase 4 baseline contract result; not a final independent appraisal model."
)


class ArtifactPredictionModel:
    def __init__(
        self,
        *,
        feature_names: tuple[str, ...],
        feature_version: str | None,
        metrics: dict[str, float | int],
        model: Any,
        model_version: str,
    ) -> None:
        self.feature_names = feature_names
        self.feature_version = feature_version
        self.metrics = metrics
        self.model = model
        self.model_version = model_version

    @classmethod
    def from_artifact(cls, artifact_path: Path) -> "ArtifactPredictionModel":
        if not artifact_path.exists():
            raise FileNotFoundError(f"Model artifact not found: {artifact_path}")
        artifact = joblib.load(artifact_path)
        return cls(
            feature_names=tuple(artifact["feature_names"]),
            feature_version=artifact.get("feature_version"),
            metrics=artifact.get("metrics", {}),
            model=artifact["model"],
            model_version=artifact["model_version"],
        )

    def predict(self, features: dict[str, float]) -> float:
        row = [[features[name] for name in self.feature_names]]
        return float(self.model.predict(row)[0])


@lru_cache
def get_session_factory() -> sessionmaker[Session]:
    engine = create_database_engine()
    return create_session_factory(engine)


def get_database_session() -> Iterator[Session]:
    with get_session_factory()() as session:
        yield session


@lru_cache
def get_prediction_model() -> ArtifactPredictionModel:
    settings = get_settings()
    try:
        return ArtifactPredictionModel.from_artifact(Path(settings.active_model_artifact_path))
    except (FileNotFoundError, KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=503, detail=f"Prediction model unavailable: {exc}") from exc


@app.get("/health")
def health() -> dict[str, str]:
    settings = get_settings()
    return {
        "service": "realtyscope-api",
        "status": "ok",
        "project": settings.project_name,
        "environment": settings.app_env,
    }


@app.get("/listings")
def list_listings(
    session: Annotated[Session, Depends(get_database_session)],
    limit: Annotated[int, Query(ge=1, le=2000)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict[str, Any]:
    total = session.scalar(select(func.count()).select_from(Listing)) or 0
    listings = session.scalars(
        select(Listing).order_by(Listing.id).limit(limit).offset(offset)
    ).all()
    return {
        "items": [_listing_payload(listing) for listing in listings],
        "limit": limit,
        "offset": offset,
        "total": total,
    }


@app.get("/stats/data-quality")
def data_quality_stats(
    session: Annotated[Session, Depends(get_database_session)],
) -> dict[str, Any]:
    latest_run = session.execute(
        select(IngestionRun, Source.name)
        .join(Source, IngestionRun.source_id == Source.id)
        .order_by(IngestionRun.started_at.desc(), IngestionRun.id.desc())
        .limit(1)
    ).first()
    return {
        "sources_total": _count(session, Source),
        "ingestion_runs_total": _count(session, IngestionRun),
        "raw_listings_total": _count(session, RawListingRecord),
        "listings_total": _count(session, Listing),
        "ml_ready_listings": session.scalar(
            select(func.count()).select_from(Listing).where(Listing.is_ml_ready.is_(True))
        )
        or 0,
        "rejected_listings_total": _count(session, RejectedListingRecord),
        "latest_ingestion_run": _latest_run_payload(latest_run),
    }


@app.post("/predict", response_model=PredictionResponse)
def predict_price(
    request: PredictionRequest,
    prediction_model: Annotated[ArtifactPredictionModel, Depends(get_prediction_model)],
) -> PredictionResponse:
    missing_features, unexpected_features = _feature_contract_diff(
        expected=prediction_model.feature_names,
        actual=request.features,
    )
    if missing_features or unexpected_features:
        raise HTTPException(
            status_code=422,
            detail={
                "missing_features": missing_features,
                "unexpected_features": unexpected_features,
            },
        )

    return PredictionResponse(
        predicted_price_rub=prediction_model.predict(request.features),
        model_version=prediction_model.model_version,
        feature_version=prediction_model.feature_version,
        metrics_summary=prediction_model.metrics,
        input_features_echo=request.features,
        feature_names=list(prediction_model.feature_names),
        caveat=BASELINE_PREDICTION_CAVEAT,
    )


def _count(session: Session, model: type[Any]) -> int:
    return session.scalar(select(func.count()).select_from(model)) or 0


def _feature_contract_diff(
    *,
    expected: tuple[str, ...],
    actual: dict[str, float],
) -> tuple[list[str], list[str]]:
    expected_names = set(expected)
    actual_names = set(actual)
    return sorted(expected_names - actual_names), sorted(actual_names - expected_names)


def _listing_payload(listing: Listing) -> dict[str, Any]:
    return {
        "id": listing.id,
        "city": listing.city,
        "address_text": listing.address_text,
        "latitude": listing.latitude,
        "longitude": listing.longitude,
        "price_rub": listing.price_rub,
        "total_area_m2": _number_payload(listing.total_area_m2),
        "rooms": listing.rooms,
        "floor": listing.floor,
        "floors_total": listing.floors_total,
        "building_year": listing.building_year,
        "property_type": listing.property_type,
        "has_coordinates": listing.has_coordinates,
        "is_ml_ready": listing.is_ml_ready,
        "cleaning_status": listing.cleaning_status,
    }


def _number_payload(value: Any) -> float | int | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return float(value)
    return value


def _latest_run_payload(row: tuple[IngestionRun, str] | None) -> dict[str, Any] | None:
    if row is None:
        return None
    run, source_name = row
    return {
        "id": run.id,
        "source_name": source_name,
        "status": run.status,
        "records_seen": run.records_seen,
        "raw_count": run.raw_count,
        "normalized_count": run.normalized_count,
        "rejected_count": run.rejected_count,
    }
