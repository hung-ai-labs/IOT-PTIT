# Frontend — Smart IoT Dashboard

Giao diện Web Dashboard, viết bằng **HTML + CSS + JavaScript thuần** (không framework,
không build step) theo SRS §1.2. Thiết kế lấy từ Figma Make
`6LtIcdRDy3tlNe9mA0At2M` và viết lại sang HTML semantic + CSS tokens.

## Chạy thử

```bash
docker compose -f infra/docker-compose.yml up -d
cd backend && mvn spring-boot:run
```

Số liệu cảm biến và phản hồi điều khiển lấy từ ESP32 thật qua MQTT.
Không tự chạy trình giả lập hoặc nạp số liệu mẫu.

Mở http://localhost:8000/login.html

| Tài khoản | Mật khẩu | Vai trò |
|---|---|---|
| `admin@ptit.edu.vn` | `123456` | ADMIN |
| `user@ptit.edu.vn` | `123456` | USER |

> Spring Boot phục vụ luôn frontend tĩnh nên không cần server riêng.
> Chưa có tài khoản? Bấm **Đăng ký** trên trang đăng nhập — tài khoản mới lưu thẳng vào PostgreSQL.

## Cấu trúc

```
frontend/
├── login.html          S1 Đăng ký + S2 Đăng nhập (một trang, hai form)
├── index.html          S3 Tổng quan
├── sensors.html        S4 Dữ liệu cảm biến
├── devices.html        S5 Điều khiển thiết bị
├── history.html        S6 Lịch sử thao tác
├── reports.html        Chuyển về Tổng quan (trang đã gỡ)
├── system.html         Chuyển về Tổng quan (trang đã gỡ)
├── profile.html        Hồ sơ (có trong Figma, ngoài phạm vi SRS)
└── assets/
    ├── css/
    │   ├── tokens.css      ⚠️ Design tokens từ Figma — đổi giao diện chỉ sửa file này
    │   ├── fonts.css       @font-face trỏ vào assets/fonts (Inter, JetBrains Mono)
    │   ├── base.css        reset + typography + keyframes
    │   ├── layout.css      sidebar, header, khung trang
    │   ├── components.css  badge, switch, table, modal, toast, phân trang…
    │   └── pages.css       style riêng từng màn hình
    ├── js/
    │   ├── api.js       Điểm gọi API thật duy nhất; không có dữ liệu giả lập.
    │   ├── ws.js        WebSocket realtime + reconnect + polling fallback
    │   ├── store.js     State dùng chung giữa các trang (sessionStorage)
    │   ├── layout.js    Dựng sidebar + header + thanh DEMO cho mọi trang
    │   ├── ui.js        toast, modal, drawer, badge, switch, phân trang
    │   ├── auth.js      Chặn truy cập khi chưa đăng nhập
    │   ├── format.js    Định dạng ngày giờ, số, đơn vị, escapeHtml
    │   ├── icons.js     Icon SVG inline
    │                    (logic từng màn hình nằm trong file .html tương ứng)
    ├── fonts/           13 file .woff2
    └── vendor/          chart.umd.js (Chart.js 4.4.1)
```

## Trạng thái hiển thị hiện tại (07/10/2026)

`assets/js/config.js` đặt `SHOW_IOT_DATA = false` theo yêu cầu: các trang cảm biến,
điều khiển, lịch sử vẫn giữ bộ lọc, cột bảng, phân trang và công tắc; chưa hiển thị
số liệu, trạng thái đèn hay lịch sử. Không xoá database, không sinh dữ liệu mẫu.

Danh mục đèn vẫn lấy từ API; trạng thái và thời gian được để trống. WebSocket IoT
không được mở trong chế độ này, tránh làm số liệu xuất hiện trở lại. Công tắc vẫn
hiển thị nhưng chưa cho gửi lệnh khi trạng thái chưa được hiển thị.

Đặt `SHOW_IOT_DATA = true` khi sẵn sàng hiển thị dữ liệu thật; các API và WebSocket
hoạt động như trước. Xác thực và chỉnh sửa hồ sơ luôn dùng API thật.

## Nối với backend

Toàn bộ lời gọi dữ liệu đi qua `assets/js/api.js`.

Xác thực, cảm biến, thiết bị, lịch sử và trạng thái hệ thống đã dùng API thật.
Không còn nhánh mock trong frontend. Báo cáo và Thông tin hệ thống đã gỡ khỏi menu;
URL cũ chuyển về Tổng quan. API trạng thái hệ thống vẫn dùng cho header và khoá điều khiển.

Dashboard hiển thị `—` khi cảm biến chưa có giá trị và chỉ dựng biểu đồ khi loại cảm biến
đang chọn có dữ liệu. Bảng hoạt động gần đây vẫn giữ khung và thông báo trống khi chưa có lịch sử.
Không hiển thị chênh lệch tự tạo hoặc trạng thái API/Database cố định.

Ba thiết bị hiển thị là **Đèn đỏ, Đèn xanh, Đèn vàng**. Giữ mã MQTT để tương thích:
`led` → Đèn đỏ (GPIO 25), `fan` → Đèn xanh (GPIO 26), `ac` → Đèn vàng (GPIO 27).

⚠️ Vì gọi API thật, **phải chạy qua backend** ở `http://localhost:8000`, không dùng
`python -m http.server` nữa (server tĩnh không có `/api/v1`).

## Trạng thái ESP32 / MQTT

Lần tải đầu lấy từ `GET /api/v1/devices` và `GET /api/v1/system/status`. Sau đó header và
banner nhận `system_status` qua WebSocket mỗi 10 giây. Sau 3 lần WS lỗi, `store.js` bật lại
polling 10 giây; kết nối WS vẫn thử lại với backoff tối đa 30 giây.

**Thanh DEMO đã gỡ** — trước đây nó giả lập trạng thái, nay sẽ nói dối vì vòng poll ghi đè lại.
Muốn chụp cảnh mất kết nối cho báo cáo: tắt `scripts/mock_device.py` rồi đợi 30 giây.

## Bảng màu

Giao diện đang dùng **nền sáng, chữ tối**. Toàn bộ màu nằm trong
`assets/css/tokens.css` — đổi bảng màu chỉ cần sửa khối `:root` của file đó,
không đụng tới file nào khác.

Màu ngữ nghĩa dùng tông 600/700 (ví dụ `--color-primary: #2563EB` thay vì
`#3B82F6`) để chữ đạt tương phản WCAG AA trên nền trắng. Nếu đổi sang nền tối
thì nhớ trả về tông 400/500, vì tông 600 trên nền tối sẽ bị chìm.

Biểu đồ Chart.js không đọc được CSS variable, nên khối script trong `index.html` có hàm
`readThemeColors()` đọc giá trị đã tính từ `tokens.css` lúc khởi tạo. Nhờ vậy
biểu đồ tự đổi màu theo bảng màu mà không phải sửa JS.

## Ảnh đại diện

`assets/img/avatar.jpg` (320×320, ~13KB) — ảnh thật của chủ dự án. Dựng bằng
`avatar(fullName, size)` trong `ui.js`, dùng ở 3 chỗ: header, thẻ người dùng ở
sidebar, và trang Hồ sơ.

Ảnh đè lên chữ cái đầu; nếu ảnh không tải được thì `onerror` xoá thẻ `<img>` và
chữ cái đầu hiện lại. Vậy nên xoá file ảnh đi giao diện vẫn chạy bình thường.

⚠️ Bảng `users` chưa có cột ảnh đại diện, nên **mọi tài khoản đăng nhập đều hiện
chung một ảnh này**. Muốn mỗi người một ảnh thì phải thêm cột `avatar_url` và
sửa `avatar()` đọc theo người dùng.

## Khung trang và cuộn

Trang cuộn bằng **thanh cuộn của chính trình duyệt**: `.app` dùng `min-height: 100vh`,
không dùng `height: 100vh + overflow: hidden`.

Đừng quay lại kiểu "app shell" khoá chiều cao rồi cho một `div` bên trong cuộn. Kiểu đó
làm phím Space / Page Up / Page Down / Home / End mất tác dụng (vì cửa sổ không cuộn,
còn `div` bên trong thì không có focus), và thanh cuộn của `div` dễ bị làm mảnh tới mức
người dùng không nhận ra khu vực đó cuộn được.

- `.app` giới hạn chiều rộng bằng `--app-max-width`, căn giữa để có khoảng trống hai bên trên màn rộng.
- `.sidebar` và `.header` dùng `position: sticky; top: 0` để đứng yên khi cuộn.
- ⚠️ `base.css` phải để `html, body { min-height: 100% }`, **không** phải `height: 100%`.
  Để `height` thì `body` bị khoá đúng một màn hình trong khi `.app` cao bằng nội dung —
  `position: sticky` tính sai vùng neo và Safari cho header/sidebar trôi mất khi cuộn.
  Chrome bỏ qua lỗi này nên thử trên Chrome sẽ không thấy.
- Dưới 900px `.sidebar` thành ngăn kéo trượt (`position: fixed`), mở bằng nút
  `#sidebarToggle` trên header và đóng bằng lớp phủ `#sidebarBackdrop` hoặc phím Escape.

## Quy ước khi sửa giao diện

- **Không hardcode màu / khoảng cách.** Mọi giá trị đi qua biến trong `tokens.css`.
- Khoảng cách làm tròn về thang `--space-*` (4px).
- Mỗi bảng/danh sách phải có đủ 4 trạng thái: loading · empty · error · có dữ liệu.
- Mỗi nút gửi lệnh phải có: idle · confirming · processing · success · failed.
- Không dùng CDN — thư viện và font đã vendor vào `assets/`.

## Đã kiểm tra

| Màn hình | Trạng thái |
|---|---|
| S1 Đăng ký | ✅ **API thật** — tạo tài khoản trong PostgreSQL, báo lỗi email trùng, tự điền email khi quay về đăng nhập |
| S2 Đăng nhập | ✅ **API thật** — JWT, đăng nhập đúng/sai, hiện/ẩn mật khẩu, spinner |
| Hồ sơ | ✅ **API thật** — `GET /auth/me` + `PATCH /auth/me`; chỉnh sửa họ tên, mã sinh viên, trường, email liên hệ; lưu hoặc hủy |
| Đăng xuất | ✅ **API thật** — thu hồi token phía server |
| S3 Tổng quan | ✅ **Realtime** — tải dữ liệu đầu bằng REST, sau đó cập nhật thẻ + biểu đồ qua sự kiện `sensor` |
| S4 Dữ liệu cảm biến | ✅ **API thật** — lọc/sắp xếp/phân trang **phía server**, drawer chi tiết, trạng thái rỗng |
| S5 Điều khiển | ✅ **Realtime** — chi tiết → xác nhận → nhận `device_state` → Success/Failed/Timeout + toast |
| S6 Lịch sử | ✅ **API thật** — lọc **phía server**, hiện lý do lỗi dưới badge kết quả |
| S7 Báo cáo | Đã gỡ theo yêu cầu ngày 07/10/2026 |
| S8 Thông tin hệ thống | Đã gỡ theo yêu cầu ngày 07/10/2026 |
| ESP32/MQTT offline | ✅ banner cảnh báo + khoá công tắc + header đổi màu |

## Khác biệt so với thiết kế Figma

**1. Đăng nhập bằng email.** Form đăng nhập/đăng ký dùng **email** thay cho *tên đăng nhập*
và **bỏ ô số điện thoại**, vì bảng `users` trong SRS §4.2.1 không có cột `username` lẫn `phone`.
Chi tiết: `docs/07-OPEN-QUESTIONS.md` OQ-13.

**2. Đã gỡ thanh DEMO** dưới header (OQ-16).

**3. Bảng dữ liệu cảm biến không gộp 3 cột.** Figma gộp Nhiệt độ · Độ ẩm · Ánh sáng vào cùng
một dòng; hiện tại mỗi dòng là một phép đo với cột **Loại** và **Giá trị** riêng — đúng
SRS §2.6, và nhờ vậy bộ lọc "loại cảm biến" mới hoạt động. Chi tiết: OQ-15.

## Realtime và fallback

- `ws.js` giữ một kết nối cho mỗi trang và tự đóng khi rời trang.
- Dashboard không gọi lại `/sensors/*` khi WS hoạt động; sự kiện mới được nối trực tiếp vào chart.
- `waitForAction()` đợi `device_state`, không poll `/device-actions/{id}` trên đường chính.
- Sau 3 lần WS lỗi, các vòng polling cũ mới chạy; khi reconnect thành công chúng tự dừng.

Responsive < 900px mới ở mức cơ bản (SRS không yêu cầu mobile).

## Tài nguyên dự án

Trang hồ sơ có mục GitHub, Figma, Project Docs và API Document. Các liên kết nằm trong
`PROJECT_RESOURCES` ở `assets/js/config.js`. Figma đã được cập nhật bằng URL người dùng cung cấp ngày 07/10/2026. Thông tin cá nhân nằm ngay dưới Lịch sử thao tác trong menu.

## Sửa giao diện bằng HTML trực tiếp

- **Đèn:** thêm `<option value="orange">Đèn cam</option>` trong `<template id="deviceOptionsTemplate">`
  đầu `index.html`. Dashboard, trang điều khiển và bộ lọc lịch sử dùng chung danh sách này.
  Mỗi value phải khác nhau. Đèn chỉ có ở frontend giữ trạng thái trống và công tắc khoá.
- **Thanh tìm kiếm cảm biến:** sửa `<template id="sensorFiltersTemplate">` đầu `sensors.html`.
  Mỗi `<option>` của `#fieldFilter` là một phạm vi tìm kiếm — giá trị phải nằm trong
  `SensorService.FIELDS` phía backend, nếu không API trả 422.
- **Thanh tìm kiếm lịch sử:** sửa `<template id="historyFiltersTemplate">` đầu `history.html`.
  Ô `#searchInput` gửi thẳng tham số `q`; backend nhận cả nhãn tiếng Việt lẫn mã gốc
  (`Đèn đỏ` ↔ `red`, `Bật` ↔ `ON`, `Thành công` ↔ `Success`).
- **Thông tin cá nhân:** thêm `<div data-label="Căn cước công dân">Chưa cập nhật</div>` vào
  `<template id="profileFieldsTemplate">` đầu `profile.html`. Các trường `data-field` hiện có
  lấy giá trị từ tài khoản, bốn trường có `data-edit` vẫn chỉnh sửa/lưu qua API.

Lưu HTML và tải lại trình duyệt, không cần khởi động lại Java khi chạy với frontend ngoài JAR.
Các dòng mới thêm dùng để hiển thị. Muốn trường mới được lưu vào tài khoản, bộ lọc mới truy vấn
được dữ liệu thật hoặc đèn mới điều khiển thật thì cần nối thêm backend tương ứng.
Không tạo số liệu cảm biến hoặc lịch sử mẫu.
