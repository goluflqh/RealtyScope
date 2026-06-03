from pathlib import Path

STREAMLIT_APP = Path("services/streamlit/app.py")
STREAMLIT_DOCKERFILE = Path("services/streamlit/Dockerfile")


def test_streamlit_app_file_exists() -> None:
    assert STREAMLIT_APP.exists()


def test_streamlit_dockerfile_keeps_repo_root_on_pythonpath() -> None:
    content = STREAMLIT_DOCKERFILE.read_text(encoding="utf-8")

    assert "PYTHONPATH=/app" in content


def test_streamlit_app_declares_real_data_dashboard_slice() -> None:
    content = STREAMLIT_APP.read_text(encoding="utf-8")

    assert "RealtyScope" in content
    assert "st.set_page_config" in content
    assert "fetch_dashboard_data" in content
    assert "st.metric" in content
    assert "st.dataframe" in content
    assert "Phase 1 scaffold" not in content


def test_streamlit_app_declares_baseline_prediction_scaffold() -> None:
    content = STREAMLIT_APP.read_text(encoding="utf-8")

    assert "request_prediction" in content
    assert "Baseline prediction" in content
    assert "st.form" in content
    assert "Run baseline prediction" in content
    assert "model_version" in content
    assert "caveat" in content


def test_streamlit_app_declares_monitoring_and_model_insights() -> None:
    content = STREAMLIT_APP.read_text(encoding="utf-8")

    assert "fetch_monitoring_data" in content
    assert "Monitoring" in content
    assert "Model insights" in content
    assert "feature_importance" in content
    assert "latest_observation_price_rub" not in content
    assert "latest_observation_price_per_m2" not in content


def test_streamlit_app_declares_data_explorer_filters() -> None:
    content = STREAMLIT_APP.read_text(encoding="utf-8")

    assert "Data explorer filters" in content
    assert "Min price (RUB)" in content
    assert "Max price (RUB)" in content
    assert "Min area (m2)" in content
    assert "Max area (m2)" in content
    assert "Rooms" in content
    assert "Source" in content
    assert "Address search" in content
    assert "filters=listing_filters" in content


def test_streamlit_app_declares_reviewer_visuals_and_map_attribution() -> None:
    content = STREAMLIT_APP.read_text(encoding="utf-8")

    assert "Reviewer visuals" in content
    assert "Price distribution" in content
    assert "Median price by rooms" in content
    assert "Listing map" in content
    assert "OpenStreetMap contributors" in content
    assert "st.bar_chart" in content
    assert "st.map" in content
