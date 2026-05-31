import json
from pathlib import Path

NOTEBOOK_PATH = Path("notebooks/phase3_eda_skeleton.ipynb")


def test_phase3_eda_notebook_skeleton_exists_and_targets_persisted_data() -> None:
    notebook = json.loads(NOTEBOOK_PATH.read_text(encoding="utf-8"))
    source = "\n".join(
        "".join(cell.get("source", []))
        for cell in notebook["cells"]
        if cell.get("cell_type") in {"markdown", "code"}
    )

    assert "Phase 3" in source
    assert "DATABASE_URL" in source
    assert "listings" in source
    assert "ingestion_runs" in source
    assert "rejected_listings" in source
    assert "missing values" in source
    assert "outliers" in source
    assert "Không ghi kết luận cuối cùng" in source


def test_phase3_eda_notebook_has_markdown_and_code_cells() -> None:
    notebook = json.loads(NOTEBOOK_PATH.read_text(encoding="utf-8"))
    cell_types = {cell["cell_type"] for cell in notebook["cells"]}

    assert {"markdown", "code"}.issubset(cell_types)
    assert notebook["metadata"]["kernelspec"]["name"] == "python3"
