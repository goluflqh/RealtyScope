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

## 2026-06-25 Local Extract Coverage And Provenance Addendum

This addendum supersedes the earlier `448 / 17,046` sparse-coverage caveat for the current database state.

A real local Moscow OpenStreetMap extract was used from BBBike:

- `data/cache/osm/Moscow.osm.geojson.xz`
- source mode: `bbbike_geojson_extract`
- attribution: `OpenStreetMap contributors`

The enrichment was run offline without public Overpass calls for the bulk rows:

```powershell
$env:PYTHONPATH = "src;."
python -m realtyscope.enrichment.osm `
  --geojson-file data\cache\osm\Moscow.osm.geojson.xz `
  --write `
  --limit 10000 `
  --radius-m 1000 `
  --progress-log output\osm-enrichment\geojson-batches-20260625.jsonl `
  --json
python -m realtyscope.enrichment.osm `
  --derive-coordinate-matches `
  --write `
  --limit 20000 `
  --progress-log output\osm-enrichment\geojson-batches-20260625.jsonl `
  --json
```

Current code against the real PostgreSQL database reports:

- `listings_total=17,046`
- `osm_features_total=17,046`
- `osm_featured_listings=17,046`
- `osm_coverage_pct=100.0`
- `osm_local_extract_rows=4,487`
- `osm_live_rows=16`
- `osm_coordinate_derived_rows=12,543`
- `osm_infrastructure_coverage_source=local_extract+live_overpass+coordinate_exact_match`

Important precision caveat: this is full persisted feature coverage for the current listings, not a claim that every row was independently fetched from live Overpass. The direct local extract rows cover representative distinct coordinates; exact-coordinate derivation copies those persisted features only to listings with identical latitude/longitude and marks them with `source_summary.derivation=coordinate_exact_match`.

Verification for the provenance code:

- `python -m pytest -p no:cacheprovider tests/test_osm_enrichment.py tests/test_api_data_routes.py tests/test_streamlit_ui_payload.py -q`: `64 passed`
- `python -m ruff check src/realtyscope/enrichment/osm.py services/api/app/main.py services/streamlit/app.py tests/test_osm_enrichment.py tests/test_api_data_routes.py tests/test_streamlit_ui_payload.py`: passed
- `python -m py_compile src\realtyscope\enrichment\osm.py services\api\app\main.py services\streamlit\app.py tests\test_osm_enrichment.py tests\test_api_data_routes.py tests\test_streamlit_ui_payload.py`: passed
- Code-new local runtime proof also passed on API `127.0.0.1:8014` and Streamlit `127.0.0.1:8512`: static audit printed `api 17046 {'cian': 2436, 'domclick': 14610}`, and CDP verified `osm_rows=17046`, `osm_local_extract_rows=4487`, `osm_coordinate_derived_rows=12543`, `osm_coverage_source=local_extract+live_overpass+coordinate_exact_match`, `monitoring.rendersOsmLocalExtractRows=true`, all page gates, and all seven screenshots with `clippedCount=0` / `overlapCount=0`.

Final Docker proof: after rebuilding Docker API/Streamlit, `127.0.0.1:8000` returns the new OSM provenance fields and Docker CDP on `8000/8501` verifies `osm_rows=17046`, `osm_local_extract_rows=4487`, `osm_coordinate_derived_rows=12543`, `osm_coverage_source=local_extract+live_overpass+coordinate_exact_match`, and district clusters with `feature_source=districtComparison+boundary+osm`.

## 2026-06-25 Rate-Limited Live Batch Evidence

No usable local OSM extract/cache was found after repeating the search in the repo and parent project tree for `.pbf`, `.osm`, `.osm.bz2`, `.mbtiles`, Overpass cache, or OSM cache files.

The missing-distinct-coordinate selector remains active:

```powershell
$env:PYTHONPATH = "src;."
python -m realtyscope.enrichment.osm --dry-run --live-overpass --limit 20 --json
```

Latest selector evidence after the rate-limited batch: `selection_mode=live_overpass_missing_distinct_coordinates`, `rows_available=4,487`, first selected IDs `[13, 15, 16, 19, 21, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37]`.

A controlled logged live batch was attempted:

```powershell
$env:PYTHONPATH = "src;."
python -m realtyscope.enrichment.osm `
  --live-overpass `
  --write `
  --limit 10 `
  --radius-m 1000 `
  --delay-seconds 2 `
  --timeout-seconds 25 `
  --progress-log output/osm-enrichment/overpass-batches-20260625.jsonl `
  --json
```

Result: `rows_inserted=4`, `rows_failed=6`, `selected_listing_ids=[10, 11, 13, 15, 16, 18, 19, 21, 22, 23]`; all failures were `HTTPError: HTTP Error 429: Too Many Requests`. Exact-coordinate derivation after the batch inserted `8` rows without a live OSM call.

API evidence after derivation: `osm_features_total=448`, `osm_featured_listings=448`, `osm_coverage_pct=2.63`, `osm_live_rows=16`, `osm_coordinate_derived_rows=432`, and `osm_infrastructure_coverage_source=live_overpass+coordinate_exact_match`.

Because public Overpass rate-limited this batch and confirmed coverage remains sparse, do not continue live batches immediately and do not describe district clusters as OSM-infrastructure-backed.

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

Use exact-coordinate derivation after a trusted live/cache run when multiple listings share the same persisted coordinates:

```powershell
.\.venv\Scripts\python.exe -m realtyscope.enrichment.osm `
  --database-url $env:DATABASE_URL `
  --derive-coordinate-matches `
  --write `
  --limit 10000 `
  --json
```

This command does not call Overpass. It copies a persisted OSM feature row only to listings with identical `latitude` / `longitude` and marks each copied row with `source_summary.derivation=coordinate_exact_match`, `derived_from_listing_id`, `source_live_osm_called`, and `live_osm_called=false`.

For a small runtime enrichment slice, use bounded live Overpass access:

```powershell
.\.venv\Scripts\python.exe -m realtyscope.enrichment.osm `
  --database-url $env:DATABASE_URL `
  --limit 5 `
  --live-overpass `
  --radius-m 1000 `
  --delay-seconds 2 `
  --timeout-seconds 25 `
  --write `
  --progress-log output/osm-enrichment/overpass-batches-20260625.jsonl `
  --json
```

Live execution uses existing listing coordinates only, does not geocode addresses, and writes one row per `(listing_id, feature_version)`. Re-running the same feature version updates existing rows instead of duplicating them. `--progress-log` appends one JSONL evidence row per dry-run/write/derive command with the operation name, controls (`limit`, radius, delay, timeout), selected listing IDs, row counts, and errors.

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

## 2026-06-25 Missing-Distinct-Coordinate Selector

The live Overpass path now avoids redundant network calls. When `fetch_elements` / `--live-overpass` is used, the selector:

- skips coordinates that already have an OSM feature for the active feature version;
- selects one representative listing per missing distinct `(latitude, longitude)`;
- leaves duplicate listings to the separate `--derive-coordinate-matches` command.

Use this dry-run before any live batch:

```powershell
$env:PYTHONPATH = "src;."
python -m realtyscope.enrichment.osm --dry-run --live-overpass --limit 20 --json
```

Latest evidence after the logged bounded live batches:

- first dry-run selector: `selection_mode=live_overpass_missing_distinct_coordinates`, `rows_available=4,493`;
- first live smoke: `rows_inserted=1`, `rows_failed=0`, `selected_listing_ids=[5]`;
- first exact-coordinate derivation: `rows_inserted=27`;
- logged dry-run before the second batch: `rows_available=4,493`, `rows_selected=2`, `selected_listing_ids=[7, 8]`;
- logged live batch: `rows_inserted=2`, `rows_failed=0`, `selected_listing_ids=[7, 8]`;
- logged exact-coordinate derivation: `rows_inserted=17`, `rows_failed=0`;
- selector after the second batch: `rows_available=4,491`, first selected IDs `[10, 11, 13, 15, 16]`;
- API coverage: `osm_features_total=436`, `osm_featured_listings=436`, `osm_coverage_pct=2.56`, `osm_live_rows=12`, `osm_coordinate_derived_rows=424`;
- batch evidence log: `output/osm-enrichment/overpass-batches-20260625.jsonl`.

This is still partial infrastructure coverage. Do not describe district clusters as full OSM-backed until a real long batch or local extract/cache covers enough of the remaining missing coordinates.

## Live OSM Caveat

Live Overpass fetching is available only as a bounded runtime command. Keep `--limit` small, use `--delay-seconds`, prefer cache/local extracts where possible, and do not run it from unit tests. Public Nominatim must not be used for bulk geocoding.

## Attribution

If RealtyScope shows maps, OpenStreetMap-derived features, or OSM-derived explanations in UI/docs, include visible attribution to OpenStreetMap contributors.
