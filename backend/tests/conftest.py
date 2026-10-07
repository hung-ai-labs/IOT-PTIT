"""Fixture dùng chung: ứng dụng chạy trên SQLite trong bộ nhớ, không cần PostgreSQL.

QUAN TRỌNG: phải tắt MQTT trước khi import `app.main`. Nếu không, mỗi TestClient
sẽ chạy lifespan thật — kết nối vào broker, publish lệnh STATUS, và ghi dữ liệu
cảm biến nhận được vào PostgreSQL của môi trường phát triển.
"""

import os

os.environ["ENABLE_MQTT"] = "false"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.core import token_store  # noqa: E402
from app.core.config import settings  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.db.session import get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.state.device_cache import device_cache  # noqa: E402

assert settings.enable_mqtt is False, (
    "Kiểm thử không được kết nối MQTT thật — kiểm tra ENABLE_MQTT trong conftest."
)


@pytest.fixture
def _database():
    """Cơ sở dữ liệu SQLite trong bộ nhớ, dùng chung một kết nối."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    yield TestingSession

    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def db_session(_database):
    """Session để bài kiểm thử nạp sẵn dữ liệu."""
    session = _database()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(_database):
    def override_get_db():
        db = _database()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    token_store.clear()
    device_cache.clear()

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    token_store.clear()
    device_cache.clear()


@pytest.fixture
def registered_user(client):
    """Tạo sẵn một tài khoản và trả về thông tin đăng nhập."""
    payload = {
        "full_name": "Nguyễn Xuân Hùng",
        "email": "hung@ptit.edu.vn",
        "password": "123456",
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201
    return payload


@pytest.fixture
def auth_token(client, registered_user):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": registered_user["email"], "password": registered_user["password"]},
    )
    assert response.status_code == 200
    return response.json()["access_token"]
