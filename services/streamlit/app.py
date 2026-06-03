import os

import pandas as pd

import streamlit as st
from services.streamlit.api_client import (
    fetch_dashboard_data,
    fetch_monitoring_data,
    request_prediction,
)
from services.streamlit.dashboard_charts import (
    listing_chart_frame,
    map_points_frame,
    price_band_frame,
    room_summary_frame,
)

API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000")
BASELINE_FEATURE_DEFAULTS = {
    "building_year": 2018.0,
    "building_year_missing": 0.0,
    "coordinates_missing": 0.0,
    "floor": 5.0,
    "floor_missing": 0.0,
    "floors_total": 20.0,
    "floors_total_missing": 0.0,
    "healthcare_count_1000m": 0.0,
    "latitude": 55.75,
    "longitude": 37.61,
    "nearest_transport_m": 0.0,
    "nearest_transport_m_missing": 1.0,
    "observation_count": 1.0,
    "observation_missing": 0.0,
    "osm_missing": 1.0,
    "parks_count_1000m": 0.0,
    "property_type_apartment": 1.0,
    "rooms": 2.0,
    "schools_count_1000m": 0.0,
    "shops_count_1000m": 0.0,
    "total_area_m2": 60.0,
    "transport_count_1000m": 0.0,
    "transport_count_500m": 0.0,
}

st.set_page_config(page_title="RealtyScope", page_icon="RS", layout="wide")

st.title("RealtyScope")
st.caption("Phase 5 monitoring and non-leaky baseline dashboard")

row_limit = st.sidebar.selectbox("Rows", [25, 100, 500, 1000], index=3)
st.sidebar.subheader("Data explorer filters")
min_price_rub = st.sidebar.number_input("Min price (RUB)", min_value=0, value=0, step=500_000)
max_price_rub = st.sidebar.number_input("Max price (RUB)", min_value=0, value=0, step=500_000)
min_area_m2 = st.sidebar.number_input("Min area (m2)", min_value=0.0, value=0.0, step=5.0)
max_area_m2 = st.sidebar.number_input("Max area (m2)", min_value=0.0, value=0.0, step=5.0)
rooms_choice = st.sidebar.selectbox("Rooms", ["Any", 1, 2, 3, 4, 5])
source_name = st.sidebar.text_input("Source", value="")
address_search = st.sidebar.text_input("Address search", value="")
listing_filters = {
    "min_price_rub": min_price_rub or None,
    "max_price_rub": max_price_rub or None,
    "min_area_m2": min_area_m2 or None,
    "max_area_m2": max_area_m2 or None,
    "rooms": rooms_choice if isinstance(rooms_choice, int) else None,
    "source_name": source_name,
    "search": address_search,
}

data = fetch_dashboard_data(API_BASE_URL, limit=row_limit, filters=listing_filters)
monitoring = fetch_monitoring_data(API_BASE_URL)

if data.errors:
    st.warning("Data API is unavailable.")

stats = data.stats or {}
metric_columns = st.columns(4)
with metric_columns[0]:
    st.metric("Listings", stats.get("listings_total", 0))
with metric_columns[1]:
    st.metric("ML-ready", stats.get("ml_ready_listings", 0))
with metric_columns[2]:
    st.metric("Rejected", stats.get("rejected_listings_total", 0))
with metric_columns[3]:
    st.metric("Runs", stats.get("ingestion_runs_total", 0))

latest_run = stats.get("latest_ingestion_run")
if isinstance(latest_run, dict):
    st.subheader("Latest ingestion run")
    st.dataframe(pd.DataFrame([latest_run]), hide_index=True, width="stretch")

st.subheader("Monitoring")
if monitoring.errors:
    st.warning("Monitoring API is unavailable.")
    for error in monitoring.errors:
        st.caption(error)
monitoring_status = monitoring.status or {}
status_columns = st.columns(3)
with status_columns[0]:
    st.metric("API status", monitoring_status.get("status", "unknown"))
with status_columns[1]:
    st.metric("Environment", monitoring_status.get("environment", "unknown"))
with status_columns[2]:
    recent_errors = monitoring_status.get("recent_errors")
    st.metric("Recent errors", len(recent_errors) if isinstance(recent_errors, list) else 0)
data_quality = monitoring_status.get("data_quality")
if isinstance(data_quality, dict):
    latest_successful_run = data_quality.get("latest_successful_ingestion_run")
    if isinstance(latest_successful_run, dict):
        collection_columns = st.columns(3)
        with collection_columns[0]:
            st.metric(
                "Last successful collection",
                latest_successful_run.get("finished_at")
                or latest_successful_run.get("started_at")
                or "unknown",
            )
        with collection_columns[1]:
            st.metric("Collection source", latest_successful_run.get("source_name", "unknown"))
        with collection_columns[2]:
            st.metric("Records seen", latest_successful_run.get("records_seen", 0))
if isinstance(recent_errors, list) and recent_errors:
    st.dataframe(pd.DataFrame(recent_errors), hide_index=True, width="stretch")

st.subheader("Listing preview")
if data.listings:
    total = data.listings_total or stats.get("listings_total") or len(data.listings)
    st.caption(f"Showing {len(data.listings)} of {total} listings")
    st.dataframe(pd.DataFrame(data.listings), hide_index=True, width="stretch")
else:
    st.info("No persisted listings available yet.")

st.subheader("Reviewer visuals")
chart_frame = listing_chart_frame(data.listings)
if chart_frame.empty:
    st.info("No listing data available for charts yet.")
else:
    price_bands = price_band_frame(chart_frame)
    room_summary = room_summary_frame(chart_frame)
    visual_columns = st.columns(2)
    with visual_columns[0]:
        st.caption("Price distribution")
        if price_bands.empty:
            st.info("No price data available.")
        else:
            st.bar_chart(price_bands.set_index("price_band"))
    with visual_columns[1]:
        st.caption("Median price by rooms")
        if room_summary.empty:
            st.info("No room summary available.")
        else:
            st.bar_chart(room_summary.set_index("rooms")[["median_price_rub"]])

    map_points = map_points_frame(chart_frame)
    st.caption("Listing map")
    if map_points.empty:
        st.info("No coordinates available for the current listing slice.")
    else:
        st.map(map_points)
        st.caption(
            "Map uses persisted listing coordinates and makes no live OSM/Overpass calls. "
            "© OpenStreetMap contributors."
        )

st.subheader("Baseline prediction")
with st.form("baseline-prediction-form"):
    input_columns = st.columns(3)
    with input_columns[0]:
        total_area_m2 = st.number_input("total_area_m2", min_value=1.0, value=60.0, step=1.0)
        rooms = st.number_input("rooms", min_value=1.0, value=2.0, step=1.0)
        floor = st.number_input("floor", min_value=0.0, value=5.0, step=1.0)
    with input_columns[1]:
        floors_total = st.number_input("floors_total", min_value=1.0, value=20.0, step=1.0)
        building_year = st.number_input(
            "building_year", min_value=1800.0, max_value=2035.0, value=2018.0, step=1.0
        )
        observation_count = st.number_input("observation_count", min_value=0.0, value=1.0, step=1.0)
    with input_columns[2]:
        latitude = st.number_input("latitude", value=55.75, step=0.01, format="%.6f")
        longitude = st.number_input("longitude", value=37.61, step=0.01, format="%.6f")
        nearest_transport_m = st.number_input(
            "nearest_transport_m", min_value=0.0, value=0.0, step=50.0
        )
    submitted = st.form_submit_button("Run baseline prediction")

if submitted:
    features = dict(BASELINE_FEATURE_DEFAULTS)
    features.update(
        {
            "building_year": building_year,
            "floor": floor,
            "floors_total": floors_total,
            "latitude": latitude,
            "longitude": longitude,
            "nearest_transport_m": nearest_transport_m,
            "nearest_transport_m_missing": 0.0 if nearest_transport_m else 1.0,
            "observation_count": observation_count,
            "rooms": rooms,
            "total_area_m2": total_area_m2,
        }
    )
    prediction = request_prediction(API_BASE_URL, features=features)
    if prediction.errors:
        st.warning("Prediction API is unavailable.")
        for error in prediction.errors:
            st.caption(error)
    elif prediction.result:
        result = prediction.result
        predicted_price = result.get("predicted_price_rub")
        if isinstance(predicted_price, int | float):
            st.metric("Predicted price (RUB)", f"{predicted_price:,.0f}")
        st.caption(
            f"model_version: {result.get('model_version')} | "
            f"feature_version: {result.get('feature_version')}"
        )
        caveat = result.get("caveat")
        if isinstance(caveat, str):
            st.caption(caveat)
        metrics_summary = result.get("metrics_summary")
        if isinstance(metrics_summary, dict):
            st.dataframe(pd.DataFrame([metrics_summary]), hide_index=True, width="stretch")

st.subheader("Model insights")
model_metadata = monitoring.model_metadata or monitoring_status.get("model")
if isinstance(model_metadata, dict):
    st.caption(
        f"model_version: {model_metadata.get('model_version')} | "
        f"feature_version: {model_metadata.get('feature_version')}"
    )
    metrics_summary = model_metadata.get("metrics_summary")
    if isinstance(metrics_summary, dict) and metrics_summary:
        st.dataframe(pd.DataFrame([metrics_summary]), hide_index=True, width="stretch")
    feature_importance = model_metadata.get("feature_importance")
    if isinstance(feature_importance, list) and feature_importance:
        st.dataframe(pd.DataFrame(feature_importance), hide_index=True, width="stretch")
else:
    st.info("Model metadata is not available yet.")
