from __future__ import annotations

import argparse
import json
import math
import sys
import time
import urllib.parse
import urllib.request
from collections.abc import Callable, Mapping, Sequence
from contextlib import suppress
from dataclasses import asdict, dataclass
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from realtyscope.database.models import Listing, OsmFeature
from realtyscope.database.session import create_database_engine

OSM_FEATURE_VERSION = "osm_local_v1"
OSM_ATTRIBUTION = "OpenStreetMap contributors"
OVERPASS_API_URL = "https://overpass-api.de/api/interpreter"
EARTH_RADIUS_M = 6_371_000.0

CallableFetchElements = Callable[[Listing], Sequence[Mapping[str, Any]]]
CallableSleep = Callable[[float], None]


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


@dataclass(frozen=True)
class OsmPersistenceResult:
    dry_run: bool
    feature_version: str
    attribution: str
    live_osm_called: bool
    rows_available: int
    rows_selected: int
    rows_inserted: int
    rows_updated: int
    rows_failed: int
    selected_listing_ids: tuple[int, ...]
    errors: tuple[dict[str, str | int], ...]

    def as_payload(self) -> dict[str, Any]:
        return asdict(self)


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


def persist_osm_features(
    session: Session,
    *,
    elements_by_listing_id: Mapping[int, Sequence[Mapping[str, Any]]] | None = None,
    fetch_elements: CallableFetchElements | None = None,
    limit: int = 50,
    feature_version: str = OSM_FEATURE_VERSION,
    delay_seconds: float = 0.0,
    sleep: CallableSleep = time.sleep,
) -> OsmPersistenceResult:
    if limit < 1:
        raise ValueError("limit must be at least 1")
    if elements_by_listing_id is not None and fetch_elements is not None:
        raise ValueError("Use either elements_by_listing_id or fetch_elements, not both")

    rows_available, listings = _coordinate_ready_listings(session, limit)
    live_osm_called = fetch_elements is not None
    rows_inserted = 0
    rows_updated = 0
    errors: list[dict[str, str | int]] = []

    for index, listing in enumerate(listings):
        if fetch_elements is not None:
            try:
                elements = fetch_elements(listing)
            except Exception as exc:  # noqa: BLE001 - external OSM failures are reported per row.
                errors.append(
                    {
                        "listing_id": listing.id,
                        "error": f"{type(exc).__name__}: {exc}",
                    }
                )
                continue
            if delay_seconds > 0 and index < len(listings) - 1:
                sleep(delay_seconds)
        else:
            elements = (elements_by_listing_id or {}).get(listing.id, ())
        record = compute_osm_features(_listing_record(listing), elements).as_record()
        record["feature_version"] = feature_version
        record["source_summary"] = {
            **record["source_summary"],
            "attribution": OSM_ATTRIBUTION,
            "live_osm_called": live_osm_called,
        }
        existing = session.scalar(
            select(OsmFeature).where(
                OsmFeature.listing_id == listing.id,
                OsmFeature.feature_version == feature_version,
            )
        )
        if existing is None:
            session.add(OsmFeature(listing_id=listing.id, **record))
            rows_inserted += 1
        else:
            _copy_osm_record(existing, record)
            rows_updated += 1

    session.flush()
    return OsmPersistenceResult(
        dry_run=False,
        feature_version=feature_version,
        attribution=OSM_ATTRIBUTION,
        live_osm_called=live_osm_called,
        rows_available=rows_available,
        rows_selected=len(listings),
        rows_inserted=rows_inserted,
        rows_updated=rows_updated,
        rows_failed=len(errors),
        selected_listing_ids=tuple(listing.id for listing in listings),
        errors=tuple(errors),
    )


def build_overpass_query(latitude: float, longitude: float, *, radius_m: int = 1000) -> str:
    return f"""
[out:json][timeout:25];
(
  node(around:{radius_m},{latitude:.7f},{longitude:.7f})["public_transport"];
  node(around:{radius_m},{latitude:.7f},{longitude:.7f})["railway"~"station|halt|tram_stop|subway_entrance"];
  node(around:{radius_m},{latitude:.7f},{longitude:.7f})["highway"="bus_stop"];
  node(around:{radius_m},{latitude:.7f},{longitude:.7f})["amenity"~"school|kindergarten|college|university|bus_station|clinic|hospital|doctors|pharmacy"];
  node(around:{radius_m},{latitude:.7f},{longitude:.7f})["leisure"~"park|garden|nature_reserve"];
  way(around:{radius_m},{latitude:.7f},{longitude:.7f})["leisure"~"park|garden|nature_reserve"];
  way(around:{radius_m},{latitude:.7f},{longitude:.7f})["landuse"~"forest|grass|recreation_ground"];
  node(around:{radius_m},{latitude:.7f},{longitude:.7f})["shop"];
  node(around:{radius_m},{latitude:.7f},{longitude:.7f})["healthcare"];
);
out center;
""".strip()


def fetch_overpass_elements(
    latitude: float,
    longitude: float,
    *,
    radius_m: int = 1000,
    overpass_url: str = OVERPASS_API_URL,
    timeout_seconds: float = 30.0,
) -> list[Mapping[str, Any]]:
    query = build_overpass_query(latitude, longitude, radius_m=radius_m)
    body = urllib.parse.urlencode({"data": query}).encode("utf-8")
    request = urllib.request.Request(
        overpass_url,
        data=body,
        headers={"User-Agent": "RealtyScope semester project OSM enrichment"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
        payload = json.loads(response.read().decode("utf-8"))
    elements = payload.get("elements", []) if isinstance(payload, Mapping) else []
    return [element for element in elements if isinstance(element, Mapping)]


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
    parser.add_argument(
        "--write",
        action="store_true",
        help="Persist OSM feature rows from --elements-file or --live-overpass.",
    )
    parser.add_argument(
        "--elements-file",
        type=argparse.FileType("r", encoding="utf-8"),
        help="JSON mapping of listing IDs to Overpass-like elements; does not call live OSM.",
    )
    parser.add_argument(
        "--live-overpass",
        action="store_true",
        help="Fetch bounded OSM elements from Overpass for selected coordinate-ready listings.",
    )
    parser.add_argument("--radius-m", type=int, default=1000, help="Overpass radius in meters.")
    parser.add_argument(
        "--delay-seconds",
        type=float,
        default=1.0,
        help="Delay between live Overpass requests.",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=30.0,
        help="Live Overpass request timeout.",
    )
    parser.add_argument("--overpass-url", default=OVERPASS_API_URL, help="Overpass API URL.")
    parser.add_argument("--json", action="store_true", help="Print JSON output.")
    args = parser.parse_args(argv)

    if args.limit < 1:
        parser.error("--limit must be at least 1")
    if args.radius_m < 1:
        parser.error("--radius-m must be at least 1")
    if args.delay_seconds < 0:
        parser.error("--delay-seconds must be zero or greater")
    if args.timeout_seconds <= 0:
        parser.error("--timeout-seconds must be greater than zero")
    if args.elements_file is not None and args.live_overpass:
        parser.error("Use either --elements-file or --live-overpass, not both")

    if not args.dry_run:
        if not args.write:
            print(
                "Use --dry-run to inspect rows or --write with --elements-file/--live-overpass "
                "to persist OSM features.",
                file=sys.stderr,
            )
            return 2
        if args.elements_file is None and not args.live_overpass:
            print(
                "Provide --elements-file or --live-overpass when using --write.",
                file=sys.stderr,
            )
            return 2

        engine = create_database_engine(args.database_url)
        with Session(engine) as session:
            if args.elements_file is not None:
                result = persist_osm_features(
                    session,
                    elements_by_listing_id=_load_elements_by_listing_id(args.elements_file),
                    limit=args.limit,
                )
            else:
                result = persist_osm_features(
                    session,
                    fetch_elements=lambda listing: fetch_overpass_elements(
                        float(listing.latitude),
                        float(listing.longitude),
                        radius_m=args.radius_m,
                        overpass_url=args.overpass_url,
                        timeout_seconds=args.timeout_seconds,
                    ),
                    limit=args.limit,
                    delay_seconds=args.delay_seconds,
                )
            session.commit()

        payload = result.as_payload()
        if args.json:
            print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
        else:
            print(
                "OSM write: "
                f"inserted={result.rows_inserted} updated={result.rows_updated} "
                f"failed={result.rows_failed} "
                f"selected={result.rows_selected} live_osm_called={result.live_osm_called}."
            )
        return 1 if result.rows_failed and not (result.rows_inserted or result.rows_updated) else 0

    if args.write:
        print(
            "--dry-run inspects readiness only; omit --dry-run when using --write.",
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
        rows_available, listings = _coordinate_ready_listings(session, limit)

    return {
        "attribution": OSM_ATTRIBUTION,
        "dry_run": True,
        "feature_version": OSM_FEATURE_VERSION,
        "live_osm_called": False,
        "rows_available": rows_available,
        "rows_selected": len(listings),
        "selected_listing_ids": [listing.id for listing in listings],
    }


def _coordinate_ready_listings(session: Session, limit: int) -> tuple[int, list[Listing]]:
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
    return int(rows_available), listings


def _listing_record(listing: Listing) -> dict[str, float | None]:
    return {"latitude": listing.latitude, "longitude": listing.longitude}


def _copy_osm_record(feature: OsmFeature, record: Mapping[str, Any]) -> None:
    feature.latitude = record["latitude"]
    feature.longitude = record["longitude"]
    feature.transport_count_500m = record["transport_count_500m"]
    feature.transport_count_1000m = record["transport_count_1000m"]
    feature.nearest_transport_m = record["nearest_transport_m"]
    feature.schools_count_1000m = record["schools_count_1000m"]
    feature.parks_count_1000m = record["parks_count_1000m"]
    feature.shops_count_1000m = record["shops_count_1000m"]
    feature.healthcare_count_1000m = record["healthcare_count_1000m"]
    feature.source_summary = record["source_summary"]


def _load_elements_by_listing_id(file_obj: Any) -> dict[int, list[Mapping[str, Any]]]:
    payload = json.load(file_obj)
    if not isinstance(payload, Mapping):
        raise ValueError("OSM elements file must contain an object keyed by listing ID")

    elements_by_listing_id: dict[int, list[Mapping[str, Any]]] = {}
    for key, value in payload.items():
        if not isinstance(value, Sequence) or isinstance(value, str):
            raise ValueError("Each OSM elements mapping value must be a list")
        elements_by_listing_id[int(key)] = [
            element for element in value if isinstance(element, Mapping)
        ]
    return elements_by_listing_id


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
