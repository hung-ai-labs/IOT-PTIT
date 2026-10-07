# Prompt cho Codex — Giai đoạn 5

> Copy toàn bộ nội dung dưới dòng kẻ này và dán vào Codex.

---

Bạn đang làm việc trong repo `IOT-PTIT` — đồ án môn IoT của sinh viên PTIT:
hệ thống giám sát và điều khiển thiết bị IoT qua MQTT.

## Đọc trước khi code (bắt buộc, theo đúng thứ tự)

1. `CLAUDE.md` — quy ước bắt buộc của dự án
2. `docs/06-ROADMAP.md` — mục **Giai đoạn 5** là việc bạn phải làm
3. `docs/03-API-SPEC.md` §7 và §8 — đặc tả `/system/status` và WebSocket
4. `docs/01-ARCHITECTURE.md` §2 — các thành phần chạy nền trong backend
5. `backend/README.md` — cách chạy, cách test, các bẫy đã biết
6. `frontend/README.md` — cách frontend gọi API

**Không được tự ý đổi stack.** Backend là FastAPI + SQLAlchemy sync + PostgreSQL,
frontend là HTML/CSS/JavaScript thuần (ES modules, không framework, không build step).
Đây là đồ án có tài liệu SRS dùng để chấm điểm.

## Trạng thái hiện tại

Giai đoạn 0–4 đã xong và **đang chạy được**:

| Đã có | Vị trí |
|---|---|
| Xác thực JWT | `backend/app/api/v1/auth.py`, `core/security.py`, `core/deps.py` |
| MQTT client | `backend/app/mqtt/client.py` (paho, chạy thread riêng) |
| Xử lý bản tin MQTT | `backend/app/mqtt/handlers.py` |
| Cache trạng thái thiết bị | `backend/app/state/device_cache.py` (thread-safe) |
| Vòng đời lệnh điều khiển | `backend/app/mqtt/registry.py` (threading.Timer) |
| API cảm biến | `backend/app/api/v1/sensors.py` |
| API thiết bị + lịch sử | `backend/app/api/v1/devices.py`, `device_actions.py` |
| ESP32 giả lập | `scripts/mock_device.py` |
| 89 test | `backend/tests/` — **tất cả đang pass, không được làm hỏng** |

Frontend đã nối API thật cho: đăng nhập, cảm biến, thiết bị, lịch sử.
Chỉ còn `USE_MOCK = { system: true, reports: true }` trong `frontend/assets/js/api.js`.

## Việc cần làm — Giai đoạn 5

### A. `GET /api/v1/system/status` (F09)

Tạo `backend/app/services/status_service.py` và `backend/app/api/v1/system.py`.

Response phải khớp `docs/03-API-SPEC.md` §7:

```json
{
  "esp": { "status": "online", "device_id": "ESP32-01",
           "last_seen": "2026-09-09T10:12:03Z", "ip": "192.168.1.20",
           "rssi": -58, "uptime": 3600 },
  "mqtt": { "status": "connected", "broker": "localhost:1883",
            "topics": ["iot/sensor","iot/control","iot/feedback","iot/status"],
            "messages_received": 1234 },
  "api": { "status": "running", "version": "1.0.0", "uptime_seconds": 3600 },
  "database": { "status": "connected", "latency_ms": 3 }
}
```

Nguồn dữ liệu — **dùng lại thứ đã có, đừng viết lại**:
- `esp` ← `app.state.device_cache.device_cache` (có sẵn `online`, `last_seen`, `ip`, `rssi`, `uptime`)
- `mqtt` ← `app.mqtt.client.mqtt_service` (có sẵn `.connected`, `.messages_received`)
  và `app.mqtt.topics`
- `api` ← `settings.app_version` + biến `STARTED_AT` trong `app/main.py`
- `database` ← ping `SELECT 1` như hàm `health()` trong `app/main.py` đang làm

**Cần khử trùng lặp:** logic ping DB hiện nằm trong `health()` ở `app/main.py`.
Chuyển nó vào `status_service` rồi để `/health` gọi lại, đừng copy-paste hai bản.

Endpoint yêu cầu Bearer token, giống mọi endpoint nghiệp vụ khác.

### B. WebSocket `/ws` (đẩy sự kiện thay cho polling)

Tạo `backend/app/ws/hub.py` với lớp `WebSocketHub`: `connect`, `disconnect`, `broadcast`.
Tạo endpoint WebSocket `/ws?token=<JWT>`.

Ba loại sự kiện, đúng như `docs/03-API-SPEC.md` §8:

```json
{"type":"sensor",        "data":{"device_id":"ESP32-01","temperature":27.5,"humidity":68,"light":420,"timestamp":"..."}}
{"type":"device_state",  "data":{"device_id":"ESP32-01","target":"fan","state":"ON","action_id":12,"result":"Success"}}
{"type":"system_status", "data":{ ...giống GET /system/status... }}
```

- `sensor` — phát khi `handle_sensor_message` ghi xong dữ liệu
- `device_state` — phát khi `handle_feedback_message` chốt kết quả, **và** khi
  `PendingCommandRegistry` đánh Timeout (cả hai đều phải phát, đừng bỏ sót nhánh timeout)
- `system_status` — phát định kỳ (10 giây/lần) từ một task nền trong `lifespan`

#### ⚠️ Điểm khó nhất của giai đoạn này — đọc kỹ

`handle_sensor_message`, `handle_feedback_message` và callback timeout **chạy trong thread
của paho-mqtt / threading.Timer, KHÔNG phải event loop của FastAPI**. Gọi coroutine trực
tiếp từ đó sẽ không chạy.

Cách làm đúng:
1. Trong `lifespan`, lưu event loop đang chạy: `asyncio.get_running_loop()`
2. Từ thread khác, phát sự kiện bằng `asyncio.run_coroutine_threadsafe(coro, loop)`
3. Bọc trong try/except — **một client WebSocket lỗi không được làm chết thread nhận MQTT**
4. Khi chưa có loop (ví dụ lúc chạy test), hàm phát sự kiện phải im lặng bỏ qua, không ném lỗi

#### Xác thực WebSocket

Trình duyệt **không đặt được header** cho WebSocket, nên token đi qua query string
`?token=<JWT>`. Tái sử dụng `decode_access_token` và kiểm tra `token_store.is_revoked()`
trong `app/core/`. Token sai/hết hạn/đã thu hồi → đóng kết nối với mã `1008` (policy violation).

### C. Frontend

1. Tạo `frontend/assets/js/ws.js` — client WebSocket:
   - tự kết nối lại khi rớt, backoff tăng dần (1s → tối đa 30s)
   - API kiểu đăng ký: `onMessage(type, handler)`
   - `close()` khi rời trang
2. Thay ba chỗ đang polling:
   - `pages/dashboard.js:329` — `POLL_INTERVAL = 5000` (cảm biến + biểu đồ)
   - `layout.js:183` — `setInterval(refreshStatus, STATUS_POLL_INTERVAL)` (trạng thái ESP/MQTT)
   - `api.js` → `waitForAction()` (poll kết quả lệnh mỗi 0,5 giây)
   **Giữ polling làm phương án dự phòng**: nếu WebSocket không kết nối được sau 3 lần thử,
   quay lại polling như hiện tại. Đừng xoá hẳn đường polling.
3. `pages/system.js` — dùng `GET /system/status` thật thay cho `mock.systemInfo`
4. `api.js` — bỏ `system` khỏi `USE_MOCK`, **xoá luôn nhánh mock** (đừng để nhánh chết)
5. Sau khi xong, `frontend/assets/js/mock.js` chỉ còn phục vụ `reports`;
   nếu không còn gì thì xoá file và bỏ dòng `import * as mock`

## Quy ước bắt buộc

- **Code, tên biến, tên hàm: tiếng Anh. Comment và chuỗi hiển thị: tiếng Việt có dấu.**
- Comment giải thích **tại sao**, không mô tả lại code đang làm gì.
- Backend: router mỏng, service dày. Router chỉ validate rồi gọi service.
- Mọi endpoint mới phải có Pydantic schema request/response rõ ràng.
- Lỗi trả về đúng định dạng chung: `{"detail": {"code": "...", "message": "..."}}` (tiếng Việt).
- Frontend: mọi màu/spacing/font đi qua biến trong `assets/css/tokens.css`. **Không hardcode.**
- Frontend: mọi lời gọi dữ liệu đi qua `assets/js/api.js`, không `fetch` rải rác trong trang.
- Không thêm thư viện mới. Không thêm CDN — font và Chart.js đã vendor trong `assets/`.

## Bẫy đã biết — đừng dẫm lại

1. **`ENABLE_MQTT=false` khi chạy test.** `tests/conftest.py` đã đặt sẵn và có `assert` chặn.
   Lý do: `TestClient(app)` chạy lifespan thật; nếu bật MQTT, mỗi bài test sẽ kết nối vào
   broker thật và ghi dữ liệu vào PostgreSQL thật. Lỗi này từng tạo 51 dòng trùng.
   **Task nền phát `system_status` cũng phải tôn trọng cờ này.**
2. **Tham số thời gian phải URL-encode.** Dấu `+` trong offset `+07:00` chưa encode sẽ thành
   dấu cách và API trả 422. Frontend dùng `URLSearchParams` (đã có hàm `query()` trong `api.js`).
3. **SQLite (dùng trong test) không lưu offset timezone**, PostgreSQL thì có. Code đọc
   timestamp phải chấp nhận cả hai — xem `sensor_service.get_series` làm mẫu.
4. **`threading.Event` dùng làm cờ dừng, không phải cờ chạy.** `wait()` trả về ngay khi
   Event đã set.
5. **PostgreSQL ở cổng 5433**, không phải 5432.

## Cách chạy và kiểm chứng

```bash
# Hạ tầng
docker compose -f infra/docker-compose.yml up -d

# Backend (phục vụ luôn frontend tĩnh)
cd backend && .venv/bin/uvicorn app.main:app --reload --port 8000

# ESP32 giả lập, terminal khác
cd backend && .venv/bin/python ../scripts/mock_device.py

# Test
cd backend && .venv/bin/python -m pytest tests -q
```

Mở http://localhost:8000 — đăng nhập `admin@ptit.edu.vn` / `123456`.

## Định nghĩa "xong"

- [ ] `GET /api/v1/system/status` trả đủ 4 khối `esp` / `mqtt` / `api` / `database`
- [ ] `/health` và `/system/status` **dùng chung** một hàm ping DB, không copy-paste
- [ ] WebSocket `/ws` từ chối token sai, hết hạn và đã thu hồi (mã đóng 1008)
- [ ] Mở Dashboard, chạy `mock_device.py` → số liệu và biểu đồ **tự đổi mà không có
      request HTTP nào** trong tab Network (trừ lần tải đầu)
- [ ] Bấm công tắc → nhận sự kiện `device_state`, không còn poll `/device-actions/{id}`
- [ ] Tắt `mock_device.py` → sau 30 giây, header và banner đổi sang offline nhờ sự kiện
      `system_status`, không cần tải lại trang
- [ ] Ngắt backend giữa chừng → frontend tự kết nối lại khi backend chạy lại
- [ ] Trang S8 Thông tin hệ thống hiển thị dữ liệu thật
- [ ] `USE_MOCK.system` đã bỏ và nhánh mock đã xoá
- [ ] **89 test cũ vẫn pass**, cộng thêm test mới cho `/system/status` và `WebSocketHub`
- [ ] Không có lỗi trong console trình duyệt

## Sau khi code xong, cập nhật tài liệu

Đây là yêu cầu bắt buộc của dự án, không phải việc phụ:

- `docs/06-ROADMAP.md` — đánh dấu Giai đoạn 5 hoàn thành, ghi rõ đã làm gì
- `docs/03-API-SPEC.md` §7, §8 — sửa cho khớp code thật (đánh dấu "✅ Đã hiện thực")
- `docs/07-OPEN-QUESTIONS.md` — thêm mục mới nếu bạn phải tự quyết điều gì mà tài liệu
  chưa nói rõ, hoặc phải lệch khỏi thiết kế Figma / SRS. Ghi rõ lý do và phương án thay thế.
- `backend/README.md` — bổ sung endpoint mới và ghi chú kỹ thuật về WebSocket
- `frontend/README.md` — cập nhật bảng trạng thái các màn hình
- `CLAUDE.md` — cập nhật bảng tiến độ

## Báo cáo lại

Khi xong, nói rõ:
- Những gì bạn **đã tự kiểm chứng bằng cách chạy thật** (không phải suy đoán)
- Những quyết định bạn phải tự đưa ra và lý do
- Những gì **chưa làm được** hoặc còn hạn chế — nói thẳng, đừng giấu
