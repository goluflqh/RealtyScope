# Báo cáo mô hình dự báo giá nhà RealtyScope

Ngày cập nhật: 2026-06-27
Artifact chính: `data/processed/models/phase5/selected_price_model_v1_non_leaky.joblib`
Feature version: `ml_features_v2_non_leaky`
Model version: `selected_price_model_v1_non_leaky`

## 1. Mục tiêu

Mục tiêu của mô hình là dự báo giá bán căn hộ tại Moscow từ bảng thông số có thể thay đổi bởi người dùng: diện tích, số phòng, tầng, năm xây dựng, tọa độ, khoảng cách giao thông, số trường học/công viên/cửa hàng, và các cờ thiếu dữ liệu.

Điểm quan trọng: mô hình hiện dự báo `price_per_m2`, sau đó backend/API nhân với `total_area_m2` do người dùng nhập để trả về `predicted_price_rub`. Vì vậy giá trị `60 m²` trên UI chỉ là giá trị khởi tạo ban đầu, không phải giả định cố định của mô hình.

## 2. Dữ liệu dùng để huấn luyện

Runtime PostgreSQL đã kiểm chứng:

| Thành phần | Giá trị |
| --- | ---: |
| Listing tổng | 17,287 |
| Listing đủ điều kiện ML | 17,287 |
| Observation | 45,764 |
| Ngày quan sát | 23 |
| Khoảng thời gian | 2026-05-14 đến 2026-06-26 |
| Listing có OSM feature | 17,046 |

## 3. Feature engineering

Feature set `ml_features_v2_non_leaky` gồm 23 feature:

- Thông số căn hộ: `total_area_m2`, `rooms`, `floor`, `floors_total`, `building_year`.
- Cờ thiếu dữ liệu: `floor_missing`, `floors_total_missing`, `building_year_missing`, `coordinates_missing`, `nearest_transport_m_missing`, `observation_missing`, `osm_missing`.
- Vị trí: `latitude`, `longitude`.
- OSM / hạ tầng xung quanh: `nearest_transport_m`, `transport_count_500m`, `transport_count_1000m`, `schools_count_1000m`, `parks_count_1000m`, `shops_count_1000m`, `healthcare_count_1000m`.
- Metadata an toàn: `observation_count`, `property_type_apartment`.

Phiên bản này loại bỏ các feature gây leakage trực tiếp:

- `latest_observation_price_rub`
- `latest_observation_price_per_m2`

Do đó mô hình không được phép “nhìn” giá gần nhất của chính listing trong input feature.

## 4. Candidate models

Training workflow so sánh 3 candidate trên cùng grouped split theo `listing_id`:

| Candidate | Vai trò |
| --- | --- |
| Ridge | Baseline tuyến tính, dễ giải thích nhưng underfit |
| RandomForest | Tree ensemble baseline ổn định |
| HistGradientBoosting | Candidate cuối, regularized để giảm overfit |

HistGradientBoosting cuối dùng cấu hình regularized:

- `learning_rate=0.06`
- `max_iter=240`
- `max_leaf_nodes=31`
- `min_samples_leaf=20`
- `l2_regularization=0.10`

Cấu hình này thay thế bản HGB cũ có `min_samples_leaf=2`, vì bản cũ có train-test gap lớn hơn và dễ bị optimistic trên random split.

## 5. Kết quả artifact cuối

Grouped random holdout từ artifact cuối:

| Metric | Giá trị |
| --- | ---: |
| Rows | 17,287 |
| Train rows | 13,829 |
| Test rows | 3,458 |
| Selected candidate | `hist_gradient_boosting` |
| Target | `price_per_m2` |
| Validation R² | 0.9314 |
| Train R² | 0.9595 |
| R² gap | 0.0281 |
| MAE | 4.81M RUB |
| RMSE | 14.94M RUB |
| MAPE | 11.04% |

Candidate comparison:

| Candidate | R² | MAE | MAPE | Train R² | Gap |
| --- | ---: | ---: | ---: | ---: | ---: |
| HistGradientBoosting | 0.9314 | 4.81M | 11.04% | 0.9595 | 0.0281 |
| RandomForest | 0.8936 | 6.76M | 16.00% | 0.9372 | 0.0437 |
| Ridge | -0.9874 | 12.71M | 27.74% | 0.5157 | 1.5032 |

Top feature importance của artifact cuối:

| Rank | Feature |
| ---: | --- |
| 1 | `latitude` |
| 2 | `longitude` |
| 3 | `shops_count_1000m` |
| 4 | `building_year` |
| 5 | `total_area_m2` |
| 6 | `schools_count_1000m` |
| 7 | `floors_total` |
| 8 | `parks_count_1000m` |

## 6. Audit overfitting

Câu hỏi: R² khoảng 0.93 có bị quá khớp không?

Kết luận ngắn: không thấy leakage trực tiếp, nhưng random split là optimistic. Vì vậy không nên chỉ nói “model đạt R² 0.93” mà phải nói kèm stress validation.

Kết quả audit:

| Validation split | Test R² | MAE | MAPE | Ý nghĩa |
| --- | ---: | ---: | ---: | --- |
| Random listing holdout | 0.9345 | 4.87M | 11.10% | Headline metric, nhưng optimistic |
| Spatial grid holdout | 0.8882 | 6.94M | 17.94% | Kiểm tra khả năng tổng quát sang vùng khác |
| Latest-20% temporal holdout | 0.8503 | 7.04M | 12.83% | Kiểm tra drift theo thời gian |

Diễn giải để bảo vệ:

> Mô hình không bị leakage trực tiếp vì feature v2 không chứa giá mục tiêu hoặc giá quan sát gần nhất. Tuy nhiên bất động sản có tương quan rất mạnh theo khu vực và thời gian, nên random holdout có thể đánh giá hơi cao. Vì vậy em audit thêm spatial và temporal holdout. Khi kiểm tra khó hơn, R² vẫn còn khoảng 0.85–0.89, cho thấy mô hình có tín hiệu thật nhưng chưa nên gọi là production-grade appraiser nếu chưa có temporal/spatial promotion gate tự động.

## 7. Backend/API logic

Luồng `/predict`:

1. Nhận `features` từ UI hoặc API client.
2. Kiểm tra feature names phải khớp artifact.
3. Model dự báo `price_per_m2`.
4. Backend nhân với `features.total_area_m2`.
5. Trả về:
   - `predicted_price_rub`;
   - `input_features_echo`;
   - `target_variable`;
   - `selected_candidate`;
   - `metrics_summary`;
   - `feature_importance`.

Điều này giải quyết lỗi cũ: thay đổi diện tích/số phòng/hạ tầng không còn bị hiểu là giá trị mặc định hoặc bị mất trước khi gọi backend.

## 8. UI logic

Trang valuation hiện có:

- input diện tích 10–1200 m²;
- input số phòng 0–20, không còn nén mọi căn `5+` thành số 5;
- input tầng, tổng số tầng, năm xây dựng;
- checkbox năm xây dựng có biết/không biết;
- checkbox tọa độ và hạ tầng có biết/không biết;
- input khoảng cách giao thông, trường học, công viên, cửa hàng, transport 500m/1000m;
- input echo hiển thị lại feature backend đã nhận;
- tự gọi canonical `/predict` khi connected API sẵn sàng.

Nếu người dùng chưa biết tọa độ/hạ tầng, UI gửi missing flags rõ ràng thay vì giả vờ giá trị 0 là dữ liệu thật.

## 9. Giới hạn trung thực

- Đây là model snapshot đã validate, không phải hệ thống tự retrain mỗi ngày.
- Chưa claim XGBoost vì dependency không có trong lock/runtime.
- Spatial/temporal validation thấp hơn random validation; đây là caveat quan trọng cần nói khi bảo vệ.
- Giá thị trường thật có thể thay đổi theo thời gian; cần promotion gate trước khi deploy retrain tự động.
- Exposure/lifecycle forecast của dự án là suy luận từ observation gaps, không phải confirmed sale/removal.

## 10. Lệnh kiểm chứng nhanh

Train lại artifact:

```powershell
$env:PYTHONPATH = (Resolve-Path .\src).Path
python -m realtyscope.ml.train `
  --database-url postgresql+psycopg://realtyscope:realtyscope@localhost:5432/realtyscope `
  --output-dir data/processed/models/phase5 `
  --feature-version ml_features_v2_non_leaky `
  --trainer selected `
  --target-variable price_per_m2 `
  --json
```

Kiểm tra API predict:

```bash
curl -fsS http://localhost:8000/model/metadata | python -m json.tool
curl -fsS -X POST http://localhost:8000/predict \
  -H 'Content-Type: application/json' \
  -d '{"features":{"building_year":2018,"building_year_missing":0,"coordinates_missing":1,"floor":5,"floor_missing":0,"floors_total":20,"floors_total_missing":0,"healthcare_count_1000m":0,"latitude":55.75,"longitude":37.61,"nearest_transport_m":0,"nearest_transport_m_missing":1,"observation_count":1,"observation_missing":0,"osm_missing":1,"parks_count_1000m":0,"property_type_apartment":1,"rooms":2,"schools_count_1000m":0,"shops_count_1000m":0,"total_area_m2":60,"transport_count_1000m":0,"transport_count_500m":0}}' \
  | python -m json.tool
```
