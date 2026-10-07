# 05 — Kế hoạch Frontend & quy trình lấy giao diện từ Figma

## 1. Nguyên tắc
- **HTML/CSS/JS thuần** theo SRS §1.2 (không React/Vue). Xem OQ-03 nếu muốn đổi.
- Mỗi màn hình = 1 file `.html` chứa cả markup lẫn logic (thẻ `<script type="module">`
  ở cuối `<body>`), import các module dùng chung từ `assets/js/`.
- Layout dùng chung: sidebar trái + topbar (SRS §3.1 "cùng một bố cục điều hướng").
- **Toàn bộ giá trị thị giác đi qua CSS variables** trong `assets/css/tokens.css`.
  Đây là điểm nối duy nhất với Figma — đổi design chỉ sửa 1 file.

## 2. Bản đồ màn hình

| File | Màn hình SRS | Route | Auth |
|---|---|---|---|
| `login.html` | S1 – Đăng ký (Hình 3.1) **và** S2 – Đăng nhập (Hình 3.2) — hai form trong một trang, đúng như prototype Figma | `/login.html` | ✗ |
| `index.html` | S3 – Tổng quan (Hình 3.3) | `/` | ✓ |
| `sensors.html` | S4 – Dữ liệu cảm biến (Hình 3.4) | `/sensors.html` | ✓ |
| `devices.html` | S5 – Điều khiển thiết bị (Hình 3.5) | `/devices.html` | ✓ |
| `history.html` | S6 – Lịch sử thao tác (Hình 3.6) | `/history.html` | ✓ |
| `reports.html` | S7 – Tạo báo cáo (Hình 3.7) | `/reports.html` | ✓ |
| `system.html` | S8 – Thông tin hệ thống (Hình 3.8) | `/system.html` | ✓ |
| `profile.html` | Hồ sơ — có trong prototype Figma, ngoài phạm vi SRS | `/profile.html` | ✓ |

## 3. Chi tiết từng màn hình

### S3 — Tổng quan
- Hàng status: 4 badge ESP32 / MQTT Broker / Web-API Server / Database → `GET /system/status` (poll 10s).
- 3 stat card: Nhiệt độ, Độ ẩm, Ánh sáng → `GET /sensors/latest`, cập nhật realtime qua WS.
- Biểu đồ đường theo thời gian → `GET /sensors/series?bucket=1m`, đẩy điểm mới từ WS.
- Khu điều khiển 3 thiết bị (switch) → dùng chung component với S5.
- "Hoạt động gần đây" → `GET /device-actions?size=5&sort=timestamp:desc`.

### S4 — Dữ liệu cảm biến
- Thanh lọc: thiết bị (select), loại cảm biến (select), từ ngày/giờ, đến ngày/giờ, ô tìm kiếm.
- Bảng: ID · Thiết bị · Loại · Giá trị · Đơn vị · Thời gian. Header click để sort.
- Phân trang dưới bảng. Trạng thái rỗng + trạng thái loading (skeleton).

### S5 — Điều khiển thiết bị
- 3 card: Đèn LED / Quạt / Điều hòa. Mỗi card: tên, mã ESP, GPIO, badge kết nối,
  lệnh gần nhất, switch ON/OFF, MQTT command/feedback topic (F10).
- Bấm switch → **modal xác nhận** (F14) → gọi API → switch chuyển sang trạng thái
  *đang xử lý* (spinner, disabled) → chờ WS → toast + đổi trạng thái, hoặc toast lỗi + hoàn nguyên.
- Nếu ESP offline / MQTT disconnected → switch disabled + banner cảnh báo (F13).

### S6 — Lịch sử thao tác
- Lọc: thiết bị, đối tượng, hành động ON/OFF, kết quả, khoảng thời gian.
- Bảng: Mã thiết bị · Đối tượng · Hành động · Người thực hiện · Kết quả (badge màu) · Thời gian.
- Badge: Pending (xám) · Success (xanh) · Failed (đỏ) · Timeout (cam).

### S7 — Tạo báo cáo
- Form: khoảng thời gian (preset 24h / 7 ngày / 30 ngày / tuỳ chọn), thiết bị,
  checkbox nhóm dữ liệu (Nhiệt độ / Độ ẩm / Ánh sáng / Lịch sử điều khiển).
- Nút "Tạo báo cáo" → trạng thái đang xử lý → khi xong: toast (Hình 3.11)
  + `<iframe>` xem trước + nút Tải xuống.

### S8 — Thông tin hệ thống
- Sơ đồ chuỗi Sensors → ESP32 → MQTT → API → DB → Dashboard → User (SVG tĩnh, node đổi màu theo trạng thái).
- Bảng thông tin MQTT: broker host/port, các topic, trạng thái kết nối, số message đã nhận.

## 4. Component dùng chung (`components.css` + `ui.js`)
`btn` (primary/secondary/danger) · `card` · `stat-card` · `badge` (success/danger/warning/neutral) ·
`switch` (có state *processing*) · `table` (sortable, empty, loading) · `pagination` ·
`modal` (confirm) · `toast` (success/error/info) · `filter-bar` · `date-range-picker` · `sidebar` · `topbar`

## 5. Quy trình lấy giao diện từ Figma  ✅ ĐÃ THỰC HIỆN (09/09/2026)

> **Đã hoàn thành.** Nguồn: Figma Make `6LtIcdRDy3tlNe9mA0At2M` — file này là
> prototype React (không phải file design thường), nên đã đọc thẳng mã nguồn để lấy
> chính xác màu, spacing và bố cục, rồi **viết lại** sang HTML semantic + CSS tokens.
> Kết quả và hướng dẫn sửa: `frontend/README.md`.
> Phần bên dưới giữ lại làm quy trình tham chiếu khi cần cập nhật design.

**Bước 0 — chuẩn bị (người dùng làm):**
Gửi link Figma file, và nếu được thì tên các frame ứng với S1–S8 để tra cứu nhanh.

**Bước 1 — Trích design tokens (làm trước tiên, 1 lần):**
Đọc các style/variable trong Figma → ghi vào `frontend/assets/css/tokens.css`:
```css
:root {
  /* Màu */
  --color-bg, --color-surface, --color-border,
  --color-text, --color-text-muted,
  --color-primary, --color-primary-hover, --color-on-primary,
  --color-success, --color-danger, --color-warning, --color-info,
  /* Typography */
  --font-family-base, --font-size-{xs,sm,base,lg,xl,2xl}, --font-weight-{regular,medium,bold},
  --line-height-tight, --line-height-base,
  /* Spacing (thang 4px) */ --space-1 … --space-12,
  /* Bo góc & đổ bóng */ --radius-{sm,md,lg,full}, --shadow-{sm,md,lg},
  /* Layout */ --sidebar-width, --topbar-height, --container-max
}
```

**Bước 2 — Dựng layout khung** (`layout.css`): sidebar + topbar + vùng nội dung, khớp lưới Figma.

**Bước 3 — Dựng component** theo §4, so sánh trực tiếp với Figma từng cái.

**Bước 4 — Dựng từng trang** theo thứ tự: S2 → S1 → S3 → S5 → S4 → S6 → S7 → S8
(đăng nhập trước để có luồng chạy được, dashboard trước vì tái sử dụng nhiều component nhất).

**Bước 5 — Nối API**: thay dữ liệu tĩnh bằng `api.js`, thêm loading/empty/error state.

**Quy tắc khi lấy từ Figma:**
- ❌ Không copy nguyên code export của Figma (div lồng nhau, absolute position, class tự sinh).
- ✅ Viết lại HTML **semantic** (`<nav> <main> <table> <form> <button>`) + CSS dùng tokens.
- ✅ Ảnh/icon: export SVG vào `assets/img/`, ưu tiên inline SVG cho icon để đổi màu theo token.
- ✅ Font: nếu Figma dùng font Google, tải về `assets/fonts/` (bản nộp không nên phụ thuộc mạng).
- ✅ Mọi khoảng cách phải làm tròn về thang `--space-*`; không dùng px lẻ rải rác.
- ✅ Sau mỗi màn hình: kiểm tra responsive ≥1280px (chính), 768px (phụ) — SRS không yêu cầu mobile.

## 6. Trạng thái UI bắt buộc (đừng quên khi dựng)
Mỗi bảng/danh sách phải có: **loading** · **empty** · **error** · **có dữ liệu**.
Mỗi nút gửi lệnh phải có: **idle** · **confirming** · **processing** · **success** · **failed/timeout**.
