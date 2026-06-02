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
