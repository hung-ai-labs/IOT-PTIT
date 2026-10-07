# 00 — Tóm tắt SRS (nguồn: "Báo cáo SRS.md")

## 1. Mục tiêu hệ thống
1. Giám sát môi trường trong nhà gần thời gian thực: nhiệt độ, độ ẩm, cường độ ánh sáng.
2. Điều khiển từ xa: Đèn LED, Quạt, Điều hòa.
3. Lưu trữ và tra cứu dữ liệu lịch sử (cảm biến + thao tác điều khiển).
4. Hỗ trợ tự động hóa theo quy tắc điều kiện môi trường *(SRS §1.3 — mức "có thể", xem 07-OPEN-QUESTIONS)*.
5. Dashboard trực quan, thao tác đơn giản.

## 2. Bốn thành phần (SRS §1.4)
| Thành phần | Trách nhiệm |
|---|---|
| Người dùng | Xem dữ liệu cảm biến, điều khiển thiết bị, xem lịch sử, xuất PDF |
| Thiết bị IoT (ESP32/ESP8266) | Đọc sensor, publish MQTT, nhận lệnh, thực thi, gửi feedback |
| MQTT Broker | Trung gian 2 chiều giữa thiết bị và server |
| Web/API Server | Nhận & lưu dữ liệu, cung cấp API, publish lệnh, sinh PDF |

## 3. Danh sách chức năng (SRS §2) → mã hoá để truy vết

| Mã | Chức năng | SRS |
|---|---|---|
| **F01** | Đăng ký tài khoản | §3.2 Hình 3.1 (thiếu API trong §4.3 — xem OQ-02) |
| **F02** | Đăng nhập / Đăng xuất, cấp token | §2.1 |
| **F03** | Xem dữ liệu cảm biến (nhiệt độ, độ ẩm, ánh sáng, thời gian đo) | §2.2 |
| **F04** | Điều khiển thiết bị (LED / Quạt / Điều hòa) | §2.3 |
| **F05** | Xem lịch sử thao tác | §2.4 |
| **F06** | Xuất báo cáo PDF | §2.5, §2.12 |
| **F07** | Tự động lưu dữ liệu cảm biến vào DB | §2.6 |
| **F08** | Tự động lưu thao tác điều khiển vào DB | §2.7 |
| **F09** | Giám sát trạng thái hệ thống (ESP / MQTT / API / DB) | §2.8 |
| **F10** | Xem chi tiết thiết bị điều khiển (GPIO, topic, uptime…) | §2.9 |
| **F11** | Trạng thái xử lý lệnh: Pending / Success / Failed / Timeout | §2.10, §4.5.7 |
| **F12** | Tra cứu: search + filter + sort + phân trang (sensor & history) | §2.11 |
| **F13** | Chặn gửi lệnh khi ESP hoặc MQTT mất kết nối + hiển thị cảnh báo | §2.8 |
| **F14** | Hộp thoại xác nhận trước khi gửi lệnh | §3.2 Hình 3.9 |

## 4. Tám màn hình (SRS §3.2)

| # | Màn hình | Nội dung chính |
|---|---|---|
| S1 | Đăng ký | Hình 3.1 |
| S2 | Đăng nhập | Hình 3.2 |
| S3 | Tổng quan (Dashboard) | Trạng thái ESP32/MQTT/API/DB; 3 giá trị sensor; biểu đồ theo thời gian; khu điều khiển 3 thiết bị; hoạt động gần đây |
| S4 | Dữ liệu cảm biến | Bảng bản ghi + tìm kiếm/lọc theo thiết bị, loại cảm biến, khoảng thời gian |
| S5 | Điều khiển thiết bị | 3 card thiết bị: trạng thái kết nối, GPIO, lệnh gần nhất, công tắc ON/OFF |
| S6 | Lịch sử thao tác | Bảng: device_id, target, action, người thực hiện, result, thời gian + lọc |
| S7 | Tạo báo cáo | Chọn khoảng thời gian + thiết bị + nhóm dữ liệu → sinh PDF, xem trước/tải |
| S8 | Thông tin hệ thống | Sơ đồ chuỗi thành phần + trạng thái + thông tin MQTT |

Overlay/state bổ sung: dialog xác nhận (3.9), toast thành công (3.10), toast báo cáo xong (3.11), trạng thái "đang xử lý" (2.10).

## 5. Cơ sở dữ liệu (SRS §4.2)
3 bảng: `users`, `data_sensor`, `device_actions`. Chi tiết trong `02-DATABASE.md`.

## 6. API (SRS §4.3)
Base `/api/v1`, JSON, Bearer token. Chi tiết trong `03-API-SPEC.md`.

## 7. MQTT (SRS §4.3.8)
`iot/sensor`, `iot/control`, `iot/feedback`. Chi tiết trong `04-MQTT-CONTRACT.md`.

## 8. Chương 2 — Kiểm thử bằng Terminal
Dùng `mosquitto_pub` / `mosquitto_sub` giả lập 3 vai trò (Hardware / Software nhận / Software gửi lệnh).
Payload mẫu: `{"temp":20,"humid":80,"light":1000}`, `{"led1":"on","led2":"off"}`.
→ Sẽ tái hiện bằng `scripts/mock_device.py` và `scripts/terminal_demo.md`.
