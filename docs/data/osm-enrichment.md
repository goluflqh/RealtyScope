# RealtyScope OpenStreetMap Enrichment

Date: 2026-06-02
Phase: 4.2 OSM infrastructure enrichment foundation

## Scope

Phase 4.2 adds the first OpenStreetMap-derived feature contract without calling public OSM services in tests. The implementation is intentionally local and fixture-friendly:

- `realtyscope.enrichment.osm.compute_osm_features` accepts a listing coordinate and Overpass-like elements supplied by the caller.
- Tests use tiny local fixtures only.
- The `osm_features` table stores deterministic feature snapshots per listing and feature version.
- The CLI supports a dry run that inspects coordinate-ready listings without calling live OSM.
- The CLI can write `osm_features` rows either from a local/cache JSON file of Overpass-like elements or from a bounded live Overpass run.

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

## Writing Feature Rows

Use a local/cache elements file when you want deterministic writes without network access:

```powershell
.\.venv\Scripts\python.exe -m realtyscope.enrichment.osm `
  --database-url $env:DATABASE_URL `
  --limit 50 `
  --elements-file data/cache/osm/overpass-elements.json `
  --write `
  --json
```

The file must be a JSON object keyed by listing ID. Each value is a list of Overpass-like elements accepted by `compute_osm_features`.

For a small runtime enrichment slice, use bounded live Overpass access:

```powershell
.\.venv\Scripts\python.exe -m realtyscope.enrichment.osm `
  --database-url $env:DATABASE_URL `
  --limit 5 `
  --live-overpass `
  --radius-m 1000 `
  --delay-seconds 2 `
  --write `
  --json
```

Live execution uses existing listing coordinates only, does not geocode addresses, and writes one row per `(listing_id, feature_version)`. Re-running the same feature version updates existing rows instead of duplicating them.

## Phase 5 Runtime Evidence

After applying Alembic head `20260602_0004`, a bounded live Overpass run was executed against the local PostgreSQL database:

```powershell
.\.venv\Scripts\python.exe -m realtyscope.enrichment.osm `
  --database-url $env:DATABASE_URL `
  --limit 5 `
  --live-overpass `
  --radius-m 300 `
  --delay-seconds 1 `
  --timeout-seconds 20 `
  --write `
  --json
```

Observed result: `rows_inserted=3`, `rows_updated=1`, `rows_failed=1`, `live_osm_called=true`. The failed row returned `HTTP 429 Too Many Requests`, so the command kept the successful rows and reported the failure instead of rolling back the whole batch. The database then contained `4` `osm_features` rows for listing IDs `[1, 2, 3, 4]`; an ML feature probe over the first five listings reported `osm_rows_present=4`.

## Live OSM Caveat

Live Overpass fetching is available only as a bounded runtime command. Keep `--limit` small, use `--delay-seconds`, prefer cache/local extracts where possible, and do not run it from unit tests. Public Nominatim must not be used for bulk geocoding.

## Attribution

If RealtyScope shows maps, OpenStreetMap-derived features, or OSM-derived explanations in UI/docs, include visible attribution to OpenStreetMap contributors.
