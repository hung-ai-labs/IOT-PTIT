# 08 — Chuyển backend sang Spring Boot (07/10/2026)

Người dùng đã xác nhận thay FastAPI bằng Spring Boot, đây là quyết định mới thay thế
ràng buộc stack Python của kế hoạch/SRS ban đầu. Các phần giao diện và MQTT giữ hợp đồng cũ.

## Ánh xạ cấu trúc

| FastAPI cũ | Spring Boot hiện tại |
|---|---|
| `app/main.py` | `IotApplication.java` |
| `api/v1/` | `controller/` |
| `schemas/` | `dto/ApiDtos.java` |
| `db/models/` | `entity/` |
| SQLAlchemy Session / truy vấn | `repository/` — Spring Data JPA |
| `services/` | `service/` |
| `core/config.py` | `config/`, `application.yml`, `.env` |
| `core/security.py`, token store | `TokenService`, `AuthService`, `JwtFilter` |
| HTTPException / error handlers | `exception/` |
| Paho Python / pending registry | `MqttService`, `MqttMessageService`, `ControlService` |
| WebSocket hub | `WebSocketService`, `WebConfig` |
| Alembic | Flyway `resources/db/migration/` |

## Hợp đồng được giữ

- `/api/v1/auth/{register,login,me,logout}`; `PATCH /auth/me` lưu hồ sơ chính chủ.
- `/api/v1/sensors`, `/latest`, `/series`, các bộ lọc và phân trang.
- `/api/v1/devices`, `/{id}`, `/{id}/actions` (202 + Pending).
- `/api/v1/device-actions`, `/{id}`.
- `/api/v1/system/status`, `/health`, frontend tĩnh `/`.
- `/ws?token=...`, JSON sự kiện `{type,data}`.
- JSON snake_case; lỗi `{detail:{code,message}}`; định dạng Page giữ `total_pages`.
- MQTT topics chuẩn và legacy; UUID `cmd_id`; timeout, thất bại, phản hồi muộn.

`SHOW_IOT_DATA=false` của frontend giữ nguyên. Chuyển backend không tự bật số liệu,
không chạy giả lập và không tạo dữ liệu cảm biến/lịch sử mẫu.

## Dữ liệu

Entity dùng đúng tên bảng/cột hiện có. Hibernate validate; Flyway baseline 0 và SQL
`IF NOT EXISTS` cho database Alembic hiện tại. Hồ sơ/password/ID được giữ.
JWT HS256 dùng lại `SECRET_KEY`; BCrypt `$2b$` của Python được Spring nhận.
Danh sách token thu hồi vẫn lưu RAM như trước, mất khi restart.

Database mới được tạo bằng V1/V2. Có thể đăng ký tài khoản trên web hoặc chạy seed tài khoản
ở `backend/README.md`; không tự tạo tài khoản mới khi khởi động thường.

## Vị trí cần sửa thường gặp

- Danh mục đèn: `config/DeviceRegistry.java`.
- DTO và danh sách target hợp lệ: `dto/ApiDtos.java`.
- API: `controller/`; nghiệp vụ: `service/`.
- Thêm target để điều khiển thật: sửa registry, DTO pattern và tạo Flyway migration thay
  ràng buộc `device_actions.target`; cập nhật firmware và bộ lọc frontend tương ứng.
- Cấu hình: `.env`/biến môi trường; khởi động lại backend khi sửa Java/cấu hình.

Python cũ ở `legacy/fastapi/` để đối chiếu; không tiếp tục chạy trên cổng 8000 cùng Java.
Báo cáo PDF chưa từng có backend hoàn chỉnh và đã gỡ khỏi UI, nên không triển khai thêm
trong lần chuyển đổi này.
