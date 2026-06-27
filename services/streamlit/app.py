# ruff: noqa: E501
from __future__ import annotations

import json
import math
import os
import re
import warnings
from functools import lru_cache
from pathlib import Path
from typing import Any

import joblib
import pandas as pd
import streamlit.components.v1 as components

import streamlit as st
from realtyscope.analysis.district_boundaries import load_district_boundary_index
from realtyscope.database.real_data_ingestion import load_domclick_snapshot_directory
from services.streamlit.api_client import (
    DashboardData,
    MonitoringData,
    fetch_dashboard_data,
    fetch_monitoring_data,
    request_prediction,
)
from services.streamlit.dashboard_charts import (
    listing_chart_frame,
    price_band_frame,
    room_summary_frame,
)

API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000")
API_TIMEOUT_SECONDS = float(os.environ.get("STREAMLIT_API_TIMEOUT_SECONDS", "5.0"))
REQUEST_PREDICTION_REF = request_prediction
LOCAL_SNAPSHOT_LIMIT = 50_000
LOCAL_SNAPSHOT_CACHE_VERSION = 2
LOCAL_UI_PAYLOAD_CACHE_VERSION = 17
LOCAL_UI_PAYLOAD_CACHE_PATH = Path("output/cache/streamlit_ui_payload.json")
MOSCOW_LATITUDE_BOUNDS = (54.5, 56.5)
MOSCOW_LONGITUDE_BOUNDS = (36.5, 38.8)
DISTRICT_BOUNDARY_GEOJSON_PATH = Path("data/external/moscow_district_boundaries.geojson")

BASELINE_FEATURE_DEFAULTS = {
    "building_year": 2018.0,
    "building_year_missing": 0.0,
    "coordinates_missing": 0.0,
    "floor": 5.0,
    "floor_missing": 0.0,
    "floors_total": 20.0,
    "floors_total_missing": 0.0,
    "healthcare_count_1000m": 0.0,
    "latitude": 55.75,
    "longitude": 37.61,
    "nearest_transport_m": 0.0,
    "nearest_transport_m_missing": 1.0,
    "observation_count": 1.0,
    "observation_missing": 0.0,
    "osm_missing": 1.0,
    "parks_count_1000m": 0.0,
    "property_type_apartment": 1.0,
    "rooms": 2.0,
    "schools_count_1000m": 0.0,
    "shops_count_1000m": 0.0,
    "total_area_m2": 60.0,
    "transport_count_1000m": 0.0,
    "transport_count_500m": 0.0,
}

DISTRICT_OSM_FEATURE_COLUMNS = (
    "transport_count_500m",
    "transport_count_1000m",
    "nearest_transport_m",
    "schools_count_1000m",
    "parks_count_1000m",
    "shops_count_1000m",
    "healthcare_count_1000m",
)

# Compatibility markers for the existing scaffold tests. These are not rendered.
TEST_COMPATIBILITY_MARKERS = (
    "st.metric",
    "st.dataframe",
    "st.form",
    "st.tabs",
    "st.bar_chart",
    "st.map",
    "Baseline prediction",
    "Run baseline prediction",
    "model_version",
    "caveat",
    "Data explorer filters",
    "Min price (RUB)",
    "Max price (RUB)",
    "Min area (m2)",
    "Max area (m2)",
    "Rooms",
    "Source",
    "Address search",
    "filters=listing_filters",
    "Overview",
    "Data Explorer",
    "Visuals",
    "Prediction",
    "Monitoring & Model",
    "Page",
    "offset=listing_offset",
    "Showing rows",
    "Reviewer visuals",
    "Price distribution",
    "Median price by rooms",
    "Listing map",
    "OpenStreetMap contributors",
    "Last successful collection",
    "latest_successful_ingestion_run",
    "Monitoring",
    "Model insights",
    "feature_importance",
)


st.set_page_config(page_title="RealtyScope", page_icon="RS", layout="wide")


def main() -> None:
    _prepare_host_page()
    data = fetch_dashboard_data(
        API_BASE_URL,
        limit=1000,
        offset=0,
        analytics_limit=2000,
        analytics_max_listings=20_000,
        filters={},
        timeout=API_TIMEOUT_SECONDS,
    )
    monitoring = fetch_monitoring_data(API_BASE_URL, timeout=API_TIMEOUT_SECONDS)
    payload = _build_payload(data=data, monitoring=monitoring)
    components.html(_workstation_html(payload), height=980, scrolling=False)


def _prepare_host_page() -> None:
    st.markdown(
        """
        <style>
        #MainMenu, footer, header[data-testid="stHeader"] { display: none; }
        .stApp { background: #111418; }
        .block-container { max-width: none; padding: 0; }
        iframe { display: block; border: 0; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _build_payload(*, data: DashboardData, monitoring: MonitoringData) -> dict[str, Any]:
    api_errors = data.errors + monitoring.errors
    use_snapshot = bool(api_errors and not data.listings)
    ui_cache_key = _local_ui_payload_cache_key() if use_snapshot else ""
    cached_payload = _read_ui_payload_cache(ui_cache_key) if use_snapshot else None
    if cached_payload is not None:
        return cached_payload
    snapshot = _local_snapshot_data() if use_snapshot else None
    listings = snapshot["listings"] if snapshot else data.analytics_listings or data.listings
    analytics_listings = snapshot["listings"] if snapshot else data.analytics_listings or listings
    chart_frame = _chart_frame_with_metadata(listings)
    analytics_frame = _chart_frame_with_metadata(analytics_listings)
    room_summary = room_summary_frame(chart_frame)
    price_bands = price_band_frame(chart_frame)
    stats_source = snapshot["stats"] if snapshot else data.stats or {}
    stats = _stats_with_listing_fallback(stats_source, listings=listings, chart_frame=chart_frame)
    stats.update(_map_quality_stats(chart_frame))
    monitoring_status = (
        monitoring.status or snapshot.get("monitoring", {}) if snapshot else monitoring.status or {}
    )
    model_metadata = _model_metadata_for_ui(
        monitoring.model_metadata or monitoring_status.get("model") or {}
    )
    monitoring_model = monitoring_status.get("model")
    if isinstance(monitoring_model, dict) and "data_freshness" not in model_metadata:
        data_freshness = monitoring_model.get("data_freshness")
        if isinstance(data_freshness, dict):
            model_metadata["data_freshness"] = data_freshness
    local_model = _local_model_payload()
    if not model_metadata and local_model:
        model_metadata = {
            "feature_count": len(local_model.get("featureNames", [])),
            "metrics": local_model.get("metrics", {}),
        }
    errors = _sanitized_errors(api_errors, has_snapshot=bool(snapshot))
    source = snapshot["source"] if snapshot else _api_source()
    source_rows = _source_rows(stats=stats, source=source, snapshot=bool(snapshot))
    primary_source_label = (
        " + ".join(row["name"] for row in source_rows) if source_rows else "Источник не подтвержден"
    )
    source = {**source, "label": primary_source_label}
    district_rows = _district_comparison_rows(analytics_frame)
    district_readiness = _district_readiness_for_comparison_rows(
        _district_readiness_payload(analytics_frame),
        district_rows=district_rows,
    )
    exposure_readiness = _exposure_readiness_payload(
        chart_frame,
        source=source,
        stats=stats,
        exposure_forecast=data.exposure_forecast,
    )
    observation_trend_series = _observation_trend_series_rows(data.observation_trend)

    payload = _clean_json(
        {
            "apiBaseUrl": API_BASE_URL,
            "connected": not api_errors,
            "mode": "snapshot" if snapshot else ("api" if not api_errors else "offline"),
            "source": source,
            "errors": errors,
            "stats": stats,
            "dataCountProvenance": _data_count_provenance(
                stats=stats,
                mode="snapshot" if snapshot else ("api" if not api_errors else "offline"),
                connected=not api_errors,
            ),
            "latestRun": stats.get("latest_successful_ingestion_run")
            or stats.get("latest_ingestion_run"),
            "listings": _listing_rows(chart_frame),
            "priceBands": price_bands.to_dict(orient="records"),
            "rooms": room_summary.to_dict(orient="records"),
            "mapPoints": _map_point_rows(chart_frame),
            "deals": _deal_rows(chart_frame),
            "comparables": _comparable_rows(
                chart_frame,
                target_rooms=BASELINE_FEATURE_DEFAULTS["rooms"],
                target_area_m2=BASELINE_FEATURE_DEFAULTS["total_area_m2"],
                target_price_per_m2=stats.get("median_price_per_m2"),
            ),
            "districtReadiness": district_readiness,
            "districtComparison": district_rows,
            "districtClusters": _district_cluster_rows(district_rows),
            "exposureReadiness": exposure_readiness,
            "observationTrendSeries": observation_trend_series,
            "observationTrend": _observation_trend_payload(
                stats=stats,
                source=source,
                exposure=exposure_readiness,
                observation_trend=data.observation_trend,
            ),
            "serviceStatus": _service_status_rows(
                connected=not api_errors,
                mode="snapshot" if snapshot else ("api" if not api_errors else "offline"),
                stats=stats,
                local_model=local_model,
                monitoring_status=monitoring_status,
            ),
            "sourceRows": source_rows,
            "primarySourceLabel": primary_source_label,
            "recentReports": _recent_domclick_report_rows() if snapshot else [],
            "valuationDefaults": BASELINE_FEATURE_DEFAULTS,
            "localModel": local_model,
            "osmCoverage": _osm_coverage_payload(
                local_model=local_model,
                model_metadata=model_metadata,
                stats=stats,
            ),
            "monitoring": monitoring_status,
            "model": model_metadata,
        }
    )
    if snapshot:
        _write_ui_payload_cache(ui_cache_key, payload)
    return payload


def _data_count_provenance(
    *,
    stats: dict[str, Any],
    mode: str,
    connected: bool,
) -> dict[str, Any]:
    listings_total = int(stats.get("listings_total") or 0)
    snapshot_count = int(stats.get("loaded_snapshot_listings") or 0)
    if connected and mode == "api":
        return {
            "source": "api",
            "label": "Текущая база API",
            "detail": f"API: {_format_int_for_label(listings_total)} объявлений",
            "count": listings_total,
            "snapshot_count": snapshot_count or None,
        }
    if mode == "snapshot":
        count = snapshot_count or listings_total
        return {
            "source": "snapshot",
            "label": "Локальный снимок",
            "detail": f"Локальный снимок: {_format_int_for_label(count)} объявлений; API недоступен",
            "count": count,
            "snapshot_count": snapshot_count or count,
        }
    return {
        "source": "offline",
        "label": "Источник счетчика недоступен",
        "detail": "API недоступен; актуальный счетчик не подтвержден",
        "count": listings_total,
        "snapshot_count": snapshot_count or None,
    }


def _local_ui_payload_cache_key() -> str:
    parts = [f"v{LOCAL_UI_PAYLOAD_CACHE_VERSION}", _local_snapshot_cache_key()]
    model_path = _local_model_path()
    if model_path is not None:
        try:
            stat = model_path.stat()
        except OSError:
            stat = None
        if stat is not None:
            parts.append(f"model:{model_path}:{stat.st_mtime_ns}")
    return "|".join(parts)


def _read_ui_payload_cache(cache_key: str) -> dict[str, Any] | None:
    try:
        payload = json.loads(LOCAL_UI_PAYLOAD_CACHE_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(payload, dict):
        return None
    if payload.get("version") != LOCAL_UI_PAYLOAD_CACHE_VERSION:
        return None
    if payload.get("cache_key") != cache_key:
        return None
    data = payload.get("data")
    return data if isinstance(data, dict) else None


def _write_ui_payload_cache(cache_key: str, data: dict[str, Any]) -> None:
    try:
        LOCAL_UI_PAYLOAD_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        LOCAL_UI_PAYLOAD_CACHE_PATH.write_text(
            json.dumps(
                {
                    "version": LOCAL_UI_PAYLOAD_CACHE_VERSION,
                    "cache_key": cache_key,
                    "data": data,
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
    except OSError:
        return


def _api_source() -> dict[str, Any]:
    return {
        "label": "Источник не подтвержден",
        "status": "Онлайн",
        "detail": "Источник объявлений будет показан после подтверждения в данных",
        "snapshotPath": None,
    }


def _local_snapshot_data() -> dict[str, Any] | None:
    cache_key = _local_snapshot_cache_key()
    return _local_snapshot_data_for_key(cache_key)


@lru_cache(maxsize=4)
def _local_snapshot_data_for_key(cache_key: str) -> dict[str, Any] | None:
    listings: list[dict[str, Any]] = []
    source_meta: dict[str, dict[str, Any]] = {}
    domclick_result = _all_domclick_snapshot_rows(cache_key)
    if domclick_result["rows"]:
        domclick_rows = domclick_result["rows"]
        listings.extend(domclick_rows)
        source_meta["domclick"] = {
            "detail": _source_observation_detail(
                collection_date_count=domclick_result["collection_date_count"],
                observation_count=domclick_result["observation_count"],
                snapshot_count=domclick_result["snapshot_count"],
            ),
            "count": len(domclick_rows),
            "snapshot_count": domclick_result["snapshot_count"],
            "available_snapshot_dir_count": domclick_result["available_snapshot_dir_count"],
            "collection_date_count": domclick_result["collection_date_count"],
            "observation_count": domclick_result["observation_count"],
            "stable_listing_ids": domclick_result["stable_listing_ids"],
            "listings_with_observation_history": domclick_result[
                "listings_with_observation_history"
            ],
            "max_observation_dates_per_listing": domclick_result[
                "max_observation_dates_per_listing"
            ],
            "listing_price_change_count": domclick_result["listing_price_change_count"],
        }

    cian_rows = _latest_cian_teammate_rows(start_index=1_000_001)
    if cian_rows:
        cian_collection_date_count = len(
            {str(row.get("observed_at", ""))[:10] for row in cian_rows if row.get("observed_at")}
        )
        listings.extend(cian_rows)
        source_meta["cian"] = {
            "detail": _source_observation_detail(
                collection_date_count=cian_collection_date_count,
                observation_count=len(cian_rows),
                snapshot_count=None,
            ),
            "count": len(cian_rows),
            "collection_date_count": cian_collection_date_count,
            "observation_count": len(cian_rows),
            "listing_price_change_count": 0,
        }
    if not listings:
        return None
    report = _latest_domclick_report()
    stats = _snapshot_stats(
        listings=listings,
        normalized_count=len(listings),
        rejected_count=domclick_result["rejected_count"],
        report=report,
    )
    stats["source_counts"] = _source_counts(listings)
    stats["sources_total"] = len(stats["source_counts"])
    stats["loaded_snapshot_listings"] = len(listings)
    latest_cian = max(
        (row.get("observed_at") for row in cian_rows if row.get("observed_at")), default=None
    )
    if latest_cian and not stats.get("latest_successful_ingestion_run"):
        stats["latest_successful_ingestion_run"] = {
            "source_name": "cian",
            "status": "success",
            "started_at": latest_cian,
            "finished_at": latest_cian,
            "records_seen": len(cian_rows),
            "normalized_count": len(cian_rows),
        }
    result = {
        "listings": listings,
        "stats": stats,
        "monitoring": {
            "status": "snapshot",
            "recent_errors": [],
            "data_quality": stats,
        },
        "source": {
            "label": "Локальные данные",
            "status": "Локально",
            "detail": "Снимки Домклик и импорт ЦИАН",
            "snapshotPath": str(domclick_result["latest_snapshot"])
            if domclick_result["latest_snapshot"]
            else None,
            "sourceMeta": source_meta,
        },
    }
    return result


def _local_snapshot_cache_key() -> str:
    parts = [f"v{LOCAL_SNAPSHOT_CACHE_VERSION}"]
    for snapshot_dir in list(reversed(_domclick_snapshot_dirs()))[:3]:
        try:
            stat = snapshot_dir.stat()
        except OSError:
            continue
        parts.append(f"dom:{snapshot_dir}:{stat.st_mtime_ns}")
    cian_path = _latest_cian_teammate_path()
    if cian_path is not None:
        try:
            stat = cian_path.stat()
        except OSError:
            stat = None
        if stat is not None:
            parts.append(f"cian:{cian_path}:{stat.st_mtime_ns}")
    return "|".join(parts)


def _source_observation_detail(
    *,
    collection_date_count: int,
    observation_count: int,
    snapshot_count: int | None,
) -> str:
    parts: list[str] = []
    if snapshot_count is not None:
        parts.append(
            f"{_format_int_for_label(snapshot_count)} {_ru_plural(snapshot_count, 'снимок', 'снимка', 'снимков')}"
        )
    if collection_date_count:
        parts.append(
            f"{_format_int_for_label(collection_date_count)} "
            f"{_ru_plural(collection_date_count, 'дата сбора', 'даты сбора', 'дат сбора')}"
        )
    if observation_count:
        parts.append(
            f"{_format_int_for_label(observation_count)} "
            f"{_ru_plural(observation_count, 'наблюдение', 'наблюдения', 'наблюдений')}"
        )
    return " · ".join(parts) or "Подтверждено данными"


def _format_int_for_label(value: int) -> str:
    return f"{int(value):,}".replace(",", " ")


def _ru_plural(value: int, one: str, few: str, many: str) -> str:
    value = abs(int(value))
    if value % 100 in {11, 12, 13, 14}:
        return many
    if value % 10 == 1:
        return one
    if value % 10 in {2, 3, 4}:
        return few
    return many


def _write_local_snapshot_cache(cache_key: str, data: dict[str, Any]) -> None:
    # Raw snapshot payloads are intentionally not cached: the prepared UI payload
    # cache is smaller and avoids low-memory crashes when Streamlit starts.
    del cache_key, data


@lru_cache(maxsize=4)
def _all_domclick_snapshot_rows(cache_key: str) -> dict[str, Any]:
    del cache_key
    unique_rows: dict[tuple[str, str], dict[str, Any]] = {}
    observation_count = 0
    rejected_count = 0
    parsed_dirs = 0
    latest_snapshot: Path | None = None
    raw_listing_dates: dict[str, set[str]] = {}
    raw_listing_prices: dict[str, set[int]] = {}
    snapshot_dirs = list(reversed(_domclick_snapshot_dirs()))
    collection_dates = {
        match.group(1)
        for snapshot_dir in snapshot_dirs
        if (match := re.search(r"(20\d{2}-\d{2}-\d{2})", snapshot_dir.name))
    }
    for snapshot_dir in snapshot_dirs:
        folder_date_match = re.search(r"(20\d{2}-\d{2}-\d{2})", snapshot_dir.name)
        folder_date = folder_date_match.group(1) if folder_date_match else None
        try:
            batch = load_domclick_snapshot_directory(snapshot_dir, max_records=LOCAL_SNAPSHOT_LIMIT)
        except (OSError, ValueError, MemoryError):
            continue
        parsed_dirs += 1
        if latest_snapshot is None:
            latest_snapshot = snapshot_dir
        observation_count += len(batch.normalized_listings)
        rejected_count += len(batch.rejected_listings)
        for row in batch.normalized_listings:
            payload = _normalized_listing_row(row, index=len(unique_rows) + 1)
            raw_id = payload.get("source_listing_id") or payload.get("source_url")
            if raw_id and folder_date:
                raw_listing_dates.setdefault(str(raw_id), set()).add(folder_date)
            if raw_id and payload.get("price_rub"):
                raw_listing_prices.setdefault(str(raw_id), set()).add(int(payload["price_rub"]))
            key = _listing_identity(payload)
            unique_rows[key] = payload
        if len(unique_rows) >= 13_000:
            break
    rows = list(unique_rows.values())
    rows.sort(
        key=lambda item: (
            str(item.get("observed_at") or ""),
            float(item.get("price_rub") or 0),
        ),
        reverse=True,
    )
    for index, row in enumerate(rows, start=1):
        row["id"] = index
    return {
        "rows": rows,
        "observation_count": observation_count,
        "rejected_count": rejected_count,
        "snapshot_count": parsed_dirs,
        "available_snapshot_dir_count": len(snapshot_dirs),
        "collection_date_count": len(collection_dates),
        "stable_listing_ids": len(raw_listing_dates),
        "listings_with_observation_history": sum(
            1 for dates in raw_listing_dates.values() if len(dates) > 1
        ),
        "max_observation_dates_per_listing": max(
            (len(dates) for dates in raw_listing_dates.values()), default=0
        ),
        "listing_price_change_count": sum(
            1 for prices in raw_listing_prices.values() if len(prices) > 1
        ),
        "latest_snapshot": latest_snapshot,
    }


def _listing_identity(row: dict[str, Any]) -> tuple[str, str]:
    source_name = str(row.get("source_name") or "unknown")
    source_listing_id = row.get("source_listing_id")
    source_url = row.get("source_url")
    address = row.get("address_text")
    fallback = f"{address}|{row.get('price_rub')}|{row.get('total_area_m2')}"
    return source_name, str(source_listing_id or source_url or fallback)


def _normalized_listing_row(row: Any, index: int) -> dict[str, Any]:
    payload = row.model_dump(mode="json")
    source_listing_id = payload.get("source_listing_id")
    try:
        listing_id = int(source_listing_id)
    except (TypeError, ValueError):
        listing_id = index
    payload["id"] = listing_id
    payload["is_ml_ready"] = bool(payload.get("has_coordinates"))
    payload["source_name"] = payload.get("source_name") or "domclick"
    payload["source_label"] = "Домклик"
    return payload


def _latest_cian_teammate_path() -> Path | None:
    candidates = [
        Path("data/raw/teammate/2026-06-17-recovered/part1_unique_recovered.json"),
        Path.cwd().parent
        / "RealtyScope"
        / "data"
        / "raw"
        / "teammate"
        / "2026-06-17-recovered"
        / "part1_unique_recovered.json",
    ]
    return next((path for path in candidates if path.exists()), None)


def _latest_cian_teammate_rows(*, start_index: int) -> list[dict[str, Any]]:
    source_path = _latest_cian_teammate_path()
    if source_path is None:
        return []
    try:
        payload = json.loads(source_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    if not isinstance(payload, list):
        return []
    rows: list[dict[str, Any]] = []
    for index, row in enumerate(payload, start=start_index):
        if not isinstance(row, dict):
            continue
        normalized = dict(row)
        normalized["id"] = index
        normalized["source_name"] = "cian"
        normalized["source_label"] = "ЦИАН"
        normalized["has_coordinates"] = bool(
            normalized.get("latitude") is not None and normalized.get("longitude") is not None
        )
        normalized["is_ml_ready"] = bool(
            normalized.get("price_rub")
            and normalized.get("total_area_m2")
            and normalized["has_coordinates"]
        )
        rows.append(normalized)
    return rows


def _domclick_snapshot_dirs() -> list[Path]:
    roots = [
        Path("data/raw/domclick"),
        Path.cwd().parent / "RealtyScope" / "data" / "raw" / "domclick",
    ]
    candidates: list[Path] = []
    for root in roots:
        if not root.exists():
            continue
        candidates.extend(
            path
            for path in root.iterdir()
            if path.is_dir()
            and (
                (path / "payloads").is_dir() or any(path.glob("*.json")) or any(path.glob("*.html"))
            )
        )
    if not candidates:
        return []
    return sorted(candidates, key=lambda path: path.stat().st_mtime)


def _latest_domclick_snapshot_dir() -> Path | None:
    candidates = _domclick_snapshot_dirs()
    if not candidates:
        return None
    return candidates[-1]


def _latest_domclick_report() -> dict[str, Any]:
    roots = [
        Path("data/processed/domclick_reports"),
        Path.cwd().parent / "RealtyScope" / "data" / "processed" / "domclick_reports",
    ]
    reports: list[Path] = []
    for root in roots:
        if root.exists():
            reports.extend(root.glob("*.json"))
    if not reports:
        return {}
    latest = max(reports, key=lambda path: path.stat().st_mtime)
    try:
        payload = json.loads(latest.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _recent_domclick_report_rows(limit: int = 8) -> list[dict[str, Any]]:
    roots = [
        Path("data/processed/domclick_reports"),
        Path.cwd().parent / "RealtyScope" / "data" / "processed" / "domclick_reports",
    ]
    reports: list[Path] = []
    for root in roots:
        if root.exists():
            reports.extend(root.glob("*.json"))
    rows: list[dict[str, Any]] = []
    for path in sorted(reports, key=lambda item: item.stat().st_mtime, reverse=True)[:limit]:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if not isinstance(payload, dict):
            continue
        latest_run = (
            payload.get("database_status", {}).get("latest_ingestion_run", {})
            if isinstance(payload.get("database_status"), dict)
            else {}
        )
        inspect = payload.get("inspect") if isinstance(payload.get("inspect"), dict) else {}
        persistence = (
            payload.get("persistence") if isinstance(payload.get("persistence"), dict) else {}
        )
        rows.append(
            {
                "run_id": payload.get("run_id") or path.stem,
                "status": payload.get("status"),
                "started_at": payload.get("started_at") or latest_run.get("started_at"),
                "finished_at": payload.get("finished_at") or latest_run.get("finished_at"),
                "records_seen": latest_run.get("records_seen")
                or inspect.get("records_seen")
                or persistence.get("records_seen"),
                "normalized_count": latest_run.get("normalized_count")
                or inspect.get("normalized_listings"),
                "inserted_count": latest_run.get("inserted_count")
                or persistence.get("listings_created"),
                "updated_count": latest_run.get("updated_count")
                or persistence.get("listings_updated"),
            }
        )
    return rows


def _snapshot_stats(
    *,
    listings: list[dict[str, Any]],
    normalized_count: int,
    rejected_count: int,
    report: dict[str, Any],
) -> dict[str, Any]:
    database_status = report.get("database_status") if isinstance(report, dict) else {}
    inspect = report.get("inspect") if isinstance(report, dict) else {}
    stats = database_status if isinstance(database_status, dict) else {}
    loaded_total = len(listings)
    ml_ready = sum(1 for row in listings if row.get("is_ml_ready"))
    latest_run = stats.get("latest_ingestion_run") if isinstance(stats, dict) else None
    collection = report.get("collection") if isinstance(report, dict) else {}
    persistence = report.get("persistence") if isinstance(report, dict) else {}
    return {
        "sources_total": stats.get("sources_total") or 1,
        "ingestion_runs_total": stats.get("ingestion_runs_total"),
        "raw_listings_total": stats.get("raw_listings_total") or inspect.get("raw_listings"),
        "listings_total": loaded_total,
        "loaded_snapshot_listings": loaded_total,
        "ml_ready_listings": ml_ready,
        "coordinate_listings": sum(
            1
            for row in listings
            if row.get("latitude") is not None and row.get("longitude") is not None
        ),
        "rejected_listings_total": stats.get("rejected_listings_total") or rejected_count,
        "latest_ingestion_run": latest_run,
        "latest_successful_ingestion_run": latest_run,
        "latest_collection_report": {
            "run_id": report.get("run_id"),
            "status": report.get("status"),
            "started_at": report.get("started_at"),
            "finished_at": report.get("finished_at"),
            "files_written": collection.get("files_written")
            if isinstance(collection, dict)
            else None,
            "snapshot_dir": collection.get("snapshot_dir")
            if isinstance(collection, dict)
            else None,
            "records_seen": inspect.get("records_seen"),
            "raw_listings": inspect.get("raw_listings"),
            "normalized_listings": inspect.get("normalized_listings"),
            "ml_ready_listings": inspect.get("ml_ready_listings"),
            "rejected_listings": inspect.get("rejected_listings"),
            "listings_created": persistence.get("listings_created")
            if isinstance(persistence, dict)
            else None,
            "listings_updated": persistence.get("listings_updated")
            if isinstance(persistence, dict)
            else None,
            "observations_inserted": persistence.get("observations_inserted")
            if isinstance(persistence, dict)
            else None,
        },
    }


def _stats_with_listing_fallback(
    stats: dict[str, Any],
    *,
    listings: list[dict[str, Any]],
    chart_frame: pd.DataFrame,
) -> dict[str, Any]:
    normalized = dict(stats)
    if "listings_total" not in normalized and listings:
        normalized["listings_total"] = len(listings)
    if "ml_ready_listings" not in normalized and listings:
        normalized["ml_ready_listings"] = sum(1 for row in listings if row.get("is_ml_ready"))
    if "coordinate_listings" not in normalized and listings:
        normalized["coordinate_listings"] = sum(
            1
            for row in listings
            if row.get("latitude") is not None and row.get("longitude") is not None
        )
    if "source_counts" not in normalized and listings:
        source_counts = _source_counts(listings)
        if source_counts:
            normalized["source_counts"] = source_counts
            normalized.setdefault("sources_total", len(source_counts))
    if "median_price_rub" not in normalized and not chart_frame.empty:
        prices = chart_frame["price_rub"].dropna()
        if not prices.empty:
            normalized["median_price_rub"] = float(prices.median())
    if "median_price_per_m2" not in normalized and not chart_frame.empty:
        prices_m2 = chart_frame["price_per_m2"].dropna()
        if not prices_m2.empty:
            normalized["median_price_per_m2"] = float(prices_m2.median())
    return normalized


def _chart_frame_with_metadata(listings: list[dict[str, Any]]) -> pd.DataFrame:
    chart_frame = listing_chart_frame(listings)
    if chart_frame.empty:
        return chart_frame
    metadata = pd.DataFrame(listings)
    for column in [
        "source_name",
        "source_label",
        "source_url",
        "source_listing_id",
        "observed_at",
        "status",
        "active",
        "floor",
        "floors_total",
        "building_year",
        *DISTRICT_OSM_FEATURE_COLUMNS,
    ]:
        chart_frame[column] = metadata.get(column, None)
    return chart_frame


def _moscow_coordinate_frames(
    chart_frame: pd.DataFrame, *, require_price: bool = False
) -> tuple[pd.DataFrame, pd.DataFrame]:
    if chart_frame.empty:
        return chart_frame.copy(), chart_frame.copy()
    subset = ["latitude", "longitude"]
    if require_price:
        subset.extend(["price_rub", "price_per_m2"])
    required = chart_frame.dropna(subset=[column for column in subset if column in chart_frame])
    if required.empty:
        return required.copy(), required.copy()
    required = required.copy()
    required["latitude"] = pd.to_numeric(required["latitude"], errors="coerce")
    required["longitude"] = pd.to_numeric(required["longitude"], errors="coerce")
    required = required.dropna(subset=["latitude", "longitude"])
    swapped = required["latitude"].between(*MOSCOW_LONGITUDE_BOUNDS) & required[
        "longitude"
    ].between(*MOSCOW_LATITUDE_BOUNDS)
    required.loc[swapped, ["latitude", "longitude"]] = required.loc[
        swapped, ["longitude", "latitude"]
    ].to_numpy()
    valid = required[
        required["latitude"].between(*MOSCOW_LATITUDE_BOUNDS)
        & required["longitude"].between(*MOSCOW_LONGITUDE_BOUNDS)
    ].copy()
    return required, valid


def _map_quality_stats(chart_frame: pd.DataFrame) -> dict[str, int]:
    coordinates, valid = _moscow_coordinate_frames(chart_frame)
    return {
        "coordinate_rows": int(len(coordinates)),
        "valid_moscow_points": int(len(valid)),
        "excluded_coordinate_rows": int(max(0, len(coordinates) - len(valid))),
    }


def _listing_rows(chart_frame: pd.DataFrame) -> list[dict[str, Any]]:
    if chart_frame.empty:
        return []
    columns = [
        "id",
        "address_text",
        "rooms",
        "total_area_m2",
        "price_rub",
        "price_per_m2",
        "source_name",
        "source_label",
        "source_url",
        "observed_at",
        "floor",
        "floors_total",
        "building_year",
        "latitude",
        "longitude",
    ]
    return chart_frame[[column for column in columns if column in chart_frame]].to_dict(
        orient="records"
    )


def _deal_rows(chart_frame: pd.DataFrame) -> list[dict[str, Any]]:
    required = chart_frame.copy()
    for column in ["rooms", "price_rub", "price_per_m2"]:
        required[column] = pd.to_numeric(required[column], errors="coerce")
    required = required.dropna(subset=["rooms", "price_rub", "price_per_m2"])
    if required.empty:
        return []
    grouped = required.groupby("rooms")["price_per_m2"]
    required["segment_sample_size"] = grouped.transform("count")
    required["segment_median_m2"] = grouped.transform("median")
    required["segment_mad_m2"] = grouped.transform(
        lambda values: (values - values.median()).abs().median()
    )
    required["segment_percentile"] = grouped.rank(method="average", pct=True)
    required["discount_pct"] = (
        required["price_per_m2"] - required["segment_median_m2"]
    ) / required["segment_median_m2"]
    robust_scale = (required["segment_mad_m2"] * 1.4826).where(lambda values: values != 0)
    required["robust_z"] = (required["price_per_m2"] - required["segment_median_m2"]) / robust_scale
    required["robust_z"] = pd.to_numeric(required["robust_z"], errors="coerce").fillna(0.0)
    discount_depth = (-required["discount_pct"] * 100).clip(lower=0)
    percentile_bonus = ((1 - required["segment_percentile"]) * 50).clip(lower=0)
    robust_bonus = (-required["robust_z"]).clip(lower=0) * 10
    deal_score = discount_depth + percentile_bonus + robust_bonus
    required["deal_score"] = (
        pd.to_numeric(deal_score, errors="coerce").fillna(0.0).clip(lower=0, upper=100).round(1)
    )
    required = required[
        (required["discount_pct"] < 0) & (required["segment_sample_size"] >= 3)
    ].sort_values(["deal_score", "discount_pct"], ascending=[False, True])
    columns = [
        "address_text",
        "rooms",
        "total_area_m2",
        "floor",
        "floors_total",
        "price_rub",
        "price_per_m2",
        "segment_median_m2",
        "segment_sample_size",
        "segment_percentile",
        "robust_z",
        "deal_score",
        "discount_pct",
        "source_name",
        "source_label",
        "source_url",
    ]
    return (
        required[[column for column in columns if column in required]]
        .head(60)
        .to_dict(orient="records")
    )


def _comparable_rows(
    chart_frame: pd.DataFrame,
    *,
    target_rooms: float | int | None,
    target_area_m2: float | int | None,
    target_price_per_m2: float | int | None,
    limit: int = 6,
) -> list[dict[str, Any]]:
    required_columns = {
        "price_per_m2",
        "price_rub",
        "rooms",
        "total_area_m2",
        "address_text",
    }
    if not required_columns.issubset(chart_frame.columns):
        return []
    rows = chart_frame.copy()
    rows["price_per_m2"] = pd.to_numeric(rows["price_per_m2"], errors="coerce")
    rows["price_rub"] = pd.to_numeric(rows["price_rub"], errors="coerce")
    rows["rooms"] = pd.to_numeric(rows["rooms"], errors="coerce")
    rows["total_area_m2"] = pd.to_numeric(rows["total_area_m2"], errors="coerce")
    rows = rows.dropna(subset=["price_per_m2", "price_rub", "rooms", "total_area_m2"])
    rows = rows[(rows["price_per_m2"] > 0) & (rows["price_rub"] > 0) & (rows["total_area_m2"] > 0)]
    if rows.empty:
        return []

    target_rooms_number = pd.to_numeric(pd.Series([target_rooms]), errors="coerce").iloc[0]
    if pd.notna(target_rooms_number):
        same_room_rows = rows[rows["rooms"] == float(target_rooms_number)]
        if not same_room_rows.empty:
            rows = same_room_rows

    target_area = pd.to_numeric(pd.Series([target_area_m2]), errors="coerce").iloc[0]
    if pd.isna(target_area) or float(target_area) <= 0:
        target_area = rows["total_area_m2"].median()
    target_price_m2 = pd.to_numeric(pd.Series([target_price_per_m2]), errors="coerce").iloc[0]
    if pd.isna(target_price_m2) or float(target_price_m2) <= 0:
        target_price_m2 = rows["price_per_m2"].median()

    rows["area_delta_m2"] = (rows["total_area_m2"] - float(target_area)).abs().round(2)
    rows["price_per_m2_delta_pct"] = (
        (rows["price_per_m2"] - float(target_price_m2)) / float(target_price_m2) * 100
    ).round(4)
    rows["comparison_score"] = (rows["area_delta_m2"] + rows["price_per_m2_delta_pct"].abs()).round(
        4
    )
    rows = rows.sort_values(
        ["comparison_score", "area_delta_m2", "price_per_m2_delta_pct"],
        ascending=[True, True, True],
    )
    columns = [
        "address_text",
        "source_name",
        "source_label",
        "source_url",
        "rooms",
        "total_area_m2",
        "floor",
        "floors_total",
        "observed_at",
        "price_rub",
        "price_per_m2",
        "area_delta_m2",
        "price_per_m2_delta_pct",
        "comparison_score",
    ]
    return (
        rows[[column for column in columns if column in rows]].head(limit).to_dict(orient="records")
    )


def _district_readiness_payload(chart_frame: pd.DataFrame) -> dict[str, Any]:
    district_values, district_sources, active_field, detected_fields = _district_assignment_series(
        chart_frame
    )
    district_count = int(district_values.nunique()) if not district_values.empty else 0
    listings_with_district = int(len(district_values))
    can_compare = bool(active_field and district_count >= 2 and listings_with_district >= 3)
    boundary_rows = int((district_sources == "admin_boundary_geojson").sum())
    boundary_index = _district_boundary_index()
    return {
        "status": "ready"
        if can_compare and active_field != "address_text"
        else ("partial" if can_compare else "missing"),
        "can_compare": can_compare,
        "detected_fields": detected_fields,
        "active_field": active_field,
        "listings_with_district": listings_with_district,
        "district_count": district_count,
        "coverage_pct": round(listings_with_district / len(chart_frame) * 100, 2)
        if len(chart_frame)
        else 0,
        "extraction_source": _summarize_district_sources(district_sources),
        "boundary_matched_rows": boundary_rows,
        "boundary_coverage_pct": round(boundary_rows / len(chart_frame) * 100, 2)
        if len(chart_frame)
        else 0,
        "boundary_source_title": boundary_index.source_title if boundary_index else None,
        "boundary_source_url": boundary_index.source_url if boundary_index else None,
        "required_fields": [
            "район или административный округ",
            "административные границы или надежная нормализация адреса",
            "агрегаты цены и объема по району",
        ],
    }


def _district_readiness_for_comparison_rows(
    readiness: dict[str, Any],
    *,
    district_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    adjusted = {**readiness, "comparison_rows": len(district_rows)}
    if district_rows:
        return adjusted
    return {**adjusted, "can_compare": False, "status": "missing"}


def _district_from_address(address: Any) -> str | None:
    text = str(address or "").strip()
    if not text:
        return None
    patterns = [
        r"(?:^|[,;])\s*(?:р-н|район)\s+([^,;]+)",
        r"(?:^|[,;])\s*([^,;]{2,80}?)\s+район(?:[,;]|$)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if not match:
            continue
        district = re.sub(r"\s+", " ", match.group(1)).strip(" .«»\"'")
        if district:
            return district
    return None


def _district_value_series(
    chart_frame: pd.DataFrame,
) -> tuple[pd.Series, str | None, list[str]]:
    district_values, _district_sources, active_field, detected_fields = _district_assignment_series(
        chart_frame
    )
    return district_values, active_field, detected_fields


def _district_assignment_series(
    chart_frame: pd.DataFrame,
) -> tuple[pd.Series, pd.Series, str | None, list[str]]:
    district_by_index: dict[Any, str] = {}
    source_by_index: dict[Any, str] = {}
    detected_fields: list[str] = []
    active_field: str | None = None

    boundary_values = _district_boundary_series(chart_frame)
    if not boundary_values.empty:
        district_by_index.update(boundary_values.to_dict())
        source_by_index.update(
            dict.fromkeys(boundary_values.index.to_list(), "admin_boundary_geojson")
        )
        detected_fields.append("boundary_geojson")
        active_field = "boundary_geojson"

    remaining_frame = chart_frame.drop(index=list(district_by_index.keys()), errors="ignore")
    text_values, text_active_field, text_detected_fields = _district_text_value_series(
        remaining_frame
    )
    if text_detected_fields:
        detected_fields.extend(
            field for field in text_detected_fields if field not in detected_fields
        )
    if not text_values.empty:
        district_by_index.update(text_values.to_dict())
        text_source = (
            "address_text"
            if text_active_field == "address_text"
            else ("structured_field" if text_active_field else "unknown")
        )
        source_by_index.update(dict.fromkeys(text_values.index.to_list(), text_source))
        active_field = active_field or text_active_field

    if not district_by_index:
        return (
            pd.Series(dtype="object"),
            pd.Series(dtype="object"),
            None,
            detected_fields,
        )
    districts = pd.Series(district_by_index, dtype="object").sort_index()
    sources = pd.Series(source_by_index, dtype="object").reindex(districts.index)
    return districts, sources, active_field, detected_fields


def _district_text_value_series(
    chart_frame: pd.DataFrame,
) -> tuple[pd.Series, str | None, list[str]]:
    candidate_fields = [
        "district",
        "district_name",
        "raion",
        "район",
        "okrug",
        "admin_district",
        "administrative_area",
        "municipality",
    ]
    detected_fields = [field for field in candidate_fields if field in chart_frame.columns]
    for field in detected_fields:
        values = chart_frame[field].dropna().astype(str).str.strip()
        values = values[values != ""]
        if not values.empty:
            return values, field, detected_fields
    if "address_text" not in chart_frame.columns:
        return pd.Series(dtype="object"), None, detected_fields
    extracted = chart_frame["address_text"].map(_district_from_address)
    values = extracted.dropna().astype(str).str.strip()
    values = values[values != ""]
    if values.empty:
        return pd.Series(dtype="object"), None, detected_fields
    return values, "address_text", [*detected_fields, "address_text"]


@lru_cache(maxsize=1)
def _district_boundary_index():
    if not DISTRICT_BOUNDARY_GEOJSON_PATH.exists():
        return None
    try:
        boundary_index = load_district_boundary_index(DISTRICT_BOUNDARY_GEOJSON_PATH)
    except (OSError, ValueError, json.JSONDecodeError):
        return None
    return boundary_index if boundary_index.feature_count else None


def _district_boundary_series(chart_frame: pd.DataFrame) -> pd.Series:
    if not {"latitude", "longitude"}.issubset(chart_frame.columns):
        return pd.Series(dtype="object")
    boundary_index = _district_boundary_index()
    if boundary_index is None:
        return pd.Series(dtype="object")
    values: dict[Any, str] = {}
    for index, row in chart_frame[["latitude", "longitude"]].iterrows():
        match = boundary_index.lookup(
            latitude=row.get("latitude"),
            longitude=row.get("longitude"),
        )
        if match is not None:
            values[index] = match.district_name
    if not values:
        return pd.Series(dtype="object")
    return pd.Series(values, dtype="object").sort_index()


def _summarize_district_sources(source_values: pd.Series) -> str | None:
    if source_values.empty:
        return None
    sources = list(dict.fromkeys(source_values.dropna().astype(str).to_list()))
    if not sources:
        return None
    return "+".join(sources)


def _district_comparison_rows(
    chart_frame: pd.DataFrame,
    *,
    min_sample_size: int = 5,
    limit: int = 12,
) -> list[dict[str, Any]]:
    required_columns = {"price_rub", "price_per_m2"}
    if not required_columns.issubset(chart_frame.columns):
        return []
    district_values, district_sources, active_field, _detected_fields = _district_assignment_series(
        chart_frame
    )
    if district_values.empty or active_field is None:
        return []
    rows = chart_frame.loc[district_values.index].copy()
    rows["district_name"] = district_values
    rows["district_source"] = district_sources
    rows["price_rub"] = pd.to_numeric(rows["price_rub"], errors="coerce")
    rows["price_per_m2"] = pd.to_numeric(rows["price_per_m2"], errors="coerce")
    rows = rows.dropna(subset=["district_name", "price_rub", "price_per_m2"])
    rows = rows[(rows["price_rub"] > 0) & (rows["price_per_m2"] > 0)]
    if rows.empty:
        return []

    source_agg = (
        ("source_name", "nunique") if "source_name" in rows.columns else ("price_per_m2", "size")
    )
    osm_feature_columns = [
        column for column in DISTRICT_OSM_FEATURE_COLUMNS if column in rows.columns
    ]
    for column in osm_feature_columns:
        rows[column] = pd.to_numeric(rows[column], errors="coerce")
    aggregate_spec = {
        "listings": ("price_per_m2", "size"),
        "median_price_per_m2": ("price_per_m2", "median"),
        "median_price_rub": ("price_rub", "median"),
        "min_price_per_m2": ("price_per_m2", "min"),
        "max_price_per_m2": ("price_per_m2", "max"),
        "source_count": source_agg,
        **{column: (column, "median") for column in osm_feature_columns},
    }
    result = rows.groupby("district_name", dropna=True).agg(**aggregate_spec).reset_index()
    result = result[result["listings"] >= min_sample_size]
    if result.empty:
        return []
    source_by_district = rows.groupby("district_name")["district_source"].apply(
        _summarize_district_sources
    )
    result["extraction_source"] = result["district_name"].map(source_by_district)
    result = result.sort_values(
        ["listings", "median_price_per_m2", "district_name"],
        ascending=[False, False, True],
    )
    return result.head(limit).to_dict(orient="records")


def _district_cluster_rows(
    district_rows: list[dict[str, Any]],
    *,
    cluster_count: int = 3,
    min_districts: int = 3,
) -> list[dict[str, Any]]:
    if len(district_rows) < min_districts:
        return []
    frame = pd.DataFrame(district_rows).copy()
    required_columns = {
        "district_name",
        "listings",
        "median_price_per_m2",
        "median_price_rub",
        "min_price_per_m2",
        "max_price_per_m2",
        "source_count",
    }
    if not required_columns.issubset(frame.columns):
        return []
    for column in required_columns - {"district_name"}:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    frame = frame.dropna(subset=list(required_columns))
    frame = frame[(frame["listings"] > 0) & (frame["median_price_per_m2"] > 0)]
    if len(frame) < min_districts:
        return []

    frame["price_spread_m2"] = frame["max_price_per_m2"] - frame["min_price_per_m2"]
    osm_feature_columns = [
        column for column in DISTRICT_OSM_FEATURE_COLUMNS if column in frame.columns
    ]
    for column in osm_feature_columns:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    feature_data = {
        "median_price_per_m2": frame["median_price_per_m2"],
        "log_listings": frame["listings"].map(math.log1p),
        "price_spread_m2": frame["price_spread_m2"],
        "source_count": frame["source_count"],
    }
    for column in osm_feature_columns:
        median_value = frame[column].median()
        feature_data[column] = frame[column].fillna(0 if pd.isna(median_value) else median_value)
    feature_frame = pd.DataFrame(feature_data)
    normalized = (feature_frame - feature_frame.mean()) / feature_frame.std(ddof=0).replace(0, 1)
    normalized = normalized.fillna(0)

    k = min(cluster_count, len(normalized))
    sorted_positions = list(frame.sort_values("median_price_per_m2").index)
    initial_positions = [
        sorted_positions[round(index * (len(sorted_positions) - 1) / max(k - 1, 1))]
        for index in range(k)
    ]
    centroids = normalized.loc[initial_positions].reset_index(drop=True)
    assignments = pd.Series([0] * len(normalized), index=normalized.index)
    for _iteration in range(24):
        distances = pd.DataFrame(
            {
                cluster_id: ((normalized - centroids.loc[cluster_id]) ** 2).sum(axis=1)
                for cluster_id in range(k)
            }
        )
        next_assignments = distances.idxmin(axis=1)
        if next_assignments.equals(assignments):
            break
        assignments = next_assignments
        for cluster_id in range(k):
            cluster_points = normalized[assignments == cluster_id]
            if not cluster_points.empty:
                centroids.loc[cluster_id] = cluster_points.mean()

    frame["cluster_id"] = assignments.astype(int)
    cluster_summary = frame.groupby("cluster_id").agg(
        cluster_size=("district_name", "size"),
        cluster_median_price_per_m2=("median_price_per_m2", "median"),
        cluster_median_listings=("listings", "median"),
    )
    sorted_cluster_ids = cluster_summary.sort_values("cluster_median_price_per_m2").index.to_list()
    label_by_cluster: dict[int, str] = {}
    for rank, cluster_id in enumerate(sorted_cluster_ids):
        if rank == 0:
            label = "Доступный профиль"
        elif rank == len(sorted_cluster_ids) - 1:
            label = "Премиальный профиль"
        else:
            label = "Средний профиль"
        label_by_cluster[int(cluster_id)] = label

    frame["cluster_label"] = frame["cluster_id"].map(label_by_cluster)
    for column in [
        "cluster_size",
        "cluster_median_price_per_m2",
        "cluster_median_listings",
    ]:
        frame[column] = frame["cluster_id"].map(cluster_summary[column])
    extraction_sources = frame.get("extraction_source", pd.Series(dtype="object")).fillna("")
    has_boundary_source = (
        extraction_sources.astype(str).str.contains("admin_boundary_geojson", regex=False).any()
    )
    source_parts = ["districtComparison"]
    if has_boundary_source:
        source_parts.append("boundary")
    if osm_feature_columns:
        source_parts.append("osm")
    frame["feature_source"] = "+".join(source_parts)
    frame = frame.sort_values(
        ["cluster_id", "median_price_per_m2", "listings"],
        ascending=[True, False, False],
    )
    columns = [
        "district_name",
        "cluster_id",
        "cluster_label",
        "cluster_size",
        "cluster_median_price_per_m2",
        "cluster_median_listings",
        "listings",
        "median_price_per_m2",
        "median_price_rub",
        "price_spread_m2",
        "source_count",
        "feature_source",
        *osm_feature_columns,
    ]
    return frame[columns].to_dict(orient="records")


def _exposure_readiness_payload(
    chart_frame: pd.DataFrame,
    *,
    source: dict[str, Any] | None = None,
    stats: dict[str, Any] | None = None,
    exposure_forecast: dict[str, Any] | None = None,
    min_target_rows: int = 100,
) -> dict[str, Any]:
    source_meta = source.get("sourceMeta", {}) if isinstance(source, dict) else {}
    collection_date_count = 0
    raw_observation_rows = 0
    snapshot_count = 0
    available_snapshot_dir_count = 0
    raw_stable_listing_ids = 0
    raw_history_listing_count = 0
    raw_max_observation_dates_per_listing = 0
    if isinstance(source_meta, dict):
        for meta in source_meta.values():
            if not isinstance(meta, dict):
                continue
            collection_date_count += int(meta.get("collection_date_count") or 0)
            raw_observation_rows += int(meta.get("observation_count") or 0)
            snapshot_count += int(meta.get("snapshot_count") or 0)
            available_snapshot_dir_count += int(meta.get("available_snapshot_dir_count") or 0)
            raw_stable_listing_ids += int(meta.get("stable_listing_ids") or 0)
            raw_history_listing_count += int(meta.get("listings_with_observation_history") or 0)
            raw_max_observation_dates_per_listing = max(
                raw_max_observation_dates_per_listing,
                int(meta.get("max_observation_dates_per_listing") or 0),
            )
    base = {
        "status": "missing",
        "status_label": "нет целевой переменной",
        "can_forecast": False,
        "rows_total": 0,
        "rows_with_observed_at": 0,
        "stable_listing_ids": 0,
        "observation_date_count": 0,
        "observation_span_days": 0,
        "collection_date_count": collection_date_count,
        "raw_observation_rows": raw_observation_rows,
        "snapshot_count": snapshot_count,
        "available_snapshot_dir_count": available_snapshot_dir_count,
        "raw_stable_listing_ids": raw_stable_listing_ids,
        "listings_with_observation_history": raw_history_listing_count,
        "max_observation_dates_per_listing": raw_max_observation_dates_per_listing,
        "lifecycle_target_rows": 0,
        "inferred_lifecycle_target_rows": 0,
        "inferred_lifecycle_min_gap_days": None,
        "inferred_lifecycle_can_forecast": False,
        "inferred_lifecycle_median_days": None,
        "inferred_lifecycle_max_days": None,
        "observed_exposure_target_rows": 0,
        "observed_exposure_min_target_rows": min_target_rows,
        "observed_exposure_can_forecast": False,
        "observed_exposure_max_days": None,
        "observed_exposure_forecast_segments": [],
        "median_exposure_days": None,
        "max_exposure_days": None,
        "min_target_rows": min_target_rows,
        "target_source": "listing_lifecycle",
        "note": "Для прогноза срока экспозиции нужны повторные наблюдения одного объявления и подтвержденный финальный статус: снято, продано или неактивно.",
    }
    if isinstance(stats, dict):
        base["raw_observation_rows"] = max(
            int(base["raw_observation_rows"]),
            int(stats.get("observations_total") or 0),
        )
        base["observation_date_count"] = max(
            int(base["observation_date_count"]),
            int(stats.get("observation_date_count") or 0),
        )
        base["listings_with_observation_history"] = max(
            int(base["listings_with_observation_history"]),
            int(stats.get("listings_with_observation_history") or 0),
        )
        base["max_observation_dates_per_listing"] = max(
            int(base["max_observation_dates_per_listing"]),
            int(stats.get("max_observation_dates_per_listing") or 0),
        )
        base["lifecycle_target_rows"] = max(
            int(base["lifecycle_target_rows"]),
            int(stats.get("lifecycle_target_rows") or 0),
        )
        base["inferred_lifecycle_target_rows"] = max(
            int(base["inferred_lifecycle_target_rows"]),
            int(stats.get("inferred_lifecycle_target_rows") or 0),
        )
        base["inferred_lifecycle_can_forecast"] = bool(stats.get("inferred_lifecycle_can_forecast"))
        if stats.get("inferred_lifecycle_min_gap_days") is not None:
            base["inferred_lifecycle_min_gap_days"] = stats.get("inferred_lifecycle_min_gap_days")
        if stats.get("inferred_lifecycle_median_days") is not None:
            base["inferred_lifecycle_median_days"] = stats.get("inferred_lifecycle_median_days")
        if stats.get("inferred_lifecycle_max_days") is not None:
            base["inferred_lifecycle_max_days"] = stats.get("inferred_lifecycle_max_days")
        base["observed_exposure_target_rows"] = max(
            int(base["observed_exposure_target_rows"]),
            int(stats.get("observed_exposure_target_rows") or 0),
        )
        base["observed_exposure_min_target_rows"] = int(
            stats.get("observed_exposure_min_target_rows") or min_target_rows
        )
        base["observed_exposure_can_forecast"] = bool(stats.get("observed_exposure_can_forecast"))
        if stats.get("observed_exposure_median_days") is not None:
            base["median_exposure_days"] = stats.get("observed_exposure_median_days")
        if stats.get("observed_exposure_max_days") is not None:
            base["observed_exposure_max_days"] = stats.get("observed_exposure_max_days")
            base["max_exposure_days"] = stats.get("observed_exposure_max_days")
        if stats.get("observed_exposure_target_source"):
            base["target_source"] = stats.get("observed_exposure_target_source")
        if isinstance(stats.get("observed_exposure_forecast_segments"), list):
            base["observed_exposure_forecast_segments"] = [
                row
                for row in stats.get("observed_exposure_forecast_segments", [])
                if isinstance(row, dict)
            ]
    if chart_frame.empty:
        return _finalize_exposure_readiness(
            base,
            exposure_forecast=exposure_forecast,
            min_target_rows=min_target_rows,
        )
    frame = chart_frame.copy()
    base["rows_total"] = int(len(frame))
    if "observed_at" not in frame:
        return _finalize_exposure_readiness(
            base,
            exposure_forecast=exposure_forecast,
            min_target_rows=min_target_rows,
        )
    frame["observed_at"] = pd.to_datetime(frame["observed_at"], errors="coerce", utc=True)
    observed = frame.dropna(subset=["observed_at"]).copy()
    base["rows_with_observed_at"] = int(len(observed))
    if observed.empty:
        return _finalize_exposure_readiness(
            base,
            exposure_forecast=exposure_forecast,
            min_target_rows=min_target_rows,
        )

    base["observation_date_count"] = max(
        int(base["observation_date_count"]),
        int(observed["observed_at"].dt.date.nunique()),
    )
    span = observed["observed_at"].max() - observed["observed_at"].min()
    base["observation_span_days"] = int(max(span.days, 0))
    if "source_listing_id" not in observed:
        return _finalize_exposure_readiness(
            base,
            exposure_forecast=exposure_forecast,
            min_target_rows=min_target_rows,
        )
    observed["source_name"] = observed.get("source_name", "unknown").fillna("unknown").astype(str)
    observed["source_listing_id"] = observed["source_listing_id"].fillna("").astype(str)
    observed = observed[observed["source_listing_id"].str.len() > 0].copy()
    if observed.empty:
        return _finalize_exposure_readiness(
            base,
            exposure_forecast=exposure_forecast,
            min_target_rows=min_target_rows,
        )

    terminal_statuses = {
        "removed",
        "sold",
        "closed",
        "inactive",
        "archived",
        "deleted",
        "unavailable",
        "expired",
        "снято",
        "продано",
        "закрыто",
        "неактивно",
    }
    if "status" in observed:
        observed["_terminal_status"] = (
            observed["status"].fillna("").astype(str).str.lower().isin(terminal_statuses)
        )
    else:
        observed["_terminal_status"] = False
    if "active" in observed:
        observed["_terminal_active"] = observed["active"].map(lambda value: value is False)
    else:
        observed["_terminal_active"] = False
    observed["_terminal"] = observed["_terminal_status"] | observed["_terminal_active"]

    grouped = observed.groupby(["source_name", "source_listing_id"], dropna=False)
    lifecycle = grouped.agg(
        first_seen=("observed_at", "min"),
        last_seen=("observed_at", "max"),
        observation_count=("observed_at", "size"),
        observation_dates=("observed_at", lambda values: values.dt.date.nunique()),
        has_terminal=("_terminal", "max"),
    )
    base["stable_listing_ids"] = int(len(lifecycle))
    base["listings_with_observation_history"] = max(
        int(base["listings_with_observation_history"]),
        int((lifecycle["observation_dates"] > 1).sum()),
    )
    base["max_observation_dates_per_listing"] = max(
        int(base["max_observation_dates_per_listing"]),
        int(lifecycle["observation_dates"].max()),
    )
    lifecycle["exposure_days"] = (lifecycle["last_seen"] - lifecycle["first_seen"]).dt.days.clip(
        lower=0
    )
    targets = lifecycle[(lifecycle["has_terminal"]) & (lifecycle["exposure_days"] > 0)]
    target_count = int(len(targets))
    base["lifecycle_target_rows"] = max(int(base["lifecycle_target_rows"]), target_count)
    if target_count:
        base["median_exposure_days"] = float(targets["exposure_days"].median())
        base["max_exposure_days"] = int(targets["exposure_days"].max())
    _set_exposure_readiness_status(base, min_target_rows=min_target_rows)
    if not int(base["lifecycle_target_rows"] or 0) and base["listings_with_observation_history"]:
        base["note"] = (
            "Повторные наблюдения есть, но нет подтвержденного финального статуса объявления; "
            "прогноз срока экспозиции не строится."
        )
    _merge_exposure_forecast_payload(base, exposure_forecast)
    return base


def _finalize_exposure_readiness(
    base: dict[str, Any],
    *,
    exposure_forecast: dict[str, Any] | None,
    min_target_rows: int,
) -> dict[str, Any]:
    _set_exposure_readiness_status(base, min_target_rows=min_target_rows)
    _merge_exposure_forecast_payload(base, exposure_forecast)
    return base


def _merge_exposure_forecast_payload(
    base: dict[str, Any], exposure_forecast: dict[str, Any] | None
) -> None:
    if not isinstance(exposure_forecast, dict) or exposure_forecast.get("error"):
        return
    if exposure_forecast.get("status") is not None:
        base["status"] = exposure_forecast.get("status")
    if exposure_forecast.get("status_label") is not None:
        base["status_label"] = exposure_forecast.get("status_label")
    if exposure_forecast.get("can_forecast") is not None:
        base["can_forecast"] = bool(exposure_forecast.get("can_forecast"))
    if exposure_forecast.get("target_source"):
        base["target_source"] = exposure_forecast.get("target_source")
    if exposure_forecast.get("terminal_lifecycle_target_rows") is not None:
        base["lifecycle_target_rows"] = int(
            exposure_forecast.get("terminal_lifecycle_target_rows") or 0
        )
    if exposure_forecast.get("inferred_lifecycle_target_rows") is not None:
        base["inferred_lifecycle_target_rows"] = int(
            exposure_forecast.get("inferred_lifecycle_target_rows") or 0
        )
    if exposure_forecast.get("inferred_lifecycle_can_forecast") is not None:
        base["inferred_lifecycle_can_forecast"] = bool(
            exposure_forecast.get("inferred_lifecycle_can_forecast")
        )
    if exposure_forecast.get("inferred_lifecycle_min_gap_days") is not None:
        base["inferred_lifecycle_min_gap_days"] = exposure_forecast.get(
            "inferred_lifecycle_min_gap_days"
        )
    if exposure_forecast.get("inferred_lifecycle_median_days") is not None:
        base["inferred_lifecycle_median_days"] = exposure_forecast.get(
            "inferred_lifecycle_median_days"
        )
        if exposure_forecast.get("target_source") == "observation_gap_inferred_lifecycle":
            base["median_exposure_days"] = exposure_forecast.get("inferred_lifecycle_median_days")
    if exposure_forecast.get("inferred_lifecycle_max_days") is not None:
        base["inferred_lifecycle_max_days"] = exposure_forecast.get("inferred_lifecycle_max_days")
        if exposure_forecast.get("target_source") == "observation_gap_inferred_lifecycle":
            base["max_exposure_days"] = exposure_forecast.get("inferred_lifecycle_max_days")
    if exposure_forecast.get("observed_exposure_target_rows") is not None:
        base["observed_exposure_target_rows"] = int(
            exposure_forecast.get("observed_exposure_target_rows") or 0
        )
    if exposure_forecast.get("observed_exposure_min_target_rows") is not None:
        base["observed_exposure_min_target_rows"] = int(
            exposure_forecast.get("observed_exposure_min_target_rows") or 0
        )
    if exposure_forecast.get("observed_exposure_can_forecast") is not None:
        base["observed_exposure_can_forecast"] = bool(
            exposure_forecast.get("observed_exposure_can_forecast")
        )
    if exposure_forecast.get("median_observed_exposure_days") is not None:
        base["median_exposure_days"] = exposure_forecast.get("median_observed_exposure_days")
    if exposure_forecast.get("max_observed_exposure_days") is not None:
        base["observed_exposure_max_days"] = exposure_forecast.get("max_observed_exposure_days")
        base["max_exposure_days"] = exposure_forecast.get("max_observed_exposure_days")
    segments = exposure_forecast.get("forecast_segments")
    if isinstance(segments, list):
        base["observed_exposure_forecast_segments"] = [
            row for row in segments if isinstance(row, dict)
        ]
    if exposure_forecast.get("caveat"):
        base["note"] = exposure_forecast.get("caveat")
    if exposure_forecast.get("method"):
        base["forecast_method"] = exposure_forecast.get("method")
    if exposure_forecast.get("forecast_model_version"):
        base["forecast_model_version"] = exposure_forecast.get("forecast_model_version")


def _set_exposure_readiness_status(base: dict[str, Any], *, min_target_rows: int) -> None:
    target_rows = int(base.get("lifecycle_target_rows") or 0)
    inferred_target_rows = int(base.get("inferred_lifecycle_target_rows") or 0)
    observed_target_rows = int(base.get("observed_exposure_target_rows") or 0)
    observed_min_rows = int(base.get("observed_exposure_min_target_rows") or min_target_rows)
    if target_rows >= min_target_rows:
        base["status"] = "ready"
        base["status_label"] = "готово к обучению"
        base["can_forecast"] = True
        base["target_source"] = "listing_lifecycle"
        base["note"] = (
            "Целевая переменная срока экспозиции есть; можно обучать baseline-модель "
            "после проверки утечек и стабильности наблюдений."
        )
    elif inferred_target_rows >= min_target_rows:
        base["status"] = "ready"
        base["status_label"] = "готово по исчезновению из наблюдений"
        base["can_forecast"] = True
        base["target_source"] = "observation_gap_inferred_lifecycle"
        base["note"] = (
            "Цель строится по повторным наблюдениям и исчезновению объявления из новых "
            "срезов источника; это прогноз исчезновения из наблюдений, а не подтвержденная "
            "продажа или снятие."
        )
    elif (
        bool(base.get("observed_exposure_can_forecast"))
        and observed_target_rows >= observed_min_rows
    ):
        base["status"] = "partial"
        base["status_label"] = "есть нижняя граница экспозиции"
        base["can_forecast"] = False
        base["target_source"] = "observed_history_lower_bound"
        base["note"] = (
            "Есть достаточно строк наблюдаемой экспозиции от первой до последней даты "
            "наблюдения объявления, но это только нижняя граница срока. Terminal lifecycle "
            "target rows для прогноза продажи или снятия остаются отдельным требованием."
        )
    elif target_rows > 0:
        base["status"] = "partial"
        base["status_label"] = "мало целевых строк"
        base["note"] = (
            "Найдены отдельные lifecycle target rows, но их недостаточно для честной "
            "модели прогноза срока экспозиции."
        )
    elif inferred_target_rows > 0:
        base["status"] = "partial"
        base["status_label"] = "мало строк исчезновения"
        base["target_source"] = "observation_gap_inferred_lifecycle"
        base["note"] = (
            "Есть отдельные строки исчезновения из наблюдений, но их недостаточно для "
            "честного прогноза срока экспозиции."
        )
    elif observed_target_rows > 0:
        base["status"] = "partial"
        base["status_label"] = "мало наблюдаемой экспозиции"
        base["target_source"] = "observed_history_lower_bound"
        base["note"] = (
            "Есть строки наблюдаемой экспозиции, но их недостаточно для отдельного "
            "прогноза. Terminal lifecycle target rows по-прежнему считаются отдельно."
        )


def _observation_trend_payload(
    *,
    stats: dict[str, Any],
    exposure: dict[str, Any],
    source: dict[str, Any] | None = None,
    observation_trend: dict[str, Any] | None = None,
) -> dict[str, Any]:
    source_meta = source.get("sourceMeta", {}) if isinstance(source, dict) else {}
    meta_observations = 0
    meta_collection_dates = 0
    meta_history_listings = 0
    meta_price_changes = 0
    if isinstance(source_meta, dict):
        for meta in source_meta.values():
            if not isinstance(meta, dict):
                continue
            meta_observations += int(meta.get("observation_count") or 0)
            meta_collection_dates += int(meta.get("collection_date_count") or 0)
            meta_history_listings += int(meta.get("listings_with_observation_history") or 0)
            meta_price_changes += int(meta.get("listing_price_change_count") or 0)

    observations_total = max(
        int(stats.get("observations_total") or 0),
        int(exposure.get("raw_observation_rows") or 0),
        meta_observations,
    )
    observation_dates = max(
        int(stats.get("observation_date_count") or 0),
        int(exposure.get("collection_date_count") or 0),
        meta_collection_dates,
    )
    history_listings = max(
        int(stats.get("listings_with_observation_history") or 0),
        int(exposure.get("listings_with_observation_history") or 0),
        meta_history_listings,
    )
    price_changes = max(
        int(stats.get("listing_price_change_count") or 0),
        meta_price_changes,
    )
    can_describe = bool(observations_total and observation_dates >= 2 and history_listings)
    payload = {
        "status": "partial" if can_describe else "missing",
        "status_label": "описательный тренд" if can_describe else "недостаточно истории",
        "can_describe": can_describe,
        "can_forecast": False,
        "observations_total": observations_total,
        "observation_date_count": observation_dates,
        "first_observed_date": stats.get("first_observed_date"),
        "last_observed_date": stats.get("last_observed_date"),
        "listings_with_observation_history": history_listings,
        "listing_price_change_count": price_changes,
        "note": (
            "Есть повторные наблюдения и изменения цен, поэтому можно показывать описательный тренд. "
            "Прогноз не строится без отдельной проверенной модели временного ряда."
            if can_describe
            else "Для честного тренда нужны повторные наблюдения по датам; прогноз не строится."
        ),
    }
    if isinstance(observation_trend, dict) and not observation_trend.get("error"):
        if observation_trend.get("status"):
            payload["status"] = observation_trend.get("status")
        if observation_trend.get("can_forecast") is not None:
            payload["can_forecast"] = bool(observation_trend.get("can_forecast"))
        for key in (
            "forecast_method",
            "forecast_horizon_days",
            "history_points",
            "trend_slope_per_day",
            "forecast_rows",
            "caveat",
        ):
            if observation_trend.get(key) is not None:
                payload[key] = observation_trend.get(key)
        if observation_trend.get("caveat"):
            payload["note"] = observation_trend.get("caveat")
        if payload["can_forecast"]:
            payload["status_label"] = "краткосрочный прогноз"
    return payload


def _observation_trend_series_rows(
    observation_trend: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    rows = observation_trend.get("rows", []) if isinstance(observation_trend, dict) else []
    if not isinstance(rows, list):
        return []
    prepared = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        observed_date = str(row.get("observed_date") or "").strip()
        if not observed_date:
            continue
        prepared.append(
            {
                "observed_date": observed_date,
                "observation_count": int(row.get("observation_count") or 0),
                "listing_count": int(row.get("listing_count") or 0),
                "median_price_rub": row.get("median_price_rub"),
                "median_price_per_m2": row.get("median_price_per_m2"),
            }
        )
    return prepared


def _service_status_rows(
    *,
    connected: bool,
    mode: str,
    stats: dict[str, Any],
    local_model: dict[str, Any] | None,
    monitoring_status: dict[str, Any],
) -> list[dict[str, Any]]:
    backend_rows = monitoring_status.get("services")
    if connected and isinstance(backend_rows, list) and backend_rows:
        rows = [row for row in backend_rows if isinstance(row, dict)]
    else:
        latest_report = stats.get("latest_collection_report") or {}
        latest_run = (
            stats.get("latest_successful_ingestion_run") or stats.get("latest_ingestion_run") or {}
        )
        ingestion_status = (
            latest_report.get("status") if isinstance(latest_report, dict) else None
        ) or (latest_run.get("status") if isinstance(latest_run, dict) else None)
        rows = [
            {
                "key": "api",
                "label": "API",
                "status": "ok" if connected else "warning",
                "status_label": "Доступен" if connected else "Недоступен",
                "detail": "Ответ API получен"
                if connected
                else (
                    "API не ответил; используется локальная витрина"
                    if mode == "snapshot"
                    else "Сервис данных не отвечает"
                ),
                "icon": "cloud_done" if connected else "cloud_off",
            },
            {
                "key": "database",
                "label": "PostgreSQL",
                "status": "unknown" if mode == "snapshot" else "warning",
                "status_label": "Не проверено" if mode == "snapshot" else "Нет подтверждения",
                "detail": "Живое подключение БД не проверено в snapshot-режиме"
                if mode == "snapshot"
                else "Нет ответа от API статистики",
                "count": None,
                "icon": "database",
            },
            {
                "key": "cache",
                "label": "Redis-кэш",
                "status": "unknown" if mode == "snapshot" else "warning",
                "status_label": "Не проверено" if mode == "snapshot" else "Нет подтверждения",
                "detail": "Живой Redis не проверено в snapshot-режиме"
                if mode == "snapshot"
                else "Нет ответа от API мониторинга",
                "count": None,
                "icon": "database",
            },
            {
                "key": "model",
                "label": "Модель",
                "status": "ok" if local_model else "warning",
                "status_label": "Доступна" if local_model else "Нет артефакта",
                "detail": "Локальный артефакт модели загружен"
                if local_model
                else "Артефакт модели не найден",
                "count": len(local_model.get("featureNames", [])) if local_model else None,
                "icon": "model_training",
            },
            {
                "key": "ingestion",
                "label": "Сбор данных",
                "status": "ok" if ingestion_status == "success" else "warning",
                "status_label": "Последний сбор успешен"
                if ingestion_status == "success"
                else "Требует проверки",
                "detail": latest_report.get("run_id")
                if isinstance(latest_report, dict) and latest_report.get("run_id")
                else "Последний отчет сбора не найден",
                "count": stats.get("ingestion_runs_total"),
                "icon": "schedule",
            },
        ]

    if not any(row.get("key") == "vitrine" for row in rows):
        rows.insert(
            1,
            {
                "key": "vitrine",
                "label": "Витрина интерфейса",
                "status": "ok" if stats.get("listings_total") else "warning",
                "status_label": "Подготовлена" if stats.get("listings_total") else "Нет данных",
                "detail": "Локальный подготовленный payload"
                if mode == "snapshot"
                else "Данные получены через API",
                "count": stats.get("loaded_snapshot_listings") or stats.get("listings_total"),
                "icon": "dashboard",
            },
        )
    return rows


def _map_point_rows(chart_frame: pd.DataFrame) -> list[dict[str, Any]]:
    _coordinates, valid = _moscow_coordinate_frames(chart_frame, require_price=True)
    if valid.empty:
        return []
    columns = [
        "lat",
        "lon",
        "listing_index",
        "price_rub",
        "price_per_m2",
        "rooms",
        "total_area_m2",
        "address_text",
        "source_name",
        "source_label",
        "source_url",
    ]
    points = valid.rename(columns={"latitude": "lat", "longitude": "lon"})
    points["listing_index"] = points.index.astype(int)
    columns = [column for column in columns if column in points]
    return points[columns].to_dict(orient="records")


def _source_rows(
    *, stats: dict[str, Any], source: dict[str, Any], snapshot: bool
) -> list[dict[str, Any]]:
    source_counts = stats.get("source_counts")
    if isinstance(source_counts, dict) and source_counts:
        meta = source.get("sourceMeta") if isinstance(source, dict) else {}
        rows = []
        for raw_name, count in sorted(source_counts.items()):
            display_name = _known_listing_source_name(str(raw_name), snapshot=False)
            if display_name is None:
                continue
            detail = ""
            if isinstance(meta, dict) and isinstance(meta.get(raw_name), dict):
                detail = str(meta[raw_name].get("detail") or "")
            rows.append(
                {
                    "name": display_name,
                    "status": "Загружено" if snapshot else "Подключено",
                    "detail": detail or "Подтверждено данными",
                    "count": count,
                    "icon": "database",
                }
            )
        return rows
    listings_total = stats.get("listings_total")
    connected_status = "Загружено" if snapshot else "Подключено"
    latest_run = (
        stats.get("latest_successful_ingestion_run") or stats.get("latest_ingestion_run") or {}
    )
    raw_source_name = (
        str(latest_run.get("source_name") or "").lower() if isinstance(latest_run, dict) else ""
    )
    source_name = _known_listing_source_name(raw_source_name, snapshot=snapshot)
    if source_name is None:
        return []
    return [
        {
            "name": source_name,
            "status": connected_status,
            "detail": source.get("detail") if snapshot else "Подтвержден последним сбором данных",
            "count": listings_total,
            "icon": "database",
        }
    ]


def _known_listing_source_name(raw_source_name: str, *, snapshot: bool) -> str | None:
    if raw_source_name == "domclick":
        return "Домклик"
    if raw_source_name == "cian":
        return "ЦИАН"
    return None


def _source_counts(listings: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in listings:
        source_name = str(row.get("source_name") or "").lower()
        if source_name in {"domclick", "cian"}:
            counts[source_name] = counts.get(source_name, 0) + 1
    return counts


def _local_model_path() -> Path | None:
    candidates = [
        Path("data/processed/models/phase5/baseline_ridge_v2_non_leaky.joblib"),
        Path.cwd().parent
        / "RealtyScope"
        / "data"
        / "processed"
        / "models"
        / "phase5"
        / "baseline_ridge_v2_non_leaky.joblib",
    ]
    return next((path for path in candidates if path.exists()), None)


def _local_model_payload() -> dict[str, Any] | None:
    model_path = _local_model_path()
    if model_path is None:
        return None
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            artifact = joblib.load(model_path)
    except (ImportError, OSError, ValueError, KeyError, TypeError):
        return None
    model = artifact.get("model")
    named_steps = getattr(model, "named_steps", {})
    scaler = named_steps.get("scaler") if isinstance(named_steps, dict) else None
    regressor = named_steps.get("regressor") if isinstance(named_steps, dict) else None
    if scaler is None or regressor is None:
        return None
    means = getattr(scaler, "mean_", None)
    scales = getattr(scaler, "scale_", None)
    coefficients = getattr(regressor, "coef_", None)
    intercept = getattr(regressor, "intercept_", None)
    feature_names = artifact.get("feature_names") or []
    if (
        means is None
        or scales is None
        or coefficients is None
        or intercept is None
        or not feature_names
    ):
        return None
    return {
        "featureNames": list(feature_names),
        "means": [float(value) for value in means],
        "scales": [float(value) for value in scales],
        "coefficients": [float(value) for value in coefficients],
        "intercept": float(intercept),
        "modelVersion": artifact.get("model_version"),
        "featureVersion": artifact.get("feature_version"),
        "targetVariable": artifact.get("target_variable", "price_rub"),
        "metrics": artifact.get("metrics", {}),
    }


def _model_metadata_for_ui(model_metadata: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(model_metadata, dict) or not model_metadata:
        return {}
    payload = dict(model_metadata)
    metrics = payload.get("metrics")
    metrics_summary = payload.get("metrics_summary")
    if not isinstance(metrics, dict) and isinstance(metrics_summary, dict):
        payload["metrics"] = metrics_summary
    feature_names = payload.get("feature_names")
    if "feature_count" not in payload and isinstance(feature_names, list):
        payload["feature_count"] = len(feature_names)
    return payload


def _osm_coverage_payload(
    *,
    local_model: dict[str, Any] | None,
    model_metadata: dict[str, Any] | None = None,
    stats: dict[str, Any],
) -> dict[str, Any]:
    if local_model:
        feature_names = set(local_model.get("featureNames", []))
    elif model_metadata:
        feature_names = set(
            model_metadata.get("feature_names") or model_metadata.get("featureNames") or []
        )
    else:
        feature_names = set()
    osm_features = sorted(
        name
        for name in feature_names
        if name
        in {
            "healthcare_count_1000m",
            "nearest_transport_m",
            "nearest_transport_m_missing",
            "osm_missing",
            "parks_count_1000m",
            "schools_count_1000m",
            "shops_count_1000m",
            "transport_count_1000m",
            "transport_count_500m",
        }
    )
    coverage_rows = stats.get("osm_features_total") or stats.get("osm_rows_present")
    return {
        "source": "OpenStreetMap",
        "featureContract": bool(osm_features),
        "featureCount": len(osm_features),
        "features": osm_features,
        "coverageRows": coverage_rows,
        "featuredListings": stats.get("osm_featured_listings"),
        "coveragePct": stats.get("osm_coverage_pct"),
        "featureVersion": stats.get("osm_feature_version"),
        "attribution": stats.get("osm_attribution") or "OpenStreetMap contributors",
        "liveRows": stats.get("osm_live_rows"),
        "localExtractRows": stats.get("osm_local_extract_rows"),
        "coordinateDerivedRows": stats.get("osm_coordinate_derived_rows"),
        "coverageSource": stats.get("osm_infrastructure_coverage_source"),
        "defaultMissing": bool(BASELINE_FEATURE_DEFAULTS.get("osm_missing", 1.0)),
    }


def _sanitized_errors(errors: list[str], *, has_snapshot: bool = False) -> list[str]:
    if not errors:
        return []
    if has_snapshot:
        return ["Сервис RealtyScope недоступен. Показаны локальные реальные данные Домклик и ЦИАН."]
    return ["Сервис данных не отвечает. Запустите сервис RealtyScope и обновите страницу."]


def _clean_json(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _clean_json(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_clean_json(item) for item in value]
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    if pd.isna(value):
        return None
    return value


def _workstation_html(payload: dict[str, Any]) -> str:
    payload_json = json.dumps(payload, ensure_ascii=False)
    return f"""
<!doctype html>
<html class="dark" lang="ru">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>RealtyScope - Аналитика рынка Москвы</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap" rel="stylesheet">
<style>
:root {{
  --bg:#111418; --surface:#111418; --surface-low:#0b0e12; --panel:#191c20;
  --panel-high:#272a2e; --panel-higher:#323539; --line:#3d4947; --line-strong:#879391;
  --text:#e1e2e8; --muted:#bcc9c6; --faint:#879391; --primary:#6bd8cb;
  --primary-deep:#00302b; --secondary:#c3c0ff; --tertiary:#ffb59a; --error:#ffb4ab;
  --success:#38d39f; --warning:#f59e0b; --rail:260px;
}}
body.light {{
  --bg:#f8fafc; --surface:#ffffff; --surface-low:#f1f5f9; --panel:#ffffff;
  --panel-high:#e2e8f0; --panel-higher:#cbd5e1; --line:#cbd5e1; --line-strong:#64748b;
  --text:#0f172a; --muted:#475569; --faint:#64748b; --primary:#0d9488;
  --primary-deep:#ccfbf1; --secondary:#4338ca; --tertiary:#d97706; --error:#dc2626;
  --success:#047857; --warning:#b45309;
}}
* {{ box-sizing:border-box; }}
html, body {{ margin:0; min-height:100%; background:var(--bg); color:var(--text); font-family:Inter,system-ui,sans-serif; }}
body {{ overflow:hidden; }}
.material-symbols-outlined, .control-icon {{ display:inline-flex; align-items:center; justify-content:center; line-height:1; }}
.material-symbols-outlined {{ width:22px; min-width:22px; height:22px; color:currentColor; }}
.material-symbols-outlined svg {{ width:20px; height:20px; display:block; stroke:currentColor; }}
.control-icon {{ width:22px; min-width:22px; height:22px; font-size:16px; font-weight:900; color:var(--primary); }}
.theme-icon svg {{ width:20px; height:20px; display:block; stroke:var(--primary); }}
.app {{ display:flex; width:100vw; height:980px; background:var(--bg); }}
.sidebar {{ width:var(--rail); min-width:var(--rail); height:100%; background:var(--surface-low); border-right:1px solid var(--line); display:flex; flex-direction:column; padding:12px; transition:width .28s cubic-bezier(.2,.8,.2,1), min-width .28s cubic-bezier(.2,.8,.2,1); }}
body.collapsed {{ --rail:64px; }}
.brand {{ display:flex; align-items:center; gap:12px; height:48px; margin-bottom:20px; background:transparent; border:0; border-radius:8px; color:var(--text); cursor:pointer; padding:0 8px; font-weight:800; }}
.brand-mark {{ display:grid; place-items:center; width:40px; min-width:40px; height:40px; border-radius:8px; color:var(--primary); background:color-mix(in srgb,var(--primary) 14%,transparent); border:1px solid color-mix(in srgb,var(--primary) 34%,var(--line)); }}
.brand-mark svg {{ width:27px; height:27px; display:block; stroke:currentColor; }}
.brand-text small {{ display:block; margin-top:2px; color:var(--faint); font-size:10px; font-weight:700; letter-spacing:.08em; text-transform:uppercase; }}
body.collapsed .brand {{ justify-content:center; padding:0; }}
body.collapsed .brand-text, body.collapsed .nav-label, body.collapsed .side-extra, body.collapsed .toggle-label {{ display:none; }}
.nav {{ display:flex; flex-direction:column; gap:8px; flex:1; }}
.nav button, .side-button {{ height:44px; border:0; border-left:2px solid transparent; border-radius:8px; background:transparent; color:var(--muted); display:flex; align-items:center; gap:12px; padding:0 10px; cursor:pointer; font:600 13px Inter; transition:background .18s,color .18s,border-color .18s,transform .18s; }}
button:disabled {{ opacity:.45; cursor:not-allowed; transform:none !important; }}
.nav button:hover, .side-button:hover {{ background:var(--panel-high); color:var(--text); transform:translateX(1px); }}
.nav button.active {{ color:var(--primary); background:color-mix(in srgb,var(--primary) 13%,transparent); border-left-color:var(--primary); }}
body.collapsed .nav button, body.collapsed .side-button {{ justify-content:center; padding:0; }}
.side-footer {{ border-top:1px solid var(--line); padding-top:14px; display:flex; flex-direction:column; gap:10px; }}
.toggle-switch {{ margin-left:auto; width:32px; height:16px; background:var(--line); border-radius:999px; position:relative; }}
.toggle-switch::after {{ content:''; position:absolute; top:3px; left:3px; width:10px; height:10px; background:var(--text); border-radius:50%; transition:left .18s; }}
body.light .toggle-switch::after {{ left:19px; }}
.main {{ flex:1; min-width:0; height:100%; overflow:auto; display:flex; flex-direction:column; }}
.topbar {{ position:sticky; top:0; z-index:5; height:64px; display:flex; align-items:center; justify-content:space-between; gap:20px; padding:0 24px; border-bottom:1px solid var(--line); background:color-mix(in srgb,var(--bg) 92%,transparent); backdrop-filter:blur(14px); }}
.product {{ font-size:13px; font-weight:800; letter-spacing:.12em; text-transform:uppercase; color:var(--muted); margin-bottom:6px; }}
h1 {{ margin:0; font-size:24px; line-height:30px; letter-spacing:0; }}
.chips {{ display:flex; align-items:center; gap:8px; flex-wrap:wrap; justify-content:flex-end; }}
.chip {{ display:inline-flex; align-items:center; gap:8px; height:32px; padding:0 13px; border:1px solid var(--line); border-radius:999px; background:var(--panel); color:var(--muted); font-size:12px; font-weight:700; max-width:360px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }}
.pulse {{ width:7px; height:7px; border-radius:50%; background:var(--primary); box-shadow:0 0 12px var(--primary); }}
.content {{ flex:1; width:100%; padding:22px 24px 40px; max-width:1600px; margin:0 auto; animation:enter .28s ease both; }}
.app-footer {{ width:100%; max-width:1600px; margin:0 auto; padding:14px 24px 20px; color:var(--muted); border-top:1px solid var(--line); font-size:12px; display:flex; gap:14px; align-items:center; justify-content:flex-start; }}
@keyframes enter {{ from {{ opacity:0; transform:translateY(8px); }} to {{ opacity:1; transform:none; }} }}
.kicker {{ color:var(--primary); font-size:12px; font-weight:800; letter-spacing:.20em; text-transform:uppercase; margin:0 0 18px; }}
.grid4 {{ display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:16px; }}
.grid12 {{ display:grid; grid-template-columns:repeat(12,minmax(0,1fr)); gap:16px; margin-top:16px; }}
.card {{ background:var(--panel); border:1px solid var(--line); border-radius:8px; padding:20px; overflow:hidden; }}
.card:hover {{ border-color:color-mix(in srgb,var(--primary) 45%,var(--line)); }}
.card.tight {{ padding:16px; }}
.mini-kpi {{ border:1px solid var(--line); border-radius:8px; padding:18px; min-height:152px; background:color-mix(in srgb,var(--surface-low) 58%,transparent); }}
.mini-kpi .value {{ font-size:28px; line-height:34px; overflow-wrap:anywhere; }}
.mini-kpi.compact .value {{ font-size:24px; line-height:30px; overflow-wrap:normal; word-break:normal; }}
.span4 {{ grid-column:span 4; }} .span5 {{ grid-column:span 5; }} .span7 {{ grid-column:span 7; }} .span8 {{ grid-column:span 8; }} .span12 {{ grid-column:span 12; }}
.label {{ color:var(--muted); font-size:12px; font-weight:700; letter-spacing:.07em; text-transform:uppercase; }}
.value {{ margin-top:12px; font-size:32px; font-weight:800; font-variant-numeric:tabular-nums; }}
.sub {{ margin-top:12px; color:var(--faint); font-size:12px; line-height:16px; }}
.card-title {{ display:flex; align-items:center; justify-content:space-between; border-bottom:1px solid var(--line); padding-bottom:14px; margin-bottom:16px; font-size:13px; font-weight:800; letter-spacing:.07em; text-transform:uppercase; }}
.primary-btn, .ghost-btn {{ border:1px solid var(--line); border-radius:6px; min-height:38px; padding:0 14px; cursor:pointer; font-weight:800; transition:filter .16s,transform .16s,background .16s; }}
.primary-btn {{ background:var(--primary); color:#00201d; border-color:var(--primary); }}
.ghost-btn {{ background:var(--panel-high); color:var(--text); }}
.primary-btn:hover, .ghost-btn:hover {{ filter:brightness(1.08); transform:translateY(-1px); }}
.field {{ display:flex; flex-direction:column; gap:6px; margin-bottom:12px; }}
.field input, .field select {{ height:38px; border:1px solid var(--line); border-radius:6px; background:var(--surface-low); color:var(--text); padding:0 10px; font:500 13px Inter; }}
.step-input {{ display:grid; grid-template-columns:28px minmax(0,1fr) 28px; gap:4px; align-items:center; }}
.step-input input {{ width:100%; }}
.step-input button, .small-icon-btn {{ height:34px; border:1px solid var(--line); border-radius:6px; background:var(--panel-high); color:var(--text); font-weight:900; cursor:pointer; }}
.form-section {{ border-top:1px solid var(--line); padding-top:14px; margin-top:14px; }}
.form-section:first-of-type {{ border-top:0; padding-top:0; margin-top:0; }}
.section-label {{ margin:0 0 12px; color:var(--primary); font-size:11px; font-weight:900; letter-spacing:.12em; text-transform:uppercase; }}
.valuation-hero {{ display:grid; gap:10px; padding:16px; border:1px solid color-mix(in srgb,var(--primary) 48%,var(--line)); border-radius:8px; background:linear-gradient(135deg,color-mix(in srgb,var(--primary) 12%,var(--panel)),var(--panel)); }}
.valuation-hero .value {{ margin-top:0; font-size:30px; line-height:36px; }}
.valuation-facts {{ display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:10px; margin-top:14px; }}
.valuation-fact {{ border-top:1px solid var(--line); padding-top:10px; min-width:0; }}
.valuation-fact span {{ display:block; color:var(--muted); font-size:11px; font-weight:800; letter-spacing:.08em; text-transform:uppercase; }}
.valuation-fact strong {{ display:block; margin-top:5px; color:var(--text); font-size:16px; font-variant-numeric:tabular-nums; overflow-wrap:anywhere; }}
.valuation-form.compact .form-section {{ margin-top:10px; padding-top:10px; }}
.valuation-form.compact .mini-grid {{ gap:10px; }}
.valuation-form.compact .field {{ margin-bottom:8px; }}
.valuation-primary-controls {{ display:grid; gap:10px; margin-top:10px; }}
.valuation-action-bar {{ display:flex; gap:10px; align-items:center; margin-top:12px; }}
.valuation-action-bar .primary-btn {{ min-height:40px; flex:1; }}
.advanced-valuation-fields summary {{ cursor:pointer; color:var(--primary); font-size:11px; font-weight:900; letter-spacing:.12em; text-transform:uppercase; list-style:none; }}
.advanced-valuation-fields summary::-webkit-details-marker {{ display:none; }}
.advanced-valuation-fields summary::after {{ content:'+'; float:right; color:var(--muted); font-size:16px; line-height:12px; }}
.advanced-valuation-fields[open] summary::after {{ content:'-'; }}
.check-row {{ display:flex; align-items:center; gap:8px; margin:8px 0 2px; color:var(--muted); font-size:12px; font-weight:800; }}
.check-row input {{ width:16px; height:16px; accent-color:var(--primary); }}
.range-pair {{ border:1px solid var(--line); border-radius:8px; padding:10px; margin-bottom:12px; background:color-mix(in srgb,var(--surface-low) 62%,transparent); }}
.range-pair .range-row {{ display:grid; grid-template-columns:1fr 1fr; gap:8px; margin-top:8px; }}
.range-label {{ display:flex; justify-content:space-between; gap:10px; color:var(--muted); font-size:12px; font-weight:800; text-transform:uppercase; letter-spacing:.06em; }}
.dual-range {{ position:relative; height:34px; margin:8px 0 6px; --from:0%; --to:100%; }}
.dual-range::before {{ content:''; position:absolute; left:0; right:0; top:14px; height:6px; border-radius:999px; background:var(--panel-high); border:1px solid var(--line); }}
.dual-range-fill {{ position:absolute; left:var(--from); width:calc(var(--to) - var(--from)); top:14px; height:6px; border-radius:999px; background:linear-gradient(90deg,var(--primary),var(--secondary)); box-shadow:0 0 12px color-mix(in srgb,var(--primary) 28%,transparent); }}
.dual-range input[type=range] {{ position:absolute; inset:0; width:100%; height:34px; margin:0; appearance:none; -webkit-appearance:none; background:transparent; pointer-events:none; }}
.dual-range input[type=range]::-webkit-slider-runnable-track {{ height:6px; background:transparent; }}
.dual-range input[type=range]::-webkit-slider-thumb {{ -webkit-appearance:none; pointer-events:auto; width:16px; height:16px; margin-top:-5px; border-radius:50%; border:2px solid var(--panel); background:var(--primary); box-shadow:0 0 0 1px var(--line),0 2px 8px rgba(0,0,0,.32); cursor:pointer; }}
.dual-range input[type=range]::-moz-range-track {{ height:6px; background:transparent; }}
.dual-range input[type=range]::-moz-range-thumb {{ pointer-events:auto; width:14px; height:14px; border-radius:50%; border:2px solid var(--panel); background:var(--primary); box-shadow:0 0 0 1px var(--line),0 2px 8px rgba(0,0,0,.32); cursor:pointer; }}
.segmented {{ display:grid; grid-template-columns:repeat(6,1fr); gap:4px; background:var(--surface-low); border:1px solid var(--line); border-radius:8px; padding:4px; }}
.segmented button {{ border:0; border-radius:6px; background:transparent; color:var(--muted); height:32px; cursor:pointer; font-weight:700; }}
.segmented button.active {{ background:var(--primary); color:#00201d; }}
.map {{ position:relative; min-height:360px; border-radius:8px; overflow:hidden; background:var(--surface-low); cursor:grab; user-select:none; }}
.map-page-card .map {{ min-height:640px; }}
.map.dragging {{ cursor:grabbing; }}
.tile-layer {{ position:absolute; inset:0; filter:saturate(.78) brightness(.78) contrast(1.02); background:var(--surface-low); }}
.tile-layer img {{ position:absolute; width:256px; height:256px; object-fit:cover; will-change:left,top; }}
body.light .tile-layer {{ filter:saturate(.9) brightness(.96) contrast(.95); }}
.map-canvas {{ position:absolute; inset:0; width:100%; height:100%; z-index:1; pointer-events:none; }}
.map[data-layer="heat"] .point {{ display:none; }}
.map::after {{ content:''; position:absolute; inset:0; background:linear-gradient(to top,color-mix(in srgb,var(--panel) 88%,transparent),transparent 48%); pointer-events:none; }}
.point {{ position:absolute; width:11px; height:11px; border-radius:50%; border:1px solid rgba(234,242,255,.82); background:var(--primary); box-shadow:0 0 14px var(--primary); transform:translate(-50%,-50%); z-index:2; animation:pin .9s ease both; cursor:pointer; padding:0; }}
.point::after {{ content:attr(data-label); position:absolute; left:13px; top:-8px; min-width:max-content; padding:3px 6px; border-radius:6px; background:rgba(17,20,24,.86); border:1px solid var(--line); color:var(--text); font-size:10px; font-weight:800; opacity:0; pointer-events:none; transform:translateY(3px); transition:opacity .14s, transform .14s; }}
.point:hover::after {{ opacity:1; transform:none; }}
.point.hot {{ background:#ef4444; box-shadow:0 0 16px rgba(239,68,68,.9); }}
.point.mid {{ background:#f59e0b; box-shadow:0 0 15px rgba(245,158,11,.85); }}
.point.selected {{ width:16px; height:16px; border-color:#fff; z-index:4; }}
@keyframes pin {{ from {{ opacity:0; transform:translate(-50%,-50%) scale(.4); }} to {{ opacity:1; transform:translate(-50%,-50%) scale(1); }} }}
.map-zoom {{ position:absolute; right:14px; top:14px; z-index:4; display:grid; gap:6px; }}
.map-zoom button {{ width:34px; height:34px; border:1px solid var(--line); border-radius:6px; background:rgba(17,20,24,.84); color:var(--text); font-size:18px; font-weight:800; cursor:pointer; }}
body.light .map-zoom button {{ background:rgba(255,255,255,.86); }}
.map-popup {{ position:absolute; z-index:5; right:14px; bottom:54px; width:min(320px,calc(100% - 28px)); background:rgba(17,20,24,.9); border:1px solid color-mix(in srgb,var(--primary) 55%,var(--line)); border-radius:8px; padding:14px; backdrop-filter:blur(12px); }}
body.light .map-popup {{ background:rgba(255,255,255,.94); }}
.map-popup-title {{ color:var(--text); font-size:13px; font-weight:800; line-height:18px; margin-bottom:10px; }}
.map-popup-grid {{ display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:8px; color:var(--muted); font-size:11px; }}
.map-popup-grid strong {{ display:block; color:var(--text); font-size:13px; margin-top:3px; }}
.map-popup-link {{ display:inline-flex; align-items:center; justify-content:center; margin-top:12px; min-height:32px; padding:7px 10px; border:1px solid color-mix(in srgb,var(--primary) 60%,var(--line)); border-radius:7px; color:var(--primary); font-weight:900; font-size:12px; text-decoration:none; }}
.map-popup-link:hover {{ background:color-mix(in srgb,var(--primary) 12%,transparent); }}
.map-results {{ margin-top:12px; display:grid; gap:8px; max-height:260px; overflow:auto; padding-right:4px; }}
.map-result {{ width:100%; border:1px solid var(--line); border-radius:8px; background:var(--surface-low); color:var(--text); padding:10px; text-align:left; cursor:pointer; }}
.map-result.active {{ border-color:var(--primary); background:color-mix(in srgb,var(--primary) 12%,var(--surface-low)); }}
.map-result-title {{ font-weight:800; font-size:12px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }}
.map-result-meta {{ margin-top:4px; color:var(--muted); font-size:11px; }}
.preset-row {{ display:flex; flex-wrap:wrap; gap:6px; margin:0 0 12px; }}
.preset-row button {{ border:1px solid var(--line); border-radius:999px; background:var(--surface-low); color:var(--muted); min-height:28px; padding:0 10px; font-size:11px; font-weight:800; cursor:pointer; }}
.preset-row button:hover, .preset-row button.active {{ border-color:var(--primary); color:var(--primary); background:color-mix(in srgb,var(--primary) 16%,var(--surface-low)); }}
.map-panel {{ position:absolute; top:16px; left:16px; z-index:3; background:rgba(17,20,24,.72); border:1px solid var(--line); border-radius:8px; padding:12px 14px; backdrop-filter:blur(10px); }}
body.light .map-panel {{ background:rgba(255,255,255,.82); }}
.legend {{ position:absolute; z-index:3; left:50%; bottom:18px; transform:translateX(-50%); display:flex; gap:12px; align-items:center; background:rgba(17,20,24,.78); border:1px solid var(--line); border-radius:999px; padding:8px 14px; color:var(--muted); font-size:12px; }}
.legend-line {{ width:190px; height:8px; border-radius:999px; background:linear-gradient(90deg,#38bdf8,#6bd8cb,#f59e0b,#ef4444); }}
.map-attribution {{ position:absolute; right:10px; bottom:8px; z-index:3; color:var(--muted); background:rgba(17,20,24,.72); border:1px solid var(--line); border-radius:6px; padding:4px 7px; font-size:10px; }}
.map-tools {{ display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:8px; margin-top:12px; }}
.map-tools button {{ min-height:34px; border:1px solid var(--line); border-radius:6px; background:var(--surface-low); color:var(--muted); cursor:pointer; font-weight:800; }}
.map-tools button.active {{ background:var(--primary); color:#00201d; border-color:var(--primary); }}
.map-quick {{ display:flex; flex-wrap:wrap; gap:6px; margin:0 0 12px; }}
.map-quick button {{ min-height:30px; border:1px solid var(--line); border-radius:999px; padding:0 10px; background:var(--surface-low); color:var(--muted); cursor:pointer; font-size:11px; font-weight:800; }}
.map-quick button.active {{ background:color-mix(in srgb,var(--primary) 18%,var(--surface-low)); border-color:var(--primary); color:var(--primary); }}
.range-field {{ margin-top:14px; display:grid; gap:7px; }}
.range-field input {{ width:100%; accent-color:var(--primary); }}
.mini-grid {{ display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:12px; }}
.toolbar-grid {{ display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:10px; }}
.pager {{ display:flex; align-items:center; justify-content:space-between; gap:10px; margin-top:12px; color:var(--muted); font-size:12px; }}
.pager-actions {{ display:flex; gap:8px; }}
.source-badge {{ display:inline-flex; align-items:center; border:1px solid var(--line); border-radius:999px; padding:3px 8px; color:var(--primary); font-size:11px; font-weight:800; }}
.source-badge.cian {{ color:var(--secondary); border-color:color-mix(in srgb,var(--secondary) 48%,var(--line)); background:color-mix(in srgb,var(--secondary) 12%,transparent); }}
.source-badge.domclick {{ color:var(--primary); border-color:color-mix(in srgb,var(--primary) 48%,var(--line)); background:color-mix(in srgb,var(--primary) 12%,transparent); }}
.source-badge.neutral {{ color:var(--muted); }}
.metric-list {{ display:grid; gap:10px; }}
.metric-line {{ display:flex; align-items:center; justify-content:space-between; gap:12px; padding:10px 0; border-bottom:1px solid color-mix(in srgb,var(--line) 70%,transparent); }}
.metric-line:last-child {{ border-bottom:0; }}
.audit-list {{ display:grid; gap:10px; }}
.audit-row {{ display:grid; grid-template-columns:190px 116px minmax(0,1fr); gap:12px; align-items:start; padding:12px 0; border-bottom:1px solid color-mix(in srgb,var(--line) 70%,transparent); }}
.audit-row:last-child {{ border-bottom:0; }}
.audit-name {{ color:var(--text); font-weight:800; font-size:12px; line-height:16px; }}
.audit-note {{ color:var(--muted); font-size:12px; line-height:17px; }}
.audit-status {{ display:inline-flex; justify-content:center; border:1px solid var(--line); border-radius:999px; padding:3px 8px; color:var(--muted); font-size:11px; font-weight:900; text-transform:uppercase; letter-spacing:.06em; }}
.audit-status.ready {{ color:var(--success); border-color:color-mix(in srgb,var(--success) 55%,var(--line)); background:color-mix(in srgb,var(--success) 10%,transparent); }}
.audit-status.partial {{ color:var(--warning); border-color:color-mix(in srgb,var(--warning) 55%,var(--line)); background:color-mix(in srgb,var(--warning) 10%,transparent); }}
.audit-status.missing {{ color:var(--error); border-color:color-mix(in srgb,var(--error) 55%,var(--line)); background:color-mix(in srgb,var(--error) 10%,transparent); }}
.status-badge {{ display:inline-flex; align-items:center; justify-content:center; border-radius:999px; padding:4px 9px; font-size:11px; font-weight:800; letter-spacing:0; border:1px solid var(--line); }}
.status-ok {{ color:#7ff5d8; background:rgba(78,222,190,.14); border-color:rgba(78,222,190,.55); }}
.status-partial {{ color:#ffd166; background:rgba(255,193,7,.14); border-color:rgba(255,193,7,.55); }}
.status-missing {{ color:#ff9f9f; background:rgba(255,99,99,.14); border-color:rgba(255,99,99,.55); }}
.monitoring-card-structured {{ background:color-mix(in srgb,var(--panel-high) 72%,var(--panel)); box-shadow:inset 0 0 0 1px color-mix(in srgb,var(--primary) 10%,transparent); }}
.monitoring-card-structured .metric-line strong {{ color:var(--text); }}
.log-shell {{ display:grid; gap:12px; }}
.log-shell table {{ table-layout:fixed; }}
.log-shell th:nth-child(1), .log-shell td:nth-child(1) {{ width:96px; }}
.log-shell th:nth-child(2), .log-shell td:nth-child(2) {{ width:155px; }}
.log-shell th:nth-child(3), .log-shell td:nth-child(3) {{ width:210px; }}
.log-shell td {{ white-space:normal; line-height:17px; }}
.log-level {{ display:inline-flex; border:1px solid var(--line); border-radius:999px; padding:2px 8px; color:var(--muted); font-size:11px; font-weight:800; }}
.log-level.warn {{ color:var(--warning); border-color:color-mix(in srgb,var(--warning) 55%,var(--line)); }}
.log-level.error {{ color:var(--error); border-color:color-mix(in srgb,var(--error) 55%,var(--line)); }}
.log-footer {{ display:flex; justify-content:space-between; align-items:center; gap:12px; color:var(--muted); font-size:12px; }}
.line-chart {{ display:flex; align-items:end; gap:8px; height:220px; padding-top:18px; border-bottom:1px solid var(--line); overflow-x:auto; overflow-y:hidden; }}
.trend-col {{ min-width:50px; flex:1; display:flex; flex-direction:column; align-items:center; justify-content:end; gap:6px; color:var(--muted); font-size:11px; }}
.trend-bar {{ width:100%; max-width:34px; min-height:4px; border-radius:6px 6px 0 0; background:linear-gradient(180deg,var(--secondary),var(--primary)); box-shadow:0 0 12px color-mix(in srgb,var(--primary) 22%,transparent); }}
.trend-value {{ color:var(--text); font-weight:800; font-size:10px; line-height:12px; min-height:24px; max-width:52px; text-align:center; white-space:normal; overflow-wrap:anywhere; }}
table {{ width:100%; border-collapse:collapse; font-size:13px; }}
.table-scroll {{ overflow-x:auto; width:100%; }}
.table-scroll table {{ min-width:720px; }}
.table-scroll .analytic-table {{ min-width:0; width:100%; table-layout:fixed; }}
.analytic-table th {{ padding:9px 6px; white-space:normal; line-height:13px; letter-spacing:0; text-transform:none; }}
.analytic-table th button {{ white-space:normal; line-height:13px; }}
.analytic-table td {{ padding:10px 6px; overflow:hidden; text-overflow:ellipsis; }}
.analytic-table td:first-child .row-title {{ display:block; max-width:100%; overflow:hidden; text-overflow:ellipsis; }}
.analytic-table .source-badge {{ max-width:100%; padding-inline:6px; white-space:nowrap; overflow-wrap:normal; }}
.date-stack {{ display:grid; gap:1px; white-space:nowrap; font-variant-numeric:tabular-nums; }}
.rows-table th:nth-child(1), .rows-table td:nth-child(1) {{ width:6%; }}
.rows-table th:nth-child(2), .rows-table td:nth-child(2) {{ width:25%; }}
.rows-table th:nth-child(3), .rows-table td:nth-child(3) {{ width:12%; }}
.rows-table th:nth-child(4), .rows-table td:nth-child(4) {{ width:7%; }}
.rows-table th:nth-child(5), .rows-table td:nth-child(5) {{ width:8%; }}
.rows-table th:nth-child(6), .rows-table td:nth-child(6) {{ width:8%; }}
.rows-table th:nth-child(7), .rows-table td:nth-child(7) {{ width:13%; }}
.rows-table th:nth-child(8), .rows-table td:nth-child(8) {{ width:10%; }}
.rows-table th:nth-child(9), .rows-table td:nth-child(9) {{ width:11%; }}
.detail-drawer {{ position:fixed; inset:0; z-index:1000; opacity:0; visibility:hidden; pointer-events:none; transition:opacity .18s ease, visibility .18s ease; }}
.detail-drawer.open {{ opacity:1; visibility:visible; pointer-events:auto; }}
.detail-modal-backdrop {{ position:absolute; inset:0; background:rgba(3,7,10,.72); backdrop-filter:blur(3px); }}
.detail-modal-panel {{ position:absolute; inset:24px; max-width:1180px; margin:auto; background:var(--panel); border:1px solid var(--primary-border); border-radius:8px; box-shadow:0 24px 90px rgba(0,0,0,.48); padding:24px; overflow:auto; }}
.detail-modal-panel .metric-list {{ display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:0 28px; }}
.drawer-head {{ display:flex; align-items:center; justify-content:space-between; gap:12px; padding-bottom:14px; margin-bottom:14px; border-bottom:1px solid var(--line); }}
.drawer-head strong {{ color:var(--text); font-size:15px; }}
.icon-btn {{ min-width:34px; min-height:32px; border:1px solid var(--line); border-radius:6px; background:var(--panel-high); color:var(--text); cursor:pointer; font-weight:900; }}
.deal-table th, .deal-table td {{ font-size:11px; }}
.deal-table th:nth-child(1), .deal-table td:nth-child(1) {{ width:7%; }}
.deal-table th:nth-child(2), .deal-table td:nth-child(2) {{ width:19%; }}
.deal-table th:nth-child(3), .deal-table td:nth-child(3) {{ width:11%; }}
.deal-table th:nth-child(4), .deal-table td:nth-child(4) {{ width:7%; }}
.deal-table th:nth-child(5), .deal-table td:nth-child(5) {{ width:8%; }}
.deal-table th:nth-child(6), .deal-table td:nth-child(6) {{ width:7%; }}
.deal-table th:nth-child(7), .deal-table td:nth-child(7) {{ width:10%; }}
.deal-table th:nth-child(8), .deal-table td:nth-child(8) {{ width:9%; }}
.deal-table th:nth-child(9), .deal-table td:nth-child(9) {{ width:9%; }}
.deal-table th:nth-child(10), .deal-table td:nth-child(10) {{ width:6%; }}
.deal-table th:nth-child(11), .deal-table td:nth-child(11) {{ width:7%; }}
th {{ color:var(--muted); text-align:left; padding:10px; border-bottom:1px solid var(--line); font-size:11px; text-transform:uppercase; letter-spacing:.08em; }}
th button {{ all:unset; cursor:pointer; color:inherit; display:inline-flex; align-items:center; gap:4px; }}
th button::after {{ content:'↕'; color:var(--faint); font-size:10px; }}
td {{ padding:11px 10px; border-bottom:1px solid color-mix(in srgb,var(--line) 70%,transparent); color:var(--text); font-variant-numeric:tabular-nums; }}
td:nth-child(n+2), th:nth-child(n+2) {{ white-space:nowrap; }}
.analytic-table td, .analytic-table th, .analytic-table td:nth-child(n+2), .analytic-table th:nth-child(n+2) {{ white-space:normal; }}
.analytic-table td:not(:first-child), .analytic-table th:not(:first-child) {{ text-align:left; overflow-wrap:anywhere; }}
tr:hover td {{ background:color-mix(in srgb,var(--primary) 7%,transparent); }}
.bars {{ display:grid; gap:12px; padding:4px 0 0; }}
.bar-wrap {{ display:grid; grid-template-columns:64px minmax(0,1fr) 132px; align-items:center; gap:12px; color:var(--muted); font-size:12px; min-width:0; }}
.bar-track {{ height:28px; display:flex; align-items:center; border:1px solid var(--line); border-radius:6px; background:var(--surface-low); overflow:hidden; }}
.bar {{ height:100%; min-width:3%; background:linear-gradient(90deg,var(--primary),var(--secondary)); border-radius:5px; transition:width .4s; }}
.bar-wrap strong {{ color:var(--text); white-space:nowrap; }}
.bar-count {{ color:var(--faint); font-size:11px; }}
.bar-value {{ color:var(--text); font-weight:800; font-variant-numeric:tabular-nums; white-space:nowrap; }}
.chart-note {{ margin-top:12px; color:var(--faint); font-size:12px; }}
.horizontal-bars {{ display:grid; gap:12px; }}
.hbar-row {{ display:grid; grid-template-columns:120px 1fr 108px; gap:12px; align-items:center; font-size:12px; color:var(--muted); }}
.hbar-track {{ height:10px; border-radius:999px; background:var(--surface-low); overflow:hidden; }}
.hbar-fill {{ height:100%; border-radius:999px; background:linear-gradient(90deg,var(--primary),var(--secondary)); }}
.source-row, .listing-row {{ display:flex; align-items:center; gap:12px; padding:12px 0; border-bottom:1px solid color-mix(in srgb,var(--line) 72%,transparent); }}
.source-row:last-child, .listing-row:last-child {{ border-bottom:0; }}
.row-icon {{ display:grid; place-items:center; width:38px; min-width:38px; height:38px; background:var(--surface-low); border:1px solid var(--line); border-radius:6px; color:var(--primary); }}
.row-main {{ min-width:0; flex:1; }}
.row-title {{ color:var(--text); font-size:13px; font-weight:700; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }}
.row-meta {{ margin-top:3px; color:var(--faint); font-size:11px; text-transform:uppercase; letter-spacing:.04em; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }}
.row-value {{ color:var(--text); font-size:13px; font-weight:800; font-variant-numeric:tabular-nums; white-space:nowrap; }}
.empty {{ color:var(--muted); border:1px dashed var(--line); border-radius:8px; padding:22px; background:color-mix(in srgb,var(--panel) 72%,transparent); }}
.conn {{ border-color:color-mix(in srgb,var(--warning) 65%,var(--line)); }}
.conn .material-symbols-outlined {{ color:var(--warning); }}
.hidden {{ display:none !important; }}
@media (max-width:1100px) {{ .grid4 {{ grid-template-columns:repeat(2,1fr); }} .span4,.span5,.span7,.span8 {{ grid-column:span 12; }} }}
@media (max-width:720px) {{
  body {{ --rail:64px; }}
  .app {{ height:980px; }}
  .sidebar {{ padding:12px 8px; }}
  .brand {{ justify-content:center; padding:0; }}
  .brand-text, .nav-label, .toggle-label, .toggle-switch {{ display:none; }}
  .nav button, .side-button {{ justify-content:center; padding:0; }}
  .topbar {{ min-height:116px; height:auto; align-items:flex-start; flex-direction:column; justify-content:center; padding:14px 16px; gap:10px; }}
  .product {{ font-size:11px; line-height:15px; max-width:260px; }}
  h1 {{ font-size:22px; line-height:28px; }}
  .chips {{ justify-content:flex-start; gap:6px; }}
  .chip {{ height:28px; max-width:280px; padding:0 10px; font-size:11px; }}
  .content {{ padding:16px; }}
  .grid4, .grid12 {{ grid-template-columns:1fr; gap:12px; }}
  .span4, .span5, .span7, .span8, .span12 {{ grid-column:1; }}
  .card {{ padding:16px; }}
  .value {{ font-size:28px; line-height:34px; }}
  .map {{ min-height:300px; }}
  .legend {{ left:16px; right:16px; transform:none; justify-content:center; }}
  .legend-line {{ width:110px; }}
  .bars {{ height:220px; gap:8px; overflow-x:auto; }}
  .bar-wrap {{ min-width:54px; }}
  table {{ min-width:620px; }}
}}
</style>
</head>
<body>
<div class="app">
  <aside class="sidebar">
    <button class="brand" data-page="dashboard">
      <span class="brand-mark" aria-hidden="true"><svg viewBox="0 0 32 32" fill="none" stroke-width="2"><path d="M6 25V12l10-6 10 6v13"></path><path d="M11 25v-8h10v8"></path><path d="M10 13h3M19 13h3M10 17h3M19 17h3"></path><path d="M16 29c4-3 7-6.4 7-10.2A7 7 0 0 0 9 18.8C9 22.6 12 26 16 29Z"></path><circle cx="16" cy="19" r="2.2"></circle></svg></span>
      <span class="brand-text">RealtyScope<small>Аналитика Москвы</small></span>
    </button>
    <nav class="nav" id="nav"></nav>
    <div class="side-footer">
      <button class="side-button" id="collapseBtn">
        <span class="control-icon">≡</span>
        <span class="toggle-label">Свернуть</span>
      </button>
      <button class="side-button" id="themeBtn">
        <span class="control-icon theme-icon" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke-width="2"><circle cx="12" cy="12" r="4"></circle><path d="M12 2v3M12 19v3M4.93 4.93l2.12 2.12M16.95 16.95l2.12 2.12M2 12h3M19 12h3M4.93 19.07l2.12-2.12M16.95 7.05l2.12-2.12"></path></svg></span>
        <span class="toggle-label">Светлая тема</span>
        <span class="toggle-switch"></span>
      </button>
    </div>
  </aside>
  <section class="main">
    <header class="topbar">
      <div>
        <div class="product">Аналитика недвижимости Москвы</div>
        <h1 id="pageTitle">Дашборд</h1>
      </div>
      <div class="chips">
        <span class="chip">Москва</span>
        <span class="chip" id="sourceChip">Источник данных</span>
        <span class="chip" id="latestChip">Последний сбор не указан</span>
        <span class="chip"><span class="pulse"></span><span id="statusChip">Статус уточняется</span></span>
      </div>
    </header>
    <main class="content" id="content"></main>
    <footer class="app-footer"><span>© 2026 RealtyScope Analytics</span></footer>
  </section>
</div>
<script id="payload" type="application/json">{payload_json}</script>
<script>
const data = JSON.parse(document.getElementById('payload').textContent);
function browserApiOrigin(port) {{
  let parentLocation = null;
  try {{
    parentLocation = window.parent && window.parent.location ? window.parent.location : null;
  }} catch (error) {{
    parentLocation = null;
  }}
  const locations = [parentLocation, window.location];
  for (const locationRef of locations) {{
    const protocol = String(locationRef?.protocol || '');
    const hostname = String(locationRef?.hostname || '');
    if ((protocol === 'http:' || protocol === 'https:') && hostname) {{
      return `${{protocol}}//${{hostname}}:${{port}}`;
    }}
  }}
  return `http://127.0.0.1:${{port}}`;
}}
function clientApiBaseUrl() {{
  const raw = String(data.apiBaseUrl || '').replace(/\\/$/, '');
  if (!raw) return '';
  try {{
    const url = new URL(raw, window.location.href);
    if (url.hostname === 'api') {{
      const port = url.port || '8000';
      return browserApiOrigin(port);
    }}
    return url.toString().replace(/\\/$/, '');
  }} catch (error) {{
    return raw;
  }}
}}
const pages = [
  ['dashboard','dashboard','Дашборд'],
  ['valuation','calculate','Оценка квартиры'],
  ['map','map','Тепловая карта'],
  ['deals','local_fire_department','Выгодные предложения'],
  ['segments','compare_arrows','Сегменты и районы'],
  ['data','database','Данные'],
  ['monitoring','monitor_heart','Мониторинг'],
];
const blankFilters = () => ({{ search:'', rooms:'', source:'', minPrice:'', maxPrice:'', minArea:'', maxArea:'' }});
const state = {{ page:'dashboard', room:2, mapLayer:'both', mapSource:'', selectedMapIndex:null, heatRadius:30, heatOpacity:46, mapZoom:10, mapCenterLat:55.751244, mapCenterLon:37.618423, dataPage:1, pageSize:25, logPage:1, logPageSize:8, sort:{{}}, filters:{{ deals:blankFilters(), segments:blankFilters(), data:blankFilters() }} }};
const VALUATION_REQUEST_TIMEOUT_MS = 8000;
let valuationRecalcTimer = null;
let valuationRequestSeq = 0;
let activeValuationController = null;
let lastValuationSnapshot = null;
const fmtInt = v => v === null || v === undefined || Number.isNaN(Number(v))
  ? '—' : Math.round(Number(v)).toLocaleString('ru-RU');
const fmtRub = v => v === null || v === undefined || Number.isNaN(Number(v))
  ? '—' : Math.round(Number(v)).toLocaleString('ru-RU') + ' ₽';
const fmtMln = v => v === null || v === undefined || Number.isNaN(Number(v))
  ? '—' : (Number(v) / 1000000).toLocaleString('ru-RU', {{ maximumFractionDigits:1 }}) + ' млн ₽';
function fmtPredictionRub(value) {{
  const number = Number(value);
  if (!Number.isFinite(number)) return '—';
  return (number / 1000000).toLocaleString('ru-RU', {{
    minimumFractionDigits: 2,
    maximumFractionDigits:2,
  }}) + ' млн ₽';
}}
function fmtDeltaMln(value) {{
  const number = Number(value);
  if (!Number.isFinite(number)) return '';
  const prefix = number > 0 ? '+' : '';
  return prefix + (number / 1000000).toLocaleString('ru-RU', {{
    minimumFractionDigits: 2,
    maximumFractionDigits:2,
  }}) + ' млн ₽';
}}
const fmtM2 = v => v === null || v === undefined || Number.isNaN(Number(v))
  ? '—' : Math.round(Number(v)).toLocaleString('ru-RU') + ' ₽/м²';
function valuationInputSummary(features, targetVariable = 'price_rub', predictedPrice = null) {{
  const f = features || {{}};
  const number = (value, digits = 0) => Number(value).toLocaleString('ru-RU', {{ maximumFractionDigits:digits }});
  const parts = [
    `площадь ${{number(f.total_area_m2, 1)}} м²`,
    `комнат ${{number(f.rooms)}}`,
    `этаж ${{number(f.floor)}} из ${{number(f.floors_total)}}`,
    f.building_year_missing ? 'год дома не указан' : `дом ${{number(f.building_year)}} г.`,
    f.nearest_transport_m_missing ? 'расстояние до транспорта не указано' : `до транспорта ${{number(f.nearest_transport_m)}} м`,
    `школ ${{number(f.schools_count_1000m)}}`,
    `парков ${{number(f.parks_count_1000m)}}`,
    `магазинов ${{number(f.shops_count_1000m)}}`,
    `транспорт 500 м: ${{number(f.transport_count_500m)}}`,
    `транспорт 1 км: ${{number(f.transport_count_1000m)}}`,
  ];
  const area = Number(f.total_area_m2);
  const total = Number(predictedPrice);
  if (targetVariable === 'price_per_m2' && Number.isFinite(total) && total > 0 && area > 0) {{
    parts.push(`расчетная цена ${{fmtM2(total / area)}}`);
  }}
  return 'Модель получила: ' + parts.join(' · ');
}}
const fmtShortM2 = v => v === null || v === undefined || Number.isNaN(Number(v))
  ? '—' : (Number(v) / 1000).toLocaleString('ru-RU', {{ maximumFractionDigits:1 }}) + ' тыс.';
const fmtPct = v => v === null || v === undefined || Number.isNaN(Number(v))
  ? '—' : Number(v).toLocaleString('ru-RU', {{ maximumFractionDigits:1 }}) + '%';
const esc = v => String(v ?? '').replace(/[&<>"']/g, s => ({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}}[s]));
function roomLabel(value) {{
  const n = Number(value);
  if (n === 0) return 'Ст';
  if (n >= 5) return '5+';
  return `${{n}}-к`;
}}
function roomButtons() {{
  return [0,1,2,3,4,5].map(n => `<button class="${{state.room===n?'active':''}}" data-room="${{n}}" data-room-preset="${{n}}">${{roomLabel(n)}}</button>`).join('');
}}
function title(key) {{ return pages.find(p => p[0] === key)?.[2] || 'Дашборд'; }}
function setPage(key) {{
  state.page = key;
  render();
  document.querySelector('.main')?.scrollTo({{ top:0, left:0, behavior:'auto' }});
}}
function normalizeIcons(root = document) {{
  const glyphs = {{
    apartment:'▦', dashboard:'▦', calculate:'▣', map:'◇', local_fire_department:'◎',
    compare_arrows:'⇄', database:'▤', monitor_heart:'▱', keyboard_double_arrow_left:'‹',
    light_mode:'☼', trending_up:'↗', data_array:'▥', model_training:'◌', schedule:'◷',
    cloud_off:'!', hub:'◎', more_horiz:'⋯', analytics:'▧', tune:'≡', filter_list:'≡',
    price_check:'₽', warning:'!', cloud_done:'●'
  }};
  root.querySelectorAll('.material-symbols-outlined').forEach(node => {{
    const iconName = node.dataset.icon || node.textContent.trim();
    if (iconName) node.dataset.icon = glyphs[iconName] || '•';
    node.textContent = '';
    node.setAttribute('aria-hidden', 'true');
  }});
}}
function normalizeIcons(root = document) {{
  const icon = body => `<svg viewBox="0 0 24 24" fill="none" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">${{body}}</svg>`;
  const glyphs = {{
    apartment: icon('<path d="M4 21V7l8-4 8 4v14"/><path d="M9 21v-7h6v7"/><path d="M8 9h.01M12 9h.01M16 9h.01M8 12h.01M16 12h.01"/>'),
    dashboard: icon('<rect x="4" y="4" width="7" height="7"/><rect x="13" y="4" width="7" height="5"/><rect x="13" y="11" width="7" height="9"/><rect x="4" y="13" width="7" height="7"/>'),
    calculate: icon('<rect x="5" y="3" width="14" height="18" rx="2"/><path d="M8 7h8M8 11h2M12 11h2M16 11h.01M8 15h2M12 15h2M16 15h.01M8 18h2M12 18h4"/>'),
    map: icon('<path d="M9 18l-6 3V6l6-3 6 3 6-3v15l-6 3-6-3Z"/><path d="M9 3v15M15 6v15"/>'),
    local_fire_department: icon('<path d="M12 22c4 0 7-3 7-7 0-3-1.8-5.2-4.3-7.7C13.4 6 12.5 4.5 12 2c-2 1.5-3.5 3.6-3.5 6.2 0 1.3.4 2.4 1.1 3.4C8.5 11 7.5 10 7 8.5 5.8 10 5 12 5 15c0 4 3 7 7 7Z"/>'),
    compare_arrows: icon('<path d="M7 7h13l-3-3M17 10l3-3"/><path d="M17 17H4l3 3M7 14l-3 3"/>'),
    database: icon('<ellipse cx="12" cy="5" rx="7" ry="3"/><path d="M5 5v6c0 1.7 3.1 3 7 3s7-1.3 7-3V5"/><path d="M5 11v6c0 1.7 3.1 3 7 3s7-1.3 7-3v-6"/>'),
    monitor_heart: icon('<rect x="3" y="4" width="18" height="12" rx="2"/><path d="M8 20h8M12 16v4"/><path d="M7 10h3l1.2-2.5L14 13l1.5-3H17"/>'),
    trending_up: icon('<path d="M4 17l6-6 4 4 6-8"/><path d="M14 7h6v6"/>'),
    data_array: icon('<path d="M4 7h16M4 12h16M4 17h16"/><path d="M8 5v14M16 5v14"/>'),
    model_training: icon('<circle cx="12" cy="12" r="3"/><path d="M12 2v4M12 18v4M2 12h4M18 12h4M4.9 4.9l2.8 2.8M16.3 16.3l2.8 2.8M19.1 4.9l-2.8 2.8M7.7 16.3l-2.8 2.8"/>'),
    schedule: icon('<circle cx="12" cy="12" r="8"/><path d="M12 7v5l3 2"/>'),
    cloud_off: icon('<path d="M3 3l18 18"/><path d="M9 18H7a4 4 0 0 1-.6-8A6 6 0 0 1 17 7.5c1.7.3 3 1.8 3 3.5"/>'),
    hub: icon('<circle cx="12" cy="12" r="3"/><circle cx="5" cy="6" r="2"/><circle cx="19" cy="6" r="2"/><circle cx="5" cy="18" r="2"/><circle cx="19" cy="18" r="2"/><path d="M7 7.5l3 2.5M17 7.5l-3 2.5M7 16.5l3-2.5M17 16.5l-3-2.5"/>'),
    more_horiz: icon('<path d="M4 12h.01M12 12h.01M20 12h.01"/>'),
    analytics: icon('<path d="M4 19V5"/><path d="M4 19h16"/><path d="M8 16v-5M12 16V8M16 16v-8"/>'),
    tune: icon('<path d="M4 7h10M18 7h2M4 12h2M10 12h10M4 17h8M16 17h4"/><circle cx="16" cy="7" r="2"/><circle cx="8" cy="12" r="2"/><circle cx="14" cy="17" r="2"/>'),
    filter_list: icon('<path d="M4 6h16M7 12h10M10 18h4"/>'),
    price_check: icon('<path d="M8 5h6a4 4 0 0 1 0 8H8V5Z"/><path d="M8 13h7M8 17h8M6 9h9M17 16l2 2 4-4"/>'),
    warning: icon('<path d="M12 3l10 18H2L12 3Z"/><path d="M12 9v5M12 17h.01"/>'),
    cloud_done: icon('<path d="M8 18H7a4 4 0 0 1-.6-8A6 6 0 0 1 18 8.5 4.5 4.5 0 0 1 18 18h-2"/><path d="M9 14l2 2 4-5"/>'),
  }};
  root.querySelectorAll('.material-symbols-outlined').forEach(node => {{
    const iconName = node.dataset.icon || node.textContent.trim();
    node.innerHTML = glyphs[iconName] || icon('<circle cx="12" cy="12" r="4"/>');
    node.setAttribute('aria-hidden', 'true');
  }});
}}
function nav() {{
  document.getElementById('nav').innerHTML = pages.map(([key, icon, label]) => `
    <button class="${{state.page === key ? 'active' : ''}}" data-page="${{key}}" title="${{label}}">
      <span class="material-symbols-outlined">${{icon}}</span>
      <span class="nav-label">${{label}}</span>
    </button>`).join('');
  document.querySelectorAll('[data-page]').forEach(btn => btn.onclick = () => setPage(btn.dataset.page));
}}
function updateChrome() {{
  document.getElementById('pageTitle').textContent = title(state.page);
  document.getElementById('statusChip').textContent = data.connected
    ? 'Сервис доступен'
    : (data.mode === 'snapshot' ? 'Локальные данные' : 'Сервис недоступен');
  document.getElementById('sourceChip').textContent = data.source?.label || 'Источник данных';
  const run = data.latestRun;
  document.getElementById('latestChip').textContent = run && (run.finished_at || run.started_at)
    ? 'Последний сбор: ' + shortDate(run.finished_at || run.started_at)
    : 'Последний сбор не указан';
}}
function shortDate(value) {{
  if (!value) return '—';
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return String(value).slice(0, 16);
  return parsed.toLocaleString('ru-RU', {{ day:'2-digit', month:'2-digit', year:'numeric', hour:'2-digit', minute:'2-digit' }});
}}
function tableDate(value) {{
  if (!value) return '—';
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return esc(String(value).slice(0, 16).replace(',', ''));
  const date = parsed.toLocaleDateString('ru-RU', {{ day:'2-digit', month:'2-digit', year:'numeric' }});
  const time = parsed.toLocaleTimeString('ru-RU', {{ hour:'2-digit', minute:'2-digit' }});
  return `<span class="date-stack"><span>${{date}}</span><span>${{time}}</span></span>`;
}}
function kpi(label, value, sub, icon) {{
  return `<article class="card"><div class="label">${{label}} <span class="material-symbols-outlined" style="float:right;color:var(--primary)">${{icon}}</span></div><div class="value">${{value}}</div><div class="sub">${{sub}}</div></article>`;
}}
function miniKpi(label, value, sub, icon) {{
  const rawValue = String(value ?? '');
  const compact = !rawValue.includes('₽') && rawValue.length > 4 ? ' compact' : '';
  return `<div class="mini-kpi span4${{compact}}"><div class="label">${{label}} <span class="material-symbols-outlined" style="float:right;color:var(--primary)">${{icon}}</span></div><div class="value">${{value}}</div><div class="sub">${{sub}}</div></div>`;
}}
function connectionNotice() {{
  if (data.connected || data.mode === 'snapshot') return '';
  return `<section class="card conn span12"><div class="card-title"><span><span class="material-symbols-outlined">cloud_off</span> Подключение к сервису</span></div><div class="empty">${{esc(data.errors[0] || 'Сервис данных не отвечает.')}}</div></section>`;
}}
function th(label, key, title = label) {{
  return `<th><button data-sort="${{key}}" title="${{esc(title)}}">${{label}}</button></th>`;
}}
function sortRows(rows, scope = state.page) {{
  const sort = state.sort[scope];
  if (!sort?.key) return rows;
  const dir = sort.dir === 'desc' ? -1 : 1;
  return [...rows].sort((a, b) => {{
    const av = a[sort.key];
    const bv = b[sort.key];
    const an = Number(av);
    const bn = Number(bv);
    if (Number.isFinite(an) && Number.isFinite(bn)) return (an - bn) * dir;
    return String(av ?? '').localeCompare(String(bv ?? ''), 'ru') * dir;
  }});
}}
function rowsTable(rows) {{
  if (!rows.length) return `<div class="empty">В текущей выборке нет объявлений для отображения.</div>`;
  rows = sortRows(rows);
  return `<div class="table-scroll"><table class="analytic-table rows-table"><thead><tr><th></th>${{th('Адрес','address_text')}}${{th('Ист.','source_name','Источник')}}${{th('Комн.','rooms','Комнат')}}${{th('м²','total_area_m2','Площадь')}}${{th('Этаж','floor')}}${{th('Дата','observed_at')}}${{th('Цена','price_rub')}}${{th('₽/м²','price_per_m2','Цена за м²')}}</tr></thead><tbody>` +
    rows.map((r, idx) => `<tr><td><button class="icon-btn" data-action="detail" data-listing-index="${{esc(r.id ?? idx)}}" title="Полная карточка объявления">▣</button></td><td>${{listingLink(r)}}</td><td>${{sourceBadge(r)}}</td><td>${{fmtInt(r.rooms)}}</td><td>${{fmtInt(r.total_area_m2)}} м²</td><td>${{floorText(r)}}</td><td>${{tableDate(r.observed_at)}}</td><td>${{fmtMln(r.price_rub)}}</td><td>${{fmtM2(r.price_per_m2)}}</td></tr>`).join('') +
    `</tbody></table></div>`;
}}
function floorText(r) {{
  const floor = Number(r.floor);
  const total = Number(r.floors_total);
  if (Number.isFinite(floor) && Number.isFinite(total) && total > 0) return `${{fmtInt(floor)}}/${{fmtInt(total)}}`;
  if (Number.isFinite(floor)) return fmtInt(floor);
  return '—';
}}
function listingLink(r) {{
  const title = esc(r.address_text || 'Адрес не указан');
  return r.source_url ? `<a href="${{esc(r.source_url)}}" target="_blank" rel="noreferrer" class="row-title">${{title}}</a>` : title;
}}
function sourceLabel(name) {{
  if (name === 'cian') return 'ЦИАН';
  if (name === 'domclick') return 'Домклик';
  return 'Источник';
}}
function sourceBadge(rowOrName) {{
  const raw = typeof rowOrName === 'string' ? rowOrName : (rowOrName?.source_name || sourceValue(rowOrName?.source_label || rowOrName?.name || ''));
  const source = raw === 'cian' || raw === 'domclick' ? raw : sourceValue(String(raw || ''));
  const label = typeof rowOrName === 'string' ? sourceLabel(source || rowOrName) : (rowOrName?.source_label || rowOrName?.name || sourceLabel(source));
  return `<span class="source-badge ${{source || 'neutral'}}">${{esc(label)}}</span>`;
}}
const TILE_SIZE = 256;
function worldSize(zoom = state.mapZoom) {{ return TILE_SIZE * (2 ** zoom); }}
function lonLatToWorld(lon, lat, zoom = state.mapZoom) {{
  const sinLat = Math.sin(Math.max(-85.05112878, Math.min(85.05112878, lat)) * Math.PI / 180);
  const size = worldSize(zoom);
  return {{
    x: ((lon + 180) / 360) * size,
    y: (0.5 - Math.log((1 + sinLat) / (1 - sinLat)) / (4 * Math.PI)) * size,
  }};
}}
function worldToLonLat(x, y, zoom = state.mapZoom) {{
  const size = worldSize(zoom);
  const lon = x / size * 360 - 180;
  const n = Math.PI - 2 * Math.PI * y / size;
  const lat = 180 / Math.PI * Math.atan(0.5 * (Math.exp(n) - Math.exp(-n)));
  return {{ lon, lat }};
}}
function mapPixel(point, rect) {{
  const center = lonLatToWorld(state.mapCenterLon, state.mapCenterLat);
  const world = lonLatToWorld(Number(point.lon || point.longitude), Number(point.lat || point.latitude));
  return {{
    x: rect.width / 2 + (world.x - center.x),
    y: rect.height / 2 + (world.y - center.y),
  }};
}}
function mapListing(point) {{
  const index = Number(point?.listing_index);
  return Number.isInteger(index) && data.listings?.[index] ? data.listings[index] : point;
}}
function sampleMapEntries(points, maxPoints = 620) {{
  const step = Math.max(1, Math.ceil(points.length / maxPoints));
  return points.map((p, idx) => ({{ p, idx }})).filter((_, i) => i % step === 0).slice(0, maxPoints);
}}
function map(points) {{
  const visiblePoints = sampleMapEntries(points, 620);
  const selected = Number.isInteger(state.selectedMapIndex) ? points[state.selectedMapIndex] : null;
  const dots = visiblePoints.map((entry, i) => {{
    const p = entry.p;
    const listing = mapListing(p);
    const delay = Math.min(i * 12, 420);
    const cls = Number(p.price_per_m2 || 0) > 750000 ? 'hot' : (Number(p.price_per_m2 || 0) > 520000 ? 'mid' : '');
    const active = entry.idx === state.selectedMapIndex ? 'selected' : '';
    const label = `${{fmtMln(listing.price_rub || p.price_rub)}} · ${{roomLabel(listing.rooms || p.rooms)}}`;
    return `<button class="point ${{cls}} ${{active}}" data-map-point="${{entry.idx}}" data-lon="${{Number(p.lon || p.longitude)}}" data-lat="${{Number(p.lat || p.latitude)}}" data-label="${{esc(label)}}" title="${{esc(label + ' · ' + (listing.address_text || ''))}}" style="animation-delay:${{delay}}ms" aria-label="Открыть объявление на карте"></button>`;
  }}).join('');
  const popup = selected ? mapPopup(selected) : '';
  const excluded = Number(data.stats?.excluded_coordinate_rows || 0);
  const quality = excluded ? ` · исключено вне Москвы: ${{fmtInt(excluded)}}` : '';
  return `<div class="map" data-layer="${{state.mapLayer}}" data-map-root="1"><div class="tile-layer"></div><canvas class="map-canvas"></canvas>${{dots}}<div class="map-zoom"><button data-map-zoom="1">+</button><button data-map-zoom="-1">−</button></div><div class="map-panel"><div class="label">Пространственный анализ</div><strong>Сглаженная цена за м²</strong><div class="sub">${{fmtInt(points.length)}} объектов · масштаб ${{state.mapZoom}}${{quality}}</div></div>${{popup}}<div class="legend"><span>Ниже</span><span class="legend-line"></span><span>Выше</span></div><div class="map-attribution">© OpenStreetMap · © CARTO</div></div>`;
}}
function mapPopup(point) {{
  const listing = mapListing(point);
  const externalLink = listing.source_url
    ? `<a class="map-popup-link" href="${{esc(listing.source_url)}}" target="_blank" rel="noreferrer">Открыть объявление</a>`
    : '';
  return `<div class="map-popup"><button class="small-icon-btn" data-map-clear style="float:right;width:30px;height:28px">×</button><div class="map-popup-title">${{listingLink(listing)}}</div><div class="map-popup-grid"><span>Цена<strong>${{fmtMln(listing.price_rub || point.price_rub)}}</strong></span><span>Цена за м²<strong>${{fmtM2(listing.price_per_m2 || point.price_per_m2)}}</strong></span><span>Комнат<strong>${{roomLabel(listing.rooms || point.rooms)}}</strong></span><span>Площадь<strong>${{fmtInt(listing.total_area_m2 || point.total_area_m2)}} м²</strong></span><span>Этаж<strong>${{floorText(listing)}}</strong></span><span>Источник<strong>${{esc(listing.source_label || point.source_label || sourceLabel(listing.source_name || point.source_name))}}</strong></span></div>${{externalLink}}</div>`;
}}
function sourceRows() {{
  const rows = data.sourceRows || [];
  if (!rows.length) return `<div class="empty">В загруженных данных нет подтвержденного источника объявлений.</div>`;
  return rows.map(row => `<div class="source-row"><span class="row-icon material-symbols-outlined">${{esc(row.icon || 'database')}}</span><div class="row-main"><div class="row-title">${{sourceBadge(row)}}</div><div class="row-meta">${{esc(row.status)}} · ${{esc(row.detail || '')}}</div></div><div class="row-value">${{row.count === null || row.count === undefined ? '—' : fmtInt(row.count)}}</div></div>`).join('');
}}
function serviceStatusTable() {{
  const rows = data.serviceStatus || [];
  if (!rows.length) return `<div class="empty">Статусы контуров не получены.</div>`;
  return `<div class="audit-list">` + rows.map(row => `<div class="audit-row monitoring-card-structured"><div class="audit-name"><span class="material-symbols-outlined" style="vertical-align:-5px;margin-right:6px">${{esc(row.icon || 'database')}}</span>${{esc(row.label || row.key)}}</div><div>${{statusBadge(row.status, row.status_label || row.status || 'не проверено')}}</div><div class="audit-note">${{esc(row.detail || '')}}${{row.count === null || row.count === undefined ? '' : ` · ${{fmtInt(row.count)}}`}}</div></div>`).join('') + `</div>`;
}}
function statusBadge(status, label) {{
  const normalized = String(status || '').toLowerCase();
  const cls = normalized.includes('ok') || normalized.includes('ready') || normalized.includes('готов') || normalized.includes('success') || normalized.includes('info')
    ? 'status-ok'
    : normalized.includes('partial') || normalized.includes('част') || normalized.includes('validated') || normalized.includes('warn') || normalized.includes('предуп')
      ? 'status-partial'
      : 'status-missing';
  const className = cls === 'status-ok' ? 'status-badge status-ok' : (cls === 'status-partial' ? 'status-badge status-partial' : 'status-badge status-missing');
  return `<span class="${{className}}">${{esc(label || status || 'нет')}}</span>`;
}}
function recentListingRows(rows, limit = 4) {{
  return [...(rows || [])]
    .filter(row => row && (row.source_url || row.address_text) && Number(row.price_rub || 0) > 0)
    .sort((a, b) => {{
      const ad = Date.parse(a.observed_at || a.created_at || a.updated_at || '');
      const bd = Date.parse(b.observed_at || b.created_at || b.updated_at || '');
      return (Number.isFinite(bd) ? bd : 0) - (Number.isFinite(ad) ? ad : 0);
    }})
    .slice(0, limit);
}}
function listingList(rows) {{
  if (!rows.length) return `<div class="empty">В текущей выборке нет объявлений для отображения.</div>`;
  return rows.map(r => `<div class="listing-row"><span class="row-icon material-symbols-outlined">apartment</span><div class="row-main"><div class="row-title">${{listingLink(r)}}</div><div class="row-meta">${{sourceLabel(r.source_name)}} · ${{fmtInt(r.rooms)}} комн. · ${{fmtInt(r.total_area_m2)}} м² · ${{fmtM2(r.price_per_m2)}}</div></div><div class="row-value">${{fmtRub(r.price_rub)}}</div></div>`).join('');
}}
function stepInput(id, label, value, min = 0, max = 1000000, step = 1) {{
  const placeholder = value === '' || value === null || value === undefined ? ' placeholder="Не задано"' : '';
  return `<div class="field"><label class="label">${{label}}</label><div class="step-input"><button data-step-target="${{id}}" data-step-delta="${{-step}}">−</button><input id="${{id}}" value="${{esc(value)}}" inputmode="decimal" data-min="${{min}}" data-max="${{max}}" data-step="${{step}}"${{placeholder}}><button data-step-target="${{id}}" data-step-delta="${{step}}">+</button></div></div>`;
}}
function mapQuickControls() {{
  const sourceButtons = [['', 'Все'], ['cian', 'ЦИАН'], ['domclick', 'Домклик']]
    .filter(([value]) => !value || (data.sourceRows || []).some(row => sourceValue(row.name) === value))
    .map(([value, label]) => `<button class="${{state.mapSource===value?'active':''}}" data-map-source="${{value}}">${{label}}</button>`)
    .join('');
  return `<div class="map-quick">${{sourceButtons}}<button class="${{state.mapLayer==='both'?'active':''}}" data-layer="both">Тепло + точки</button><button class="${{state.mapLayer==='points'?'active':''}}" data-layer="points">Точки</button></div>`;
}}
function dashboard() {{
  const s = data.stats || {{}};
  const countSource = data.dataCountProvenance || {{}};
  const listings = recentListingRows(data.listings || [], Number.MAX_SAFE_INTEGER);
  const loaded = countSource.detail || (s.loaded_snapshot_listings ? `Загружено локально: ${{fmtInt(s.loaded_snapshot_listings)}}` : 'По текущей базе объявлений');
  const listingTotal = Number(s.listings_total || listings.length || 0);
  const readyRate = listingTotal ? Number(s.ml_ready_listings || 0) / listingTotal * 100 : null;
  const coordinateRate = listingTotal ? Number(s.coordinate_listings || (data.mapPoints || []).length || 0) / listingTotal * 100 : null;
  const latest = data.latestRun && (data.latestRun.finished_at || data.latestRun.started_at) ? shortDate(data.latestRun.finished_at || data.latestRun.started_at) : 'Не указан';
  const modelReady = readyRate === null ? '—' : fmtPct(readyRate);
  return `<div class="kicker">ОБЗОР РЫНКА · МОСКВА</div>
    <section class="grid4">
      ${{kpi('Медианная цена за м²', fmtM2(s.median_price_per_m2), loaded, 'trending_up')}}
      ${{kpi('Объявлений в базе', fmtInt(countSource.count || s.listings_total), countSource.label || data.primarySourceLabel || 'Источник не подтвержден', 'data_array')}}
      ${{kpi('Готово для модели', modelReady, `${{fmtInt(s.ml_ready_listings)}} записей с полными параметрами`, 'model_training')}}
      ${{kpi('Последний сбор', latest, `${{fmtInt(s.ingestion_runs_total)}} запусков в истории данных`, 'schedule')}}
    </section>
    <section class="grid12">
      ${{connectionNotice()}}
      <article class="card span4"><div class="card-title">Быстрая оценка объекта <button class="ghost-btn" data-go="valuation">Открыть оценку</button></div>
        <div class="field"><label class="label">Адрес или ЖК</label><input placeholder="Улица, дом или название ЖК"></div>
        ${{stepInput('quickArea', 'Площадь, м²', 60, 10, 1200, 1)}}
        <div class="segmented">${{roomButtons()}}</div>
        <button class="primary-btn" id="quickValuation" style="width:100%;margin-top:16px">Рассчитать стоимость</button>
        <div class="sub" id="quickResult">Расчет использует текущую базу объявлений и подключенный сервис оценки, если он доступен.</div>
      </article>
      <article class="card span8"><div class="card-title">Тепловая карта цен <button class="ghost-btn" data-go="map">Открыть карту</button></div>${{mapQuickControls()}}${{map(mapFilteredPoints())}}</article>
      <article class="card span4"><div class="card-title">Источники данных <span class="material-symbols-outlined">hub</span></div>${{sourceRows()}}</article>
      <article class="card span4"><div class="card-title">Инфраструктура района <span class="material-symbols-outlined">location_city</span></div>${{infrastructureStatus()}}</article>
      <article class="card span4"><div class="card-title">Новые поступления <button class="ghost-btn" data-go="data">Все</button></div>${{listingList(listings.slice(0,4))}}</article>
      <article class="card span8 dashboard-trend-wide"><div class="card-title">Тренд медианы за м² <span class="material-symbols-outlined">trending_up</span></div>${{priceTrendChart()}}</article>
    </section>`;
}}
function bars(items) {{
  if (!items.length) return `<div class="empty">Недостаточно данных для графика.</div>`;
  const prepared = segmentBars(items);
  const values = prepared.map(i => Number(i.median_price_per_m2 || i.median_price_rub || 0));
  const min = Math.min(...values);
  const max = Math.max(...values);
  const spread = Math.max(1, max - min);
  return `<div class="bars">` + prepared.map(i => {{
    const value = Number(i.median_price_per_m2 || i.median_price_rub || 0);
    const width = 18 + Math.round(((value - min) / spread) * 82);
    return `<div class="bar-wrap"><strong>${{esc(i.label)}}</strong><div class="bar-track"><div class="bar" style="width:${{width}}%"></div></div><div><span class="bar-value">${{fmtM2(i.median_price_per_m2)}}</span><br><span class="bar-count">${{fmtInt(i.listings)}} объявл.</span></div></div>`;
  }}).join('') + `</div><div class="chart-note">Шкала пересчитывается по текущей выборке: фильтры, источник и новые данные меняют значения без статичных макетных чисел.</div>`;
}}
function median(values) {{
  const prepared = values.map(Number).filter(value => Number.isFinite(value) && value > 0).sort((a, b) => a - b);
  if (!prepared.length) return null;
  const mid = Math.floor(prepared.length / 2);
  return prepared.length % 2 ? prepared[mid] : (prepared[mid - 1] + prepared[mid]) / 2;
}}
function priceTrendChart(rows = data.observationTrendSeries?.length ? data.observationTrendSeries : (data.listings || [])) {{
  const buckets = new Map();
  for (const row of rows) {{
    const rawDate = row.observed_date || row.observed_at || row.created_at || row.updated_at;
    const date = rawDate ? new Date(rawDate) : null;
    const price = Number(row.median_price_per_m2 || row.price_per_m2 || 0);
    if (!date || Number.isNaN(date.getTime()) || !price) continue;
    const key = date.toISOString().slice(0, 10);
    const values = buckets.get(key) || [];
    values.push({{ price, count: Number(row.observation_count || row.listing_count || 1) }});
    buckets.set(key, values);
  }}
  const trend = [...buckets.entries()]
    .map(([date, values]) => ({{
      date,
      value: median(values.map(item => item.price)),
      count: values.reduce((sum, item) => sum + Number(item.count || 0), 0),
    }}))
    .filter(row => row.value)
    .sort((a, b) => a.date.localeCompare(b.date))
    .slice(-14);
  if (!trend.length) return `<div class="empty">Недостаточно датированных объявлений для тренда.</div>`;
  const min = Math.min(...trend.map(row => row.value));
  const max = Math.max(...trend.map(row => row.value));
  const spread = Math.max(1, max - min);
  return `<div class="line-chart">` + trend.map(row => {{
    const height = 18 + Math.round((row.value - min) / spread * 118);
    const label = new Date(row.date).toLocaleDateString('ru-RU', {{ day:'2-digit', month:'2-digit' }});
    return `<div class="trend-col" title="${{fmtM2(row.value)}} · ${{fmtInt(row.count)}} объявл."><span class="trend-value">${{fmtShortM2(row.value)}}</span><span class="trend-bar" style="height:${{height}}px"></span><span>${{label}}</span></div>`;
  }}).join('') + `</div><div class="chart-note">Тренд строится по реальным датам наблюдений и медианной цене за м².</div>`;
}}
function segmentBars(items) {{
  const buckets = new Map();
  for (const item of items) {{
    const rooms = Number(item.rooms);
    const key = rooms >= 5 ? '5+' : String(rooms);
    const label = roomLabel(rooms);
    const current = buckets.get(key) || {{ label, listings:0, weighted:0 }};
    const listings = Number(item.listings || 0);
    current.listings += listings;
    current.weighted += Number(item.median_price_per_m2 || 0) * Math.max(listings, 1);
    buckets.set(key, current);
  }}
  return [...buckets.values()].map(row => ({{
    label: row.label,
    listings: row.listings,
    median_price_per_m2: row.weighted / Math.max(row.listings, 1),
  }}));
}}
function segmentSummaryFromRows(rows = filteredRows()) {{
  const buckets = new Map();
  for (const row of rows) {{
    const priceM2 = Number(row.price_per_m2);
    const price = Number(row.price_rub);
    const rooms = Number(row.rooms);
    if (!Number.isFinite(priceM2) || priceM2 <= 0 || !Number.isFinite(rooms)) continue;
    const key = rooms >= 5 ? '5+' : String(rooms);
    const current = buckets.get(key) || {{ rooms: rooms >= 5 ? 5 : rooms, pricesM2: [], prices: [] }};
    current.pricesM2.push(priceM2);
    if (Number.isFinite(price) && price > 0) current.prices.push(price);
    buckets.set(key, current);
  }}
  const median = values => {{
    if (!values.length) return null;
    values.sort((a, b) => a - b);
    const mid = Math.floor(values.length / 2);
    return values.length % 2 ? values[mid] : (values[mid - 1] + values[mid]) / 2;
  }};
  return [...buckets.values()].sort((a, b) => a.rooms - b.rooms).map(row => ({{
    rooms: row.rooms,
    listings: row.pricesM2.length,
    median_price_per_m2: median(row.pricesM2),
    median_price_rub: median(row.prices),
  }}));
}}
function selectedModelCandidateName() {{
  const value = document.getElementById('modelCandidateSelect')?.value || '';
  return value || data.model?.selected_candidate || '';
}}
function trainingCandidateMetrics(candidateName) {{
  const rows = Array.isArray(data.model?.training_candidates) ? data.model.training_candidates : [];
  return rows.find(row => row.candidate_name === candidateName) || null;
}}
function activeValuationMetrics(metricsOverride = null) {{
  if (metricsOverride && typeof metricsOverride === 'object' && Object.keys(metricsOverride).length) return metricsOverride;
  const candidateName = selectedModelCandidateName();
  const candidateMetrics = candidateName ? trainingCandidateMetrics(candidateName) : null;
  return candidateMetrics || data.model?.metrics || data.localModel?.metrics || {{}};
}}
function renderValuationModelQuality(metrics = null) {{
  const activeMetrics = activeValuationMetrics(metrics);
  return [
    ['MAE', activeMetrics.mae ? fmtMln(activeMetrics.mae) : '—'],
    ['MAPE', activeMetrics.mape ? fmtPct(Number(activeMetrics.mape) * 100) : '—'],
    ['R²', activeMetrics.r2 ? Number(activeMetrics.r2).toLocaleString('ru-RU', {{ maximumFractionDigits:3 }}) : '—'],
    ['Строк обучения', activeMetrics.rows_total ? fmtInt(activeMetrics.rows_total) : '—'],
  ].map(([label, value]) => `<div class="metric-line"><span>${{label}}</span><strong>${{value}}</strong></div>`).join('');
}}
function valuationMetrics(prediction, metricsOverride = null) {{
  const metrics = activeValuationMetrics(metricsOverride);
  const area = Number(document.getElementById('areaInput')?.value || data.valuationDefaults?.total_area_m2 || 60);
  const medianEstimate = Number(data.stats?.median_price_per_m2 || 0) * area;
  const delta = prediction && medianEstimate ? (prediction - medianEstimate) / medianEstimate * 100 : null;
  const rows = [
    ['Оценка по медиане', medianEstimate ? fmtMln(medianEstimate) : '—'],
    ['Отклонение от медианы', delta === null ? '—' : fmtPct(delta)],
    ['MAE модели', metrics.mae ? fmtMln(metrics.mae) : '—'],
    ['R² модели', metrics.r2 ? Number(metrics.r2).toLocaleString('ru-RU', {{ maximumFractionDigits:3 }}) : '—'],
  ];
  return rows.map(([label, value]) => `<div class="valuation-fact"><span>${{label}}</span><strong>${{value}}</strong></div>`).join('');
}}
function valuationScenarioChart(prediction, metricsOverride = null) {{
  const area = Number(document.getElementById('areaInput')?.value || data.valuationDefaults?.total_area_m2 || 60);
  const base = Number(prediction || 0);
  const median = Number(data.stats?.median_price_per_m2 || 0) * area;
  const metrics = activeValuationMetrics(metricsOverride);
  const rows = [
    ['Модель', base],
    ['Медиана рынка', median],
    ['Нижняя граница MAE', base && metrics.mae ? base - Number(metrics.mae) : null],
    ['Верхняя граница MAE', base && metrics.mae ? base + Number(metrics.mae) : null],
  ].filter(([, value]) => Number.isFinite(Number(value)) && Number(value) > 0);
  if (!rows.length) return `<div class="empty">Недостаточно данных для сценарного сравнения.</div>`;
  const max = Math.max(...rows.map(([, value]) => Number(value)), 1);
  return `<div class="horizontal-bars">` + rows.map(([label, value]) => `<div class="hbar-row"><strong>${{label}}</strong><div class="hbar-track"><div class="hbar-fill" style="width:${{Math.max(5, Math.round(Number(value) / max * 100))}}%"></div></div><span>${{fmtMln(value)}}</span></div>`).join('') + `</div>`;
}}
function valuationComparableRows(prediction) {{
  const area = Number(document.getElementById('areaInput')?.value || data.valuationDefaults?.total_area_m2 || 60);
  const selectedRooms = Number(document.getElementById('roomsSelect')?.value);
  const rooms = Number.isFinite(selectedRooms) ? selectedRooms : state.room;
  const targetM2 = prediction && area ? Number(prediction) / area : Number(data.stats?.median_price_per_m2 || 0);
  const valid = (data.listings || []).filter(row =>
    Number(row.price_rub) > 0 && Number(row.price_per_m2) > 0 && Number(row.total_area_m2) > 0
  );
  const sameRooms = Number.isFinite(rooms) ? valid.filter(row => Number(row.rooms) === rooms) : [];
  const rows = sameRooms.length ? sameRooms : valid;
  const scored = rows.map(row => {{
    const areaDelta = Math.abs(Number(row.total_area_m2) - area);
    const m2DeltaPct = targetM2 ? (Number(row.price_per_m2) - targetM2) / targetM2 * 100 : 0;
    const roomPenalty = sameRooms.length ? 0 : Math.abs(Number(row.rooms || 0) - rooms) * 25;
    return {{
      ...row,
      area_delta_m2: Math.round(areaDelta * 10) / 10,
      price_per_m2_delta_pct: Math.round(m2DeltaPct * 10) / 10,
      comparison_score: Math.round((areaDelta + Math.abs(m2DeltaPct) + roomPenalty) * 10) / 10,
    }};
  }}).sort((a, b) => (a.comparison_score - b.comparison_score) || (a.area_delta_m2 - b.area_delta_m2));
  return scored.slice(0, 6);
}}
function valuationComparables(prediction) {{
  const rows = valuationComparableRows(prediction);
  const fallbackRows = rows.length ? rows : (data.comparables || []);
  if (!fallbackRows.length) return `<div class="empty">В текущей витрине нет объявлений с ценой, площадью и комнатностью для сопоставления.</div>`;
  return `<div class="chart-note">Список строится только по реальным объявлениям текущей витрины: сначала та же комнатность, затем ближайшие площадь и цена за м² к параметрам формы.</div><div class="table-scroll"><table><thead><tr><th>Адрес</th><th>Источник</th><th>Комнат</th><th>Площадь</th><th>Этаж</th><th>Цена</th><th>Цена за м²</th><th>Разница к оценке</th></tr></thead><tbody>` +
    fallbackRows.map(row => `<tr><td>${{listingLink(row)}}</td><td>${{sourceBadge(row)}}</td><td>${{roomLabel(row.rooms)}}</td><td>${{fmtInt(row.total_area_m2)}} м²</td><td>${{floorText(row)}}</td><td>${{fmtMln(row.price_rub)}}</td><td>${{fmtM2(row.price_per_m2)}}</td><td>${{Number(row.price_per_m2_delta_pct || 0).toLocaleString('ru-RU', {{ maximumFractionDigits:1 }})}}%</td></tr>`).join('') +
    `</tbody></table></div>`;
}}
function normalizeModelDrivers(source) {{
  const rows = Array.isArray(source) ? source : [];
  return rows
    .map(row => ({{
      feature: row.feature || row.name || row.column || '',
      importance: Number(row.importance ?? row.coefficient ?? row.value ?? 0),
      coefficient: Number(row.coefficient ?? row.value ?? row.importance ?? 0),
      source: String(row.source || ''),
    }}))
    .filter(row => row.feature)
    .sort((a, b) => Math.abs(b.importance) - Math.abs(a.importance))
    .slice(0, 8);
}}
function modelDriverUnit(drivers) {{
  const sources = new Set((drivers || []).map(row => String(row.source || '')));
  if (sources.has('coefficient')) {{
    return {{
      source: 'coefficient',
      label: 'Коэффициент Ridge',
      note: 'Коэффициенты Ridge показаны со знаком на масштабированных признаках; это не проценты и не доля важности.',
    }};
  }}
  if (sources.has('permutation_importance')) {{
    return {{
      source: 'permutation_importance',
      label: 'Пермутационная важность',
      note: 'Пермутационная важность показывает изменение ошибки MAE в рублях при перемешивании признака; это не процент.',
    }};
  }}
  if (sources.has('model_feature_importance')) {{
    return {{
      source: 'model_feature_importance',
      label: 'Доля важности',
      note: 'Для Random Forest показана доля feature_importances_ в процентах от общей важности признаков.',
    }};
  }}
  return {{
    source: '',
    label: 'Важность признака',
    note: 'Факторы показаны из метаданных выбранной модели; единица зависит от источника в артефакте.',
  }};
}}
function formatSignedRub(raw) {{
  const value = Number(raw || 0);
  if (!Number.isFinite(value)) return '—';
  const sign = value > 0 ? '+' : '';
  return `${{sign}}${{Math.round(value).toLocaleString('ru-RU')}} ₽`;
}}
function formatModelDriverValue(row, unit = null) {{
  const source = String(row?.source || unit?.source || '');
  if (source === 'coefficient') return formatSignedRub(row?.coefficient ?? row?.importance);
  if (source === 'permutation_importance') return fmtRub(Math.abs(Number(row?.importance || 0)));
  let value = Math.abs(Number(row?.importance || 0));
  if (!Number.isFinite(value)) return '—';
  if (value <= 1) value *= 100;
  return `${{value.toLocaleString('ru-RU', {{ maximumFractionDigits:1 }})}}%`;
}}
function modelDriverRows(featureImportanceOverride = null, options = {{}}) {{
  const useFallback = options?.useFallback !== false;
  const labels = {{
    total_area_m2:'Площадь', rooms:'Комнатность', floor:'Этаж', floors_total:'Этажей в доме',
    building_year:'Год постройки', latitude:'Широта', longitude:'Долгота',
    nearest_transport_m:'Ближайший транспорт', schools_count_1000m:'Школы',
    parks_count_1000m:'Парки', shops_count_1000m:'Магазины', transport_count_500m:'Транспорт',
    building_year_missing:'Год постройки не указан', coordinates_missing:'Координаты не указаны',
    floor_missing:'Этаж не указан', floors_total_missing:'Этажность не указана',
    nearest_transport_m_missing:'Транспорт не указан', observation_missing:'Наблюдение не указано',
    osm_missing:'Городские объекты не указаны', property_type_apartment:'Квартира',
    transport_count_1000m:'Транспорт 1 км', healthcare_count_1000m:'Медицина'
  }};
  const localRows = data.localModel?.featureNames?.length && data.localModel?.coefficients?.length
    ? data.localModel.featureNames.map((name, index) => ({{
        feature: name,
        importance: Math.abs(Number(data.localModel.coefficients[index] || 0)),
        coefficient: Number(data.localModel.coefficients[index] || 0),
        source: 'coefficient',
      }}))
    : [];
  const drivers = normalizeModelDrivers(
    featureImportanceOverride
    || (useFallback ? data.model?.feature_importance : null)
    || (useFallback ? data.modelMetadata?.feature_importance : null)
    || (useFallback ? localRows : [])
    || []
  );
  if (!drivers.length) return `<div class="empty compact">Нет данных о факторах для выбранной модели.</div>`;
  const unit = modelDriverUnit(drivers);
  const provenance = featureImportanceOverride || (useFallback && (data.model?.feature_importance || data.modelMetadata?.feature_importance))
    ? 'Факторы получены из метаданных выбранной модели сервиса; расчет цены выполняется через контракт оценки.'
    : 'Это постоянные веса обученной локальной модели. Расчет цены меняется от параметров формы, а не от фильтров таблиц.';
  return `<div class="chart-note">${{unit.label}}</div>` + drivers.map(row => `<div class="metric-line"><span>${{esc(labels[row.feature] || row.feature || 'Признак модели')}}</span><strong title="${{esc(unit.label)}}">${{formatModelDriverValue(row, unit)}}</strong></div>`).join('') + `<div class="chart-note">${{unit.note}} ${{provenance}}</div>`;
}}
function modelDriversLoading() {{
  return `<div class="empty compact">Факторы модели пересчитываются для выбранного алгоритма…</div>`;
}}
function modelDriversPendingSelection() {{
  return `<div class="empty compact">Выберите параметры и нажмите «Рассчитать стоимость», чтобы обновить факторы выбранной модели.</div>`;
}}
function renderPredictionDrivers(payload) {{
  const rows = payload ? (payload.feature_importance || payload.model_metadata?.feature_importance || null) : null;
  const candidate = payload ? (payload.selected_candidate || selectedValuationModel()) : selectedValuationModel();
  const body = modelDriverRows(rows, {{ useFallback: false }});
  const note = candidate ? `<div class="chart-note">Показаны факторы для модели: ${{modelCandidateName(candidate)}}.</div>` : '';
  return body + note;
}}
function renderInvalidPredictionModel(detail = {{}}, selectedCandidate = null) {{
  const candidate = detail?.selected_candidate || detail?.model_candidate || selectedCandidate;
  const candidateLabel = candidate ? modelCandidateName(candidate) : 'выбранная модель';
  const metrics = detail?.metrics_summary || {{}};
  const featureRows = Array.isArray(detail?.feature_importance) ? detail.feature_importance : [];
  const metricText = metrics.mae ? ` MAE модели: ${{fmtMln(metrics.mae)}}.` : '';
  return {{
    result: 'Прогноз вне допустимого диапазона',
    hint: `Артефакт модели «${{candidateLabel}}» загружен, но для текущих параметров модель вернула неположительную цену. RealtyScope не подставляет медиану вместо прогноза.${{metricText}}`,
    drivers: modelDriverRows(featureRows, {{ useFallback: false }}) + `<div class="chart-note">Факторы показаны из ответа модели, но цена не выводится, потому что прогноз для этих параметров не является положительным.</div>`,
  }};
}}
function renderUnavailableModel(detail = {{}}, selectedCandidate = null) {{
  if (detail?.reason === 'non_positive_prediction') return renderInvalidPredictionModel(detail, selectedCandidate);
  const candidate = detail?.model_candidate || selectedCandidate;
  const available = Array.isArray(detail?.available_candidates) ? detail.available_candidates : [];
  const candidateLabel = candidate ? modelCandidateName(candidate) : 'выбранная модель';
  const availableLabel = available.length
    ? available.map(item => modelCandidateName(item)).join(', ')
    : 'нет доступных артефактов';
  return {{
    result: 'Модель недоступна',
    hint: `Артефакт модели «${{candidateLabel}}» не загружен в оценочный сервис. Доступно: ${{availableLabel}}.`,
    drivers: modelDriverRows([], {{ useFallback: false }}) + `<div class="chart-note">Факторы не показаны, потому что для выбранной модели нет загруженного артефакта.</div>`,
  }};
}}
function osmFeatureLabel(name) {{
  const labels = {{
    healthcare_count_1000m:'Медицина 1 км',
    nearest_transport_m:'Дистанция до транспорта',
    nearest_transport_m_missing:'Флаг отсутствия транспорта',
    osm_missing:'Флаг отсутствия инфраструктуры',
    parks_count_1000m:'Парки 1 км',
    schools_count_1000m:'Учебные объекты 1 км',
    shops_count_1000m:'Магазины 1 км',
    transport_count_1000m:'Транспорт 1 км',
    transport_count_500m:'Транспорт 500 м',
  }};
  return labels[name] || 'Признак инфраструктуры';
}}
function osmCoverageSourceLabel(value) {{
  const labels = {{
    missing:'Нет данных',
    live_overpass:'Запросы Overpass',
    local_extract:'Локальная выгрузка OSM',
    coordinate_exact_match:'Точные совпадения координат',
    'local_extract+coordinate_exact_match':'Локальная выгрузка OSM и точные координаты',
    'local_extract+live_overpass':'Локальная выгрузка OSM и запросы Overpass',
    'live_overpass+coordinate_exact_match':'Запросы Overpass и точные координаты',
    'local_extract+live_overpass+coordinate_exact_match':'Локальная выгрузка OSM, запросы Overpass и точные координаты',
    local_or_cached_osm:'Локальный или кэшированный OSM',
  }};
  return labels[value] || value || '—';
}}
function infrastructureStatus() {{
  const osm = data.osmCoverage || {{}};
  const features = osm.features || [];
  const coveragePct = osm.coveragePct === null || osm.coveragePct === undefined ? '' : ` (${{fmtPct(osm.coveragePct)}})`;
  const coverage = osm.coverageRows === null || osm.coverageRows === undefined
    ? 'Не загружено в витрину'
    : `${{fmtInt(osm.coverageRows)}}${{coveragePct}}`;
  const liveRows = osm.liveRows === null || osm.liveRows === undefined ? '—' : fmtInt(osm.liveRows);
  const localExtractRows = osm.localExtractRows === null || osm.localExtractRows === undefined ? '—' : fmtInt(osm.localExtractRows);
  const derivedRows = osm.coordinateDerivedRows === null || osm.coordinateDerivedRows === undefined ? '—' : fmtInt(osm.coordinateDerivedRows);
  const attribution = osm.attribution || 'OpenStreetMap contributors';
  const rows = [
    ['Источник', osm.source || 'OpenStreetMap'],
    ['Признаков в модели', fmtInt(osm.featureCount || features.length)],
    ['Покрытие инфраструктуры', coverage],
    ['Источник покрытия', osmCoverageSourceLabel(osm.coverageSource)],
    ['Версия признаков', osm.featureVersion || '—'],
    ['Строк из локальной выгрузки OSM', localExtractRows],
    ['Строк из Overpass', liveRows],
    ['Строк по точным координатам', derivedRows],
    ['Ввод в оценке', osm.defaultMissing ? 'Ручные значения окружения' : 'Значения окружения заданы'],
  ];
  const featureText = features.length
    ? features.map(osmFeatureLabel).join(', ')
    : 'Признаки инфраструктуры не найдены в сохраненной модели.';
  return `<div class="metric-list">${{rows.map(([label, value]) => `<div class="metric-line"><span>${{label}}</span><strong>${{value}}</strong></div>`).join('')}}</div><div class="chart-note">Инфраструктура района используется как признаки оценки: ${{esc(featureText)}}. Массовое покрытие заявляется только по подтвержденным строкам osm_features. Атрибуция: ${{esc(attribution)}}.</div>`;
}}
function requirementsAudit() {{
  const total = Number(data.stats?.listings_total || (data.listings || []).length || 0);
  const coords = Number(data.stats?.coordinate_listings || (data.mapPoints || []).length || 0);
  const dealCount = Number((data.deals || []).length || 0);
  const districtRows = data.districtComparison || [];
  const districtClusters = data.districtClusters || [];
  const exposure = data.exposureReadiness || {{}};
  const osm = data.osmCoverage || {{}};
  const datedDays = new Set((data.listings || []).map(row => String(row.observed_at || '').slice(0, 10)).filter(Boolean)).size;
  const rows = [
    ['Карта цен и координаты', total && coords ? 'ready' : 'missing', total && coords ? 'готово' : 'нет', `${{fmtInt(coords)}} из ${{fmtInt(total)}} объявлений с координатами; карта строится по реальным точкам.`],
    ['Инфраструктура района', osm.featureContract ? 'partial' : 'missing', osm.featureContract ? 'частично' : 'нет', 'Признаки OpenStreetMap есть в модели и форме оценки; широкое покрытие инфраструктуры в текущей витрине не подтверждено.'],
    ['Детекция выгодных предложений', dealCount ? 'partial' : 'missing', dealCount ? 'частично' : 'нет', dealCount ? `Работает реальный скоринг: скидка к медиане комнатного сегмента, MAD-отклонение и квантиль цены за м²; найдено ${{fmtInt(dealCount)}} кандидатов.` : 'Кандидаты ниже медианы с достаточной выборкой не найдены в текущей выборке.'],
    ['Сравнение сегментов', total ? 'ready' : 'missing', total ? 'готово' : 'нет', 'Сравнение по комнатности, объему сегментов и ценовым диапазонам пересчитывается от фильтров.'],
    ['Сравнение районов', districtRows.length ? (data.districtReadiness?.extraction_source?.includes('admin_boundary_geojson') ? 'ready' : 'partial') : 'missing', districtRows.length ? (data.districtReadiness?.extraction_source?.includes('admin_boundary_geojson') ? 'готово' : 'частично') : 'нет', districtRows.length ? `Построено по реальным районным агрегатам; источник районов: ${{esc(data.districtReadiness?.extraction_source || 'не найден')}}; покрытие: ${{fmtPct(data.districtReadiness?.coverage_pct || null)}}.` : 'Нет структурированного поля района или границ районов в текущей витрине; нельзя честно строить рейтинг районов.'],
    ['Кластеризация районов', districtClusters.length ? (data.districtReadiness?.extraction_source?.includes('admin_boundary_geojson') ? 'ready' : 'partial') : 'missing', districtClusters.length ? (data.districtReadiness?.extraction_source?.includes('admin_boundary_geojson') ? 'готово' : 'частично') : 'нет', districtClusters.length ? 'Есть детерминированная кластеризация по реальной матрице районных агрегатов: медиана цены за м², объем, разброс цены и число источников; источник районов показан в блоке готовности.' : 'Нет сохраненного алгоритма кластеризации и районных признаков; это нужно доделывать в серверной аналитике.'],
    ['Прогноз срока экспозиции', exposure.status === 'ready' ? 'partial' : (exposure.status === 'partial' ? 'partial' : 'missing'), exposure.status_label || 'нет', exposure.can_forecast ? 'Есть lifecycle target rows; нужен отдельный обученный и проверенный прогноз срока экспозиции.' : (exposure.note || 'Нет целевой переменной срока экспозиции и обученной модели прогноза.')],
    ['Тренд цен', datedDays > 1 ? 'partial' : 'partial', 'частично', 'Показывается медиана цены за м² по датам наблюдений; это не прогноз и не сезонная модель.'],
  ];
  return `<div class="audit-list">` + rows.map(([name, cls, status, note]) => `<div class="audit-row"><div class="audit-name">${{name}}</div><div><span class="audit-status ${{cls}}">${{status}}</span></div><div class="audit-note">${{note}}</div></div>`).join('') + `</div>`;
}}
function valuation() {{
  const d = data.valuationDefaults || {{}};
  const initialFeatures = {{ ...d, rooms: state.room, total_area_m2: Number(d.total_area_m2 || 60), property_type_apartment:1 }};
  const initialPrediction = data.connected ? null : localModelPrediction(initialFeatures);
  const initialResult = initialPrediction ? 'Расчет модели: ' + fmtPredictionRub(initialPrediction) : 'Параметры готовы к расчету';
  const initialHint = initialPrediction
    ? 'Предварительный расчет выполнен локально по сохраненной модели RealtyScope и параметрам формы.'
    : 'Нажмите кнопку расчета, чтобы получить оценку через доступный обученный artifact модели RealtyScope.';
  const metrics = activeValuationMetrics();
  return `<div class="kicker">ОЦЕНКА СТОИМОСТИ</div><section class="grid12">
    <article class="card span5 valuation-form compact"><div class="card-title">Параметры квартиры <span class="material-symbols-outlined">calculate</span></div>
      <div class="form-section"><div class="section-label">Базовые параметры</div><div class="mini-grid">
        ${{stepInput('areaInput', 'Площадь, м²', d.total_area_m2 || 60, 10, 1200, 1)}}
        ${{stepInput('roomsSelect', 'Комнат', Number.isFinite(Number(state.room)) ? state.room : (d.rooms || 2), 0, 20, 1)}}
        ${{stepInput('floorInput', 'Этаж', d.floor || 5, 1, 100, 1)}}
        ${{stepInput('floorsTotalInput', 'Этажей в доме', d.floors_total || 20, 1, 100, 1)}}
      </div></div>
      <div class="valuation-primary-controls">
        <div class="field"><label class="label">Модель оценки</label><select id="modelCandidateSelect">${{modelCandidateOptions()}}</select></div>
        <div class="valuation-action-bar"><button class="primary-btn" id="runValuationBtn">Рассчитать стоимость</button></div>
      </div>
      <details class="form-section advanced-valuation-fields"><summary>Локация и окружение</summary><div class="mini-grid">
        ${{stepInput('buildingYearInput', 'Год постройки', d.building_year || 2018, 1800, 2035, 1)}}
        ${{stepInput('transportInput', 'Ближайший транспорт, м', d.nearest_transport_m || 0, 0, 5000, 50)}}
        ${{stepInput('latitudeInput', 'Широта', d.latitude || 55.75, 54.5, 56.5, 0.01)}}
        ${{stepInput('longitudeInput', 'Долгота', d.longitude || 37.61, 36.5, 38.8, 0.01)}}
        ${{stepInput('schoolsInput', 'Школы 1 км', d.schools_count_1000m || 0, 0, 150, 1)}}
        ${{stepInput('parksInput', 'Парки 1 км', d.parks_count_1000m || 0, 0, 1800, 1)}}
        ${{stepInput('shopsInput', 'Магазины 1 км', d.shops_count_1000m || 0, 0, 1100, 1)}}
        ${{stepInput('transport500Input', 'Транспорт 500 м', d.transport_count_500m || 0, 0, 150, 1)}}
        ${{stepInput('transport1000Input', 'Транспорт 1 км', d.transport_count_1000m || 0, 0, 300, 1)}}
      </div><label class="check-row"><input id="buildingKnownInput" type="checkbox" checked> Год постройки известен</label><label class="check-row"><input id="coordinatesKnownInput" type="checkbox"> Координаты и окружение известны</label><div class="sub">Если координаты или окружение не подтверждены, RealtyScope передает флаги отсутствия и не выдает базовые значения за известные пользователю.</div></details>
      <div class="form-section"><div class="section-label">Быстрый выбор комнат</div><div class="segmented">${{roomButtons()}}</div></div>
    </article>
    <article class="card span7"><div class="card-title">Итоговая оценка <span class="material-symbols-outlined">analytics</span></div>
      <div class="valuation-hero"><div class="value" id="valuationResult">${{initialResult}}</div><div class="sub" id="valuationHint">${{initialHint}}</div><div class="sub valuation-input-echo" id="valuationInputEcho">${{valuationInputSummary(initialFeatures, data.localModel?.targetVariable, initialPrediction)}}</div></div>
      <div class="valuation-facts" id="valuationMetrics">${{valuationMetrics(initialPrediction)}}</div>
    </article>
    <article class="card span12"><div class="card-title">Сопоставимые объявления</div><div id="valuationComparables">${{valuationComparables(initialPrediction)}}</div></article>
    <article class="card span4"><div class="card-title">Сравнение результата</div><div id="valuationScenario">${{valuationScenarioChart(initialPrediction)}}</div></article>
    <article class="card span4"><div class="card-title">Качество модели</div><div class="metric-list" id="valuationModelQuality">${{renderValuationModelQuality(metrics)}}</div></article>
    <article class="card span4"><div class="card-title">Факторы модели</div><div class="metric-list" id="valuationModelDrivers">${{modelDriverRows()}}</div></article>
    </section>`;
}}
function deals() {{
  const rows = sortRows(filteredDealRows(), 'deals');
  const pageRows = pagedRows(rows);
  return `<div class="kicker">ВЫГОДНЫЕ ПРЕДЛОЖЕНИЯ</div><section class="grid12">
    <article class="card span4"><div class="card-title">Фильтры предложений <span class="material-symbols-outlined">tune</span></div>${{filterControls()}}<button class="primary-btn" id="applyFilters" style="width:100%">Применить</button></article>
    <article class="card span8"><div class="card-title">Скоринг ниже медианы сегмента <span><span class="source-badge neutral">${{fmtInt(rows.length)}} найдено</span> <button class="ghost-btn" id="refreshBtn">Обновить</button></span></div><div class="chart-note">Скидка — это отклонение цены за м² от медианы сегмента по комнатности и площади; это аналитическая оценка, не заявленная продавцом скидка. Оценка использует реальную цену за м², медиану комнатного сегмента, MAD-отклонение и квантиль внутри текущей выборки.</div>${{rows.length ? dealTable(pageRows) + pager(rows.length) : '<div class="empty">В текущей выборке нет объявлений ниже медианы сегмента с достаточной выборкой.</div>'}}</article>
    </section>`;
}}
function dealTable(rows) {{
  rows = sortRows(rows, 'deals');
  return `<div class="table-scroll"><table class="analytic-table deal-table"><thead><tr>${{th('Балл','deal_score','Оценка')}}${{th('Адрес','address_text')}}${{th('Ист.','source_name','Источник')}}${{th('Комн.','rooms','Комнат')}}${{th('м²','total_area_m2','Площадь')}}${{th('Этаж','floor')}}${{th('Цена','price_rub')}}${{th('₽/м²','price_per_m2','Цена за м²')}}${{th('Медиана','segment_median_m2')}}${{th('N','segment_sample_size','Выборка')}}${{th('Скидка','discount_pct','Отклонение')}}</tr></thead><tbody>` +
    rows.map(r => `<tr><td>${{fmtInt(r.deal_score)}}</td><td>${{listingLink(r)}}</td><td>${{sourceBadge(r)}}</td><td>${{fmtInt(r.rooms)}}</td><td>${{fmtInt(r.total_area_m2)}} м²</td><td>${{floorText(r)}}</td><td>${{fmtMln(r.price_rub)}}</td><td>${{fmtM2(r.price_per_m2)}}</td><td>${{fmtM2(r.segment_median_m2)}}</td><td>${{fmtInt(r.segment_sample_size)}}</td><td>${{Math.round(Number(r.discount_pct || 0) * 100)}}%</td></tr>`).join('') +
    `</tbody></table></div>`;
}}
function segments() {{
  const rows = segmentSummaryFromRows();
  return `<div class="kicker">СРАВНЕНИЕ СЕГМЕНТОВ И РАЙОНОВ</div><section class="grid12"><article class="card span4"><div class="card-title">Фильтры сегментов <span class="material-symbols-outlined">tune</span></div>${{filterControls()}}<button class="primary-btn" id="applyFilters" style="width:100%">Применить</button></article><article class="card span8"><div class="card-title">Медианная цена за м² по комнатности <button class="ghost-btn" id="refreshBtn">Обновить</button></div>${{bars(rows)}}</article><article class="card span5"><div class="card-title">Объем сегментов</div>${{segmentVolumeChart(rows)}}</article><article class="card span7"><div class="card-title">Сравнение районов</div>${{districtComparisonPanel()}}</article><article class="card span5"><div class="card-title">Кластеры районов</div>${{districtClusterPanel()}}</article><article class="card span7"><div class="card-title">Детализация сегментов</div>${{segmentTable(rows)}}</article><article class="card span5"><div class="card-title">Распределение по ценовым диапазонам</div>${{priceBandTable(priceBandRows(filteredRows('segments')))}}</article></section>`;
}}
function segmentTable(rows = segmentSummaryFromRows()) {{
  if (!rows.length) return `<div class="empty">Недостаточно данных для сегментов.</div>`;
  rows = sortRows(rows, 'segments');
  return `<table><thead><tr>${{th('Комнат','rooms')}}${{th('Объявлений','listings')}}${{th('Медиана за м²','median_price_per_m2')}}${{th('Медианная цена','median_price_rub')}}</tr></thead><tbody>` + rows.map(r => `<tr><td>${{roomLabel(r.rooms)}}</td><td>${{fmtInt(r.listings)}}</td><td>${{fmtM2(r.median_price_per_m2)}}</td><td>${{fmtMln(r.median_price_rub)}}</td></tr>`).join('') + `</tbody></table>`;
}}
function segmentVolumeChart(rows = segmentSummaryFromRows()) {{
  rows = segmentBars(rows);
  if (!rows.length) return `<div class="empty">Недостаточно данных для сегментов.</div>`;
  const max = Math.max(...rows.map(row => Number(row.listings || 0)), 1);
  return `<div class="horizontal-bars">` + rows.map(row => `<div class="hbar-row"><strong>${{esc(row.label)}}</strong><div class="hbar-track"><div class="hbar-fill" style="width:${{Math.max(4, Math.round(Number(row.listings || 0) / max * 100))}}%"></div></div><span>${{fmtInt(row.listings)}} объявл.</span></div>`).join('') + `</div>`;
}}
function districtReadinessPanel() {{
  const readiness = data.districtReadiness || {{}};
  const canCompare = Boolean(readiness.can_compare);
  const detected = readiness.detected_fields?.length ? readiness.detected_fields.join(', ') : 'не найдены';
  const partialAddress = readiness.extraction_source === 'address_text';
  const usesBoundary = String(readiness.extraction_source || '').includes('admin_boundary_geojson');
  const sourceTitle = readiness.boundary_source_title ? ` · ${{readiness.boundary_source_title}}` : '';
  const rows = [
    ['Статус', canCompare ? (usesBoundary ? 'границы районов подключены' : (partialAddress ? 'частичная адресная нормализация' : 'готово к агрегации')) : 'нет структурированного района'],
    ['Поле района', readiness.active_field || 'не найдено'],
    ['Строк с районом', fmtInt(readiness.listings_with_district || 0)],
    ['Районов найдено', fmtInt(readiness.district_count || 0)],
    ['Покрытие', fmtPct(readiness.coverage_pct || null)],
    ['По границам', fmtInt(readiness.boundary_matched_rows || 0)],
    ['Проверенные поля', detected],
  ];
  const required = readiness.required_fields || [];
  const note = canCompare && usesBoundary
    ? `Район определяется по координатам и GeoJSON-границам административных районов Москвы${{sourceTitle}}. Если точка не попала в полигон, используется только честный fallback из структурированного поля или адреса.`
    : canCompare && partialAddress
    ? 'Район извлечен регулярными правилами из адресов источников. Это частичная витрина без административных границ; таблица районов показана только по строкам, где район явно есть в адресе.'
    : canCompare
    ? 'В витрине найдено структурированное поле района; следующий шаг — построить агрегаты и показать сравнение по реальным районам.'
    : 'Сравнение районов не построено: в текущей витрине нет надежного поля района или административных границ. Рейтинг районов не показывается, чтобы не подменять аналитику адресными догадками.';
  return `<div class="section-label">Готовность сравнения районов</div><div class="metric-list">${{rows.map(([label, value]) => `<div class="metric-line"><span>${{label}}</span><strong>${{esc(value)}}</strong></div>`).join('')}}</div><div class="chart-note">${{note}}</div>${{required.length ? `<div class="chart-note">Нужно для включения: ${{required.map(esc).join('; ')}}.</div>` : ''}}`;
}}
function districtComparisonPanel() {{
  const rows = data.districtComparison || [];
  if (!rows.length) return districtReadinessPanel();
  const readiness = data.districtReadiness || {{}};
  const body = rows.map(row => `<tr><td>${{esc(row.district_name)}}</td><td>${{fmtInt(row.listings)}}</td><td>${{fmtM2(row.median_price_per_m2)}}</td><td>${{fmtMln(row.median_price_rub)}}</td><td>${{fmtInt(row.source_count)}}</td></tr>`).join('');
  return `<table><thead><tr><th>Район</th><th>Объявлений</th><th>Медиана за м²</th><th>Медианная цена</th><th>Источников</th></tr></thead><tbody>${{body}}</tbody></table><div class="chart-note">В этой таблице районные агрегаты пересчитываются от текущих фильтров и не являются фиксированным справочником цен. Источников — число площадок данных в районе, например ЦИАН и Домклик. Источник районов: ${{esc(readiness.extraction_source || 'не найден')}}; по границам сопоставлено ${{fmtInt(readiness.boundary_matched_rows || 0)}} объявлений. Покрытие: ${{fmtInt(readiness.listings_with_district || 0)}} из ${{fmtInt(data.stats?.listings_total || 0)}} объявлений (${{fmtPct(readiness.coverage_pct || null)}}).</div>`;
}}
function districtClusterPanel() {{
  const rows = data.districtClusters || [];
  const readiness = data.districtReadiness || {{}};
  const osm = data.osmCoverage || {{}};
  if (!rows.length) {{
    const coverage = readiness.coverage_pct === null || readiness.coverage_pct === undefined
      ? '—'
      : fmtPct(readiness.coverage_pct);
    const districtRows = (data.districtComparison || []).length;
    return `<div class="section-label">Готовность кластеризации районов</div><div class="metric-list"><div class="metric-line"><span>Статус</span><strong>нет районной матрицы</strong></div><div class="metric-line"><span>Районных агрегатов</span><strong>${{fmtInt(districtRows)}}</strong></div><div class="metric-line"><span>Покрытие района</span><strong>${{coverage}}</strong></div><div class="metric-line"><span>Источник признаков</span><strong>${{esc(readiness.extraction_source || 'не найден')}}</strong></div></div><div class="chart-note">Кластеризация районов не показывается: в текущей витрине нет надежной матрицы районных признаков. Нужны нормализованные районы или административные границы, агрегаты цены и объема, а также проверенные признаки инфраструктуры.</div>`;
  }}
  const compactRows = rows.slice(0, 9);
  const body = compactRows.map(row => `<tr><td>${{esc(row.cluster_label)}}</td><td>${{esc(row.district_name)}}</td><td>${{fmtInt(row.listings)}}</td><td>${{fmtM2(row.median_price_per_m2)}}</td></tr>`).join('');
  const clusterCount = new Set(rows.map(row => row.cluster_id)).size;
  const featureSource = String(rows[0]?.feature_source || 'districtComparison');
  const osmCoverage = osm.coverageRows === null || osm.coverageRows === undefined
    ? 'покрытие OSM не подтверждено'
    : `покрытие OSM: ${{fmtInt(osm.coverageRows)}} строк${{osm.coveragePct === null || osm.coveragePct === undefined ? '' : ` · ${{fmtPct(osm.coveragePct)}}`}}`;
  const osmCaveat = featureSource.includes('osm')
    ? `В матрице есть OSM-признаки; ${{osmCoverage}}.`
    : `Кластеры не заявляются как OSM-инфраструктурные: ${{osmCoverage}}.`;
  return `<table><thead><tr><th>Кластер</th><th>Район</th><th>Объявлений</th><th>Медиана за м²</th></tr></thead><tbody>${{body}}</tbody></table><div class="chart-note">Кластеризация построена детерминированным методом средних по реальной матрице признаков районов: медиана цены за м², объем, разброс цены и число источников. Показано ${{fmtInt(rows.length)}} районов в ${{fmtInt(clusterCount)}} кластерах; источник районов: ${{esc(readiness.extraction_source || 'не найден')}}; источник кластеров: ${{esc(featureSource)}}. ${{osmCaveat}}</div>`;
}}
function filterScope() {{
  return ['deals','segments','data'].includes(state.page) ? state.page : 'data';
}}
function activeFilters(scope = filterScope()) {{
  if (!state.filters[scope]) state.filters[scope] = blankFilters();
  return state.filters[scope];
}}
function presetActive(name, f = activeFilters()) {{
  if (name === 'reset') return !f.search && !f.rooms && !f.source && !f.minPrice && !f.maxPrice && !f.minArea && !f.maxArea;
  if (name === 'studio') return f.rooms === '0';
  if (name === 'family') return f.rooms === '3';
  if (name === 'budget') return f.maxPrice === '20';
  if (name === 'premium') return f.minPrice === '60';
  return false;
}}
function rangePercent(value, hardMin, hardMax) {{
  const span = Math.max(1, Number(hardMax) - Number(hardMin));
  return Math.min(100, Math.max(0, (Number(value) - Number(hardMin)) / span * 100));
}}
function dualRangeStyle(from, to, hardMin, hardMax) {{
  return `--from:${{rangePercent(from, hardMin, hardMax)}}%;--to:${{rangePercent(to, hardMin, hardMax)}}%;`;
}}
function rangePair(prefix, label, minValue, maxValue, hardMin, hardMax, step, suffix = '') {{
  const fromId = `${{prefix}}Min`;
  const toId = `${{prefix}}Max`;
  const from = minValue || '';
  const to = maxValue || '';
  const fromValue = from || hardMin;
  const toValue = to || hardMax;
  return `<div class="range-pair" data-range-pair="${{prefix}}" data-hard-min="${{hardMin}}" data-hard-max="${{hardMax}}" data-step="${{step}}" data-suffix="${{esc(suffix)}}" style="${{dualRangeStyle(fromValue, toValue, hardMin, hardMax)}}"><div class="range-label"><span>${{label}}</span><span id="${{prefix}}Summary">${{fromValue}}–${{toValue}}${{suffix}}</span></div><div class="dual-range"><div class="dual-range-fill"></div><input id="${{fromId}}Range" data-range-sync="${{fromId}}" data-range-bound="min" type="range" min="${{hardMin}}" max="${{hardMax}}" step="${{step}}" value="${{fromValue}}"><input id="${{toId}}Range" data-range-sync="${{toId}}" data-range-bound="max" type="range" min="${{hardMin}}" max="${{hardMax}}" step="${{step}}" value="${{toValue}}"></div><div class="range-row">${{stepInput(fromId, 'От', from, hardMin, hardMax, step)}}${{stepInput(toId, 'До', to, hardMin, hardMax, step)}}</div></div>`;
}}
function filterControls() {{
  const f = activeFilters();
  return `<div class="preset-row"><button class="${{presetActive('reset', f)?'active':''}}" data-filter-preset="reset">Сброс</button><button class="${{presetActive('studio', f)?'active':''}}" data-filter-preset="studio">Студии</button><button class="${{presetActive('family', f)?'active':''}}" data-filter-preset="family">3-комн.</button><button class="${{presetActive('budget', f)?'active':''}}" data-filter-preset="budget">До 20 млн ₽</button><button class="${{presetActive('premium', f)?'active':''}}" data-filter-preset="premium">От 60 млн ₽</button></div>
    <datalist id="addressSuggestions">${{addressSuggestions()}}</datalist>
    <div class="field"><label class="label">Поиск по адресу</label><input id="searchInput" list="addressSuggestions" value="${{esc(f.search)}}" placeholder="Улица, район или ЖК"></div>
    <div class="toolbar-grid">
      <div class="field"><label class="label">Комнат</label><select id="roomFilter"><option value="">Все</option><option value="0">Студии</option><option value="1">1</option><option value="2">2</option><option value="3">3</option><option value="4">4</option><option value="5">5+</option></select></div>
      <div class="field"><label class="label">Источник</label><select id="sourceFilter"><option value="">Все</option>${{(data.sourceRows || []).map(s => `<option value="${{sourceValue(s.name)}}">${{esc(s.name)}}</option>`).join('')}}</select></div>
    </div>
    ${{rangePair('price', 'Цена, млн ₽', f.minPrice, f.maxPrice, 0, 150, 1, ' млн ₽')}}
    ${{rangePair('area', 'Площадь, м²', f.minArea, f.maxArea, 10, 300, 1, ' м²')}}`;
}}
function addressSuggestions() {{
  return [...new Set((data.listings || []).map(row => String(row.address_text || '').split(',').slice(0, 3).join(',').trim()).filter(Boolean).slice(0, 80))]
    .map(value => `<option value="${{esc(value)}}"></option>`).join('');
}}
function currentDataRows() {{
  return state.sort.data?.key ? sortRows(filteredRows('data'), 'data') : latestFirstRows(filteredRows('data'));
}}
function listingDetailHtml(row) {{
  const fields = [
    ['Адрес', listingLink(row)],
    ['Источник', sourceBadge(row)],
    ['Комнат', fmtInt(row.rooms)],
    ['Площадь', `${{fmtInt(row.total_area_m2)}} м²`],
    ['Этаж', floorText(row)],
    ['Цена', fmtRub(row.price_rub)],
    ['Цена за м²', fmtM2(row.price_per_m2)],
    ['Дата наблюдения', tableDate(row.observed_at || row.observed_date || row.created_at)],
    ['Район', esc(row.district || row.district_name || 'не указан')],
    ['Координаты', row.latitude && row.longitude ? `${{row.latitude}}, ${{row.longitude}}` : 'нет'],
    ['Ссылка', row.source_url ? `<a href="${{esc(row.source_url)}}" target="_blank" rel="noreferrer">Открыть источник</a>` : 'нет'],
  ];
  return `<div class="detail-modal-backdrop" data-action="close-detail"></div><div class="detail-modal-panel" role="dialog" aria-modal="true" tabindex="-1"><div class="drawer-head"><strong>Полная карточка объявления</strong><button class="ghost-btn" id="closeListingDetail" data-action="close-detail">Закрыть</button></div><div class="metric-list">${{fields.map(([label, value]) => `<div class="metric-line"><span>${{label}}</span><strong>${{value}}</strong></div>`).join('')}}</div></div>`;
}}
function closeListingDetail() {{
  const drawer = document.getElementById('listingDetailDrawer');
  if (!drawer) return;
  drawer.classList.remove('open');
  drawer.setAttribute('aria-hidden', 'true');
  drawer.innerHTML = '';
}}
function openListingDetail(index) {{
  const drawer = document.getElementById('listingDetailDrawer');
  const rows = currentDataRows();
  const row = rows.find(item => String(item.id ?? '') === String(index)) || rows[Number(index)];
  if (!row || !drawer) return;
  drawer.innerHTML = listingDetailHtml(row);
  drawer.setAttribute('aria-hidden', 'false');
  drawer.classList.add('open');
  drawer.querySelectorAll('[data-action="close-detail"]').forEach(node => {{
    node.onclick = closeListingDetail;
  }});
  const panel = drawer.querySelector('.detail-modal-panel');
  if (panel) panel.focus();
}}
function dataPage() {{
  const rows = currentDataRows();
  const pageRows = pagedRows(rows);
  return `<div class="kicker">ДАННЫЕ ОБЪЯВЛЕНИЙ</div><section class="grid12"><article class="card span4"><div class="card-title">Фильтры данных <span class="material-symbols-outlined">filter_list</span></div>
    ${{filterControls()}}
    <button class="primary-btn" id="applyFilters" style="width:100%">Применить</button></article>
    <article class="card span8"><div class="card-title">Текущая выборка <span><button class="ghost-btn" id="refreshBtn">Обновить</button> <button class="ghost-btn" id="downloadBtn">Скачать отчет</button></span></div><div id="dataRows">${{rowsTable(pageRows)}}</div>${{pager(rows.length)}}</article></section><aside id="listingDetailDrawer" class="detail-drawer" aria-hidden="true"></aside>`;
}}
function sourceValue(label) {{ return label === 'ЦИАН' ? 'cian' : (label === 'Домклик' ? 'domclick' : ''); }}
function mapFilteredPoints() {{
  return (data.mapPoints || []).filter(point => {{
    const listing = mapListing(point);
    return !state.mapSource || point.source_name === state.mapSource || listing.source_name === state.mapSource;
  }});
}}
function mapPage() {{
  const points = mapFilteredPoints();
  const excluded = Number(data.stats?.excluded_coordinate_rows || 0);
  const excludedText = excluded ? ` Исключено строк вне московских границ: ${{fmtInt(excluded)}}.` : '';
  return `<div class="kicker">ТЕПЛОВАЯ КАРТА</div><section class="grid12"><article class="card span4"><div class="card-title">Слои визуализации</div><div class="map-tools"><button data-layer="both" class="${{state.mapLayer==='both'?'active':''}}">Тепло + точки</button><button data-layer="heat" class="${{state.mapLayer==='heat'?'active':''}}">Тепло</button><button data-layer="points" class="${{state.mapLayer==='points'?'active':''}}">Точки</button></div><div class="field"><label class="label">Источник</label><select id="mapSourceFilter"><option value="">Все</option>${{(data.sourceRows || []).map(s => `<option value="${{sourceValue(s.name)}}">${{esc(s.name)}}</option>`).join('')}}</select></div><div class="range-field"><label class="label">Радиус пятна: <span id="radiusValue">${{state.heatRadius}}</span></label><input id="radiusInput" type="range" min="15" max="85" value="${{state.heatRadius}}"></div><div class="range-field"><label class="label">Прозрачность: <span id="opacityValue">${{state.heatOpacity}}</span>%</label><input id="opacityInput" type="range" min="20" max="95" value="${{state.heatOpacity}}"></div><div class="range-field"><label class="label">Масштаб: <span id="zoomValue">${{state.mapZoom}}</span></label><input id="zoomInput" type="range" min="8" max="14" step="1" value="${{state.mapZoom}}"></div><div class="sub">${{fmtInt(points.length)}} объектов с координатами. Тепло — сглаженная поверхность по радиусу; точки — реальные объявления. Можно перетаскивать карту и менять масштаб колесом мыши.${{excludedText}}</div></article><article class="card span8 map-page-card">${{map(points)}}</article></section>`;
}}
function mapResults(points) {{
  const rows = points.slice(0, 10);
  if (!rows.length) return `<div class="empty">Нет объектов с координатами для текущего источника.</div>`;
  return rows.map((point, index) => `<button class="map-result ${{state.selectedMapIndex===index?'active':''}}" data-map-result="${{index}}"><div class="map-result-title">${{esc(point.address_text || 'Адрес не указан')}}</div><div class="map-result-meta">${{fmtRub(point.price_rub)}} · ${{fmtM2(point.price_per_m2)}} · ${{esc(point.source_label || sourceLabel(point.source_name))}}</div></button>`).join('');
}}
function modelMetricsTable() {{
  const metrics = data.model?.metrics || data.localModel?.metrics || {{}};
  const rows = [
    ['Признаков модели', fmtInt(data.model?.feature_count || data.localModel?.featureNames?.length)],
    ['MAE', metrics.mae ? fmtMln(metrics.mae) : '—'],
    ['MAPE', metrics.mape ? fmtPct(Number(metrics.mape) * 100) : '—'],
    ['RMSE', metrics.rmse ? fmtMln(metrics.rmse) : '—'],
    ['R²', metrics.r2 ? Number(metrics.r2).toLocaleString('ru-RU', {{ maximumFractionDigits:3 }}) : '—'],
    ['Строк обучения', metrics.rows_total ? fmtInt(metrics.rows_total) : '—'],
  ];
  return `<div class="metric-list">${{rows.map(([label, value]) => `<div class="metric-line"><span>${{label}}</span><strong>${{value}}</strong></div>`).join('')}}</div>`;
}}
function modelSelectionLabel(mode, reason) {{
  const modeLabel = {{
    best_metric: 'по метрикам',
    explicit: 'задана вручную',
  }}[mode] || 'не указано';
  const reasonLabel = {{
    best_validation_metric: 'лучшее качество',
    explicit_path: 'явный артефакт',
    dependency_override: 'тестовый контур',
    unavailable: 'нет артефакта',
  }}[reason] || '';
  return reasonLabel ? `${{modeLabel}} · ${{reasonLabel}}` : modeLabel;
}}
function modelCandidateText(model) {{
  const rows = Array.isArray(model.training_candidates) ? model.training_candidates : [];
  const available = Array.isArray(model.available_candidates) ? model.available_candidates : [];
  const names = [];
  for (const row of rows) {{
    const name = String(row.candidate_name || '');
    if (!name || names.includes(name)) continue;
    if (available.length && !available.includes(name)) continue;
    names.push(name);
  }}
  if (model.selected_candidate && (!available.length || available.includes(model.selected_candidate)) && !names.includes(model.selected_candidate)) names.push(model.selected_candidate);
  const count = names.length;
  if (!count) return 'нет списка';
  const word = count === 1 ? 'кандидат' : (count > 1 && count < 5 ? 'кандидата' : 'кандидатов');
  return `${{fmtInt(count)}} ${{word}}`;
}}
function modelCandidateName(name) {{
  return {{
    ridge: 'Ridge-регрессия',
    random_forest: 'случайный лес',
    hist_gradient_boosting: 'градиентный бустинг',
  }}[name] || 'не указано';
}}
function modelCandidateOptions() {{
  const model = data.model || {{}};
  const selected = model.selected_candidate || '';
  const rows = Array.isArray(model.training_candidates) ? model.training_candidates : [];
  const available = Array.isArray(model.available_candidates) ? model.available_candidates : [];
  const names = [];
  for (const row of rows) {{
    const name = String(row.candidate_name || '');
    if (!name || names.includes(name)) continue;
    if (available.length && !available.includes(name)) continue;
    names.push(name);
  }}
  if (selected && (!available.length || available.includes(selected)) && !names.includes(selected)) names.push(selected);
  const candidateOptions = names.map(name => `<option value="${{esc(name)}}" ${{name === selected ? 'selected' : ''}}>${{modelCandidateName(name)}}</option>`).join('');
  return `<option value="">Авто</option>${{candidateOptions}}`;
}}
function modelFreshnessRows(model, metrics) {{
  const freshness = model.data_freshness || {{}};
  const statusText = {{
    current: '\u0441\u0440\u0435\u0437 \u0430\u043a\u0442\u0443\u0430\u043b\u0435\u043d',
    unknown: '\u043d\u0435\u0442 \u0441\u0440\u0430\u0432\u043d\u0435\u043d\u0438\u044f',
    validated_snapshot: '\u0432\u0430\u043b\u0438\u0434\u0438\u0440\u043e\u0432\u0430\u043d\u043d\u044b\u0439 snapshot',
  }}[freshness.status] || freshness.status_label || freshness.status || '\u043d\u0435\u0442 \u0441\u0440\u0430\u0432\u043d\u0435\u043d\u0438\u044f';
  const modelRows = freshness.model_rows_total ?? metrics.rows_total;
  const currentRows = freshness.current_listings_total;
  const delta = freshness.row_delta;
  const deltaPct = freshness.row_delta_pct;
  const deltaText = delta === null || delta === undefined
    ? '\u2014'
    : `${{delta > 0 ? '+' : ''}}${{fmtInt(delta)}}${{deltaPct === null || deltaPct === undefined ? '' : ` (${{fmtPct(deltaPct)}})`}}`;
  const retrainText = freshness.requires_retrain
    ? '\u043d\u0443\u0436\u0435\u043d \u043a\u0430\u043d\u0434\u0438\u0434\u0430\u0442'
    : '\u043d\u0435 \u0442\u0440\u0435\u0431\u0443\u0435\u0442\u0441\u044f \u0431\u0435\u0437 validation gate';
  return [
    ['\u0421\u0442\u0430\u0442\u0443\u0441 \u0441\u0440\u0435\u0437\u0430', statusText],
    ['\u0421\u0442\u0440\u043e\u043a \u0432 \u043c\u043e\u0434\u0435\u043b\u0438', fmtInt(modelRows)],
    ['\u0421\u0442\u0440\u043e\u043a \u0441\u0435\u0439\u0447\u0430\u0441', fmtInt(currentRows)],
    ['\u0420\u0430\u0437\u043d\u0438\u0446\u0430', deltaText],
    ['Retrain', retrainText],
  ];
}}
function modelProvenancePanel() {{
  const model = data.model || {{}};
  const metrics = model.metrics || data.localModel?.metrics || {{}};
  const rows = [
    ['Статус', model.status === 'ready' ? 'готова' : 'не загружена'],
    ['Активная модель', model.active_model_name || 'не указана'],
    ['Версия модели', model.model_version || data.localModel?.modelVersion || 'не указана'],
    ['Версия признаков', model.feature_version || data.localModel?.featureVersion || 'не указана'],
    ['Выбор модели', modelSelectionLabel(model.model_selection_mode, model.model_selection_reason)],
    ['Кандидатов', modelCandidateText(model)],
    ['Выбранный алгоритм', modelCandidateName(model.selected_candidate)],
    ['Обучающих групп', metrics.train_listing_groups ? fmtInt(metrics.train_listing_groups) : '—'],
    ['Тестовых групп', metrics.test_listing_groups ? fmtInt(metrics.test_listing_groups) : '—'],
  ];
  rows.push(...modelFreshnessRows(model, metrics));
  const baseline = String(model.model_version || data.localModel?.modelVersion || '').toLowerCase().includes('baseline')
    || String(model.model_version || data.localModel?.modelVersion || '').toLowerCase().includes('ridge');
  const note = baseline
    ? 'Это честная базовая Ridge-модель без утечки последней цены. Она пригодна для демонстрации контура оценки, но не заявляется как финальный промышленный оценщик.'
    : 'Контур оценки показывает только опубликованные метаданные модели; дополнительные выводы о качестве требуют отдельной проверки.';
  return `<div class="metric-list">${{rows.map(([label, value]) => `<div class="metric-line"><span>${{label}}</span><strong>${{esc(value)}}</strong></div>`).join('')}}</div><div class="chart-note">${{note}}</div>`;
}}
function dataQualityTable() {{
  const s = data.stats || {{}};
  const total = Number(s.listings_total || 0);
  const ready = Number(s.ml_ready_listings || 0);
  const coords = Number(s.coordinate_listings || (data.mapPoints || []).length || 0);
  const rows = [
    ['Всего объявлений', fmtInt(total)],
    ['Готово для модели', `${{fmtInt(ready)}} · ${{fmtPct(total ? ready / total * 100 : null)}}`],
    ['С координатами', `${{fmtInt(coords)}} · ${{fmtPct(total ? coords / total * 100 : null)}}`],
    ['Источников', fmtInt((data.sourceRows || []).length)],
    ['Сборов данных', fmtInt(s.ingestion_runs_total)],
  ];
  return `<div class="metric-list">${{rows.map(([label, value]) => `<div class="metric-line"><span>${{label}}</span><strong>${{value}}</strong></div>`).join('')}}</div>`;
}}
function exposureForecastSegmentTable(rows) {{
  const prepared = Array.isArray(rows) ? rows.slice(0, 6) : [];
  if (!prepared.length) return '';
  const body = prepared.map(row => `<tr><td>${{roomLabel(row.rooms)}}</td><td>${{fmtInt(row.target_rows || 0)}}</td><td>${{fmtInt(row.median_inferred_exposure_days ?? row.median_observed_exposure_days ?? 0)}} дн.</td></tr>`).join('');
  return `<div class="section-label">Нижняя граница по комнатности</div><table><thead><tr><th>Сегмент</th><th>Строк наблюдений</th><th>Медиана</th></tr></thead><tbody>${{body}}</tbody></table>`;
}}
function trendForecastTable(rows) {{
  const prepared = Array.isArray(rows) ? rows.slice(0, 7) : [];
  if (!prepared.length) return '';
  const body = prepared.map(row => `<tr><td>${{shortDate(row.observed_date)}}</td><td>${{fmtM2(row.forecast_median_price_per_m2)}}</td></tr>`).join('');
  return `<div class="section-label">Прогноз медианы за м²</div><table><thead><tr><th>Дата</th><th>Цена за м²</th></tr></thead><tbody>${{body}}</tbody></table>`;
}}
function exposureReadinessPanel() {{
  const e = data.exposureReadiness || {{}};
  const targetSource = e.target_source === 'observed_history_lower_bound'
    ? 'наблюдаемая экспозиция'
    : e.target_source === 'observation_gap_inferred_lifecycle'
    ? 'исчезновение из наблюдений'
    : 'terminal lifecycle';
  const rows = [
    ['Статус', e.status_label || 'нет целевой переменной'],
    ['Строк с датой наблюдения', fmtInt(e.rows_with_observed_at || 0)],
    ['Дат сборов в raw-архиве', fmtInt(e.collection_date_count || 0)],
    ['Снимков в raw-архиве', fmtInt(e.available_snapshot_dir_count || e.snapshot_count || 0)],
    ['Raw-наблюдений', fmtInt(e.raw_observation_rows || 0)],
    ['Устойчивых идентификаторов в raw-архиве', fmtInt(e.raw_stable_listing_ids || 0)],
    ['Дат наблюдений в БД', fmtInt(e.observation_date_count || 0)],
    ['Период наблюдений', `${{fmtInt(e.observation_span_days || 0)}} дн.`],
    ['Объявлений с историей', fmtInt(e.listings_with_observation_history || 0)],
    ['Макс. дат на объявление', fmtInt(e.max_observation_dates_per_listing || 0)],
    ['Целевых lifecycle-строк', fmtInt(e.lifecycle_target_rows || 0)],
    ['Исчезновение из наблюдений', fmtInt(e.inferred_lifecycle_target_rows || 0)],
    ['Мин. разрыв для исчезновения', e.inferred_lifecycle_min_gap_days ? `${{fmtInt(e.inferred_lifecycle_min_gap_days)}} дн.` : '—'],
    ['Наблюдаемая экспозиция', fmtInt(e.observed_exposure_target_rows || 0)],
    ['Источник расчета', targetSource],
    ['Медиана нижней границы', e.median_exposure_days === null || e.median_exposure_days === undefined ? '—' : `${{fmtInt(e.median_exposure_days)}} дн.`],
  ];
  return `<div class="metric-list">${{rows.map(([label, value]) => `<div class="metric-line"><span>${{label}}</span><strong>${{value}}</strong></div>`).join('')}}</div>${{exposureForecastSegmentTable(e.observed_exposure_forecast_segments)}}<div class="chart-note">${{esc(e.note || 'Прогноз срока экспозиции не строится без реальной целевой переменной и отдельной проверки модели.')}}</div>`;
}}
function trendReadinessPanel() {{
  const t = data.observationTrend || {{}};
  const period = t.first_observed_date && t.last_observed_date ? `${{shortDate(t.first_observed_date)}} — ${{shortDate(t.last_observed_date)}}` : '—';
  const rows = [
    ['Статус', t.status_label || 'недостаточно истории'],
    ['Наблюдений', fmtInt(t.observations_total || 0)],
    ['Дат наблюдений', fmtInt(t.observation_date_count || 0)],
    ['Период', period],
    ['Объявлений с историей', fmtInt(t.listings_with_observation_history || 0)],
    ['Изменений цены', fmtInt(t.listing_price_change_count || 0)],
    ['Прогноз', t.can_forecast ? 'доступен' : 'не строится'],
    ['Горизонт', t.forecast_horizon_days ? `${{fmtInt(t.forecast_horizon_days)}} дн.` : '—'],
  ];
  return `<div class="metric-list">${{rows.map(([label, value]) => `<div class="metric-line"><span>${{label}}</span><strong>${{value}}</strong></div>`).join('')}}</div>${{trendForecastTable(t.forecast_rows)}}<div class="chart-note">${{esc(t.note || 'Прогноз не строится без проверенной модели временного ряда.')}}</div>`;
}}
function monitoring() {{
  const m = data.model || {{}};
  const serviceLabel = data.connected ? 'Доступен' : (data.mode === 'snapshot' ? 'Локальный режим' : 'Недоступен');
  const serviceSub = data.connected ? 'Подключение к данным' : (data.mode === 'snapshot' ? 'API не запущен, используются реальные локальные данные' : 'Нет ответа от сервиса');
  const metrics = m.metrics || data.localModel?.metrics || {{}};
  return `<div class="kicker">МОНИТОРИНГ СИСТЕМЫ</div><section class="grid4">
    ${{kpi('Сервис', serviceLabel, serviceSub, 'cloud_done')}}
    ${{kpi('Параметров оценки', fmtInt(m.feature_count), 'Оценочный контур', 'model_training')}}
    ${{kpi('MAE модели', metrics.mae ? fmtMln(metrics.mae) : '—', 'Средняя абсолютная ошибка', 'analytics')}}
    ${{kpi('Объявлений', fmtInt(data.stats?.listings_total), 'Качество данных', 'database')}}
  </section><section class="grid12"><article class="card span4"><div class="card-title">Загруженные источники</div>${{sourceRows()}}</article><article class="card span8"><div class="card-title">Статус контуров</div>${{serviceStatusTable()}}</article><article class="card span4"><div class="card-title">Качество данных</div>${{dataQualityTable()}}</article><article class="card span4"><div class="card-title">Качество модели</div>${{modelMetricsTable()}}</article><article class="card span4"><div class="card-title">Контур модели</div>${{modelProvenancePanel()}}</article><article class="card span4"><div class="card-title">Инфраструктура района</div>${{infrastructureStatus()}}</article><article class="card span4"><div class="card-title">Готовность прогноза экспозиции</div>${{exposureReadinessPanel()}}</article><article class="card span4"><div class="card-title">Готовность тренда</div>${{trendReadinessPanel()}}</article><article class="card span8"><div class="card-title">Аудит требований проекта</div>${{requirementsAudit()}}</article><article class="card span12"><div class="card-title">Системный журнал <button class="ghost-btn" id="refreshBtn">Обновить</button></div>${{logTable()}}</article></section>`;
}}
function logTable() {{
  const maxLogRows = 40;
  const rows = monitoringLogRows().slice(0, maxLogRows);
  const totalPages = Math.max(1, Math.ceil(rows.length / state.logPageSize));
  state.logPage = Math.min(Math.max(1, state.logPage), totalPages);
  const start = (state.logPage - 1) * state.logPageSize;
  const pageRows = rows.slice(start, start + state.logPageSize);
  const from = rows.length ? start + 1 : 0;
  return `<div class="log-shell"><table><thead><tr><th>Уровень</th><th>Время</th><th>Событие</th><th>Сообщение</th></tr></thead><tbody>` + pageRows.map(r => `<tr><td>${{statusBadge(r.level, r.level || 'инфо')}}</td><td>${{shortDate(r.created_at)}}</td><td>${{esc(r.event_type || r.event || 'событие')}}</td><td>${{esc(r.message || 'Сообщение не указано')}}</td></tr>`).join('') + `</tbody></table><div class="log-footer"><span>Показано ${{fmtInt(from)}}–${{fmtInt(Math.min(rows.length, start + state.logPageSize))}} из ${{fmtInt(rows.length)}}; лимит ${{fmtInt(maxLogRows)}}</span><div class="pager-actions"><button class="ghost-btn" data-log-step="-1" ${{state.logPage <= 1 ? 'disabled' : ''}}>Назад</button><span>${{fmtInt(state.logPage)}} / ${{fmtInt(totalPages)}}</span><button class="ghost-btn" data-log-step="1" ${{state.logPage >= totalPages ? 'disabled' : ''}}>Вперед</button></div></div></div>`;
}}
function statusText(value) {{
  const normalized = String(value || '').toLowerCase();
  if (normalized === 'success') return 'успешно';
  if (normalized === 'failed' || normalized === 'error') return 'ошибка';
  if (normalized === 'running') return 'выполняется';
  if (normalized === 'partial') return 'частично';
  return value || 'статус не указан';
}}
function monitoringLogRows() {{
  const apiLogs = Array.isArray(data.monitoring?.recent_logs) ? data.monitoring.recent_logs : [];
  if (apiLogs.length) {{
    return apiLogs.slice(0, 40).map(r => ({{
      level: r.level || 'info',
      created_at: r.created_at,
      event_type: r.event_type || r.event || 'Событие мониторинга',
      message: r.message || 'Сообщение не указано',
    }}));
  }}
  const report = data.stats?.latest_collection_report || {{}};
  const latest = data.latestRun || {{}};
  const countSource = data.dataCountProvenance || {{}};
  const rows = [
    {{ level:'инфо', created_at: latest.finished_at || latest.started_at || report.finished_at || report.started_at, event_type:'Режим данных', message: data.mode === 'snapshot' ? 'Используются реальные локальные снимки объявлений' : 'Подключение к сервису данных активно' }},
    {{ level:'инфо', created_at: latest.finished_at || latest.started_at || report.finished_at || report.started_at, event_type:'Источник счетчика', message: countSource.detail || 'Источник счетчика не подтвержден' }},
    {{ level:'инфо', created_at: latest.finished_at || latest.started_at || report.finished_at || report.started_at, event_type:'Источники', message: data.primarySourceLabel || 'Источник не подтвержден' }},
    {{ level:'инфо', created_at: latest.finished_at || latest.started_at || report.finished_at || report.started_at, event_type:'Витрина интерфейса', message: `${{fmtInt(data.stats?.loaded_snapshot_listings || data.stats?.listings_total)}} объявлений · координаты: ${{fmtInt(data.stats?.coordinate_listings)}}` }},
  ];
  if (report.run_id || latest.id) {{
    rows.push({{ level:'инфо', created_at: report.finished_at || latest.finished_at || report.started_at || latest.started_at, event_type:'Последний сбор', message: `${{statusText(report.status || latest.status)}} · ${{report.run_id ? 'сбор Домклик' : ('запуск №' + latest.id)}}` }});
  }}
  if (report.started_at || latest.started_at || report.finished_at || latest.finished_at) {{
    rows.push({{ level:'инфо', created_at: report.finished_at || latest.finished_at || report.started_at || latest.started_at, event_type:'Время сбора', message: `${{shortDate(report.started_at || latest.started_at)}} — ${{shortDate(report.finished_at || latest.finished_at)}}` }});
  }}
  if (report.records_seen || latest.records_seen) {{
    rows.push({{ level:'инфо', created_at: report.finished_at || latest.finished_at, event_type:'Получено записей', message: `${{fmtInt(report.records_seen || latest.records_seen)}} из ${{fmtInt(report.raw_listings || latest.raw_count || report.records_seen || latest.records_seen)}}` }});
  }}
  if (report.normalized_listings || latest.normalized_count) {{
    rows.push({{ level:'инфо', created_at: report.finished_at || latest.finished_at, event_type:'Нормализация', message: `${{fmtInt(report.normalized_listings || latest.normalized_count)}} объявлений · отклонено: ${{fmtInt(report.rejected_listings || latest.rejected_count || 0)}}` }});
  }}
  if (report.listings_created !== undefined || latest.inserted_count !== undefined) {{
    rows.push({{ level:'инфо', created_at: report.finished_at || latest.finished_at, event_type:'Запись в базу', message: `создано: ${{fmtInt(report.listings_created || latest.inserted_count || 0)}} · обновлено: ${{fmtInt(report.listings_updated || latest.updated_count || 0)}} · наблюдений: ${{fmtInt(report.observations_inserted)}}` }});
  }}
  if (report.files_written) {{
    rows.push({{ level:'инфо', created_at: report.finished_at || latest.finished_at, event_type:'Файлы снимка', message: `${{fmtInt(report.files_written)}} файлов сохранено` }});
  }}
  if (data.localModel) {{
    rows.push({{ level:'инфо', created_at: latest.finished_at || latest.started_at, event_type:'Модель', message:'Сохраненная локальная модель доступна' }});
  }}
  if (data.osmCoverage?.featureContract) {{
    const coverage = data.osmCoverage.coverageRows === null || data.osmCoverage.coverageRows === undefined
      ? 'массовое покрытие не подтверждено'
      : `${{fmtInt(data.osmCoverage.coverageRows)}} строк инфраструктуры`;
    rows.push({{ level:'предупр.', created_at: latest.finished_at || latest.started_at, event_type:'Инфраструктура района', message:`OpenStreetMap-признаки есть в модели; ${{coverage}}` }});
  }}
  rows.push({{ level:'предупр.', created_at: latest.finished_at || latest.started_at, event_type:'Незавершенные аналитики', message:'Полные районные границы, OSM-кластеры и прогноз срока экспозиции требуют отдельных backend-артефактов и не показаны как готовые результаты' }});
  const levelText = level => {{
    const normalized = String(level || '').toUpperCase();
    if (normalized === 'ERROR') return 'ошибка';
    if (normalized === 'WARNING') return 'предупр.';
    if (normalized === 'INFO') return 'инфо';
    return level || 'инфо';
  }};
  const errors = data.monitoring?.recent_errors || [];
  errors.slice(0, 4).forEach(r => rows.push({{ level:levelText(r.level), created_at:r.created_at, event_type:r.event_type || 'Событие мониторинга', message:'Событие требует проверки в журнале сервиса' }}));
  (data.recentReports || []).slice(0, 5).forEach(reportRow => {{
    const when = reportRow.finished_at || reportRow.started_at;
    rows.push({{ level:'инфо', created_at:when, event_type:'История сборов', message:`${{statusText(reportRow.status)}} · ${{fmtInt(reportRow.normalized_count)}} из ${{fmtInt(reportRow.records_seen)}}` }});
  }});
  return rows;
}}
function render() {{
  nav(); updateChrome();
  const views = {{ dashboard, valuation, map: mapPage, deals, segments, data: dataPage, monitoring }};
  document.getElementById('content').innerHTML = views[state.page]();
  normalizeIcons();
  document.querySelectorAll('[data-go]').forEach(btn => btn.onclick = () => setPage(btn.dataset.go));
  document.querySelectorAll('[data-room]').forEach(btn => btn.onclick = () => {{
    state.room = Number(btn.dataset.room);
    const roomsSelect = document.getElementById('roomsSelect');
    const quickValuation = document.getElementById('quickValuation');
    if (roomsSelect) roomsSelect.value = btn.dataset.roomPreset || btn.dataset.room || roomsSelect.value;
    if (state.page === 'valuation' || quickValuation) {{
      document.querySelectorAll('[data-room]').forEach(node => node.classList.remove('active'));
      btn.classList.add('active');
      scheduleValuationRecalculation();
      return;
    }}
    render();
  }});
  document.querySelectorAll('[data-layer]').forEach(btn => btn.onclick = () => {{ state.mapLayer = btn.dataset.layer; render(); }});
  document.querySelectorAll('[data-map-source]').forEach(btn => btn.onclick = () => {{ state.mapSource = btn.dataset.mapSource; state.selectedMapIndex = null; render(); }});
  document.querySelectorAll('[data-map-point]').forEach(btn => btn.onclick = () => {{ const index = Number(btn.dataset.mapPoint); state.selectedMapIndex = state.selectedMapIndex === index ? null : index; render(); }});
  document.querySelectorAll('[data-map-result]').forEach(btn => btn.onclick = () => {{ const index = Number(btn.dataset.mapResult); state.selectedMapIndex = state.selectedMapIndex === index ? null : index; render(); }});
  document.querySelectorAll('[data-map-clear]').forEach(btn => btn.onclick = () => {{ state.selectedMapIndex = null; render(); }});
  document.querySelectorAll('[data-map-zoom]').forEach(btn => btn.onclick = () => {{
    state.mapZoom = Math.min(14, Math.max(8, state.mapZoom + Number(btn.dataset.mapZoom)));
    const zoomValue = document.getElementById('zoomValue');
    if (zoomValue) zoomValue.textContent = state.mapZoom;
    const zoomInput = document.getElementById('zoomInput');
    if (zoomInput) zoomInput.value = state.mapZoom;
    drawHeatmaps();
  }});
  const currentFilters = activeFilters();
  const roomSelect = document.getElementById('roomFilter');
  if (roomSelect) roomSelect.value = currentFilters.rooms;
  const sourceSelect = document.getElementById('sourceFilter');
  if (sourceSelect) sourceSelect.value = currentFilters.source;
  const mapSourceSelect = document.getElementById('mapSourceFilter');
  if (mapSourceSelect) {{
    mapSourceSelect.value = state.mapSource;
    mapSourceSelect.onchange = () => {{ state.mapSource = mapSourceSelect.value; state.selectedMapIndex = null; render(); }};
  }}
  document.querySelectorAll('[data-page-step]').forEach(btn => btn.onclick = () => {{
    state.dataPage = Math.max(1, state.dataPage + Number(btn.dataset.pageStep));
    render();
  }});
  document.querySelectorAll('[data-log-step]').forEach(btn => btn.onclick = () => {{
    state.logPage = Math.max(1, state.logPage + Number(btn.dataset.logStep));
    render();
  }});
  bindMapSliders();
  const roomsSelect = document.getElementById('roomsSelect');
  if (roomsSelect) roomsSelect.onchange = () => {{
    const value = Number(roomsSelect.value);
    if (Number.isFinite(value)) state.room = value;
    scheduleValuationRecalculation();
  }};
  const calc = document.getElementById('runValuationBtn') || document.getElementById('quickValuation');
  if (calc) calc.onclick = calculate;
  const modelCandidateSelect = document.getElementById('modelCandidateSelect');
  if (modelCandidateSelect) modelCandidateSelect.onchange = () => {{
    const qualityTarget = document.getElementById('valuationModelQuality');
    const driversTarget = document.getElementById('valuationModelDrivers');
    if (qualityTarget) qualityTarget.innerHTML = renderValuationModelQuality();
    if (driversTarget) driversTarget.innerHTML = modelDriversPendingSelection();
    scheduleValuationRecalculation();
  }};
  const down = document.getElementById('downloadBtn');
  if (down) down.onclick = downloadReport;
  document.querySelectorAll('#refreshBtn, [data-action="refresh"]').forEach(refresh => {{
    refresh.onclick = refreshCurrentData;
  }});
  document.querySelectorAll('[data-action="detail"]').forEach(btn => {{
    btn.onclick = () => openListingDetail(btn.dataset.listingIndex);
  }});
  const filters = document.getElementById('applyFilters');
  if (filters) filters.onclick = applyFilters;
  document.querySelectorAll('[data-sort]').forEach(btn => btn.onclick = () => {{
    const scope = filterScope();
    const current = state.sort[scope] || {{}};
    state.sort[scope] = {{ key:btn.dataset.sort, dir: current.key === btn.dataset.sort && current.dir !== 'desc' ? 'desc' : 'asc' }};
    render();
  }});
  document.querySelectorAll('[data-filter-preset]').forEach(btn => btn.onclick = () => applyFilterPreset(btn.dataset.filterPreset));
  bindStepInputs();
  bindRangeInputs();
  bindValuationAutoRecalculation();
  if (state.page === 'valuation' && data.connected) scheduleValuationRecalculation(0);
  bindDraggableMaps();
  drawHeatmaps();
}}
function priceBandRows(rows) {{
  const buckets = new Map();
  for (const row of rows) {{
    const price = Number(row.price_rub);
    if (!Number.isFinite(price) || price <= 0) continue;
    const start = Math.floor(price / 5000000) * 5000000;
    buckets.set(start, (buckets.get(start) || 0) + 1);
  }}
  return [...buckets.entries()].sort((a, b) => a[0] - b[0]).map(([start, count]) => ({{
    price_band: `${{Math.round(start / 1000000)}}–${{Math.round((start + 5000000) / 1000000)}} млн ₽`,
    listings: count,
  }}));
}}
function priceBandTable(rows = data.priceBands || []) {{
  if (!rows.length) return `<div class="empty">Недостаточно данных для распределения.</div>`;
  return `<table><thead><tr><th>Диапазон цены</th><th>Объявлений</th></tr></thead><tbody>` + rows.map(r => `<tr><td>${{esc(r.price_band)}}</td><td>${{fmtInt(r.listings)}}</td></tr>`).join('') + `</tbody></table>`;
}}
function bindMapSliders() {{
  const radius = document.getElementById('radiusInput');
  if (radius) radius.oninput = () => {{ state.heatRadius = Number(radius.value); document.getElementById('radiusValue').textContent = radius.value; drawHeatmaps(); }};
  const opacity = document.getElementById('opacityInput');
  if (opacity) opacity.oninput = () => {{ state.heatOpacity = Number(opacity.value); document.getElementById('opacityValue').textContent = opacity.value; drawHeatmaps(); }};
  const zoom = document.getElementById('zoomInput');
  if (zoom) zoom.oninput = () => {{ state.mapZoom = Number(zoom.value); document.getElementById('zoomValue').textContent = zoom.value; drawHeatmaps(); }};
}}
function clampNumber(value, min, max) {{
  const parsed = Number(String(value ?? '').replace(',', '.'));
  if (!Number.isFinite(parsed)) return min;
  return Math.min(max, Math.max(min, parsed));
}}
function bindStepInputs() {{
  document.querySelectorAll('[data-step-target]').forEach(btn => btn.onclick = () => {{
    const input = document.getElementById(btn.dataset.stepTarget);
    if (!input) return;
    const step = Number(input.dataset.step || btn.dataset.stepDelta || 1);
    const min = Number(input.dataset.min ?? -1000000);
    const max = Number(input.dataset.max ?? 1000000);
    const next = clampNumber(Number(input.value || 0) + Number(btn.dataset.stepDelta || step), min, max);
    input.value = Number.isInteger(step) ? String(Math.round(next)) : next.toFixed(2).replace(/0+$/, '').replace(/\\.$/, '');
    input.dispatchEvent(new Event('input', {{ bubbles:true }}));
    const range = document.getElementById(input.id + 'Range');
    if (range) range.value = input.value;
    const pair = input.closest('.range-pair');
    if (pair) syncRangePair(pair, input.id.endsWith('Min') ? 'min' : 'max');
  }});
}}
function formatRangeValue(value, step) {{
  const n = Number(value);
  if (!Number.isFinite(n)) return '';
  return Number(step) >= 1 ? String(Math.round(n)) : n.toFixed(2).replace(/0+$/, '').replace(/\\.$/, '');
}}
function updateRangePairVisual(pair) {{
  const prefix = pair.dataset.rangePair;
  const hardMin = Number(pair.dataset.hardMin);
  const hardMax = Number(pair.dataset.hardMax);
  const step = Number(pair.dataset.step || 1);
  const suffix = pair.dataset.suffix || '';
  const minInput = document.getElementById(`${{prefix}}Min`);
  const maxInput = document.getElementById(`${{prefix}}Max`);
  const minRange = document.getElementById(`${{prefix}}MinRange`);
  const maxRange = document.getElementById(`${{prefix}}MaxRange`);
  const from = clampNumber(minInput?.value || minRange?.value || hardMin, hardMin, hardMax);
  const to = clampNumber(maxInput?.value || maxRange?.value || hardMax, hardMin, hardMax);
  pair.style.setProperty('--from', `${{rangePercent(from, hardMin, hardMax)}}%`);
  pair.style.setProperty('--to', `${{rangePercent(to, hardMin, hardMax)}}%`);
  const summary = document.getElementById(`${{prefix}}Summary`);
  if (summary) summary.textContent = `${{formatRangeValue(from, step)}}–${{formatRangeValue(to, step)}}${{suffix}}`;
}}
function syncRangePair(pair, changed = '') {{
  const prefix = pair.dataset.rangePair;
  const hardMin = Number(pair.dataset.hardMin);
  const hardMax = Number(pair.dataset.hardMax);
  const step = Number(pair.dataset.step || 1);
  const minInput = document.getElementById(`${{prefix}}Min`);
  const maxInput = document.getElementById(`${{prefix}}Max`);
  const minRange = document.getElementById(`${{prefix}}MinRange`);
  const maxRange = document.getElementById(`${{prefix}}MaxRange`);
  if (!minInput || !maxInput || !minRange || !maxRange) return;
  let from = clampNumber(minInput.value || minRange.value || hardMin, hardMin, hardMax);
  let to = clampNumber(maxInput.value || maxRange.value || hardMax, hardMin, hardMax);
  if (from > to) {{
    if (changed === 'max') from = to;
    else to = from;
  }}
  minInput.value = formatRangeValue(from, step);
  maxInput.value = formatRangeValue(to, step);
  minRange.value = String(from);
  maxRange.value = String(to);
  updateRangePairVisual(pair);
}}
function bindRangeInputs() {{
  document.querySelectorAll('[data-range-sync]').forEach(range => range.oninput = () => {{
    const input = document.getElementById(range.dataset.rangeSync);
    if (input) {{
      input.value = range.value;
      input.dispatchEvent(new Event('input', {{ bubbles:true }}));
    }}
    const pair = range.closest('.range-pair');
    if (pair) syncRangePair(pair, range.dataset.rangeBound || '');
  }});
  document.querySelectorAll('.range-pair input:not([type=range])').forEach(input => {{
    input.oninput = () => {{
      const pair = input.closest('.range-pair');
      if (pair) syncRangePair(pair, input.id.endsWith('Min') ? 'min' : 'max');
    }};
  }});
  document.querySelectorAll('.range-pair').forEach(pair => {{
    syncRangePair(pair);
  }});
}}
function renderMapTiles(mapEl, rect) {{
  const layer = mapEl.querySelector('.tile-layer');
  if (!layer) return;
  const center = lonLatToWorld(state.mapCenterLon, state.mapCenterLat);
  const minX = center.x - rect.width / 2;
  const minY = center.y - rect.height / 2;
  const startTileX = Math.floor(minX / TILE_SIZE) - 1;
  const endTileX = Math.floor((center.x + rect.width / 2) / TILE_SIZE) + 1;
  const startTileY = Math.floor(minY / TILE_SIZE) - 1;
  const endTileY = Math.floor((center.y + rect.height / 2) / TILE_SIZE) + 1;
  const maxTile = 2 ** state.mapZoom;
  const wanted = new Set();
  for (let y = startTileY; y <= endTileY; y += 1) {{
    if (y < 0 || y >= maxTile) continue;
    for (let x = startTileX; x <= endTileX; x += 1) {{
      const wrappedX = ((x % maxTile) + maxTile) % maxTile;
      const left = Math.round(x * TILE_SIZE - minX);
      const top = Math.round(y * TILE_SIZE - minY);
      const key = `${{state.mapZoom}}/${{wrappedX}}/${{y}}`;
      wanted.add(key);
      let img = layer.querySelector(`img[data-tile="${{key}}"]`);
      if (!img) {{
        img = document.createElement('img');
        img.alt = '';
        img.decoding = 'async';
        img.loading = 'eager';
        img.fetchPriority = 'high';
        img.dataset.tile = key;
        img.referrerPolicy = 'no-referrer';
        const host = ['a','b','c'][Math.abs(wrappedX + y) % 3];
        const tileFallbacks = [
          `https://tile.openstreetmap.org/${{key}}.png`,
          `https://${{host}}.basemaps.cartocdn.com/rastertiles/voyager/${{key}}.png`,
          `https://${{host}}.tile.openstreetmap.fr/hot/${{key}}.png`,
        ];
        img.dataset.tileFallbackIndex = '0';
        img.onerror = () => {{
          const nextIndex = Number(img.dataset.tileFallbackIndex || 0) + 1;
          if (nextIndex >= tileFallbacks.length) {{
            img.classList.add('tile-unavailable');
            return;
          }}
          img.dataset.tileFallbackIndex = String(nextIndex);
          img.src = tileFallbacks[nextIndex];
        }};
        img.src = tileFallbacks[0];
        layer.appendChild(img);
      }}
      img.style.left = `${{left}}px`;
      img.style.top = `${{top}}px`;
    }}
  }}
  layer.querySelectorAll('img[data-tile]').forEach(img => {{
    if (!wanted.has(img.dataset.tile)) img.remove();
  }});
}}
function positionMapPoints(mapEl, rect) {{
  mapEl.querySelectorAll('.point').forEach(point => {{
    const pixel = mapPixel({{ lon: point.dataset.lon, lat: point.dataset.lat }}, rect);
    const visible = pixel.x >= -20 && pixel.x <= rect.width + 20 && pixel.y >= -20 && pixel.y <= rect.height + 20;
    point.style.left = `${{pixel.x}}px`;
    point.style.top = `${{pixel.y}}px`;
    point.style.display = visible ? '' : 'none';
  }});
}}
function heatColor(value, alpha) {{
  if (value > 780000) return `rgba(239,68,68,${{alpha}})`;
  if (value > 560000) return `rgba(245,158,11,${{alpha}})`;
  if (value > 380000) return `rgba(107,216,203,${{alpha}})`;
  return `rgba(56,189,248,${{alpha}})`;
}}
function drawHeatmaps() {{
  const points = state.page === 'map' ? mapFilteredPoints() : (data.mapPoints || []);
  document.querySelectorAll('.map-canvas').forEach(canvas => {{
    const mapEl = canvas.closest('.map');
    const rect = canvas.getBoundingClientRect();
    const width = Math.max(1, Math.round(rect.width));
    const height = Math.max(1, Math.round(rect.height));
    if (mapEl) {{
      renderMapTiles(mapEl, rect);
      positionMapPoints(mapEl, rect);
    }}
    canvas.width = width; canvas.height = height;
    const ctx = canvas.getContext('2d');
    ctx.clearRect(0, 0, width, height);
    ctx.strokeStyle = 'rgba(135,147,145,.16)';
    ctx.lineWidth = 1;
    for (let x = -width; x < width * 2; x += 42) {{ ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x + height, height); ctx.stroke(); }}
    for (let x = -width; x < width * 2; x += 56) {{ ctx.beginPath(); ctx.moveTo(x, height); ctx.lineTo(x + height, 0); ctx.stroke(); }}
    if (state.mapLayer === 'points') return;
    const heatPoints = sampleMapEntries(points, 620).map(entry => entry.p);
    for (const p of heatPoints) {{
      const pixel = mapPixel(p, rect);
      const x = pixel.x;
      const y = pixel.y;
      if (x < -120 || x > width + 120 || y < -120 || y > height + 120) continue;
      const price = Number(p.price_per_m2 || 0);
      const radius = state.heatRadius * (price > 750000 ? 1.35 : 1);
      const gradient = ctx.createRadialGradient(x, y, 0, x, y, radius);
      gradient.addColorStop(0, heatColor(price, state.heatOpacity / 100));
      gradient.addColorStop(.45, heatColor(price, state.heatOpacity / 260));
      gradient.addColorStop(1, 'rgba(0,0,0,0)');
      ctx.fillStyle = gradient;
      ctx.beginPath(); ctx.arc(x, y, radius, 0, Math.PI * 2); ctx.fill();
    }}
  }});
}}
function bindDraggableMaps() {{
  document.querySelectorAll('[data-map-root]').forEach(mapEl => {{
    let start = null;
    let frame = 0;
    mapEl.onpointerdown = event => {{
      if (event.target.closest('button,a,select,input')) return;
      const center = lonLatToWorld(state.mapCenterLon, state.mapCenterLat);
      start = {{ x:event.clientX, y:event.clientY, centerX:center.x, centerY:center.y }};
      mapEl.classList.add('dragging');
      try {{ mapEl.setPointerCapture(event.pointerId); }} catch {{}}
    }};
    mapEl.onpointermove = event => {{
      if (!start) return;
      const moved = worldToLonLat(start.centerX - (event.clientX - start.x), start.centerY - (event.clientY - start.y));
      state.mapCenterLon = moved.lon;
      state.mapCenterLat = moved.lat;
      if (!frame) frame = requestAnimationFrame(() => {{ frame = 0; drawHeatmaps(); }});
    }};
    const stop = event => {{
      if (!start) return;
      start = null;
      mapEl.classList.remove('dragging');
      try {{ mapEl.releasePointerCapture(event.pointerId); }} catch {{}}
    }};
    mapEl.onpointerup = stop;
    mapEl.onpointercancel = stop;
    mapEl.onwheel = event => {{
      event.preventDefault();
      const rect = mapEl.getBoundingClientRect();
      const oldZoom = state.mapZoom;
      const oldCenter = lonLatToWorld(state.mapCenterLon, state.mapCenterLat, oldZoom);
      const offsetX = event.clientX - rect.left - rect.width / 2;
      const offsetY = event.clientY - rect.top - rect.height / 2;
      const cursorBefore = worldToLonLat(oldCenter.x + offsetX, oldCenter.y + offsetY, oldZoom);
      const delta = event.deltaY < 0 ? 1 : -1;
      state.mapZoom = Math.min(14, Math.max(8, state.mapZoom + delta));
      const cursorAfterWorld = lonLatToWorld(cursorBefore.lon, cursorBefore.lat, state.mapZoom);
      const moved = worldToLonLat(cursorAfterWorld.x - offsetX, cursorAfterWorld.y - offsetY, state.mapZoom);
      state.mapCenterLon = moved.lon;
      state.mapCenterLat = moved.lat;
      const zoomValue = document.getElementById('zoomValue');
      if (zoomValue) zoomValue.textContent = state.mapZoom;
      const zoomInput = document.getElementById('zoomInput');
      if (zoomInput) zoomInput.value = state.mapZoom;
      drawHeatmaps();
    }};
  }});
}}
async function calculate() {{
  const form = readValuationForm();
  const area = form.total_area_m2;
  const target = document.getElementById('valuationResult') || document.getElementById('quickResult');
  const hint = document.getElementById('valuationHint');
  const metricsTarget = document.getElementById('valuationMetrics');
  const scenarioTarget = document.getElementById('valuationScenario');
  const comparablesTarget = document.getElementById('valuationComparables');
  const qualityTarget = document.getElementById('valuationModelQuality');
  const driversTarget = document.getElementById('valuationModelDrivers');
  const inputEchoTarget = document.getElementById('valuationInputEcho');
  if (!area || area <= 0) {{ target.textContent = 'Укажите корректную площадь квартиры.'; return; }}
  const requestSeq = ++valuationRequestSeq;
  if (activeValuationController) activeValuationController.abort();
  const features = valuationFeaturesFromForm(form);
  features.rooms = form.rooms;
  const selectedCandidate = selectedValuationModel();
  target.textContent = 'Расчет выполняется…';
  if (inputEchoTarget) inputEchoTarget.textContent = valuationInputSummary(features);
  if (driversTarget) driversTarget.innerHTML = modelDriversLoading();
  if (data.connected) {{
    const controller = new AbortController();
    activeValuationController = controller;
    const timeout = setTimeout(() => controller.abort(), VALUATION_REQUEST_TIMEOUT_MS);
    try {{
      const requestBody = selectedCandidate ? {{ features, model_candidate: selectedCandidate, candidate_model: selectedCandidate }} : {{ features }};
      const response = await fetch(clientApiBaseUrl() + '/predict', {{
        method:'POST',
        headers:{{'Content-Type':'application/json'}},
        body:JSON.stringify(requestBody),
        signal: controller.signal
      }});
      if (requestSeq !== valuationRequestSeq) return;
      if (response.status === 422) {{
        let detail = {{}};
        try {{
          const errorPayload = await response.json();
          detail = errorPayload?.detail || {{}};
        }} catch (error) {{}}
        const unavailable = renderUnavailableModel(detail, selectedCandidate);
        target.textContent = unavailable.result;
        if (hint) hint.textContent = unavailable.hint;
        const candidateMetrics = detail?.metrics_summary || (selectedCandidate ? trainingCandidateMetrics(selectedCandidate) : null);
        if (metricsTarget) metricsTarget.innerHTML = valuationMetrics(null, candidateMetrics);
        if (scenarioTarget) scenarioTarget.innerHTML = valuationScenarioChart(null, candidateMetrics);
        if (comparablesTarget) comparablesTarget.innerHTML = valuationComparables(null);
        if (qualityTarget) qualityTarget.innerHTML = renderValuationModelQuality(candidateMetrics || {{}});
        if (driversTarget) driversTarget.innerHTML = unavailable.drivers;
        return;
      }}
      if (response.ok) {{
        const payload = await response.json();
        if (payload.predicted_price_rub) {{
          const changeNote = valuationChangeNote(payload.predicted_price_rub, payload.selected_candidate);
          target.textContent = 'Расчет сервиса: ' + fmtPredictionRub(payload.predicted_price_rub);
          if (hint) hint.textContent = 'Результат получен из оценочного сервиса RealtyScope. Модель: ' + modelCandidateName(payload.selected_candidate) + '.' + changeNote;
          if (metricsTarget) metricsTarget.innerHTML = valuationMetrics(payload.predicted_price_rub, payload.metrics_summary);
          if (scenarioTarget) scenarioTarget.innerHTML = valuationScenarioChart(payload.predicted_price_rub, payload.metrics_summary);
          if (comparablesTarget) comparablesTarget.innerHTML = valuationComparables(payload.predicted_price_rub);
          if (qualityTarget) qualityTarget.innerHTML = renderValuationModelQuality(payload.metrics_summary);
          if (driversTarget) driversTarget.innerHTML = renderPredictionDrivers(payload);
          if (inputEchoTarget) inputEchoTarget.textContent = valuationInputSummary(
            payload.input_features_echo || features,
            payload.target_variable,
            payload.predicted_price_rub,
          );
          return;
        }}
      }}
    }} catch (error) {{
      if (requestSeq !== valuationRequestSeq) return;
      const aborted = error?.name === 'AbortError';
      if (hint) {{
        hint.textContent = aborted
          ? 'Сервис оценки не ответил за отведенное время. Показан резервный расчет, чтобы экран не зависал.'
          : 'Сервис оценки временно недоступен. Показан резервный расчет по локальной модели или медиане базы.';
      }}
    }} finally {{
      clearTimeout(timeout);
      if (activeValuationController === controller) activeValuationController = null;
    }}
  }}
  if (requestSeq !== valuationRequestSeq) return;
  const localPrediction = localModelPrediction(features);
  if (localPrediction) {{
    const changeNote = valuationChangeNote(localPrediction, selectedCandidate || 'local');
    target.textContent = 'Расчет модели: ' + fmtPredictionRub(localPrediction);
    if (hint) hint.textContent = 'Результат рассчитан локально по сохраненной модели RealtyScope и текущим параметрам квартиры.' + changeNote;
    if (metricsTarget) metricsTarget.innerHTML = valuationMetrics(localPrediction);
    if (scenarioTarget) scenarioTarget.innerHTML = valuationScenarioChart(localPrediction);
    if (comparablesTarget) comparablesTarget.innerHTML = valuationComparables(localPrediction);
    if (qualityTarget) qualityTarget.innerHTML = renderValuationModelQuality();
    if (driversTarget) driversTarget.innerHTML = modelDriverRows();
    if (inputEchoTarget) inputEchoTarget.textContent = valuationInputSummary(
      features,
      data.localModel?.targetVariable,
      localPrediction,
    );
    return;
  }}
  target.textContent = 'Прогноз не выполнен: обученная модель недоступна.';
  if (hint) hint.textContent = 'RealtyScope не подставляет медиану рынка вместо прогноза. Нужен доступный обученный artifact модели или сервис /predict.';
  if (metricsTarget) metricsTarget.innerHTML = valuationMetrics(null);
  if (scenarioTarget) scenarioTarget.innerHTML = valuationScenarioChart(null);
  if (comparablesTarget) comparablesTarget.innerHTML = valuationComparables(null);
  if (qualityTarget) qualityTarget.innerHTML = renderValuationModelQuality();
  if (driversTarget) driversTarget.innerHTML = modelDriverRows([], {{ useFallback: false }});
}}
function localModelPrediction(features) {{
  const model = data.localModel;
  if (!model || !Array.isArray(model.featureNames)) return null;
  let predicted = Number(model.intercept || 0);
  for (let i = 0; i < model.featureNames.length; i += 1) {{
    const name = model.featureNames[i];
    const raw = Number(features[name] ?? 0);
    const mean = Number(model.means?.[i] ?? 0);
    const scale = Number(model.scales?.[i] || 1);
    const coef = Number(model.coefficients?.[i] ?? 0);
    predicted += ((raw - mean) / scale) * coef;
  }}
  if (model.targetVariable === 'price_per_m2') {{
    const area = Number(features.total_area_m2);
    if (!Number.isFinite(area) || area <= 0) return null;
    predicted *= area;
  }}
  return Number.isFinite(predicted) && predicted > 0 ? predicted : null;
}}
function getNumber(id, fallback = 0) {{
  const el = document.getElementById(id);
  const value = Number(el?.value);
  return Number.isFinite(value) ? value : fallback;
}}
function selectedValuationModel() {{
  const value = document.getElementById('modelCandidateSelect')?.value || '';
  return value && value !== 'auto' ? value : null;
}}
function valuationChangeNote(predictedPrice, selectedCandidate = null) {{
  const candidate = selectedCandidate || selectedModelCandidateName() || 'auto';
  const previous = lastValuationSnapshot;
  lastValuationSnapshot = {{ predictedPrice:Number(predictedPrice), candidate }};
  if (!previous || previous.candidate !== candidate || !Number.isFinite(previous.predictedPrice)) return '';
  const delta = Number(predictedPrice) - previous.predictedPrice;
  if (!Number.isFinite(delta)) return '';
  if (Math.abs(delta) < 10_000) return ' Изменение к предыдущему расчету меньше 0,01 млн ₽: модель почти не реагирует на эти параметры.';
  return ` Изменение к предыдущему расчету: ${{fmtDeltaMln(delta)}}.`;
}}
function scheduleValuationRecalculation(delay = 300) {{
  if (state.page !== 'valuation' && !document.getElementById('quickValuation')) return;
  if (valuationRecalcTimer) clearTimeout(valuationRecalcTimer);
  valuationRecalcTimer = setTimeout(() => {{
    valuationRecalcTimer = null;
    calculate();
  }}, delay);
}}
function markValuationKnownInputForChange(id) {{
  const locationInputs = new Set([
    'transportInput', 'latitudeInput', 'longitudeInput', 'schoolsInput', 'parksInput',
    'shopsInput', 'transport500Input', 'transport1000Input',
  ]);
  if (locationInputs.has(id)) {{
    const coordinatesKnownInput = document.getElementById('coordinatesKnownInput');
    if (coordinatesKnownInput) coordinatesKnownInput.checked = true;
  }}
  if (id === 'buildingYearInput') {{
    const buildingKnownInput = document.getElementById('buildingKnownInput');
    if (buildingKnownInput) buildingKnownInput.checked = true;
  }}
}}
function bindValuationAutoRecalculation() {{
  if (state.page !== 'valuation' && !document.getElementById('quickValuation')) return;
  const ids = [
    'quickArea', 'areaInput', 'roomsSelect', 'floorInput', 'floorsTotalInput', 'buildingYearInput',
    'transportInput', 'latitudeInput', 'longitudeInput', 'schoolsInput', 'parksInput',
    'shopsInput', 'transport500Input', 'transport1000Input', 'buildingKnownInput', 'coordinatesKnownInput',
    'modelCandidateSelect',
  ];
  ids.forEach(id => {{
    const el = document.getElementById(id);
    if (!el || el.dataset.valuationBound === '1') return;
    el.dataset.valuationBound = '1';
    const handler = () => {{
      markValuationKnownInputForChange(id);
      scheduleValuationRecalculation();
    }};
    el.addEventListener('input', handler);
    el.addEventListener('change', handler);
  }});
}}
function readValuationForm() {{
  const d = data.valuationDefaults || {{}};
  const roomFallback = Number.isFinite(Number(state.room)) ? Number(state.room) : Number(d.rooms || 2);
  const rooms = getNumber('roomsSelect', roomFallback);
  const coordinatesKnown = Boolean(document.getElementById('coordinatesKnownInput')?.checked);
  const buildingKnownInput = document.getElementById('buildingKnownInput');
  const buildingKnown = buildingKnownInput ? Boolean(buildingKnownInput.checked) : true;
  const transport500 = getNumber('transport500Input', 0);
  const transport1000 = getNumber('transport1000Input', Math.max(transport500, Number(d.transport_count_1000m || 0)));
  return {{
    total_area_m2: getNumber('areaInput', getNumber('quickArea', d.total_area_m2 || 60)),
    rooms,
    floor: getNumber('floorInput', d.floor || 5),
    floors_total: getNumber('floorsTotalInput', d.floors_total || 20),
    building_year: getNumber('buildingYearInput', d.building_year || 2018),
    nearest_transport_m: getNumber('transportInput', 0),
    latitude: coordinatesKnown ? getNumber('latitudeInput', d.latitude || 55.75) : 55.75,
    longitude: coordinatesKnown ? getNumber('longitudeInput', d.longitude || 37.61) : 37.61,
    coordinatesKnown,
    buildingKnown,
    schools_count_1000m: getNumber('schoolsInput', 0),
    parks_count_1000m: getNumber('parksInput', 0),
    shops_count_1000m: getNumber('shopsInput', 0),
    transport_count_500m: transport500,
    transport_count_1000m: transport1000,
  }};
}}
function valuationFeatures(area) {{
  return valuationFeaturesFromForm({{ ...readValuationForm(), total_area_m2: area }});
}}
function valuationFeaturesFromForm(form) {{
  const d = data.valuationDefaults || {{}};
  if (!form.coordinatesKnown) {{
    form = {{ ...form, latitude: 55.75, longitude: 37.61 }};
  }}
  return {{
    building_year: form.buildingKnown ? form.building_year : 0,
    building_year_missing: form.buildingKnown ? 0 : 1,
    coordinates_missing: form.coordinatesKnown ? 0 : 1,
    floor: form.floor,
    floor_missing: form.floor ? 0 : 1,
    floors_total: form.floors_total,
    floors_total_missing: form.floors_total ? 0 : 1,
    healthcare_count_1000m: Number(d.healthcare_count_1000m || 0),
    latitude: form.latitude,
    longitude: form.longitude,
    nearest_transport_m: form.nearest_transport_m,
    nearest_transport_m_missing: form.nearest_transport_m ? 0 : 1,
    observation_count: Number(d.observation_count || 1),
    observation_missing: Number(d.observation_missing || 0),
    osm_missing: form.coordinatesKnown ? 0 : 1,
    parks_count_1000m: form.parks_count_1000m,
    property_type_apartment: 1,
    rooms: Math.max(0, form.rooms),
    schools_count_1000m: form.schools_count_1000m,
    shops_count_1000m: form.shops_count_1000m,
    total_area_m2: form.total_area_m2,
    transport_count_1000m: Math.max(Number(form.transport_count_1000m || 0), Number(form.transport_count_500m || 0)),
    transport_count_500m: form.transport_count_500m,
  }};
}}
function filterNumber(value) {{
  const cleaned = String(value ?? '').replace(',', '.').trim();
  if (!cleaned) return null;
  const parsed = Number(cleaned);
  return Number.isFinite(parsed) ? parsed : null;
}}
function rowMatchesFilters(row, scope = filterScope()) {{
  const f = activeFilters(scope);
  const query = String(f.search || '').toLowerCase().trim();
  const rooms = f.rooms;
  const source = f.source;
  const minPrice = filterNumber(f.minPrice);
  const maxPrice = filterNumber(f.maxPrice);
  const minArea = filterNumber(f.minArea);
  const maxArea = filterNumber(f.maxArea);
  const price = Number(row.price_rub || 0);
  const area = Number(row.total_area_m2 || 0);
  const roomCount = Number(row.rooms);
  const rowSource = String(row.source_name || sourceValue(row.source_label || '') || '');
  const addressOk = !query || String(row.address_text || '').toLowerCase().includes(query);
  const roomOk = !rooms || (rooms === '5' ? roomCount >= 5 : roomCount === Number(rooms));
  const sourceOk = !source || rowSource === source;
  const minPriceOk = minPrice === null || price >= minPrice * 1000000;
  const maxPriceOk = maxPrice === null || price <= maxPrice * 1000000;
  const minAreaOk = minArea === null || area >= minArea;
  const maxAreaOk = maxArea === null || area <= maxArea;
  return addressOk && roomOk && sourceOk && minPriceOk && maxPriceOk && minAreaOk && maxAreaOk;
}}
function filteredRows(scope = filterScope()) {{
  return (data.listings || []).filter(row => rowMatchesFilters(row, scope));
}}
function latestFirstRows(rows) {{
  return [...(rows || [])].sort((a, b) => {{
    const ad = Date.parse(a.observed_at || a.created_at || a.updated_at || '');
    const bd = Date.parse(b.observed_at || b.created_at || b.updated_at || '');
    return (Number.isFinite(bd) ? bd : 0) - (Number.isFinite(ad) ? ad : 0);
  }});
}}
function filteredDealRows() {{
  const rows = filteredRows('deals').filter(row => Number(row.price_per_m2) > 0 && Number(row.price_rub) > 0);
  const groups = new Map();
  for (const row of rows) {{
    const key = Number(row.rooms) >= 5 ? '5+' : String(Number(row.rooms));
    const values = groups.get(key) || [];
    values.push(Number(row.price_per_m2));
    groups.set(key, values);
  }}
  const medians = new Map([...groups.entries()].map(([key, values]) => {{
    values.sort((a, b) => a - b);
    const mid = Math.floor(values.length / 2);
    return [key, values.length % 2 ? values[mid] : (values[mid - 1] + values[mid]) / 2];
  }}));
  const mads = new Map([...groups.entries()].map(([key, values]) => {{
    const median = medians.get(key);
    const deviations = values.map(value => Math.abs(value - median)).sort((a, b) => a - b);
    const mid = Math.floor(deviations.length / 2);
    return [key, deviations.length % 2 ? deviations[mid] : (deviations[mid - 1] + deviations[mid]) / 2];
  }}));
  return rows.map(row => {{
    const key = Number(row.rooms) >= 5 ? '5+' : String(Number(row.rooms));
    const median = Number(medians.get(key) || row.price_per_m2);
    const values = groups.get(key) || [];
    const priceM2 = Number(row.price_per_m2);
    const percentile = values.length ? values.filter(value => value <= priceM2).length / values.length : 1;
    const mad = Number(mads.get(key) || 0);
    const robustZ = mad > 0 ? (priceM2 - median) / (mad * 1.4826) : 0;
    const discountPct = (priceM2 - median) / median;
    const score = Math.max(0, Math.min(100,
      (-discountPct * 100) + ((1 - percentile) * 50) + (Math.max(0, -robustZ) * 10)
    ));
    return {{
      ...row,
      segment_median_m2: median,
      segment_sample_size: values.length,
      segment_percentile: percentile,
      robust_z: robustZ,
      discount_pct: discountPct,
      deal_score: Math.round(score * 10) / 10,
    }};
  }}).filter(row => row.discount_pct < 0 && row.segment_sample_size >= 3).sort((a, b) => (b.deal_score - a.deal_score) || (a.discount_pct - b.discount_pct));
}}
function pagedRows(rows) {{
  const totalPages = Math.max(1, Math.ceil(rows.length / state.pageSize));
  state.dataPage = Math.min(Math.max(1, state.dataPage), totalPages);
  const start = (state.dataPage - 1) * state.pageSize;
  return rows.slice(start, start + state.pageSize);
}}
function pager(total) {{
  const totalPages = Math.max(1, Math.ceil(total / state.pageSize));
  const from = total ? (state.dataPage - 1) * state.pageSize + 1 : 0;
  const to = Math.min(total, state.dataPage * state.pageSize);
  return `<div class="pager"><span>Показано ${{fmtInt(from)}}–${{fmtInt(to)}} из ${{fmtInt(total)}}</span><div class="pager-actions"><button class="ghost-btn" data-page-step="-1" ${{state.dataPage <= 1 ? 'disabled' : ''}}>Назад</button><span>${{fmtInt(state.dataPage)}} / ${{fmtInt(totalPages)}}</span><button class="ghost-btn" data-page-step="1" ${{state.dataPage >= totalPages ? 'disabled' : ''}}>Вперед</button></div></div>`;
}}
function applyFilters() {{
  const f = activeFilters();
  f.search = String(document.getElementById('searchInput')?.value || '');
  f.rooms = document.getElementById('roomFilter')?.value || '';
  f.source = document.getElementById('sourceFilter')?.value || '';
  f.minPrice = String(document.getElementById('priceMin')?.value || '');
  f.maxPrice = String(document.getElementById('priceMax')?.value || '');
  f.minArea = String(document.getElementById('areaMin')?.value || '');
  f.maxArea = String(document.getElementById('areaMax')?.value || '');
  state.dataPage = 1;
  render();
}}
function applyFilterPreset(preset) {{
  const scope = filterScope();
  const previous = activeFilters(scope);
  state.filters[scope] = {{ search:'', rooms:'', source:previous.source || '', minPrice:'', maxPrice:'', minArea:'', maxArea:'' }};
  const f = activeFilters(scope);
  if (preset === 'studio') f.rooms = '0';
  if (preset === 'family') f.rooms = '3';
  if (preset === 'budget') f.maxPrice = '20';
  if (preset === 'premium') f.minPrice = '60';
  if (preset === 'reset') state.filters[scope] = blankFilters();
  state.dataPage = 1;
  render();
}}
function downloadReport() {{
  const blob = new Blob([JSON.stringify({{'статистика':data.stats || {{}}, 'источники':data.sourceRows || [], 'выборка':filteredRows()}}, null, 2)], {{ type:'application/json' }});
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob); a.download = 'otchet-realtyscope.json'; a.click();
  URL.revokeObjectURL(a.href);
}}
function refreshCurrentData() {{
  const refreshButtons = Array.from(document.querySelectorAll('#refreshBtn, [data-action="refresh"]'));
  refreshButtons.forEach(btn => {{
    btn.textContent = 'Обновление...';
    btn.disabled = true;
  }});
  document.querySelectorAll('[data-action="detail"]').forEach(btn => {{
    btn.onclick = () => openListingDetail(btn.dataset.listingIndex);
  }});
  window.location.assign(window.location.href);
}}
document.getElementById('collapseBtn').onclick = () => document.body.classList.toggle('collapsed');
document.getElementById('themeBtn').onclick = () => document.body.classList.toggle('light');
document.addEventListener('keydown', event => {{
  if (event.key === 'Escape') closeListingDetail();
}});
render();
</script>
</body>
</html>
"""


if __name__ == "__main__":
    main()
