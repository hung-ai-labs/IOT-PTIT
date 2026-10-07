# 07 — Điểm chưa rõ trong SRS & phương án đề xuất

✅ = đã chốt với người dùng · 🟡 = đã chọn phương án mặc định, có thể đổi · 🔴 = cần hỏi trước khi quyết

**Không còn mục 🔴 nào đang mở.**

---

### OQ-01 🟡 — Hai bộ tên MQTT topic mâu thuẫn
SRS §4.3.8 dùng `iot/sensor`, `iot/control`, `iot/feedback`;
Chương 2 §2.1 dùng `Sensor_data`, `Device_control`, `device_response`.

**Chọn:** `iot/*` làm chuẩn (thuộc phần thiết kế, đặt tên nhất quán).
Backend subscribe thêm bộ cũ khi `MQTT_LEGACY_TOPICS=true` để bài kiểm thử Chương 2 vẫn tái hiện được.
*Nếu báo cáo đã in kèm ảnh chụp terminal dùng tên cũ, chỉ cần bật cờ này khi demo.*

### OQ-02 🟡 — Thiếu API đăng ký
Hình 3.1 có màn hình đăng ký nhưng §4.3.2 chỉ có login/me/logout.
**Chọn:** bổ sung `POST /api/v1/auth/register`. Không mâu thuẫn SRS, chỉ là chỗ thiếu.

### OQ-03 ✅ ĐÃ CHỐT (09/09/2026) — Frontend dùng vanilla JS
SRS §1.2 ghi rõ "HTML, CSS và JavaScript". Prototype Figma viết bằng React,
nhưng đã được **viết lại sang HTML/CSS/JS thuần**, không build step.
Đã hoàn thành — xem `frontend/README.md`.

### OQ-04 🟡 — Không có bảng `devices`
SRS chỉ định 3 bảng. Nhưng F10 cần lưu GPIO, topic, tên thiết bị.
**Chọn:** khai báo tĩnh trong `DEVICE_REGISTRY` (config), không thêm bảng → giữ đúng SRS §4.2.
*Đổi ý sau này thì thêm bảng `devices` là việc nhỏ.*

### OQ-05 🟡 — Async hay sync cho DB & MQTT?
**Chọn:** SQLAlchemy **sync** + `run_in_threadpool`, MQTT dùng `paho-mqtt` chạy thread riêng.
Lý do: đơn giản, ít bug, hiệu năng thừa đủ cho quy mô đồ án.
*Nếu muốn "chuẩn async" hơn: `asyncpg` + `AsyncSession` + `gmqtt`.*

### OQ-06 ✅ ĐÃ CHỐT (09/09/2026) — Chưa làm tự động hóa
SRS §1.3 nêu mục tiêu tự động điều khiển theo điều kiện môi trường nhưng không có
chức năng/API/bảng/màn hình nào cho nó. **Quyết định: không làm trong phiên bản này**,
ghi là hướng phát triển tương lai trong README.
*(Dashboard vẫn có banner cảnh báo nhiệt độ > 30°C kèm nút "Bật điều hòa" thủ công —
đây là gợi ý cho người dùng, không phải tự động hóa.)*

### OQ-07 🟡 — Realtime: WebSocket hay polling?
SRS chỉ mô tả "Web Dashboard gọi API để lấy dữ liệu" (polling), nhưng §1.3 yêu cầu "gần thời gian thực".
**Chọn:** WebSocket `/ws` làm chính. Sau 3 lần kết nối lỗi, frontend bật lại polling cũ;
WebSocket vẫn tiếp tục reconnect với backoff 1→30 giây và tắt polling khi kết nối lại.
Không phá vỡ SRS, chỉ tăng chất lượng.

### OQ-08 🟡 — Bao nhiêu thiết bị ESP?
SRS luôn nói số ít ("thiết bị ESP32"). **Chọn:** thiết kế hỗ trợ nhiều `device_id`
(API đều có tham số `device_id`) nhưng demo với **một** thiết bị `esp32-01`.

### OQ-09 ✅ ĐÃ CHỐT (09/09/2026) — Điều hòa dùng **Relay**
Điều khiển bằng relay đóng/ngắt nguồn (không dùng IR blaster).
Firmware GĐ9 chỉ cần `digitalWrite` trên chân GPIO 27 giống LED và Quạt —
cả ba thiết bị dùng chung một hàm điều khiển.

### OQ-10 🟡 — Vai trò ADMIN dùng để làm gì?
Bảng `users` có `role` nhưng SRS không mô tả quyền khác biệt.
**Chọn:** cùng quyền như USER trong bản này; chỉ dựng sẵn cột + dependency `require_admin`
để mở rộng sau. Nếu muốn phân quyền thật (ví dụ chỉ ADMIN được điều khiển), báo để bổ sung.

### OQ-11 🟡 — Timeout lệnh điều khiển bao lâu?
SRS nói "trong thời gian quy định" nhưng không cho con số.
**Chọn:** 5 giây (`COMMAND_TIMEOUT_SECONDS`), ESP offline sau 30 giây không heartbeat.

### OQ-12 🟡 — Lưu file PDF ở đâu, giữ bao lâu?
**Chọn:** `backend/storage/reports/{uuid}.pdf`, dọn file cũ hơn 7 ngày bằng script.
Không lưu metadata vào DB (giữ đúng 3 bảng của SRS) — dùng tên file làm `report_id`.

---

### OQ-13 🟡 — Đăng nhập bằng email, form Figma lại hỏi tên đăng nhập + số điện thoại
*(Phát sinh ở Giai đoạn 2, 09/09/2026)*

Ba nguồn nói ba kiểu:
- **SRS §2.1**: "Người dùng nhập **tên đăng nhập hoặc email** và mật khẩu".
- **SRS §4.2.1** (bảng `users`): chỉ có `full_name`, `email`, `password_hash`, `role`
  — **không có** cột `username`, cũng không có `phone`.
- **Prototype Figma**: form đăng nhập ghi "TÊN ĐĂNG NHẬP" (demo `nguyenxuanhung`),
  form đăng ký hỏi Họ tên · **Số điện thoại** · **Tên đăng nhập** · Mật khẩu.

**Đã chọn: đăng nhập bằng email**, vì đó là thứ duy nhất bảng `users` có và
việc đổi nhãn giao diện rẻ hơn nhiều so với việc sửa lược đồ CSDL trong SRS.

Thay đổi trên giao diện so với Figma:
| Figma | Hiện tại |
|---|---|
| Đăng nhập: TÊN ĐĂNG NHẬP | **EMAIL** (`type="email"`) |
| Đăng ký: Họ tên · SĐT · Tên đăng nhập · Mật khẩu | Họ tên · **Email** · Mật khẩu |
| Demo: `nguyenxuanhung / 123456` | `admin@ptit.edu.vn / 123456` |

**Nếu muốn giữ đúng form Figma** thì phải thêm cột `username` (unique) và `phone` vào bảng
`users` — tức là sửa SRS §4.2.1. Báo nếu bạn chọn hướng này, sửa mất khoảng 30 phút
(model + migration + schema + router + 2 ô input).

---

### OQ-14 🟡 — Danh sách token thu hồi lưu trong bộ nhớ
*(Phát sinh ở Giai đoạn 2)*

`app/core/token_store.py` giữ các `jti` đã đăng xuất trong một dict Python.
Hệ quả: **restart server thì token đã đăng xuất dùng lại được** cho tới khi hết hạn (8 giờ).

Chấp nhận được ở quy mô đồ án (một tiến trình, một máy). Nếu chạy nhiều worker
(`uvicorn --workers`) hoặc cần bền vững thì chuyển sang Redis.

---

### OQ-15 🟡 — Bảng dữ liệu cảm biến: một dòng mỗi phép đo, không gộp 3 cột
*(Phát sinh ở Giai đoạn 3, 09/09/2026)*

Prototype Figma hiển thị bảng đã gộp: mỗi dòng có sẵn 3 cột Nhiệt độ · Độ ẩm · Ánh sáng.
Nhưng bảng `data_sensor` lưu **mỗi phép đo một dòng riêng** (SRS §4.2.2), và SRS §2.6 ghi rõ
bản ghi gồm: *ID, Mã thiết bị, **Loại cảm biến**, **Giá trị**, **Đơn vị**, Thời gian*.

**Đã chọn: hiển thị đúng như SRS §2.6** — cột `Loại` và `Giá trị` riêng, thay vì gộp.

Lý do:
1. Khớp chính xác danh sách trường mà SRS §2.6 liệt kê.
2. Bộ lọc "loại cảm biến" (SRS §2.11, có sẵn trong thiết kế Figma) chỉ có nghĩa khi mỗi dòng
   thuộc về một loại. Ở prototype Figma bộ lọc này không làm gì cả.
3. Không phải gộp nhóm theo timestamp — vốn không đáng tin khi ba cảm biến gửi lệch nhau.

Phong cách hiển thị giữ nguyên (cùng component bảng, badge, màu theo loại), chỉ đổi cột.
Nếu muốn quay lại kiểu gộp, cần thêm một API riêng gộp theo timestamp — báo nếu bạn chọn hướng đó.

---

### OQ-16 🟡 — Đã gỡ thanh DEMO khỏi giao diện
*(Phát sinh ở Giai đoạn 4, 09/09/2026)*

Thanh nút `Normal / ESP32 Offline / MQTT Offline / Success Toast / Error Toast` dưới header
là giàn giáo dựng khi chưa có backend. Từ Giai đoạn 4, trạng thái ESP32 và MQTT lấy thật từ
server (`GET /devices`, `GET /health` ở GĐ4; `/system/status` + WebSocket từ GĐ5), nên các
nút này sẽ **nói dối**: bấm "ESP32 Offline" thì lần cập nhật thật tiếp theo ghi đè thành online.

**Đã gỡ toàn bộ thanh DEMO.** Muốn chụp màn hình cảnh mất kết nối cho báo cáo thì tắt
trình giả lập (`Ctrl+C` ở `scripts/mock_device.py`), đợi 30 giây — trung thực hơn hẳn.

---

### OQ-17 🟡 — Timeout dùng `threading.Timer`, phát WebSocket qua event loop
*(Phát sinh ở Giai đoạn 4)*

Lệnh có thể được chốt bởi **thread của paho-mqtt** (khi feedback về) hoặc bởi **thread của
Timer** (khi hết giờ). Phần cập nhật DB vẫn chạy đồng bộ trong các thread này. Từ GĐ5,
cả hai phải phát sự kiện WebSocket nên event loop FastAPI được lưu trong `lifespan`, rồi
coroutine được chuyển sang loop bằng `asyncio.run_coroutine_threadsafe`.

Đánh đổi: mỗi lệnh đang chờ tốn một thread. Với quy mô đồ án (tối đa 3 lệnh đồng thời) thì
không đáng kể. Nếu sau này có hàng trăm thiết bị, nên chuyển sang một vòng lặp asyncio duy nhất.

Chống tranh chấp: `action_service.mark_result()` **chỉ cập nhật khi bản ghi còn ở `Pending`**,
nên feedback và timeout không thể ghi đè nhau dù chạy song song.

Nếu app chưa có event loop (ví dụ gọi handler trực tiếp trong test), cầu phát sự kiện im lặng
bỏ qua. Một client WebSocket lỗi cũng bị hub loại riêng, không làm chết thread MQTT/Timer.
