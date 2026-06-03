import json
from collections.abc import Iterator
from contextlib import asynccontextmanager, suppress
from datetime import UTC, datetime
from decimal import Decimal
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Any

import joblib
from fastapi import Depends, FastAPI, HTTPException, Query, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from realtyscope.config import get_settings
from realtyscope.database.models import (
    AppLog,
    IngestionRun,
    Listing,
    RawListingRecord,
    RejectedListingRecord,
    Source,
)
from realtyscope.database.session import create_database_engine, create_session_factory
from services.api.app.schemas import PredictionRequest, PredictionResponse

BASELINE_PREDICTION_CAVEAT = (
    "Phase 5 non-leaky baseline contract result; not a final independent appraisal model."
)
LISTINGS_CACHE_TTL_SECONDS = 60


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

    @property
    def feature_importance(self) -> list[dict[str, float | str]]:
        named_steps = getattr(self.model, "named_steps", {})
        regressor = named_steps.get("regressor") if isinstance(named_steps, dict) else None
        coefficients = getattr(regressor, "coef_", None)
        if coefficients is None:
            return []
        return sorted(
            [
                {
                    "feature": feature_name,
                    "coefficient": coefficient,
                    "importance": abs(coefficient),
                }
                for feature_name, coefficient in zip(
                    self.feature_names,
                    [float(value) for value in coefficients],
                    strict=True,
                )
            ],
            key=lambda item: item["importance"],
            reverse=True,
        )

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


@asynccontextmanager
async def lifespan(app: FastAPI) -> Iterator[None]:
    app.state.session_factory = create_session_factory(create_database_engine())
    redis_client, redis_error = _create_redis_client()
    app.state.redis_client = redis_client
    app.state.redis_error = redis_error
    settings = get_settings()
    try:
        app.state.prediction_model = ArtifactPredictionModel.from_artifact(
            Path(settings.active_model_artifact_path)
        )
        app.state.prediction_model_error = None
    except (FileNotFoundError, KeyError, TypeError, ValueError) as exc:
        app.state.prediction_model = None
        app.state.prediction_model_error = str(exc)
    try:
        yield
    finally:
        if redis_client is not None:
            with suppress(Exception):
                redis_client.close()


app = FastAPI(
    title="RealtyScope API",
    version="0.1.0",
    description="API skeleton for the RealtyScope grade-5 real estate data service.",
    lifespan=lifespan,
)


@lru_cache
def get_session_factory() -> sessionmaker[Session]:
    engine = create_database_engine()
    return create_session_factory(engine)


def get_database_session(request: Request) -> Iterator[Session]:
    session_factory = getattr(request.app.state, "session_factory", None)
    if session_factory is None:
        session_factory = get_session_factory()
    with session_factory() as session:
        yield session


def get_redis_client(request: Request) -> Any | None:
    return getattr(request.app.state, "redis_client", None)


def _create_redis_client() -> tuple[Any | None, str | None]:
    try:
        from redis import Redis
        from redis.exceptions import RedisError
    except ImportError as exc:
        return None, f"Redis package unavailable: {exc}"

    settings = get_settings()
    try:
        client = Redis.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_connect_timeout=1.0,
            socket_timeout=1.0,
        )
        client.ping()
    except RedisError as exc:
        return None, str(exc)
    return client, None


@lru_cache
def _cached_prediction_model() -> ArtifactPredictionModel:
    settings = get_settings()
    try:
        return ArtifactPredictionModel.from_artifact(Path(settings.active_model_artifact_path))
    except (FileNotFoundError, KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=503, detail=f"Prediction model unavailable: {exc}") from exc


def get_prediction_model(request: Request) -> ArtifactPredictionModel:
    state_model = getattr(request.app.state, "prediction_model", None)
    if state_model is not None:
        return state_model

    state_error = getattr(request.app.state, "prediction_model_error", None)
    if state_error:
        raise HTTPException(status_code=503, detail=f"Prediction model unavailable: {state_error}")

    return _cached_prediction_model()


def get_optional_prediction_model(request: Request) -> ArtifactPredictionModel | None:
    try:
        return get_prediction_model(request)
    except HTTPException:
        return None


@app.get("/health")
def health() -> dict[str, str]:
    settings = get_settings()
    return {
        "service": "realtyscope-api",
        "status": "ok",
        "project": settings.project_name,
        "environment": settings.app_env,
    }


@app.get("/data")
@app.get("/listings")
def list_listings(
    session: Annotated[Session, Depends(get_database_session)],
    redis_client: Annotated[Any | None, Depends(get_redis_client)] = None,
    limit: Annotated[int, Query(ge=1, le=2000)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict[str, Any]:
    cache_key = _listings_cache_key(limit=limit, offset=offset)
    cached_payload = _read_json_cache(redis_client, cache_key)
    if cached_payload is not None:
        return cached_payload

    payload = _listings_payload(session, limit=limit, offset=offset)
    _write_json_cache(
        redis_client,
        cache_key,
        payload,
        ttl_seconds=LISTINGS_CACHE_TTL_SECONDS,
    )
    return payload


def _listings_payload(session: Session, *, limit: int, offset: int) -> dict[str, Any]:
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
    return _data_quality_stats_payload(session)


@app.get("/model/metadata")
def model_metadata(
    prediction_model: Annotated[
        ArtifactPredictionModel | None,
        Depends(get_optional_prediction_model),
    ],
) -> dict[str, Any]:
    return _model_metadata_payload(prediction_model)


@app.get("/monitoring/status")
def monitoring_status(
    session: Annotated[Session, Depends(get_database_session)],
    prediction_model: Annotated[
        ArtifactPredictionModel | None,
        Depends(get_optional_prediction_model),
    ],
) -> dict[str, Any]:
    settings = get_settings()
    return {
        "service": "realtyscope-api",
        "status": "ok",
        "project": settings.project_name,
        "environment": settings.app_env,
        "data_quality": _data_quality_stats_payload(session),
        "model": _model_metadata_payload(prediction_model),
        "recent_errors": _recent_error_payloads(session),
    }


def _data_quality_stats_payload(session: Session) -> dict[str, Any]:
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


def _listings_cache_key(*, limit: int, offset: int) -> str:
    return f"realtyscope:listings:v1:limit={limit}:offset={offset}"


def _read_json_cache(redis_client: Any | None, key: str) -> dict[str, Any] | None:
    if redis_client is None:
        return None

    try:
        cached_value = redis_client.get(key)
    except Exception:
        return None
    if not cached_value:
        return None
    if isinstance(cached_value, bytes):
        cached_value = cached_value.decode("utf-8")

    try:
        payload = json.loads(cached_value)
    except (TypeError, ValueError):
        return None
    return payload if isinstance(payload, dict) else None


def _write_json_cache(
    redis_client: Any | None,
    key: str,
    payload: dict[str, Any],
    *,
    ttl_seconds: int,
) -> None:
    if redis_client is None:
        return

    try:
        redis_client.setex(key, ttl_seconds, json.dumps(payload, sort_keys=True))
    except Exception:
        return


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
        "started_at": _datetime_payload(run.started_at),
        "finished_at": _datetime_payload(run.finished_at),
        "records_seen": run.records_seen,
        "raw_count": run.raw_count,
        "normalized_count": run.normalized_count,
        "rejected_count": run.rejected_count,
        "inserted_count": run.inserted_count,
        "updated_count": run.updated_count,
        "error_summary": run.error_summary,
    }


def _model_metadata_payload(model: ArtifactPredictionModel | None) -> dict[str, Any]:
    settings = get_settings()
    if model is None:
        return {
            "status": "unavailable",
            "active_model_name": settings.active_model_name,
            "artifact_path": settings.active_model_artifact_path,
            "model_version": None,
            "feature_version": None,
            "feature_names": [],
            "feature_count": 0,
            "metrics_summary": {},
            "feature_importance": [],
            "error": "Prediction model unavailable",
        }

    feature_importance = getattr(model, "feature_importance", [])
    return {
        "status": "ready",
        "active_model_name": settings.active_model_name,
        "artifact_path": settings.active_model_artifact_path,
        "model_version": model.model_version,
        "feature_version": model.feature_version,
        "feature_names": list(model.feature_names),
        "feature_count": len(model.feature_names),
        "metrics_summary": model.metrics,
        "feature_importance": [dict(item) for item in feature_importance],
        "error": None,
    }


def _recent_error_payloads(session: Session, *, limit: int = 10) -> list[dict[str, Any]]:
    rows = session.scalars(
        select(AppLog)
        .where(AppLog.level.in_(["ERROR", "WARNING"]))
        .order_by(AppLog.created_at.desc(), AppLog.id.desc())
        .limit(limit)
    ).all()
    return [
        {
            "id": row.id,
            "level": row.level,
            "event_type": row.event_type,
            "message": row.message,
            "created_at": _datetime_payload(row.created_at),
            "source_id": row.source_id,
            "ingestion_run_id": row.ingestion_run_id,
            "context": row.context,
        }
        for row in rows
    ]


def _datetime_payload(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.isoformat()
