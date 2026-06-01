import os

import pandas as pd

import streamlit as st
from services.streamlit.api_client import fetch_dashboard_data

API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000")

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
