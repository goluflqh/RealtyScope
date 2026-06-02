import json
from pathlib import Path

NOTEBOOK_PATH = Path("notebooks/phase4_eda_observations.ipynb")
EN_DOC_PATH = Path("docs/data/phase4-eda-observations.md")
VI_DOC_PATH = Path("docs/data/phase4-eda-observations.vi.md")


def _notebook_source() -> str:
    notebook = json.loads(NOTEBOOK_PATH.read_text(encoding="utf-8"))
    return "\n".join(
        "".join(cell.get("source", []))
        for cell in notebook["cells"]
        if cell.get("cell_type") in {"markdown", "code"}
    )


def test_phase4_eda_observation_notebook_has_required_sections() -> None:
    source = _notebook_source()

    assert "Phase 4" in source
    assert "DATABASE_URL" in source
    assert "listing_observations" in source
    assert "latest listing distributions" in source
    assert "observation count and price-change analysis" in source
    assert "coordinate coverage" in source
    assert "candidate OSM enrichment readiness" in source
    assert "naive baseline target distribution" in source
    assert "Kết luận tiếng Việt" in source


def test_phase4_eda_notebook_has_markdown_and_code_cells() -> None:
    notebook = json.loads(NOTEBOOK_PATH.read_text(encoding="utf-8"))
    cell_types = {cell["cell_type"] for cell in notebook["cells"]}

    assert {"markdown", "code"}.issubset(cell_types)
    assert notebook["metadata"]["kernelspec"]["name"] == "python3"


def test_phase4_eda_docs_record_observation_limits_and_next_steps() -> None:
    english = EN_DOC_PATH.read_text(encoding="utf-8")
    vietnamese = VI_DOC_PATH.read_text(encoding="utf-8")

    assert "2000" in english
    assert "listing_observations" in english
    assert "0 price changes" in english
    assert "OpenStreetMap" in english
    assert "naive baseline" in english

    assert "2000" in vietnamese
    assert "listing_observations" in vietnamese
    assert "0 biến động giá" in vietnamese
    assert "OpenStreetMap" in vietnamese
    assert "baseline naive" in vietnamese
