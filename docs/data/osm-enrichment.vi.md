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

## Attribution

Nếu RealtyScope hiển thị map, feature derived từ OpenStreetMap, hoặc giải thích dựa trên OSM trong UI/docs, phải ghi attribution rõ cho OpenStreetMap contributors.
