# 02 — Thiết kế cơ sở dữ liệu (PostgreSQL)

> Cập nhật 07/10/2026: backend đã chuyển sang Spring Boot theo xác nhận của người dùng. Mục dưới giữ kế hoạch cũ để đối chiếu; xem [08-SPRING-BOOT-MIGRATION.md](08-SPRING-BOOT-MIGRATION.md) và [backend/README.md](../backend/README.md) để chạy và sửa code hiện tại.

Theo SRS §4.2: 3 bảng `users`, `data_sensor`, `device_actions`.
Phần "Bổ sung" bên dưới là các cột/index cần thiết để hiện thực F09–F12 mà SRS chưa nêu chi tiết.

## 1. ERD

```
users (1) ────< device_actions (N)
                    │
                 device_id (VARCHAR, không FK — thiết bị không có bảng riêng trong SRS)
                    │
data_sensor ────────┘  (cùng không gian device_id)
```

## 2. DDL

```sql
-- 2.1 users
CREATE TABLE users (
    id            BIGSERIAL PRIMARY KEY,
    full_name     VARCHAR(100) NOT NULL,
    email         VARCHAR(150) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role          VARCHAR(20)  NOT NULL DEFAULT 'USER'
                  CHECK (role IN ('USER','ADMIN')),
    created_at    TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ  NOT NULL DEFAULT now()
);
CREATE INDEX idx_users_email ON users(email);

-- 2.2 data_sensor
CREATE TABLE data_sensor (
    id          BIGSERIAL PRIMARY KEY,
    device_id   VARCHAR(50)  NOT NULL,
    sensor_type VARCHAR(20)  NOT NULL
                CHECK (sensor_type IN ('temperature','humidity','light')),
    value       NUMERIC(10,2) NOT NULL,
    unit        VARCHAR(10)  NOT NULL,          -- '°C' | '%' | 'lux'
    timestamp   TIMESTAMPTZ  NOT NULL DEFAULT now()
);
-- phục vụ F12: lọc theo device + type + khoảng thời gian, sort giảm dần
-- Thực tế tạo ASC: PostgreSQL quét btree ngược với cùng chi phí, nên DESC không cần thiết
-- khi các cột dẫn đầu đều là điều kiện bằng.
CREATE INDEX idx_sensor_lookup ON data_sensor (device_id, sensor_type, timestamp);
CREATE INDEX idx_sensor_time   ON data_sensor (timestamp);

-- 2.3 device_actions
CREATE TABLE device_actions (
    id         BIGSERIAL PRIMARY KEY,
    device_id  VARCHAR(50) NOT NULL,
    target     VARCHAR(20) NOT NULL CHECK (target IN ('red','green','yellow')),
    action     VARCHAR(20) NOT NULL CHECK (action IN ('ON','OFF')),
    issued_by  BIGINT      REFERENCES users(id) ON DELETE SET NULL,
    result     VARCHAR(20) NOT NULL DEFAULT 'Pending'
               CHECK (result IN ('Pending','Success','Failed','Timeout')),
    timestamp  TIMESTAMPTZ NOT NULL DEFAULT now(),

    -- Bổ sung (không có trong SRS nhưng bắt buộc để hiện thực F11):
    cmd_id       UUID        NOT NULL UNIQUE,     -- khớp lệnh ↔ feedback MQTT
    responded_at TIMESTAMPTZ,                     -- thời điểm nhận feedback
    error_msg    VARCHAR(255)                     -- lý do khi Failed
);
CREATE INDEX idx_actions_lookup ON device_actions (device_id, target, result, timestamp);
CREATE INDEX idx_actions_time   ON device_actions (timestamp);
CREATE UNIQUE INDEX ix_device_actions_cmd_id ON device_actions (cmd_id);
```

## 3. Quy ước giá trị

| Trường | Giá trị hợp lệ |
|---|---|
| `sensor_type` | `temperature` (°C), `humidity` (%), `light` (lux) |
| `target` | `led`, `fan`, `ac` — hiển thị: Đèn LED / Quạt / Điều hòa |
| `action` | `ON`, `OFF` |
| `result` | `Pending` → `Success` \| `Failed` \| `Timeout` |
| `device_id` | Chuỗi định danh ESP, ví dụ `esp32-01` |

## 4. Ràng buộc & lưu ý

- Mật khẩu: bcrypt (`passlib[bcrypt]`), cost 12. **Không bao giờ** lưu plaintext.
- Toàn bộ timestamp lưu UTC (`TIMESTAMPTZ`); frontend đổi sang `Asia/Ho_Chi_Minh`.
- `device_id` không có bảng `devices` riêng vì SRS chỉ định 3 bảng. Danh sách thiết bị
  chấp hành (led/fan/ac + GPIO + topic) khai báo **tĩnh trong config** (`DEVICE_REGISTRY`
  ở `app/core/config.py`) — đủ cho F10, đúng phạm vi SRS. Xem OQ-04.
- Bảng `data_sensor` tăng nhanh (3 dòng / 5s ≈ 51k dòng/ngày). Với đồ án thì chấp nhận;
  nếu cần, thêm job xoá dữ liệu > 30 ngày (`scripts/prune_sensor.py`).

## 5. Migration  ✅ ĐÃ THỰC HIỆN
- Migration đầu tiên: `backend/alembic/versions/056c8b671af8_*.py`.
- Lệnh: xem `backend/README.md` §Migration.
- Seed: `scripts/seed.py` → 2 tài khoản (`admin@ptit.edu.vn` / `user@ptit.edu.vn`, mật khẩu `123456`),
  864 bản ghi cảm biến 24h gần nhất, 40 bản ghi lịch sử điều khiển.
  Thêm `--reset` để xoá sạch trước khi nạp.

## 6. Khác biệt so với DDL ở trên (do SQLAlchemy sinh ra)
- Khoá chính khai báo `BigInteger().with_variant(Integer, "sqlite")` để test chạy được trên
  SQLite trong bộ nhớ. Trên PostgreSQL vẫn là `BIGSERIAL`.
- Index trên `timestamp` tạo theo chiều ASC (lý do ở §2).

## 7. Hồ sơ cá nhân (07/10/2026)

Migration `8f34b207c912` thêm `student_id VARCHAR(30)`, `school VARCHAR(200)` và
`contact_email VARCHAR(150)` vào bảng `users`. Các trường có thể để trống.
Email liên hệ tách khỏi email đăng nhập; cập nhật qua `PATCH /api/v1/auth/me`, chỉ cho chính chủ.
Thông tin B23DCCN361, trường PTIT và email liên hệ được nạp cho tài khoản Nguyễn Xuân Hùng
(`admin@ptit.edu.vn`), không áp dụng mặc định cho tài khoản khác.
