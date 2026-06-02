# RealtyScope Phase 4 EDA Theo Observation History

Ngày: 2026-06-02
Nguồn: database mặc định của RealtyScope sau audit data-readiness Phase 4.0.
Notebook: `notebooks/phase4_eda_observations.ipynb`

## Snapshot Dữ Liệu

- Bảng canonical `listings`: 2000 dòng.
- Bảng `listing_observations`: 2000 dòng.
- Listing có tọa độ: 2000 dòng, coverage 100.00%.
- Listing ML-ready: 2000 dòng, coverage 100.00%.
- Listing có nhiều hơn một observation: 0.
- Có 0 biến động giá trong observation history hiện tại, nên bảng observation đã chứng minh được persistence coverage nhưng chưa đủ để kết luận xu hướng thời gian.

## Phân Phối Latest Listing

Các phân phối giá và diện tích đủ dùng cho EDA cross-sectional và baseline đầu tiên:

| Metric | Min | P25 | Median | P75 | P95 | Max |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `price_rub` | 4,699,000 | 17,000,000 | 24,387,349.5 | 38,456,904.5 | 103,751,048.5 | 1,905,387,907 |
| `price_per_m2` | 143,442.62 | 362,983.96 | 469,539.57 | 604,147.12 | 1,042,105.83 | 4,860,683.44 |
| `total_area_m2` | 10.00 | 39.38 | 55.80 | 76.40 | 127.82 | 438.00 |

Phân phối số phòng:

| Số phòng | Số listing |
| ---: | ---: |
| 0 | 194 |
| 1 | 510 |
| 2 | 646 |
| 3 | 483 |
| 4 | 132 |
| 5 | 30 |
| 6 | 4 |
| 7 | 1 |

Các listing có giá hoặc giá/m2 rất cao nên được xem là outlier candidates trước khi train model, không drop âm thầm.

## Observation Count Và Price-Change Analysis

Hiện mỗi canonical listing có đúng một dòng trong `listing_observations`:

- Observation count min/median/max: 1 / 1 / 1.
- Listing có nhiều hơn một observation: 0.
- Có 0 biến động giá trên toàn bộ 2000 listing.

Điều này đủ để xác nhận Phase 3.7 đã populate observation table, nhưng chưa đủ để phân tích trend, volatility, listing lifetime, hoặc temporal leakage. Các phân tích đó cần đợi scheduled daily capture tạo nhiều observation/listing và có raw payload thay đổi.

## Coordinate Coverage Và OpenStreetMap Readiness

Coverage tọa độ đã đủ tốt để bắt đầu Phase 4.2 OpenStreetMap enrichment:

- `has_coordinates`, `latitude`, và `longitude` khớp cho cả 2000 listing.
- Candidate OpenStreetMap features nên bắt đầu từ transport, schools, parks, shops, healthcare counts, và nearest transport distance.
- Phase 4.1 không gọi live OSM hoặc Overpass. Docs/UI dùng dữ liệu derived từ OpenStreetMap trong tương lai phải có attribution và nên dùng access có limit, cache, rate-limit hoặc local extract.

## Baseline Naive Và Target Distribution

Có thể dùng baseline naive làm mốc so sánh đầu tiên trước scikit-learn model:

- Median `price_rub`: 24,387,349.5 RUB.
- Median `price_per_m2`: 469,539.57 RUB/m2.

Baseline naive này cố ý đơn giản. Nên đánh giá nó sau khi feature snapshot deterministic và rule chống temporal leakage đã rõ.

## Kết Luận

Phase 4.1 đủ điều kiện cho EDA cross-sectional và chuẩn bị baseline đầu tiên. Dữ liệu cũng đã sẵn sàng cho OSM enrichment vì coordinate coverage đạt 100.00%. Giới hạn chính hiện tại là observation history chưa trưởng thành: `listing_observations` mới có một snapshot/listing và 0 biến động giá, nên mọi kết luận về trend hoặc price-change phải giữ conservative cho tới khi daily capture tích lũy thêm lịch sử.
