# Kế Hoạch Phase 9 RealtyScope: Workstream Sạch Và Bằng Chứng Thật

Kế hoạch kỹ thuật chính nằm ở `docs/superpowers/plans/2026-06-20-realtyscope-phase9-clean-workstreams-plan.md`. Bản tiếng Việt này là tóm tắt vận hành để tiếp tục dự án mà không mất ngữ cảnh.

## Mục tiêu

Phase 9 không được làm như một nhánh lớn trộn mọi thứ. Ta sẽ đi theo các nhánh/worktree sạch:

- Phase 8: chuẩn bị nhánh scheduler `ops/domclick-scheduler-validated-20260619` để publish/PR khi được phép.
- Phase 9A: xác nhận data/backend readiness từ PostgreSQL/API/Redis thật, không chạy live Domclick nếu chưa được duyệt.
- Phase 9B: xây workflow MLOps retrain-compare-promote: dry-run compare, promote/reject có gate, rollback/selection, report quyết định, tests.
- Phase 9C: vá khoảng trống API/monitoring sau khi model selection đã có.
- Phase 9D: tiếp tục UI Nga dark từ `ui/recovered-real-data-dashboard-20260620`, không dùng `ui/realtyscope-ultimate-redesign` làm nguồn chính.
- Phase 9E: cập nhật docs/CI/demo từ bằng chứng mới, không phóng đại baseline model hoặc dữ liệu trend.

## Ràng buộc chính

- `main` hiện sạch nhưng ahead `origin/main` 5 commit; không push/merge `main` trộn lẫn.
- Không đổi trigger scheduler và không chạy live Domclick capture nếu chưa được duyệt rõ.
- Không dùng dữ liệu giả/sample làm bằng chứng production UI.
- Không xóa stash/branch, rewrite history, reset/repoint `main`, push/merge remote nếu chưa được duyệt.
- Nếu thêm dependency ML nặng như XGBoost thì cần kế hoạch riêng trước.

## Bằng chứng khởi điểm

- Scheduler đã có hai lần chạy tự động liên tiếp thành công vào 2026-06-19 và 2026-06-20 Moscow.
- UI real-data Nga đã được phục hồi vào worktree `C:\Users\lequa\.config\superpowers\worktrees\RealtyScope\ui-recovered-real-data-dashboard-20260620`, commit `b6922b7`.
- Nhánh `ml/model-promotion-workflow` hiện mới có phần định hướng docs trong `docs/project-status.md`, chưa có code compare/promote/rollback thật.

## Cổng hoàn thành Phase 9

Chỉ coi Phase 9 hoàn thành khi có bằng chứng hiện tại cho tất cả điểm sau:

- Phase 8 scheduler branch sạch, test lại, và giữ bằng chứng 2 lần chạy tự động thành công.
- Phase 9A có bằng chứng API/PostgreSQL/Redis thật và các nhánh data/backend sạch.
- Phase 9B có dry-run compare, promote/reject có gate, rollback/selection, report, tests.
- Phase 9C API/monitoring đọc selected model và trạng thái runtime mà không train trong request.
- Phase 9D UI Nga khởi động lại từ nhánh phục hồi, dùng dữ liệu API/PostgreSQL thật, và được browser/runtime check.
- Phase 9E docs/CI/demo phản ánh đúng trạng thái đã kiểm chứng.
