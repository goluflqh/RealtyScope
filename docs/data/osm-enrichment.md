# RealtyScope OpenStreetMap Enrichment

Date: 2026-06-02
Phase: 4.2 OSM infrastructure enrichment foundation

## Scope

Phase 4.2 adds the first OpenStreetMap-derived feature contract without calling public OSM services in tests. The implementation is intentionally local and fixture-friendly:

- `realtyscope.enrichment.osm.compute_osm_features` accepts a listing coordinate and Overpass-like elements supplied by the caller.
- Tests use tiny local fixtures only.
- The `osm_features` table stores deterministic feature snapshots per listing and feature version.
- The CLI supports a dry run that inspects coordinate-ready listings without calling live OSM or writing enrichment rows.

OpenStreetMap is an enrichment source, not the primary listing source. Domclick remains the listing source of record.

## Feature Contract

Current feature version: `osm_local_v1`.

The conservative first feature set is:

| Field | Meaning |
| --- | --- |
| `transport_count_500m` | Transport nodes/stations/stops within 500 m. |
| `transport_count_1000m` | Transport nodes/stations/stops within 1000 m. |
| `nearest_transport_m` | Distance to nearest transport feature within the configured radius. |
| `schools_count_1000m` | School, kindergarten, college, or university amenities within 1000 m. |
| `parks_count_1000m` | Park, garden, nature reserve, forest/grass/recreation landuse within 1000 m. |
| `shops_count_1000m` | Any tagged shop within 1000 m. |
| `healthcare_count_1000m` | Healthcare, clinic, hospital, doctors, pharmacy amenities within 1000 m. |
| `source_summary` | Small JSON summary of fixture/local source coverage. |

## Persistence

The `osm_features` table stores one row per `(listing_id, feature_version)`. This keeps feature snapshots reproducible for Phase 4.3 ML feature rows and lets a later feature version be added without overwriting earlier experiments.

## Dry Run

Use dry run to verify how many coordinate-ready listings are available:

```powershell
.\.venv\Scripts\python.exe -m realtyscope.enrichment.osm --database-url $env:DATABASE_URL --limit 50 --dry-run --json
```

The dry run reports selected listing IDs, feature version, and `live_osm_called=false`. It does not call Overpass, public OSM APIs, or Nominatim.

## Live OSM Caveat

Live Overpass fetching is intentionally not implemented in this subphase. The next safe step would be a bounded fetcher that uses existing listing coordinates, cache/local extracts where possible, strict request limits, and rate limiting. Public Nominatim must not be used for bulk geocoding.

## Attribution

If RealtyScope shows maps, OpenStreetMap-derived features, or OSM-derived explanations in UI/docs, include visible attribution to OpenStreetMap contributors.
