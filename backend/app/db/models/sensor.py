"""Bảng data_sensor — SRS §4.2.2."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    Index,
    Integer,
    Numeric,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base


class DataSensor(Base):
    __tablename__ = "data_sensor"
    __table_args__ = (
        CheckConstraint(
            "sensor_type IN ('temperature', 'humidity', 'light')",
            name="ck_data_sensor_type",
        ),
        # Phục vụ F12: lọc theo thiết bị + loại cảm biến + khoảng thời gian
        Index("idx_sensor_lookup", "device_id", "sensor_type", "timestamp"),
        Index("idx_sensor_time", "timestamp"),
    )

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"), primary_key=True
    )
    device_id: Mapped[str] = mapped_column(String(50), nullable=False)
    sensor_type: Mapped[str] = mapped_column(String(20), nullable=False)
    value: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    unit: Mapped[str] = mapped_column(String(10), nullable=False)

    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    def __repr__(self) -> str:
        return f"<DataSensor {self.device_id} {self.sensor_type}={self.value}{self.unit}>"
