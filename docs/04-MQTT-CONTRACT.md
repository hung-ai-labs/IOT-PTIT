# 04 — Hợp đồng MQTT

## 1. Chọn bộ topic

SRS có **hai** bộ topic khác nhau:
- §4.3.8: `iot/sensor`, `iot/control`, `iot/feedback`
- Chương 2 (kiểm thử terminal): `Sensor_data`, `Device_control`, `device_response`

👉 **Chọn bộ §4.3.8 làm chuẩn chính thức** (thuộc phần thiết kế hệ thống, đặt tên nhất quán,
chữ thường, có namespace). Bộ Chương 2 chỉ là tên tạm khi test terminal.
Để bài kiểm thử Chương 2 vẫn chạy đúng, backend subscribe **cả hai** qua cấu hình
`MQTT_LEGACY_TOPICS=true` (mặc định bật trong dev, tắt khi nộp). Xem OQ-01.

| Topic | Chiều | Người publish | Người subscribe | QoS |
|---|---|---|---|---|
| `iot/sensor` | ESP → Server | ESP32 | FastAPI | 1 |
| `iot/control` | Server → ESP | FastAPI | ESP32 | 1 |
| `iot/feedback` | ESP → Server | ESP32 | FastAPI | 1 |
| `iot/status` ➕ | ESP → Server | ESP32 (LWT + heartbeat) | FastAPI | 1, retain |

## 2. Payload

### 2.1 `iot/sensor`
```json
{
  "device_id": "esp32-01",
  "temp": 27.5,
  "humid": 68.2,
  "light": 420,
  "ts": "2026-09-09T10:12:03Z"
}
```
- Giữ tên `temp/humid/light` để tương thích payload trong SRS Chương 2.
- `ts` tuỳ chọn; thiếu thì server dùng thời điểm nhận.
- Server tách thành 3 bản ghi `data_sensor` (temperature/°C, humidity/%, light/lux).
- Validate biên: temp −40..85, humid 0..100, light 0..100000. Ngoài biên → bỏ qua + log warning.

### 2.2 `iot/control`
```json
{
  "cmd_id": "3f1a...uuid",
  "device_id": "esp32-01",
  "target": "fan",
  "action": "ON",
  "issued_at": "2026-09-09T10:12:05Z"
}
```
- Tên hiển thị (07/10/2026): `led` = Đèn đỏ, `fan` = Đèn xanh, `ac` = Đèn vàng; giữ mã MQTT cũ để tương thích.
- `target`: `led` | `fan` | `ac` · `action`: `ON` | `OFF` | `STATUS`
- `STATUS` = yêu cầu ESP báo lại trạng thái hiện tại (dùng khi server khởi động lại).

### 2.3 `iot/feedback`
```json
{
  "cmd_id": "3f1a...uuid",
  "device_id": "esp32-01",
  "target": "fan",
  "state": "ON",
  "result": "Success",
  "error": null,
  "ts": "2026-09-09T10:12:05Z"
}
```
- `result`: `Success` | `Failed`. **Không bao giờ là `Timeout`** — `Timeout` do server tự đặt.
- Feedback không có `cmd_id` khớp (ví dụ ESP tự đổi trạng thái) → vẫn cập nhật `DeviceStateCache`,
  ghi `device_actions` với `issued_by = NULL`.

### 2.4 `iot/status` (heartbeat + Last Will)
```json
{ "device_id": "esp32-01", "status": "online", "ip": "192.168.1.20", "rssi": -58, "uptime": 3600 }
```
- ESP đặt LWT: topic `iot/status`, payload `{"device_id":"esp32-01","status":"offline"}`, retain = true.
- Heartbeat mỗi 10s. Server coi ESP **offline** khi `now - last_seen > 30s`.

## 3. Timeout & vòng đời lệnh

```
POST /devices/{id}/actions
  → INSERT device_actions (result='Pending', cmd_id=UUID)
  → publish iot/control
  → registry.register(cmd_id, timeout=5s)
  → HTTP 202 trả về ngay

  ├─ nhận iot/feedback trong 5s → UPDATE result='Success'|'Failed', responded_at=now
  │                             → cache.set(target, state) → WS broadcast device_state
  └─ quá 5s                     → UPDATE result='Timeout'  → WS broadcast device_state (giữ state cũ)
```
Hằng số cấu hình: `COMMAND_TIMEOUT_SECONDS=5`, `DEVICE_OFFLINE_SECONDS=30`, `HEARTBEAT_SECONDS=10`.

## 4. Cấu hình client backend
- Thư viện: `paho-mqtt` chạy trong thread riêng + `asyncio.run_coroutine_threadsafe`
  (hoặc `gmqtt` thuần async — quyết định ở OQ-05).
- `client_id = f"fastapi-{uuid4().hex[:8]}"`, `clean_session=False`, auto-reconnect backoff 1→30s.
- Xác thực broker: username/password trong `.env` (`MQTT_USERNAME`, `MQTT_PASSWORD`).
  Dev có thể `allow_anonymous true` trong `mosquitto.conf`.

## 5. Kiểm thử bằng Terminal (tái hiện SRS Chương 2)

```bash
# T2 — nghe dữ liệu cảm biến
mosquitto_sub -h localhost -p 1883 -t "iot/sensor" -v

# T1 — giả lập Hardware gửi dữ liệu
mosquitto_pub -h localhost -p 1883 -t "iot/sensor" \
  -m '{"device_id":"esp32-01","temp":20,"humid":80,"light":1000}'

# T1 — nghe lệnh điều khiển
mosquitto_sub -h localhost -p 1883 -t "iot/control" -v

# T3 — gửi lệnh
mosquitto_pub -h localhost -p 1883 -t "iot/control" \
  -m '{"cmd_id":"test-1","device_id":"esp32-01","target":"led","action":"ON"}'

# T1 — Hardware phản hồi
mosquitto_pub -h localhost -p 1883 -t "iot/feedback" \
  -m '{"cmd_id":"test-1","device_id":"esp32-01","target":"led","state":"ON","result":"Success"}'
```

`scripts/mock_device.py` tự động hoá toàn bộ luồng trên (publish sensor định kỳ,
subscribe control, trả feedback sau độ trễ ngẫu nhiên 0.2–1s, có cờ `--fail-rate` để test Failed/Timeout).
