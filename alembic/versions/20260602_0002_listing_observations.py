"""add listing observations

Revision ID: 20260602_0002
Revises: 20260531_0001
Create Date: 2026-06-02 00:02:00.000000

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260602_0002"
down_revision: str | None = "20260531_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


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
        "listing_observations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("listing_id", sa.Integer(), nullable=False),
        sa.Column("source_id", sa.Integer(), nullable=False),
        sa.Column("raw_listing_id", sa.Integer(), nullable=False),
        sa.Column("source_listing_id", sa.String(length=200), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("price_rub", sa.Integer(), nullable=False),
        sa.Column("price_per_m2", sa.Numeric(12, 2), nullable=False),
        sa.Column("total_area_m2", sa.Numeric(10, 2), nullable=False),
        sa.Column("rooms", sa.Integer(), nullable=False),
        sa.Column("floor", sa.Integer(), nullable=True),
        sa.Column("floors_total", sa.Integer(), nullable=True),
        sa.Column("active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("status", sa.String(length=30), server_default="observed", nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(
            ["listing_id"],
            ["listings.id"],
            name="fk_listing_observations_listing_id_listings",
        ),
        sa.ForeignKeyConstraint(
            ["raw_listing_id"],
            ["raw_listings.id"],
            name="fk_listing_observations_raw_listing_id_raw_listings",
        ),
        sa.ForeignKeyConstraint(
            ["source_id"],
            ["sources.id"],
            name="fk_listing_observations_source_id_sources",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_listing_observations"),
        sa.UniqueConstraint(
            "raw_listing_id",
            name="uq_listing_observations_raw_listing_id",
        ),
    )
    op.create_index(
        "ix_listing_observations_listing_observed",
        "listing_observations",
        ["listing_id", "observed_at"],
    )
    op.create_index(
        "ix_listing_observations_source_listing_observed",
        "listing_observations",
        ["source_id", "source_listing_id", "observed_at"],
    )


def downgrade() -> None:
    op.drop_table("listing_observations")
