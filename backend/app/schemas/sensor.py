"""Schema cho API dữ liệu cảm biến — docs/03-API-SPEC.md §3."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

SensorType = Literal["temperature", "humidity", "light"]


class SensorRecordOut(BaseModel):
    """Một bản ghi trong bảng `data_sensor` (SRS §2.6)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    device_id: str
    sensor_type: SensorType
    value: float
    unit: str
    timestamp: datetime


class SensorReading(BaseModel):
    """Giá trị mới nhất của một loại cảm biến."""

    value: float
    unit: str
    timestamp: datetime


class LatestSensorOut(BaseModel):
    """Kết quả `GET /sensors/latest` — có thể thiếu loại nào chưa từng có dữ liệu."""

    device_id: str | None = None
    temperature: SensorReading | None = None
    humidity: SensorReading | None = None
    light: SensorReading | None = None


class SeriesPoint(BaseModel):
    """Một điểm trên biểu đồ Dashboard: trung bình của mỗi loại trong một khoảng."""

    time: str = Field(description="Nhãn HH:MM để hiển thị trên trục ngang")
    timestamp: datetime
    temp: float | None = None
    humidity: float | None = None
    light: float | None = None
