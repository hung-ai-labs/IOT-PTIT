"""Thao tác cơ sở dữ liệu trên bảng `device_actions`.

Tầng thấp nhất, chỉ đụng tới DB. Được dùng bởi cả ba nơi:
  • router  (tạo lệnh, tra cứu lịch sử)
  • handler MQTT  (ghi kết quả Success/Failed khi thiết bị phản hồi)
  • registry      (ghi kết quả Timeout khi hết giờ chờ)

Tách riêng để `registry.py` và `control_service.py` không import vòng nhau.
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session, joinedload

from app.db.models.device_action import DeviceAction
from app.db.session import SessionLocal

logger = logging.getLogger(__name__)

SORTABLE_COLUMNS = {
    "id": DeviceAction.id,
    "device_id": DeviceAction.device_id,
    "target": DeviceAction.target,
    "action": DeviceAction.action,
    "result": DeviceAction.result,
    "timestamp": DeviceAction.timestamp,
}


def create_pending(
    db: Session,
    *,
    device_id: str,
    target: str,
    action: str,
    issued_by: int | None,
) -> DeviceAction:
    """Ghi lệnh ở trạng thái Pending trước khi publish lên MQTT."""
    record = DeviceAction(
        device_id=device_id,
        target=target,
        action=action,
        issued_by=issued_by,
        result="Pending",
        cmd_id=uuid.uuid4(),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def mark_result(
    action_id: int,
    result: str,
    *,
    error: str | None = None,
    session: Session | None = None,
) -> bool:
    """Cập nhật kết quả cho một lệnh đang chờ.

    Gọi được từ bất kỳ thread nào (paho-mqtt hoặc threading.Timer) nên tự mở
    session riêng khi không được truyền vào.

    Trả về False nếu lệnh không còn ở trạng thái Pending — nghĩa là đã có nơi
    khác chốt kết quả trước (chống tranh chấp giữa feedback và timeout).
    """
    own_session = session is None
    db = session or SessionLocal()
    try:
        record = db.get(DeviceAction, action_id)
        if record is None:
            logger.warning("Không tìm thấy device_action id=%s", action_id)
            return False

        if record.result != "Pending":
            logger.debug(
                "Bỏ qua cập nhật %s cho lệnh %s: đã là %s",
                result, action_id, record.result,
            )
            return False

        record.result = result
        record.responded_at = datetime.now(UTC)
        record.error_msg = error
        db.commit()
        return True
    except Exception:
        db.rollback()
        logger.exception("Không cập nhật được kết quả cho lệnh %s", action_id)
        return False
    finally:
        if own_session:
            db.close()


def get(db: Session, action_id: int) -> DeviceAction | None:
    return db.get(DeviceAction, action_id)


def get_by_cmd_id(cmd_id, session: Session | None = None) -> DeviceAction | None:
    """Tìm bản ghi theo `cmd_id` nhận từ MQTT. Gọi được từ thread của paho."""
    own_session = session is None
    db = session or SessionLocal()
    try:
        return db.scalars(select(DeviceAction).where(DeviceAction.cmd_id == cmd_id)).first()
    finally:
        if own_session:
            db.close()


def get_last_action(db: Session, device_id: str, target: str) -> DeviceAction | None:
    """Lệnh gần nhất của một thiết bị chấp hành, dùng cho ô 'Lệnh cuối'."""
    return db.scalars(
        select(DeviceAction)
        .where(DeviceAction.device_id == device_id, DeviceAction.target == target)
        .order_by(DeviceAction.timestamp.desc())
        .limit(1)
    ).first()


def get_last_successful_states(db: Session) -> dict[tuple[str, str], bool]:
    """Trạng thái ON/OFF cuối cùng đã được thiết bị xác nhận, cho mỗi (thiết bị, đối tượng).

    Dùng để khôi phục `DeviceStateCache` sau khi server khởi động lại.
    """
    latest_ids = (
        select(func.max(DeviceAction.id))
        .where(DeviceAction.result == "Success")
        .group_by(DeviceAction.device_id, DeviceAction.target)
    )
    rows = db.scalars(select(DeviceAction).where(DeviceAction.id.in_(latest_ids)))
    return {(row.device_id, row.target): row.action == "ON" for row in rows}


def _apply_filters(
    statement: Select,
    *,
    device_id: str | None,
    target: str | None,
    action: str | None,
    result: str | None,
    date_from: datetime | None,
    date_to: datetime | None,
) -> Select:
    if device_id:
        statement = statement.where(DeviceAction.device_id == device_id)
    if target:
        statement = statement.where(DeviceAction.target == target)
    if action:
        statement = statement.where(DeviceAction.action == action)
    if result:
        statement = statement.where(DeviceAction.result == result)
    if date_from:
        statement = statement.where(DeviceAction.timestamp >= date_from)
    if date_to:
        statement = statement.where(DeviceAction.timestamp <= date_to)
    return statement


def list_actions(
    db: Session,
    *,
    device_id: str | None = None,
    target: str | None = None,
    action: str | None = None,
    result: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    page: int = 1,
    size: int = 20,
    sort: str = "timestamp:desc",
) -> tuple[list[DeviceAction], int]:
    """Tra cứu lịch sử thao tác có lọc, sắp xếp và phân trang (F05, F12)."""
    filters = {
        "device_id": device_id,
        "target": target,
        "action": action,
        "result": result,
        "date_from": date_from,
        "date_to": date_to,
    }

    total = db.scalar(
        _apply_filters(select(func.count()).select_from(DeviceAction), **filters)
    ) or 0

    field, _, direction = sort.partition(":")
    column = SORTABLE_COLUMNS.get(field, DeviceAction.timestamp)
    order = column.asc() if direction == "asc" else column.desc()

    statement = (
        _apply_filters(select(DeviceAction), **filters)
        .options(joinedload(DeviceAction.issuer))
        .order_by(order, DeviceAction.id.desc())
        .offset((page - 1) * size)
        .limit(size)
    )
    return list(db.scalars(statement)), total
