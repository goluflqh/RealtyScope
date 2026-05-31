"""initial database foundation

Revision ID: 20260531_0001
Revises:
Create Date: 2026-05-31 00:01:00.000000

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260531_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

json_type = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    ]


def upgrade() -> None:
    op.create_table(
        "sources",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("source_type", sa.String(length=50), nullable=False),
        sa.Column("enabled", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        *_timestamps(),
        sa.PrimaryKeyConstraint("id", name="pk_sources"),
        sa.UniqueConstraint("name", name="uq_sources_name"),
    )

    op.create_table(
        "ingestion_runs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source_id", sa.Integer(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("records_seen", sa.Integer(), nullable=False),
        sa.Column("raw_count", sa.Integer(), nullable=False),
        sa.Column("normalized_count", sa.Integer(), nullable=False),
        sa.Column("rejected_count", sa.Integer(), nullable=False),
        sa.Column("inserted_count", sa.Integer(), nullable=False),
        sa.Column("updated_count", sa.Integer(), nullable=False),
        sa.Column("error_summary", sa.Text(), nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(
            ["source_id"], ["sources.id"], name="fk_ingestion_runs_source_id_sources"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_ingestion_runs"),
    )
    op.create_index("ix_ingestion_runs_source_status", "ingestion_runs", ["source_id", "status"])

    op.create_table(
        "raw_listings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source_id", sa.Integer(), nullable=False),
        sa.Column("ingestion_run_id", sa.Integer(), nullable=True),
        sa.Column("source_listing_id", sa.String(length=200), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("payload_hash", sa.String(length=64), nullable=False),
        sa.Column("raw_payload", json_type, nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(
            ["ingestion_run_id"],
            ["ingestion_runs.id"],
            name="fk_raw_listings_ingestion_run_id_ingestion_runs",
        ),
        sa.ForeignKeyConstraint(
            ["source_id"], ["sources.id"], name="fk_raw_listings_source_id_sources"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_raw_listings"),
        sa.UniqueConstraint(
            "source_id", "payload_hash", name="uq_raw_listings_source_payload_hash"
        ),
    )
    op.create_index(
        "ix_raw_listings_source_listing_observed",
        "raw_listings",
        ["source_id", "source_listing_id", "observed_at"],
    )

    op.create_table(
        "listings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("city", sa.String(length=100), nullable=False),
        sa.Column("address_text", sa.Text(), nullable=True),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("price_rub", sa.Integer(), nullable=False),
        sa.Column("total_area_m2", sa.Numeric(10, 2), nullable=False),
        sa.Column("rooms", sa.Integer(), nullable=False),
        sa.Column("floor", sa.Integer(), nullable=True),
        sa.Column("floors_total", sa.Integer(), nullable=True),
        sa.Column("building_year", sa.Integer(), nullable=True),
        sa.Column("property_type", sa.String(length=80), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("has_coordinates", sa.Boolean(), nullable=False),
        sa.Column("is_ml_ready", sa.Boolean(), nullable=False),
        sa.Column("cleaning_status", sa.String(length=80), nullable=False),
        sa.Column("cleaning_notes", sa.Text(), nullable=True),
        sa.Column("active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        *_timestamps(),
        sa.PrimaryKeyConstraint("id", name="pk_listings"),
    )
    op.create_index("ix_listings_city_price", "listings", ["city", "price_rub"])
    op.create_index("ix_listings_geo", "listings", ["latitude", "longitude"])
    op.create_index("ix_listings_ml_ready", "listings", ["is_ml_ready"])

    op.create_table(
        "listing_source_links",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("listing_id", sa.Integer(), nullable=False),
        sa.Column("raw_listing_id", sa.Integer(), nullable=False),
        sa.Column("source_id", sa.Integer(), nullable=False),
        sa.Column("source_listing_id", sa.String(length=200), nullable=False),
        sa.Column("match_strategy", sa.String(length=80), nullable=False),
        sa.Column("match_confidence", sa.Float(), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(
            ["listing_id"], ["listings.id"], name="fk_listing_source_links_listing_id_listings"
        ),
        sa.ForeignKeyConstraint(
            ["raw_listing_id"],
            ["raw_listings.id"],
            name="fk_listing_source_links_raw_listing_id_raw_listings",
        ),
        sa.ForeignKeyConstraint(
            ["source_id"], ["sources.id"], name="fk_listing_source_links_source_id_sources"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_listing_source_links"),
        sa.UniqueConstraint("raw_listing_id", name="uq_listing_source_links_raw_listing_id"),
        sa.UniqueConstraint(
            "source_id", "source_listing_id", name="uq_listing_source_links_source_listing"
        ),
    )

    op.create_table(
        "rejected_listings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source_id", sa.Integer(), nullable=True),
        sa.Column("ingestion_run_id", sa.Integer(), nullable=True),
        sa.Column("row_number", sa.Integer(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("raw_payload", json_type, nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(
            ["ingestion_run_id"],
            ["ingestion_runs.id"],
            name="fk_rejected_listings_ingestion_run_id_ingestion_runs",
        ),
        sa.ForeignKeyConstraint(
            ["source_id"], ["sources.id"], name="fk_rejected_listings_source_id_sources"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_rejected_listings"),
    )
    op.create_index(
        "ix_rejected_listings_source_run", "rejected_listings", ["source_id", "ingestion_run_id"]
    )

    op.create_table(
        "app_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("level", sa.String(length=30), nullable=False),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("source_id", sa.Integer(), nullable=True),
        sa.Column("ingestion_run_id", sa.Integer(), nullable=True),
        sa.Column("context", json_type, nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(
            ["ingestion_run_id"],
            ["ingestion_runs.id"],
            name="fk_app_logs_ingestion_run_id_ingestion_runs",
        ),
        sa.ForeignKeyConstraint(
            ["source_id"], ["sources.id"], name="fk_app_logs_source_id_sources"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_app_logs"),
    )
    op.create_index("ix_app_logs_level_created", "app_logs", ["level", "created_at"])


def downgrade() -> None:
    op.drop_table("app_logs")
    op.drop_table("rejected_listings")
    op.drop_table("listing_source_links")
    op.drop_table("listings")
    op.drop_table("raw_listings")
    op.drop_table("ingestion_runs")
    op.drop_table("sources")
