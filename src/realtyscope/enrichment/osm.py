from __future__ import annotations

import argparse
import json
import math
import sys
from collections.abc import Mapping, Sequence
from contextlib import suppress
from dataclasses import asdict, dataclass
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from realtyscope.database.models import Listing
from realtyscope.database.session import create_database_engine

OSM_FEATURE_VERSION = "osm_local_v1"
OSM_ATTRIBUTION = "OpenStreetMap contributors"
EARTH_RADIUS_M = 6_371_000.0


@dataclass(frozen=True)
class OsmFeatureSummary:
    latitude: float
    longitude: float
    transport_count_500m: int
    transport_count_1000m: int
    nearest_transport_m: float | None
    schools_count_1000m: int
    parks_count_1000m: int
    shops_count_1000m: int
    healthcare_count_1000m: int
    osm_feature_version: str
    source_summary: dict[str, Any]

    def as_record(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["feature_version"] = payload.pop("osm_feature_version")
        return payload


def compute_osm_features(
    listing: Mapping[str, Any],
    elements: Sequence[Mapping[str, Any]],
    *,
    radii_m: Sequence[int] = (500, 1000),
) -> OsmFeatureSummary:
    latitude, longitude = _listing_coordinates(listing)
    max_radius_m = max(radii_m) if radii_m else 1000

    transport_distances: list[float] = []
    transport_count_500m = 0
    transport_count_1000m = 0
    schools_count_1000m = 0
    parks_count_1000m = 0
    shops_count_1000m = 0
    healthcare_count_1000m = 0
    elements_with_coordinates = 0
    elements_used = 0

    for element in elements:
        coordinates = _element_coordinates(element)
        if coordinates is None:
            continue
        elements_with_coordinates += 1
        distance_m = _haversine_m(latitude, longitude, coordinates[0], coordinates[1])
        tags = _tags(element)
        categories = _categories(tags)
        if not categories or distance_m > max_radius_m:
            continue

        elements_used += 1
        if "transport" in categories:
            transport_distances.append(distance_m)
            if distance_m <= 500:
                transport_count_500m += 1
            if distance_m <= 1000:
                transport_count_1000m += 1
        if distance_m <= 1000:
            if "school" in categories:
                schools_count_1000m += 1
            if "park" in categories:
                parks_count_1000m += 1
            if "shop" in categories:
                shops_count_1000m += 1
            if "healthcare" in categories:
                healthcare_count_1000m += 1

    nearest_transport_m = min(transport_distances) if transport_distances else None
    return OsmFeatureSummary(
        latitude=latitude,
        longitude=longitude,
        transport_count_500m=transport_count_500m,
        transport_count_1000m=transport_count_1000m,
        nearest_transport_m=round(nearest_transport_m, 2)
        if nearest_transport_m is not None
        else None,
        schools_count_1000m=schools_count_1000m,
        parks_count_1000m=parks_count_1000m,
        shops_count_1000m=shops_count_1000m,
        healthcare_count_1000m=healthcare_count_1000m,
        osm_feature_version=OSM_FEATURE_VERSION,
        source_summary={
            "elements_seen": len(elements),
            "elements_with_coordinates": elements_with_coordinates,
            "elements_used": elements_used,
            "max_radius_m": max_radius_m,
            "live_osm_called": False,
        },
    )


def main(argv: Sequence[str] | None = None) -> int:
    with suppress(AttributeError):
        sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(
        description="Compute or inspect RealtyScope OpenStreetMap enrichment readiness."
    )
    parser.add_argument("--database-url", default=None, help="Override database URL.")
    parser.add_argument("--limit", type=int, default=50, help="Maximum listings to inspect.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Inspect rows without live OSM calls.",
    )
    parser.add_argument("--json", action="store_true", help="Print JSON output.")
    args = parser.parse_args(argv)

    if args.limit < 1:
        parser.error("--limit must be at least 1")

    if not args.dry_run:
        print(
            "Live OSM/Overpass enrichment is not implemented in Phase 4.2; "
            "use --dry-run or fixture/local extracts.",
            file=sys.stderr,
        )
        return 2

    payload = _build_dry_run_payload(args.database_url, args.limit)
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    else:
        print(
            "OSM dry run: "
            f"{payload['rows_selected']} of {payload['rows_available']} "
            "coordinate-ready listings selected."
        )
    return 0


def _build_dry_run_payload(database_url: str | None, limit: int) -> dict[str, Any]:
    engine = create_database_engine(database_url)
    with Session(engine) as session:
        coordinate_filter = (
            Listing.has_coordinates.is_(True),
            Listing.latitude.is_not(None),
            Listing.longitude.is_not(None),
        )
        rows_available = (
            session.scalar(select(func.count()).select_from(Listing).where(*coordinate_filter)) or 0
        )
        listings = session.scalars(
            select(Listing).where(*coordinate_filter).order_by(Listing.id).limit(limit)
        ).all()

    return {
        "attribution": OSM_ATTRIBUTION,
        "dry_run": True,
        "feature_version": OSM_FEATURE_VERSION,
        "live_osm_called": False,
        "rows_available": rows_available,
        "rows_selected": len(listings),
        "selected_listing_ids": [listing.id for listing in listings],
    }


def _listing_coordinates(listing: Mapping[str, Any]) -> tuple[float, float]:
    latitude = listing.get("latitude")
    longitude = listing.get("longitude")
    if latitude is None or longitude is None:
        raise ValueError("listing must include latitude and longitude")
    return float(latitude), float(longitude)


def _element_coordinates(element: Mapping[str, Any]) -> tuple[float, float] | None:
    if element.get("lat") is not None and element.get("lon") is not None:
        return float(element["lat"]), float(element["lon"])
    center = element.get("center")
    if (
        isinstance(center, Mapping)
        and center.get("lat") is not None
        and center.get("lon") is not None
    ):
        return float(center["lat"]), float(center["lon"])
    geometry = element.get("geometry")
    if isinstance(geometry, Sequence) and not isinstance(geometry, str):
        points = [
            (float(point["lat"]), float(point["lon"]))
            for point in geometry
            if isinstance(point, Mapping)
            and point.get("lat") is not None
            and point.get("lon") is not None
        ]
        if points:
            return sum(point[0] for point in points) / len(points), sum(
                point[1] for point in points
            ) / len(points)
    return None


def _tags(element: Mapping[str, Any]) -> Mapping[str, Any]:
    tags = element.get("tags")
    return tags if isinstance(tags, Mapping) else {}


def _categories(tags: Mapping[str, Any]) -> set[str]:
    categories: set[str] = set()
    amenity = str(tags.get("amenity", ""))
    railway = str(tags.get("railway", ""))
    highway = str(tags.get("highway", ""))
    leisure = str(tags.get("leisure", ""))
    landuse = str(tags.get("landuse", ""))

    if tags.get("public_transport") or railway in {"station", "halt", "tram_stop"}:
        categories.add("transport")
    if railway in {"subway_entrance", "station"} or amenity == "bus_station":
        categories.add("transport")
    if highway == "bus_stop":
        categories.add("transport")
    if amenity in {"school", "kindergarten", "college", "university"}:
        categories.add("school")
    if leisure in {"park", "garden", "nature_reserve"}:
        categories.add("park")
    if landuse in {"forest", "grass", "recreation_ground"}:
        categories.add("park")
    if tags.get("shop"):
        categories.add("shop")
    if tags.get("healthcare") or amenity in {"clinic", "hospital", "doctors", "pharmacy"}:
        categories.add("healthcare")
    return categories


def _haversine_m(lat_a: float, lon_a: float, lat_b: float, lon_b: float) -> float:
    phi_a = math.radians(lat_a)
    phi_b = math.radians(lat_b)
    delta_phi = math.radians(lat_b - lat_a)
    delta_lambda = math.radians(lon_b - lon_a)
    haversine = (
        math.sin(delta_phi / 2) ** 2
        + math.cos(phi_a) * math.cos(phi_b) * math.sin(delta_lambda / 2) ** 2
    )
    return EARTH_RADIUS_M * 2 * math.atan2(math.sqrt(haversine), math.sqrt(1 - haversine))


if __name__ == "__main__":
    raise SystemExit(main())
