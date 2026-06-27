import os
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "src"))

from services.streamlit.api_client import fetch_dashboard_data, fetch_monitoring_data  # noqa: E402
from services.streamlit.app import (  # noqa: E402
    API_BASE_URL,
    API_TIMEOUT_SECONDS,
    _build_payload,
    _workstation_html,
)

EXPECTED_LISTINGS_TOTAL = 17_287
EXPECTED_SOURCE_COUNTS = {"cian": 2_436, "domclick": 14_851}


def validate_static_audit_payload(payload: dict, *, require_api: bool) -> None:
    if not require_api:
        return
    mode = payload.get("mode")
    if mode != "api":
        raise SystemExit(f"Static audit requires API mode, got {mode!r}")
    stats = payload.get("stats") or {}
    source_counts = stats.get("source_counts")
    if not isinstance(source_counts, dict) or not source_counts:
        raise SystemExit("Static audit requires real source_counts from the API payload")
    listings_total = int(stats.get("listings_total") or 0)
    if listings_total != EXPECTED_LISTINGS_TOTAL:
        raise SystemExit(
            f"Static audit requires the full real dataset, got listings_total={listings_total}"
        )
    normalized_counts = {
        str(name).lower(): int(count)
        for name, count in source_counts.items()
        if isinstance(count, int | float)
    }
    if normalized_counts != EXPECTED_SOURCE_COUNTS:
        raise SystemExit(
            "Static audit requires full real source_counts "
            f"{EXPECTED_SOURCE_COUNTS}, got {normalized_counts}"
        )
    model = payload.get("model") or {}
    data_freshness = model.get("data_freshness") if isinstance(model, dict) else None
    if not isinstance(data_freshness, dict) or not data_freshness.get("status"):
        raise SystemExit("Static audit requires model.data_freshness from the API payload")
    if data_freshness.get("status") == "unknown":
        raise SystemExit("Static audit requires known model.data_freshness status")


def build_payload_with_retries(*, require_api: bool) -> dict:
    last_payload: dict | None = None
    attempts = 3 if require_api else 1
    for attempt in range(1, attempts + 1):
        dashboard = fetch_dashboard_data(
            API_BASE_URL,
            analytics_limit=2000,
            analytics_max_listings=20_000,
            timeout=API_TIMEOUT_SECONDS,
        )
        monitoring = fetch_monitoring_data(API_BASE_URL, timeout=API_TIMEOUT_SECONDS)
        payload = _build_payload(data=dashboard, monitoring=monitoring)
        try:
            validate_static_audit_payload(payload, require_api=require_api)
        except SystemExit:
            last_payload = payload
            if attempt >= attempts:
                raise
            time.sleep(1.5)
            continue
        return payload
    assert last_payload is not None
    validate_static_audit_payload(last_payload, require_api=require_api)
    return last_payload


def main() -> None:
    require_api = os.environ.get("STATIC_AUDIT_ALLOW_OFFLINE") != "1"
    payload = build_payload_with_retries(require_api=require_api)
    output_path = Path("output/playwright/realtyscope-static-audit.html")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(_workstation_html(payload), encoding="utf-8")
    stats = payload.get("stats", {})
    print(payload.get("mode"), stats.get("listings_total"), stats.get("source_counts"))
    print(output_path)


if __name__ == "__main__":
    main()
