import pandas as pd
from services.streamlit.dashboard_charts import (
    listing_chart_frame,
    map_points_frame,
    price_band_frame,
    room_summary_frame,
)


def test_listing_chart_frame_coerces_numeric_fields_and_derives_price_per_m2() -> None:
    frame = listing_chart_frame(
        [
            {
                "id": 1,
                "address_text": "Moscow, API Street, 10",
                "price_rub": 18_000_000,
                "total_area_m2": 60,
                "rooms": 2,
                "latitude": 55.751,
                "longitude": 37.618,
            },
            {
                "id": 2,
                "address_text": "Moscow, Garden Ring, 25",
                "price_rub": "31000000",
                "total_area_m2": "80",
                "rooms": "3",
                "latitude": "55.76",
                "longitude": "37.62",
            },
            {
                "id": 3,
                "address_text": "Incomplete row",
                "price_rub": None,
                "total_area_m2": 0,
                "rooms": None,
                "latitude": None,
                "longitude": None,
            },
        ]
    )

    assert list(frame.columns) == [
        "id",
        "address_text",
        "price_rub",
        "total_area_m2",
        "rooms",
        "latitude",
        "longitude",
        "price_per_m2",
    ]
    assert frame.loc[0, "price_per_m2"] == 300_000
    assert frame.loc[1, "price_per_m2"] == 387_500
    assert pd.isna(frame.loc[2, "price_per_m2"])


def test_price_band_frame_counts_listings_by_five_million_rub_bands() -> None:
    chart_frame = listing_chart_frame(
        [
            {"price_rub": 12_500_000, "total_area_m2": 50, "rooms": 1},
            {"price_rub": 18_000_000, "total_area_m2": 60, "rooms": 2},
            {"price_rub": 31_000_000, "total_area_m2": 80, "rooms": 3},
        ]
    )

    bands = price_band_frame(chart_frame)

    assert bands.to_dict(orient="records") == [
        {"price_band": "10-15M", "listings": 1},
        {"price_band": "15-20M", "listings": 1},
        {"price_band": "30-35M", "listings": 1},
    ]


def test_room_summary_frame_reports_counts_and_medians_by_room_count() -> None:
    chart_frame = listing_chart_frame(
        [
            {"price_rub": 18_000_000, "total_area_m2": 60, "rooms": 2},
            {"price_rub": 22_000_000, "total_area_m2": 80, "rooms": 2},
            {"price_rub": 31_000_000, "total_area_m2": 100, "rooms": 3},
        ]
    )

    summary = room_summary_frame(chart_frame)

    assert summary.to_dict(orient="records") == [
        {
            "rooms": 2,
            "listings": 2,
            "median_price_rub": 20_000_000.0,
            "median_price_per_m2": 287_500.0,
        },
        {
            "rooms": 3,
            "listings": 1,
            "median_price_rub": 31_000_000.0,
            "median_price_per_m2": 310_000.0,
        },
    ]


def test_map_points_frame_keeps_only_rows_with_coordinates() -> None:
    chart_frame = listing_chart_frame(
        [
            {
                "id": 1,
                "address_text": "Moscow, API Street, 10",
                "price_rub": 18_000_000,
                "total_area_m2": 60,
                "rooms": 2,
                "latitude": 55.751,
                "longitude": 37.618,
            },
            {
                "id": 2,
                "address_text": "No coordinates",
                "price_rub": 12_500_000,
                "total_area_m2": 44,
                "rooms": 1,
            },
        ]
    )

    points = map_points_frame(chart_frame)

    assert points.to_dict(orient="records") == [
        {
            "lat": 55.751,
            "lon": 37.618,
            "price_rub": 18_000_000.0,
            "rooms": 2.0,
            "address_text": "Moscow, API Street, 10",
        }
    ]
