"""Schema kiểm tra dữ liệu nhận từ MQTT — docs/04-MQTT-CONTRACT.md §2.

Bản tin từ thiết bị là dữ liệu không đáng tin: mọi trường đều được kiểm tra
kiểu và biên trước khi ghi vào cơ sở dữ liệu.
"""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class SensorPayload(BaseModel):
    """Bản tin trên `iot/sensor`.

    Giữ tên trường ngắn (`temp`, `humid`, `light`) cho khớp payload mẫu ở
    SRS Chương 2 và tiết kiệm băng thông phía ESP.
    """

    model_config = ConfigDict(extra="ignore")

    device_id: str = Field(min_length=1, max_length=50)
    temp: float | None = None
    humid: float | None = None
    light: float | None = None
    ts: datetime | None = None


class FeedbackPayload(BaseModel):
    """Bản tin trên `iot/feedback` — kết quả thực thi lệnh."""

    model_config = ConfigDict(extra="ignore")

    device_id: str = Field(min_length=1, max_length=50)
    target: Literal["led", "fan", "ac"]
    state: Literal["ON", "OFF"]
    result: Literal["Success", "Failed"] = "Success"
    # Không có cmd_id khi thiết bị tự đổi trạng thái (nút bấm tay).
    cmd_id: UUID | None = None
    error: str | None = None
    ts: datetime | None = None


class StatusPayload(BaseModel):
    """Bản tin trên `iot/status` — heartbeat và Last Will."""

    model_config = ConfigDict(extra="ignore")

    device_id: str = Field(min_length=1, max_length=50)
    status: Literal["online", "offline"] = "online"
    ip: str | None = None
    rssi: int | None = None
    uptime: int | None = None


class ControlPayload(BaseModel):
    """Bản tin publish lên `iot/control`."""

    cmd_id: UUID
    device_id: str
    target: Literal["led", "fan", "ac"]
    action: Literal["ON", "OFF", "STATUS"]
    issued_at: datetime
