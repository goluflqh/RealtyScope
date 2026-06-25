from __future__ import annotations

import json
from pathlib import Path

from realtyscope.analysis.district_boundaries import (
    load_district_boundary_index,
    normalize_district_name,
)


def _write_boundary_geojson(path: Path) -> Path:
    payload = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"name": "район Раменки", "name_lat": "rajon Ramenki"},
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
                "properties": {"name": "Можайский район", "name_lat": "Mozhajskij rajon"},
                "geometry": {
                    "type": "MultiPolygon",
                    "coordinates": [
                        [
                            [
                                [37.20, 55.60],
                                [37.40, 55.60],
                                [37.40, 55.80],
                                [37.20, 55.80],
                                [37.20, 55.60],
                            ]
                        ]
                    ],
                },
            },
        ],
        "metadata": {
            "dataTitle": "Fixture/OpenStreetMap",
            "dataUrl": "https://example.test/boundaries",
        },
    }
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return path


def test_normalize_district_name_removes_raion_prefix_and_suffix() -> None:
    assert normalize_district_name("район Раменки") == "Раменки"
    assert normalize_district_name("Можайский район") == "Можайский"
    assert normalize_district_name("Басманный район") == "Басманный"


def test_boundary_index_assigns_clean_district_names_from_geojson(tmp_path: Path) -> None:
    index = load_district_boundary_index(_write_boundary_geojson(tmp_path / "districts.geojson"))

    ramenki = index.lookup(longitude=37.61, latitude=55.75)
    mozhaysky = index.lookup(longitude=37.30, latitude=55.70)

    assert index.feature_count == 2
    assert index.source_title == "Fixture/OpenStreetMap"
    assert ramenki is not None
    assert ramenki.district_name == "Раменки"
    assert ramenki.raw_name == "район Раменки"
    assert mozhaysky is not None
    assert mozhaysky.district_name == "Можайский"
    assert index.lookup(longitude=38.20, latitude=55.70) is None


def test_boundary_index_reads_utf8_bom_metadata_file(tmp_path: Path) -> None:
    geojson_path = _write_boundary_geojson(tmp_path / "districts.geojson")
    payload = json.loads(geojson_path.read_text(encoding="utf-8"))
    payload.pop("metadata", None)
    geojson_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    geojson_path.with_suffix(".metadata.json").write_text(
        '\ufeff{"dataTitle": "GIS-Lab/OpenStreetMap", "dataUrl": "https://example.test/osm"}',
        encoding="utf-8",
    )

    index = load_district_boundary_index(geojson_path)

    assert index.source_title == "GIS-Lab/OpenStreetMap"
    assert index.source_url == "https://example.test/osm"
