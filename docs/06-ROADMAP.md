# 06 — Lộ trình triển khai

Thứ tự này cho phép chạy end-to-end sớm (không cần chờ ESP32 thật, không cần chờ Figma).
Đánh dấu `[x]` khi xong.

---

## Giai đoạn 0 — Hạ tầng & khung dự án  ✅ XONG (09/09/2026)
- [x] Cấu trúc thư mục theo `01-ARCHITECTURE.md` §4, §5
- [x] `infra/docker-compose.yml`: PostgreSQL 16 (cổng **5433**) + Mosquitto 2 + `mosquitto.conf`
- [x] `backend/requirements.txt` (dùng **bcrypt trực tiếp**, không dùng passlib — xem `backend/README.md`)
- [x] `app/core/config.py` (Settings + DEVICE_REGISTRY + SENSOR_UNITS/RANGES) + `.env.example`
- [x] `app/mqtt/topics.py` — hằng số topic
- [x] `app/main.py`: `GET /health` trả 200, `/docs` mở được, phục vụ luôn frontend tĩnh
- [x] `.gitignore`
- [x] `git init` — nhánh `main`, remote `https://github.com/hung-ai-labs/IOT-PTIT` (07/10/2026)

## Giai đoạn 1 — Database  ✅ XONG (09/09/2026)
- [x] 3 model SQLAlchemy theo `02-DATABASE.md` (`user.py`, `sensor.py`, `device_action.py`)
- [x] `app/core/security.py` — bcrypt + JWT
- [x] Alembic init + migration `056c8b671af8` + `upgrade head` (đã kiểm tra `alembic check`, không drift)
- [x] `scripts/seed.py`: 2 tài khoản, 864 bản ghi cảm biến (24h), 40 bản ghi lịch sử
- [x] Kiểm tra index bằng `EXPLAIN` — index đã tạo đúng; ở quy mô seed planner còn chọn
      `idx_sensor_time`, sẽ dùng `idx_sensor_lookup` khi dữ liệu lớn
- [x] 11 test pass (`tests/test_health.py`, `test_security.py`, `test_models.py`)

## Giai đoạn 2 — Xác thực (F01, F02)  ✅ XONG (09/09/2026)
- [x] `core/security.py`: bcrypt hash/verify, JWT có `jti` để thu hồi
- [x] `core/token_store.py`: danh sách token đã thu hồi (in-memory, tự dọn khi hết hạn)
- [x] `schemas/auth.py`, `schemas/common.py`
- [x] `POST /auth/register`, `POST /auth/login`, `GET /auth/me`, `POST /auth/logout`
- [x] `core/deps.py`: `get_current_user`, `require_admin` (dựng sẵn, chưa dùng — OQ-10)
- [x] Chuẩn hoá lỗi 422 về cùng định dạng `{"detail": {"code", "message"}}`
- [x] 13 test auth (đăng ký/đăng nhập đúng-sai, email trùng, chuẩn hoá email,
      token hỏng, thu hồi khi đăng xuất, không ảnh hưởng phiên khác) — tổng **24 test pass**
- [x] **Frontend đã nối API thật**: `login.html`, `auth-page.js`, `layout.js`, `profile.js`

## Giai đoạn 3 — MQTT + thu thập dữ liệu (F03, F07)  ✅ XONG (09/09/2026)
- [x] `mqtt/client.py`: kết nối trong lifespan, auto-reconnect backoff 1→30s, subscribe 4 topic
      (+ 2 topic cũ của SRS Chương 2 khi bật `MQTT_LEGACY_TOPICS`)
- [x] `schemas/mqtt.py`: Pydantic kiểm tra mọi bản tin trước khi ghi DB
- [x] `mqtt/handlers.py`: validate payload → ghi 1 dòng `data_sensor` cho mỗi loại cảm biến,
      bỏ qua giá trị ngoài biên nhưng vẫn giữ các giá trị hợp lệ trong cùng bản tin
- [x] `state/device_cache.py`: `DeviceStateCache` thread-safe + `last_seen` từ `iot/status` & `iot/sensor`,
      xử lý Last Will
- [x] `scripts/mock_device.py`: publish sensor 5s/lần, heartbeat 10s, LWT, nhận `iot/control`
      và trả `iot/feedback`; cờ `--fail-rate` và `--timeout-rate`
- [x] `services/sensor_service.py` + `GET /sensors/latest`, `GET /sensors`, `GET /sensors/series`
- [x] `/health` báo thêm trạng thái MQTT và số bản tin đã nhận
- [x] 34 test mới (14 handler + 20 API) — tổng **58 test pass**
- [x] **Frontend đã nối API thật**: `USE_MOCK.sensors = false`; Dashboard poll 5 giây,
      trang Dữ liệu cảm biến lọc/sắp xếp/phân trang phía server
- [x] Kiểm thử terminal theo `04-MQTT-CONTRACT.md` §5 — bản tin xấu bị chặn, topic cũ vẫn nhận

## Giai đoạn 4 — Điều khiển thiết bị (F04, F08, F10, F11, F13)  ✅ XONG (09/09/2026)
- [x] `DEVICE_REGISTRY` trong config (led/fan/ac + GPIO + tên hiển thị)
- [x] `services/action_service.py` — tầng DB dùng chung cho router, handler và registry
- [x] `mqtt/registry.py` — `PendingCommandRegistry` dùng `threading.Timer`, timeout 5s
- [x] `services/control_service.py` — nghiệp vụ gửi lệnh và đọc trạng thái
- [x] `POST /devices/{device_id}/actions` (202 + Pending), `GET /devices`, `GET /devices/{id}`
- [x] Handler `iot/feedback` → chốt result + cập nhật cache; phản hồi đến muộn **không** ghi đè Timeout
- [x] Timer timeout → `result='Timeout'` kèm `error_msg`
- [x] Chặn khi MQTT down (503) / ESP offline (409) / lệnh đang chạy (409)
- [x] `GET /device-actions` và `GET /device-actions/{id}` *(kéo từ GĐ5 lên để frontend dùng được ngay)*
- [x] Khôi phục trạng thái ON/OFF khi khởi động lại + publish lệnh `STATUS` hỏi phần cứng
- [x] **31 test mới** — Success, Failed, Timeout, DeviceOffline, MQTT down, lệnh trùng,
      publish lỗi, phản hồi lạ, phản hồi muộn — tổng **89 test pass**
- [x] **Frontend đã nối API thật**: `USE_MOCK` chỉ còn `system` và `reports`;
      đã **gỡ thanh DEMO** vì trạng thái ESP/MQTT nay là thật

## Giai đoạn 5 — Lịch sử & trạng thái hệ thống (F05, F09, F12)  ✅ XONG (09/09/2026)
- [x] `GET /device-actions` với đầy đủ filter/sort/phân trang *(đã làm ở GĐ4)*
- [x] `GET /system/status` có đủ ESP / MQTT / API / DB; `/health` dùng chung hàm ping DB
- [x] WebSocket `/ws?token=<JWT>` xác thực token và đóng `1008` khi sai/hết hạn/thu hồi
- [x] `WebSocketHub` broadcast `sensor` / `device_state` / `system_status`; MQTT và Timer
      chuyển coroutine sang event loop bằng `asyncio.run_coroutine_threadsafe`
- [x] Frontend realtime cho Dashboard, header, trang thiết bị và S8; polling chỉ bật sau
      3 lần WebSocket lỗi, client vẫn tự reconnect với backoff 1→30 giây
- [x] 12 test mới cho status, hub, xác thực WS và đủ ba nhánh phát sự kiện — tổng **101 test pass**

## Giai đoạn 6 — Báo cáo PDF (F06)
- [ ] `templates/report.html` (bìa, thông tin kỳ báo cáo, bảng sensor tóm tắt, bảng lịch sử, biểu đồ ảnh)
- [ ] `report_service.py`: truy vấn → tổng hợp (min/max/avg) → WeasyPrint → lưu file
- [ ] `POST /reports/pdf`, `GET /reports/{id}/download`, `GET /reports/{id}/preview`
- [ ] Kiểm tra tiếng Việt có dấu hiển thị đúng trong PDF (nhúng font Noto Sans / DejaVu)

## Giai đoạn 7 — Frontend khung  ✅ XONG
- [x] `tokens.css` (đã lấy trực tiếp từ Figma, không cần bản tạm)
- [x] `base.css`, `layout.css`, `components.css`, `pages.css`, `fonts.css`
- [x] `api.js`, `auth.js`, `ui.js`, `format.js`, `store.js`, `layout.js`, `icons.js`
- [x] 8 file HTML + 8 file JS trang, layout chung dựng bằng `layout.js`
- [x] Chạy được end-to-end với dữ liệu giả (`mock.js`, cờ `USE_MOCK` trong `api.js`)
- [x] `ws.js` — WebSocket + reconnect backoff + polling fallback (GĐ5)
- [x] Bỏ `USE_MOCK.system`; chỉ còn `reports` chờ GĐ6

## Giai đoạn 8 — Áp giao diện Figma  ✅ XONG (09/09/2026)
> Nguồn: Figma Make `6LtIcdRDy3tlNe9mA0At2M` (prototype React) → viết lại sang vanilla JS.
- [x] Bước 1: trích design tokens → `frontend/assets/css/tokens.css`
- [x] Bước 2: layout khung (sidebar + header + thanh DEMO) khớp Figma
- [x] Bước 3: component (badge, switch, toast, modal, drawer, bảng, phân trang…)
- [x] Bước 4: 8 màn hình + màn Hồ sơ
- [x] Bước 5: loading / empty / error / processing state
- [x] Vendor Inter + JetBrains Mono + Chart.js vào `assets/` (không phụ thuộc CDN)
- [x] Kiểm tra trực quan từng màn trên trình duyệt

## Giai đoạn 9 — Firmware ESP32/ESP8266
- [ ] Sketch: WiFi + MQTT (PubSubClient) + LWT + heartbeat 10s
- [ ] Đọc DHT22 (nhiệt độ, độ ẩm) + LDR/BH1750 (ánh sáng), publish `iot/sensor` 5s/lần
- [ ] Subscribe `iot/control`, điều khiển GPIO cho LED / Quạt (relay) / Điều hòa (relay hoặc IR)
- [ ] Publish `iot/feedback` kèm `cmd_id`
- [ ] `firmware/README.md`: sơ đồ nối chân + thư viện + cách nạp

## Giai đoạn 10 — Hoàn thiện & bàn giao
- [ ] Test tự động: pytest cho auth, sensors, control (mock MQTT)
- [ ] `README.md`: mô tả, kiến trúc, hướng dẫn cài đặt & chạy, ảnh chụp màn hình
- [ ] Rà đối chiếu F01–F14 với SRS, ghi bảng truy vết yêu cầu → mã nguồn
- [ ] Chụp màn hình cho báo cáo (Hình 2.1–2.3 terminal, Hình 3.1–3.11 giao diện)
- [ ] Kiểm tra bảo mật cơ bản: không lộ secret, không SQL injection, mật khẩu đã hash, CORS đúng

---

## Đường găng khuyến nghị
`GĐ0 → GĐ1 → GĐ2 → GĐ3 → GĐ4` là phần cốt lõi. Sau GĐ4 hệ thống đã "chạy được" với mock device.
GĐ7 có thể làm song song. GĐ9 (phần cứng) độc lập, làm khi có linh kiện.
GĐ8 chờ Figma — không chặn bất cứ giai đoạn nào khác.
