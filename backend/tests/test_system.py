"""Kiểm thử trạng thái hệ thống — Giai đoạn 5 (F09)."""

from app.mqtt import topics
from app.services import status_service
from app.state.device_cache import device_cache


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_system_status_requires_authentication(client) -> None:
    response = client.get("/api/v1/system/status")

    assert response.status_code == 401


def test_system_status_returns_all_components(
    client, auth_token, db_session, monkeypatch
) -> None:
    monkeypatch.setattr(status_service, "engine", db_session.get_bind())
    device_cache.touch("ESP32-01", ip="192.168.1.20", rssi=-58, uptime=3600)

    response = client.get("/api/v1/system/status", headers=auth(auth_token))

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"esp", "mqtt", "api", "database"}
    assert body["esp"] == {
        "status": "online",
        "device_id": "ESP32-01",
        "last_seen": body["esp"]["last_seen"],
        "ip": "192.168.1.20",
        "rssi": -58,
        "uptime": 3600,
    }
    assert body["mqtt"]["topics"] == [
        topics.TOPIC_SENSOR,
        topics.TOPIC_CONTROL,
        topics.TOPIC_FEEDBACK,
        topics.TOPIC_STATUS,
    ]
    assert body["api"]["status"] == "running"
    assert body["api"]["version"]
    assert body["database"]["status"] == "connected"
    assert body["database"]["latency_ms"] is not None


def test_health_and_system_use_shared_database_check(
    client, auth_token, monkeypatch
) -> None:
    calls = 0
    real_check = status_service.check_database

    def counted_check():
        nonlocal calls
        calls += 1
        return real_check()

    monkeypatch.setattr(status_service, "check_database", counted_check)

    client.get("/health")
    client.get("/api/v1/system/status", headers=auth(auth_token))

    assert calls == 2
