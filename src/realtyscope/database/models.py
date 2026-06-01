from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
    true,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from realtyscope.database.base import Base


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Source(TimestampMixin, Base):
    __tablename__ = "sources"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)
    enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=true()
    )

    ingestion_runs: Mapped[list[IngestionRun]] = relationship(back_populates="source")
    raw_listings: Mapped[list[RawListingRecord]] = relationship(back_populates="source")
    observations: Mapped[list[ListingObservation]] = relationship(back_populates="source")


class IngestionRun(TimestampMixin, Base):
    __tablename__ = "ingestion_runs"
    __table_args__ = (Index("ix_ingestion_runs_source_status", "source_id", "status"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id"), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    records_seen: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    raw_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    normalized_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rejected_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    inserted_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    updated_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_summary: Mapped[str | None] = mapped_column(Text)

    source: Mapped[Source] = relationship(back_populates="ingestion_runs")
    raw_listings: Mapped[list[RawListingRecord]] = relationship(back_populates="ingestion_run")
    rejected_listings: Mapped[list[RejectedListingRecord]] = relationship(
        back_populates="ingestion_run"
    )


class RawListingRecord(TimestampMixin, Base):
    __tablename__ = "raw_listings"
    __table_args__ = (
        UniqueConstraint("source_id", "payload_hash", name="uq_raw_listings_source_payload_hash"),
        Index(
            "ix_raw_listings_source_listing_observed",
            "source_id",
            "source_listing_id",
            "observed_at",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id"), nullable=False)
    ingestion_run_id: Mapped[int | None] = mapped_column(ForeignKey("ingestion_runs.id"))
    source_listing_id: Mapped[str] = mapped_column(String(200), nullable=False)
    source_url: Mapped[str | None] = mapped_column(Text)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    payload_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    raw_payload: Mapped[dict[str, Any]] = mapped_column(nullable=False)

    source: Mapped[Source] = relationship(back_populates="raw_listings")
    ingestion_run: Mapped[IngestionRun | None] = relationship(back_populates="raw_listings")
    source_link: Mapped[ListingSourceLink | None] = relationship(
        back_populates="raw_listing", uselist=False
    )
    observation: Mapped[ListingObservation | None] = relationship(
        back_populates="raw_listing", uselist=False
    )


class Listing(TimestampMixin, Base):
    __tablename__ = "listings"
    __table_args__ = (
        Index("ix_listings_city_price", "city", "price_rub"),
        Index("ix_listings_geo", "latitude", "longitude"),
        Index("ix_listings_ml_ready", "is_ml_ready"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    address_text: Mapped[str | None] = mapped_column(Text)
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
    price_rub: Mapped[int] = mapped_column(Integer, nullable=False)
    total_area_m2: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    rooms: Mapped[int] = mapped_column(Integer, nullable=False)
    floor: Mapped[int | None] = mapped_column(Integer)
    floors_total: Mapped[int | None] = mapped_column(Integer)
    building_year: Mapped[int | None] = mapped_column(Integer)
    property_type: Mapped[str] = mapped_column(String(80), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    has_coordinates: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_ml_ready: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    cleaning_status: Mapped[str] = mapped_column(String(80), nullable=False)
    cleaning_notes: Mapped[str | None] = mapped_column(Text)
    active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=true()
    )
    first_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    links: Mapped[list[ListingSourceLink]] = relationship(
        back_populates="listing", cascade="all, delete-orphan"
    )
    observations: Mapped[list[ListingObservation]] = relationship(
        back_populates="listing", cascade="all, delete-orphan"
    )


class ListingSourceLink(TimestampMixin, Base):
    __tablename__ = "listing_source_links"
    __table_args__ = (
        UniqueConstraint("raw_listing_id", name="uq_listing_source_links_raw_listing_id"),
        UniqueConstraint(
            "source_id", "source_listing_id", name="uq_listing_source_links_source_listing"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    listing_id: Mapped[int] = mapped_column(ForeignKey("listings.id"), nullable=False)
    raw_listing_id: Mapped[int] = mapped_column(ForeignKey("raw_listings.id"), nullable=False)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id"), nullable=False)
    source_listing_id: Mapped[str] = mapped_column(String(200), nullable=False)
    match_strategy: Mapped[str] = mapped_column(String(80), nullable=False)
    match_confidence: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)

    listing: Mapped[Listing] = relationship(back_populates="links")
    raw_listing: Mapped[RawListingRecord] = relationship(back_populates="source_link")


class ListingObservation(TimestampMixin, Base):
    __tablename__ = "listing_observations"
    __table_args__ = (
        UniqueConstraint("raw_listing_id", name="uq_listing_observations_raw_listing_id"),
        Index("ix_listing_observations_listing_observed", "listing_id", "observed_at"),
        Index(
            "ix_listing_observations_source_listing_observed",
            "source_id",
            "source_listing_id",
            "observed_at",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    listing_id: Mapped[int] = mapped_column(ForeignKey("listings.id"), nullable=False)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id"), nullable=False)
    raw_listing_id: Mapped[int] = mapped_column(ForeignKey("raw_listings.id"), nullable=False)
    source_listing_id: Mapped[str] = mapped_column(String(200), nullable=False)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    price_rub: Mapped[int] = mapped_column(Integer, nullable=False)
    price_per_m2: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    total_area_m2: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    rooms: Mapped[int] = mapped_column(Integer, nullable=False)
    floor: Mapped[int | None] = mapped_column(Integer)
    floors_total: Mapped[int | None] = mapped_column(Integer)
    active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=true()
    )
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="observed", server_default="observed"
    )

    listing: Mapped[Listing] = relationship(back_populates="observations")
    source: Mapped[Source] = relationship(back_populates="observations")
    raw_listing: Mapped[RawListingRecord] = relationship(back_populates="observation")


class RejectedListingRecord(TimestampMixin, Base):
    __tablename__ = "rejected_listings"
    __table_args__ = (Index("ix_rejected_listings_source_run", "source_id", "ingestion_run_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[int | None] = mapped_column(ForeignKey("sources.id"))
    ingestion_run_id: Mapped[int | None] = mapped_column(ForeignKey("ingestion_runs.id"))
    row_number: Mapped[int | None] = mapped_column(Integer)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    raw_payload: Mapped[dict[str, Any]] = mapped_column(nullable=False)

    ingestion_run: Mapped[IngestionRun | None] = relationship(back_populates="rejected_listings")


class AppLog(TimestampMixin, Base):
    __tablename__ = "app_logs"
    __table_args__ = (Index("ix_app_logs_level_created", "level", "created_at"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    level: Mapped[str] = mapped_column(String(30), nullable=False)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    source_id: Mapped[int | None] = mapped_column(ForeignKey("sources.id"))
    ingestion_run_id: Mapped[int | None] = mapped_column(ForeignKey("ingestion_runs.id"))
    context: Mapped[dict[str, Any] | None] = mapped_column(nullable=True)
