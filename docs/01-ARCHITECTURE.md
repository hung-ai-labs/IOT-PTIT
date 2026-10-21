# 01 — Kiến trúc & cấu trúc mã nguồn

> Cập nhật 07/10/2026: backend đã chuyển sang Spring Boot theo xác nhận của người dùng. Mục dưới giữ kế hoạch cũ để đối chiếu; xem [08-SPRING-BOOT-MIGRATION.md](08-SPRING-BOOT-MIGRATION.md) và [backend/README.md](../backend/README.md) để chạy và sửa code hiện tại.

## 1. Sơ đồ khối

```
┌──────────┐  I2C/ADC  ┌─────────────┐  MQTT   ┌───────────┐  MQTT   ┌──────────────┐
│ Sensors  │──────────▶│ ESP32/8266  │────────▶│ Mosquitto │────────▶│   FastAPI    │
│ DHT/LDR  │           │  firmware   │◀────────│  Broker   │◀────────│ (mqtt client)│
└──────────┘           └─────────────┘         └───────────┘         └──────┬───────┘
                              │  GPIO                                       │
                              ▼                                             │ SQLAlchemy
                       ┌──────────────┐                                     ▼
                       │ LED/Fan/AC   │                              ┌─────────────┐
                       └──────────────┘                              │ PostgreSQL  │
                                                                     └─────────────┘
                                                                            ▲
   ┌───────────────┐   REST /api/v1  +  WebSocket /ws                       │
   │ Web Dashboard │◀───────────────────────────────────────────────────────┘
   │ HTML/CSS/JS   │
   └───────────────┘
```

## 2. Tiến trình bên trong Backend

FastAPI chạy 1 process với các thành phần chạy song song trong `lifespan`:

| Thành phần | Vai trò |
|---|---|
| **HTTP router** | Phục vụ REST API + static frontend |
| **MQTT client** (asyncio task) | Subscribe `iot/sensor`, `iot/feedback`; publish `iot/control` |
| **PendingCommandRegistry** | `dict[cmd_id → asyncio.Future]`, khớp lệnh với feedback, áp timeout |
| **WebSocket Hub** | Broadcast sensor mới + đổi trạng thái thiết bị tới các tab đang mở |
| **DeviceStateCache** | Trạng thái ON/OFF + last_seen của từng thiết bị (in-memory, nguồn sự thật cho S3/S5) |
| **HealthChecker** | Ping DB + kiểm tra MQTT connected + last_seen ESP cho `GET /system/status` |

> Lưu ý: `DeviceStateCache` là in-memory nên restart server sẽ mất. Khi khởi động,
> khôi phục bằng bản ghi `device_actions` mới nhất có `result=Success` cho mỗi target,
> rồi publish `iot/control` với `action=STATUS` để ESP báo lại trạng thái thật.

## 3. Luồng chính

### 3.1 Thu thập dữ liệu cảm biến (F03, F07)
1. ESP đọc sensor mỗi `SENSOR_INTERVAL` (mặc định 5s).
2. ESP publish `iot/sensor` payload JSON.
3. Handler backend validate bằng Pydantic → ghi 3 dòng vào `data_sensor` (temperature / humidity / light).
4. Cập nhật `DeviceStateCache.last_seen`.
5. Broadcast qua WebSocket `{type:"sensor", ...}` → Dashboard cập nhật số + biểu đồ.
6. Trang S4 vẫn dùng REST + phân trang (không realtime).

### 3.2 Điều khiển thiết bị (F04, F08, F11)
1. User bật/tắt trên S3 hoặc S5 → hiện dialog xác nhận (F14).
2. `POST /api/v1/devices/{device_id}/actions` `{target, action}`.
3. Backend kiểm tra: MQTT connected? ESP online (`last_seen` < 30s)? Nếu không → **409 Conflict** (F13).
4. Tạo `cmd_id`, INSERT `device_actions` với `result='Pending'`.
5. Publish `iot/control`, đăng ký Future vào `PendingCommandRegistry` với timeout 5s.
6. Trả **202 Accepted** kèm `{action_id, cmd_id, result:"Pending"}` — **không chờ đồng bộ**.
7. Feedback về `iot/feedback` → resolve Future → UPDATE `result='Success'|'Failed'`, cập nhật cache, broadcast WS.
8. Hết 5s không có feedback → UPDATE `result='Timeout'`, broadcast WS.
9. Frontend nhận WS (hoặc poll `GET /device-actions/{id}` fallback) → đổi switch + toast.

### 3.3 Báo cáo PDF (F06)
Đồng bộ: `POST /reports/pdf` → truy vấn → render Jinja2 → WeasyPrint → lưu `storage/reports/{uuid}.pdf`
→ trả `{report_id, download_url, preview_url}`. `GET /reports/{id}/download` trả file.

## 4. Cấu trúc thư mục backend

```
backend/app/
├── main.py                  # create_app(), lifespan, CORS, StaticFiles, include_router
├── core/
│   ├── config.py            # Settings (pydantic-settings), đọc .env
│   ├── security.py          # hash/verify password, create/decode JWT
│   └── deps.py              # get_db, get_current_user
├── db/
│   ├── session.py           # engine, SessionLocal
│   └── models/
│       ├── user.py          # User
│       ├── sensor.py        # DataSensor
│       └── device_action.py # DeviceAction
├── schemas/
│   ├── auth.py  sensor.py  device.py  action.py  report.py  system.py  common.py
├── api/v1/
│   ├── router.py            # gộp các router con
│   ├── auth.py  sensors.py  devices.py  device_actions.py  reports.py  system.py
├── mqtt/
│   ├── client.py            # MqttService: connect, publish, subscribe loop
│   ├── handlers.py          # on_sensor_message, on_feedback_message
│   ├── registry.py          # PendingCommandRegistry
│   └── topics.py            # hằng số topic
├── services/
│   ├── sensor_service.py  control_service.py  report_service.py  status_service.py
├── ws/hub.py                # WebSocketHub: connect/disconnect/broadcast
├── state/device_cache.py    # DeviceStateCache
└── templates/report.html    # template PDF
```

## 5. Cấu trúc thư mục frontend

```
frontend/
├── login.html  register.html  index.html(dashboard)
├── sensors.html  devices.html  history.html  reports.html  system.html
└── assets/
    ├── css/
    │   ├── tokens.css       # ⚠️ ĐÍCH ĐẾN CỦA DESIGN TOKEN TỪ FIGMA
    │   ├── base.css         # reset + typography
    │   ├── layout.css       # sidebar + topbar + grid
    │   ├── components.css   # button, card, table, badge, switch, modal, toast
    │   └── pages/*.css
    ├── js/
    │   ├── api.js           # fetch wrapper + token + xử lý 401
    │   ├── auth.js          # guard trang, login/logout
    │   ├── ws.js            # WebSocket client + auto reconnect
    │   ├── ui.js            # toast, modal, badge helpers
    │   ├── format.js        # định dạng ngày giờ, số, đơn vị
    │       (logic từng màn hình nằm trong thẻ <script type="module"> của file .html)
    ├── vendor/chart.umd.js
    └── img/
```

## 6. Nguyên tắc thiết kế
- **Router mỏng, service dày**: router chỉ validate + gọi service.
- **Không I/O chặn trong async handler**: DB dùng session sync trong `run_in_threadpool`, hoặc chuyển hẳn sang `asyncpg` + `AsyncSession` (quyết định ở OQ-05).
- **Một nguồn sự thật cho trạng thái thiết bị**: `DeviceStateCache`, không đọc rải rác từ DB.
- **Frontend không tự suy diễn trạng thái**: sau khi bấm switch, chỉ đổi UI khi backend xác nhận.
