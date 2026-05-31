import os

import pandas as pd

import streamlit as st
from services.streamlit.api_client import fetch_dashboard_data

API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000")

st.set_page_config(page_title="RealtyScope", page_icon="RS", layout="wide")

st.title("RealtyScope")
st.caption("Phase 3.5 real-data dashboard")

data = fetch_dashboard_data(API_BASE_URL)

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
    st.dataframe(pd.DataFrame([latest_run]), hide_index=True, use_container_width=True)

st.subheader("Listing preview")
if data.listings:
    st.dataframe(pd.DataFrame(data.listings), hide_index=True, use_container_width=True)
else:
    st.info("No persisted listings available yet.")
