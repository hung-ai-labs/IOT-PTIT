# Backend — Smart IoT (Spring Boot)

Backend chính đã chuyển từ FastAPI sang **Spring Boot 3.5.16 / Java 17** theo xác nhận
ngày 07/10/2026. REST API, MQTT, WebSocket và PostgreSQL giữ hợp đồng dữ liệu cũ.

## Cấu trúc

```text
backend/
├── pom.xml
├── .env.example
└── src/
    ├── main/java/vn/ptit/iot/
    │   ├── IotApplication.java
    │   ├── config/        JWT filter, CORS, WebSocket, danh mục thiết bị, .env
    │   ├── controller/    auth, sensors, devices, device-actions, system
    │   ├── dto/           request/response, payload MQTT
    │   ├── entity/        User, SensorReading, DeviceAction
    │   ├── exception/     định dạng lỗi thống nhất
    │   ├── repository/    Spring Data JPA
    │   └── service/       nghiệp vụ, JWT, MQTT, trạng thái, WebSocket, seed
    ├── main/resources/
    │   ├── application.yml
    │   └── db/migration/  Flyway SQL
    └── test/              JUnit, MockMvc, H2; không kết nối MQTT thật
```

## Cài đặt và chạy

Cần **JDK 17+**, Maven 3.6.3+ và Docker. Có thể mở `pom.xml` trong IntelliJ IDEA
rồi chạy `IotApplication`.

Từ thư mục gốc:

```bash
docker compose -f infra/docker-compose.yml up -d
cd backend
# Chỉ cần lần đầu nếu chưa có .env; không ghi đè file .env đang dùng.
cp .env.example .env
mvn spring-boot:run
```

Mở `http://localhost:8000` · Swagger `http://localhost:8000/docs` · OpenAPI `/openapi.json`.
PostgreSQL vẫn ở **5433**, MQTT **1883**. Không chạy FastAPI đồng thời trên cổng 8000.

- `.env` được nạp khi chạy `IotApplication`; biến môi trường có ưu tiên cao hơn.
- `DATABASE_URL` kiểu Python cũ được tự chuyển sang JDBC để dùng lại `.env` hiện có.
- Có thể dùng `DB_URL`, `DB_USERNAME`, `DB_PASSWORD` cho cấu hình JDBC mới.
- Giữ `SECRET_KEY` cũ để tiếp tục dùng JWT FastAPI còn hiệu lực. BCrypt `$2b$` cũ được hỗ trợ.
- Frontend ngoài thư mục Java được phục vụ trực tiếp trong môi trường phát triển và đóng gói
  vào JAR khi build. Tuỳ chỉnh vị trí bằng `FRONTEND_DIR`.

## Sửa code khi demo

- Sửa HTML/CSS/JS: lưu file, tải lại trình duyệt (`⌘ + Shift + R` nếu còn cache).
- Sửa Java: dừng backend bằng `Ctrl + C`, chạy lại `mvn spring-boot:run`, rồi tải lại web.
- Sửa `.env`: khởi động lại backend.
- Sửa cấu trúc database: thêm migration **mới** `V3__...sql`, không sửa migration đã chạy.

## Database và chuyển đổi

Flyway tự chạy lúc khởi động; Hibernate chỉ **validate**, không tự xoá/tạo lại bảng.

- Database trống: V1 tạo ba bảng và index, V2 thêm các trường hồ sơ.
- Database Alembic hiện có: baseline tại 0, migration dùng `IF NOT EXISTS`, giữ dữ liệu,
  ID, password hash và hồ sơ. Bảng `alembic_version` cũ được giữ để đối chiếu.
- V2 chỉ điền hồ sơ còn trống cho tài khoản Nguyễn Xuân Hùng; không ghi đè giá trị đã sửa.
- V3 đổi mã thiết bị cũ sang `red`, `green`, `yellow`. Callback `beforeEachMigrate.sql`
  chuẩn hoá tên ràng buộc PostgreSQL để cả database trống và database Alembic cũ
  đều chạy được V3, không sửa nội dung các migration đã áp dụng.
- Không cần chạy Alembic cho backend Java.

Thông tin kết nối trong IntelliJ Database hoặc pgAdmin với cấu hình Docker mặc định:

| Thuộc tính | Giá trị |
|---|---|
| Loại database | PostgreSQL |
| Host / Port | `localhost` / `5433` |
| Database | `iot_db` |
| User | `iot` |
| Password | Xem cấu hình local trong `infra/docker-compose.yml` và `backend/.env` |

Ba bảng nghiệp vụ: `users` (tài khoản/hồ sơ), `data_sensor` (số đo),
`device_actions` (lệnh và phản hồi). Dữ liệu được giữ trong Docker volume
`postgres_data` khi khởi động lại container.

## Khởi tạo tài khoản (tuỳ chọn, không sinh số liệu)

Database hiện có giữ tài khoản cũ. Với database mới, bạn có thể đăng ký trên web hoặc:

```bash
mvn package
SEED_PASSWORD='mat-khau-ban-chon' ENABLE_MQTT=false \
  java -jar target/iot-backend-1.0.0.jar \
  --spring.main.web-application-type=none --iot.seed-accounts=true
```

Tạo `admin@ptit.edu.vn` và `user@ptit.edu.vn`; tài khoản đã tồn tại được bỏ qua.
Không thay mật khẩu, không tạo cảm biến hoặc thao tác mẫu.

## Kiểm thử và build

```bash
mvn test
mvn package
java -jar target/iot-backend-1.0.0.jar
```

`application-test.yml` dùng H2 riêng, MQTT bị tắt và mock; không đọc `.env` hay kết nối DB thật.
Các bài kiểm thử kiểm tra JSON API, tài khoản/hồ sơ, quyền truy cập, JWT, BCrypt, MQTT,
phản hồi điều khiển, timeout/phản hồi muộn, WebSocket.

## MQTT và WebSocket

- Client MQTT sống cùng ứng dụng, tự kết nối lại, không tạo trong request.
- Topics: `iot/sensor`, `iot/control`, `iot/feedback`, `iot/status`; hỗ trợ topic cũ qua
  `MQTT_LEGACY_TOPICS`.
- Lệnh có UUID `cmd_id`; kết quả cập nhật có điều kiện `result='Pending'`, chống ghi đè
  giữa feedback và timeout. Phản hồi sai device/target không được chốt lệnh.
- `/ws?token=<JWT>` giữ dạng `{type, data}` của frontend; token sai/hết hạn/thu hồi đóng 1008.
- `SHOW_IOT_DATA=false` ở frontend vẫn giữ giao diện trống như yêu cầu; đặt `true` khi
  muốn hiển thị dữ liệu thật. Không tự chạy trình giả lập.

Bản Python cũ được lưu ở `../legacy/fastapi/` để đối chiếu; không còn là backend chính.
Báo cáo PDF/Thông tin hệ thống đã gỡ khỏi giao diện; không thêm tính năng PDF mới trong lần chuyển đổi này.
