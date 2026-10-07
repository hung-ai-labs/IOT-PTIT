# Backend — Smart IoT (FastAPI)

REST API + MQTT bridge cho Hệ thống Giám sát và Điều khiển IoT.
Đặc tả: [`../docs/03-API-SPEC.md`](../docs/03-API-SPEC.md) · Kiến trúc: [`../docs/01-ARCHITECTURE.md`](../docs/01-ARCHITECTURE.md)

## Cài đặt lần đầu

```bash
# 1. Hạ tầng (PostgreSQL + Mosquitto)
docker compose -f infra/docker-compose.yml up -d

# 2. Môi trường Python (cần Python 3.12)
cd backend
python3.12 -m venv .venv
.venv/bin/pip install -r requirements.txt

# 3. Cấu hình
cp .env.example .env        # sửa SECRET_KEY trước khi triển khai thật

# 4. Tạo bảng
.venv/bin/alembic upgrade head

# 5. Nạp dữ liệu mẫu
.venv/bin/python ../scripts/seed.py  # chỉ tạo tài khoản, không sinh số liệu mẫu
```

## Chạy

```bash
cd backend && .venv/bin/uvicorn app.main:app --reload --port 8000
```

Chưa có ESP32 thật? Mở terminal thứ hai và chạy trình giả lập:

```bash
cd backend && .venv/bin/python ../scripts/mock_device.py
```

Nó publish `iot/sensor` mỗi 5 giây, heartbeat `iot/status` mỗi 10 giây, đặt Last Will,
và trả lời lệnh trên `iot/control` bằng `iot/feedback`. Thử luồng lỗi:

```bash
.venv/bin/python ../scripts/mock_device.py --fail-rate 0.3      # 30% lệnh trả Failed
.venv/bin/python ../scripts/mock_device.py --timeout-rate 0.2   # 20% lệnh không phản hồi
```

⚠️ Trình giả lập ghi ~36 dòng/phút vào `data_sensor`. Nhớ `Ctrl+C` khi không dùng,
hoặc `pkill -f mock_device.py`.

| Địa chỉ | Nội dung |
|---|---|
| http://localhost:8000/ | Web Dashboard (frontend tĩnh, FastAPI phục vụ luôn) |
| http://localhost:8000/docs | Swagger UI |
| http://localhost:8000/health | Trạng thái API + độ trễ DB |
| ws://localhost:8000/ws?token=&lt;JWT&gt; | WebSocket realtime (sensor, thiết bị, hệ thống) |

## Tài khoản mẫu (sau khi seed)

| Email | Mật khẩu | Vai trò |
|---|---|---|
| `admin@ptit.edu.vn` | `123456` | ADMIN |
| `user@ptit.edu.vn` | `123456` | USER |

Frontend **đã nối vào các tài khoản này** — đăng nhập bằng **email**, không phải tên đăng nhập
(bảng `users` không có cột `username`, xem `../docs/07-OPEN-QUESTIONS.md` OQ-13).

## Kiểm thử

```bash
cd backend && .venv/bin/python -m pytest tests -q
```

`tests/test_models.py` chạy trên SQLite trong bộ nhớ nên **không cần** PostgreSQL.
`tests/test_health.py` cần PostgreSQL đang chạy để `/health` trả `ok` (nếu không sẽ là `degraded`,
test vẫn pass).

## Migration

```bash
.venv/bin/alembic revision --autogenerate -m "mô tả thay đổi"   # xem lại file sinh ra trước khi chạy
.venv/bin/alembic upgrade head
.venv/bin/alembic downgrade -1
.venv/bin/alembic check          # phát hiện model lệch với DB
```

URL kết nối do `alembic/env.py` nạp từ `.env`, **không** khai báo trong `alembic.ini`.

## Cấu trúc

```
backend/
├── app/
│   ├── main.py            create_app(), lifespan, /health, mount frontend
│   ├── core/
│   │   ├── config.py      Settings + DEVICE_REGISTRY + SENSOR_UNITS/RANGES
│   │   └── security.py    bcrypt + JWT
│   ├── db/
│   │   ├── base.py        Base + gom model (Alembic import file này)
│   │   ├── session.py     engine, SessionLocal, get_db
│   │   └── models/        user.py · sensor.py · device_action.py
│   ├── mqtt/topics.py     Hằng số topic
│   ├── schemas/           (Giai đoạn 2+)
│   ├── api/v1/            (Giai đoạn 2+)
│   ├── services/          (Giai đoạn 3+)
│   ├── ws/hub.py          quản lý client WS + cầu thread-safe sang event loop
│   └── state/             (Giai đoạn 3)
├── alembic/               Migration
└── tests/
```

## MQTT

Client khởi động trong `lifespan` của FastAPI (`app/mqtt/client.py`), chạy trên thread riêng
của paho-mqtt với auto-reconnect backoff 1→30 giây. **Backend vẫn khởi động được khi broker
chưa sẵn sàng** — paho tự thử lại.

| Topic | Chiều | Xử lý bởi |
|---|---|---|
| `iot/sensor` | ESP → Server | `handle_sensor_message` → ghi `data_sensor` |
| `iot/status` | ESP → Server | `handle_status_message` → cập nhật `device_cache` |
| `iot/feedback` | ESP → Server | `handle_feedback_message` → cập nhật trạng thái ON/OFF |
| `iot/control` | Server → ESP | `control_service.send_action` publish lệnh |

Bộ topic cũ của SRS Chương 2 (`Sensor_data`, `device_response`) cũng được subscribe khi
`MQTT_LEGACY_TOPICS=true`, để bài kiểm thử terminal vẫn tái hiện được (OQ-01).

**Mọi bản tin đều đi qua Pydantic trước khi chạm cơ sở dữ liệu** (`app/schemas/mqtt.py`):
JSON hỏng, thiếu `device_id`, sai kiểu, hoặc giá trị ngoài biên (`SENSOR_RANGES`) đều bị bỏ
và ghi log cảnh báo. Giá trị ngoài biên trong một bản tin không làm mất các giá trị hợp lệ
còn lại của bản tin đó.

Kiểm tra nhanh bằng terminal:

```bash
docker exec iot-mosquitto mosquitto_sub -h localhost -t 'iot/#' -v
docker exec iot-mosquitto mosquitto_pub -h localhost -t 'iot/sensor' \
  -m '{"device_id":"ESP32-01","temp":27.5,"humid":62,"light":243}'
```

## Vòng đời lệnh điều khiển

```
POST /devices/{id}/actions
  → kiểm tra MQTT / thiết bị online / lệnh trùng   (F13)
  → INSERT device_actions (result='Pending', cmd_id=UUID)
  → publish iot/control
  → PendingCommandRegistry.register()  — hẹn giờ COMMAND_TIMEOUT_SECONDS
  → HTTP 202 trả về NGAY, không chờ thiết bị

  ├─ iot/feedback đúng hạn → resolve() → Success | Failed
  └─ hết giờ               → Timer     → Timeout
```

Điểm cần nhớ:
- **`mark_result()` chỉ ghi khi bản ghi còn `Pending`.** Nhờ vậy feedback đến muộn không ghi
  đè kết quả Timeout, dù hai thread chạy song song.
- **Kết quả Failed/Timeout không đổi trạng thái ON/OFF** hiển thị — giữ nguyên trạng thái cũ
  đúng như SRS §4.5.7.
- **Lệnh `STATUS`** (hỏi phần cứng lúc khởi động) không tạo bản ghi `device_actions` và không
  được đăng ký timeout.
- Mỗi lệnh chờ tốn một `threading.Timer` — chấp nhận được ở quy mô 3 thiết bị (xem OQ-17).

## ⚠️ Kiểm thử không được chạm hạ tầng thật

`tests/conftest.py` đặt `ENABLE_MQTT=false` **trước khi import `app.main`**, và có `assert`
chặn nếu cờ này bị bật.

Vì sao quan trọng: `TestClient(app)` chạy lifespan thật. Nếu để MQTT bật, **mỗi bài kiểm thử**
sẽ kết nối vào broker của môi trường phát triển, publish lệnh `STATUS`, và ghi dữ liệu cảm biến
nhận được vào PostgreSQL thật — đã từng gây ra 51 dòng trùng và làm ESP32 giả lập nghẽn.

## Ghi chú kỹ thuật

- **Cổng PostgreSQL là 5433**, không phải 5432 — tránh đụng PostgreSQL 14 cài sẵn qua Homebrew.
- **Dùng `bcrypt` trực tiếp, không dùng `passlib`.** passlib 1.7.4 không tương thích bcrypt 4.x
  (`module 'bcrypt' has no attribute '__about__'`) và đã ngừng bảo trì.
  bcrypt chỉ xử lý 72 byte đầu của mật khẩu — schema đăng ký sẽ giới hạn ở tầng API.
- **Khoá chính dùng `BigInteger().with_variant(Integer, "sqlite")`** để test chạy được trên
  SQLite trong bộ nhớ (SQLite không tự tăng với BIGINT). Trên PostgreSQL vẫn là `BIGSERIAL`.
- **`DB_ECHO`** tách riêng khỏi `DEBUG`. Bật `DB_ECHO=true` khi cần soi câu lệnh SQL.
- **`CORS_ORIGINS`** khai báo dạng chuỗi ngăn cách bởi dấu phẩy; `NoDecode` tắt cơ chế
  tự parse JSON của pydantic-settings để validator nhận được chuỗi thô.
- **WeasyPrint chưa chạy được** — thiếu thư viện hệ thống. Trước Giai đoạn 6 cần:
  ```bash
  brew install pango gdk-pixbuf libffi
  ```
  Package Python đã cài sẵn, chỉ thiếu native lib.
- **`DeviceStateCache` nằm trong RAM.** Restart server là mất trạng thái ON/OFF; Giai đoạn 4
  sẽ khôi phục bằng cách publish lệnh `STATUS` để thiết bị báo lại.
- **Gom nhóm cho biểu đồ làm phía Python**, không dùng `date_bin()` của PostgreSQL, để test
  chạy được trên SQLite. Số dòng đọc bị chặn ở `MAX_SERIES_ROWS = 20_000` (~9 giờ dữ liệu).
- **SQLite không lưu offset thời gian**, PostgreSQL (`TIMESTAMPTZ`) thì có. Code đọc timestamp
  phải chấp nhận cả hai — xem `sensor_service.get_series`.
- **Index `idx_sensor_lookup`** hiện chưa được planner chọn vì bảng seed quá nhỏ (864 dòng,
  cùng một `device_id`). Với dữ liệu thật (~51k dòng/ngày, nhiều thiết bị) index này sẽ có tác dụng.
- **`app/db/base_class.py` giữ `Base`, `app/db/base.py` gom model.** Tách ra để tránh import
  vòng (model import `Base`, còn `base.py` import model). `app/db/models/__init__.py` import
  cả ba model để SQLAlchemy phân giải được `relationship` khai báo bằng tên chuỗi.

## API đã có

| Method | Path | Auth |
|---|---|---|
| GET | `/health` | ✗ |
| POST | `/api/v1/auth/register` | ✗ |
| POST | `/api/v1/auth/login` | ✗ |
| GET | `/api/v1/auth/me` | ✓ |
| POST | `/api/v1/auth/logout` | ✓ |
| GET | `/api/v1/sensors` | ✓ |
| GET | `/api/v1/sensors/latest` | ✓ |
| GET | `/api/v1/sensors/series` | ✓ |
| GET | `/api/v1/devices` | ✓ |
| GET | `/api/v1/devices/{device_id}` | ✓ |
| POST | `/api/v1/devices/{device_id}/actions` | ✓ |
| GET | `/api/v1/device-actions` | ✓ |
| GET | `/api/v1/device-actions/{action_id}` | ✓ |
| GET | `/api/v1/system/status` | ✓ |
| WS | `/ws?token=<JWT>` | query token |

Đặc tả đầy đủ: [`../docs/03-API-SPEC.md`](../docs/03-API-SPEC.md) · thử trực tiếp tại `/docs`.

### Ghi chú về xác thực
- JWT mang `jti`; đăng xuất đưa `jti` vào `app/core/token_store.py` (in-memory).
  **Restart server thì danh sách thu hồi mất** — xem OQ-14.
- Đăng nhập sai email và sai mật khẩu trả cùng thông báo, và vẫn băm một lần khi không tìm
  thấy tài khoản, để thời gian phản hồi không tiết lộ email nào tồn tại.
- `require_admin` đã dựng sẵn trong `core/deps.py` nhưng **chưa dùng** — SRS không mô tả
  quyền khác biệt giữa USER và ADMIN (OQ-10).

## Trạng thái hệ thống và WebSocket

`GET /api/v1/system/status` trả bốn khối ESP / MQTT / API / database. Phép ping DB
`SELECT 1` nằm ở `services/status_service.py` và được dùng chung với `/health`.

WebSocket `/ws?token=<JWT>` từ chối token sai, hết hạn hoặc đã thu hồi bằng mã đóng `1008`.
Ba loại sự kiện được phát:

- `sensor`: sau khi handler đã commit dữ liệu cảm biến.
- `device_state`: sau feedback Success/Failed hoặc khi Timer chốt Timeout.
- `system_status`: mỗi 10 giây trong lifespan, chỉ khi `ENABLE_MQTT=true`.

Callback paho và `threading.Timer` không chạy trong event loop FastAPI. `app/ws/hub.py`
dùng `asyncio.run_coroutine_threadsafe`; nếu app chưa có loop thì bỏ qua an toàn. Hub tự loại
client gửi lỗi để một tab hỏng không ảnh hưởng thread nhận MQTT.

## Tiếp theo

Giai đoạn 6 — sinh và tải báo cáo PDF. Xem [`../docs/06-ROADMAP.md`](../docs/06-ROADMAP.md).
