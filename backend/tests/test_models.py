"""Kiểm thử ràng buộc của model trên SQLite trong bộ nhớ (không cần PostgreSQL)."""

import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from app.db.base import Base, DataSensor, DeviceAction, User


@pytest.fixture
def db():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def test_email_must_be_unique(db) -> None:
    db.add(User(full_name="A", email="a@ptit.edu.vn", password_hash="x"))
    db.commit()

    db.add(User(full_name="B", email="a@ptit.edu.vn", password_hash="y"))
    with pytest.raises(IntegrityError):
        db.commit()


def test_sensor_type_is_constrained(db) -> None:
    db.add(
        DataSensor(
            device_id="ESP32-01", sensor_type="áp suất", value=1, unit="hPa"
        )
    )
    with pytest.raises(IntegrityError):
        db.commit()


def test_device_action_defaults_to_pending(db) -> None:
    user = User(full_name="A", email="a@ptit.edu.vn", password_hash="x")
    db.add(user)
    db.flush()

    action = DeviceAction(
        device_id="ESP32-01",
        target="fan",
        action="ON",
        issued_by=user.id,
        cmd_id=uuid.uuid4(),
    )
    db.add(action)
    db.commit()

    assert action.result == "Pending"
    assert action.issuer is user


def test_invalid_result_is_rejected(db) -> None:
    db.add(
        DeviceAction(
            device_id="ESP32-01",
            target="fan",
            action="ON",
            result="Unknown",
            cmd_id=uuid.uuid4(),
        )
    )
    with pytest.raises(IntegrityError):
        db.commit()
