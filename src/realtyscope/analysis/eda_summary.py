from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from decimal import Decimal
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from realtyscope.database.models import (
    IngestionRun,
    Listing,
    RawListingRecord,
    RejectedListingRecord,
    Source,
)
from realtyscope.database.session import create_database_engine

GRADE_4_MIN_RECORDS = 1000


class EdaSummary(BaseModel):
    model_config = ConfigDict(frozen=True)

    sources_total: int
    ingestion_runs_total: int
    raw_listings_total: int
    listings_total: int
    rejected_listings_total: int
    ml_ready_listings: int
    coordinate_coverage: float
    rejected_rate: float
    price_rub_min: int | None
    price_rub_max: int | None
    price_rub_avg: float | None
    total_area_m2_avg: float | None
    price_per_m2_avg: float | None
    rooms_distribution: dict[str, int]
    latest_ingestion_run: dict[str, Any] | None
    ml_readiness_conclusion: str


def build_eda_summary(database_url: str | None = None) -> EdaSummary:
    engine = create_database_engine(database_url)
    with Session(engine) as session:
        sources_total = _count(session, Source)
        ingestion_runs_total = _count(session, IngestionRun)
        listings_total = _count(session, Listing)
        rejected_total = _count(session, RejectedListingRecord)
        raw_total = _count(session, RawListingRecord)
        ml_ready = (
            session.scalar(
                select(func.count()).select_from(Listing).where(Listing.is_ml_ready.is_(True))
            )
            or 0
        )
        has_coordinates = (
            session.scalar(
                select(func.count()).select_from(Listing).where(Listing.has_coordinates.is_(True))
            )
            or 0
        )
        price_min, price_max, price_avg = session.execute(
            select(
                func.min(Listing.price_rub),
                func.max(Listing.price_rub),
                func.avg(Listing.price_rub),
            )
        ).one()
        area_avg = session.scalar(select(func.avg(Listing.total_area_m2)))
        price_area_rows = session.execute(
            select(Listing.price_rub, Listing.total_area_m2).where(Listing.total_area_m2 > 0)
        ).all()
        rooms_distribution = {
            str(rooms): count
            for rooms, count in session.execute(
                select(Listing.rooms, func.count()).group_by(Listing.rooms).order_by(Listing.rooms)
            )
        }
        latest_run = session.execute(
            select(IngestionRun, Source.name)
            .join(Source, IngestionRun.source_id == Source.id)
            .order_by(IngestionRun.started_at.desc(), IngestionRun.id.desc())
            .limit(1)
        ).first()

    records_seen = listings_total + rejected_total
    coordinate_coverage = has_coordinates / listings_total if listings_total else 0.0
    rejected_rate = rejected_total / records_seen if records_seen else 0.0
    price_per_m2_avg = _average_price_per_m2(price_area_rows)
    return EdaSummary(
        sources_total=sources_total,
        ingestion_runs_total=ingestion_runs_total,
        raw_listings_total=raw_total,
        listings_total=listings_total,
        rejected_listings_total=rejected_total,
        ml_ready_listings=ml_ready,
        coordinate_coverage=coordinate_coverage,
        rejected_rate=rejected_rate,
        price_rub_min=_optional_int(price_min),
        price_rub_max=_optional_int(price_max),
        price_rub_avg=_optional_float(price_avg),
        total_area_m2_avg=_optional_float(area_avg),
        price_per_m2_avg=price_per_m2_avg,
        rooms_distribution=rooms_distribution,
        latest_ingestion_run=_latest_run_payload(latest_run),
        ml_readiness_conclusion=_ml_readiness_conclusion(listings_total, ml_ready),
    )


def render_eda_markdown(summary: EdaSummary) -> str:
    return "\n".join(
        [
            "# RealtyScope Phase 3.5 EDA Summary",
            "",
            "## Tổng quan dữ liệu",
            f"- Số source: {summary.sources_total}",
            f"- Số ingestion run: {summary.ingestion_runs_total}",
            f"- Số raw listing: {summary.raw_listings_total}",
            f"- Số listing đã chuẩn hóa: {summary.listings_total}",
            f"- Số rejected listing: {summary.rejected_listings_total}",
            f"- Tỷ lệ rejected: {_percent(summary.rejected_rate)}",
            "",
            "## Chất lượng dữ liệu",
            f"- Số listing sẵn sàng cho ML: {summary.ml_ready_listings}",
            f"- Tỷ lệ có tọa độ: {_percent(summary.coordinate_coverage)}",
            f"- Kết luận ML readiness: {summary.ml_readiness_conclusion}",
            "",
            "## Phân phối giá và diện tích",
            f"- Giá nhỏ nhất: {_format_number(summary.price_rub_min)} RUB",
            f"- Giá lớn nhất: {_format_number(summary.price_rub_max)} RUB",
            f"- Giá trung bình: {_format_number(summary.price_rub_avg)} RUB",
            f"- Diện tích trung bình: {_format_number(summary.total_area_m2_avg)} m2",
            f"- Giá/m2 trung bình: {_format_number(summary.price_per_m2_avg)} RUB/m2",
            "",
            "## Phân phối số phòng",
            _rooms_distribution_markdown(summary.rooms_distribution),
            "",
            "## Ingestion run mới nhất",
            _latest_run_markdown(summary.latest_ingestion_run),
            "",
        ]
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build a RealtyScope EDA summary from database rows."
    )
    parser.add_argument("--database-url", default=None, help="Override database URL for this run.")
    parser.add_argument("--output", type=Path, help="Optional markdown output path.")
    parser.add_argument("--json", action="store_true", help="Print JSON summary.")
    args = parser.parse_args(argv)

    summary = build_eda_summary(args.database_url)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(render_eda_markdown(summary), encoding="utf-8")
    if args.json:
        print(json.dumps(summary.model_dump(mode="json"), ensure_ascii=False, sort_keys=True))
    else:
        print(render_eda_markdown(summary))
    return 0


def _count(session: Session, model: type[Any]) -> int:
    return session.scalar(select(func.count()).select_from(model)) or 0


def _average_price_per_m2(price_area_rows: Sequence[tuple[Any, Any]]) -> float | None:
    values = [
        _optional_float(price) / _optional_float(area)
        for price, area in price_area_rows
        if _optional_float(price) is not None and _optional_float(area) not in (None, 0)
    ]
    if not values:
        return None
    return sum(values) / len(values)


def _optional_int(value: Any) -> int | None:
    if value is None:
        return None
    return int(value)


def _optional_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return float(value)
    return float(value)


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


def _ml_readiness_conclusion(listings_total: int, ml_ready: int) -> str:
    if listings_total < GRADE_4_MIN_RECORDS:
        return "Chưa đủ cơ sở để chuyển sang ML: cần ít nhất 1000 records thật."
    if ml_ready == 0:
        return "Chưa đủ cơ sở để chuyển sang ML: chưa có listing sẵn sàng cho ML."
    return "Có thể bắt đầu baseline ML sau khi kiểm tra outliers và missing values chi tiết."


def _percent(value: float) -> str:
    return f"{value:.2%}"


def _format_number(value: float | int | None) -> str:
    if value is None:
        return "n/a"
    return f"{value:,.2f}".rstrip("0").rstrip(".")


def _rooms_distribution_markdown(distribution: dict[str, int]) -> str:
    if not distribution:
        return "- Chưa có dữ liệu số phòng."
    return "\n".join(f"- {rooms} phòng: {count}" for rooms, count in distribution.items())


def _latest_run_markdown(latest_run: dict[str, Any] | None) -> str:
    if latest_run is None:
        return "- Chưa có ingestion run."
    return "\n".join(
        [
            f"- Source: {latest_run['source_name']}",
            f"- Status: {latest_run['status']}",
            f"- Records seen: {latest_run['records_seen']}",
            f"- Normalized: {latest_run['normalized_count']}",
            f"- Rejected: {latest_run['rejected_count']}",
        ]
    )


if __name__ == "__main__":
    raise SystemExit(main())
