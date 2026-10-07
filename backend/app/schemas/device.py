"""Schema cho API điều khiển thiết bị — docs/03-API-SPEC.md §4, §5."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

Target = Literal["led", "fan", "ac"]
Action = Literal["ON", "OFF"]
ActionResult = Literal["Pending", "Success", "Failed", "Timeout"]


class DeviceOut(BaseModel):
    """Một thiết bị chấp hành trên thẻ điều khiển (SRS §2.9)."""

    device_id: str
    target: Target
    name: str = Field(description="Tên hiển thị, ví dụ 'Đèn LED'")
    gpio: str
    icon: str
    state: Action = Field(description="Trạng thái hiện tại theo phản hồi gần nhất")
    connection: Literal["online", "offline"]
    last_command: datetime | None = None
    last_seen: datetime | None = None


class DeviceDetailOut(BaseModel):
    """Chi tiết một ESP và các thiết bị gắn trên nó (F10)."""

    device_id: str
    connection: Literal["online", "offline"]
    ip: str | None = None
    rssi: int | None = None
    uptime: int | None = None
    last_seen: datetime | None = None
    command_topic: str
    feedback_topic: str
    targets: list[DeviceOut]


class ActionRequest(BaseModel):
    target: Target
    action: Action


class ActionAcceptedOut(BaseModel):
    """Phản hồi 202: lệnh đã tiếp nhận, chưa biết kết quả."""

    action_id: int
    cmd_id: UUID
    device_id: str
    target: Target
    action: Action
    result: ActionResult = "Pending"
    timeout_seconds: float = Field(description='Thời gian tối đa chờ thiết bị phản hồi')


class IssuerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str


class DeviceActionOut(BaseModel):
    """Một dòng trong lịch sử thao tác (SRS §2.4)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    device_id: str
    target: Target
    target_label: str = Field(description="Tên tiếng Việt của đối tượng điều khiển")
    action: Action
    issued_by: IssuerOut | None = None
    result: ActionResult
    timestamp: datetime
    responded_at: datetime | None = None
    error_msg: str | None = None
