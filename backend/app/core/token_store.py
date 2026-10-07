"""Danh sách token đã thu hồi khi người dùng đăng xuất.

Lưu trong bộ nhớ nên sẽ mất khi khởi động lại server — chấp nhận được ở quy mô
đồ án (token hết hạn sau 8 giờ). Nếu chạy nhiều worker hoặc cần bền vững thì
chuyển sang Redis.
"""

from datetime import UTC, datetime

# jti → thời điểm token hết hạn
_revoked: dict[str, datetime] = {}


def revoke(jti: str, expires_at: datetime) -> None:
    _purge_expired()
    _revoked[jti] = expires_at


def is_revoked(jti: str | None) -> bool:
    if not jti:
        return False
    _purge_expired()
    return jti in _revoked


def clear() -> None:
    """Dùng trong kiểm thử."""
    _revoked.clear()


def _purge_expired() -> None:
    """Bỏ các jti đã quá hạn để dict không phình vô hạn."""
    now = datetime.now(UTC)
    for jti in [key for key, exp in _revoked.items() if exp <= now]:
        del _revoked[jti]
