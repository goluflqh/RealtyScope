import json
from datetime import UTC, date, datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from realtyscope.database.base import Base
from realtyscope.database.models import IngestionRun, Listing, ListingObservation, Source
from realtyscope.database.session import create_database_engine
from realtyscope.ingestion.domclick_scheduled_batch import main, run_domclick_scheduled_batch
from realtyscope.ingestion.domclick_snapshot_collector import FetchedDomclickSnapshot

ROBOTS_TXT = """
User-agent: *
Disallow: /search
Disallow: /*?*
Allow: /sitemaps/
Allow: /card/
"""


def test_scheduled_batch_collects_inspects_commits_and_reports_idempotent(
    tmp_path: Path,
) -> None:
    database_url = _sqlite_database_url(tmp_path / "scheduled_domclick.sqlite3")
    engine = create_database_engine(database_url)
    Base.metadata.create_all(engine)

    first = run_domclick_scheduled_batch(
        urls=["https://domclick.ru/card/sale__flat__scheduled-1/"],
        output_root=tmp_path / "data" / "raw" / "domclick",
        collection_date=date(2026, 6, 1),
        database_url=database_url,
        commit_to_database=True,
        max_urls=5,
        delay_seconds=0,
        max_records=10,
        min_records=1,
        report_dir=tmp_path / "reports",
        fetch_text=lambda _url: ROBOTS_TXT,
        fetch_snapshot=_fetch_listing_snapshot,
        sleep=lambda _seconds: None,
    )

    assert first.status == "success"
    assert first.collection is not None
    assert first.collection.files_written == 1
    assert first.inspect is not None
    assert first.inspect.records_seen == 1
    assert first.persistence is not None
    assert first.persistence.raw_inserted == 1
    assert first.persistence.listings_created == 1
    assert first.database_status is not None
    assert first.database_status.ingestion_runs_total == 1
    assert first.report_path is not None
    assert Path(first.report_path).is_file()

    manifest = json.loads(
        (Path(first.collection.snapshot_dir) / "manifest.json").read_text(encoding="utf-8")
    )
    assert manifest["capture_mode"] == "chrome_assisted_scheduled_batch"
    assert manifest["batch_run_id"] == first.run_id
    assert manifest["max_urls"] == 5
    assert manifest["delay_seconds"] == 0

    second = run_domclick_scheduled_batch(
        urls=["https://domclick.ru/card/sale__flat__scheduled-1/"],
        output_root=tmp_path / "data" / "raw" / "domclick",
        collection_date=date(2026, 6, 1),
        database_url=database_url,
        commit_to_database=True,
        max_urls=5,
        delay_seconds=0,
        max_records=10,
        min_records=1,
        report_dir=tmp_path / "reports",
        fetch_text=lambda _url: ROBOTS_TXT,
        fetch_snapshot=_fetch_listing_snapshot,
        sleep=lambda _seconds: None,
    )

    assert second.status == "success"
    assert second.persistence is not None
    assert second.persistence.raw_inserted == 0
    assert second.persistence.raw_reused == 1
    assert second.persistence.listings_created == 0
    assert second.persistence.listings_updated == 1
    assert second.database_status is not None
    assert second.database_status.ingestion_runs_total == 2

    with Session(engine) as session:
        assert len(session.scalars(select(IngestionRun)).all()) == 2
        listings = session.scalars(select(Listing)).all()
        assert len(listings) == 1
        assert listings[0].address_text == "Москва, Плановая улица, 1"


def test_scheduled_batch_reused_snapshot_records_new_observation_timestamp(
    tmp_path: Path,
) -> None:
    database_url = _sqlite_database_url(tmp_path / "scheduled_domclick_reused.sqlite3")
    engine = create_database_engine(database_url)
    Base.metadata.create_all(engine)
    first_started_at = datetime(2026, 6, 1, 0, 0, tzinfo=UTC)
    second_started_at = datetime(2026, 6, 2, 0, 0, tzinfo=UTC)

    first = run_domclick_scheduled_batch(
        urls=["https://domclick.ru/card/sale__flat__scheduled-1/"],
        output_root=tmp_path / "data" / "raw" / "domclick",
        collection_date=date(2026, 6, 1),
        database_url=database_url,
        commit_to_database=True,
        max_urls=5,
        delay_seconds=0,
        max_records=10,
        min_records=1,
        report_dir=tmp_path / "reports",
        fetch_text=lambda _url: ROBOTS_TXT,
        fetch_snapshot=_fetch_listing_snapshot,
        sleep=lambda _seconds: None,
        clock=lambda: first_started_at,
    )
    assert first.status == "success"
    assert first.collection is not None

    second = run_domclick_scheduled_batch(
        source_path=Path(first.collection.snapshot_dir),
        database_url=database_url,
        commit_to_database=True,
        max_records=10,
        min_records=1,
        report_dir=tmp_path / "reports",
        clock=lambda: second_started_at,
    )

    assert second.status == "success"
    assert second.persistence is not None
    assert second.persistence.raw_inserted == 0
    assert second.persistence.raw_reused == 1
    assert second.persistence.observations_inserted == 1

    with Session(engine) as session:
        observations = session.scalars(
            select(ListingObservation).order_by(ListingObservation.observed_at)
        ).all()

    assert [_as_utc(observation.observed_at) for observation in observations] == [
        first_started_at,
        second_started_at,
    ]
    assert len({observation.raw_listing_id for observation in observations}) == 1


def test_missing_manifest_partial_commit_requires_explicit_observed_at(
    tmp_path: Path,
) -> None:
    database_url = _sqlite_database_url(tmp_path / "scheduled_domclick_partial.sqlite3")
    engine = create_database_engine(database_url)
    Base.metadata.create_all(engine)
    snapshot_dir = _write_partial_payload_snapshot(tmp_path)
    recovery_started_at = datetime(2026, 6, 5, 1, 54, tzinfo=UTC)

    report = run_domclick_scheduled_batch(
        source_path=snapshot_dir,
        database_url=database_url,
        commit_to_database=True,
        max_records=10,
        min_records=1,
        require_manifest=False,
        report_dir=tmp_path / "reports",
        clock=lambda: recovery_started_at,
    )

    assert report.status == "failed"
    assert report.persistence is None
    assert report.error_summary is not None
    assert "observed_at" in report.error_summary

    with Session(engine) as session:
        assert session.scalar(select(Source)) is None


def test_missing_manifest_partial_recovery_uses_explicit_observed_at(
    tmp_path: Path,
) -> None:
    database_url = _sqlite_database_url(tmp_path / "scheduled_domclick_partial_recovery.sqlite3")
    engine = create_database_engine(database_url)
    Base.metadata.create_all(engine)
    snapshot_dir = _write_partial_payload_snapshot(tmp_path)
    capture_observed_at = datetime(2026, 6, 4, 21, 0, 46, tzinfo=UTC)
    recovery_started_at = datetime(2026, 6, 4, 22, 54, 10, tzinfo=UTC)

    report = run_domclick_scheduled_batch(
        source_path=snapshot_dir,
        database_url=database_url,
        commit_to_database=True,
        max_records=10,
        min_records=1,
        require_manifest=False,
        observed_at=capture_observed_at,
        report_dir=tmp_path / "reports",
        clock=lambda: recovery_started_at,
    )

    assert report.status == "success"
    assert report.persistence is not None
    assert report.persistence.observations_inserted == 1
    assert report.observed_at == capture_observed_at

    with Session(engine) as session:
        observation = session.scalars(select(ListingObservation)).one()
        run = session.scalars(select(IngestionRun)).one()

    assert _as_utc(observation.observed_at) == capture_observed_at
    assert _as_utc(run.started_at) == capture_observed_at


def test_scheduled_batch_fails_before_commit_when_inspect_count_is_too_low(
    tmp_path: Path,
) -> None:
    database_url = _sqlite_database_url(tmp_path / "scheduled_domclick_empty.sqlite3")
    engine = create_database_engine(database_url)
    Base.metadata.create_all(engine)

    report = run_domclick_scheduled_batch(
        urls=["https://domclick.ru/card/sale__flat__empty-1/"],
        output_root=tmp_path / "data" / "raw" / "domclick",
        collection_date=date(2026, 6, 1),
        database_url=database_url,
        commit_to_database=True,
        delay_seconds=0,
        min_records=1,
        report_dir=tmp_path / "reports",
        fetch_text=lambda _url: ROBOTS_TXT,
        fetch_snapshot=_fetch_empty_snapshot,
        sleep=lambda _seconds: None,
    )

    assert report.status == "failed"
    assert report.inspect is not None
    assert report.inspect.records_seen == 0
    assert report.persistence is None
    assert report.error_summary is not None
    assert "below threshold" in report.error_summary
    assert report.report_path is not None
    assert Path(report.report_path).is_file()

    with Session(engine) as session:
        assert session.scalar(select(Source)) is None


def test_scheduled_batch_fails_before_commit_when_clean_count_is_too_low(
    tmp_path: Path,
) -> None:
    database_url = _sqlite_database_url(tmp_path / "scheduled_domclick_not_clean.sqlite3")
    engine = create_database_engine(database_url)
    Base.metadata.create_all(engine)

    report = run_domclick_scheduled_batch(
        urls=["https://domclick.ru/card/sale__flat__mixed-clean-1/"],
        output_root=tmp_path / "data" / "raw" / "domclick",
        collection_date=date(2026, 6, 1),
        database_url=database_url,
        commit_to_database=True,
        delay_seconds=0,
        min_records=1,
        min_normalized_records=2,
        max_records=10,
        report_dir=tmp_path / "reports",
        fetch_text=lambda _url: ROBOTS_TXT,
        fetch_snapshot=_fetch_mixed_clean_snapshot,
        sleep=lambda _seconds: None,
    )

    assert report.status == "failed"
    assert report.min_normalized_records == 2
    assert report.inspect is not None
    assert report.inspect.records_seen == 2
    assert report.inspect.normalized_listings == 1
    assert report.persistence is None
    assert report.error_summary is not None
    assert "clean-data threshold" in report.error_summary

    with Session(engine) as session:
        assert session.scalar(select(Source)) is None


def test_scheduled_batch_status_cli_reports_database_counts(tmp_path: Path, capsys) -> None:
    database_url = _sqlite_database_url(tmp_path / "scheduled_status.sqlite3")
    engine = create_database_engine(database_url)
    Base.metadata.create_all(engine)

    exit_code = main(["status", "--database-url", database_url, "--json"])

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload == {
        "source_name": "domclick",
        "source_exists": False,
        "ingestion_runs_total": 0,
        "raw_listings_total": 0,
        "listings_total": 0,
        "rejected_listings_total": 0,
        "latest_ingestion_run": None,
    }


def _fetch_listing_snapshot(url: str) -> FetchedDomclickSnapshot:
    return FetchedDomclickSnapshot(
        url=url,
        status_code=200,
        headers={"content-type": "application/json"},
        body=json.dumps(
            {
                "items": [
                    {
                        "id": "scheduled-1",
                        "url": "https://domclick.ru/card/sale__flat__scheduled-1/",
                        "address": "Москва, Плановая улица, 1",
                        "price": 12_700_000,
                        "area": 42.5,
                        "rooms": 2,
                        "lat": 55.821,
                        "lng": 37.498,
                    }
                ]
            },
            ensure_ascii=False,
        ).encode("utf-8"),
    )


def _fetch_empty_snapshot(url: str) -> FetchedDomclickSnapshot:
    return FetchedDomclickSnapshot(
        url=url,
        status_code=200,
        headers={"content-type": "application/json"},
        body=json.dumps({"items": []}).encode("utf-8"),
    )


def _fetch_mixed_clean_snapshot(url: str) -> FetchedDomclickSnapshot:
    return FetchedDomclickSnapshot(
        url=url,
        status_code=200,
        headers={"content-type": "application/json"},
        body=json.dumps(
            {
                "items": [
                    {
                        "id": "clean-1",
                        "url": "https://domclick.ru/card/sale__flat__clean-1/",
                        "address": "Москва, Чистая улица, 1",
                        "price": 12_700_000,
                        "area": 42.5,
                        "rooms": 2,
                    },
                    {
                        "id": "rejected-1",
                        "url": "https://domclick.ru/card/sale__flat__rejected-1/",
                        "address": "Москва, Неполная улица, 2",
                        "area": 38.0,
                        "rooms": 1,
                    },
                ]
            },
            ensure_ascii=False,
        ).encode("utf-8"),
    )


def _write_partial_payload_snapshot(tmp_path: Path) -> Path:
    snapshot_dir = tmp_path / "data" / "raw" / "domclick" / "2026-06-05-bulk"
    payloads_dir = snapshot_dir / "payloads"
    payloads_dir.mkdir(parents=True)
    payload = {
        "items": [
            {
                "id": "partial-1",
                "url": "https://domclick.ru/card/sale__flat__partial-1/",
                "address": "Москва, Частичная улица, 1",
                "price": 12_700_000,
                "area": 42.5,
                "rooms": 2,
                "lat": 55.821,
                "lng": 37.498,
            }
        ]
    }
    (payloads_dir / "search-offset-000000.json").write_text(
        json.dumps(payload, ensure_ascii=False), encoding="utf-8"
    )
    return snapshot_dir


def _sqlite_database_url(path: Path) -> str:
    return f"sqlite+pysqlite:///{path.as_posix()}"


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value
