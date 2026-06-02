import os

import pandas as pd

import streamlit as st
from services.streamlit.api_client import fetch_dashboard_data, request_prediction

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
    "latest_observation_price_per_m2": 300_000.0,
    "latest_observation_price_rub": 18_000_000.0,
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
st.caption("Phase 3.5 real-data dashboard")

row_limit = st.sidebar.selectbox("Rows", [25, 100, 500, 1000], index=3)
data = fetch_dashboard_data(API_BASE_URL, limit=row_limit)

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

st.subheader("Listing preview")
if data.listings:
    total = data.listings_total or stats.get("listings_total") or len(data.listings)
    st.caption(f"Showing {len(data.listings)} of {total} listings")
    st.dataframe(pd.DataFrame(data.listings), hide_index=True, width="stretch")
else:
    st.info("No persisted listings available yet.")

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
        latest_observation_price_rub = st.number_input(
            "latest_observation_price_rub", min_value=0.0, value=18_000_000.0, step=500_000.0
        )
    with input_columns[2]:
        latest_observation_price_per_m2 = st.number_input(
            "latest_observation_price_per_m2", min_value=0.0, value=300_000.0, step=10_000.0
        )
        latitude = st.number_input("latitude", value=55.75, step=0.01, format="%.6f")
        longitude = st.number_input("longitude", value=37.61, step=0.01, format="%.6f")
    submitted = st.form_submit_button("Run baseline prediction")

if submitted:
    features = dict(BASELINE_FEATURE_DEFAULTS)
    features.update(
        {
            "building_year": building_year,
            "floor": floor,
            "floors_total": floors_total,
            "latest_observation_price_per_m2": latest_observation_price_per_m2,
            "latest_observation_price_rub": latest_observation_price_rub,
            "latitude": latitude,
            "longitude": longitude,
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
