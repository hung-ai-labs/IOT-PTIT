"""Lớp Base khai báo của SQLAlchemy.

Tách riêng khỏi `base.py` để tránh import vòng: model import `Base` từ đây,
còn `base.py` chỉ làm nhiệm vụ gom model cho Alembic.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
