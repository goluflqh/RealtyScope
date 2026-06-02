from pathlib import Path

STREAMLIT_APP = Path("services/streamlit/app.py")


def test_streamlit_app_file_exists() -> None:
    assert STREAMLIT_APP.exists()


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
