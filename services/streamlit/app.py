import streamlit as st

st.set_page_config(page_title="RealtyScope", page_icon="🏠", layout="wide")

st.title("RealtyScope")
st.caption("Phase 1 scaffold")

st.write(
    "RealtyScope will estimate Moscow apartment sale prices using Domclick listings, "
    "OpenStreetMap enrichment, FastAPI, MLflow, Redis, and PostgreSQL."
)

st.info("The full dashboard pages will be implemented after ingestion, database, and model phases.")
