import json
from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from realtyscope.database.base import Base
from realtyscope.database.models import IngestionRun, Listing, RejectedListingRecord, Source
from realtyscope.database.real_data_ingestion import main


def _write_domclick_daily_snapshot(snapshot_dir: Path) -> None:
    payloads_dir = snapshot_dir / "payloads"
    pages_dir = snapshot_dir / "pages"
    payloads_dir.mkdir(parents=True)
    pages_dir.mkdir(parents=True)
    (snapshot_dir / "manifest.json").write_text(
        json.dumps(
            {
                "source_name": "domclick",
                "collector_version": "test",
                "entries": [
                    {"path": "payloads/listings.json", "source_type": "domclick_json"},
                    {"path": "pages/detail.html", "source_type": "domclick_html"},
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (payloads_dir / "listings.json").write_text(
        json.dumps(
            {
                "items": [
                    {
                        "id": "domclick-dir-1",
                        "url": "https://domclick.ru/card/sale__flat__domclick-dir-1/",
                        "address": "Москва, Новый Арбат, 12",
                        "price": 19_400_000,
                        "area": 57.2,
                        "rooms": 2,
                        "lat": 55.7522,
                        "lng": 37.6031,
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (pages_dir / "detail.html").write_text(
        """
        <!doctype html>
        <html>
          <body>
            <script type="application/json">
            {
              "items": [
                {
                  "id": "domclick-dir-bad-1",
                  "url": "https://domclick.ru/card/sale__flat__domclick-dir-bad-1/",
                  "address": "Москва, Остоженка, 5",
                  "area": 44.0,
                  "rooms": 1
                }
              ]
            }
            </script>
          </body>
        </html>
        """,
        encoding="utf-8",
    )


def test_domclick_html_snapshot_command_persists_embedded_json_rows(tmp_path: Path, capsys) -> None:
    source_path = tmp_path / "domclick_snapshot.html"
    source_path.write_text(
        """
        <!doctype html>
        <html>
          <head><title>Domclick snapshot</title></head>
          <body>
            <script id="__NEXT_DATA__" type="application/json">
            {
              "props": {
                "pageProps": {
                  "items": [
                    {
                      "id": "domclick-html-1",
                      "url": "https://domclick.ru/card/sale__flat__domclick-html-1/",
                      "address": "Москва, Арбат, 10",
                      "price": 22_500_000,
                      "area": 61.0,
                      "rooms": 3,
                      "lat": 55.752,
                      "lng": 37.592
                    }
                  ]
                }
              }
            }
            </script>
          </body>
        </html>
        """.replace("22_500_000", "22500000"),
        encoding="utf-8",
    )
    database_path = tmp_path / "real_data_html.sqlite3"
    database_url = f"sqlite+pysqlite:///{database_path.as_posix()}"
    engine = create_engine(database_url)
    Base.metadata.create_all(engine)

    exit_code = main(
        [
            "--source-type",
            "domclick_html",
            "--source-path",
            str(source_path),
            "--database-url",
            database_url,
            "--json",
        ]
    )

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["source_type"] == "domclick_html"
    assert payload["records_seen"] == 1
    assert payload["raw_inserted"] == 1
    assert payload["listings_created"] == 1

    with Session(engine) as session:
        listings = session.scalars(select(Listing)).all()

    assert len(listings) == 1
    assert listings[0].address_text == "Москва, Арбат, 10"
    assert listings[0].price_rub == 22_500_000


def test_domclick_html_snapshot_command_persists_ssr_state_rows(tmp_path: Path, capsys) -> None:
    source_path = tmp_path / "domclick_search_snapshot.html"
    ssr_state = {
        "search": {
            "pages": [
                {
                    "ids": [2077280654],
                    "entities": {
                        "2077280654": {
                            "id": 2077280654,
                            "path": "https://domclick.ru/card/sale__flat__2077280654",
                            "offerType": "flat",
                            "address": {"displayName": "Москва, улица Перерва, 58"},
                            "objectInfo": {"area": 38.8, "rooms": 1, "floor": 6},
                            "house": {"floors": 17, "buildYear": 2000},
                            "location": {"lat": 55.663109, "lon": 37.761034},
                            "price": 13_400_000,
                            "resourceLogLevelClient": "__UNDEFINED__",
                        }
                    },
                }
            ]
        }
    }
    ssr_script = json.dumps(ssr_state, ensure_ascii=False).replace('"__UNDEFINED__"', "undefined")
    source_path.write_text(
        f"""
        <!doctype html>
        <html>
          <body>
            <script>
              window.__SSR_STATE__={ssr_script};
              window.__SSR_CONTEXT__={{"requestId":"test"}};
            </script>
          </body>
        </html>
        """,
        encoding="utf-8",
    )
    database_path = tmp_path / "real_data_html_ssr.sqlite3"
    database_url = f"sqlite+pysqlite:///{database_path.as_posix()}"
    engine = create_engine(database_url)
    Base.metadata.create_all(engine)

    exit_code = main(
        [
            "--source-type",
            "domclick_html",
            "--source-path",
            str(source_path),
            "--database-url",
            database_url,
            "--json",
        ]
    )

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["records_seen"] == 1
    assert payload["raw_inserted"] == 1
    assert payload["listings_created"] == 1

    with Session(engine) as session:
        listings = session.scalars(select(Listing)).all()

    assert len(listings) == 1
    assert listings[0].address_text == "Москва, улица Перерва, 58"
    assert float(listings[0].total_area_m2) == 38.8


def test_domclick_json_snapshot_command_persists_rows(tmp_path: Path, capsys) -> None:
    source_path = tmp_path / "domclick_snapshot.json"
    source_path.write_text(
        json.dumps(
            {
                "items": [
                    {
                        "id": "domclick-real-1",
                        "url": "https://domclick.ru/card/sale__flat__domclick-real-1/",
                        "address": "Москва, Тверская улица, 1",
                        "price": 14_200_000,
                        "area": 52.4,
                        "rooms": 2,
                        "lat": 55.7601,
                        "lng": 37.6187,
                        "floor": 5,
                        "floorsTotal": 12,
                        "builtYear": 2008,
                        "description": "Domclick snapshot row for parser verification.",
                    },
                    {
                        "id": "domclick-bad-1",
                        "url": "https://domclick.ru/card/sale__flat__domclick-bad-1/",
                        "area": 41.0,
                        "rooms": 1,
                    },
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    database_path = tmp_path / "real_data.sqlite3"
    database_url = f"sqlite+pysqlite:///{database_path.as_posix()}"
    engine = create_engine(database_url)
    Base.metadata.create_all(engine)

    exit_code = main(
        [
            "--source-type",
            "domclick_json",
            "--source-path",
            str(source_path),
            "--database-url",
            database_url,
            "--json",
        ]
    )

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["source_type"] == "domclick_json"
    assert payload["records_seen"] == 2
    assert payload["raw_inserted"] == 1
    assert payload["listings_created"] == 1
    assert payload["rejected_inserted"] == 1

    with Session(engine) as session:
        source = session.scalar(select(Source).where(Source.name == "domclick"))
        listings = session.scalars(select(Listing)).all()
        rejected = session.scalars(select(RejectedListingRecord)).all()

    assert source is not None
    assert len(listings) == 1
    assert listings[0].address_text == "Москва, Тверская улица, 1"
    assert listings[0].price_rub == 14_200_000
    assert len(rejected) == 1
    assert "price" in rejected[0].reason


def test_domclick_snapshot_directory_command_persists_daily_snapshot(
    tmp_path: Path, capsys
) -> None:
    snapshot_dir = tmp_path / "data" / "raw" / "domclick" / "2026-05-31"
    _write_domclick_daily_snapshot(snapshot_dir)
    database_path = tmp_path / "real_data_snapshot_dir.sqlite3"
    database_url = f"sqlite+pysqlite:///{database_path.as_posix()}"
    engine = create_engine(database_url)
    Base.metadata.create_all(engine)

    exit_code = main(
        [
            "--source-type",
            "domclick_snapshot_dir",
            "--source-path",
            str(snapshot_dir),
            "--database-url",
            database_url,
            "--json",
        ]
    )

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["source_type"] == "domclick_snapshot_dir"
    assert payload["records_seen"] == 2
    assert payload["raw_inserted"] == 1
    assert payload["listings_created"] == 1
    assert payload["rejected_inserted"] == 1

    with Session(engine) as session:
        ingestion_runs = session.scalars(select(IngestionRun)).all()
        listings = session.scalars(select(Listing)).all()
        rejected = session.scalars(select(RejectedListingRecord)).all()

    assert len(ingestion_runs) == 1
    assert ingestion_runs[0].records_seen == 2
    assert ingestion_runs[0].raw_count == 1
    assert ingestion_runs[0].rejected_count == 1
    assert len(listings) == 1
    assert listings[0].address_text == "Москва, Новый Арбат, 12"
    assert len(rejected) == 1
    assert "price" in rejected[0].reason


def test_domclick_snapshot_directory_inspect_only_reports_counts_without_database(
    tmp_path: Path, capsys
) -> None:
    snapshot_dir = tmp_path / "data" / "raw" / "domclick" / "2026-05-31"
    _write_domclick_daily_snapshot(snapshot_dir)

    exit_code = main(
        [
            "--source-type",
            "domclick_snapshot_dir",
            "--source-path",
            str(snapshot_dir),
            "--inspect-only",
            "--json",
        ]
    )

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload == {
        "source_type": "domclick_snapshot_dir",
        "source_path": str(snapshot_dir),
        "mode": "inspect_only",
        "records_seen": 2,
        "raw_listings": 1,
        "normalized_listings": 1,
        "rejected_listings": 1,
        "ml_ready_listings": 1,
    }


def test_domclick_snapshot_directory_skips_unparseable_snapshot_files(
    tmp_path: Path, capsys
) -> None:
    snapshot_dir = tmp_path / "data" / "raw" / "domclick" / "2026-06-01"
    pages_dir = snapshot_dir / "pages"
    payloads_dir = snapshot_dir / "payloads"
    pages_dir.mkdir(parents=True)
    payloads_dir.mkdir(parents=True)
    (pages_dir / "hydrated_search.html").write_text(
        "<html><body>listing text only after hydration</body></html>",
        encoding="utf-8",
    )
    (payloads_dir / "search_state.json").write_text(
        json.dumps(
            {
                "search": {
                    "pages": [
                        {
                            "ids": [2077280654],
                            "entities": {
                                "2077280654": {
                                    "id": 2077280654,
                                    "path": "https://domclick.ru/card/sale__flat__2077280654",
                                    "offerType": "flat",
                                    "address": {"displayName": "Москва, улица Перерва, 58"},
                                    "objectInfo": {"area": 38.8, "rooms": 1, "floor": 6},
                                    "house": {"floors": 17},
                                    "location": {"lat": 55.663109, "lon": 37.761034},
                                    "price": 13_400_000,
                                }
                            },
                        }
                    ]
                }
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    exit_code = main(
        [
            "--source-type",
            "domclick_snapshot_dir",
            "--source-path",
            str(snapshot_dir),
            "--inspect-only",
            "--json",
        ]
    )

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["records_seen"] == 1
    assert payload["normalized_listings"] == 1
    assert payload["rejected_listings"] == 0
