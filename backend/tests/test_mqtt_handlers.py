"""Kiểm thử xử lý bản tin MQTT — Giai đoạn 3 (F07)."""

import json
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.mqtt.handlers as handlers
from app.db.base import Base
from app.db.models.sensor import DataSensor
from app.state.device_cache import device_cache


@pytest.fixture
def db(monkeypatch):
    """Cho handler ghi vào SQLite trong bộ nhớ thay vì PostgreSQL."""
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    monkeypatch.setattr(handlers, "SessionLocal", TestingSession)
    device_cache.clear()

    session = TestingSession()
    try:
        yield session
    finally:
        session.close()
        device_cache.clear()
        engine.dispose()


def payload(**fields) -> bytes:
    return json.dumps(fields).encode()


# ─── iot/sensor ──────────────────────────────────────────────
def test_sensor_message_creates_one_row_per_type(db) -> None:
    written = handlers.handle_sensor_message(
        payload(device_id="ESP32-01", temp=27.5, humid=62, light=243)
    )

    assert written == 3
    rows = db.scalars(select(DataSensor).order_by(DataSensor.sensor_type)).all()
    assert [r.sensor_type for r in rows] == ["humidity", "light", "temperature"]
    assert [r.unit for r in rows] == ["%", "lux", "°C"]
    assert float(next(r.value for r in rows if r.sensor_type == "temperature")) == 27.5


def test_sensor_message_broadcasts_after_commit(db, monkeypatch) -> None:
    events = []
    monkeypatch.setattr(
        handlers, "broadcast_from_thread", lambda event_type, data: events.append((event_type, data))
    )

    written = handlers.handle_sensor_message(
        payload(device_id="ESP32-01", temp=27.5, humid=62, light=243)
    )

    assert written == 3
    assert events[0][0] == "sensor"
    assert events[0][1]["temperature"] == 27.5
    assert events[0][1]["device_id"] == "ESP32-01"


def test_partial_payload_writes_only_present_fields(db) -> None:
    written = handlers.handle_sensor_message(payload(device_id="ESP32-01", temp=27.5))

    assert written == 1
    assert db.scalar(select(func.count()).select_from(DataSensor)) == 1


def test_out_of_range_values_are_skipped(db) -> None:
    written = handlers.handle_sensor_message(
        payload(device_id="ESP32-01", temp=999, humid=500, light=-5)
    )

    assert written == 0
    assert db.scalar(select(func.count()).select_from(DataSensor)) == 0


def test_out_of_range_value_does_not_block_valid_ones(db) -> None:
    written = handlers.handle_sensor_message(
        payload(device_id="ESP32-01", temp=999, humid=62, light=243)
    )

    assert written == 2


def test_malformed_json_is_ignored(db) -> None:
    assert handlers.handle_sensor_message(b"khong phai json") == 0
    assert db.scalar(select(func.count()).select_from(DataSensor)) == 0


def test_missing_device_id_is_ignored(db) -> None:
    assert handlers.handle_sensor_message(payload(temp=25)) == 0


def test_wrong_type_is_ignored(db) -> None:
    assert handlers.handle_sensor_message(payload(device_id="ESP32-01", temp="nóng")) == 0


def test_sensor_message_marks_device_online(db) -> None:
    handlers.handle_sensor_message(payload(device_id="ESP32-01", temp=27.5))

    device = device_cache.get("ESP32-01")
    assert device is not None
    assert device.online is True


def test_explicit_timestamp_is_used(db) -> None:
    """Nếu bản tin có `ts` thì dùng nó, không lấy thời điểm nhận."""
    moment = datetime.now(UTC) - timedelta(hours=2)
    handlers.handle_sensor_message(
        payload(device_id="ESP32-01", temp=27.5, ts=moment.isoformat())
    )

    stored = db.scalars(select(DataSensor)).one().timestamp
    # SQLite không lưu offset nên trả về datetime naive; PostgreSQL (TIMESTAMPTZ)
    # trả về datetime có timezone. Chuẩn hoá về UTC rồi mới so sánh.
    if stored.tzinfo is None:
        stored = stored.replace(tzinfo=UTC)

    assert abs((stored - moment).total_seconds()) < 1


# ─── iot/status ──────────────────────────────────────────────
def test_status_online_updates_cache(db) -> None:
    handlers.handle_status_message(
        payload(device_id="ESP32-01", status="online", ip="192.168.1.105", rssi=-58)
    )

    device = device_cache.get("ESP32-01")
    assert device.online is True
    assert device.ip == "192.168.1.105"
    assert device.rssi == -58


def test_last_will_marks_device_offline(db) -> None:
    handlers.handle_status_message(payload(device_id="ESP32-01", status="online"))
    handlers.handle_status_message(payload(device_id="ESP32-01", status="offline"))

    assert device_cache.get("ESP32-01").online is False


# ─── iot/feedback ────────────────────────────────────────────
def test_feedback_success_updates_target_state(db) -> None:
    handlers.handle_feedback_message(
        payload(device_id="ESP32-01", target="fan", state="ON", result="Success")
    )

    assert device_cache.get("ESP32-01").targets["fan"] is True


def test_feedback_failed_does_not_change_state(db) -> None:
    handlers.handle_feedback_message(
        payload(device_id="ESP32-01", target="fan", state="ON", result="Failed")
    )

    assert "fan" not in device_cache.get("ESP32-01").targets


def test_feedback_with_unknown_target_is_ignored(db) -> None:
    handlers.handle_feedback_message(
        payload(device_id="ESP32-01", target="máy giặt", state="ON", result="Success")
    )

    assert device_cache.get("ESP32-01") is None
