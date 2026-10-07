"""API dữ liệu cảm biến — SRS §2.2, §2.11, §4.3.3."""

from datetime import datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Query

from app.core.deps import CurrentUser, DbSession
from app.schemas.common import Page
from app.schemas.sensor import LatestSensorOut, SensorRecordOut, SeriesPoint
from app.services import sensor_service

router = APIRouter(prefix="/sensors", tags=["sensors"])

SensorTypeQuery = Annotated[
    Literal["temperature", "humidity", "light"] | None,
    Query(description="Lọc theo loại cảm biến"),
]
DeviceQuery = Annotated[str | None, Query(description="Mã thiết bị IoT, ví dụ ESP32-01")]
FromQuery = Annotated[datetime | None, Query(alias="from", description="Mốc bắt đầu (ISO-8601)")]
ToQuery = Annotated[datetime | None, Query(alias="to", description="Mốc kết thúc (ISO-8601)")]


@router.get("/latest", response_model=LatestSensorOut, summary="Giá trị cảm biến mới nhất")
def latest(user: CurrentUser, db: DbSession, device_id: DeviceQuery = None) -> LatestSensorOut:
    """Giá trị mới nhất của nhiệt độ, độ ẩm và ánh sáng — dùng cho 3 thẻ trên Dashboard."""
    return sensor_service.get_latest(db, device_id)


@router.get("/series", response_model=list[SeriesPoint], summary="Dữ liệu cho biểu đồ")
def series(
    user: CurrentUser,
    db: DbSession,
    device_id: DeviceQuery = None,
    date_from: FromQuery = None,
    date_to: ToQuery = None,
    bucket: Annotated[Literal["1m", "5m", "1h"], Query()] = "1m",
    points: Annotated[int, Query(ge=5, le=200, description="Số cột tối đa")] = 30,
) -> list[SeriesPoint]:
    """Dữ liệu đã gom nhóm theo khoảng thời gian, tránh đổ hàng chục nghìn điểm vào biểu đồ."""
    return sensor_service.get_series(
        db,
        device_id=device_id,
        date_from=date_from,
        date_to=date_to,
        bucket=bucket,
        points=points,
    )


@router.get("", response_model=Page[SensorRecordOut], summary="Tra cứu lịch sử dữ liệu cảm biến")
def list_records(
    user: CurrentUser,
    db: DbSession,
    device_id: DeviceQuery = None,
    sensor_type: SensorTypeQuery = None,
    date_from: FromQuery = None,
    date_to: ToQuery = None,
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 20,
    sort: Annotated[str, Query(description="Ví dụ: timestamp:desc, value:asc")] = "timestamp:desc",
) -> Page[SensorRecordOut]:
    """Lọc, sắp xếp và phân trang bảng `data_sensor` (F12)."""
    records, total = sensor_service.list_records(
        db,
        device_id=device_id,
        sensor_type=sensor_type,
        date_from=date_from,
        date_to=date_to,
        page=page,
        size=size,
        sort=sort,
    )
    return Page[SensorRecordOut](
        items=[SensorRecordOut.model_validate(record) for record in records],
        page=page,
        size=size,
        total=total,
        total_pages=max(1, -(-total // size)),
    )
