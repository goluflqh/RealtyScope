from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class DistrictBoundaryMatch:
    district_name: str
    raw_name: str
    source_title: str | None = None
    source_url: str | None = None


@dataclass(frozen=True)
class DistrictBoundary:
    district_name: str
    raw_name: str
    polygons: tuple[tuple[tuple[tuple[float, float], ...], ...], ...]
    bbox: tuple[float, float, float, float]

    def contains(self, *, longitude: float, latitude: float) -> bool:
        min_lon, min_lat, max_lon, max_lat = self.bbox
        if longitude < min_lon or longitude > max_lon or latitude < min_lat or latitude > max_lat:
            return False
        return any(_polygon_contains(longitude, latitude, polygon) for polygon in self.polygons)


@dataclass(frozen=True)
class DistrictBoundaryIndex:
    boundaries: tuple[DistrictBoundary, ...]
    source_title: str | None = None
    source_url: str | None = None

    @property
    def feature_count(self) -> int:
        return len(self.boundaries)

    def lookup(self, *, longitude: Any, latitude: Any) -> DistrictBoundaryMatch | None:
        try:
            lon = float(longitude)
            lat = float(latitude)
        except (TypeError, ValueError):
            return None
        for boundary in self.boundaries:
            if boundary.contains(longitude=lon, latitude=lat):
                return DistrictBoundaryMatch(
                    district_name=boundary.district_name,
                    raw_name=boundary.raw_name,
                    source_title=self.source_title,
                    source_url=self.source_url,
                )
        return None


def normalize_district_name(name: Any) -> str:
    value = re.sub(r"\s+", " ", str(name or "")).strip(" .«»\"'")
    value = re.sub(r"^район\s+", "", value, flags=re.IGNORECASE).strip()
    value = re.sub(r"\s+район$", "", value, flags=re.IGNORECASE).strip()
    return value


def load_district_boundary_index(path: str | Path) -> DistrictBoundaryIndex:
    geojson_path = Path(path)
    with geojson_path.open("r", encoding="utf-8-sig") as fh:
        payload = json.load(fh)
    metadata = _load_metadata(geojson_path, payload)
    boundaries = []
    for feature in payload.get("features") or []:
        boundary = _boundary_from_feature(feature)
        if boundary is not None:
            boundaries.append(boundary)
    return DistrictBoundaryIndex(
        boundaries=tuple(boundaries),
        source_title=metadata.get("dataTitle") or metadata.get("source_title"),
        source_url=metadata.get("dataUrl") or metadata.get("source_url"),
    )


def _load_metadata(geojson_path: Path, payload: dict[str, Any]) -> dict[str, Any]:
    metadata = payload.get("metadata")
    if isinstance(metadata, dict):
        return metadata
    sibling = geojson_path.with_suffix(".metadata.json")
    if not sibling.exists():
        return {}
    with sibling.open("r", encoding="utf-8-sig") as fh:
        loaded = json.load(fh)
    return loaded if isinstance(loaded, dict) else {}


def _boundary_from_feature(feature: dict[str, Any]) -> DistrictBoundary | None:
    properties = feature.get("properties") or {}
    raw_name = str(properties.get("name") or "").strip()
    district_name = normalize_district_name(raw_name)
    if not district_name:
        return None
    geometry = feature.get("geometry") or {}
    polygons = _geometry_polygons(geometry)
    if not polygons:
        return None
    points = [point for polygon in polygons for ring in polygon for point in ring]
    lons = [point[0] for point in points]
    lats = [point[1] for point in points]
    return DistrictBoundary(
        district_name=district_name,
        raw_name=raw_name,
        polygons=polygons,
        bbox=(min(lons), min(lats), max(lons), max(lats)),
    )


def _geometry_polygons(
    geometry: dict[str, Any],
) -> tuple[tuple[tuple[tuple[float, float], ...], ...], ...]:
    geometry_type = geometry.get("type")
    coordinates = geometry.get("coordinates")
    if geometry_type == "Polygon":
        parsed = _parse_polygon(coordinates)
        return (parsed,) if parsed else ()
    if geometry_type == "MultiPolygon":
        polygons = [_parse_polygon(polygon) for polygon in coordinates or []]
        return tuple(polygon for polygon in polygons if polygon)
    return ()


def _parse_polygon(raw_polygon: Any) -> tuple[tuple[tuple[float, float], ...], ...]:
    rings = []
    for raw_ring in raw_polygon or []:
        ring = []
        for point in raw_ring or []:
            try:
                lon = float(point[0])
                lat = float(point[1])
            except (TypeError, ValueError, IndexError):
                continue
            ring.append((lon, lat))
        if len(ring) >= 4:
            rings.append(tuple(ring))
    return tuple(rings)


def _polygon_contains(
    longitude: float,
    latitude: float,
    polygon: tuple[tuple[tuple[float, float], ...], ...],
) -> bool:
    if not polygon or not _ring_contains(longitude, latitude, polygon[0]):
        return False
    return not any(_ring_contains(longitude, latitude, hole) for hole in polygon[1:])


def _ring_contains(
    longitude: float,
    latitude: float,
    ring: tuple[tuple[float, float], ...],
) -> bool:
    inside = False
    previous = len(ring) - 1
    for current, (lon_i, lat_i) in enumerate(ring):
        lon_j, lat_j = ring[previous]
        if (lat_i > latitude) != (lat_j > latitude):
            crossing_lon = (lon_j - lon_i) * (latitude - lat_i) / ((lat_j - lat_i) or 1e-12) + lon_i
            if longitude < crossing_lon:
                inside = not inside
        previous = current
    return inside
