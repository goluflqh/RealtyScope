import json
import math
from collections.abc import Iterator, Mapping
from contextlib import asynccontextmanager, suppress
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from functools import lru_cache
from pathlib import Path, PureWindowsPath
from typing import Annotated, Any

import joblib
from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, sessionmaker

from realtyscope.config import get_settings
from realtyscope.database.models import (
    AppLog,
    IngestionRun,
    Listing,
    ListingObservation,
    ListingSourceLink,
    OsmFeature,
    RawListingRecord,
    RejectedListingRecord,
    Source,
)
from realtyscope.database.session import create_database_engine, create_session_factory
from realtyscope.ml.model_selection import SelectedModel, load_selected_model
from services.api.app.schemas import PredictionRequest, PredictionResponse

BASELINE_PREDICTION_CAVEAT = (
    "Phase 5 non-leaky baseline contract result; not a final independent appraisal model."
)
LISTINGS_CACHE_TTL_SECONDS = 60
MIN_OBSERVED_EXPOSURE_TARGET_ROWS = 100
INFERRED_LIFECYCLE_MIN_GAP_DAYS = 3
MIN_TREND_FORECAST_POINTS = 7
TREND_FORECAST_HORIZON_DAYS = 7
TERMINAL_LISTING_STATUSES = {
    "removed",
    "sold",
    "closed",
    "inactive",
    "archived",
    "deleted",
    "unavailable",
    "expired",
    "снято",
    "продано",
    "закрыто",
    "неактивно",
}


@dataclass(frozen=True)
class ModelArtifactSelection:
    path: Path
    mode: str
    reason: str
    candidates: tuple[dict[str, Any], ...]


class ArtifactPredictionModel:
    def __init__(
        self,
        *,
        artifact_path: Path | None = None,
        feature_names: tuple[str, ...],
        feature_version: str | None,
        metrics: dict[str, float | int],
        model: Any,
        model_version: str,
        selection: ModelArtifactSelection | None = None,
        selected_candidate: str | None = None,
        feature_importance: list[dict[str, Any]] | None = None,
        training_candidates: list[dict[str, Any]] | None = None,
        target_variable: str = "price_rub",
    ) -> None:
        self.artifact_path = artifact_path
        self.feature_names = feature_names
        self.feature_version = feature_version
        self.metrics = metrics
        self.model = model
        self.model_version = model_version
        self.selection = selection
        self.selected_candidate = selected_candidate
        self._feature_importance = feature_importance or []
        self.training_candidates = training_candidates or []
        self.target_variable = target_variable

    @property
    def feature_importance(self) -> list[dict[str, float | str]]:
        if self._feature_importance:
            return [
                {
                    "feature": str(row["feature"]),
                    "importance": float(row["importance"]),
                    "coefficient": float(row.get("coefficient") or 0.0),
                    "source": str(row.get("source") or "artifact"),
                }
                for row in self._feature_importance
                if "feature" in row and "importance" in row
            ]
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
    def from_artifact(
        cls,
        artifact_path: Path,
        *,
        selection: ModelArtifactSelection | None = None,
    ) -> "ArtifactPredictionModel":
        if not artifact_path.exists():
            raise FileNotFoundError(f"Model artifact not found: {artifact_path}")
        artifact = joblib.load(artifact_path)
        return cls(
            artifact_path=artifact_path,
            feature_names=tuple(artifact["feature_names"]),
            feature_version=artifact.get("feature_version"),
            metrics=artifact.get("metrics", {}),
            model=artifact["model"],
            model_version=artifact["model_version"],
            selection=selection,
            selected_candidate=artifact.get("selected_candidate"),
            feature_importance=artifact.get("feature_importance") or [],
            training_candidates=artifact.get("candidate_metrics") or [],
            target_variable=artifact.get("target_variable", "price_rub"),
        )

    def predict(self, features: dict[str, float]) -> float:
        row = [[features[name] for name in self.feature_names]]
        pred = float(self.model.predict(row)[0])
        if self.target_variable == "price_per_m2":
            area = features.get("total_area_m2")
            if area is None:
                raise ValueError("total_area_m2 is required to scale price_per_m2 predictions")
            return pred * area
        return pred

    def available_candidate_names(self) -> list[str]:
        names = {
            str(row["candidate_name"])
            for row in self.training_candidates
            if row.get("candidate_name") and row.get("candidate_artifact_path")
        }
        for row in self.training_candidates:
            candidate_name = str(row.get("candidate_name") or "")
            if candidate_name and self._selection_artifact_path_for_candidate(candidate_name):
                names.add(candidate_name)
        if self.selected_candidate:
            names.add(self.selected_candidate)
        return sorted(names)

    def candidate_model(self, candidate_name: str) -> "ArtifactPredictionModel":
        requested = candidate_name.strip()
        if not requested:
            raise KeyError(candidate_name)
        if requested == self.selected_candidate:
            return self
        for row in self.training_candidates:
            if row.get("candidate_name") != requested:
                continue
            artifact_path_value = row.get("candidate_artifact_path")
            if not artifact_path_value:
                break
            artifact_path = self._candidate_artifact_path_from_value(artifact_path_value)
            if artifact_path is None:
                break
            model = ArtifactPredictionModel.from_artifact(artifact_path, selection=self.selection)
            if not model.selected_candidate:
                model.selected_candidate = requested
            return model
        selection_artifact_path = self._selection_artifact_path_for_candidate(requested)
        if selection_artifact_path:
            model = ArtifactPredictionModel.from_artifact(
                selection_artifact_path,
                selection=self.selection,
            )
            if not model.selected_candidate:
                model.selected_candidate = requested
            return model
        raise KeyError(candidate_name)

    def _candidate_artifact_path_from_value(self, artifact_path_value: Any) -> Path | None:
        raw_value = str(artifact_path_value)
        artifact_path = Path(raw_value)
        if artifact_path.exists():
            return artifact_path
        if self.artifact_path is None:
            return None
        candidate_names = (artifact_path.name, PureWindowsPath(raw_value).name)
        for candidate_name in candidate_names:
            if not candidate_name:
                continue
            sibling_path = self.artifact_path.parent / candidate_name
            if sibling_path.exists():
                return sibling_path
        return None

    def _selection_artifact_path_for_candidate(self, candidate_name: str) -> Path | None:
        if self.selection is None:
            return None
        requested = candidate_name.strip().lower()
        if not requested:
            return None
        for candidate in self.selection.candidates:
            selected_candidate = str(candidate.get("selected_candidate") or "").strip().lower()
            if selected_candidate != requested:
                continue
            artifact_path = self._candidate_artifact_path_from_value(candidate.get("artifact_path"))
            if artifact_path is not None:
                return artifact_path
        for candidate in self.selection.candidates:
            artifact_path_value = candidate.get("artifact_path")
            if not artifact_path_value:
                continue
            haystack = " ".join(
                str(candidate.get(key) or "") for key in ("artifact_path", "model_version")
            ).lower()
            if requested not in haystack:
                continue
            artifact_path = self._candidate_artifact_path_from_value(artifact_path_value)
            if artifact_path is not None:
                return artifact_path
        return None


@asynccontextmanager
async def lifespan(app: FastAPI) -> Iterator[None]:
    app.state.session_factory = create_session_factory(create_database_engine())
    redis_client, redis_error = _create_redis_client()
    app.state.redis_client = redis_client
    app.state.redis_error = redis_error
    settings = get_settings()
    try:
        app.state.prediction_model = _load_selected_prediction_model(settings)
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
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
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


def _load_selected_prediction_model(settings: Any) -> ArtifactPredictionModel:
    selection = _select_model_artifact(
        explicit_path=Path(settings.active_model_artifact_path),
        search_dir=Path(settings.model_artifact_dir),
        selection_mode=settings.model_selection_mode,
    )
    return ArtifactPredictionModel.from_artifact(selection.path, selection=selection)


def _select_model_artifact(
    *,
    explicit_path: Path,
    search_dir: Path,
    selection_mode: str,
) -> ModelArtifactSelection:
    mode = (selection_mode or "best_metric").strip().lower()
    if mode == "explicit":
        if not explicit_path.exists():
            raise FileNotFoundError(f"Model artifact not found: {explicit_path}")
        candidate = _model_artifact_candidate(explicit_path)
        return ModelArtifactSelection(
            path=explicit_path,
            mode=mode,
            reason="explicit_path",
            candidates=(candidate,),
        )
    if mode != "best_metric":
        raise ValueError(f"Unsupported model selection mode: {selection_mode}")

    candidates = [
        candidate
        for path in _model_artifact_paths(explicit_path=explicit_path, search_dir=search_dir)
        if (candidate := _safe_model_artifact_candidate(path)) is not None
    ]
    if not candidates:
        raise FileNotFoundError(
            f"No valid model artifacts found in {search_dir} or at {explicit_path}"
        )
    candidates.sort(key=_model_artifact_rank, reverse=True)
    return ModelArtifactSelection(
        path=Path(str(candidates[0]["artifact_path"])),
        mode=mode,
        reason="best_validation_metric",
        candidates=tuple(candidates),
    )


def _model_artifact_paths(*, explicit_path: Path, search_dir: Path) -> list[Path]:
    paths: list[Path] = []
    if explicit_path.exists():
        paths.append(explicit_path)
    if search_dir.exists():
        paths.extend(search_dir.rglob("*.joblib"))

    unique_paths: list[Path] = []
    seen: set[str] = set()
    for path in paths:
        key = str(path.resolve())
        if key in seen:
            continue
        seen.add(key)
        unique_paths.append(path)
    return unique_paths


def _safe_model_artifact_candidate(path: Path) -> dict[str, Any] | None:
    try:
        return _model_artifact_candidate(path)
    except Exception:
        return None


def _model_artifact_candidate(path: Path) -> dict[str, Any]:
    artifact = joblib.load(path)
    if not isinstance(artifact, Mapping):
        raise TypeError(f"Model artifact is not a mapping: {path}")
    metrics = artifact.get("metrics") or {}
    if not isinstance(metrics, dict):
        metrics = {}
    return {
        "artifact_path": str(path),
        "model_version": artifact["model_version"],
        "feature_version": artifact.get("feature_version"),
        "selected_candidate": artifact.get("selected_candidate"),
        "r2": _float_metric(metrics.get("r2")),
        "mae": _float_metric(metrics.get("mae")),
        "rows_total": _int_metric(metrics.get("rows_total")),
        "feature_count": len(artifact.get("feature_names") or []),
    }


def _model_artifact_rank(candidate: dict[str, Any]) -> tuple[int, float, int, float, int]:
    r2 = candidate.get("r2")
    mae = candidate.get("mae")
    rows_total = candidate.get("rows_total") or 0
    return (
        1 if isinstance(r2, float) else 0,
        r2 if isinstance(r2, float) else float("-inf"),
        1 if isinstance(mae, float) else 0,
        -mae if isinstance(mae, float) else float("-inf"),
        int(rows_total),
    )


def _float_metric(value: Any) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if result == result else None


def _int_metric(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


@lru_cache
def _cached_prediction_model() -> ArtifactPredictionModel:
    settings = get_settings()
    try:
        return _load_selected_prediction_model(settings)
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
    min_price_rub: Annotated[int | None, Query(ge=0)] = None,
    max_price_rub: Annotated[int | None, Query(ge=0)] = None,
    min_area_m2: Annotated[float | None, Query(ge=0)] = None,
    max_area_m2: Annotated[float | None, Query(ge=0)] = None,
    rooms: Annotated[int | None, Query(ge=0)] = None,
    source_name: Annotated[str | None, Query(min_length=1, max_length=100)] = None,
    search: Annotated[str | None, Query(min_length=1, max_length=200)] = None,
) -> dict[str, Any]:
    filters = _active_listing_filters(
        min_price_rub=min_price_rub,
        max_price_rub=max_price_rub,
        min_area_m2=min_area_m2,
        max_area_m2=max_area_m2,
        rooms=rooms,
        source_name=source_name,
        search=search,
    )
    cache_key = _listings_cache_key(limit=limit, offset=offset, filters=filters)
    cached_payload = _read_json_cache(redis_client, cache_key)
    if cached_payload is not None:
        return cached_payload

    payload = _listings_payload(session, limit=limit, offset=offset, filters=filters)
    _write_json_cache(
        redis_client,
        cache_key,
        payload,
        ttl_seconds=LISTINGS_CACHE_TTL_SECONDS,
    )
    return payload


def _listings_payload(
    session: Session,
    *,
    limit: int,
    offset: int,
    filters: dict[str, Any] | None = None,
) -> dict[str, Any]:
    conditions = _listing_filter_conditions(filters or {})
    count_query = select(func.count()).select_from(Listing)
    listings_query = select(Listing).order_by(Listing.id).limit(limit).offset(offset)
    for condition in conditions:
        count_query = count_query.where(condition)
        listings_query = listings_query.where(condition)

    total = session.scalar(count_query) or 0
    listings = session.scalars(listings_query).all()
    source_metadata = _source_metadata_by_listing_id(
        session,
        listing_ids=[listing.id for listing in listings],
    )
    osm_metadata = _osm_metadata_by_listing_id(
        session,
        listing_ids=[listing.id for listing in listings],
    )
    return {
        "items": [
            _listing_payload(
                listing,
                source_metadata=source_metadata.get(listing.id),
                osm_metadata=osm_metadata.get(listing.id),
            )
            for listing in listings
        ],
        "limit": limit,
        "offset": offset,
        "total": total,
    }


@app.get("/stats/data-quality")
def data_quality_stats(
    session: Annotated[Session, Depends(get_database_session)],
) -> dict[str, Any]:
    return _data_quality_stats_payload(session)


@app.get("/stats/observation-trend")
def observation_trend_stats(
    session: Annotated[Session, Depends(get_database_session)],
    limit: Annotated[int, Query(ge=1, le=365)] = 60,
) -> dict[str, Any]:
    return _observation_trend_stats_payload(session, limit=limit)


@app.get("/stats/exposure-forecast")
def exposure_forecast_stats(
    session: Annotated[Session, Depends(get_database_session)],
) -> dict[str, Any]:
    return _exposure_forecast_stats_payload(session)


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
    request: Request,
    session: Annotated[Session, Depends(get_database_session)],
    prediction_model: Annotated[
        ArtifactPredictionModel | None,
        Depends(get_optional_prediction_model),
    ],
    redis_client: Annotated[Any | None, Depends(get_redis_client)] = None,
) -> dict[str, Any]:
    settings = get_settings()
    data_quality = _data_quality_stats_payload(session)
    model_payload = dict(_model_metadata_payload(prediction_model))
    model_payload["data_freshness"] = _model_data_freshness(
        model_payload=model_payload,
        data_quality=data_quality,
    )
    return {
        "service": "realtyscope-api",
        "status": "ok",
        "project": settings.project_name,
        "environment": settings.app_env,
        "data_quality": data_quality,
        "model": model_payload,
        "services": _service_status_rows(
            data_quality=data_quality,
            model_payload=model_payload,
            redis_client=redis_client,
            redis_error=getattr(request.app.state, "redis_error", None),
        ),
        "recent_errors": _recent_error_payloads(session),
        "recent_logs": _recent_log_payloads(session),
    }


def _service_status_rows(
    *,
    data_quality: dict[str, Any],
    model_payload: dict[str, Any],
    redis_client: Any | None,
    redis_error: str | None,
) -> list[dict[str, Any]]:
    latest_success = data_quality.get("latest_successful_ingestion_run") or {}
    ingestion_ok = isinstance(latest_success, dict) and latest_success.get("status") == "success"
    if redis_client is not None:
        cache_status = {
            "key": "cache",
            "label": "Redis-кэш",
            "status": "ok",
            "status_label": "Доступен",
            "detail": "Redis-клиент подключен к API",
            "icon": "memory",
        }
    else:
        cache_status = {
            "key": "cache",
            "label": "Redis-кэш",
            "status": "warning" if redis_error else "unknown",
            "status_label": "Недоступен" if redis_error else "Не проверено",
            "detail": "Redis не подключен к API" if redis_error else "Статус Redis не передан",
            "icon": "memory",
        }
    return [
        {
            "key": "api",
            "label": "API",
            "status": "ok",
            "status_label": "Доступен",
            "detail": "Ответ /monitoring/status получен",
            "icon": "cloud_done",
        },
        {
            "key": "database",
            "label": "PostgreSQL",
            "status": "ok",
            "status_label": "Проверено",
            "detail": "Запрос статистики данных выполнен",
            "count": data_quality.get("listings_total"),
            "icon": "database",
        },
        cache_status,
        {
            "key": "model",
            "label": "Модель",
            "status": "ok" if model_payload.get("status") == "ready" else "warning",
            "status_label": "Готова" if model_payload.get("status") == "ready" else "Недоступна",
            "detail": model_payload.get("model_version") or "Активная модель не загружена",
            "count": model_payload.get("feature_count"),
            "icon": "model_training",
        },
        {
            "key": "ingestion",
            "label": "Сбор данных",
            "status": "ok" if ingestion_ok else "warning",
            "status_label": "Последний сбор успешен" if ingestion_ok else "Требует проверки",
            "detail": latest_success.get("source_name") or "Последний успешный сбор не найден",
            "count": data_quality.get("ingestion_runs_total"),
            "icon": "schedule",
        },
    ]


def _data_quality_stats_payload(session: Session) -> dict[str, Any]:
    latest_run = session.execute(
        select(IngestionRun, Source.name)
        .join(Source, IngestionRun.source_id == Source.id)
        .order_by(IngestionRun.started_at.desc(), IngestionRun.id.desc())
        .limit(1)
    ).first()
    latest_successful_run = session.execute(
        select(IngestionRun, Source.name)
        .join(Source, IngestionRun.source_id == Source.id)
        .where(IngestionRun.status == "success")
        .order_by(IngestionRun.started_at.desc(), IngestionRun.id.desc())
        .limit(1)
    ).first()
    observation_stats = _observation_lifecycle_stats(session)
    listings_total = _count(session, Listing)
    return {
        "sources_total": _count(session, Source),
        "ingestion_runs_total": _count(session, IngestionRun),
        "raw_listings_total": _count(session, RawListingRecord),
        "listings_total": listings_total,
        "source_counts": _source_counts(session),
        "ml_ready_listings": session.scalar(
            select(func.count()).select_from(Listing).where(Listing.is_ml_ready.is_(True))
        )
        or 0,
        "rejected_listings_total": _count(session, RejectedListingRecord),
        **observation_stats,
        **_osm_feature_stats(session, listings_total=listings_total),
        "latest_ingestion_run": _latest_run_payload(latest_run),
        "latest_successful_ingestion_run": _latest_run_payload(latest_successful_run),
    }


def _source_counts(session: Session) -> dict[str, int]:
    rows = session.execute(
        select(
            Source.name,
            func.count(func.distinct(ListingSourceLink.listing_id)),
        )
        .join(ListingSourceLink, ListingSourceLink.source_id == Source.id)
        .group_by(Source.name)
        .order_by(Source.name)
    ).all()
    return {str(source_name): int(count or 0) for source_name, count in rows}


def _observation_lifecycle_stats(session: Session) -> dict[str, Any]:
    status_rows = session.execute(
        select(
            ListingObservation.status,
            ListingObservation.active,
            func.count(ListingObservation.id),
        ).group_by(ListingObservation.status, ListingObservation.active)
    ).all()
    status_counts: dict[str, int] = {}
    inactive_total = 0
    lifecycle_target_rows = 0
    for status, active, count in status_rows:
        normalized_status = str(status or "unknown").lower()
        row_count = int(count or 0)
        status_counts[normalized_status] = status_counts.get(normalized_status, 0) + row_count
        if active is False:
            inactive_total += row_count
        if active is False or normalized_status in TERMINAL_LISTING_STATUSES:
            lifecycle_target_rows += row_count

    observation_date = func.date(ListingObservation.observed_at)
    per_listing = (
        select(
            ListingObservation.source_id.label("source_id"),
            ListingObservation.source_listing_id.label("source_listing_id"),
            func.count(func.distinct(observation_date)).label("observation_dates"),
            func.count(func.distinct(ListingObservation.price_rub)).label("price_count"),
        )
        .group_by(ListingObservation.source_id, ListingObservation.source_listing_id)
        .subquery()
    )
    per_listing_summary = session.execute(
        select(
            func.count().filter(per_listing.c.observation_dates > 1),
            func.coalesce(func.max(per_listing.c.observation_dates), 0),
            func.count().filter(per_listing.c.price_count > 1),
        )
    ).one()
    date_range = session.execute(
        select(
            func.min(observation_date),
            func.max(observation_date),
        ).select_from(ListingObservation)
    ).one()
    observed_exposure = _observed_exposure_stats(session)
    inferred_lifecycle = _inferred_lifecycle_exposure_stats(session)
    return {
        "observations_total": _count(session, ListingObservation),
        "observation_date_count": session.scalar(
            select(func.count(func.distinct(observation_date))).select_from(ListingObservation)
        )
        or 0,
        "first_observed_date": str(date_range[0]) if date_range[0] is not None else None,
        "last_observed_date": str(date_range[1]) if date_range[1] is not None else None,
        "observation_status_counts": status_counts,
        "inactive_observations_total": inactive_total,
        "listings_with_observation_history": int(per_listing_summary[0] or 0),
        "max_observation_dates_per_listing": int(per_listing_summary[1] or 0),
        "listing_price_change_count": int(per_listing_summary[2] or 0),
        "lifecycle_target_rows": lifecycle_target_rows,
        **observed_exposure,
        **inferred_lifecycle,
    }


def _observed_exposure_stats(session: Session) -> dict[str, Any]:
    observation_rows = session.execute(
        select(
            ListingObservation.source_id,
            ListingObservation.source_listing_id,
            ListingObservation.observed_at,
            ListingObservation.rooms,
        ).where(ListingObservation.observed_at.is_not(None))
    ).all()
    grouped: dict[tuple[int | None, str], dict[str, Any]] = {}
    for source_id, source_listing_id, observed_at, rooms in observation_rows:
        source_listing_key = str(source_listing_id or "").strip()
        if not source_listing_key or observed_at is None:
            continue
        bucket = grouped.setdefault(
            (source_id, source_listing_key),
            {"observed_at": [], "rooms": None},
        )
        bucket["observed_at"].append(observed_at)
        if rooms is not None:
            bucket["rooms"] = int(rooms)

    durations: list[int] = []
    durations_by_rooms: dict[int, list[int]] = {}
    for group in grouped.values():
        observed_values = group["observed_at"]
        observed_dates = sorted({value.date() for value in observed_values})
        if len(observed_dates) <= 1:
            continue
        exposure_days = (observed_dates[-1] - observed_dates[0]).days
        if exposure_days > 0:
            durations.append(exposure_days)
            rooms = group.get("rooms")
            if isinstance(rooms, int):
                durations_by_rooms.setdefault(rooms, []).append(exposure_days)

    durations.sort()
    target_rows = len(durations)
    forecast_segments = [
        {
            "rooms": rooms,
            "target_rows": len(segment_durations),
            "median_observed_exposure_days": _rounded_number_payload(_median(segment_durations)),
            "target_source": "observed_history_lower_bound",
        }
        for rooms, segment_durations in sorted(durations_by_rooms.items())
    ]
    return {
        "observed_exposure_target_rows": target_rows,
        "observed_exposure_can_forecast": target_rows >= MIN_OBSERVED_EXPOSURE_TARGET_ROWS,
        "observed_exposure_median_days": _rounded_number_payload(_median(durations))
        if durations
        else None,
        "observed_exposure_max_days": max(durations) if durations else None,
        "observed_exposure_min_target_rows": MIN_OBSERVED_EXPOSURE_TARGET_ROWS,
        "observed_exposure_target_source": "observed_history_lower_bound",
        "observed_exposure_forecast_segments": forecast_segments,
    }


def _inferred_lifecycle_exposure_stats(session: Session) -> dict[str, Any]:
    observation_rows = session.execute(
        select(
            ListingObservation.source_id,
            ListingObservation.source_listing_id,
            ListingObservation.observed_at,
            ListingObservation.rooms,
        ).where(ListingObservation.observed_at.is_not(None))
    ).all()
    grouped: dict[tuple[int | None, str], dict[str, Any]] = {}
    source_latest_dates: dict[int | None, date] = {}
    for source_id, source_listing_id, observed_at, rooms in observation_rows:
        source_listing_key = str(source_listing_id or "").strip()
        if not source_listing_key or observed_at is None:
            continue
        observed_date = observed_at.date()
        latest_date = source_latest_dates.get(source_id)
        if latest_date is None or observed_date > latest_date:
            source_latest_dates[source_id] = observed_date
        bucket = grouped.setdefault(
            (source_id, source_listing_key),
            {"observed_dates": set(), "rooms": None},
        )
        bucket["observed_dates"].add(observed_date)
        if rooms is not None:
            bucket["rooms"] = int(rooms)

    durations: list[int] = []
    durations_by_rooms: dict[int, list[int]] = {}
    for (source_id, _source_listing_id), group in grouped.items():
        observed_dates = sorted(group["observed_dates"])
        if len(observed_dates) <= 1:
            continue
        latest_source_date = source_latest_dates.get(source_id)
        if latest_source_date is None:
            continue
        first_date = observed_dates[0]
        last_date = observed_dates[-1]
        gap_days = (latest_source_date - last_date).days
        if gap_days < INFERRED_LIFECYCLE_MIN_GAP_DAYS:
            continue
        exposure_days = (last_date - first_date).days
        if exposure_days <= 0:
            continue
        durations.append(exposure_days)
        rooms = group.get("rooms")
        if isinstance(rooms, int):
            durations_by_rooms.setdefault(rooms, []).append(exposure_days)

    durations.sort()
    target_rows = len(durations)
    forecast_segments = [
        {
            "rooms": rooms,
            "target_rows": len(segment_durations),
            "median_inferred_exposure_days": _rounded_number_payload(_median(segment_durations)),
            "target_source": "observation_gap_inferred_lifecycle",
        }
        for rooms, segment_durations in sorted(durations_by_rooms.items())
    ]
    return {
        "inferred_lifecycle_target_rows": target_rows,
        "inferred_lifecycle_can_forecast": target_rows >= MIN_OBSERVED_EXPOSURE_TARGET_ROWS,
        "inferred_lifecycle_min_gap_days": INFERRED_LIFECYCLE_MIN_GAP_DAYS,
        "inferred_lifecycle_median_days": _rounded_number_payload(_median(durations))
        if durations
        else None,
        "inferred_lifecycle_max_days": max(durations) if durations else None,
        "inferred_lifecycle_target_source": "observation_gap_inferred_lifecycle",
        "inferred_lifecycle_forecast_segments": forecast_segments,
    }


def _exposure_forecast_stats_payload(session: Session) -> dict[str, Any]:
    observation_stats = _observation_lifecycle_stats(session)
    terminal_target_rows = int(observation_stats.get("lifecycle_target_rows") or 0)
    inferred_target_rows = int(observation_stats.get("inferred_lifecycle_target_rows") or 0)
    observed_target_rows = int(observation_stats.get("observed_exposure_target_rows") or 0)
    min_target_rows = int(
        observation_stats.get("observed_exposure_min_target_rows")
        or MIN_OBSERVED_EXPOSURE_TARGET_ROWS
    )
    if terminal_target_rows >= min_target_rows:
        status = "ready"
        status_label = "готово по lifecycle-цели"
        can_forecast = True
        target_source = "listing_lifecycle"
        caveat = (
            "Целевая переменная строится по подтвержденным terminal lifecycle строкам. "
            "Перед продуктовым прогнозом нужна отдельная проверка утечек и метрик модели."
        )
    elif inferred_target_rows >= min_target_rows:
        status = "ready"
        status_label = "готово по исчезновению из наблюдений"
        can_forecast = True
        target_source = "observation_gap_inferred_lifecycle"
        caveat = (
            "Цель строится по реальным повторным наблюдениям: объявление видели минимум "
            "в две даты и оно не встречалось еще минимум "
            f"{INFERRED_LIFECYCLE_MIN_GAP_DAYS} дн. Это рабочий прогноз исчезновения "
            "из наблюдений, но не подтвержденный факт продажи или снятия."
        )
    elif observed_target_rows >= min_target_rows:
        status = "partial"
        status_label = "есть нижняя граница экспозиции"
        can_forecast = False
        target_source = "observed_history_lower_bound"
        caveat = (
            "Есть достаточно строк наблюдаемой экспозиции от первой до последней даты "
            "наблюдения объявления, но это только нижняя граница срока. Terminal lifecycle "
            "target rows для прогноза продажи или снятия остаются отдельным требованием."
        )
    elif terminal_target_rows > 0 or inferred_target_rows > 0 or observed_target_rows > 0:
        status = "partial"
        status_label = "недостаточно целевых строк"
        can_forecast = False
        target_source = (
            "observation_gap_inferred_lifecycle"
            if inferred_target_rows > 0
            else "observed_history_lower_bound"
            if observed_target_rows > 0
            else "listing_lifecycle"
        )
        caveat = (
            "Есть отдельные строки экспозиции, но их меньше минимального порога. "
            "Текущий расчет можно показывать только как диагностическую готовность; "
            "нижняя граница наблюдаемой экспозиции не заменяет факт продажи или снятия."
        )
    else:
        status = "missing"
        status_label = "нет целевой переменной"
        can_forecast = False
        target_source = "listing_lifecycle"
        caveat = (
            "Нет достаточных lifecycle или наблюдаемых target rows для честного "
            "прогноза срока экспозиции."
        )
    if target_source == "observation_gap_inferred_lifecycle":
        method = "gap_inferred_lifecycle_median_v1"
        forecast_model_version = "inferred_lifecycle_gap_median_v1"
        forecast_segments = observation_stats.get("inferred_lifecycle_forecast_segments") or []
    else:
        method = "segment_median_observed_exposure"
        forecast_model_version = "observed_exposure_segment_median_v1"
        forecast_segments = observation_stats.get("observed_exposure_forecast_segments") or []
    return {
        "status": status,
        "status_label": status_label,
        "can_forecast": can_forecast,
        "target_source": target_source,
        "method": method,
        "forecast_model_version": forecast_model_version,
        "terminal_lifecycle_target_rows": terminal_target_rows,
        "terminal_lifecycle_can_forecast": terminal_target_rows >= min_target_rows,
        "inferred_lifecycle_target_rows": inferred_target_rows,
        "inferred_lifecycle_can_forecast": inferred_target_rows >= min_target_rows,
        "inferred_lifecycle_min_gap_days": observation_stats.get("inferred_lifecycle_min_gap_days"),
        "inferred_lifecycle_median_days": observation_stats.get("inferred_lifecycle_median_days"),
        "inferred_lifecycle_max_days": observation_stats.get("inferred_lifecycle_max_days"),
        "observed_exposure_target_rows": observed_target_rows,
        "observed_exposure_min_target_rows": min_target_rows,
        "observed_exposure_can_forecast": bool(
            observation_stats.get("observed_exposure_can_forecast")
        ),
        "median_observed_exposure_days": observation_stats.get("observed_exposure_median_days"),
        "max_observed_exposure_days": observation_stats.get("observed_exposure_max_days"),
        "forecast_segments": forecast_segments if isinstance(forecast_segments, list) else [],
        "observation_date_count": observation_stats.get("observation_date_count"),
        "first_observed_date": observation_stats.get("first_observed_date"),
        "last_observed_date": observation_stats.get("last_observed_date"),
        "observations_total": observation_stats.get("observations_total"),
        "listings_with_observation_history": observation_stats.get(
            "listings_with_observation_history"
        ),
        "max_observation_dates_per_listing": observation_stats.get(
            "max_observation_dates_per_listing"
        ),
        "caveat": caveat,
    }


def _osm_feature_stats(session: Session, *, listings_total: int) -> dict[str, Any]:
    rows_total = _count(session, OsmFeature)
    featured_listings = (
        session.scalar(
            select(func.count(func.distinct(OsmFeature.listing_id))).select_from(OsmFeature)
        )
        or 0
    )
    feature_version = session.scalar(
        select(OsmFeature.feature_version)
        .group_by(OsmFeature.feature_version)
        .order_by(func.count(OsmFeature.id).desc(), OsmFeature.feature_version)
        .limit(1)
    )
    source_summaries = session.scalars(select(OsmFeature.source_summary)).all()
    attribution = next(
        (
            summary.get("attribution")
            for summary in source_summaries
            if isinstance(summary, dict) and summary.get("attribution")
        ),
        None,
    )
    live_rows = sum(
        1
        for summary in source_summaries
        if isinstance(summary, dict) and summary.get("live_osm_called") is True
    )
    local_extract_rows = sum(
        1 for summary in source_summaries if _is_direct_local_osm_extract_summary(summary)
    )
    coordinate_derived_rows = sum(
        1
        for summary in source_summaries
        if isinstance(summary, dict) and summary.get("derivation") == "coordinate_exact_match"
    )
    coverage_source = _osm_coverage_source(
        rows_total=rows_total,
        live_rows=live_rows,
        local_extract_rows=local_extract_rows,
        coordinate_derived_rows=coordinate_derived_rows,
    )
    coverage_pct = (
        round(int(featured_listings) / listings_total * 100, 2) if listings_total else 0.0
    )
    return {
        "osm_features_total": rows_total,
        "osm_featured_listings": int(featured_listings),
        "osm_coverage_pct": coverage_pct,
        "osm_feature_version": feature_version,
        "osm_attribution": attribution,
        "osm_live_rows": live_rows,
        "osm_local_extract_rows": local_extract_rows,
        "osm_coordinate_derived_rows": coordinate_derived_rows,
        "osm_infrastructure_coverage_source": coverage_source,
    }


def _is_direct_local_osm_extract_summary(summary: Any) -> bool:
    if not isinstance(summary, dict):
        return False
    if summary.get("derivation") == "coordinate_exact_match":
        return False
    return summary.get("source") == "bbbike_geojson_extract"


def _osm_coverage_source(
    *,
    rows_total: int,
    live_rows: int,
    local_extract_rows: int,
    coordinate_derived_rows: int,
) -> str:
    if not rows_total:
        return "missing"
    sources: list[str] = []
    if local_extract_rows:
        sources.append("local_extract")
    if live_rows:
        sources.append("live_overpass")
    if coordinate_derived_rows:
        sources.append("coordinate_exact_match")
    if sources:
        return "+".join(sources)
    return "local_or_cached_osm"


def _observation_trend_stats_payload(session: Session, *, limit: int) -> dict[str, Any]:
    observation_date = func.date(ListingObservation.observed_at)
    recent_dates = session.scalars(
        select(observation_date)
        .select_from(ListingObservation)
        .where(ListingObservation.price_rub > 0, ListingObservation.price_per_m2 > 0)
        .distinct()
        .order_by(observation_date.desc())
        .limit(limit)
    ).all()
    if not recent_dates:
        return {
            "status": "missing",
            "can_forecast": False,
            "metric": "median_price_per_m2",
            "rows": [],
        }

    rows = session.execute(
        select(
            observation_date,
            ListingObservation.source_id,
            ListingObservation.source_listing_id,
            ListingObservation.price_rub,
            ListingObservation.price_per_m2,
        )
        .where(
            observation_date.in_(recent_dates),
            ListingObservation.price_rub > 0,
            ListingObservation.price_per_m2 > 0,
        )
        .order_by(observation_date.asc(), ListingObservation.observed_at.asc())
    ).all()

    buckets: dict[str, dict[str, Any]] = {}
    for observed_date, source_id, source_listing_id, price_rub, price_per_m2 in rows:
        key = str(observed_date)
        bucket = buckets.setdefault(
            key,
            {"price_rub": [], "price_per_m2": [], "listing_keys": set()},
        )
        bucket["price_rub"].append(float(price_rub))
        bucket["price_per_m2"].append(float(price_per_m2))
        bucket["listing_keys"].add((source_id, str(source_listing_id)))

    trend_rows = []
    for observed_date in sorted(buckets):
        bucket = buckets[observed_date]
        trend_rows.append(
            {
                "observed_date": observed_date,
                "observation_count": len(bucket["price_rub"]),
                "listing_count": len(bucket["listing_keys"]),
                "median_price_rub": _rounded_number_payload(_median(bucket["price_rub"])),
                "median_price_per_m2": _rounded_number_payload(_median(bucket["price_per_m2"])),
            }
        )

    forecast = _trend_forecast_payload(trend_rows)
    return {
        "status": "ready" if forecast["can_forecast"] else ("partial" if trend_rows else "missing"),
        "can_forecast": forecast["can_forecast"],
        "metric": "median_price_per_m2",
        "rows": trend_rows,
        **forecast,
    }


def _trend_forecast_payload(trend_rows: list[dict[str, Any]]) -> dict[str, Any]:
    prepared: list[tuple[date, float]] = []
    for row in trend_rows:
        observed_date = row.get("observed_date")
        median_price_per_m2 = row.get("median_price_per_m2")
        if not observed_date or median_price_per_m2 is None:
            continue
        try:
            parsed_date = date.fromisoformat(str(observed_date))
            value = float(median_price_per_m2)
        except (TypeError, ValueError):
            continue
        if value > 0:
            prepared.append((parsed_date, value))

    prepared.sort(key=lambda item: item[0])
    if len(prepared) < MIN_TREND_FORECAST_POINTS:
        return {
            "can_forecast": False,
            "forecast_method": None,
            "forecast_horizon_days": 0,
            "history_points": len(prepared),
            "trend_slope_per_day": None,
            "forecast_rows": [],
            "caveat": "Недостаточно дат наблюдений для проверяемого прогноза тренда.",
        }

    first_date = prepared[0][0]
    x_values = [(observed_date - first_date).days for observed_date, _value in prepared]
    y_values = [value for _observed_date, value in prepared]
    x_mean = sum(x_values) / len(x_values)
    y_mean = sum(y_values) / len(y_values)
    denominator = sum((x_value - x_mean) ** 2 for x_value in x_values)
    if denominator <= 0:
        return {
            "can_forecast": False,
            "forecast_method": None,
            "forecast_horizon_days": 0,
            "history_points": len(prepared),
            "trend_slope_per_day": None,
            "forecast_rows": [],
            "caveat": "Даты наблюдений не дают временной оси для прогноза тренда.",
        }

    slope = (
        sum(
            (x_value - x_mean) * (y_value - y_mean)
            for x_value, y_value in zip(x_values, y_values, strict=True)
        )
        / denominator
    )
    intercept = y_mean - slope * x_mean
    last_date = prepared[-1][0]
    forecast_rows = []
    for offset in range(1, TREND_FORECAST_HORIZON_DAYS + 1):
        forecast_date = last_date + timedelta(days=offset)
        x_value = (forecast_date - first_date).days
        predicted = max(0, intercept + slope * x_value)
        forecast_rows.append(
            {
                "observed_date": forecast_date.isoformat(),
                "forecast_median_price_per_m2": _rounded_number_payload(predicted),
            }
        )

    return {
        "can_forecast": True,
        "forecast_method": "linear_median_price_per_m2_v1",
        "forecast_horizon_days": TREND_FORECAST_HORIZON_DAYS,
        "history_points": len(prepared),
        "trend_slope_per_day": _rounded_number_payload(slope),
        "forecast_rows": forecast_rows,
        "caveat": (
            "Краткосрочный прогноз построен линейной моделью по дневной медиане цены за м². "
            "Это аналитический тренд по наблюдениям, а не гарантия будущей цены."
        ),
    }


def _median(values: list[float]) -> float:
    prepared = sorted(value for value in values if value > 0)
    if not prepared:
        return 0.0
    midpoint = len(prepared) // 2
    if len(prepared) % 2:
        return prepared[midpoint]
    return (prepared[midpoint - 1] + prepared[midpoint]) / 2


def _rounded_number_payload(value: float) -> int | float:
    rounded = round(float(value), 2)
    if rounded.is_integer():
        return int(rounded)
    return rounded


@app.post("/predict", response_model=PredictionResponse)
def predict_price(
    request: PredictionRequest,
    prediction_model: Annotated[ArtifactPredictionModel, Depends(get_prediction_model)],
) -> PredictionResponse:
    requested_candidate = request.model_candidate or request.candidate_model
    active_model = _prediction_model_for_request(
        prediction_model,
        requested_candidate,
    )
    missing_features, unexpected_features = _feature_contract_diff(
        expected=active_model.feature_names,
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

    predicted_price = active_model.predict(request.features)
    if not math.isfinite(predicted_price) or predicted_price <= 0:
        selected_candidate = getattr(active_model, "selected_candidate", None)
        raise HTTPException(
            status_code=422,
            detail={
                "model_candidate": requested_candidate or selected_candidate,
                "reason": "non_positive_prediction",
                "available_candidates": _available_model_candidates(prediction_model),
                "model_version": active_model.model_version,
                "feature_version": active_model.feature_version,
                "metrics_summary": active_model.metrics,
                "feature_names": list(active_model.feature_names),
                "selected_candidate": selected_candidate,
                "feature_importance": [
                    dict(item) for item in getattr(active_model, "feature_importance", [])
                ],
            },
        )

    return PredictionResponse(
        predicted_price_rub=predicted_price,
        model_version=active_model.model_version,
        feature_version=active_model.feature_version,
        metrics_summary=active_model.metrics,
        input_features_echo=request.features,
        feature_names=list(active_model.feature_names),
        target_variable=getattr(active_model, "target_variable", "price_rub"),
        selected_candidate=getattr(active_model, "selected_candidate", None),
        feature_importance=[dict(item) for item in getattr(active_model, "feature_importance", [])],
        caveat=BASELINE_PREDICTION_CAVEAT,
    )


def _prediction_model_for_request(
    prediction_model: ArtifactPredictionModel,
    model_candidate: str | None,
) -> ArtifactPredictionModel:
    if not model_candidate:
        return prediction_model
    try:
        return prediction_model.candidate_model(model_candidate)
    except KeyError as exc:
        raise HTTPException(
            status_code=422,
            detail={
                "model_candidate": model_candidate,
                "available_candidates": _available_model_candidates(prediction_model),
            },
        ) from exc


def _available_model_candidates(prediction_model: ArtifactPredictionModel) -> list[str]:
    available = getattr(prediction_model, "available_candidate_names", None)
    if callable(available):
        return list(available())
    return sorted(
        str(row["candidate_name"])
        for row in getattr(prediction_model, "training_candidates", [])
        if isinstance(row, dict) and row.get("candidate_name")
    )


def _count(session: Session, model: type[Any]) -> int:
    return session.scalar(select(func.count()).select_from(model)) or 0


def _active_listing_filters(
    *,
    min_price_rub: int | None,
    max_price_rub: int | None,
    min_area_m2: float | None,
    max_area_m2: float | None,
    rooms: int | None,
    source_name: str | None,
    search: str | None,
) -> dict[str, Any]:
    filters: dict[str, Any] = {}
    for key, value in {
        "min_price_rub": min_price_rub,
        "max_price_rub": max_price_rub,
        "min_area_m2": min_area_m2,
        "max_area_m2": max_area_m2,
        "rooms": rooms,
    }.items():
        if value is not None:
            filters[key] = value

    for key, value in {"source_name": source_name, "search": search}.items():
        if value is not None and value.strip():
            filters[key] = value.strip()
    return filters


def _listing_filter_conditions(filters: dict[str, Any]) -> list[Any]:
    conditions: list[Any] = []
    if "min_price_rub" in filters:
        conditions.append(Listing.price_rub >= filters["min_price_rub"])
    if "max_price_rub" in filters:
        conditions.append(Listing.price_rub <= filters["max_price_rub"])
    if "min_area_m2" in filters:
        conditions.append(Listing.total_area_m2 >= filters["min_area_m2"])
    if "max_area_m2" in filters:
        conditions.append(Listing.total_area_m2 <= filters["max_area_m2"])
    if "rooms" in filters:
        conditions.append(Listing.rooms == filters["rooms"])
    if source_name := filters.get("source_name"):
        source_ids = select(Source.id).where(Source.name == source_name)
        conditions.append(Listing.links.any(ListingSourceLink.source_id.in_(source_ids)))
    if search := filters.get("search"):
        pattern = f"%{str(search).lower()}%"
        conditions.append(
            or_(
                func.lower(Listing.city).like(pattern),
                func.lower(func.coalesce(Listing.address_text, "")).like(pattern),
            )
        )
    return conditions


def _listings_cache_key(
    *,
    limit: int,
    offset: int,
    filters: dict[str, Any] | None = None,
) -> str:
    key = f"realtyscope:listings:v2:limit={limit}:offset={offset}"
    if not filters:
        return key
    filter_suffix = ":".join(f"{name}={value}" for name, value in sorted(filters.items()))
    return f"{key}:{filter_suffix}"


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


def _source_metadata_by_listing_id(
    session: Session,
    *,
    listing_ids: list[int],
) -> dict[int, dict[str, Any]]:
    if not listing_ids:
        return {}

    latest_observation = (
        select(
            ListingObservation.listing_id.label("listing_id"),
            ListingObservation.source_id.label("source_id"),
            ListingObservation.source_listing_id.label("source_listing_id"),
            func.max(ListingObservation.observed_at).label("observed_at"),
        )
        .where(ListingObservation.listing_id.in_(listing_ids))
        .group_by(
            ListingObservation.listing_id,
            ListingObservation.source_id,
            ListingObservation.source_listing_id,
        )
        .subquery()
    )
    rows = session.execute(
        select(
            ListingSourceLink.listing_id,
            Source.name,
            ListingSourceLink.source_listing_id,
            RawListingRecord.source_url,
            latest_observation.c.observed_at,
            RawListingRecord.observed_at,
        )
        .join(Source, Source.id == ListingSourceLink.source_id)
        .join(RawListingRecord, RawListingRecord.id == ListingSourceLink.raw_listing_id)
        .outerjoin(
            latest_observation,
            (latest_observation.c.listing_id == ListingSourceLink.listing_id)
            & (latest_observation.c.source_id == ListingSourceLink.source_id)
            & (latest_observation.c.source_listing_id == ListingSourceLink.source_listing_id),
        )
        .where(ListingSourceLink.listing_id.in_(listing_ids))
        .order_by(ListingSourceLink.listing_id, Source.name, ListingSourceLink.id)
    ).all()
    metadata: dict[int, dict[str, Any]] = {}
    for (
        listing_id,
        source_name,
        source_listing_id,
        source_url,
        latest_observed_at,
        raw_observed_at,
    ) in rows:
        if listing_id in metadata:
            continue
        metadata[int(listing_id)] = {
            "source_name": source_name,
            "source_label": _source_label(source_name),
            "source_listing_id": source_listing_id,
            "source_url": source_url,
            "observed_at": _datetime_payload(latest_observed_at or raw_observed_at),
        }
    return metadata


def _osm_metadata_by_listing_id(
    session: Session,
    *,
    listing_ids: list[int],
) -> dict[int, dict[str, Any]]:
    if not listing_ids:
        return {}
    rows = session.scalars(
        select(OsmFeature)
        .where(OsmFeature.listing_id.in_(listing_ids))
        .order_by(OsmFeature.listing_id, OsmFeature.updated_at.desc(), OsmFeature.id.desc())
    ).all()
    metadata: dict[int, dict[str, Any]] = {}
    for row in rows:
        if row.listing_id in metadata:
            continue
        source_summary = row.source_summary if isinstance(row.source_summary, dict) else {}
        metadata[int(row.listing_id)] = {
            "osm_feature_version": row.feature_version,
            "osm_attribution": source_summary.get("attribution"),
            "transport_count_500m": row.transport_count_500m,
            "transport_count_1000m": row.transport_count_1000m,
            "nearest_transport_m": _number_payload(row.nearest_transport_m),
            "schools_count_1000m": row.schools_count_1000m,
            "parks_count_1000m": row.parks_count_1000m,
            "shops_count_1000m": row.shops_count_1000m,
            "healthcare_count_1000m": row.healthcare_count_1000m,
        }
    return metadata


def _source_label(source_name: str | None) -> str | None:
    if source_name == "domclick":
        return "Домклик"
    if source_name == "cian":
        return "ЦИАН"
    return source_name


def _listing_payload(
    listing: Listing,
    *,
    source_metadata: dict[str, Any] | None = None,
    osm_metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload = {
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
    if source_metadata:
        payload.update(source_metadata)
    if osm_metadata:
        payload.update(osm_metadata)
    return payload


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
    selected_model = _load_selected_model_payload(settings.active_model_selection_path)
    if model is None:
        return {
            "status": "unavailable",
            "active_model_name": settings.active_model_name,
            "artifact_path": settings.active_model_artifact_path,
            "model_selection_mode": settings.model_selection_mode,
            "model_selection_reason": "unavailable",
            "model_candidates": [],
            "model_artifact_scan_candidates": [],
            "available_candidates": [],
            "selected_candidate": None,
            "training_candidates": [],
            "model_version": None,
            "feature_version": None,
            "feature_names": [],
            "feature_count": 0,
            "target_variable": None,
            "metrics_summary": {},
            "feature_importance": [],
            "selected_model": selected_model,
            "error": "Prediction model unavailable",
        }

    feature_importance = getattr(model, "feature_importance", [])
    selection = getattr(model, "selection", None)
    artifact_path = getattr(model, "artifact_path", None)
    return {
        "status": "ready",
        "active_model_name": settings.active_model_name,
        "artifact_path": str(artifact_path or settings.active_model_artifact_path),
        "model_selection_mode": selection.mode if selection else settings.model_selection_mode,
        "model_selection_reason": selection.reason if selection else "dependency_override",
        "model_candidates": _prediction_model_candidate_rows(model),
        "model_artifact_scan_candidates": list(selection.candidates) if selection else [],
        "available_candidates": _available_model_candidates(model),
        "selected_candidate": getattr(model, "selected_candidate", None),
        "training_candidates": list(getattr(model, "training_candidates", [])),
        "model_version": model.model_version,
        "feature_version": model.feature_version,
        "feature_names": list(model.feature_names),
        "feature_count": len(model.feature_names),
        "target_variable": getattr(model, "target_variable", "price_rub"),
        "metrics_summary": model.metrics,
        "feature_importance": [dict(item) for item in feature_importance],
        "selected_model": selected_model,
        "error": None,
    }


def _prediction_model_candidate_rows(model: ArtifactPredictionModel) -> list[dict[str, Any]]:
    available_candidates = set(_available_model_candidates(model))
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for candidate in getattr(model, "training_candidates", []):
        if not isinstance(candidate, dict):
            continue
        candidate_name = str(candidate.get("candidate_name") or "").strip()
        if not candidate_name or candidate_name in seen:
            continue
        if available_candidates and candidate_name not in available_candidates:
            continue
        row = dict(candidate)
        row["candidate_name"] = candidate_name
        if not row.get("candidate_artifact_path"):
            selected_candidate = str(getattr(model, "selected_candidate", "") or "")
            artifact_path = getattr(model, "artifact_path", None)
            if candidate_name == selected_candidate and artifact_path is not None:
                row["candidate_artifact_path"] = str(artifact_path)
        rows.append(row)
        seen.add(candidate_name)
    if rows:
        return rows
    selected_candidate = str(getattr(model, "selected_candidate", "") or "").strip()
    if selected_candidate:
        row = {"candidate_name": selected_candidate}
        artifact_path = getattr(model, "artifact_path", None)
        if artifact_path is not None:
            row["candidate_artifact_path"] = str(artifact_path)
        return [row]
    return []


def _model_data_freshness(
    *,
    model_payload: dict[str, Any],
    data_quality: dict[str, Any],
) -> dict[str, Any]:
    metrics = model_payload.get("metrics_summary")
    if not isinstance(metrics, Mapping):
        metrics = {}
    model_rows = _int_metric(metrics.get("rows_total"))
    current_rows = _int_metric(data_quality.get("listings_total"))
    if not model_rows or not current_rows:
        return {
            "status": "unknown",
            "status_label": "unknown",
            "model_rows_total": model_rows,
            "current_listings_total": current_rows,
            "row_delta": None,
            "row_delta_pct": None,
            "requires_retrain": False,
            "note": (
                "Model/data freshness cannot be compared because training-row "
                "metadata or current listing count is unavailable."
            ),
        }

    row_delta = current_rows - model_rows
    row_delta_pct = round(row_delta / model_rows * 100, 2)
    if row_delta <= 0:
        return {
            "status": "current",
            "status_label": "current training snapshot",
            "model_rows_total": model_rows,
            "current_listings_total": current_rows,
            "row_delta": row_delta,
            "row_delta_pct": row_delta_pct,
            "requires_retrain": False,
            "note": "Model training rows cover the current listing count.",
        }

    return {
        "status": "validated_snapshot",
        "status_label": "validated training snapshot",
        "model_rows_total": model_rows,
        "current_listings_total": current_rows,
        "row_delta": row_delta,
        "row_delta_pct": row_delta_pct,
        "requires_retrain": False,
        "note": (
            "Model remains the last validated artifact; retrain only after a candidate "
            "passes the promotion gate."
        ),
    }


def _load_selected_model_payload(selection_path: str) -> dict[str, Any] | None:
    try:
        selected_model = load_selected_model(Path(selection_path))
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
        return None
    if selected_model is None:
        return None
    return _selected_model_metadata_payload(selected_model)


def _selected_model_metadata_payload(selected_model: SelectedModel) -> dict[str, Any]:
    return {
        "model_version": selected_model.model_version,
        "artifact_path": str(selected_model.artifact_path),
        "feature_version": selected_model.feature_version,
        "metrics_summary": dict(selected_model.metrics),
        "selected_at": _datetime_payload(selected_model.selected_at),
        "rollback_available": selected_model.previous is not None,
        "previous_model_version": (
            selected_model.previous.model_version if selected_model.previous is not None else None
        ),
        "previous_artifact_path": (
            str(selected_model.previous.artifact_path)
            if selected_model.previous is not None
            else None
        ),
    }


def _recent_error_payloads(session: Session, *, limit: int = 10) -> list[dict[str, Any]]:
    rows = session.scalars(
        select(AppLog)
        .where(AppLog.level.in_(["ERROR", "WARNING"]))
        .order_by(AppLog.created_at.desc(), AppLog.id.desc())
        .limit(limit)
    ).all()
    return [_app_log_payload(row, include_context=True) for row in rows]


def _recent_log_payloads(session: Session, *, limit: int = 40) -> list[dict[str, Any]]:
    rows = session.scalars(
        select(AppLog).order_by(AppLog.created_at.desc(), AppLog.id.desc()).limit(limit)
    ).all()
    return [_app_log_payload(row, include_context=False) for row in rows]


def _app_log_payload(row: AppLog, *, include_context: bool) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "id": row.id,
        "level": row.level,
        "event_type": row.event_type,
        "message": _clean_log_message(row.message),
        "created_at": _datetime_payload(row.created_at),
        "source_id": row.source_id,
        "ingestion_run_id": row.ingestion_run_id,
    }
    if include_context:
        payload["context"] = row.context
    return payload


def _clean_log_message(message: str, *, max_length: int = 240) -> str:
    cleaned = " ".join(str(message).split())
    if len(cleaned) <= max_length:
        return cleaned
    return f"{cleaned[: max_length - 1].rstrip()}…"


def _datetime_payload(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.isoformat()
