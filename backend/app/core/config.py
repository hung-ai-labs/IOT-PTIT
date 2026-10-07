"""Cấu hình ứng dụng, đọc từ biến môi trường / file .env."""

from functools import lru_cache
from pathlib import Path
from typing import Annotated, Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

# Danh sách thiết bị chấp hành khai báo tĩnh.
# SRS §4.2 chỉ định 3 bảng (users, data_sensor, device_actions) nên không tạo
# bảng `devices` riêng — xem docs/07-OPEN-QUESTIONS.md OQ-04.
DEVICE_REGISTRY: dict[str, dict[str, str]] = {
    "led": {"name": "Đèn đỏ", "gpio": "GPIO 25", "icon": "💡"},
    "fan": {"name": "Đèn xanh", "gpio": "GPIO 26", "icon": "💡"},
    "ac": {"name": "Đèn vàng", "gpio": "GPIO 27", "icon": "💡"},
}

# Đơn vị đo theo loại cảm biến (SRS §4.2.2).
SENSOR_UNITS: dict[str, str] = {
    "temperature": "°C",
    "humidity": "%",
    "light": "lux",
}

# Biên hợp lệ của giá trị cảm biến; ngoài biên thì bỏ qua bản tin.
SENSOR_RANGES: dict[str, tuple[float, float]] = {
    "temperature": (-40.0, 85.0),
    "humidity": (0.0, 100.0),
    "light": (0.0, 100_000.0),
}


class Settings(BaseSettings):
    # Đường dẫn tuyệt đối tới backend/.env: nếu để ".env" tương đối thì file chỉ
    # được đọc khi chạy từ thư mục backend/. Chạy từ gốc repo (cách CLAUDE.md §5
    # và .claude/launch.json dùng) sẽ không thấy .env và âm thầm rơi về giá trị
    # mặc định — gồm cả SECRET_KEY placeholder.
    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[2] / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ─── Ứng dụng ────────────────────────────────────────────
    app_name: str = "Smart IoT — Monitoring & Control"
    app_version: str = "1.0.0"
    debug: bool = False
    api_prefix: str = "/api/v1"

    # ─── Cơ sở dữ liệu ───────────────────────────────────────
    database_url: str = "postgresql+psycopg://iot:iot_password@localhost:5433/iot_db"
    # Tách khỏi `debug`: bật riêng khi cần soi câu lệnh SQL, vì log SQL rất dài.
    db_echo: bool = False

    # ─── Bảo mật ─────────────────────────────────────────────
    secret_key: str = "doi-khoa-nay-truoc-khi-trien-khai-that"
    jwt_algorithm: Literal["HS256"] = "HS256"
    access_token_expire_hours: int = 8

    # ─── MQTT ────────────────────────────────────────────────
    # Tắt trong kiểm thử: nếu bật, mỗi TestClient sẽ kết nối vào broker thật,
    # publish lệnh STATUS và ghi dữ liệu cảm biến nhận được vào PostgreSQL thật.
    enable_mqtt: bool = True
    mqtt_host: str = "localhost"
    mqtt_port: int = 1883
    mqtt_username: str = ""
    mqtt_password: str = ""
    mqtt_legacy_topics: bool = True

    # ─── Ngưỡng thời gian ────────────────────────────────────
    # float để kiểm thử đặt được ngưỡng dưới 1 giây mà không phải chờ thật.
    command_timeout_seconds: float = 5.0
    device_offline_seconds: int = 30
    heartbeat_seconds: int = 10

    # ─── CORS ────────────────────────────────────────────────
    # NoDecode: tắt cơ chế tự parse JSON của pydantic-settings để validator
    # bên dưới nhận được chuỗi thô "a,b,c" từ .env.
    cors_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:8000", "http://localhost:5173"]
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def split_origins(cls, value: object) -> object:
        """Cho phép khai báo dạng chuỗi ngăn cách bởi dấu phẩy trong .env."""
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
