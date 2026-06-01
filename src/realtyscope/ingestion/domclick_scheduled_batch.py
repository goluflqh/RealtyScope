from __future__ import annotations

import argparse
import json
import sys
import time
from collections.abc import Callable, Mapping, Sequence
from contextlib import suppress
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from realtyscope.database.models import (
    IngestionRun,
    Listing,
    ListingSourceLink,
    RawListingRecord,
    RejectedListingRecord,
    Source,
)
from realtyscope.database.persistence import PersistedIngestionResult
from realtyscope.database.real_data_ingestion import (
    DOMCLICK_SOURCE_NAME,
    RealSourceInspectResult,
    inspect_real_source_snapshot,
    persist_real_source_snapshot,
)
from realtyscope.database.session import create_database_engine, create_session_factory
from realtyscope.ingestion.domclick_snapshot_collector import (
    COLLECTOR_VERSION,
    FetchedDomclickSnapshot,
    collect_domclick_snapshots,
)

DOMCLICK_SNAPSHOT_SOURCE_TYPE = "domclick_snapshot_dir"
DEFAULT_REPORT_DIR = Path("data/processed/domclick_reports")
SCHEDULED_BATCH_VERSION = "realtyscope-domclick-scheduled-batch-v1"


class DomclickCollectionSummary(BaseModel):
    model_config = ConfigDict(frozen=True)

    snapshot_dir: str
    manifest_path: str | None = None
    files_written: int
    capture_mode: str


class LatestIngestionRunSummary(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: int
    status: str
    started_at: datetime
    finished_at: datetime | None
    records_seen: int
    raw_count: int
    normalized_count: int
    rejected_count: int
    inserted_count: int
    updated_count: int
    error_summary: str | None = None


class DomclickIngestionStatus(BaseModel):
    model_config = ConfigDict(frozen=True)

    source_name: str = DOMCLICK_SOURCE_NAME
    source_exists: bool
    ingestion_runs_total: int
    raw_listings_total: int
    listings_total: int
    rejected_listings_total: int
    latest_ingestion_run: LatestIngestionRunSummary | None = None


class ScheduledDomclickBatchReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    run_id: str
    status: str
    started_at: datetime
    finished_at: datetime
    commit_to_database: bool
    min_records: int
    min_normalized_records: int
    collection: DomclickCollectionSummary | None = None
    inspect: RealSourceInspectResult | None = None
    persistence: PersistedIngestionResult | None = None
    database_status: DomclickIngestionStatus | None = None
    report_path: str | None = None
    error_summary: str | None = None


def run_domclick_scheduled_batch(
    *,
    source_path: Path | None = None,
    urls: Sequence[str] | None = None,
    url_file: Path | None = None,
    output_root: Path = Path("data/raw/domclick"),
    collection_date: date | None = None,
    database_url: str | None = None,
    commit_to_database: bool = False,
    max_urls: int = 100,
    delay_seconds: float = 2.0,
    timeout_seconds: float = 20.0,
    max_records: int = 100,
    min_records: int = 1,
    min_normalized_records: int = 0,
    capture_mode: str = "chrome_assisted_scheduled_batch",
    operator_note: str | None = None,
    require_manifest: bool = True,
    report_dir: Path | None = DEFAULT_REPORT_DIR,
    fetch_text: Callable[[str], str] | None = None,
    fetch_snapshot: Callable[[str], FetchedDomclickSnapshot] | None = None,
    sleep: Callable[[float], None] | None = None,
) -> ScheduledDomclickBatchReport:
    started_at = datetime.now(UTC)
    run_id = _make_run_id(started_at)
    collection: DomclickCollectionSummary | None = None
    inspect_result: RealSourceInspectResult | None = None
    persistence_result: PersistedIngestionResult | None = None
    database_status: DomclickIngestionStatus | None = None
    status = "success"
    error_summary: str | None = None

    try:
        _validate_limits(
            max_urls=max_urls,
            max_records=max_records,
            min_records=min_records,
            min_normalized_records=min_normalized_records,
            delay_seconds=delay_seconds,
            timeout_seconds=timeout_seconds,
        )
        snapshot_dir, collection = _prepare_snapshot_dir(
            source_path=source_path,
            urls=urls,
            url_file=url_file,
            output_root=output_root,
            collection_date=collection_date,
            max_urls=max_urls,
            delay_seconds=delay_seconds,
            timeout_seconds=timeout_seconds,
            capture_mode=capture_mode,
            operator_note=operator_note,
            run_id=run_id,
            require_manifest=require_manifest,
            fetch_text=fetch_text,
            fetch_snapshot=fetch_snapshot,
            sleep=sleep,
        )
        inspect_result = inspect_real_source_snapshot(
            source_type=DOMCLICK_SNAPSHOT_SOURCE_TYPE,
            source_path=snapshot_dir,
            max_records=max_records,
        )
        if inspect_result.records_seen < min_records:
            raise RuntimeError(
                "Domclick inspect count is below threshold: "
                f"records_seen={inspect_result.records_seen} min_records={min_records}"
            )
        if inspect_result.normalized_listings < min_normalized_records:
            raise RuntimeError(
                "Domclick normalized listing count is below clean-data threshold: "
                f"normalized_listings={inspect_result.normalized_listings} "
                f"min_normalized_records={min_normalized_records}"
            )

        if commit_to_database:
            persistence_result = persist_real_source_snapshot(
                source_type=DOMCLICK_SNAPSHOT_SOURCE_TYPE,
                source_path=snapshot_dir,
                database_url=database_url,
                max_records=max_records,
            )

        if commit_to_database or database_url is not None:
            database_status = load_domclick_ingestion_status(database_url=database_url)
    except Exception as exc:  # noqa: BLE001 - scheduled reports must capture any failure.
        status = "failed"
        error_summary = f"{type(exc).__name__}: {exc}"

    report = ScheduledDomclickBatchReport(
        run_id=run_id,
        status=status,
        started_at=started_at,
        finished_at=datetime.now(UTC),
        commit_to_database=commit_to_database,
        min_records=min_records,
        min_normalized_records=min_normalized_records,
        collection=collection,
        inspect=inspect_result,
        persistence=persistence_result,
        database_status=database_status,
        error_summary=error_summary,
    )
    return _write_report(report, report_dir=report_dir)


def load_domclick_ingestion_status(database_url: str | None = None) -> DomclickIngestionStatus:
    engine = create_database_engine(database_url)
    session_factory = create_session_factory(engine)
    with session_factory() as session:
        return build_domclick_ingestion_status(session)


def build_domclick_ingestion_status(session: Session) -> DomclickIngestionStatus:
    source = session.scalar(select(Source).where(Source.name == DOMCLICK_SOURCE_NAME))
    if source is None:
        return DomclickIngestionStatus(
            source_exists=False,
            ingestion_runs_total=0,
            raw_listings_total=0,
            listings_total=0,
            rejected_listings_total=0,
        )

    latest_run = session.scalars(
        select(IngestionRun)
        .where(IngestionRun.source_id == source.id)
        .order_by(IngestionRun.started_at.desc(), IngestionRun.id.desc())
        .limit(1)
    ).first()

    return DomclickIngestionStatus(
        source_exists=True,
        ingestion_runs_total=_count(
            session, select(func.count(IngestionRun.id)).where(IngestionRun.source_id == source.id)
        ),
        raw_listings_total=_count(
            session,
            select(func.count(RawListingRecord.id)).where(RawListingRecord.source_id == source.id),
        ),
        listings_total=_count(
            session,
            select(func.count(func.distinct(Listing.id)))
            .join(ListingSourceLink, Listing.id == ListingSourceLink.listing_id)
            .where(ListingSourceLink.source_id == source.id),
        ),
        rejected_listings_total=_count(
            session,
            select(func.count(RejectedListingRecord.id)).where(
                RejectedListingRecord.source_id == source.id
            ),
        ),
        latest_ingestion_run=_latest_run_summary(latest_run),
    )


def _prepare_snapshot_dir(
    *,
    source_path: Path | None,
    urls: Sequence[str] | None,
    url_file: Path | None,
    output_root: Path,
    collection_date: date | None,
    max_urls: int,
    delay_seconds: float,
    timeout_seconds: float,
    capture_mode: str,
    operator_note: str | None,
    run_id: str,
    require_manifest: bool,
    fetch_text: Callable[[str], str] | None,
    fetch_snapshot: Callable[[str], FetchedDomclickSnapshot] | None,
    sleep: Callable[[float], None] | None,
) -> tuple[Path, DomclickCollectionSummary]:
    requested_urls = _load_urls(urls, url_file)
    if source_path is not None and requested_urls:
        raise ValueError("Use either --source-path or Domclick URLs, not both")
    if source_path is not None:
        snapshot_dir = source_path
        manifest_path = _manifest_path(snapshot_dir, require_manifest=require_manifest)
        return snapshot_dir, DomclickCollectionSummary(
            snapshot_dir=str(snapshot_dir),
            manifest_path=str(manifest_path) if manifest_path is not None else None,
            files_written=_count_snapshot_files(snapshot_dir),
            capture_mode=capture_mode,
        )
    if not requested_urls:
        raise ValueError(
            "Provide --source-path, --url, or --url-file for scheduled batch ingestion"
        )

    collection_result = collect_domclick_snapshots(
        requested_urls,
        output_root=output_root,
        collection_date=collection_date,
        fetch_text=fetch_text,
        fetch_snapshot=fetch_snapshot,
        sleep=sleep or time.sleep,
        delay_seconds=delay_seconds,
        timeout_seconds=timeout_seconds,
        max_urls=max_urls,
        collector_version=f"{COLLECTOR_VERSION}; {SCHEDULED_BATCH_VERSION}",
        capture_mode=capture_mode,
        batch_run_id=run_id,
        operator_note=operator_note,
    )
    return collection_result.snapshot_dir, DomclickCollectionSummary(
        snapshot_dir=str(collection_result.snapshot_dir),
        manifest_path=str(collection_result.manifest_path),
        files_written=collection_result.files_written,
        capture_mode=capture_mode,
    )


def _validate_limits(
    *,
    max_urls: int,
    max_records: int,
    min_records: int,
    min_normalized_records: int,
    delay_seconds: float,
    timeout_seconds: float,
) -> None:
    if max_urls <= 0:
        raise ValueError("max_urls must be greater than zero")
    if max_records <= 0:
        raise ValueError("max_records must be greater than zero")
    if min_records < 0:
        raise ValueError("min_records must be zero or greater")
    if min_records > max_records:
        raise ValueError("min_records must be less than or equal to max_records")
    if min_normalized_records < 0:
        raise ValueError("min_normalized_records must be zero or greater")
    if min_normalized_records > max_records:
        raise ValueError("min_normalized_records must be less than or equal to max_records")
    if delay_seconds < 0:
        raise ValueError("delay_seconds must be zero or greater")
    if timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be greater than zero")


def _manifest_path(snapshot_dir: Path, *, require_manifest: bool) -> Path | None:
    manifest_path = snapshot_dir / "manifest.json"
    if manifest_path.is_file():
        return manifest_path
    if require_manifest:
        raise ValueError(f"Domclick snapshot directory is missing manifest.json: {snapshot_dir}")
    return None


def _count_snapshot_files(snapshot_dir: Path) -> int:
    supported_suffixes = {".htm", ".html", ".json"}
    return sum(
        1
        for candidate in snapshot_dir.rglob("*")
        if candidate.is_file()
        and candidate.name.lower() != "manifest.json"
        and candidate.suffix.lower() in supported_suffixes
    )


def _load_urls(urls: Sequence[str] | None, url_file: Path | None) -> list[str]:
    loaded_urls = [url.strip() for url in urls or () if url.strip()]
    if url_file is not None:
        loaded_urls.extend(
            line.strip()
            for line in url_file.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        )
    return loaded_urls


def _latest_run_summary(run: IngestionRun | None) -> LatestIngestionRunSummary | None:
    if run is None:
        return None
    return LatestIngestionRunSummary(
        id=run.id,
        status=run.status,
        started_at=run.started_at,
        finished_at=run.finished_at,
        records_seen=run.records_seen,
        raw_count=run.raw_count,
        normalized_count=run.normalized_count,
        rejected_count=run.rejected_count,
        inserted_count=run.inserted_count,
        updated_count=run.updated_count,
        error_summary=run.error_summary,
    )


def _count(session: Session, statement: Any) -> int:
    value = session.scalar(statement)
    return int(value or 0)


def _make_run_id(started_at: datetime) -> str:
    return f"domclick-{started_at.strftime('%Y%m%dT%H%M%S')}-{started_at.microsecond:06d}Z"


def _write_report(
    report: ScheduledDomclickBatchReport,
    *,
    report_dir: Path | None,
) -> ScheduledDomclickBatchReport:
    if report_dir is None:
        return report
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / f"{report.run_id}.json"
    report = report.model_copy(update={"report_path": str(report_path)})
    report_path.write_text(
        _json_text(report.model_dump(mode="json", exclude_none=True)),
        encoding="utf-8",
    )
    return report


def _json_text(payload: Mapping[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def _print_json(payload: Mapping[str, Any]) -> None:
    with suppress(AttributeError):
        sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))


def _add_run_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    run_parser = subparsers.add_parser(
        "run",
        help="Run one bounded Domclick capture/inspect/optional-commit batch.",
    )
    run_parser.add_argument("--source-path", type=Path, help="Existing Domclick day directory.")
    run_parser.add_argument("--url", action="append", default=[], help="Domclick URL to capture.")
    run_parser.add_argument(
        "--url-file",
        type=Path,
        help="Text file with one Domclick URL per line.",
    )
    run_parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("data/raw/domclick"),
        help="Root directory for captured Domclick snapshots.",
    )
    run_parser.add_argument(
        "--collection-date",
        type=date.fromisoformat,
        default=None,
        help="Collection date in YYYY-MM-DD format. Defaults to today in UTC.",
    )
    run_parser.add_argument("--database-url", default=None, help="Override database URL.")
    run_parser.add_argument("--commit", action="store_true", help="Persist after inspect passes.")
    run_parser.add_argument("--max-urls", type=int, default=100, help="Maximum URLs per run.")
    run_parser.add_argument("--delay-seconds", type=float, default=2.0, help="Delay between URLs.")
    run_parser.add_argument("--timeout-seconds", type=float, default=20.0, help="HTTP timeout.")
    run_parser.add_argument(
        "--max-records",
        type=int,
        default=100,
        help="Maximum records to parse.",
    )
    run_parser.add_argument("--min-records", type=int, default=1, help="Fail below this count.")
    run_parser.add_argument(
        "--min-normalized-records",
        type=int,
        default=0,
        help="Fail before commit unless inspect finds at least this many normalized listings.",
    )
    run_parser.add_argument(
        "--capture-mode",
        default="chrome_assisted_scheduled_batch",
        help="Manifest/report label for how the batch was captured.",
    )
    run_parser.add_argument("--operator-note", default=None, help="Optional manifest note.")
    run_parser.add_argument(
        "--allow-missing-manifest",
        action="store_true",
        help="Allow pre-existing snapshot dirs without manifest.json.",
    )
    run_parser.add_argument(
        "--report-dir",
        type=Path,
        default=DEFAULT_REPORT_DIR,
        help="Directory for generated batch reports; use an ignored runtime path.",
    )
    run_parser.add_argument("--json", action="store_true", help="Print JSON summary.")


def _add_status_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    status_parser = subparsers.add_parser("status", help="Report current Domclick DB status.")
    status_parser.add_argument("--database-url", default=None, help="Override database URL.")
    status_parser.add_argument("--json", action="store_true", help="Print JSON summary.")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run bounded scheduled Domclick batches; this is not a continuous scraper."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    _add_run_parser(subparsers)
    _add_status_parser(subparsers)
    args = parser.parse_args(argv)

    if args.command == "status":
        status = load_domclick_ingestion_status(database_url=args.database_url)
        payload = status.model_dump(mode="json")
        if args.json:
            _print_json(payload)
        else:
            print(
                "Domclick ingestion status "
                f"runs={status.ingestion_runs_total} listings={status.listings_total} "
                f"raw={status.raw_listings_total} rejected={status.rejected_listings_total}"
            )
        return 0

    report = run_domclick_scheduled_batch(
        source_path=args.source_path,
        urls=args.url,
        url_file=args.url_file,
        output_root=args.output_root,
        collection_date=args.collection_date,
        database_url=args.database_url,
        commit_to_database=args.commit,
        max_urls=args.max_urls,
        delay_seconds=args.delay_seconds,
        timeout_seconds=args.timeout_seconds,
        max_records=args.max_records,
        min_records=args.min_records,
        min_normalized_records=args.min_normalized_records,
        capture_mode=args.capture_mode,
        operator_note=args.operator_note,
        require_manifest=not args.allow_missing_manifest,
        report_dir=args.report_dir,
    )
    payload = report.model_dump(mode="json", exclude_none=True)
    if args.json:
        _print_json(payload)
    else:
        print(
            "Domclick scheduled batch "
            f"status={report.status} records_seen="
            f"{report.inspect.records_seen if report.inspect else 0} "
            f"normalized={report.inspect.normalized_listings if report.inspect else 0} "
            f"report_path={report.report_path}"
        )
    return 0 if report.status == "success" else 1


if __name__ == "__main__":
    raise SystemExit(main())
