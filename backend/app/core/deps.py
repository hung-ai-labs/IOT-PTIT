"""Dependency dùng chung cho các router."""

from datetime import UTC, datetime
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core import token_store
from app.core.security import decode_access_token
from app.db.models.user import User
from app.db.session import get_db

bearer_scheme = HTTPBearer(auto_error=False)

DbSession = Annotated[Session, Depends(get_db)]


def _unauthorized(message: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={"code": "UNAUTHORIZED", "message": message},
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user(
    db: DbSession,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> User:
    """Giải mã Bearer token và trả về người dùng tương ứng."""
    if credentials is None:
        raise _unauthorized("Chưa đăng nhập.")

    try:
        payload = decode_access_token(credentials.credentials)
    except jwt.ExpiredSignatureError as exc:
        raise _unauthorized("Phiên đăng nhập đã hết hạn.") from exc
    except jwt.PyJWTError as exc:
        raise _unauthorized("Token không hợp lệ.") from exc

    if token_store.is_revoked(payload.get("jti")):
        raise _unauthorized("Token đã bị thu hồi do đăng xuất.")

    user = db.get(User, int(payload["sub"]))
    if user is None:
        raise _unauthorized("Tài khoản không còn tồn tại.")

    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_admin(user: CurrentUser) -> User:
    """Dựng sẵn cho các API chỉ dành cho ADMIN.

    Bản này chưa dùng tới: SRS không mô tả quyền khác biệt giữa USER và ADMIN
    (xem docs/07-OPEN-QUESTIONS.md OQ-10).
    """
    if user.role != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "FORBIDDEN", "message": "Yêu cầu quyền quản trị."},
        )
    return user


def token_expiry(payload: dict) -> datetime:
    return datetime.fromtimestamp(payload["exp"], tz=UTC)
