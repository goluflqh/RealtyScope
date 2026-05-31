from pathlib import Path

from realtyscope.ingestion.teammate_import import import_teammate_csv


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
