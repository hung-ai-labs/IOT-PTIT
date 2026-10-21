# 03 — Đặc tả API (`/api/v1`)

Backend hiện tại: Spring Boot (07/10/2026), giữ đường dẫn và JSON của FastAPI cũ. Xem [08-SPRING-BOOT-MIGRATION.md](08-SPRING-BOOT-MIGRATION.md).

Bám sát SRS §4.3. Mục ➕ là bổ sung cần thiết (không mâu thuẫn SRS).

## 1. Quy ước chung
- Base URL: `/api/v1` · Content-Type `application/json` (trừ tải PDF).
- Xác thực: `Authorization: Bearer <JWT>`. Token HS256, hạn 8 giờ.
- Lỗi trả về thống nhất:
  ```json
  { "detail": { "code": "DEVICE_OFFLINE", "message": "Thiết bị esp32-01 đang mất kết nối." } }
  ```
- Phân trang: query `page` (từ 1), `size` (mặc định 20, tối đa 100). Response:
  ```json
  { "items": [...], "page": 1, "size": 20, "total": 1234, "total_pages": 62 }
  ```
- Sắp xếp: `sort=<field>:<asc|desc>`, ví dụ `sort=timestamp:desc`.
- Thời gian trong query: ISO-8601, ví dụ `from=2026-09-01T00:00:00Z`.

## 2. Xác thực (SRS §4.3.2)

> ✅ **Đã hiện thực** (Giai đoạn 2) — mô tả dưới đây khớp với mã nguồn thực tế.

| Method | Path | Auth | Mô tả |
|---|---|---|---|
| POST | `/auth/register` ➕ | ✗ | Đăng ký (màn hình S1, SRS Hình 3.1). Body: `full_name` (2–100), `email`, `password` (6–72). Vai trò luôn là `USER`. → `201` trả `UserOut` |
| POST | `/auth/login` | ✗ | Body: `email`, `password`. → `{access_token, token_type:"bearer", expires_in, user}` |
| GET | `/auth/me` | ✓ | Thông tin user hiện tại |
| PATCH | `/auth/me` ➕ | ✓ | Cập nhật hồ sơ của chính mình: `full_name` (2–100), `student_id` (≤30 hoặc null), `school` (≤200 hoặc null), `contact_email` (email hoặc null). Không sửa email đăng nhập hoặc vai trò. |
| POST | `/auth/logout` | ✓ | Thu hồi token hiện tại (theo `jti`) → `204` |

`UserOut` = `{id, full_name, email, student_id, school, contact_email, role, created_at}` — **không bao giờ** trả `password_hash`.

Lỗi: `401 INVALID_CREDENTIALS` · `401 UNAUTHORIZED` · `409 EMAIL_EXISTS` · `422 VALIDATION_ERROR`.

**Chi tiết hiện thực:**
- Email được chuẩn hoá (cắt khoảng trắng + chữ thường) trước khi lưu và khi đăng nhập.
- Đăng nhập sai email và sai mật khẩu trả **cùng một** thông báo, và vẫn băm một lần khi
  không tìm thấy tài khoản, để thời gian phản hồi không tiết lộ email nào tồn tại.
- JWT mang `jti`; đăng xuất đưa `jti` vào danh sách thu hồi trong bộ nhớ. Các phiên đăng nhập
  khác của cùng người dùng **không** bị ảnh hưởng. Danh sách mất khi restart server —
  chấp nhận được vì token chỉ sống 8 giờ (`ACCESS_TOKEN_EXPIRE_HOURS`).
- Mật khẩu giới hạn 72 byte vì đó là giới hạn của bcrypt.

⚠️ **Đăng nhập bằng email, không phải tên đăng nhập.** SRS §2.1 nói "tên đăng nhập hoặc email"
nhưng bảng `users` (SRS §4.2.1) không có cột `username` — xem `07-OPEN-QUESTIONS.md` OQ-13.

## 3. Dữ liệu cảm biến (SRS §4.3.3)

> ✅ **Đã hiện thực** (Giai đoạn 3). Tất cả đều yêu cầu Bearer token.

| Method | Path | Mô tả |
|---|---|---|
| GET | `/sensors/latest` | Giá trị mới nhất mỗi loại. Query: `device_id`. → `{device_id, temperature:{value,unit,timestamp}, humidity, light}` — loại chưa có dữ liệu trả `null` |
| GET | `/sensors` | Tra cứu lịch sử, có phân trang. Query: `device_id, sensor_type, q, field, from, to, page, size, sort` |
| GET | `/sensors/series` ➕ | Dữ liệu cho biểu đồ Dashboard. Query: `device_id, from, to, bucket=1m\|5m\|1h, points` |

**`GET /sensors`** trả `Page[SensorRecordOut]`:
```json
{ "items": [ {"id":3000,"device_id":"ESP32-01","sensor_type":"light",
              "value":235.0,"unit":"lux","timestamp":"2026-09-09T08:47:01+07:00"} ],
  "page": 1, "size": 20, "total": 1269, "total_pages": 64 }
```
Mỗi bản ghi là **một phép đo của một loại cảm biến** — đúng SRS §2.6 (ID · Mã thiết bị ·
Loại cảm biến · Giá trị · Đơn vị · Thời gian). Xem OQ-15 về khác biệt với prototype Figma.

- `sensor_type`: `temperature` | `humidity` | `light` (sai giá trị → 422)
- `sort`: `<trường>:<asc|desc>`, trường hợp lệ `id, device_id, sensor_type, value, timestamp`
- `size`: 1–100 (mặc định 20) · `page`: từ 1
- `q`: ô tìm kiếm tự do của màn S4. Người dùng gõ **đúng chuỗi họ nhìn thấy trên bảng**,
  nên server so khớp trên bản đã định dạng theo giờ `Asia/Ho_Chi_Minh`
  (`DD/MM/YYYY HH24:MI:SS`) — gõ `16:25`, `07/10/2026` hay `07/10/2026 16:25` đều ra kết quả.
- `field`: phạm vi của `q` — bỏ trống (tìm cả thời gian, giá trị và `device_id`), `time`,
  hoặc một loại cảm biến. Chọn một loại cảm biến vừa lọc `sensor_type`, vừa đổi ý nghĩa
  của `q` thành "giá trị đo". Giá trị lạ → 422.

**`GET /sensors/series`** trả mảng điểm đã gom nhóm, tránh đổ hàng chục nghìn điểm vào Chart.js:
```json
[ {"time":"08:41","timestamp":"2026-09-09T01:41:00Z","temp":26.4,"humidity":61.5,"light":232.5} ]
```
`points` (5–200, mặc định 30) là số cột tối đa. Gom nhóm thực hiện phía Python để chạy được
trên cả PostgreSQL lẫn SQLite; số dòng đọc bị chặn ở 20.000.

⚠️ **Tham số `from`/`to` phải được URL-encode.** Chuỗi ISO có offset `+07:00` — dấu `+` chưa
encode sẽ bị hiểu thành dấu cách và API trả 422. Dùng `URLSearchParams` (JS) hoặc `params=`
(httpx) thay vì ghép chuỗi tay.

## 4. Điều khiển thiết bị (SRS §4.3.4)

> ✅ **Đã hiện thực** (Giai đoạn 4). Tất cả đều yêu cầu Bearer token.

| Method | Path | Mô tả |
|---|---|---|
| GET | `/devices` | Danh sách 3 thiết bị chấp hành + trạng thái |
| GET | `/devices/{device_id}/targets/{target}` | Chi tiết đúng một đèn trên ESP (F10) |
| POST | `/devices/{device_id}/actions` | Gửi lệnh. Body `{target, action}` → **202** |

`GET /devices` trả mảng:
```json
[{"device_id":"ESP32-01","target":"green","name":"Đèn xanh","gpio":"GPIO 26","icon":"💡",
  "state":"ON","connection":"online",
  "last_command":"2026-09-09T09:15:47+07:00","last_seen":"2026-09-09T09:16:01+07:00"}]
```

`GET /devices/ESP32-01/targets/red` trả một đối tượng đèn đỏ với các trường
giống một phần tử của danh sách, bổ sung `ip`, `rssi`, `uptime`, `command_topic`,
`feedback_topic`; không có mảng `targets`. Target nhận `red`, `green`, `yellow`;
target không tồn tại trả **404 TARGET_NOT_FOUND**. ESP chưa được ghi nhận trả
`offline`, metadata kết nối có thể `null`, như API danh sách.

Đường dẫn cũ `GET /devices/{device_id}` chỉ giữ để tương thích, trả thông tin ESP
kèm `targets`; không hiển thị trong Swagger và frontend không còn gọi đường dẫn này.

`POST /devices/{device_id}/actions` → **202 Accepted**, **không chờ thiết bị**:
```json
{"action_id":127,"cmd_id":"3f1a…","device_id":"ESP32-01",
 "target":"green","action":"OFF","result":"Pending","timeout_seconds":5.0}
```

Điều kiện chặn (F13) — kiểm tra **trước** khi ghi bản ghi nào:
| Tình huống | Mã HTTP | `code` |
|---|---|---|
| MQTT chưa kết nối | `503` | `MQTT_UNAVAILABLE` |
| ESP `last_seen` > 30s | `409` | `DEVICE_OFFLINE` |
| Đang có lệnh Pending cho cùng `target` | `409` | `COMMAND_IN_PROGRESS` |
| Publish MQTT thất bại | `503` | `MQTT_UNAVAILABLE` (bản ghi được chốt `Failed`, không treo Pending) |

## 5. Lịch sử thao tác (SRS §4.3.5)

> ✅ **Đã hiện thực** (làm sớm ở Giai đoạn 4).

| Method | Path | Mô tả |
|---|---|---|
| GET | `/device-actions` | Query: `device_id, target, action, result, q, from, to, page, size, sort` |

- `q`: chỉ tìm theo thời gian hiển thị tại Việt Nam, ví dụ `16:53`, `16:53:49`
  hoặc `07/10/2026 16:53`. Thiết bị, hành động và kết quả lọc riêng qua
  `target`, `action`, `result`.
| GET | `/device-actions/{action_id}` ➕ | Trạng thái một lệnh — frontend poll trong lúc chờ |

Trả `Page[DeviceActionOut]`; mỗi item:
```json
{"id":127,"device_id":"ESP32-01","target":"green","target_label":"Đèn xanh","action":"OFF",
 "issued_by":{"id":5,"full_name":"Nguyễn Xuân Hùng"},"result":"Success",
 "timestamp":"…","responded_at":"…","error_msg":null}
```
`issued_by` là `null` khi thiết bị tự đổi trạng thái (feedback không kèm `cmd_id`).

### Vòng đời một lệnh (F11)

```
Pending ──── iot/feedback đúng hạn ───→ Success | Failed
        └─── quá COMMAND_TIMEOUT_SECONDS ───→ Timeout
```

- Phản hồi **đến muộn không ghi đè** kết quả Timeout đã chốt (`mark_result` chỉ đổi khi
  bản ghi còn ở `Pending`).
- Kết quả `Failed` hoặc `Timeout` **không** làm đổi trạng thái ON/OFF hiển thị.
- Lệnh `STATUS` (server hỏi thiết bị lúc khởi động) **không** tạo bản ghi `device_actions`.

## 6. Báo cáo (SRS §4.3.6)

| Method | Path | Mô tả |
|---|---|---|
| POST | `/reports/pdf` | Body: `{from, to, device_id, sections:["temperature","humidity","light","actions"]}` → `{report_id, filename, size_bytes, download_url, preview_url, generated_at}` |
| GET | `/reports/{report_id}/download` ➕ | Trả `application/pdf` (`Content-Disposition: attachment`) |
| GET | `/reports/{report_id}/preview` ➕ | Trả `application/pdf` inline (cho `<iframe>` xem trước, Hình 3.11) |

## 7. Trạng thái hệ thống (SRS §4.3.7)

> ✅ **Đã hiện thực** (Giai đoạn 5). Yêu cầu Bearer token.

`GET /system/status` →
```json
{
  "esp": { "status": "online", "device_id": "ESP32-01", "last_seen": "2026-09-09T10:12:03Z",
           "ip": "192.168.1.20", "rssi": -58, "uptime": 3600 },
  "mqtt": { "status": "connected", "broker": "localhost:1883",
            "topics": ["iot/sensor","iot/control","iot/feedback","iot/status"],
            "messages_received": 1234 },
  "api": { "status": "running", "version": "1.0.0", "uptime_seconds": 3600 },
  "database": { "status": "connected", "latency_ms": 3 }
}
```
Trạng thái: ESP `online|offline` · MQTT & DB `connected|disconnected` · API `running|unavailable`.
Phép ping `SELECT 1` nằm trong `status_service.check_database()` và được dùng chung bởi
`/health`, `/system/status` và sự kiện WebSocket định kỳ.

## 8. WebSocket ➕ (`/ws`)

> ✅ **Đã hiện thực** (Giai đoạn 5).

Không có trong SRS nhưng cần cho yêu cầu "gần thời gian thực" (§1.3). Có polling fallback.
Kết nối: `ws://host/ws?token=<JWT>`. Server đẩy:

```json
{"type":"sensor",       "data":{"device_id":"esp32-01","temperature":27.5,"humidity":68,"light":420,"timestamp":"..."}}
{"type":"device_state", "data":{"device_id":"esp32-01","target":"green","state":"ON","action_id":12,"result":"Success"}}
{"type":"system_status","data":{ ... giống §7 ... }}
```

- Token sai, hết hạn hoặc đã thu hồi: server chấp nhận handshake rồi đóng mã `1008`.
- `sensor` phát sau khi dữ liệu đã commit; `device_state` phát khi feedback chốt kết quả
  và khi Timer chốt `Timeout`; `system_status` phát mỗi 10 giây.
- Handler MQTT và Timer chạy ngoài event loop, nên dùng `asyncio.run_coroutine_threadsafe`.
  Khi app chưa có loop (như test đơn vị), sự kiện được bỏ qua an toàn.
- Frontend thử lại với backoff 1→30 giây. Sau 3 lần lỗi, polling cũ được bật làm fallback;
  WebSocket vẫn tiếp tục thử lại và tự tắt polling ngay khi kết nối thành công.

## 9. Mã HTTP (SRS §4.3.9)
`200` OK · `201` Created · `202` Accepted (lệnh đã tiếp nhận) · `400` sai dữ liệu ·
`401` chưa xác thực · `404` không tìm thấy · `409` xung đột trạng thái ·
`422` validation · `500` lỗi server · `503` dịch vụ phụ thuộc không khả dụng.
