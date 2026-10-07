"""Đăng ký toàn bộ model khi package được import.

Cần thiết vì `User.actions` và `DeviceAction.issuer` tham chiếu nhau bằng tên
chuỗi — SQLAlchemy chỉ phân giải được khi cả hai lớp đã được nạp.
"""

from app.db.models.device_action import DeviceAction
from app.db.models.sensor import DataSensor
from app.db.models.user import User

__all__ = ["User", "DataSensor", "DeviceAction"]
