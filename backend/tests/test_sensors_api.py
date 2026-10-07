"""Kiểm thử API dữ liệu cảm biến — Giai đoạn 3 (F03, F12)."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from app.db.models.sensor import DataSensor

UNITS = {"temperature": "°C", "humidity": "%", "light": "lux"}


@pytest.fixture
def seeded(client, db_session):
    """10 chu kỳ đo, mỗi chu kỳ 3 loại cảm biến, cách nhau 1 phút."""
    now = datetime.now(UTC)
    rows = []
    for i in range(10):
        moment = now - timedelta(minutes=i)
        for sensor_type, value in (
            ("temperature", 25 + i),
            ("humidity", 60 + i),
            ("light", 200 + i),
        ):
            rows.append(
                DataSensor(
                    device_id="ESP32-01" if i % 2 == 0 else "ESP32-02",
                    sensor_type=sensor_type,
                    value=Decimal(f"{value}.00"),
                    unit=UNITS[sensor_type],
                    timestamp=moment,
                )
            )
    db_session.add_all(rows)
    db_session.commit()
    return rows


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


# ─── Bảo vệ bằng token ───────────────────────────────────────
@pytest.mark.parametrize("path", ["/api/v1/sensors", "/api/v1/sensors/latest", "/api/v1/sensors/series"])
def test_endpoints_require_authentication(client, path) -> None:
    assert client.get(path).status_code == 401


# ─── GET /sensors ────────────────────────────────────────────
def test_list_returns_paginated_records(client, auth_token, seeded) -> None:
    response = client.get("/api/v1/sensors?size=5", headers=auth(auth_token))

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 30
    assert body["size"] == 5
    assert body["total_pages"] == 6
    assert len(body["items"]) == 5


def test_list_filters_by_sensor_type(client, auth_token, seeded) -> None:
    response = client.get(
        "/api/v1/sensors?sensor_type=temperature&size=100", headers=auth(auth_token)
    )

    body = response.json()
    assert body["total"] == 10
    assert {item["sensor_type"] for item in body["items"]} == {"temperature"}


def test_list_filters_by_device(client, auth_token, seeded) -> None:
    response = client.get("/api/v1/sensors?device_id=ESP32-02&size=100", headers=auth(auth_token))

    body = response.json()
    assert body["total"] == 15
    assert {item["device_id"] for item in body["items"]} == {"ESP32-02"}


def test_list_filters_by_time_range(client, auth_token, seeded) -> None:
    # Dùng params= để httpx tự URL-encode; nếu ghép chuỗi thẳng thì dấu "+"
    # trong offset "+00:00" bị hiểu thành dấu cách và API trả 422.
    response = client.get(
        "/api/v1/sensors",
        params={
            # Lấy mốc 3 phút 30 giây để chu kỳ i=3 nằm hẳn trong khoảng,
            # không phụ thuộc vài mili-giây lệch giữa lúc nạp dữ liệu và lúc gọi.
            "from": (datetime.now(UTC) - timedelta(minutes=3, seconds=30)).isoformat(),
            "size": 100,
        },
        headers=auth(auth_token),
    )

    assert response.status_code == 200
    # 4 chu kỳ (0–3 phút trước) × 3 loại
    assert response.json()["total"] == 12


def test_list_rejects_unencoded_timestamp(client, auth_token) -> None:
    """Ghi lại hành vi: client phải URL-encode mốc thời gian có offset."""
    response = client.get(
        "/api/v1/sensors?from=2026-09-09T01:00:00+00:00", headers=auth(auth_token)
    )

    assert response.status_code == 422


def test_list_sorts_by_value_ascending(client, auth_token, seeded) -> None:
    response = client.get(
        "/api/v1/sensors?sensor_type=temperature&sort=value:asc&size=100",
        headers=auth(auth_token),
    )

    values = [item["value"] for item in response.json()["items"]]
    assert values == sorted(values)


def test_list_defaults_to_newest_first(client, auth_token, seeded) -> None:
    response = client.get("/api/v1/sensors?size=100", headers=auth(auth_token))

    timestamps = [item["timestamp"] for item in response.json()["items"]]
    assert timestamps == sorted(timestamps, reverse=True)


def test_list_rejects_oversized_page(client, auth_token) -> None:
    response = client.get("/api/v1/sensors?size=999", headers=auth(auth_token))

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "VALIDATION_ERROR"


def test_list_rejects_unknown_sensor_type(client, auth_token) -> None:
    assert client.get("/api/v1/sensors?sensor_type=áp suất", headers=auth(auth_token)).status_code == 422


def test_empty_database_returns_empty_page(client, auth_token) -> None:
    response = client.get("/api/v1/sensors", headers=auth(auth_token))

    body = response.json()
    assert body["items"] == []
    assert body["total"] == 0
    assert body["total_pages"] == 1


# ─── GET /sensors/latest ─────────────────────────────────────
def test_latest_returns_newest_value_per_type(client, auth_token, seeded) -> None:
    response = client.get("/api/v1/sensors/latest", headers=auth(auth_token))

    body = response.json()
    # Chu kỳ i=0 là mới nhất → temp 25, humidity 60, light 200
    assert body["temperature"]["value"] == 25
    assert body["temperature"]["unit"] == "°C"
    assert body["humidity"]["value"] == 60
    assert body["light"]["value"] == 200


def test_latest_can_filter_by_device(client, auth_token, seeded) -> None:
    response = client.get("/api/v1/sensors/latest?device_id=ESP32-02", headers=auth(auth_token))

    # ESP32-02 chỉ có các chu kỳ lẻ; mới nhất là i=1 → temp 26
    assert response.json()["temperature"]["value"] == 26


def test_latest_with_no_data_returns_nulls(client, auth_token) -> None:
    body = client.get("/api/v1/sensors/latest", headers=auth(auth_token)).json()

    assert body["temperature"] is None
    assert body["humidity"] is None
    assert body["light"] is None


# ─── GET /sensors/series ─────────────────────────────────────
def test_series_groups_into_buckets(client, auth_token, seeded) -> None:
    response = client.get("/api/v1/sensors/series?bucket=1m&points=20", headers=auth(auth_token))

    assert response.status_code == 200
    points = response.json()
    assert len(points) <= 20
    assert points
    first = points[0]
    assert set(first) >= {"time", "timestamp", "temp", "humidity", "light"}
    assert len(first["time"]) == 5  # định dạng HH:MM


def test_series_respects_points_limit(client, auth_token, seeded) -> None:
    points = client.get(
        "/api/v1/sensors/series?bucket=1m&points=5", headers=auth(auth_token)
    ).json()

    assert len(points) <= 5


def test_series_with_no_data_is_empty(client, auth_token) -> None:
    assert client.get("/api/v1/sensors/series", headers=auth(auth_token)).json() == []


def test_series_rejects_unknown_bucket(client, auth_token) -> None:
    assert client.get("/api/v1/sensors/series?bucket=7s", headers=auth(auth_token)).status_code == 422
