from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.orm import Session

from realtyscope.database.models import (
    IngestionRun,
    Listing,
    ListingObservation,
    ListingSourceLink,
    RawListingRecord,
    RejectedListingRecord,
    Source,
)
from realtyscope.ingestion.contracts import IngestionBatch, NormalizedListing, RawListing


class PersistedIngestionResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    ingestion_run_id: int
    records_seen: int
    raw_inserted: int
    raw_reused: int
    listings_created: int
    listings_updated: int
    observations_inserted: int
    rejected_inserted: int


def persist_ingestion_batch(
    session: Session,
    batch: IngestionBatch,
    *,
    source_name: str,
    source_type: str = "listing",
) -> PersistedIngestionResult:
    source = _get_or_create_source(session, source_name=source_name, source_type=source_type)
    run = IngestionRun(
        source_id=source.id,
        started_at=_batch_started_at(batch),
        finished_at=datetime.now(UTC),
        status="success",
        records_seen=batch.records_seen,
        raw_count=len(batch.raw_listings),
        normalized_count=len(batch.normalized_listings),
        rejected_count=len(batch.rejected_listings),
    )
    session.add(run)
    session.flush()

    raw_by_source_listing_id: dict[str, RawListingRecord] = {}
    raw_inserted = 0
    raw_reused = 0
    for raw_listing in batch.raw_listings:
        raw_record, was_inserted = _get_or_create_raw_listing(
            session, source.id, run.id, raw_listing
        )
        raw_by_source_listing_id[raw_listing.source_listing_id] = raw_record
        if was_inserted:
            raw_inserted += 1
        else:
            raw_reused += 1

    listings_created = 0
    listings_updated = 0
    observations_inserted = 0
    for normalized in batch.normalized_listings:
        raw_record = raw_by_source_listing_id.get(normalized.source_listing_id)
        if raw_record is None:
            continue
        listing, created = _upsert_listing_from_normalized(
            session, source.id, raw_record, normalized
        )
        if created:
            listings_created += 1
        else:
            listings_updated += 1
        if _create_listing_observation(session, listing, source.id, raw_record, normalized):
            observations_inserted += 1

    rejected_inserted = 0
    for rejected in batch.rejected_listings:
        session.add(
            RejectedListingRecord(
                source_id=source.id,
                ingestion_run_id=run.id,
                row_number=rejected.row_number,
                reason=rejected.reason,
                raw_payload=rejected.raw_payload,
            )
        )
        rejected_inserted += 1

    run.inserted_count = raw_inserted + listings_created + observations_inserted + rejected_inserted
    run.updated_count = listings_updated
    session.flush()

    return PersistedIngestionResult(
        ingestion_run_id=run.id,
        records_seen=batch.records_seen,
        raw_inserted=raw_inserted,
        raw_reused=raw_reused,
        listings_created=listings_created,
        listings_updated=listings_updated,
        observations_inserted=observations_inserted,
        rejected_inserted=rejected_inserted,
    )


def _get_or_create_source(session: Session, *, source_name: str, source_type: str) -> Source:
    source = session.scalar(select(Source).where(Source.name == source_name))
    if source is not None:
        return source
    source = Source(name=source_name, source_type=source_type)
    session.add(source)
    session.flush()
    return source


def _get_or_create_raw_listing(
    session: Session,
    source_id: int,
    ingestion_run_id: int,
    raw_listing: RawListing,
) -> tuple[RawListingRecord, bool]:
    existing = session.scalar(
        select(RawListingRecord).where(
            RawListingRecord.source_id == source_id,
            RawListingRecord.payload_hash == raw_listing.payload_hash,
        )
    )
    if existing is not None:
        return existing, False

    record = RawListingRecord(
        source_id=source_id,
        ingestion_run_id=ingestion_run_id,
        source_listing_id=raw_listing.source_listing_id,
        source_url=raw_listing.source_url,
        observed_at=raw_listing.observed_at,
        payload_hash=raw_listing.payload_hash,
        raw_payload=raw_listing.raw_payload,
    )
    session.add(record)
    session.flush()
    return record, True


def _upsert_listing_from_normalized(
    session: Session,
    source_id: int,
    raw_record: RawListingRecord,
    normalized: NormalizedListing,
) -> tuple[Listing, bool]:
    existing_link = session.scalar(
        select(ListingSourceLink).where(
            ListingSourceLink.source_id == source_id,
            ListingSourceLink.source_listing_id == normalized.source_listing_id,
        )
    )
    has_coordinates = normalized.has_coordinates
    is_ml_ready = _is_ml_ready(normalized)
    cleaning_status = "ml_ready" if is_ml_ready else "needs_coordinates"

    if existing_link is not None:
        listing = existing_link.listing
        _copy_normalized_fields(listing, normalized, has_coordinates, is_ml_ready, cleaning_status)
        existing_link.raw_listing_id = raw_record.id
        listing.last_seen_at = normalized.observed_at
        session.flush()
        return listing, False

    listing = Listing(
        city=normalized.city,
        address_text=normalized.address_text,
        latitude=normalized.latitude,
        longitude=normalized.longitude,
        price_rub=normalized.price_rub,
        total_area_m2=normalized.total_area_m2,
        rooms=normalized.rooms,
        floor=normalized.floor,
        floors_total=normalized.floors_total,
        building_year=normalized.building_year,
        property_type=normalized.property_type,
        description=normalized.description,
        has_coordinates=has_coordinates,
        is_ml_ready=is_ml_ready,
        cleaning_status=cleaning_status,
        first_seen_at=normalized.observed_at,
        last_seen_at=normalized.observed_at,
    )
    listing.links.append(
        ListingSourceLink(
            source_id=source_id,
            raw_listing_id=raw_record.id,
            source_listing_id=normalized.source_listing_id,
            match_strategy="exact_source_listing_id",
            match_confidence=1.0,
        )
    )
    session.add(listing)
    session.flush()
    return listing, True


def _create_listing_observation(
    session: Session,
    listing: Listing,
    source_id: int,
    raw_record: RawListingRecord,
    normalized: NormalizedListing,
) -> bool:
    existing_id = session.scalar(
        select(ListingObservation.id).where(ListingObservation.raw_listing_id == raw_record.id)
    )
    if existing_id is not None:
        return False

    session.add(
        ListingObservation(
            listing_id=listing.id,
            source_id=source_id,
            raw_listing_id=raw_record.id,
            source_listing_id=normalized.source_listing_id,
            observed_at=normalized.observed_at,
            price_rub=normalized.price_rub,
            price_per_m2=normalized.price_per_m2,
            total_area_m2=normalized.total_area_m2,
            rooms=normalized.rooms,
            floor=normalized.floor,
            floors_total=normalized.floors_total,
            active=True,
            status="observed",
        )
    )
    session.flush()
    return True


def _copy_normalized_fields(
    listing: Listing,
    normalized: NormalizedListing,
    has_coordinates: bool,
    is_ml_ready: bool,
    cleaning_status: str,
) -> None:
    listing.city = normalized.city
    listing.address_text = normalized.address_text
    listing.latitude = normalized.latitude
    listing.longitude = normalized.longitude
    listing.price_rub = normalized.price_rub
    listing.total_area_m2 = normalized.total_area_m2
    listing.rooms = normalized.rooms
    listing.floor = normalized.floor
    listing.floors_total = normalized.floors_total
    listing.building_year = normalized.building_year
    listing.property_type = normalized.property_type
    listing.description = normalized.description
    listing.has_coordinates = has_coordinates
    listing.is_ml_ready = is_ml_ready
    listing.cleaning_status = cleaning_status


def _is_ml_ready(normalized: NormalizedListing) -> bool:
    return normalized.price_rub > 0 and normalized.total_area_m2 > 0 and normalized.has_coordinates


def _batch_started_at(batch: IngestionBatch) -> datetime:
    observed_values = [item.observed_at for item in batch.raw_listings]
    if observed_values:
        return min(observed_values)
    return datetime.now(UTC)
