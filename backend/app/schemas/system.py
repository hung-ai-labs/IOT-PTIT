"""Schema trạng thái hệ thống và sự kiện WebSocket — docs/03-API-SPEC.md §7, §8."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class EspStatus(BaseModel):
    status: Literal["online", "offline"]
    device_id: str
    last_seen: datetime | None = None
    ip: str | None = None
    rssi: int | None = None
    uptime: int | None = None


class MqttStatus(BaseModel):
    status: Literal["connected", "disconnected"]
    broker: str
    topics: list[str]
    messages_received: int


class ApiStatus(BaseModel):
    status: Literal["running", "unavailable"]
    version: str
    uptime_seconds: float


class DatabaseStatus(BaseModel):
    status: Literal["connected", "disconnected"]
    latency_ms: float | None = None


class SystemStatusOut(BaseModel):
    esp: EspStatus
    mqtt: MqttStatus
    api: ApiStatus
    database: DatabaseStatus
