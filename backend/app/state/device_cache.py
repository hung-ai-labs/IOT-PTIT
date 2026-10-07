"""Trạng thái thiết bị IoT trong bộ nhớ.

Đây là nguồn sự thật cho trạng thái ON/OFF và tình trạng kết nối hiển thị trên
Dashboard (docs/01-ARCHITECTURE.md §2). Dữ liệu bị mất khi restart server —
Giai đoạn 4 sẽ khôi phục bằng cách publish lệnh `STATUS` để thiết bị báo lại.

Lớp này bị truy cập từ hai luồng: thread của paho-mqtt (ghi) và các request
handler của FastAPI (đọc), nên mọi thao tác đều nằm trong Lock.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import UTC, datetime

from app.core.config import settings


@dataclass
class DeviceState:
    """Trạng thái của một ESP và các thiết bị chấp hành gắn trên nó."""

    device_id: str
    last_seen: datetime | None = None
    ip: str | None = None
    rssi: int | None = None
    uptime: int | None = None
    # target ('led' | 'fan' | 'ac') → True nếu đang bật
    targets: dict[str, bool] = field(default_factory=dict)

    @property
    def online(self) -> bool:
        if self.last_seen is None:
            return False
        age = (datetime.now(UTC) - self.last_seen).total_seconds()
        return age <= settings.device_offline_seconds


class DeviceStateCache:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._devices: dict[str, DeviceState] = {}

    def _get_or_create(self, device_id: str) -> DeviceState:
        device = self._devices.get(device_id)
        if device is None:
            device = DeviceState(device_id=device_id)
            self._devices[device_id] = device
        return device

    def touch(
        self,
        device_id: str,
        *,
        ip: str | None = None,
        rssi: int | None = None,
        uptime: int | None = None,
    ) -> None:
        """Ghi nhận thiết bị vừa gửi tin — dùng cho heartbeat và bản tin cảm biến."""
        with self._lock:
            device = self._get_or_create(device_id)
            device.last_seen = datetime.now(UTC)
            if ip is not None:
                device.ip = ip
            if rssi is not None:
                device.rssi = rssi
            if uptime is not None:
                device.uptime = uptime

    def mark_offline(self, device_id: str) -> None:
        """Gọi khi nhận Last Will của thiết bị."""
        with self._lock:
            self._get_or_create(device_id).last_seen = None

    def set_target_state(self, device_id: str, target: str, is_on: bool) -> None:
        with self._lock:
            self._get_or_create(device_id).targets[target] = is_on

    def get(self, device_id: str) -> DeviceState | None:
        with self._lock:
            return self._devices.get(device_id)

    def all(self) -> list[DeviceState]:
        with self._lock:
            return list(self._devices.values())

    def any_online(self) -> bool:
        return any(device.online for device in self.all())

    def clear(self) -> None:
        """Dùng trong kiểm thử."""
        with self._lock:
            self._devices.clear()


# Một instance dùng chung cho toàn ứng dụng.
device_cache = DeviceStateCache()
