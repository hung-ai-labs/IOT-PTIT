# Hệ thống Giám sát và Điều khiển IoT — PTIT

Dự án giám sát nhiệt độ, độ ẩm, ánh sáng qua ESP32/MQTT và điều khiển ba đèn đỏ,
xanh, vàng. Backend FastAPI, PostgreSQL, frontend HTML/CSS/JavaScript thuần.

## Tài nguyên

- [Mã nguồn GitHub](https://github.com/hung-ai-labs/IOT-PTIT)
- [Tài liệu dự án](docs/README.md)
- Figma: sẽ bổ sung sau.
- API Swagger: `http://localhost:8000/docs` khi backend đang chạy.

## Chạy dự án

Cài đặt Python 3.12, Docker và làm theo [hướng dẫn backend](backend/README.md)
để tạo môi trường, cấu hình `.env` và chạy migration trước lần chạy đầu.

```bash
docker compose -f infra/docker-compose.yml up -d
cd backend
.venv/bin/uvicorn app.main:app --reload --port 8000
```

Mở `http://localhost:8000`. PostgreSQL dùng cổng **5433**.

Giao diện hiện giữ đầy đủ chức năng nhưng **chưa hiển thị dữ liệu IoT** theo yêu cầu.
Khi sẵn sàng hiển thị dữ liệu thật, đặt `SHOW_IOT_DATA = true` trong
`frontend/assets/js/config.js`. Không tự chạy trình giả lập hoặc nạp số liệu mẫu.
Script `scripts/seed.py` chỉ tạo tài khoản; hồ sơ cá nhân lưu vào PostgreSQL.

## Kiểm thử

```bash
cd backend
ENABLE_MQTT=false .venv/bin/python -m pytest tests -q
```

Xem [hướng dẫn frontend](frontend/README.md) và [đặc tả API](docs/03-API-SPEC.md).
