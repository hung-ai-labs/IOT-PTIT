"""Nơi gom toàn bộ model.

Alembic và các bài kiểm thử import file này để `Base.metadata` chứa đủ các bảng.
Model không được import từ đây (sẽ gây import vòng) — chúng import `base_class`.
"""

from app.db.base_class import Base
from app.db.models import DataSensor, DeviceAction, User

__all__ = ["Base", "User", "DataSensor", "DeviceAction"]
