from __future__ import annotations

from typing import Any

import pandas as pd

CHART_COLUMNS = [
    "id",
    "address_text",
    "price_rub",
    "total_area_m2",
    "rooms",
    "latitude",
    "longitude",
    "price_per_m2",
]
PRICE_BAND_STEP_RUB = 5_000_000


def listing_chart_frame(listings: list[dict[str, Any]]) -> pd.DataFrame:
    frame = pd.DataFrame(listings)
    if frame.empty:
        return pd.DataFrame(columns=CHART_COLUMNS)

    for column in ["id", "price_rub", "total_area_m2", "rooms", "latitude", "longitude"]:
        if column not in frame:
            frame[column] = pd.NA
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    if "address_text" not in frame:
        frame["address_text"] = ""

    has_price_and_area = (frame["price_rub"] > 0) & (frame["total_area_m2"] > 0)
    frame["price_per_m2"] = pd.NA
    frame.loc[has_price_and_area, "price_per_m2"] = (
        frame.loc[has_price_and_area, "price_rub"] / frame.loc[has_price_and_area, "total_area_m2"]
    )
    return frame[CHART_COLUMNS]


def price_band_frame(chart_frame: pd.DataFrame) -> pd.DataFrame:
    prices = chart_frame.get("price_rub", pd.Series(dtype="float64")).dropna()
    prices = prices[prices > 0]
    if prices.empty:
        return pd.DataFrame(columns=["price_band", "listings"])

    band_starts = ((prices // PRICE_BAND_STEP_RUB) * PRICE_BAND_STEP_RUB).astype(int)
    counts = band_starts.value_counts().sort_index()
    return pd.DataFrame(
        [
            {
                "price_band": _price_band_label(band_start),
                "listings": int(count),
            }
            for band_start, count in counts.items()
        ]
    )


def room_summary_frame(chart_frame: pd.DataFrame) -> pd.DataFrame:
    required = chart_frame.dropna(subset=["rooms", "price_rub", "price_per_m2"])
    if required.empty:
        return pd.DataFrame(
            columns=["rooms", "listings", "median_price_rub", "median_price_per_m2"]
        )

    grouped = (
        required.groupby("rooms", as_index=False)
        .agg(
            listings=("price_rub", "count"),
            median_price_rub=("price_rub", "median"),
            median_price_per_m2=("price_per_m2", "median"),
        )
        .sort_values("rooms")
    )
    grouped["rooms"] = grouped["rooms"].astype(int)
    return grouped.reset_index(drop=True)


def map_points_frame(chart_frame: pd.DataFrame) -> pd.DataFrame:
    required = chart_frame.dropna(subset=["latitude", "longitude"])
    if required.empty:
        return pd.DataFrame(columns=["lat", "lon", "price_rub", "rooms", "address_text"])

    points = required.rename(columns={"latitude": "lat", "longitude": "lon"})[
        ["lat", "lon", "price_rub", "rooms", "address_text"]
    ].copy()
    return points.reset_index(drop=True)


def _price_band_label(band_start: int) -> str:
    start_millions = band_start // 1_000_000
    end_millions = (band_start + PRICE_BAND_STEP_RUB) // 1_000_000
    return f"{start_millions}-{end_millions}M"
