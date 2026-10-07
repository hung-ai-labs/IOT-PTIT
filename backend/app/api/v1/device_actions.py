"""API lịch sử thao tác điều khiển — SRS §2.4, §2.11, §4.3.5."""

from datetime import datetime
from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, Query, status

from app.core.deps import CurrentUser, DbSession
from app.schemas.common import ErrorResponse, Page
from app.schemas.device import DeviceActionOut
from app.services import action_service, control_service

router = APIRouter(prefix="/device-actions", tags=["device-actions"])


@router.get("", response_model=Page[DeviceActionOut], summary="Tra cứu lịch sử thao tác")
def list_actions(
    user: CurrentUser,
    db: DbSession,
    device_id: Annotated[str | None, Query()] = None,
    target: Annotated[Literal["led", "fan", "ac"] | None, Query()] = None,
    action: Annotated[Literal["ON", "OFF"] | None, Query()] = None,
    result: Annotated[Literal["Pending", "Success", "Failed", "Timeout"] | None, Query()] = None,
    date_from: Annotated[datetime | None, Query(alias="from")] = None,
    date_to: Annotated[datetime | None, Query(alias="to")] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 20,
    sort: Annotated[str, Query(description="Ví dụ: timestamp:desc")] = "timestamp:desc",
) -> Page[DeviceActionOut]:
    """Lọc theo thiết bị, đối tượng, hành động, kết quả và khoảng thời gian (F05, F12)."""
    records, total = action_service.list_actions(
        db,
        device_id=device_id,
        target=target,
        action=action,
        result=result,
        date_from=date_from,
        date_to=date_to,
        page=page,
        size=size,
        sort=sort,
    )
    return Page[DeviceActionOut](
        items=[control_service.to_action_out(record) for record in records],
        page=page,
        size=size,
        total=total,
        total_pages=max(1, -(-total // size)),
    )


@router.get(
    "/{action_id}",
    response_model=DeviceActionOut,
    summary="Trạng thái của một lệnh",
    responses={404: {"model": ErrorResponse, "description": "Không tìm thấy lệnh"}},
)
def get_action(user: CurrentUser, db: DbSession, action_id: int) -> DeviceActionOut:
    """Theo dõi một lệnh vừa gửi cho tới khi có kết quả cuối cùng (F11).

    Frontend gọi lặp endpoint này trong lúc hiển thị trạng thái *đang xử lý*.
    Giai đoạn 5 sẽ thay bằng WebSocket đẩy từ server.
    """
    record = action_service.get(db, action_id)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "ACTION_NOT_FOUND", "message": f"Không tìm thấy lệnh #{action_id}."},
        )
    return control_service.to_action_out(record)
