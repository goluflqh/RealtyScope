"""add osm features

Revision ID: 20260602_0003
Revises: 20260602_0002
Create Date: 2026-06-02 05:35:00.000000

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260602_0003"
down_revision: str | None = "20260602_0002"
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
        "osm_features",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("listing_id", sa.Integer(), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("feature_version", sa.String(length=80), nullable=False),
        sa.Column("transport_count_500m", sa.Integer(), nullable=False),
        sa.Column("transport_count_1000m", sa.Integer(), nullable=False),
        sa.Column("nearest_transport_m", sa.Float(), nullable=True),
        sa.Column("schools_count_1000m", sa.Integer(), nullable=False),
        sa.Column("parks_count_1000m", sa.Integer(), nullable=False),
        sa.Column("shops_count_1000m", sa.Integer(), nullable=False),
        sa.Column("healthcare_count_1000m", sa.Integer(), nullable=False),
        sa.Column("source_summary", json_type, nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(
            ["listing_id"], ["listings.id"], name="fk_osm_features_listing_id_listings"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_osm_features"),
        sa.UniqueConstraint(
            "listing_id", "feature_version", name="uq_osm_features_listing_version"
        ),
    )
    op.create_index(
        "ix_osm_features_listing_version",
        "osm_features",
        ["listing_id", "feature_version"],
    )


def downgrade() -> None:
    op.drop_table("osm_features")
