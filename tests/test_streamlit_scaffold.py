from pathlib import Path


STREAMLIT_APP = Path("services/streamlit/app.py")


def test_streamlit_app_file_exists() -> None:
    assert STREAMLIT_APP.exists()


def test_streamlit_app_declares_realtyscope_title() -> None:
    content = STREAMLIT_APP.read_text(encoding="utf-8")

    assert "RealtyScope" in content
    assert "st.set_page_config" in content
    assert "Phase 1 scaffold" in content
