"""Xử lý bản tin nhận được từ MQTT Broker.

Các hàm ở đây chạy trong thread của paho-mqtt, **không** phải event loop của
FastAPI, nên dùng session đồng bộ và không được gọi coroutine trực tiếp.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from decimal import Decimal

from pydantic import ValidationError

from app.core.config import SENSOR_RANGES, SENSOR_UNITS
from app.db.models.sensor import DataSensor
from app.db.session import SessionLocal
from app.mqtt.registry import pending_commands
from app.schemas.mqtt import FeedbackPayload, SensorPayload, StatusPayload
from app.services import action_service
from app.state.device_cache import device_cache
from app.ws.hub import broadcast_from_thread

logger = logging.getLogger(__name__)

# Tên trường trong payload MQTT → loại cảm biến trong cơ sở dữ liệu
FIELD_TO_SENSOR_TYPE = {
    "temp": "temperature",
    "humid": "humidity",
    "light": "light",
}


def _in_range(sensor_type: str, value: float) -> bool:
    low, high = SENSOR_RANGES[sensor_type]
    return low <= value <= high


def handle_sensor_message(raw: bytes) -> int:
    """Ghi bản tin cảm biến vào cơ sở dữ liệu.

    Một bản tin chứa tối đa 3 giá trị nên sinh tối đa 3 dòng `data_sensor`
    (SRS §2.6: mỗi bản ghi gồm loại cảm biến, giá trị và đơn vị riêng).

    Trả về số dòng đã ghi.
    """
    try:
        payload = SensorPayload.model_validate_json(raw)
    except ValidationError as exc:
        logger.warning("Bỏ qua bản tin iot/sensor sai định dạng: %s", exc.errors()[:2])
        return 0

    measured_at = payload.ts or datetime.now(UTC)
    rows: list[DataSensor] = []

    for field, sensor_type in FIELD_TO_SENSOR_TYPE.items():
        value = getattr(payload, field)
        if value is None:
            continue

        if not _in_range(sensor_type, value):
            logger.warning(
                "Bỏ qua %s=%s của %s: ngoài biên %s",
                sensor_type, value, payload.device_id, SENSOR_RANGES[sensor_type],
            )
            continue

        rows.append(
            DataSensor(
                device_id=payload.device_id,
                sensor_type=sensor_type,
                value=Decimal(f"{value:.2f}"),
                unit=SENSOR_UNITS[sensor_type],
                timestamp=measured_at,
            )
        )

    # Thiết bị vẫn được coi là online kể cả khi mọi giá trị đều ngoài biên.
    device_cache.touch(payload.device_id)

    if not rows:
        return 0

    session = SessionLocal()
    try:
        session.add_all(rows)
        session.commit()
    except Exception:
        session.rollback()
        logger.exception("Không ghi được dữ liệu cảm biến của %s", payload.device_id)
        return 0
    finally:
        session.close()

    logger.debug("Đã ghi %d giá trị cảm biến từ %s", len(rows), payload.device_id)
    values = {row.sensor_type: float(row.value) for row in rows}
    broadcast_from_thread(
        "sensor",
        {
            "device_id": payload.device_id,
            "temperature": values.get("temperature"),
            "humidity": values.get("humidity"),
            "light": values.get("light"),
            "timestamp": measured_at.isoformat(),
        },
    )
    return len(rows)


def handle_status_message(raw: bytes) -> None:
    """Cập nhật heartbeat hoặc Last Will của thiết bị."""
    try:
        payload = StatusPayload.model_validate_json(raw)
    except ValidationError as exc:
        logger.warning("Bỏ qua bản tin iot/status sai định dạng: %s", exc.errors()[:2])
        return

    if payload.status == "offline":
        device_cache.mark_offline(payload.device_id)
        logger.info("Thiết bị %s báo offline (Last Will).", payload.device_id)
        return

    device_cache.touch(
        payload.device_id, ip=payload.ip, rssi=payload.rssi, uptime=payload.uptime
    )


def handle_feedback_message(raw: bytes) -> None:
    """Chốt kết quả một lệnh điều khiển từ phản hồi của thiết bị (F11).

    Ba tình huống:
      • có `cmd_id` và lệnh còn chờ  → cập nhật Success/Failed vào device_actions
      • có `cmd_id` nhưng đã timeout → chỉ ghi log, KHÔNG ghi đè kết quả Timeout
      • không có `cmd_id`            → thiết bị tự đổi trạng thái (nút bấm tay),
                                       chỉ cập nhật cache
    """
    try:
        payload = FeedbackPayload.model_validate_json(raw)
    except ValidationError as exc:
        logger.warning("Bỏ qua bản tin iot/feedback sai định dạng: %s", exc.errors()[:2])
        return

    device_cache.touch(payload.device_id)

    # Chỉ đổi trạng thái hiển thị khi thiết bị báo thực thi thành công.
    if payload.result == "Success":
        device_cache.set_target_state(payload.device_id, payload.target, payload.state == "ON")

    if payload.cmd_id is None:
        logger.info(
            "Thiết bị %s tự đổi %s → %s (không kèm cmd_id)",
            payload.device_id, payload.target, payload.state,
        )
        return

    command = pending_commands.resolve(payload.cmd_id)
    if command is None:
        # Không còn trong danh sách chờ. Tra cơ sở dữ liệu để biết vì sao, thay vì
        # đoán bừa: lệnh STATUS lúc khởi động cũng không hề được đăng ký.
        try:
            record = action_service.get_by_cmd_id(payload.cmd_id)
        except Exception:  # noqa: BLE001 — lỗi DB không được làm chết thread nhận MQTT
            logger.warning(
                "Không kiểm tra được phản hồi lạ %s trong cơ sở dữ liệu.",
                payload.cmd_id,
                exc_info=True,
            )
            return
        if record is None:
            logger.debug(
                "Bỏ qua phản hồi cho cmd_id %s: không phải lệnh do người dùng gửi "
                "(ví dụ lệnh STATUS lúc khởi động).",
                payload.cmd_id,
            )
        else:
            logger.warning(
                "Phản hồi đến muộn cho lệnh %s — đã chốt %s trước đó.",
                payload.cmd_id, record.result,
            )
        return

    updated = action_service.mark_result(
        command.action_id, payload.result, error=payload.error
    )
    if updated:
        broadcast_from_thread(
            "device_state",
            {
                "device_id": payload.device_id,
                "target": payload.target,
                "state": payload.state,
                "action_id": command.action_id,
                "result": payload.result,
                "error_msg": payload.error,
            },
        )
    logger.info(
        "Lệnh %s (%s %s): %s",
        payload.cmd_id, command.target, command.action, payload.result,
    )
