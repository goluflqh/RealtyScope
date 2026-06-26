# RealtyScope OpenStreetMap Enrichment

Ngày: 2026-06-02
Phase: 4.2 OSM infrastructure enrichment foundation

## Phạm Vi

Phase 4.2 thêm contract đầu tiên cho feature derived từ OpenStreetMap nhưng không gọi public OSM service trong tests. Implementation hiện tại cố ý local và dễ test bằng fixture:

- `realtyscope.enrichment.osm.compute_osm_features` nhận tọa độ listing và elements dạng Overpass-like do caller truyền vào.
- Tests chỉ dùng fixture nhỏ trong repo.
- Bảng `osm_features` lưu deterministic feature snapshots theo listing và feature version.
- CLI có dry run để kiểm tra listing có tọa độ mà không gọi live OSM.
- CLI có thể ghi `osm_features` rows từ file JSON local/cache chứa Overpass-like elements hoặc từ một live Overpass run có giới hạn.

OpenStreetMap là nguồn enrichment, không phải nguồn listing chính. Domclick vẫn là source of record cho listing.

## 2026-06-25 Addendum Local Extract Va Provenance

Addendum nay supersede caveat cu `448 / 17,046` cho trang thai database hien tai.

Da dung mot local Moscow OpenStreetMap extract that tu BBBike:

- `data/cache/osm/Moscow.osm.geojson.xz`
- source mode: `bbbike_geojson_extract`
- attribution: `OpenStreetMap contributors`

Bulk enrichment chay offline, khong goi public Overpass cho cac row bulk:

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

Code hien tai khi doc real PostgreSQL database bao:

- `listings_total=17,046`
- `osm_features_total=17,046`
- `osm_featured_listings=17,046`
- `osm_coverage_pct=100.0`
- `osm_local_extract_rows=4,487`
- `osm_live_rows=16`
- `osm_coordinate_derived_rows=12,543`
- `osm_infrastructure_coverage_source=local_extract+live_overpass+coordinate_exact_match`

Caveat ve do chinh xac: day la full persisted feature coverage cho listing hien tai, khong phai claim moi row deu duoc fetch doc lap tu live Overpass. Direct local extract rows cover representative distinct coordinates; exact-coordinate derivation chi copy feature da persisted sang listing co cung chinh xac latitude/longitude va mark `source_summary.derivation=coordinate_exact_match`.

Verification cho provenance code:

- `python -m pytest -p no:cacheprovider tests/test_osm_enrichment.py tests/test_api_data_routes.py tests/test_streamlit_ui_payload.py -q`: `64 passed`
- `python -m ruff check src/realtyscope/enrichment/osm.py services/api/app/main.py services/streamlit/app.py tests/test_osm_enrichment.py tests/test_api_data_routes.py tests/test_streamlit_ui_payload.py`: passed
- `python -m py_compile src\realtyscope\enrichment\osm.py services\api\app\main.py services\streamlit\app.py tests\test_osm_enrichment.py tests\test_api_data_routes.py tests\test_streamlit_ui_payload.py`: passed
- Code-new local runtime cung da pass tren API `127.0.0.1:8014` va Streamlit `127.0.0.1:8512`: static audit in `api 17046 {'cian': 2436, 'domclick': 14610}`, CDP verify `osm_rows=17046`, `osm_local_extract_rows=4487`, `osm_coordinate_derived_rows=12543`, `osm_coverage_source=local_extract+live_overpass+coordinate_exact_match`, `monitoring.rendersOsmLocalExtractRows=true`, tat ca page gates, va 7 screenshot deu `clippedCount=0` / `overlapCount=0`.

Final Docker proof: sau khi rebuild Docker API/Streamlit, `127.0.0.1:8000` tra provenance field moi va Docker CDP tren `8000/8501` verify `osm_rows=17046`, `osm_local_extract_rows=4487`, `osm_coordinate_derived_rows=12543`, `osm_coverage_source=local_extract+live_overpass+coordinate_exact_match`, va district clusters co `feature_source=districtComparison+boundary+osm`.

## Feature Contract

Feature version hiện tại: `osm_local_v1`.

Feature set đầu tiên giữ conservative:

| Field | Ý nghĩa |
| --- | --- |
| `transport_count_500m` | Số transport nodes/stations/stops trong bán kính 500 m. |
| `transport_count_1000m` | Số transport nodes/stations/stops trong bán kính 1000 m. |
| `nearest_transport_m` | Khoảng cách tới transport feature gần nhất trong bán kính cấu hình. |
| `schools_count_1000m` | School, kindergarten, college, hoặc university amenities trong 1000 m. |
| `parks_count_1000m` | Park, garden, nature reserve, forest/grass/recreation landuse trong 1000 m. |
| `shops_count_1000m` | Shop có tag bất kỳ trong 1000 m. |
| `healthcare_count_1000m` | Healthcare, clinic, hospital, doctors, pharmacy amenities trong 1000 m. |
| `source_summary` | JSON nhỏ mô tả coverage của fixture/local source. |

## Persistence

Bảng `osm_features` lưu một row cho mỗi `(listing_id, feature_version)`. Cách này giúp feature snapshot reproducible cho Phase 4.3 ML feature rows và cho phép thêm feature version mới mà không overwrite experiment cũ.

## Dry Run

Dùng dry run để kiểm tra số listing đã sẵn sàng về tọa độ:

```powershell
.\.venv\Scripts\python.exe -m realtyscope.enrichment.osm --database-url $env:DATABASE_URL --limit 50 --dry-run --json
```

Dry run trả selected listing IDs, feature version, và `live_osm_called=false`. Nó không gọi Overpass, public OSM APIs, hoặc Nominatim.

## Ghi Feature Rows

Dùng file elements local/cache khi cần ghi deterministic mà không cần network:

```powershell
.\.venv\Scripts\python.exe -m realtyscope.enrichment.osm `
  --database-url $env:DATABASE_URL `
  --limit 50 `
  --elements-file data/cache/osm/overpass-elements.json `
  --write `
  --json
```

File này phải là JSON object keyed by listing ID. Mỗi value là list Overpass-like elements mà `compute_osm_features` đọc được.

Với runtime enrichment nhỏ, dùng live Overpass có giới hạn:

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

Live execution chỉ dùng tọa độ listing đã có, không geocode address, và ghi một row cho mỗi `(listing_id, feature_version)`. Chạy lại cùng feature version sẽ update row hiện có thay vì tạo trùng.

## Evidence Runtime Phase 5

Sau khi apply Alembic head `20260602_0004`, một live Overpass run có giới hạn đã được chạy trên local PostgreSQL database:

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

Kết quả quan sát: `rows_inserted=3`, `rows_updated=1`, `rows_failed=1`, `live_osm_called=true`. Row fail trả `HTTP 429 Too Many Requests`, nên command giữ các row thành công và report lỗi thay vì rollback cả batch. Database sau đó có `4` rows trong `osm_features` cho listing IDs `[1, 2, 3, 4]`; probe ML features trên năm listing đầu báo `osm_rows_present=4`.

## Caveat Về Live OSM

Live Overpass fetching chỉ có dưới dạng runtime command có giới hạn. Giữ `--limit` nhỏ, dùng `--delay-seconds`, ưu tiên cache/local extracts nếu có thể, và không chạy trong unit tests. Không dùng public Nominatim để bulk geocoding.

## 2026-06-25 Missing-Distinct-Coordinate Selector

Live Overpass path bay gio tranh goi mang trung lap:

- bo qua toa do da co OSM feature cho feature version hien tai;
- chon mot listing dai dien cho moi toa do distinct con thieu;
- duplicate listings duoc lap bang `--derive-coordinate-matches`.

Dry-run nen chay truoc moi live batch:

```powershell
$env:PYTHONPATH = "src;."
python -m realtyscope.enrichment.osm --dry-run --live-overpass --limit 20 --json
```

Dung `--progress-log output/osm-enrichment/overpass-batches-20260625.jsonl` cho moi dry-run/write/derive batch de append mot JSONL evidence row gom operation, limit, radius, delay, timeout, selected listing IDs, row counts, va errors.

Evidence moi nhat: batch dau tien co `selection_mode=live_overpass_missing_distinct_coordinates`, `rows_available=4,493`; live smoke them `1` row that va derive exact-coordinate them `27` rows. Batch logged tiep theo dry-run chon `[7, 8]`, live Overpass them `2` rows that voi `rows_failed=0`, sau do derive exact-coordinate them `17` rows. Selector sau batch con `rows_available=4,491`, first selected IDs `[10, 11, 13, 15, 16]`. API coverage hien la `osm_features_total=436`, `osm_featured_listings=436`, `osm_coverage_pct=2.56`, `osm_live_rows=12`, `osm_coordinate_derived_rows=424`.

Day van la partial infrastructure coverage. Khong noi district clusters la full OSM-backed cho den khi co long batch that hoac local extract/cache that.

## Attribution

Nếu RealtyScope hiển thị map, feature derived từ OpenStreetMap, hoặc giải thích dựa trên OSM trong UI/docs, phải ghi attribution rõ cho OpenStreetMap contributors.
