import os
import subprocess
import sys
from pathlib import Path

import pytest
from scripts.playwright import generate_static_audit as audit


def test_static_audit_requires_api_payload_when_requested() -> None:
    with pytest.raises(SystemExit, match="Static audit requires API mode"):
        audit.validate_static_audit_payload(
            {"mode": "offline", "stats": {"listings_total": 1000}},
            require_api=True,
        )


def test_static_audit_script_bootstraps_src_import_path() -> None:
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import runpy; "
                "runpy.run_path('scripts/playwright/generate_static_audit.py', "
                "run_name='static_audit_import_test')"
            ),
        ],
        cwd=audit.REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr


def test_static_audit_requires_full_source_counts_when_requested() -> None:
    with pytest.raises(SystemExit, match="source_counts"):
        audit.validate_static_audit_payload(
            {"mode": "api", "stats": {"listings_total": 16_512}},
            require_api=True,
        )


def test_static_audit_requires_current_full_source_coverage_when_requested() -> None:
    with pytest.raises(SystemExit, match="full real dataset"):
        audit.validate_static_audit_payload(
            {
                "mode": "api",
                "stats": {
                    "listings_total": 16_512,
                    "source_counts": {"cian": 2_436, "domclick": 14_076},
                },
            },
            require_api=True,
        )


def test_static_audit_requires_model_data_freshness_when_requested() -> None:
    with pytest.raises(SystemExit, match="model.data_freshness"):
        audit.validate_static_audit_payload(
            {
                "mode": "api",
                "stats": {
                    "listings_total": 17_287,
                    "source_counts": {"cian": 2_436, "domclick": 14_851},
                },
                "model": {
                    "status": "ready",
                    "metrics": {"rows_total": 17_046},
                },
            },
            require_api=True,
        )


def test_static_audit_accepts_current_full_api_payload_shape() -> None:
    audit.validate_static_audit_payload(
        {
            "mode": "api",
            "stats": {
                "listings_total": 17_287,
                "source_counts": {"cian": 2_436, "domclick": 14_851},
            },
            "model": {
                "status": "ready",
                "data_freshness": {
                    "status": "validated_snapshot",
                    "model_rows_total": 17_287,
                    "current_listings_total": 17_287,
                    "row_delta": 0,
                    "requires_retrain": False,
                },
            },
        },
        require_api=True,
    )


def test_static_audit_ui_contract_mentions_manual_refresh_and_detail_drawer() -> None:
    content = Path("services/streamlit/app.py").read_text(encoding="utf-8")

    assert "function refreshCurrentData()" in content
    assert "setInterval(async ()" not in content
    assert "listingDetailDrawer" in content
    assert "status-badge status-ok" in content
    assert "const maxLogRows = 40" in content
    assert "Нет данных о факторах" in content
