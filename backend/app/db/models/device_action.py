"""Bảng device_actions — SRS §4.2.3.

Các cột cmd_id / responded_at / error_msg không có trong SRS nhưng bắt buộc
để hiện thực vòng đời lệnh Pending → Success | Failed | Timeout (F11).
Xem docs/02-DATABASE.md §2.3.
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base


class DeviceAction(Base):
    __tablename__ = "device_actions"
    __table_args__ = (
        CheckConstraint("target IN ('led', 'fan', 'ac')", name="ck_device_actions_target"),
        CheckConstraint("action IN ('ON', 'OFF')", name="ck_device_actions_action"),
        CheckConstraint(
            "result IN ('Pending', 'Success', 'Failed', 'Timeout')",
            name="ck_device_actions_result",
        ),
        Index("idx_actions_lookup", "device_id", "target", "result", "timestamp"),
        Index("idx_actions_time", "timestamp"),
    )

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"), primary_key=True
    )
    device_id: Mapped[str] = mapped_column(String(50), nullable=False)
    target: Mapped[str] = mapped_column(String(20), nullable=False)
    action: Mapped[str] = mapped_column(String(20), nullable=False)

    # NULL khi thiết bị tự đổi trạng thái (feedback không khớp cmd_id nào).
    issued_by: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    result: Mapped[str] = mapped_column(String(20), nullable=False, default="Pending")

    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # Khớp lệnh publish lên iot/control với phản hồi trên iot/feedback.
    cmd_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, nullable=False, unique=True, index=True, default=uuid.uuid4
    )
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_msg: Mapped[str | None] = mapped_column(String(255), nullable=True)

    issuer: Mapped["User | None"] = relationship(back_populates="actions")  # noqa: F821

    def __repr__(self) -> str:
        return f"<DeviceAction {self.target} {self.action} → {self.result}>"
