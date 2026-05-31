import json
from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from realtyscope.database.base import Base
from realtyscope.database.models import Listing, RejectedListingRecord, Source
from realtyscope.database.real_data_ingestion import main


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
