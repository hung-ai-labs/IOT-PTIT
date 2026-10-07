"""Kiểm thử WebSocketHub, xác thực `/ws` và cầu phát từ thread."""

import asyncio
from datetime import UTC, datetime, timedelta

import jwt
import pytest
from starlette.websockets import WebSocketDisconnect

from app.core.config import settings
from app.ws.hub import WebSocketHub, broadcast_from_thread


class FakeWebSocket:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.accepted = False
        self.messages: list[dict] = []

    async def accept(self) -> None:
        self.accepted = True

    async def send_json(self, message: dict) -> None:
        if self.fail:
            raise RuntimeError("client disconnected")
        self.messages.append(message)


def test_hub_broadcasts_and_removes_failed_clients() -> None:
    async def scenario() -> None:
        hub = WebSocketHub()
        healthy = FakeWebSocket()
        broken = FakeWebSocket(fail=True)
        await hub.connect(healthy)
        await hub.connect(broken)

        await hub.broadcast({"type": "sensor", "data": {"temperature": 27.5}})

        assert healthy.accepted is True
        assert healthy.messages[0]["type"] == "sensor"
        assert hub.connection_count == 1

    asyncio.run(scenario())


def test_thread_bridge_is_silent_without_event_loop() -> None:
    broadcast_from_thread("sensor", {"device_id": "ESP32-01"})


def test_websocket_rejects_invalid_token_with_1008(client) -> None:
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect("/ws?token=invalid") as websocket:
            websocket.receive_json()

    assert exc_info.value.code == 1008


def test_websocket_rejects_expired_token_with_1008(client) -> None:
    expired = jwt.encode(
        {
            "sub": "1",
            "jti": "expired-test-token",
            "exp": datetime.now(UTC) - timedelta(seconds=1),
        },
        settings.secret_key,
        algorithm=settings.jwt_algorithm,
    )

    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect(f"/ws?token={expired}") as websocket:
            websocket.receive_json()

    assert exc_info.value.code == 1008


def test_websocket_rejects_revoked_token_with_1008(client, auth_token) -> None:
    response = client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert response.status_code == 204

    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect(f"/ws?token={auth_token}") as websocket:
            websocket.receive_json()

    assert exc_info.value.code == 1008


def test_websocket_receives_threadsafe_broadcast(client, auth_token) -> None:
    with client.websocket_connect(f"/ws?token={auth_token}") as websocket:
        broadcast_from_thread("sensor", {"device_id": "ESP32-01", "temperature": 27.5})
        message = websocket.receive_json()

    assert message == {
        "type": "sensor",
        "data": {"device_id": "ESP32-01", "temperature": 27.5},
    }
