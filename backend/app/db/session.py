"""Engine và session factory của SQLAlchemy."""

from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,      # tự phát hiện kết nối chết sau khi DB restart
    pool_size=5,
    max_overflow=10,
    echo=settings.db_echo,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    """Dependency của FastAPI: mở session cho một request rồi đóng lại."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
