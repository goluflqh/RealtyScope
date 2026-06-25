from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from collections.abc import Sequence
from contextlib import suppress
from dataclasses import asdict, dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from realtyscope.database.models import ListingObservation, RawListingRecord, Source
from realtyscope.database.session import create_database_engine

DEFAULT_MIN_GAP_DAYS = 3


@dataclass(frozen=True)
class TerminalLifecycleCandidate:
    source_name: str
    source_listing_id: str
    source_url: str
    first_observed_date: str
    last_observed_date: str
    latest_source_observed_date: str
    gap_days: int
    observed_exposure_days: int
    verification_status: str = "needs_source_verification"


def select_terminal_lifecycle_candidates(
    session: Session,
    *,
    min_gap_days: int = DEFAULT_MIN_GAP_DAYS,
    limit: int | None = 100,
) -> list[TerminalLifecycleCandidate]:
    source_latest_dates: dict[int, object] = {}
    grouped_observations: dict[tuple[int, str], dict[str, object]] = defaultdict(
        lambda: {"dates": set(), "source_name": ""}
    )
    observation_rows = session.execute(
        select(
            ListingObservation.source_id,
            Source.name,
            ListingObservation.source_listing_id,
            ListingObservation.observed_at,
        ).join(Source, Source.id == ListingObservation.source_id)
    )
    for source_id, source_name, source_listing_id, observed_at in observation_rows:
        if observed_at is None:
            continue
        source_listing_key = str(source_listing_id or "").strip()
        if not source_listing_key:
            continue
        observed_date = observed_at.date()
        latest_date = source_latest_dates.get(int(source_id))
        if latest_date is None or observed_date > latest_date:
            source_latest_dates[int(source_id)] = observed_date
        bucket = grouped_observations[(int(source_id), source_listing_key)]
        dates = bucket["dates"]
        assert isinstance(dates, set)
        dates.add(observed_date)
        bucket["source_name"] = str(source_name)

    source_urls: dict[tuple[int, str], str] = {}
    raw_rows = session.execute(
        select(
            RawListingRecord.source_id,
            RawListingRecord.source_listing_id,
            RawListingRecord.source_url,
        ).where(RawListingRecord.source_url.is_not(None))
    )
    for source_id, source_listing_id, source_url in raw_rows:
        source_listing_key = str(source_listing_id or "").strip()
        source_url_value = str(source_url or "").strip()
        if source_listing_key and source_url_value:
            source_urls.setdefault((int(source_id), source_listing_key), source_url_value)

    candidates: list[TerminalLifecycleCandidate] = []
    for (source_id, source_listing_id), group in grouped_observations.items():
        dates_value = group["dates"]
        assert isinstance(dates_value, set)
        observed_dates = sorted(dates_value)
        latest_source_date = source_latest_dates.get(source_id)
        source_url = source_urls.get((source_id, source_listing_id))
        if len(observed_dates) <= 1 or latest_source_date is None or source_url is None:
            continue
        last_observed_date = observed_dates[-1]
        first_observed_date = observed_dates[0]
        gap_days = (latest_source_date - last_observed_date).days
        observed_exposure_days = (last_observed_date - first_observed_date).days
        if gap_days < min_gap_days or observed_exposure_days <= 0:
            continue
        candidates.append(
            TerminalLifecycleCandidate(
                source_name=str(group["source_name"]),
                source_listing_id=source_listing_id,
                source_url=source_url,
                first_observed_date=first_observed_date.isoformat(),
                last_observed_date=last_observed_date.isoformat(),
                latest_source_observed_date=latest_source_date.isoformat(),
                gap_days=gap_days,
                observed_exposure_days=observed_exposure_days,
            )
        )

    candidates.sort(
        key=lambda candidate: (
            candidate.gap_days,
            candidate.observed_exposure_days,
            candidate.source_name,
            candidate.source_listing_id,
        ),
        reverse=True,
    )
    if limit is None:
        return candidates
    return candidates[: max(0, limit)]


def build_terminal_lifecycle_candidates(
    *,
    database_url: str | None = None,
    min_gap_days: int = DEFAULT_MIN_GAP_DAYS,
    limit: int | None = 100,
) -> list[TerminalLifecycleCandidate]:
    engine = create_database_engine(database_url)
    with Session(engine) as session:
        return select_terminal_lifecycle_candidates(
            session,
            min_gap_days=min_gap_days,
            limit=limit,
        )


def main(argv: Sequence[str] | None = None) -> int:
    with suppress(AttributeError):
        sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(
        description=(
            "List RealtyScope observations that need source verification before they can "
            "be treated as terminal lifecycle rows."
        )
    )
    parser.add_argument("--database-url", default=None, help="Override database URL.")
    parser.add_argument("--min-gap-days", type=int, default=DEFAULT_MIN_GAP_DAYS)
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--json", action="store_true", help="Print JSON rows.")
    args = parser.parse_args(argv)

    candidates = build_terminal_lifecycle_candidates(
        database_url=args.database_url,
        min_gap_days=args.min_gap_days,
        limit=args.limit,
    )
    payload = [asdict(candidate) for candidate in candidates]
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    else:
        for row in payload:
            print(
                "{source_name} {source_listing_id} gap={gap_days}d "
                "exposure={observed_exposure_days}d {source_url}".format(**row)
            )
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
