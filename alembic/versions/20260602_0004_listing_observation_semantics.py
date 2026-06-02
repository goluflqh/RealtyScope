"""allow repeated raw payload observation timestamps

Revision ID: 20260602_0004
Revises: 20260602_0003
Create Date: 2026-06-02 18:00:00.000000

"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "20260602_0004"
down_revision: str | None = "20260602_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("listing_observations") as batch_op:
        batch_op.drop_constraint(
            "uq_listing_observations_raw_listing_id",
            type_="unique",
        )
        batch_op.create_unique_constraint(
            "uq_listing_observations_source_listing_observed",
            ["source_id", "source_listing_id", "observed_at"],
        )


def downgrade() -> None:
    with op.batch_alter_table("listing_observations") as batch_op:
        batch_op.drop_constraint(
            "uq_listing_observations_source_listing_observed",
            type_="unique",
        )
        batch_op.create_unique_constraint(
            "uq_listing_observations_raw_listing_id",
            ["raw_listing_id"],
        )
