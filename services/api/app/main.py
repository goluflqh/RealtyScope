from collections.abc import Iterator
from decimal import Decimal
from functools import lru_cache
from typing import Annotated, Any

from fastapi import Depends, FastAPI, Query
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

app = FastAPI(
    title="RealtyScope API",
    version="0.1.0",
    description="API skeleton for the RealtyScope grade-5 real estate data service.",
)


@lru_cache
def get_session_factory() -> sessionmaker[Session]:
    engine = create_database_engine()
    return create_session_factory(engine)


def get_database_session() -> Iterator[Session]:
    with get_session_factory()() as session:
        yield session


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
    limit: Annotated[int, Query(ge=1, le=500)] = 50,
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


def _count(session: Session, model: type[Any]) -> int:
    return session.scalar(select(func.count()).select_from(model)) or 0


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
