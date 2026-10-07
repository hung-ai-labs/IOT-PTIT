"""Băm mật khẩu và phát hành JWT.

Được dùng ở Giai đoạn 2 (router auth) và bởi scripts/seed.py.
"""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import bcrypt
import jwt

from app.core.config import settings

# bcrypt cost 12 — cân bằng giữa an toàn và thời gian đăng nhập.
BCRYPT_ROUNDS = 12

# bcrypt chỉ xử lý tối đa 72 byte đầu của mật khẩu. Schema đăng ký giới hạn
# độ dài ở tầng API; ở đây cắt để không ném lỗi với dữ liệu cũ.
MAX_PASSWORD_BYTES = 72


def _encode(plain_password: str) -> bytes:
    return plain_password.encode("utf-8")[:MAX_PASSWORD_BYTES]


def hash_password(plain_password: str) -> str:
    salt = bcrypt.gensalt(rounds=BCRYPT_ROUNDS)
    return bcrypt.hashpw(_encode(plain_password), salt).decode("utf-8")


def verify_password(plain_password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(_encode(plain_password), password_hash.encode("utf-8"))
    except ValueError:
        # Hash sai định dạng (dữ liệu hỏng) — coi như không khớp.
        return False


def token_lifetime_seconds() -> int:
    return settings.access_token_expire_hours * 3600


def create_access_token(subject: str | int, extra: dict[str, Any] | None = None) -> str:
    """Tạo JWT với `sub` là id người dùng và `jti` để có thể thu hồi khi đăng xuất."""
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": str(subject),
        "jti": uuid.uuid4().hex,
        "iat": now,
        "exp": now + timedelta(hours=settings.access_token_expire_hours),
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict[str, Any]:
    """Giải mã JWT. Ném jwt.PyJWTError nếu token sai hoặc hết hạn."""
    return jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
