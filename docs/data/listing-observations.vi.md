# Listing Observations và lịch sử giá

Ngày: 2026-06-02
Phase: 3.7 Observation / Price History Layer

RealtyScope bây giờ tách rõ trạng thái mới nhất của listing khỏi lịch sử quan sát theo thời gian. Đây là nền để phân tích tăng/giảm giá, làm trend dashboard, EDA theo thời gian, và validation cho ML sau này.

## Các lớp dữ liệu

| Lớp | Bảng | Mục đích | Quy tắc thay đổi |
| --- | --- | --- | --- |
| Raw source snapshot | `raw_listings` | Lưu payload gốc từ nguồn và `payload_hash` để audit/replay. | Chỉ insert một lần cho mỗi `(source_id, payload_hash)`. Nếu replay đúng payload cũ thì dùng lại row cũ. |
| Canonical latest listing | `listings` + `listing_source_links` | Lưu trạng thái normalized mới nhất của listing: giá hiện tại, diện tích, số phòng, tầng, tọa độ, quality flags. | Update khi persist normalized record mới hơn cho cùng `(source_id, source_listing_id)`. |
| Historical observation | `listing_observations` | Lưu snapshot normalized đã quan sát từ một raw listing: thời điểm quan sát, giá, giá/m2, diện tích, số phòng, tầng, trạng thái active/status. | Chỉ insert một lần cho mỗi `(source_id, source_listing_id, observed_at)`. Replay cùng timestamp không tạo observation trùng. Timestamp quan sát mới có chủ ý vẫn có thể tạo observation mới dù raw payload row được reuse. |

## Vì sao cần cả canonical và observation?

`listings` trả lời câu hỏi: "Trạng thái mới nhất đang biết của listing căn hộ này là gì?"

`listing_observations` trả lời câu hỏi: "Theo thời gian, listing này đã được quan sát với các trạng thái nào, và giá/thông tin đã đổi lúc nào?"

Tách hai lớp này giúp tránh hai lỗi lớn:

- API/dashboard đọc dữ liệu hiện tại vẫn đơn giản vì chỉ cần đọc `listings`;
- EDA/trend/ML không mất lịch sử khi canonical row bị update sang giá mới.

## Schema của observation

Mỗi row Phase 3.7 trong `listing_observations` gồm:

- `listing_id`: FK tới canonical listing;
- `source_id` và `source_listing_id`: định danh nguồn để group và so sánh theo source;
- `raw_listing_id`: FK tới raw snapshot để audit/replay;
- `observed_at`: thời điểm quan sát từ normalized listing;
- `price_rub` và `price_per_m2`: metric chính cho lịch sử giá;
- `total_area_m2`, `rooms`, `floor`, `floors_total`: snapshot các thuộc tính listing có thể ảnh hưởng phân tích;
- `active` và `status`: trạng thái snapshot, hiện khởi tạo là `active=true`, `status=observed`.

Indexes phục vụ các truy vấn sau:

- `ix_listing_observations_listing_observed`: xem lịch sử một listing theo thời gian;
- `ix_listing_observations_source_listing_observed`: xem lịch sử theo source listing và so sánh giữa nguồn.

Unique constraint `uq_listing_observations_source_listing_observed` ngăn tạo observation trùng cho cùng source listing tại cùng timestamp quan sát. Constraint này cố ý cho phép raw payload lặp lại tạo observation muộn hơn khi scheduled run ghi `observed_at` mới.

## Hành vi persistence

Khi persist một `IngestionBatch`:

1. `raw_listings` được insert hoặc reuse theo `payload_hash`.
2. `listings` được create/update theo `(source_id, source_listing_id)` thông qua `listing_source_links`.
3. `listing_observations` chỉ được insert nếu source listing đó chưa từng tạo observation tại cùng `observed_at`.

Kết quả mong đợi:

- Listing xuất hiện lần đầu: một raw row, một canonical listing row, một observation row.
- Replay cùng payload tại cùng `observed_at`: raw row được reuse, canonical listing được refresh, không tạo observation trùng.
- Replay cùng payload tại `observed_at` mới có chủ ý: raw row được reuse, canonical listing được refresh, tạo observation row mới.
- Cùng source listing nhưng giá hoặc payload quan trọng thay đổi: raw row mới, canonical listing update sang giá mới nhất, observation row mới.

## Ranh giới hiện tại

Phase 3.7 chỉ thêm backend history storage. Phase này chưa thêm trend API, filter theo period, seasonality chart, hoặc biểu đồ so sánh trong Streamlit. Các phần dashboard/API sau nên đọc từ `listing_observations`.
