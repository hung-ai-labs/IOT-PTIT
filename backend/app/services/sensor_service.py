"""Truy vấn dữ liệu cảm biến phục vụ API."""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.db.models.sensor import DataSensor
from app.schemas.sensor import LatestSensorOut, SensorReading, SeriesPoint

# Múi giờ hiển thị. Cơ sở dữ liệu luôn lưu UTC (docs/02-DATABASE.md §4).
DISPLAY_TZ = ZoneInfo("Asia/Ho_Chi_Minh")

# Độ rộng mỗi cột của biểu đồ.
BUCKET_SECONDS = {"1m": 60, "5m": 300, "1h": 3600}

# Gom nhóm thực hiện bằng Python nên phải chặn số dòng đọc lên.
# Với 3 loại cảm biến, 5 giây/lần thì 20.000 dòng ≈ 9 giờ dữ liệu.
MAX_SERIES_ROWS = 20_000

SORTABLE_COLUMNS = {
    "id": DataSensor.id,
    "device_id": DataSensor.device_id,
    "sensor_type": DataSensor.sensor_type,
    "value": DataSensor.value,
    "timestamp": DataSensor.timestamp,
}


def _apply_filters(
    statement: Select,
    *,
    device_id: str | None,
    sensor_type: str | None,
    date_from: datetime | None,
    date_to: datetime | None,
) -> Select:
    if device_id:
        statement = statement.where(DataSensor.device_id == device_id)
    if sensor_type:
        statement = statement.where(DataSensor.sensor_type == sensor_type)
    if date_from:
        statement = statement.where(DataSensor.timestamp >= date_from)
    if date_to:
        statement = statement.where(DataSensor.timestamp <= date_to)
    return statement


def list_records(
    db: Session,
    *,
    device_id: str | None = None,
    sensor_type: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    page: int = 1,
    size: int = 20,
    sort: str = "timestamp:desc",
) -> tuple[list[DataSensor], int]:
    """Tra cứu có lọc, sắp xếp và phân trang (F12). Trả về (danh sách, tổng số)."""
    filters = {
        "device_id": device_id,
        "sensor_type": sensor_type,
        "date_from": date_from,
        "date_to": date_to,
    }

    total = db.scalar(
        _apply_filters(select(func.count()).select_from(DataSensor), **filters)
    ) or 0

    field, _, direction = sort.partition(":")
    column = SORTABLE_COLUMNS.get(field, DataSensor.timestamp)
    order = column.asc() if direction == "asc" else column.desc()

    statement = (
        _apply_filters(select(DataSensor), **filters)
        # Thêm id để thứ tự ổn định khi nhiều dòng cùng timestamp.
        .order_by(order, DataSensor.id.desc())
        .offset((page - 1) * size)
        .limit(size)
    )
    return list(db.scalars(statement)), total


def get_latest(db: Session, device_id: str | None = None) -> LatestSensorOut:
    """Giá trị mới nhất của từng loại cảm biến."""
    result = LatestSensorOut(device_id=device_id)

    for sensor_type in ("temperature", "humidity", "light"):
        statement = select(DataSensor).where(DataSensor.sensor_type == sensor_type)
        if device_id:
            statement = statement.where(DataSensor.device_id == device_id)

        row = db.scalars(statement.order_by(DataSensor.timestamp.desc()).limit(1)).first()
        if row is None:
            continue

        setattr(
            result,
            sensor_type,
            SensorReading(value=float(row.value), unit=row.unit, timestamp=row.timestamp),
        )
        if result.device_id is None:
            result.device_id = row.device_id

    return result


def get_series(
    db: Session,
    *,
    device_id: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    bucket: str = "1m",
    points: int = 30,
) -> list[SeriesPoint]:
    """Dữ liệu đã gom nhóm cho biểu đồ Dashboard.

    Gom nhóm bằng Python thay vì SQL để mã chạy được trên cả PostgreSQL lẫn
    SQLite (bài kiểm thử). Nếu sau này cần khoảng thời gian dài hơn thì chuyển
    sang `date_bin()` của PostgreSQL.
    """
    seconds = BUCKET_SECONDS.get(bucket, 60)
    date_to = date_to or datetime.now(UTC)
    date_from = date_from or date_to - timedelta(seconds=seconds * points)

    statement = _apply_filters(
        select(DataSensor),
        device_id=device_id,
        sensor_type=None,
        date_from=date_from,
        date_to=date_to,
    ).order_by(DataSensor.timestamp.asc()).limit(MAX_SERIES_ROWS)

    # bucket_index → {sensor_type: [giá trị...]}
    buckets: dict[int, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    for row in db.scalars(statement):
        moment = row.timestamp
        if moment.tzinfo is None:
            moment = moment.replace(tzinfo=UTC)
        index = int(moment.timestamp()) // seconds
        buckets[index][row.sensor_type].append(float(row.value))

    def average(values: list[float]) -> float | None:
        return round(sum(values) / len(values), 2) if values else None

    series: list[SeriesPoint] = []
    for index in sorted(buckets)[-points:]:
        values = buckets[index]
        moment = datetime.fromtimestamp(index * seconds, tz=UTC)
        series.append(
            SeriesPoint(
                time=moment.astimezone(DISPLAY_TZ).strftime("%H:%M"),
                timestamp=moment,
                temp=average(values["temperature"]),
                humidity=average(values["humidity"]),
                light=average(values["light"]),
            )
        )

    return series
