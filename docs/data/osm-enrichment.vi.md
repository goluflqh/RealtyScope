# RealtyScope OpenStreetMap Enrichment

Ngày: 2026-06-02
Phase: 4.2 OSM infrastructure enrichment foundation

## Phạm Vi

Phase 4.2 thêm contract đầu tiên cho feature derived từ OpenStreetMap nhưng không gọi public OSM service trong tests. Implementation hiện tại cố ý local và dễ test bằng fixture:

- `realtyscope.enrichment.osm.compute_osm_features` nhận tọa độ listing và elements dạng Overpass-like do caller truyền vào.
- Tests chỉ dùng fixture nhỏ trong repo.
- Bảng `osm_features` lưu deterministic feature snapshots theo listing và feature version.
- CLI có dry run để kiểm tra listing có tọa độ, không gọi live OSM và không ghi enrichment rows.

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

## Caveat Về Live OSM

Live Overpass fetching chưa được implement trong subphase này. Bước an toàn tiếp theo là bounded fetcher dùng tọa độ listing có sẵn, cache hoặc local extracts nếu có thể, strict request limits, và rate limiting. Không dùng public Nominatim để bulk geocoding.

## Attribution

Nếu RealtyScope hiển thị map, feature derived từ OpenStreetMap, hoặc giải thích dựa trên OSM trong UI/docs, phải ghi attribution rõ cho OpenStreetMap contributors.
