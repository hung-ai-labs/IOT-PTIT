"""Nghiệp vụ điều khiển thiết bị (F04, F08, F10, F11, F13)."""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import DEVICE_REGISTRY, settings
from app.db.models.device_action import DeviceAction
from app.mqtt import topics
from app.mqtt.client import mqtt_service
from app.mqtt.registry import pending_commands
from app.schemas.device import ActionAcceptedOut, DeviceActionOut, DeviceDetailOut, DeviceOut
from app.services import action_service
from app.state.device_cache import device_cache

logger = logging.getLogger(__name__)

# Thiết bị mặc định khi client không nói rõ — hệ thống demo chỉ có một ESP (OQ-08).
DEFAULT_DEVICE_ID = "ESP32-01"


def target_label(target: str) -> str:
    return DEVICE_REGISTRY.get(target, {}).get("name", target)


# ─── Đọc trạng thái ──────────────────────────────────────────
def _build_device_out(db: Session, device_id: str, target: str) -> DeviceOut:
    config = DEVICE_REGISTRY[target]
    cached = device_cache.get(device_id)
    last_action = action_service.get_last_action(db, device_id, target)

    return DeviceOut(
        device_id=device_id,
        target=target,
        name=config["name"],
        gpio=config["gpio"],
        icon=config["icon"],
        state="ON" if (cached and cached.targets.get(target)) else "OFF",
        connection="online" if (cached and cached.online) else "offline",
        last_command=last_action.timestamp if last_action else None,
        last_seen=cached.last_seen if cached else None,
    )


def list_devices(db: Session, device_id: str | None = None) -> list[DeviceOut]:
    """Ba thiết bị chấp hành của một ESP, kèm trạng thái hiện tại."""
    resolved = device_id or _resolve_default_device_id()
    return [_build_device_out(db, resolved, target) for target in DEVICE_REGISTRY]


def get_device_detail(db: Session, device_id: str) -> DeviceDetailOut:
    cached = device_cache.get(device_id)
    return DeviceDetailOut(
        device_id=device_id,
        connection="online" if (cached and cached.online) else "offline",
        ip=cached.ip if cached else None,
        rssi=cached.rssi if cached else None,
        uptime=cached.uptime if cached else None,
        last_seen=cached.last_seen if cached else None,
        command_topic=topics.TOPIC_CONTROL,
        feedback_topic=topics.TOPIC_FEEDBACK,
        targets=[_build_device_out(db, device_id, target) for target in DEVICE_REGISTRY],
    )


def _resolve_default_device_id() -> str:
    """Lấy ESP đầu tiên đã từng gửi tin; nếu chưa có thì dùng mã mặc định."""
    devices = device_cache.all()
    return devices[0].device_id if devices else DEFAULT_DEVICE_ID


def to_action_out(record: DeviceAction) -> DeviceActionOut:
    return DeviceActionOut(
        id=record.id,
        device_id=record.device_id,
        target=record.target,
        target_label=target_label(record.target),
        action=record.action,
        issued_by=record.issuer,
        result=record.result,
        timestamp=record.timestamp,
        responded_at=record.responded_at,
        error_msg=record.error_msg,
    )


# ─── Gửi lệnh ────────────────────────────────────────────────
def _reject(code: str, message: str, http_status: int) -> HTTPException:
    return HTTPException(status_code=http_status, detail={"code": code, "message": message})


def _ensure_can_send(device_id: str, target: str) -> None:
    """Ba điều kiện chặn lệnh (F13, SRS §2.8)."""
    if not mqtt_service.connected:
        raise _reject(
            "MQTT_UNAVAILABLE",
            "Chưa kết nối được MQTT Broker. Không thể gửi lệnh điều khiển.",
            status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    cached = device_cache.get(device_id)
    if cached is None or not cached.online:
        raise _reject(
            "DEVICE_OFFLINE",
            f"Thiết bị {device_id} đang mất kết nối. "
            f"Không nhận được tin nào trong {settings.device_offline_seconds} giây qua.",
            status.HTTP_409_CONFLICT,
        )

    if pending_commands.has_pending(device_id, target):
        raise _reject(
            "COMMAND_IN_PROGRESS",
            f"Đang có lệnh chờ xử lý cho {target_label(target)}. Vui lòng đợi kết quả.",
            status.HTTP_409_CONFLICT,
        )


def send_action(
    db: Session, *, device_id: str, target: str, action: str, issued_by: int | None
) -> ActionAcceptedOut:
    """Ghi lệnh Pending, publish lên MQTT rồi trả về ngay — không chờ thiết bị.

    Kết quả cuối cùng đến sau qua `iot/feedback` hoặc do đồng hồ timeout chốt;
    client theo dõi bằng `GET /device-actions/{action_id}`.
    """
    _ensure_can_send(device_id, target)

    record = action_service.create_pending(
        db, device_id=device_id, target=target, action=action, issued_by=issued_by
    )

    published = mqtt_service.publish(
        topics.TOPIC_CONTROL,
        {
            "cmd_id": str(record.cmd_id),
            "device_id": device_id,
            "target": target,
            "action": action,
            "issued_at": datetime.now(UTC).isoformat(),
        },
    )

    if not published:
        # Không publish được thì chốt Failed luôn, đừng để lệnh treo ở Pending.
        action_service.mark_result(
            record.id, "Failed", error="Không publish được lệnh lên MQTT Broker", session=db
        )
        raise _reject(
            "MQTT_UNAVAILABLE",
            "Không gửi được lệnh lên MQTT Broker.",
            status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    pending_commands.register(record.cmd_id, record.id, device_id, target, action)

    return ActionAcceptedOut(
        action_id=record.id,
        cmd_id=record.cmd_id,
        device_id=device_id,
        target=target,
        action=action,
        result="Pending",
        timeout_seconds=settings.command_timeout_seconds,
    )


# ─── Khôi phục sau khi khởi động lại ─────────────────────────
def restore_device_states(db: Session) -> int:
    """Nạp lại trạng thái ON/OFF từ lệnh thành công gần nhất của mỗi thiết bị.

    `DeviceStateCache` nằm trong RAM nên mất khi restart. Đây là phương án tạm;
    `request_status_refresh()` mới cho trạng thái thật từ phần cứng.
    """
    states = action_service.get_last_successful_states(db)
    for (device_id, target), is_on in states.items():
        device_cache.set_target_state(device_id, target, is_on)

    if states:
        logger.info("Khôi phục trạng thái %d thiết bị chấp hành từ lịch sử.", len(states))
    return len(states)


def request_status_refresh(device_ids: list[str]) -> None:
    """Yêu cầu thiết bị báo lại trạng thái thật (action `STATUS`).

    Không tạo bản ghi `device_actions` vì đây không phải thao tác của người dùng.
    """
    import uuid

    for device_id in device_ids:
        for target in DEVICE_REGISTRY:
            mqtt_service.publish(
                topics.TOPIC_CONTROL,
                {
                    "cmd_id": str(uuid.uuid4()),
                    "device_id": device_id,
                    "target": target,
                    "action": "STATUS",
                    "issued_at": datetime.now(UTC).isoformat(),
                },
            )
