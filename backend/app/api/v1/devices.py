"""API điều khiển thiết bị — SRS §2.3, §2.9, §2.10, §4.3.4."""

from typing import Annotated

from fastapi import APIRouter, Path, status

from app.core.deps import CurrentUser, DbSession
from app.schemas.common import ErrorResponse
from app.schemas.device import ActionAcceptedOut, ActionRequest, DeviceDetailOut, DeviceOut
from app.services import control_service

router = APIRouter(prefix="/devices", tags=["devices"])

DeviceIdPath = Annotated[str, Path(min_length=1, max_length=50, examples=["ESP32-01"])]


@router.get("", response_model=list[DeviceOut], summary="Danh sách thiết bị và trạng thái")
def list_devices(user: CurrentUser, db: DbSession, device_id: str | None = None) -> list[DeviceOut]:
    """Ba thiết bị chấp hành (Đèn LED, Quạt, Điều hòa) kèm trạng thái ON/OFF và kết nối."""
    return control_service.list_devices(db, device_id)


@router.get("/{device_id}", response_model=DeviceDetailOut, summary="Chi tiết một ESP")
def get_device(user: CurrentUser, db: DbSession, device_id: DeviceIdPath) -> DeviceDetailOut:
    """Thông tin ESP: IP, RSSI, uptime, MQTT topic và các thiết bị gắn trên nó (F10)."""
    return control_service.get_device_detail(db, device_id)


@router.post(
    "/{device_id}/actions",
    response_model=ActionAcceptedOut,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Gửi lệnh điều khiển",
    responses={
        409: {"model": ErrorResponse, "description": "Thiết bị offline hoặc đang có lệnh chờ"},
        503: {"model": ErrorResponse, "description": "MQTT Broker không khả dụng"},
    },
)
def send_action(
    user: CurrentUser, db: DbSession, device_id: DeviceIdPath, payload: ActionRequest
) -> ActionAcceptedOut:
    """Tiếp nhận lệnh và publish lên `iot/control`.

    Trả **202 Accepted** ngay với `result = "Pending"`, không chờ thiết bị phản hồi.
    Theo dõi kết quả bằng `GET /device-actions/{action_id}`.
    """
    return control_service.send_action(
        db,
        device_id=device_id,
        target=payload.target,
        action=payload.action,
        issued_by=user.id,
    )
