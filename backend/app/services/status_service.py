"""Tổng hợp trạng thái các thành phần của hệ thống IoT."""

from __future__ import annotations

import time

from sqlalchemy import text

from app.core.config import settings
from app.db.session import engine
from app.mqtt import topics
from app.mqtt.client import mqtt_service
from app.schemas.system import (
    ApiStatus,
    DatabaseStatus,
    EspStatus,
    MqttStatus,
    SystemStatusOut,
)
from app.services.control_service import DEFAULT_DEVICE_ID
from app.state.device_cache import device_cache


def check_database() -> DatabaseStatus:
    """Ping cơ sở dữ liệu và đo độ trễ bằng một truy vấn tối thiểu."""
    started = time.perf_counter()
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception:  # noqa: BLE001 — endpoint trạng thái phải trả được khi DB hỏng
        return DatabaseStatus(status="disconnected", latency_ms=None)

    latency_ms = round((time.perf_counter() - started) * 1000, 2)
    return DatabaseStatus(status="connected", latency_ms=latency_ms)


def get_system_status(started_at: float) -> SystemStatusOut:
    """Tạo ảnh chụp trạng thái dùng chung cho REST, health và WebSocket."""
    devices = device_cache.all()
    device = devices[0] if devices else None

    return SystemStatusOut(
        esp=EspStatus(
            status="online" if device and device.online else "offline",
            device_id=device.device_id if device else DEFAULT_DEVICE_ID,
            last_seen=device.last_seen if device else None,
            ip=device.ip if device else None,
            rssi=device.rssi if device else None,
            uptime=device.uptime if device else None,
        ),
        mqtt=MqttStatus(
            status="connected" if mqtt_service.connected else "disconnected",
            broker=f"{settings.mqtt_host}:{settings.mqtt_port}",
            topics=[
                topics.TOPIC_SENSOR,
                topics.TOPIC_CONTROL,
                topics.TOPIC_FEEDBACK,
                topics.TOPIC_STATUS,
            ],
            messages_received=mqtt_service.messages_received,
        ),
        api=ApiStatus(
            status="running",
            version=settings.app_version,
            uptime_seconds=round(time.monotonic() - started_at, 1),
        ),
        database=check_database(),
    )
