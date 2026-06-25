import importlib.util
from pathlib import Path

import pytest


def _load_static_audit_module():
    module_path = Path("output/playwright/generate_static_audit.py")
    spec = importlib.util.spec_from_file_location("generate_static_audit", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_static_audit_requires_api_payload_when_requested() -> None:
    audit = _load_static_audit_module()

    with pytest.raises(SystemExit, match="Static audit requires API mode"):
        audit.validate_static_audit_payload(
            {"mode": "offline", "stats": {"listings_total": 1000}},
            require_api=True,
        )


def test_static_audit_requires_full_source_counts_when_requested() -> None:
    audit = _load_static_audit_module()

    with pytest.raises(SystemExit, match="source_counts"):
        audit.validate_static_audit_payload(
            {"mode": "api", "stats": {"listings_total": 16_512}},
            require_api=True,
        )


def test_static_audit_accepts_current_full_api_payload_shape() -> None:
    audit = _load_static_audit_module()

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
