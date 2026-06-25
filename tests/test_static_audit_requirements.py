import pytest
from scripts.playwright import generate_static_audit as audit


def test_static_audit_requires_api_payload_when_requested() -> None:
    with pytest.raises(SystemExit, match="Static audit requires API mode"):
        audit.validate_static_audit_payload(
            {"mode": "offline", "stats": {"listings_total": 1000}},
            require_api=True,
        )


def test_static_audit_requires_full_source_counts_when_requested() -> None:
    with pytest.raises(SystemExit, match="source_counts"):
        audit.validate_static_audit_payload(
            {"mode": "api", "stats": {"listings_total": 16_512}},
            require_api=True,
        )


def test_static_audit_accepts_current_full_api_payload_shape() -> None:
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
