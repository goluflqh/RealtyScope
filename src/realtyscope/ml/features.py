from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from contextlib import suppress
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.orm import Session

from realtyscope.database.models import Listing, ListingObservation, OsmFeature
from realtyscope.database.session import create_database_engine

FEATURE_VERSION = "ml_features_v1"
NON_LEAKY_FEATURE_VERSION = "ml_features_v2_non_leaky"
FEATURE_VERSIONS = (FEATURE_VERSION, NON_LEAKY_FEATURE_VERSION)
OSM_FEATURE_VERSION = "osm_local_v1"


class FeatureRow(BaseModel):
    model_config = ConfigDict(frozen=True)

    listing_id: int
    feature_version: str
    target_price_rub: int
    features: dict[str, float]


def build_feature_rows(
    session: Session,
    *,
    limit: int | None = None,
    feature_version: str = FEATURE_VERSION,
) -> list[FeatureRow]:
    _validate_feature_version(feature_version)
    listings_query = (
        select(Listing)
        .where(Listing.is_ml_ready.is_(True), Listing.price_rub > 0, Listing.total_area_m2 > 0)
        .order_by(Listing.id)
    )
    if limit is not None:
        listings_query = listings_query.limit(limit)
    listings = session.scalars(listings_query).all()
    listing_ids = [listing.id for listing in listings]
    latest_observations, observation_counts = _latest_observations(session, listing_ids)
    osm_features = _osm_features(session, listing_ids)

    return [
        FeatureRow(
            listing_id=listing.id,
            feature_version=feature_version,
            target_price_rub=listing.price_rub,
            features=_features_for_listing(
                listing=listing,
                latest_observation=latest_observations.get(listing.id),
                observation_count=observation_counts.get(listing.id, 0),
                osm_feature=osm_features.get(listing.id),
                feature_version=feature_version,
            ),
        )
        for listing in listings
    ]


def build_feature_summary(
    database_url: str | None = None,
    *,
    limit: int | None = None,
    feature_version: str = FEATURE_VERSION,
) -> dict[str, Any]:
    engine = create_database_engine(database_url)
    with Session(engine) as session:
        rows = build_feature_rows(session, limit=limit, feature_version=feature_version)

    targets = [row.target_price_rub for row in rows]
    feature_count = len(rows[0].features) if rows else 0
    osm_rows_present = sum(1 for row in rows if row.features["osm_missing"] == 0.0)
    return {
        "feature_version": feature_version,
        "rows_total": len(rows),
        "feature_count": feature_count,
        "osm_rows_present": osm_rows_present,
        "target_price_rub": _target_summary(targets),
    }


def main(argv: Sequence[str] | None = None) -> int:
    with suppress(AttributeError):
        sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description="Build RealtyScope ML feature row summary.")
    parser.add_argument("--database-url", default=None, help="Override database URL.")
    parser.add_argument("--limit", type=int, default=None, help="Optional row limit.")
    parser.add_argument(
        "--feature-version",
        choices=FEATURE_VERSIONS,
        default=FEATURE_VERSION,
        help="Feature snapshot version to build.",
    )
    parser.add_argument("--json", action="store_true", help="Print JSON output.")
    args = parser.parse_args(argv)

    if args.limit is not None and args.limit < 1:
        parser.error("--limit must be at least 1")

    summary = build_feature_summary(
        args.database_url,
        limit=args.limit,
        feature_version=args.feature_version,
    )
    if args.json:
        print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    else:
        print(
            f"Built {summary['rows_total']} feature rows "
            f"with {summary['feature_count']} features each."
        )
    return 0


def _features_for_listing(
    *,
    listing: Listing,
    latest_observation: ListingObservation | None,
    observation_count: int,
    osm_feature: OsmFeature | None,
    feature_version: str,
) -> dict[str, float]:
    _validate_feature_version(feature_version)
    floor = _optional_float(listing.floor)
    floors_total = _optional_float(listing.floors_total)
    building_year = _optional_float(listing.building_year)
    latitude = _optional_float(listing.latitude)
    longitude = _optional_float(listing.longitude)
    features = {
        "total_area_m2": _required_float(listing.total_area_m2),
        "rooms": float(listing.rooms),
        "floor": floor or 0.0,
        "floor_missing": _missing_flag(floor),
        "floors_total": floors_total or 0.0,
        "floors_total_missing": _missing_flag(floors_total),
        "building_year": building_year or 0.0,
        "building_year_missing": _missing_flag(building_year),
        "latitude": latitude or 0.0,
        "longitude": longitude or 0.0,
        "coordinates_missing": 0.0 if listing.has_coordinates and latitude and longitude else 1.0,
        "property_type_apartment": 1.0 if listing.property_type == "apartment" else 0.0,
        "observation_count": float(observation_count),
        "observation_missing": 0.0 if latest_observation is not None else 1.0,
    }
    if feature_version == FEATURE_VERSION:
        features.update(
            {
                "latest_observation_price_rub": _observation_value(latest_observation, "price_rub"),
                "latest_observation_price_per_m2": _observation_value(
                    latest_observation,
                    "price_per_m2",
                ),
            }
        )
    features.update(_osm_feature_values(osm_feature))
    return features


def _validate_feature_version(feature_version: str) -> None:
    if feature_version not in FEATURE_VERSIONS:
        supported = ", ".join(FEATURE_VERSIONS)
        raise ValueError(
            f"unsupported feature version {feature_version!r}; expected one of {supported}"
        )


def _latest_observations(
    session: Session, listing_ids: Sequence[int]
) -> tuple[dict[int, ListingObservation], dict[int, int]]:
    if not listing_ids:
        return {}, {}
    observations = session.scalars(
        select(ListingObservation)
        .where(ListingObservation.listing_id.in_(listing_ids))
        .order_by(
            ListingObservation.listing_id, ListingObservation.observed_at, ListingObservation.id
        )
    ).all()
    latest: dict[int, ListingObservation] = {}
    counts: dict[int, int] = {}
    for observation in observations:
        counts[observation.listing_id] = counts.get(observation.listing_id, 0) + 1
        latest[observation.listing_id] = observation
    return latest, counts


def _osm_features(session: Session, listing_ids: Sequence[int]) -> dict[int, OsmFeature]:
    if not listing_ids:
        return {}
    rows = session.scalars(
        select(OsmFeature)
        .where(
            OsmFeature.listing_id.in_(listing_ids),
            OsmFeature.feature_version == OSM_FEATURE_VERSION,
        )
        .order_by(OsmFeature.listing_id, OsmFeature.id)
    ).all()
    return {row.listing_id: row for row in rows}


def _osm_feature_values(osm_feature: OsmFeature | None) -> dict[str, float]:
    if osm_feature is None:
        return {
            "osm_missing": 1.0,
            "transport_count_500m": 0.0,
            "transport_count_1000m": 0.0,
            "nearest_transport_m": 0.0,
            "nearest_transport_m_missing": 1.0,
            "schools_count_1000m": 0.0,
            "parks_count_1000m": 0.0,
            "shops_count_1000m": 0.0,
            "healthcare_count_1000m": 0.0,
        }
    nearest_transport = _optional_float(osm_feature.nearest_transport_m)
    return {
        "osm_missing": 0.0,
        "transport_count_500m": float(osm_feature.transport_count_500m),
        "transport_count_1000m": float(osm_feature.transport_count_1000m),
        "nearest_transport_m": nearest_transport or 0.0,
        "nearest_transport_m_missing": _missing_flag(nearest_transport),
        "schools_count_1000m": float(osm_feature.schools_count_1000m),
        "parks_count_1000m": float(osm_feature.parks_count_1000m),
        "shops_count_1000m": float(osm_feature.shops_count_1000m),
        "healthcare_count_1000m": float(osm_feature.healthcare_count_1000m),
    }


def _observation_value(observation: ListingObservation | None, field_name: str) -> float:
    if observation is None:
        return 0.0
    return _required_float(getattr(observation, field_name))


def _required_float(value: Any) -> float:
    converted = _optional_float(value)
    if converted is None:
        return 0.0
    return converted


def _optional_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return float(value)
    return float(value)


def _missing_flag(value: Any) -> float:
    return 1.0 if value is None else 0.0


def _target_summary(targets: Sequence[int]) -> dict[str, float | int | None]:
    if not targets:
        return {"min": None, "max": None, "mean": None}
    return {
        "min": min(targets),
        "max": max(targets),
        "mean": sum(targets) / len(targets),
    }


if __name__ == "__main__":
    raise SystemExit(main())
