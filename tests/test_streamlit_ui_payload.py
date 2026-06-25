import json

import pandas as pd
from services.streamlit import app as streamlit_app
from services.streamlit.api_client import DashboardData, MonitoringData
from services.streamlit.app import (
    _build_payload,
    _comparable_rows,
    _data_count_provenance,
    _deal_rows,
    _district_cluster_rows,
    _district_comparison_rows,
    _district_from_address,
    _district_readiness_for_comparison_rows,
    _district_readiness_payload,
    _exposure_readiness_payload,
    _listing_rows,
    _map_point_rows,
    _map_quality_stats,
    _observation_trend_payload,
    _osm_coverage_payload,
    _service_status_rows,
    _source_observation_detail,
    _workstation_html,
)


def _write_district_boundary_fixture(path):
    payload = {
        "type": "FeatureCollection",
        "metadata": {
            "dataTitle": "Fixture/OpenStreetMap",
            "dataUrl": "https://example.test/boundaries",
        },
        "features": [
            {
                "type": "Feature",
                "properties": {"name": "район Раменки"},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [
                            [37.50, 55.65],
                            [37.70, 55.65],
                            [37.70, 55.85],
                            [37.50, 55.85],
                            [37.50, 55.65],
                        ]
                    ],
                },
            },
            {
                "type": "Feature",
                "properties": {"name": "Можайский район"},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [
                            [37.20, 55.60],
                            [37.40, 55.60],
                            [37.40, 55.80],
                            [37.20, 55.80],
                            [37.20, 55.60],
                        ]
                    ],
                },
            },
        ],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return path


def test_streamlit_api_timeout_default_allows_live_api_cold_start() -> None:
    assert streamlit_app.API_TIMEOUT_SECONDS >= 5.0


def test_data_count_provenance_separates_api_and_snapshot_counts() -> None:
    api = _data_count_provenance(
        stats={"listings_total": 17_046},
        mode="api",
        connected=True,
    )
    snapshot = _data_count_provenance(
        stats={"listings_total": 15_765, "loaded_snapshot_listings": 15_765},
        mode="snapshot",
        connected=False,
    )

    assert api["source"] == "api"
    assert api["count"] == 17_046
    assert "API" in api["label"]
    assert snapshot["source"] == "snapshot"
    assert snapshot["count"] == 15_765
    assert snapshot["snapshot_count"] == 15_765
    assert "снимок" in snapshot["label"].lower()
    assert "API" not in snapshot["label"]


def test_workstation_html_renders_data_count_provenance() -> None:
    html = _workstation_html(
        {
            "dataCountProvenance": {
                "source": "snapshot",
                "label": "Локальный снимок",
                "detail": "Локальный снимок: 15 765 объявлений; API недоступен",
                "count": 15_765,
                "snapshot_count": 15_765,
            }
        }
    )

    assert "Источник счетчика" in html
    assert "Локальный снимок" in html


def test_osm_coverage_payload_keeps_backend_coverage_evidence() -> None:
    payload = _osm_coverage_payload(
        local_model={"featureNames": ["osm_missing", "transport_count_500m"]},
        model_metadata={},
        stats={
            "osm_features_total": 24,
            "osm_featured_listings": 20,
            "osm_coverage_pct": 12.5,
            "osm_feature_version": "osm_local_v1",
            "osm_attribution": "OpenStreetMap contributors",
            "osm_live_rows": 18,
            "osm_local_extract_rows": 5,
            "osm_coordinate_derived_rows": 6,
            "osm_infrastructure_coverage_source": (
                "local_extract+live_overpass+coordinate_exact_match"
            ),
        },
    )

    assert payload["coverageRows"] == 24
    assert payload["featuredListings"] == 20
    assert payload["coveragePct"] == 12.5
    assert payload["featureVersion"] == "osm_local_v1"
    assert payload["attribution"] == "OpenStreetMap contributors"
    assert payload["liveRows"] == 18
    assert payload["localExtractRows"] == 5
    assert payload["coordinateDerivedRows"] == 6
    assert (
        payload["coverageSource"] == "local_extract+live_overpass+coordinate_exact_match"
    )


def test_local_model_payload_ignores_unloadable_fallback_artifact(monkeypatch, tmp_path) -> None:
    model_path = tmp_path / "selected_price_model_v1_non_leaky.joblib"
    model_path.write_bytes(b"not-a-real-joblib")

    monkeypatch.setattr(streamlit_app, "_local_model_path", lambda: model_path)
    monkeypatch.setattr(
        streamlit_app.joblib,
        "load",
        lambda _path: (_ for _ in ()).throw(ImportError("sklearn DLL unavailable")),
    )

    assert streamlit_app._local_model_payload() is None


def test_build_payload_keeps_local_model_fallback_with_api_model_metadata(monkeypatch) -> None:
    local_model = {
        "featureNames": ["rooms", "total_area_m2"],
        "means": [1.5, 55.0],
        "scales": [0.5, 10.0],
        "coefficients": [1_000_000.0, 250_000.0],
        "intercept": 20_000_000.0,
        "modelVersion": "baseline_ridge_v2_non_leaky",
        "featureVersion": "ml_features_v2_non_leaky",
        "metrics": {"rows_total": 8_366, "r2": 0.6231827045433119},
    }

    monkeypatch.setattr(streamlit_app, "_local_model_payload", lambda: local_model)

    payload = _build_payload(
        data=DashboardData(
            stats={"listings_total": 1, "source_counts": {"domclick": 1}},
            listings=[
                {
                    "id": 1,
                    "address_text": "ÐœÐ¾ÑÐºÐ²Ð°, Ð¢Ð²ÐµÑ€ÑÐºÐ°Ñ ÑƒÐ»Ð¸Ñ†Ð°, 1",
                    "rooms": 2,
                    "total_area_m2": 61.5,
                    "price_rub": 24_000_000,
                    "price_per_m2": 390_244,
                    "source_name": "domclick",
                    "latitude": 55.757,
                    "longitude": 37.615,
                }
            ],
            listings_total=1,
            errors=[],
        ),
        monitoring=MonitoringData(
            status={
                "status": "ok",
                "services": [
                    {
                        "key": "model",
                        "label": "ÐœÐ¾Ð´ÐµÐ»ÑŒ",
                        "status": "ok",
                        "status_label": "Ð“Ð¾Ñ‚Ð¾Ð²Ð°",
                        "detail": "baseline_ridge_v2_non_leaky",
                        "count": 23,
                    }
                ],
            },
            model_metadata={
                "status": "ready",
                "model_version": "baseline_ridge_v2_non_leaky",
                "feature_version": "ml_features_v2_non_leaky",
                "feature_count": 23,
                "feature_names": ["rooms", "total_area_m2"],
                "metrics_summary": {"rows_total": 8_366, "r2": 0.6231827045433119},
                "feature_importance": [
                    {"feature": "total_area_m2", "importance": 56_840_154.31}
                ],
            },
            errors=[],
        ),
    )

    assert payload["mode"] == "api"
    assert payload["localModel"] == local_model
    assert payload["model"]["model_version"] == "baseline_ridge_v2_non_leaky"
    assert payload["model"]["metrics"]["rows_total"] == 8_366
    assert payload["model"]["feature_importance"][0]["feature"] == "total_area_m2"


def test_build_payload_uses_full_analytics_rows_for_districts(monkeypatch) -> None:
    monkeypatch.setattr(streamlit_app, "_local_model_payload", lambda: None)
    preview_rows = [
        {
            "id": 1,
            "address_text": "Москва, Тверская улица, 1",
            "rooms": 2,
            "total_area_m2": 61.5,
            "price_rub": 24_000_000,
            "price_per_m2": 390_244,
            "source_name": "domclick",
            "latitude": 55.757,
            "longitude": 37.615,
        }
    ]
    analytics_rows = []
    index = 1
    for district, base_price_m2 in [
        ("Раменки", 900_000),
        ("Можайский", 430_000),
        ("Даниловский", 620_000),
    ]:
        for step in range(5):
            price_per_m2 = base_price_m2 + step * 10_000
            analytics_rows.append(
                {
                    "id": index,
                    "address_text": f"Россия, Москва, район {district}, улица {index}",
                    "rooms": 2,
                    "total_area_m2": 60.0,
                    "price_rub": price_per_m2 * 60,
                    "price_per_m2": price_per_m2,
                    "source_name": "domclick" if index % 2 else "cian",
                    "source_label": "Домклик" if index % 2 else "ЦИАН",
                    "transport_count_500m": step + 1,
                    "schools_count_1000m": step + 2,
                }
            )
            index += 1

    payload = _build_payload(
        data=DashboardData(
            stats={"listings_total": 15, "source_counts": {"domclick": 8, "cian": 7}},
            listings=preview_rows,
            analytics_listings=analytics_rows,
            listings_total=15,
            errors=[],
        ),
        monitoring=MonitoringData(status={"status": "ok"}, model_metadata={}, errors=[]),
    )

    assert [row["id"] for row in payload["listings"]] == [1]
    assert payload["listings"][0]["address_text"] == preview_rows[0]["address_text"]
    assert len(payload["districtComparison"]) == 3
    assert {row["district_name"] for row in payload["districtComparison"]} == {
        "Раменки",
        "Можайский",
        "Даниловский",
    }
    assert payload["districtReadiness"]["status"] == "partial"
    assert payload["districtReadiness"]["comparison_rows"] == 3
    assert all("transport_count_500m" in row for row in payload["districtComparison"])
    assert len(payload["districtClusters"]) == 3
    assert all(
        row["feature_source"] == "districtComparison+osm"
        for row in payload["districtClusters"]
    )


def test_build_payload_keeps_api_observation_trend_series(monkeypatch) -> None:
    monkeypatch.setattr(streamlit_app, "_local_model_payload", lambda: None)
    trend_payload = {
        "status": "ready",
        "can_forecast": True,
        "metric": "median_price_per_m2",
        "forecast_method": "linear_median_price_per_m2_v1",
        "forecast_horizon_days": 7,
        "history_points": 8,
        "trend_slope_per_day": 10_000,
        "forecast_rows": [
            {
                "observed_date": "2026-06-24",
                "forecast_median_price_per_m2": 430_000.0,
            }
        ],
        "caveat": "Краткосрочный прогноз построен по дневной медиане.",
        "rows": [
            {
                "observed_date": "2026-06-22",
                "observation_count": 1200,
                "listing_count": 1180,
                "median_price_rub": 22_000_000,
                "median_price_per_m2": 410_000.0,
            },
            {
                "observed_date": "2026-06-23",
                "observation_count": 2000,
                "listing_count": 1987,
                "median_price_rub": 24_000_000,
                "median_price_per_m2": 420_000.0,
            },
        ],
    }

    payload = _build_payload(
        data=DashboardData(
            stats={"listings_total": 1, "source_counts": {"domclick": 1}},
            listings=[
                {
                    "id": 1,
                    "address_text": "Москва, Тверская улица, 1",
                    "rooms": 2,
                    "total_area_m2": 61.5,
                    "price_rub": 24_000_000,
                    "price_per_m2": 390_244,
                    "source_name": "domclick",
                    "observed_at": "2026-06-01T12:00:00+00:00",
                }
            ],
            observation_trend=trend_payload,
            listings_total=1,
            errors=[],
        ),
        monitoring=MonitoringData(status={"status": "ok"}, model_metadata={}, errors=[]),
    )

    assert payload["observationTrendSeries"] == trend_payload["rows"]
    assert payload["observationTrend"]["can_forecast"] is True
    assert payload["observationTrend"]["forecast_method"] == "linear_median_price_per_m2_v1"
    assert payload["observationTrend"]["forecast_rows"] == trend_payload["forecast_rows"]


def test_listing_rows_keep_reviewer_table_fields() -> None:
    frame = pd.DataFrame(
        [
            {
                "id": 1,
                "address_text": "Москва, Тверская улица, 1",
                "rooms": 2,
                "total_area_m2": 61.5,
                "price_rub": 24_000_000,
                "price_per_m2": 390_244,
                "source_name": "domclick",
                "source_label": "Домклик",
                "source_url": "https://example.test/listing/1",
                "observed_at": "2026-06-23T22:25:10+03:00",
                "floor": 7,
                "floors_total": 16,
                "building_year": 2019,
                "latitude": 55.757,
                "longitude": 37.615,
            }
        ]
    )

    [row] = _listing_rows(frame)

    assert row["floor"] == 7
    assert row["floors_total"] == 16
    assert row["building_year"] == 2019
    assert row["observed_at"] == "2026-06-23T22:25:10+03:00"
    assert row["latitude"] == 55.757
    assert row["longitude"] == 37.615


def test_source_observation_detail_separates_collection_dates_from_rows() -> None:
    detail = _source_observation_detail(
        collection_date_count=2,
        observation_count=2_441,
        snapshot_count=None,
    )

    assert "2" in detail
    assert "2 441" in detail
    assert "дат" in detail
    assert "наблюден" in detail


def test_map_points_are_self_contained_and_clamped_to_moscow_bounds() -> None:
    frame = pd.DataFrame(
        [
            {
                "address_text": "Москва, Арбат, 10",
                "rooms": 2,
                "total_area_m2": 54.0,
                "price_rub": 32_000_000,
                "price_per_m2": 592_592,
                "source_name": "cian",
                "source_label": "ЦИАН",
                "source_url": "https://example.test/cian/1",
                "latitude": 55.752,
                "longitude": 37.592,
            },
            {
                "address_text": "Координаты перепутаны",
                "rooms": 1,
                "total_area_m2": 38.0,
                "price_rub": 14_000_000,
                "price_per_m2": 368_421,
                "source_name": "domclick",
                "source_label": "Домклик",
                "source_url": "https://example.test/domclick/2",
                "latitude": 37.61,
                "longitude": 55.76,
            },
            {
                "address_text": "Санкт-Петербург",
                "rooms": 3,
                "total_area_m2": 70.0,
                "price_rub": 18_000_000,
                "price_per_m2": 257_142,
                "source_name": "domclick",
                "source_label": "Домклик",
                "source_url": "https://example.test/domclick/3",
                "latitude": 59.93,
                "longitude": 30.31,
            },
        ]
    )

    points = _map_point_rows(frame)

    assert len(points) == 2
    assert points[0] == {
        "lat": 55.752,
        "lon": 37.592,
        "listing_index": 0,
        "price_rub": 32_000_000,
        "price_per_m2": 592_592,
        "rooms": 2,
        "total_area_m2": 54.0,
        "address_text": "Москва, Арбат, 10",
        "source_name": "cian",
        "source_label": "ЦИАН",
        "source_url": "https://example.test/cian/1",
    }
    assert points[1]["lat"] == 55.76
    assert points[1]["lon"] == 37.61

    assert _map_quality_stats(frame) == {
        "coordinate_rows": 3,
        "valid_moscow_points": 2,
        "excluded_coordinate_rows": 1,
    }


def test_deal_rows_use_robust_real_segment_score() -> None:
    frame = pd.DataFrame(
        [
            {
                "address_text": "Москва, скидка 1",
                "rooms": 2,
                "total_area_m2": 50.0,
                "price_rub": 15_000_000,
                "price_per_m2": 300_000,
                "source_name": "domclick",
                "source_label": "Домклик",
                "source_url": "https://example.test/deal/1",
            },
            {
                "address_text": "Москва, скидка 2",
                "rooms": 2,
                "total_area_m2": 55.0,
                "price_rub": 22_000_000,
                "price_per_m2": 400_000,
                "source_name": "domclick",
                "source_label": "Домклик",
                "source_url": "https://example.test/deal/2",
            },
            {
                "address_text": "Москва, медиана 1",
                "rooms": 2,
                "total_area_m2": 60.0,
                "price_rub": 30_000_000,
                "price_per_m2": 500_000,
                "source_name": "cian",
                "source_label": "ЦИАН",
                "source_url": "https://example.test/deal/3",
            },
            {
                "address_text": "Москва, верх",
                "rooms": 2,
                "total_area_m2": 65.0,
                "price_rub": 39_000_000,
                "price_per_m2": 600_000,
                "source_name": "cian",
                "source_label": "ЦИАН",
                "source_url": "https://example.test/deal/4",
            },
        ]
    )

    rows = _deal_rows(frame)

    assert [row["address_text"] for row in rows] == ["Москва, скидка 1", "Москва, скидка 2"]
    assert rows[0]["segment_median_m2"] == 450_000
    assert rows[0]["segment_sample_size"] == 4
    assert rows[0]["segment_percentile"] == 0.25
    assert rows[0]["robust_z"] < 0
    assert rows[0]["deal_score"] > rows[1]["deal_score"]


def test_comparable_rows_use_real_room_area_price_neighbors() -> None:
    frame = pd.DataFrame(
        [
            {
                "address_text": "Москва, похожая 1",
                "rooms": 2,
                "total_area_m2": 61.0,
                "price_rub": 31_000_000,
                "price_per_m2": 508_196,
                "source_name": "domclick",
                "source_label": "Домклик",
                "source_url": "https://example.test/comparable/1",
                "floor": 6,
                "floors_total": 18,
                "observed_at": "2026-06-23T22:25:10+03:00",
            },
            {
                "address_text": "Москва, похожая 2",
                "rooms": 2,
                "total_area_m2": 58.0,
                "price_rub": 28_000_000,
                "price_per_m2": 482_758,
                "source_name": "cian",
                "source_label": "ЦИАН",
                "source_url": "https://example.test/comparable/2",
                "floor": 4,
                "floors_total": 12,
                "observed_at": "2026-06-22T10:00:00+03:00",
            },
            {
                "address_text": "Москва, другая комнатность",
                "rooms": 3,
                "total_area_m2": 60.0,
                "price_rub": 30_000_000,
                "price_per_m2": 500_000,
                "source_name": "domclick",
                "source_label": "Домклик",
                "source_url": "https://example.test/comparable/3",
            },
        ]
    )

    rows = _comparable_rows(frame, target_rooms=2, target_area_m2=60.0, target_price_per_m2=500_000)

    assert [row["address_text"] for row in rows] == ["Москва, похожая 1", "Москва, похожая 2"]
    assert rows[0]["comparison_score"] < rows[1]["comparison_score"]
    assert rows[0]["area_delta_m2"] == 1.0
    assert rows[0]["price_per_m2_delta_pct"] == 1.6392
    assert rows[0]["source_url"] == "https://example.test/comparable/1"


def test_district_readiness_marks_missing_without_structured_district_fields() -> None:
    frame = pd.DataFrame(
        [
            {
                "address_text": "Москва, Тверская улица, 1",
                "rooms": 2,
                "price_rub": 24_000_000,
                "price_per_m2": 390_244,
            }
        ]
    )

    readiness = _district_readiness_payload(frame)

    assert readiness["can_compare"] is False
    assert readiness["status"] == "missing"
    assert readiness["detected_fields"] == []
    assert readiness["listings_with_district"] == 0


def test_district_readiness_detects_real_structured_district_field() -> None:
    frame = pd.DataFrame(
        [
            {
                "district": "Тверской",
                "address_text": "Москва, Тверская улица, 1",
                "price_rub": 24_000_000,
                "price_per_m2": 390_244,
            },
            {
                "district": "Тверской",
                "address_text": "Москва, Тверская улица, 2",
                "price_rub": 25_000_000,
                "price_per_m2": 410_000,
            },
            {
                "district": "Арбат",
                "address_text": "Москва, Арбат, 10",
                "price_rub": 30_000_000,
                "price_per_m2": 500_000,
            },
        ]
    )

    readiness = _district_readiness_payload(frame)

    assert readiness["can_compare"] is True
    assert readiness["status"] == "ready"
    assert readiness["detected_fields"] == ["district"]
    assert readiness["listings_with_district"] == 3
    assert readiness["district_count"] == 2


def test_district_readiness_requires_real_comparison_rows() -> None:
    readiness = {
        "status": "partial",
        "can_compare": True,
        "listings_with_district": 4,
        "district_count": 3,
    }

    adjusted = _district_readiness_for_comparison_rows(readiness, district_rows=[])

    assert adjusted["can_compare"] is False
    assert adjusted["status"] == "missing"
    assert adjusted["comparison_rows"] == 0


def test_district_from_address_extracts_source_provided_moscow_district() -> None:
    assert (
        _district_from_address(
            "Россия, Москва, Западный административный округ, район Раменки, жилой комплекс Событие"
        )
        == "Раменки"
    )
    assert (
        _district_from_address(
            "Россия, Москва, Западный административный округ, "
            "Можайский район, жилой комплекс Верейская 41"
        )
        == "Можайский"
    )
    assert _district_from_address("Москва, Тверская улица, 1") is None


def test_district_comparison_rows_use_extracted_real_address_districts() -> None:
    frame = pd.DataFrame(
        [
            {
                "address_text": "Россия, Москва, район Раменки, улица 1",
                "price_rub": 30_000_000,
                "price_per_m2": 500_000,
                "source_name": "domclick",
                "transport_count_500m": 2,
                "schools_count_1000m": 3,
            },
            {
                "address_text": "Россия, Москва, район Раменки, улица 2",
                "price_rub": 32_000_000,
                "price_per_m2": 520_000,
                "source_name": "cian",
                "transport_count_500m": 4,
                "schools_count_1000m": 5,
            },
            {
                "address_text": "Россия, Москва, Можайский район, улица 3",
                "price_rub": 22_000_000,
                "price_per_m2": 410_000,
                "source_name": "cian",
                "transport_count_500m": 1,
                "schools_count_1000m": 2,
            },
            {
                "address_text": "Москва, район без цены",
                "price_rub": None,
                "price_per_m2": None,
                "source_name": "domclick",
            },
        ]
    )

    rows = _district_comparison_rows(frame, min_sample_size=1)

    assert [row["district_name"] for row in rows] == ["Раменки", "Можайский"]
    assert rows[0]["listings"] == 2
    assert rows[0]["median_price_per_m2"] == 510_000
    assert rows[0]["median_price_rub"] == 31_000_000
    assert rows[0]["source_count"] == 2
    assert rows[0]["transport_count_500m"] == 3
    assert rows[0]["schools_count_1000m"] == 4
    assert rows[0]["extraction_source"] == "address_text"
    assert rows[1]["listings"] == 1


def test_district_comparison_prefers_boundary_geojson_when_coordinates_match(
    monkeypatch, tmp_path
) -> None:
    boundary_path = _write_district_boundary_fixture(tmp_path / "districts.geojson")
    monkeypatch.setattr(streamlit_app, "DISTRICT_BOUNDARY_GEOJSON_PATH", boundary_path)
    streamlit_app._district_boundary_index.cache_clear()
    frame = pd.DataFrame(
        [
            {
                "address_text": "Москва, улица без района 1",
                "latitude": 55.75,
                "longitude": 37.61,
                "price_rub": 30_000_000,
                "price_per_m2": 500_000,
                "source_name": "domclick",
            },
            {
                "address_text": "Москва, улица без района 2",
                "latitude": 55.76,
                "longitude": 37.62,
                "price_rub": 32_000_000,
                "price_per_m2": 520_000,
                "source_name": "cian",
            },
            {
                "address_text": "Москва, улица без района 3",
                "latitude": 55.70,
                "longitude": 37.30,
                "price_rub": 22_000_000,
                "price_per_m2": 410_000,
                "source_name": "cian",
            },
        ]
    )

    readiness = _district_readiness_payload(frame)
    rows = _district_comparison_rows(frame, min_sample_size=1)

    assert readiness["status"] == "ready"
    assert readiness["active_field"] == "boundary_geojson"
    assert readiness["extraction_source"] == "admin_boundary_geojson"
    assert readiness["listings_with_district"] == 3
    assert readiness["coverage_pct"] == 100
    assert readiness["boundary_source_title"] == "Fixture/OpenStreetMap"
    assert [row["district_name"] for row in rows] == ["Раменки", "Можайский"]
    assert all(row["extraction_source"] == "admin_boundary_geojson" for row in rows)
    streamlit_app._district_boundary_index.cache_clear()


def test_district_cluster_rows_use_real_district_feature_matrix() -> None:
    district_rows = [
        {
            "district_name": "Раменки",
            "listings": 120,
            "median_price_per_m2": 900_000,
            "median_price_rub": 60_000_000,
            "min_price_per_m2": 820_000,
            "max_price_per_m2": 1_050_000,
            "source_count": 2,
        },
        {
            "district_name": "Пресненский",
            "listings": 90,
            "median_price_per_m2": 850_000,
            "median_price_rub": 55_000_000,
            "min_price_per_m2": 780_000,
            "max_price_per_m2": 980_000,
            "source_count": 2,
        },
        {
            "district_name": "Можайский",
            "listings": 80,
            "median_price_per_m2": 420_000,
            "median_price_rub": 24_000_000,
            "min_price_per_m2": 360_000,
            "max_price_per_m2": 500_000,
            "source_count": 1,
        },
        {
            "district_name": "Нижегородский",
            "listings": 70,
            "median_price_per_m2": 390_000,
            "median_price_rub": 21_000_000,
            "min_price_per_m2": 340_000,
            "max_price_per_m2": 470_000,
            "source_count": 1,
        },
        {
            "district_name": "Сокольники",
            "listings": 50,
            "median_price_per_m2": 620_000,
            "median_price_rub": 36_000_000,
            "min_price_per_m2": 570_000,
            "max_price_per_m2": 700_000,
            "source_count": 2,
        },
        {
            "district_name": "Басманный",
            "listings": 55,
            "median_price_per_m2": 650_000,
            "median_price_rub": 38_000_000,
            "min_price_per_m2": 590_000,
            "max_price_per_m2": 720_000,
            "source_count": 2,
        },
    ]

    clusters = _district_cluster_rows(district_rows, cluster_count=3)

    assert len(clusters) == 6
    assert len({row["cluster_id"] for row in clusters}) == 3
    assert {row["district_name"] for row in clusters} == {
        "Раменки",
        "Пресненский",
        "Можайский",
        "Нижегородский",
        "Сокольники",
        "Басманный",
    }
    premium = [row for row in clusters if "Премиальный" in row["cluster_label"]]
    accessible = [row for row in clusters if "Доступный" in row["cluster_label"]]
    assert {row["district_name"] for row in premium} == {"Раменки", "Пресненский"}
    assert {row["district_name"] for row in accessible} == {"Можайский", "Нижегородский"}
    assert all(row["feature_source"] == "districtComparison" for row in clusters)
    assert all(row["cluster_size"] >= 1 for row in clusters)


def test_district_cluster_rows_use_osm_features_when_available() -> None:
    district_rows = [
        {
            "district_name": "Раменки",
            "listings": 120,
            "median_price_per_m2": 900_000,
            "median_price_rub": 60_000_000,
            "min_price_per_m2": 820_000,
            "max_price_per_m2": 1_050_000,
            "source_count": 2,
            "transport_count_500m": 4,
            "schools_count_1000m": 6,
        },
        {
            "district_name": "Пресненский",
            "listings": 90,
            "median_price_per_m2": 850_000,
            "median_price_rub": 55_000_000,
            "min_price_per_m2": 780_000,
            "max_price_per_m2": 980_000,
            "source_count": 2,
            "transport_count_500m": 5,
            "schools_count_1000m": 5,
        },
        {
            "district_name": "Можайский",
            "listings": 80,
            "median_price_per_m2": 420_000,
            "median_price_rub": 24_000_000,
            "min_price_per_m2": 360_000,
            "max_price_per_m2": 500_000,
            "source_count": 1,
            "transport_count_500m": 1,
            "schools_count_1000m": 2,
        },
    ]

    clusters = _district_cluster_rows(district_rows, cluster_count=2)

    assert len(clusters) == 3
    assert all(row["feature_source"] == "districtComparison+osm" for row in clusters)
    assert all("transport_count_500m" in row for row in clusters)
    assert all("schools_count_1000m" in row for row in clusters)


def test_workstation_html_renders_district_cluster_panel() -> None:
    html = _workstation_html(
        {
            "mode": "snapshot",
            "stats": {"listings_total": 2},
            "rows": [],
            "mapPoints": [],
            "deals": [],
            "dashboard": {"room_summary": [], "price_bands": []},
            "districtReadiness": {
                "listings_with_district": 2,
                "coverage_pct": 100.0,
                "extraction_source": "address_text",
            },
            "districtComparison": [],
            "districtClusters": [
                {
                    "district_name": "Раменки",
                    "cluster_id": 2,
                    "cluster_label": "Премиальный профиль",
                    "listings": 40,
                    "median_price_per_m2": 500_000,
                    "feature_source": "districtComparison",
                }
            ],
        }
    )

    assert "Кластеры районов" in html
    assert "function districtClusterPanel()" in html
    assert "districtClusterPanel()" in html
    assert "Кластеры не заявляются как OSM-инфраструктурные" in html


def test_workstation_html_renders_missing_district_cluster_readiness() -> None:
    html = _workstation_html(
        {
            "mode": "api",
            "stats": {"listings_total": 16_512},
            "rows": [],
            "mapPoints": [],
            "deals": [],
            "dashboard": {"room_summary": [], "price_bands": []},
            "districtReadiness": {
                "can_compare": False,
                "listings_with_district": 0,
                "coverage_pct": 0.4,
                "extraction_source": "address_text",
            },
            "districtComparison": [],
            "districtClusters": [],
        }
    )

    assert "Готовность кластеризации районов" in html
    assert "нет районной матрицы" in html
    assert "Кластеризация районов не показывается" in html


def test_workstation_html_renders_model_provenance_and_baseline_caveat() -> None:
    html = _workstation_html(
        {
            "mode": "api",
            "stats": {"listings_total": 16_512},
            "rows": [],
            "mapPoints": [],
            "deals": [],
            "dashboard": {"room_summary": [], "price_bands": []},
            "model": {
                "status": "ready",
                "active_model_name": "realtyscope-price-model",
                "model_version": "baseline_ridge_v2_non_leaky",
                "feature_version": "ml_features_v2_non_leaky",
                "model_selection_mode": "best_metric",
                "model_selection_reason": "best_validation_metric",
                "selected_candidate": "hist_gradient_boosting",
                "model_candidates": [
                    {"model_version": "baseline_ridge_v2_non_leaky"},
                    {"model_version": "baseline_ridge_v1"},
                ],
                "training_candidates": [
                    {"candidate_name": "random_forest", "r2": 0.64},
                    {"candidate_name": "hist_gradient_boosting", "r2": 0.65},
                    {"candidate_name": "ridge", "r2": 0.62},
                ],
                "feature_count": 23,
                "metrics": {
                    "rows_total": 8_366,
                    "train_listing_groups": 6_692,
                    "test_listing_groups": 1_674,
                    "r2": 0.6231827045433119,
                },
            },
        }
    )

    assert "Контур модели" in html
    assert "baseline_ridge_v2_non_leaky" in html
    assert "ml_features_v2_non_leaky" in html
    assert "Выбор модели" in html
    assert "по метрикам" in html
    assert "modelCandidateText" in html
    assert "кандидата" in html
    assert "Выбранный алгоритм" in html
    assert "градиентный бустинг" in html
    assert "modelCandidateOptions" in html
    assert "modelCandidateSelect" in html
    assert "model_candidate" in html
    assert "row.candidate_artifact_path || name === selected" not in html
    assert "Авто" in html
    assert "базовая Ridge-модель" in html
    assert "не заявляется как финальный промышленный оценщик" in html


def test_workstation_html_prefers_api_model_metrics_over_local_fallback() -> None:
    html = _workstation_html(
        {
            "model": {"metrics": {"r2": 0.88}},
            "localModel": {"metrics": {"r2": 0.62}},
        }
    )

    assert "data.model?.metrics || data.localModel?.metrics" in html
    assert "data.localModel?.metrics || data.model?.metrics" not in html


def test_workstation_html_auto_refreshes_when_api_monitoring_signature_changes() -> None:
    html = _workstation_html({"mode": "api", "connected": True, "apiBaseUrl": "http://api.test"})

    assert "scheduleAutoRefresh" in html
    assert "setInterval" in html
    assert "/monitoring/status" in html
    assert "document.hidden" in html
    assert "window.location.reload()" in html


def test_workstation_html_recalculates_when_model_candidate_changes() -> None:
    html = _workstation_html({})

    assert "modelCandidateSelect.onchange" in html
    assert "void calculate()" in html


def test_workstation_html_updates_valuation_model_blocks_from_prediction_payload() -> None:
    html = _workstation_html({})

    assert "function activeValuationMetrics" in html
    assert "function renderValuationModelQuality" in html
    assert 'id="valuationModelQuality"' in html
    assert 'id="valuationModelDrivers"' in html
    assert "payload.metrics_summary" in html
    assert "payload.feature_importance" in html
    assert "valuationMetrics(payload.predicted_price_rub, payload.metrics_summary)" in html
    assert "valuationScenarioChart(payload.predicted_price_rub, payload.metrics_summary)" in html
    assert "renderValuationModelQuality(payload.metrics_summary)" in html
    assert "modelDriverRows(payload.feature_importance)" in html


def test_workstation_html_keeps_real_map_tile_fallbacks() -> None:
    html = _workstation_html({})

    assert "tile.openstreetmap.org" in html
    assert "img.dataset.tileFallbackIndex" in html
    assert "img.onerror = () => img.remove();" not in html
    assert html.index("tile.openstreetmap.org") < html.index("basemaps.cartocdn")


def test_workstation_html_renders_observed_exposure_forecast_provenance() -> None:
    html = _workstation_html({})

    assert "Наблюдаемая экспозиция" in html
    assert "Источник расчета" in html
    assert "Нижняя граница по комнатности" in html
    assert "observed_history_lower_bound" in html


def test_workstation_html_renders_trend_forecast_rows() -> None:
    html = _workstation_html(
        {
            "observationTrend": {
                "can_forecast": True,
                "forecast_method": "linear_median_price_per_m2_v1",
                "forecast_horizon_days": 7,
                "history_points": 22,
                "trend_slope_per_day": -1648.29,
                "forecast_rows": [
                    {
                        "observed_date": "2026-06-25",
                        "forecast_median_price_per_m2": 468_649.79,
                    }
                ],
            }
        }
    )

    assert "trendForecastTable" in html
    assert "forecast_median_price_per_m2" in html
    assert "Прогноз медианы за м²" in html
    assert "trendForecastTable(t.forecast_rows)" in html


def test_exposure_readiness_requires_terminal_lifecycle_target() -> None:
    frame = pd.DataFrame(
        [
            {
                "source_name": "domclick",
                "source_listing_id": "a",
                "observed_at": "2026-06-20T10:00:00+03:00",
                "status": "observed",
            },
            {
                "source_name": "domclick",
                "source_listing_id": "a",
                "observed_at": "2026-06-24T10:00:00+03:00",
                "status": "observed",
            },
            {
                "source_name": "cian",
                "source_listing_id": "b",
                "observed_at": "2026-05-14T10:00:00+03:00",
                "status": "observed",
            },
        ]
    )

    readiness = _exposure_readiness_payload(
        frame,
        source={
            "sourceMeta": {
                "domclick": {
                    "collection_date_count": 24,
                    "snapshot_count": 25,
                    "available_snapshot_dir_count": 30,
                    "observation_count": 40_380,
                }
            }
        },
    )

    assert readiness["status"] == "missing"
    assert readiness["can_forecast"] is False
    assert readiness["listings_with_observation_history"] == 1
    assert readiness["lifecycle_target_rows"] == 0
    # This fixture has three distinct observed dates; production API stats are covered below.
    assert readiness["observation_date_count"] == 3
    assert readiness["collection_date_count"] == 24
    assert readiness["raw_observation_rows"] == 40_380


def test_exposure_readiness_uses_raw_history_without_fake_forecast() -> None:
    frame = pd.DataFrame(
        [
            {
                "source_name": "domclick",
                "source_listing_id": "a",
                "observed_at": "2026-06-24T10:00:00+03:00",
                "status": "observed",
            }
        ]
    )

    readiness = _exposure_readiness_payload(
        frame,
        source={
            "sourceMeta": {
                "domclick": {
                    "collection_date_count": 24,
                    "snapshot_count": 25,
                    "available_snapshot_dir_count": 30,
                    "observation_count": 40_380,
                    "stable_listing_ids": 13_324,
                    "listings_with_observation_history": 7_484,
                    "max_observation_dates_per_listing": 21,
                }
            }
        },
    )

    assert readiness["status"] == "missing"
    assert readiness["can_forecast"] is False
    assert readiness["lifecycle_target_rows"] == 0
    assert readiness["raw_stable_listing_ids"] == 13_324
    assert readiness["listings_with_observation_history"] == 7_484
    assert readiness["max_observation_dates_per_listing"] == 21


def test_exposure_readiness_uses_api_lifecycle_stats() -> None:
    frame = pd.DataFrame(
        [
            {
                "source_name": "domclick",
                "source_listing_id": "a",
                "observed_at": "2026-06-23T10:00:00+03:00",
                "status": "observed",
            }
        ]
    )

    readiness = _exposure_readiness_payload(
        frame,
        stats={
            "observations_total": 42_765,
            "observation_date_count": 21,
            "listings_with_observation_history": 7_456,
            "max_observation_dates_per_listing": 19,
            "lifecycle_target_rows": 0,
            "inactive_observations_total": 0,
            "observation_status_counts": {"observed": 42_765},
        },
    )

    assert readiness["raw_observation_rows"] == 42_765
    assert readiness["observation_date_count"] == 21
    assert readiness["listings_with_observation_history"] == 7_456
    assert readiness["max_observation_dates_per_listing"] == 19
    assert readiness["lifecycle_target_rows"] == 0
    assert readiness["can_forecast"] is False


def test_exposure_readiness_uses_observed_history_lower_bound_forecast_stats() -> None:
    readiness = _exposure_readiness_payload(
        pd.DataFrame(),
        stats={
            "observations_total": 42_765,
            "observation_date_count": 21,
            "listings_with_observation_history": 7_456,
            "max_observation_dates_per_listing": 19,
            "lifecycle_target_rows": 0,
            "observed_exposure_target_rows": 7_456,
            "observed_exposure_can_forecast": True,
            "observed_exposure_median_days": 7,
            "observed_exposure_max_days": 21,
            "observed_exposure_target_source": "observed_history_lower_bound",
            "observed_exposure_forecast_segments": [
                {
                    "rooms": 2,
                    "target_rows": 2_300,
                    "median_observed_exposure_days": 8,
                    "target_source": "observed_history_lower_bound",
                }
            ],
        },
    )

    assert readiness["status"] == "partial"
    assert readiness["can_forecast"] is False
    assert readiness["lifecycle_target_rows"] == 0
    assert readiness["observed_exposure_target_rows"] == 7_456
    assert readiness["observed_exposure_can_forecast"] is True
    assert readiness["median_exposure_days"] == 7
    assert readiness["target_source"] == "observed_history_lower_bound"
    assert readiness["observed_exposure_forecast_segments"][0]["target_rows"] == 2_300
    assert "наблюдаем" in readiness["note"].lower()


def test_exposure_readiness_prefers_exposure_forecast_endpoint_payload() -> None:
    readiness = _exposure_readiness_payload(
        pd.DataFrame(),
        stats={
            "observations_total": 42_765,
            "observation_date_count": 21,
            "lifecycle_target_rows": 0,
        },
        exposure_forecast={
            "status": "partial",
            "status_label": "есть нижняя граница экспозиции",
            "can_forecast": False,
            "target_source": "observed_history_lower_bound",
            "terminal_lifecycle_target_rows": 0,
            "observed_exposure_target_rows": 7_456,
            "observed_exposure_min_target_rows": 100,
            "observed_exposure_can_forecast": True,
            "median_observed_exposure_days": 7,
            "max_observed_exposure_days": 21,
            "forecast_segments": [
                {
                    "rooms": 2,
                    "target_rows": 2_440,
                    "median_observed_exposure_days": 6,
                    "target_source": "observed_history_lower_bound",
                }
            ],
            "caveat": "нижняя граница срока",
        },
    )

    assert readiness["status"] == "partial"
    assert readiness["can_forecast"] is False
    assert readiness["target_source"] == "observed_history_lower_bound"
    assert readiness["lifecycle_target_rows"] == 0
    assert readiness["observed_exposure_target_rows"] == 7_456
    assert readiness["observed_exposure_can_forecast"] is True
    assert readiness["median_exposure_days"] == 7
    assert readiness["observed_exposure_max_days"] == 21
    assert readiness["observed_exposure_forecast_segments"][0]["target_rows"] == 2_440
    assert readiness["note"] == "нижняя граница срока"


def test_exposure_readiness_renders_inferred_lifecycle_forecast() -> None:
    readiness = _exposure_readiness_payload(
        pd.DataFrame(),
        stats={
            "observations_total": 44_765,
            "observation_date_count": 22,
            "lifecycle_target_rows": 0,
        },
        exposure_forecast={
            "status": "ready",
            "status_label": "готово по исчезновению из наблюдений",
            "can_forecast": True,
            "target_source": "observation_gap_inferred_lifecycle",
            "terminal_lifecycle_target_rows": 0,
            "inferred_lifecycle_target_rows": 4_962,
            "inferred_lifecycle_can_forecast": True,
            "inferred_lifecycle_min_gap_days": 3,
            "inferred_lifecycle_median_days": 6,
            "inferred_lifecycle_max_days": 21,
            "forecast_segments": [
                {
                    "rooms": 2,
                    "target_rows": 1_678,
                    "median_inferred_exposure_days": 6,
                    "target_source": "observation_gap_inferred_lifecycle",
                }
            ],
            "method": "gap_inferred_lifecycle_median_v1",
            "forecast_model_version": "inferred_lifecycle_gap_median_v1",
            "caveat": "прогноз исчезновения из наблюдений",
        },
    )

    assert readiness["status"] == "ready"
    assert readiness["can_forecast"] is True
    assert readiness["target_source"] == "observation_gap_inferred_lifecycle"
    assert readiness["lifecycle_target_rows"] == 0
    assert readiness["inferred_lifecycle_target_rows"] == 4_962
    assert readiness["inferred_lifecycle_min_gap_days"] == 3
    assert readiness["median_exposure_days"] == 6
    assert readiness["max_exposure_days"] == 21
    assert readiness["observed_exposure_forecast_segments"][0]["target_rows"] == 1_678
    assert readiness["forecast_method"] == "gap_inferred_lifecycle_median_v1"
    assert readiness["note"] == "прогноз исчезновения из наблюдений"


def test_observation_trend_payload_marks_forecast_missing_without_model() -> None:
    trend = _observation_trend_payload(
        stats={
            "observations_total": 42_765,
            "observation_date_count": 21,
            "first_observed_date": "2026-05-14",
            "last_observed_date": "2026-06-23",
            "listings_with_observation_history": 7_456,
            "listing_price_change_count": 1_300,
        },
        exposure={
            "lifecycle_target_rows": 0,
            "can_forecast": False,
        },
    )

    assert trend["status"] == "partial"
    assert trend["can_forecast"] is False
    assert trend["observations_total"] == 42_765
    assert trend["observation_date_count"] == 21
    assert trend["listing_price_change_count"] == 1_300
    assert "прогноз" in trend["note"].lower()


def test_exposure_readiness_detects_real_terminal_targets() -> None:
    frame = pd.DataFrame(
        [
            {
                "source_name": "domclick",
                "source_listing_id": "a",
                "observed_at": "2026-06-20T10:00:00+03:00",
                "status": "observed",
            },
            {
                "source_name": "domclick",
                "source_listing_id": "a",
                "observed_at": "2026-06-24T10:00:00+03:00",
                "status": "removed",
            },
            {
                "source_name": "domclick",
                "source_listing_id": "b",
                "observed_at": "2026-06-21T10:00:00+03:00",
                "active": True,
            },
            {
                "source_name": "domclick",
                "source_listing_id": "b",
                "observed_at": "2026-06-23T10:00:00+03:00",
                "active": False,
            },
        ]
    )

    readiness = _exposure_readiness_payload(frame, min_target_rows=2)

    assert readiness["status"] == "ready"
    assert readiness["can_forecast"] is True
    assert readiness["lifecycle_target_rows"] == 2
    assert readiness["median_exposure_days"] == 3.0
    assert readiness["max_exposure_days"] == 4


def test_service_status_rows_do_not_claim_live_db_or_cache_in_snapshot_mode() -> None:
    rows = _service_status_rows(
        connected=False,
        mode="snapshot",
        stats={
            "listings_total": 15_765,
            "loaded_snapshot_listings": 15_765,
            "coordinate_listings": 15_765,
            "latest_collection_report": {
                "run_id": "domclick-20260623T222510-140967Z",
                "status": "success",
                "records_seen": 2_000,
                "normalized_listings": 2_000,
            },
        },
        local_model={"featureNames": ["rooms", "total_area_m2"]},
        monitoring_status={},
    )

    by_key = {row["key"]: row for row in rows}

    assert by_key["api"]["status"] == "warning"
    assert by_key["api"]["label"] == "API"
    assert "локальная витрина" in by_key["api"]["detail"]
    assert by_key["vitrine"]["status"] == "ok"
    assert by_key["vitrine"]["count"] == 15_765
    assert by_key["database"]["status"] == "unknown"
    assert by_key["cache"]["status"] == "unknown"
    assert "не проверено" in by_key["database"]["status_label"].lower()
    assert "не проверено" in by_key["cache"]["status_label"].lower()
    assert by_key["model"]["status"] == "ok"
    assert by_key["ingestion"]["status"] == "ok"
