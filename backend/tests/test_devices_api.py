"""Kiểm thử API điều khiển thiết bị — Giai đoạn 4 (F04, F08, F10, F11, F13)."""

import json
import uuid
from datetime import UTC, datetime, timedelta

import pytest

import app.mqtt.handlers as handlers
from app.core.config import settings
from app.db.models.device_action import DeviceAction
from app.mqtt.registry import pending_commands
from app.state.device_cache import device_cache


class FakeMqtt:
    """Thay thế MQTT client thật: ghi lại mọi lệnh publish thay vì gửi đi."""

    def __init__(self, connected: bool = True, publish_ok: bool = True) -> None:
        self.connected = connected
        self.publish_ok = publish_ok
        self.published: list[tuple[str, dict]] = []

    def publish(self, topic: str, payload: dict, qos: int = 1) -> bool:
        self.published.append((topic, payload))
        return self.publish_ok

    @property
    def last_payload(self) -> dict:
        return self.published[-1][1]


@pytest.fixture
def mqtt(monkeypatch):
    """MQTT giả, đã kết nối. Gắn vào cả control_service lẫn nơi khác dùng chung."""
    fake = FakeMqtt()
    monkeypatch.setattr("app.services.control_service.mqtt_service", fake)
    pending_commands.clear()
    yield fake
    pending_commands.clear()


@pytest.fixture
def online_device():
    """Đánh dấu ESP32-01 vừa gửi tin, tức là đang online."""
    device_cache.clear()
    device_cache.touch("ESP32-01", ip="192.168.1.105", rssi=-58, uptime=3600)
    yield "ESP32-01"
    device_cache.clear()


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def send(client, token, target="fan", action="ON", device_id="ESP32-01"):
    return client.post(
        f"/api/v1/devices/{device_id}/actions",
        json={"target": target, "action": action},
        headers=auth(token),
    )


# ─── Bảo vệ bằng token ───────────────────────────────────────
@pytest.mark.parametrize(
    "path",
    [
        "/api/v1/devices",
        "/api/v1/devices/ESP32-01",
        "/api/v1/device-actions",
        "/api/v1/device-actions/1",
    ],
)
def test_get_endpoints_require_authentication(client, path) -> None:
    assert client.get(path).status_code == 401


def test_send_action_requires_authentication(client) -> None:
    response = client.post(
        "/api/v1/devices/ESP32-01/actions", json={"target": "fan", "action": "ON"}
    )
    assert response.status_code == 401


# ─── GET /devices ────────────────────────────────────────────
def test_list_devices_returns_three_actuators(client, auth_token, online_device) -> None:
    response = client.get("/api/v1/devices", headers=auth(auth_token))

    assert response.status_code == 200
    devices = response.json()
    assert [d["target"] for d in devices] == ["led", "fan", "ac"]
    assert [d["name"] for d in devices] == ["Đèn đỏ", "Đèn xanh", "Đèn vàng"]
    assert all(d["connection"] == "online" for d in devices)
    assert all(d["state"] == "OFF" for d in devices)  # cache trống → mặc định OFF


def test_devices_report_offline_without_recent_message(client, auth_token) -> None:
    device_cache.clear()
    response = client.get("/api/v1/devices", headers=auth(auth_token))

    assert all(d["connection"] == "offline" for d in response.json())


def test_device_detail_exposes_mqtt_topics(client, auth_token, online_device) -> None:
    body = client.get("/api/v1/devices/ESP32-01", headers=auth(auth_token)).json()

    assert body["command_topic"] == "iot/control"
    assert body["feedback_topic"] == "iot/feedback"
    assert body["ip"] == "192.168.1.105"
    assert body["rssi"] == -58
    assert len(body["targets"]) == 3


# ─── POST /devices/{id}/actions ──────────────────────────────
def test_send_action_returns_202_pending(client, auth_token, online_device, mqtt) -> None:
    response = send(client, auth_token)

    assert response.status_code == 202
    body = response.json()
    assert body["result"] == "Pending"
    assert body["target"] == "fan"
    assert body["timeout_seconds"] == settings.command_timeout_seconds
    uuid.UUID(body["cmd_id"])  # phải là UUID hợp lệ


def test_send_action_publishes_to_control_topic(client, auth_token, online_device, mqtt) -> None:
    body = send(client, auth_token, target="led", action="OFF").json()

    topic, payload = mqtt.published[-1]
    assert topic == "iot/control"
    assert payload["cmd_id"] == body["cmd_id"]
    assert payload["target"] == "led"
    assert payload["action"] == "OFF"
    assert payload["device_id"] == "ESP32-01"


def test_send_action_records_pending_row(client, auth_token, online_device, mqtt, db_session) -> None:
    action_id = send(client, auth_token).json()["action_id"]

    record = db_session.get(DeviceAction, action_id)
    assert record.result == "Pending"
    assert record.responded_at is None
    assert record.issued_by is not None


def test_action_appears_in_history_with_issuer(client, auth_token, online_device, mqtt) -> None:
    send(client, auth_token)

    body = client.get("/api/v1/device-actions", headers=auth(auth_token)).json()
    assert body["total"] == 1
    item = body["items"][0]
    assert item["target_label"] == "Đèn xanh"
    assert item["issued_by"]["full_name"] == "Nguyễn Xuân Hùng"


# ─── Điều kiện chặn lệnh (F13) ───────────────────────────────
def test_rejects_when_device_offline(client, auth_token, mqtt) -> None:
    device_cache.clear()
    response = send(client, auth_token)

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "DEVICE_OFFLINE"


def test_rejects_when_mqtt_disconnected(client, auth_token, online_device, monkeypatch) -> None:
    monkeypatch.setattr(
        "app.services.control_service.mqtt_service", FakeMqtt(connected=False)
    )
    response = send(client, auth_token)

    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "MQTT_UNAVAILABLE"


def test_rejects_second_command_for_same_target(client, auth_token, online_device, mqtt) -> None:
    assert send(client, auth_token, target="fan").status_code == 202

    response = send(client, auth_token, target="fan")
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "COMMAND_IN_PROGRESS"


def test_allows_command_for_a_different_target(client, auth_token, online_device, mqtt) -> None:
    assert send(client, auth_token, target="fan").status_code == 202
    assert send(client, auth_token, target="led").status_code == 202


def test_failed_publish_marks_action_failed(
    client, auth_token, online_device, monkeypatch, db_session
) -> None:
    monkeypatch.setattr(
        "app.services.control_service.mqtt_service", FakeMqtt(publish_ok=False)
    )
    response = send(client, auth_token)

    assert response.status_code == 503
    record = db_session.query(DeviceAction).one()
    assert record.result == "Failed"
    assert "MQTT" in record.error_msg


def test_rejects_unknown_target(client, auth_token, online_device, mqtt) -> None:
    assert send(client, auth_token, target="máy giặt").status_code == 422


def test_rejects_unknown_action(client, auth_token, online_device, mqtt) -> None:
    assert send(client, auth_token, action="BLINK").status_code == 422


# ─── Vòng đời lệnh: feedback (F11) ───────────────────────────
def test_feedback_resolves_pending_command(
    client, auth_token, online_device, mqtt, db_session, monkeypatch, _database
) -> None:
    monkeypatch.setattr(handlers, "SessionLocal", _database)
    monkeypatch.setattr("app.services.action_service.SessionLocal", _database)

    body = send(client, auth_token, target="fan", action="ON").json()

    handlers.handle_feedback_message(json.dumps({
        "cmd_id": body["cmd_id"],
        "device_id": "ESP32-01",
        "target": "fan",
        "state": "ON",
        "result": "Success",
    }).encode())

    record = db_session.get(DeviceAction, body["action_id"])
    db_session.refresh(record)
    assert record.result == "Success"
    assert record.responded_at is not None
    assert device_cache.get("ESP32-01").targets["fan"] is True
    assert pending_commands.pending_count() == 0


def test_feedback_broadcasts_device_state(
    client, auth_token, online_device, mqtt, monkeypatch, _database
) -> None:
    events = []
    monkeypatch.setattr(handlers, "SessionLocal", _database)
    monkeypatch.setattr("app.services.action_service.SessionLocal", _database)
    monkeypatch.setattr(
        handlers, "broadcast_from_thread", lambda event_type, data: events.append((event_type, data))
    )
    body = send(client, auth_token, target="fan", action="ON").json()

    handlers.handle_feedback_message(json.dumps({
        "cmd_id": body["cmd_id"],
        "device_id": "ESP32-01",
        "target": "fan",
        "state": "ON",
        "result": "Success",
    }).encode())

    assert events == [("device_state", {
        "device_id": "ESP32-01",
        "target": "fan",
        "state": "ON",
        "action_id": body["action_id"],
        "result": "Success",
        "error_msg": None,
    })]


def test_failed_feedback_keeps_previous_state(
    client, auth_token, online_device, mqtt, db_session, monkeypatch, _database
) -> None:
    monkeypatch.setattr(handlers, "SessionLocal", _database)
    monkeypatch.setattr("app.services.action_service.SessionLocal", _database)

    body = send(client, auth_token, target="fan", action="ON").json()

    handlers.handle_feedback_message(json.dumps({
        "cmd_id": body["cmd_id"],
        "device_id": "ESP32-01",
        "target": "fan",
        "state": "OFF",
        "result": "Failed",
        "error": "Relay không đóng được",
    }).encode())

    record = db_session.get(DeviceAction, body["action_id"])
    db_session.refresh(record)
    assert record.result == "Failed"
    assert record.error_msg == "Relay không đóng được"
    # Thất bại thì KHÔNG đổi trạng thái hiển thị
    assert "fan" not in device_cache.get("ESP32-01").targets


def test_feedback_for_unknown_command_is_ignored(client, auth_token, online_device, mqtt) -> None:
    handlers.handle_feedback_message(json.dumps({
        "cmd_id": str(uuid.uuid4()),
        "device_id": "ESP32-01",
        "target": "fan",
        "state": "ON",
        "result": "Success",
    }).encode())

    # Vẫn cập nhật cache, chỉ không có bản ghi nào để chốt.
    assert device_cache.get("ESP32-01").targets["fan"] is True


# ─── Vòng đời lệnh: timeout ──────────────────────────────────
def test_timeout_marks_action_and_clears_registry(
    client, auth_token, online_device, mqtt, db_session, monkeypatch, _database
) -> None:
    monkeypatch.setattr("app.services.action_service.SessionLocal", _database)
    monkeypatch.setattr(settings, "command_timeout_seconds", 0.2)

    body = send(client, auth_token).json()
    assert pending_commands.pending_count() == 1

    import time
    time.sleep(0.5)

    record = db_session.get(DeviceAction, body["action_id"])
    db_session.refresh(record)
    assert record.result == "Timeout"
    assert "phản hồi" in record.error_msg
    assert pending_commands.pending_count() == 0


def test_timeout_broadcasts_device_state(
    client, auth_token, online_device, mqtt, monkeypatch, _database
) -> None:
    events = []
    monkeypatch.setattr("app.services.action_service.SessionLocal", _database)
    monkeypatch.setattr(settings, "command_timeout_seconds", 0.05)
    monkeypatch.setattr(
        "app.mqtt.registry.broadcast_from_thread",
        lambda event_type, data: events.append((event_type, data)),
    )

    body = send(client, auth_token, target="fan", action="ON").json()

    import time
    time.sleep(0.15)

    assert events[0][0] == "device_state"
    assert events[0][1]["action_id"] == body["action_id"]
    assert events[0][1]["result"] == "Timeout"
    assert events[0][1]["state"] == "OFF"


def test_late_feedback_does_not_overwrite_timeout(
    client, auth_token, online_device, mqtt, db_session, monkeypatch, _database
) -> None:
    monkeypatch.setattr(handlers, "SessionLocal", _database)
    monkeypatch.setattr("app.services.action_service.SessionLocal", _database)
    monkeypatch.setattr(settings, "command_timeout_seconds", 0.2)

    body = send(client, auth_token).json()

    import time
    time.sleep(0.5)  # để timeout chốt trước

    handlers.handle_feedback_message(json.dumps({
        "cmd_id": body["cmd_id"],
        "device_id": "ESP32-01",
        "target": "fan",
        "state": "ON",
        "result": "Success",
    }).encode())

    record = db_session.get(DeviceAction, body["action_id"])
    db_session.refresh(record)
    assert record.result == "Timeout", "Phản hồi đến muộn không được ghi đè Timeout"


# ─── GET /device-actions ─────────────────────────────────────
@pytest.fixture
def history(db_session):
    now = datetime.now(UTC)
    rows = [
        DeviceAction(device_id="ESP32-01", target="led", action="ON",
                     result="Success", cmd_id=uuid.uuid4(), timestamp=now),
        DeviceAction(device_id="ESP32-01", target="fan", action="OFF",
                     result="Failed", cmd_id=uuid.uuid4(), timestamp=now - timedelta(minutes=1)),
        DeviceAction(device_id="ESP32-02", target="ac", action="ON",
                     result="Timeout", cmd_id=uuid.uuid4(), timestamp=now - timedelta(minutes=2)),
    ]
    db_session.add_all(rows)
    db_session.commit()
    return rows


def test_history_filters_by_result(client, auth_token, history) -> None:
    body = client.get("/api/v1/device-actions?result=Failed", headers=auth(auth_token)).json()

    assert body["total"] == 1
    assert body["items"][0]["target"] == "fan"


def test_history_filters_by_target_and_action(client, auth_token, history) -> None:
    body = client.get(
        "/api/v1/device-actions?target=led&action=ON", headers=auth(auth_token)
    ).json()

    assert body["total"] == 1


def test_history_filters_by_device(client, auth_token, history) -> None:
    body = client.get(
        "/api/v1/device-actions?device_id=ESP32-02", headers=auth(auth_token)
    ).json()

    assert body["total"] == 1
    assert body["items"][0]["result"] == "Timeout"


def test_history_is_newest_first(client, auth_token, history) -> None:
    items = client.get("/api/v1/device-actions", headers=auth(auth_token)).json()["items"]

    assert [i["target"] for i in items] == ["led", "fan", "ac"]


def test_history_null_issuer_is_allowed(client, auth_token, history) -> None:
    """Thiết bị tự đổi trạng thái → issued_by = NULL."""
    items = client.get("/api/v1/device-actions", headers=auth(auth_token)).json()["items"]

    assert all(item["issued_by"] is None for item in items)


def test_get_single_action(client, auth_token, history) -> None:
    action_id = history[0].id
    body = client.get(f"/api/v1/device-actions/{action_id}", headers=auth(auth_token)).json()

    assert body["id"] == action_id
    assert body["target_label"] == "Đèn đỏ"


def test_get_unknown_action_returns_404(client, auth_token) -> None:
    response = client.get("/api/v1/device-actions/99999", headers=auth(auth_token))

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "ACTION_NOT_FOUND"
