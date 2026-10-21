# Hệ thống Giám sát và Điều khiển IoT — PTIT

Giám sát nhiệt độ, độ ẩm, ánh sáng qua ESP32/MQTT và điều khiển ba đèn đỏ, xanh, vàng.
Backend đã chuyển sang **Spring Boot / Java 17 / Maven** theo xác nhận ngày 07/10/2026.
Database PostgreSQL, frontend HTML/CSS/JavaScript thuần.

## Tài nguyên

- [Mã nguồn GitHub](https://github.com/hung-ai-labs/IOT-PTIT)
- [Thiết kế Figma](https://www.figma.com/make/6LtIcdRDy3tlNe9mA0At2M/Follow-the-instructions?t=9IZehyceEY8oOncd-1&preview-route=%2Fdashboard)
- [Tài liệu dự án](docs/README.md)
- Swagger: `http://localhost:8000/docs` · OpenAPI: `/openapi.json`.

## Chạy

Cần JDK 17+, Maven và Docker. Xem [hướng dẫn backend](backend/README.md) trước lần chạy đầu.

```bash
docker compose -f infra/docker-compose.yml up -d
cd backend
# Chỉ copy nếu chưa có .env; giữ .env cũ khi chuyển từ FastAPI.
cp .env.example .env
mvn spring-boot:run
```

Mở `http://localhost:8000`. PostgreSQL dùng cổng **5433**. Flyway tự chạy migration
và dùng lại database hiện có; BCrypt/JWT tương thích tài khoản FastAPI cũ.

Giao diện hiện giữ đầy đủ chức năng nhưng **chưa hiển thị dữ liệu IoT** theo yêu cầu.
Khi sẵn sàng, đặt `SHOW_IOT_DATA = true` trong `frontend/assets/js/config.js`.
Không tự chạy giả lập hoặc nạp số liệu mẫu.

## Kiểm thử và đóng gói

```bash
cd backend
mvn test
mvn package
java -jar target/iot-backend-1.0.0.jar
```

Test Java dùng H2 riêng và MQTT mock. Sửa Java cần build/chạy lại; sửa HTML/CSS/JS chỉ
cần lưu và tải lại trang. Python cũ được lưu ở [legacy/fastapi](legacy/fastapi/README.md).

Xem [frontend](frontend/README.md), [kiến trúc Spring Boot](docs/08-SPRING-BOOT-MIGRATION.md)
và [đặc tả API](docs/03-API-SPEC.md).
