from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Mapping, Sequence
from contextlib import suppress
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from realtyscope.database.models import Listing, ListingObservation
from realtyscope.database.session import create_database_engine

GRADE_4_MIN_RECORDS = 1000


class DataReadinessSummary(BaseModel):
    model_config = ConfigDict(frozen=True)

    listings_total: int
    with_coordinates: int
    without_coordinates: int
    observations_total: int
    listings_with_multiple_observations: int
    price_changes_detected: int
    ml_ready_listings: int
    coordinate_coverage: float
    ml_ready_coverage: float
    missing_core_fields: dict[str, int]
    readiness_conclusion: str


def summarize_data_readiness(session: Session) -> DataReadinessSummary:
    listings_total = _count_statement(session, select(func.count()).select_from(Listing))
    with_coordinates = _count_statement(
        session,
        select(func.count())
        .select_from(Listing)
        .where(
            Listing.has_coordinates.is_(True),
            Listing.latitude.is_not(None),
            Listing.longitude.is_not(None),
        ),
    )
    without_coordinates = listings_total - with_coordinates
    observations_total = _count_statement(
        session, select(func.count()).select_from(ListingObservation)
    )
    ml_ready = _count_statement(
        session,
        select(func.count()).select_from(Listing).where(Listing.is_ml_ready.is_(True)),
    )

    observation_counts = (
        select(
            ListingObservation.listing_id.label("listing_id"),
            func.count(ListingObservation.id).label("observation_count"),
            func.count(func.distinct(ListingObservation.price_rub)).label("distinct_prices"),
        )
        .group_by(ListingObservation.listing_id)
        .subquery()
    )
    listings_with_multiple_observations = _count_statement(
        session,
        select(func.count())
        .select_from(observation_counts)
        .where(observation_counts.c.observation_count > 1),
    )
    price_changes = _count_statement(
        session,
        select(func.count())
        .select_from(observation_counts)
        .where(observation_counts.c.distinct_prices > 1),
    )
    missing_core_fields = {
        "price": _count_statement(
            session,
            select(func.count())
            .select_from(Listing)
            .where(or_(Listing.price_rub.is_(None), Listing.price_rub <= 0)),
        ),
        "area": _count_statement(
            session,
            select(func.count())
            .select_from(Listing)
            .where(or_(Listing.total_area_m2.is_(None), Listing.total_area_m2 <= 0)),
        ),
        "rooms": _count_statement(
            session,
            select(func.count()).select_from(Listing).where(Listing.rooms.is_(None)),
        ),
        "coordinates": without_coordinates,
    }

    coordinate_coverage = with_coordinates / listings_total if listings_total else 0.0
    ml_ready_coverage = ml_ready / listings_total if listings_total else 0.0
    return DataReadinessSummary(
        listings_total=listings_total,
        with_coordinates=with_coordinates,
        without_coordinates=without_coordinates,
        observations_total=observations_total,
        listings_with_multiple_observations=listings_with_multiple_observations,
        price_changes_detected=price_changes,
        ml_ready_listings=ml_ready,
        coordinate_coverage=coordinate_coverage,
        ml_ready_coverage=ml_ready_coverage,
        missing_core_fields=missing_core_fields,
        readiness_conclusion=_readiness_conclusion(
            listings_total=listings_total,
            ml_ready_listings=ml_ready,
            missing_core_fields=missing_core_fields,
        ),
    )


def build_data_readiness_summary(database_url: str | None = None) -> DataReadinessSummary:
    engine = create_database_engine(database_url)
    with Session(engine) as session:
        return summarize_data_readiness(session)


def render_data_readiness_markdown(summary: DataReadinessSummary) -> str:
    return "\n".join(
        [
            "# RealtyScope Phase 4 Data Readiness",
            "",
            "## Tổng quan",
            f"- Số listing canonical: {summary.listings_total}",
            f"- Số observation history: {summary.observations_total}",
            f"- Số listing có nhiều hơn một observation: "
            f"{summary.listings_with_multiple_observations}",
            f"- Listing có price changes: {summary.price_changes_detected}",
            "",
            "## Tọa độ và ML readiness",
            f"- Số listing có tọa độ: {summary.with_coordinates}",
            f"- Số listing thiếu tọa độ: {summary.without_coordinates}",
            f"- Tỷ lệ có tọa độ: {_percent(summary.coordinate_coverage)}",
            f"- Số listing sẵn sàng cho ML: {summary.ml_ready_listings}",
            f"- Tỷ lệ sẵn sàng cho ML: {_percent(summary.ml_ready_coverage)}",
            "",
            "## Missing core fields",
            _missing_fields_markdown(summary.missing_core_fields),
            "",
            "## Kết luận",
            f"- {summary.readiness_conclusion}",
            "",
        ]
    )


def main(argv: Sequence[str] | None = None) -> int:
    with suppress(AttributeError):
        sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(
        description="Build a RealtyScope Phase 4 data-readiness summary from database rows."
    )
    parser.add_argument("--database-url", default=None, help="Override database URL for this run.")
    parser.add_argument("--output", type=Path, help="Optional markdown output path.")
    parser.add_argument("--json", action="store_true", help="Print JSON summary.")
    args = parser.parse_args(argv)

    summary = build_data_readiness_summary(args.database_url)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(render_data_readiness_markdown(summary), encoding="utf-8")
    if args.json:
        print(json.dumps(summary.model_dump(mode="json"), ensure_ascii=False, sort_keys=True))
    else:
        print(render_data_readiness_markdown(summary))
    return 0


def _count_statement(session: Session, statement: Any) -> int:
    return session.scalar(statement) or 0


def _readiness_conclusion(
    *, listings_total: int, ml_ready_listings: int, missing_core_fields: Mapping[str, int]
) -> str:
    if listings_total < GRADE_4_MIN_RECORDS:
        return "Chưa đủ 1000 listing thật để chốt baseline ML cho tiêu chí course."
    if ml_ready_listings == 0:
        return "Chưa có listing sẵn sàng cho ML; cần sửa core fields trước."
    if missing_core_fields.get("coordinates", 0):
        return "Có thể làm EDA, nhưng OSM/ML cần xử lý phần listing thiếu tọa độ."
    return "Dữ liệu đủ để bắt đầu EDA observation-based và baseline ML đơn giản."


def _missing_fields_markdown(missing_core_fields: Mapping[str, int]) -> str:
    labels = {
        "price": "Thiếu/invalid price",
        "area": "Thiếu/invalid area",
        "rooms": "Thiếu/invalid rooms",
        "coordinates": "Thiếu tọa độ",
    }
    return "\n".join(
        f"- {labels.get(field, field)}: {count}" for field, count in missing_core_fields.items()
    )


def _percent(value: float) -> str:
    return f"{value:.2%}"


if __name__ == "__main__":
    raise SystemExit(main())
