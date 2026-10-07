"""Theo dõi các lệnh điều khiển đang chờ thiết bị phản hồi.

Vòng đời một lệnh (SRS §2.10, §4.5.7 — docs/04-MQTT-CONTRACT.md §3):

    POST /devices/{id}/actions
      → ghi device_actions (result='Pending')
      → publish iot/control
      → register(cmd_id, action_id)  — hẹn giờ COMMAND_TIMEOUT_SECONDS
      → HTTP 202 trả về ngay, KHÔNG chờ thiết bị

      ├─ nhận iot/feedback đúng hạn → resolve() → Success | Failed
      └─ hết giờ                    → timer chạy → Timeout

Dùng `threading.Timer` thay vì asyncio: lệnh được chốt bởi thread của paho-mqtt
(khi có feedback) hoặc bởi thread của timer. Phần cập nhật DB vẫn đồng bộ; riêng
sự kiện WebSocket được chuyển an toàn sang event loop của FastAPI qua `app.ws.hub`.
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass
from uuid import UUID

from app.core.config import settings
from app.services import action_service
from app.state.device_cache import device_cache
from app.ws.hub import broadcast_from_thread

logger = logging.getLogger(__name__)


@dataclass
class PendingCommand:
    cmd_id: UUID
    action_id: int
    device_id: str
    target: str
    action: str
    timer: threading.Timer


class PendingCommandRegistry:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._pending: dict[UUID, PendingCommand] = {}

    def register(
        self, cmd_id: UUID, action_id: int, device_id: str, target: str, action: str
    ) -> None:
        """Bắt đầu đếm ngược cho một lệnh vừa được publish."""
        timer = threading.Timer(
            settings.command_timeout_seconds, self._on_timeout, args=(cmd_id,)
        )
        timer.daemon = True

        with self._lock:
            self._pending[cmd_id] = PendingCommand(
                cmd_id=cmd_id,
                action_id=action_id,
                device_id=device_id,
                target=target,
                action=action,
                timer=timer,
            )
        timer.start()

    def resolve(self, cmd_id: UUID) -> PendingCommand | None:
        """Chốt một lệnh: huỷ đồng hồ và lấy nó ra khỏi danh sách chờ.

        Trả về None nếu lệnh đã bị timeout hoặc chưa từng được đăng ký
        (ví dụ thiết bị tự đổi trạng thái, không có cmd_id tương ứng).
        """
        with self._lock:
            command = self._pending.pop(cmd_id, None)

        if command is None:
            return None

        command.timer.cancel()
        return command

    def has_pending(self, device_id: str, target: str) -> bool:
        """Đang có lệnh nào chờ cho đúng thiết bị chấp hành này không (F13)."""
        with self._lock:
            return any(
                command.device_id == device_id and command.target == target
                for command in self._pending.values()
            )

    def pending_count(self) -> int:
        with self._lock:
            return len(self._pending)

    def _on_timeout(self, cmd_id: UUID) -> None:
        """Chạy trong thread của Timer khi thiết bị không phản hồi kịp."""
        with self._lock:
            command = self._pending.pop(cmd_id, None)

        if command is None:
            return  # feedback đã về ngay trước khi đồng hồ điểm

        logger.warning(
            "Lệnh %s (%s %s trên %s) không nhận được phản hồi sau %ss → Timeout",
            cmd_id, command.target, command.action, command.device_id,
            settings.command_timeout_seconds,
        )
        updated = action_service.mark_result(
            command.action_id,
            "Timeout",
            error=f"Không nhận được phản hồi sau {settings.command_timeout_seconds:g}s",
        )
        if updated:
            cached = device_cache.get(command.device_id)
            current_state = bool(cached and cached.targets.get(command.target))
            broadcast_from_thread(
                "device_state",
                {
                    "device_id": command.device_id,
                    "target": command.target,
                    "state": "ON" if current_state else "OFF",
                    "action_id": command.action_id,
                    "result": "Timeout",
                    "error_msg": (
                        "Không nhận được phản hồi sau "
                        f"{settings.command_timeout_seconds:g}s"
                    ),
                },
            )

    def clear(self) -> None:
        """Huỷ mọi đồng hồ đang chạy — dùng khi tắt server và trong kiểm thử."""
        with self._lock:
            for command in self._pending.values():
                command.timer.cancel()
            self._pending.clear()


pending_commands = PendingCommandRegistry()
