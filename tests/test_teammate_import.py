from pathlib import Path

from realtyscope.ingestion.teammate_import import import_teammate_csv, import_teammate_json


def test_import_teammate_csv_accepts_valid_rows(tmp_path: Path) -> None:
    csv_path = tmp_path / "teammate.csv"
    csv_path.write_text(
        "source_name,source_listing_id,source_url,observed_at,city,address_text,latitude,"
        "longitude,price_rub,total_area_m2,rooms,floor,floors_total,building_year,"
        "property_type,description\n"
        "teammate_file,t-1,https://example.test/1,2026-05-31T10:00:00+00:00,"
        "Moscow,Test address,55.75,37.62,12000000,48.5,2,4,12,2010,"
        "apartment,Sunny flat\n",
        encoding="utf-8",
    )

    batch = import_teammate_csv(csv_path)

    assert batch.records_seen == 1
    assert len(batch.raw_listings) == 1
    assert len(batch.normalized_listings) == 1
    assert len(batch.rejected_listings) == 0
    assert batch.normalized_listings[0].source_listing_id == "t-1"
    assert batch.normalized_listings[0].has_coordinates is True


def test_import_teammate_csv_generates_missing_listing_id(tmp_path: Path) -> None:
    csv_path = tmp_path / "teammate.csv"
    csv_path.write_text(
        "source_name,source_listing_id,source_url,observed_at,city,price_rub,"
        "total_area_m2,rooms,property_type\n"
        "teammate_file,,https://example.test/1,2026-05-31T10:00:00+00:00,"
        "Moscow,12000000,48.5,2,apartment\n",
        encoding="utf-8",
    )

    batch = import_teammate_csv(csv_path)

    assert batch.normalized_listings[0].source_listing_id.startswith("generated_")


def test_import_teammate_csv_rejects_missing_required_fields(tmp_path: Path) -> None:
    csv_path = tmp_path / "teammate.csv"
    csv_path.write_text(
        "source_name,source_listing_id,observed_at,city,price_rub,total_area_m2,"
        "rooms,property_type\n"
        "teammate_file,t-1,2026-05-31T10:00:00+00:00,Moscow,,48.5,2,"
        "apartment\n",
        encoding="utf-8",
    )

    batch = import_teammate_csv(csv_path)

    assert len(batch.normalized_listings) == 0
    assert len(batch.rejected_listings) == 1
    assert "price_rub" in batch.rejected_listings[0].reason


def test_import_teammate_json_accepts_contract_rows(tmp_path: Path) -> None:
    json_path = tmp_path / "teammate.json"
    json_path.write_text(
        """
        [
          {
            "source_name": "cian",
            "source_listing_id": "330398493",
            "source_url": "https://www.cian.ru/sale/flat/330398493/",
            "observed_at": "2026-05-14T09:37:52.268794+00:00",
            "city": "Moscow",
            "address_text": "Test address",
            "latitude": 55.75,
            "longitude": 37.62,
            "price_rub": 12000000,
            "total_area_m2": 48.5,
            "rooms": 2,
            "floor": 4,
            "floors_total": 12,
            "building_year": 2010,
            "property_type": "apartment",
            "description": "Sunny flat"
          },
          {
            "source_name": "cian",
            "source_listing_id": "bad-1",
            "observed_at": "2026-05-14T09:37:52.268794+00:00",
            "city": null,
            "price_rub": 9000000,
            "total_area_m2": 40.0,
            "rooms": 1,
            "property_type": "apartment"
          }
        ]
        """,
        encoding="utf-8",
    )

    batch = import_teammate_json(json_path)

    assert batch.records_seen == 2
    assert len(batch.raw_listings) == 1
    assert len(batch.normalized_listings) == 1
    assert len(batch.rejected_listings) == 1
    assert batch.normalized_listings[0].source_listing_id == "330398493"
    assert batch.normalized_listings[0].has_coordinates is True
    assert "city" in batch.rejected_listings[0].reason
