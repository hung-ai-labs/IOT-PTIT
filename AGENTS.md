# AGENTS.md — Hệ thống Giám sát và Điều khiển IoT (PTIT)

Tài liệu hướng dẫn cho Codex khi làm việc trong repo này.
Nguồn yêu cầu gốc: `docs/00-SRS-SUMMARY.md` (chắt lọc từ "Báo cáo SRS.md").

---

## 1. Bối cảnh dự án

Hệ thống IoT giám sát môi trường trong nhà (nhiệt độ, độ ẩm, ánh sáng) và điều khiển
từ xa 3 thiết bị chấp hành (Đèn LED, Quạt, Điều hòa).

Luồng dữ liệu:

```
Sensors → ESP32/ESP8266 → MQTT Broker → FastAPI → PostgreSQL → Web Dashboard → User
User → Web Dashboard → FastAPI → MQTT Broker → ESP32 → (feedback) → FastAPI → DB → Dashboard
```

## 2. Stack công nghệ (cố định theo SRS — KHÔNG tự ý đổi)

| Lớp | Công nghệ |
|---|---|
| Backend | **FastAPI** (Python 3.11+), Uvicorn |
| Database | **PostgreSQL** + SQLAlchemy 2.x + Alembic |
| Frontend | **HTML + CSS + JavaScript thuần** (không framework), Chart.js cho biểu đồ |
| IoT Protocol | **MQTT** (Mosquitto broker), thư viện `paho-mqtt` / `gmqtt` |
| Firmware | **ESP32 / ESP8266** (Arduino C++, PubSubClient) |
| PDF | WeasyPrint (HTML→PDF) |

> Nếu cần lệch khỏi stack này, PHẢI hỏi trước — đây là đồ án có SRS chấm điểm.

## 3. Cấu trúc thư mục

```
IOT-PTIT/
├── AGENTS.md                 # file này
├── docs/                     # tài liệu kế hoạch (đọc trước khi code)
├── backend/                  # FastAPI app
│   ├── app/
│   │   ├── main.py           # khởi tạo app, lifespan, mount routers
│   │   ├── core/             # config, security (JWT), deps
│   │   ├── db/               # session, models SQLAlchemy
│   │   ├── schemas/          # Pydantic v2
│   │   ├── api/v1/           # routers: auth, sensors, devices, device_actions, reports, system
│   │   ├── mqtt/             # MQTT client, subscribe handlers, pending-command registry
│   │   ├── services/         # business logic
│   │   ├── ws/               # WebSocket hub (realtime push)
│   │   └── templates/        # Jinja2 template cho PDF
│   ├── alembic/
│   ├── tests/
│   └── requirements.txt
├── frontend/                 # static site, serve qua FastAPI StaticFiles
│   ├── *.html                # 8 màn hình
│   └── assets/{css,js,img}
├── firmware/esp32/           # sketch Arduino
├── infra/                    # docker-compose (postgres + mosquitto), mosquitto.conf
└── scripts/                  # seed data, mock publisher để test không cần ESP32
```

## 4. Quy ước bắt buộc

### Ngôn ngữ
- **Code, tên biến, tên hàm, comment kỹ thuật: tiếng Anh.**
- **UI text, thông báo cho người dùng, tài liệu: tiếng Việt có dấu.**
- Trả lời người dùng bằng **tiếng Việt**.

### Backend
- Mọi API nghiệp vụ nằm dưới prefix `/api/v1`.
- Response format thống nhất: xem `docs/03-API-SPEC.md` §Quy ước.
- Không bao giờ lưu mật khẩu thuần — dùng `bcrypt` qua `passlib`.
- Không hardcode secret/connection string — đọc từ `.env` qua `app/core/config.py`.
- Timestamp luôn dùng `TIMESTAMPTZ` và UTC ở tầng lưu trữ; đổi sang `Asia/Ho_Chi_Minh` ở tầng hiển thị.
- Mỗi endpoint mới phải có Pydantic schema request/response rõ ràng (để `/docs` tự sinh đúng).

### MQTT
- Topic chuẩn của dự án (xem `docs/04-MQTT-CONTRACT.md`):
  `iot/sensor` (lên), `iot/control` (xuống), `iot/feedback` (lên).
- Mọi lệnh điều khiển mang `cmd_id` (UUID) để khớp lệnh ↔ phản hồi.
- MQTT client chạy trong lifespan của FastAPI, **không** tạo client mới trong request handler.

### Frontend
- Vanilla JS, ES modules, không bundler. Logic riêng của mỗi màn hình nằm **ngay trong
  file `.html`** của màn đó, trong một thẻ `<script type="module">` duy nhất ở cuối `<body>`.
  Module dùng chung (`api.js`, `ui.js`, `layout.js`, `store.js`, `ws.js`…) vẫn là file riêng
  trong `assets/js/` và được `import` vào — **không sao chép chúng vào từng trang.**
- Toàn bộ màu sắc / spacing / font đi qua CSS variables trong `assets/css/tokens.css`
  → khi lấy design từ Figma chỉ cần cập nhật file này.
- Gọi API qua wrapper duy nhất `assets/js/api.js` (tự gắn Bearer token, tự xử lý 401).
- Không dùng CDN cho thư viện quan trọng ở bản nộp — vendor vào `assets/vendor/`.

### Git
- Commit message tiếng Anh, dạng `feat: ...`, `fix: ...`, `docs: ...`.
- Chỉ commit khi người dùng yêu cầu.

## 5. Cách chạy dự án

```bash
docker compose -f infra/docker-compose.yml up -d
cd backend && .venv/bin/uvicorn app.main:app --reload --port 8000

# Không có ESP32? Chạy giả lập ở một terminal khác:
cd backend && .venv/bin/python ../scripts/mock_device.py
```

Mở http://localhost:8000 (FastAPI phục vụ luôn frontend tĩnh) · Swagger: `/docs`

Cài đặt lần đầu, migration, seed, kiểm thử: xem **`backend/README.md`**.

⚠️ **PostgreSQL chạy ở cổng 5433**, không phải 5432 (tránh đụng PostgreSQL cài qua Homebrew).
⚠️ Dùng **`python3.12`** để tạo venv. Dùng **`bcrypt` trực tiếp, không dùng `passlib`.**
⚠️ **`ENABLE_MQTT=false` bắt buộc khi chạy test** (đã đặt sẵn trong `tests/conftest.py`).
Nếu để `true`, mỗi `TestClient` sẽ kết nối broker thật và ghi dữ liệu vào PostgreSQL thật.

## 6. Trạng thái công việc

| Giai đoạn | Trạng thái |
|---|---|
| GĐ0 Hạ tầng & khung dự án | ✅ xong |
| GĐ1 Database | ✅ xong |
| GĐ7 Frontend khung | ✅ xong |
| GĐ8 Áp giao diện Figma | ✅ xong |
| GĐ2 Xác thực | ✅ xong — frontend đã nối API thật |
| GĐ3 MQTT + thu thập cảm biến | ✅ xong — frontend đã nối API thật |
| GĐ4 Điều khiển thiết bị | ✅ xong — frontend đã nối API thật |
| **GĐ5 Trạng thái hệ thống + WebSocket** | ⬅️ **tiếp theo** |
| GĐ6, 9, 10 | chưa bắt đầu |

Checklist chi tiết: `docs/06-ROADMAP.md`.
**Trước khi bắt đầu một task, đọc mục tương ứng trong `docs/` rồi mới code.**

## 7. Vấn đề còn mở

`docs/07-OPEN-QUESTIONS.md` liệt kê các điểm SRS mâu thuẫn/thiếu và phương án đề xuất.
Không tự quyết những mục được đánh dấu 🔴 — phải hỏi người dùng.

## 8. Frontend — ĐÃ DỰNG XONG (09/09/2026)

Giao diện đã lấy từ Figma Make `6LtIcdRDy3tlNe9mA0At2M` và viết lại sang vanilla JS.
**Đọc `frontend/README.md` trước khi sửa bất cứ thứ gì trong `frontend/`.**

Điểm cần nhớ:
- Mọi màu / spacing / font nằm trong `frontend/assets/css/tokens.css`. **Không hardcode.**
- Mọi lời gọi dữ liệu đi qua `frontend/assets/js/api.js`. **Xác thực đã dùng API thật.**
  Xác thực, cảm biến, thiết bị, lịch sử đều dùng API thật. Chỉ còn
  `USE_MOCK = { system, reports }` — xong GĐ5/GĐ6 thì đặt `false` rồi **xoá luôn nhánh mock**.
- Font (Inter, JetBrains Mono) và Chart.js đã vendor vào `assets/` — không thêm CDN.
- **Thanh DEMO đã gỡ** (GĐ4): trạng thái ESP32/MQTT nay lấy thật từ server nên nút giả lập
  sẽ nói dối. Muốn demo cảnh mất kết nối thì tắt `scripts/mock_device.py`.

Chạy thử:

```bash
python3 -m http.server 5173 --directory frontend
```

## 9. Các quyết định đã chốt

| Mã | Quyết định |
|---|---|
| OQ-03 | Frontend **vanilla JS**, không React (đúng SRS §1.2) |
| OQ-06 | **Chưa làm** tự động hóa theo điều kiện môi trường — ghi là hướng phát triển tương lai |
| OQ-09 | Điều hòa điều khiển bằng **Relay** (không dùng IR), giống LED và Quạt |

Chi tiết và các mục còn lại: `docs/07-OPEN-QUESTIONS.md`.
