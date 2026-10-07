"""Quản lý kết nối WebSocket và bắc cầu an toàn từ các thread MQTT."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Coroutine
from typing import Any

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class WebSocketHub:
    """Giữ các tab đang kết nối và phát một sự kiện tới tất cả tab."""

    def __init__(self) -> None:
        self._connections: set[WebSocket] = set()

    @property
    def connection_count(self) -> int:
        return len(self._connections)

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections.add(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        self._connections.discard(websocket)

    async def broadcast(self, message: dict[str, Any]) -> None:
        if not self._connections:
            return

        connections = list(self._connections)
        results = await asyncio.gather(
            *(websocket.send_json(message) for websocket in connections),
            return_exceptions=True,
        )
        for websocket, result in zip(connections, results, strict=True):
            if isinstance(result, BaseException):
                self.disconnect(websocket)
                logger.warning("Đã loại một kết nối WebSocket bị lỗi: %s", result)

    def clear(self) -> None:
        """Dọn danh sách kết nối khi tắt app và trong kiểm thử."""
        self._connections.clear()


websocket_hub = WebSocketHub()
_event_loop: asyncio.AbstractEventLoop | None = None


def set_event_loop(loop: asyncio.AbstractEventLoop) -> None:
    global _event_loop
    _event_loop = loop


def clear_event_loop() -> None:
    global _event_loop
    _event_loop = None


def _log_future_result(future: asyncio.Future) -> None:
    try:
        future.result()
    except Exception:  # noqa: BLE001 — lỗi WS không được làm chết thread MQTT/Timer
        logger.warning("Không phát được sự kiện WebSocket", exc_info=True)


def broadcast_from_thread(event_type: str, data: dict[str, Any]) -> None:
    """Lên lịch phát sự kiện từ thread paho/Timer vào event loop của FastAPI."""
    loop = _event_loop
    if loop is None or loop.is_closed():
        return

    coroutine: Coroutine[Any, Any, None] = websocket_hub.broadcast(
        {"type": event_type, "data": data}
    )
    try:
        future = asyncio.run_coroutine_threadsafe(coroutine, loop)
        future.add_done_callback(_log_future_result)
    except Exception:  # noqa: BLE001
        coroutine.close()
        logger.warning("Không thể chuyển sự kiện WebSocket vào event loop", exc_info=True)
