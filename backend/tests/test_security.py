"""Kiểm thử băm mật khẩu và JWT (Giai đoạn 1)."""

import jwt
import pytest

from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_hash_is_not_plaintext_and_is_salted() -> None:
    first = hash_password("123456")
    second = hash_password("123456")

    assert first != "123456"
    assert first != second, "Mỗi lần băm phải dùng salt khác nhau"


def test_verify_password() -> None:
    password_hash = hash_password("123456")

    assert verify_password("123456", password_hash) is True
    assert verify_password("sai-mat-khau", password_hash) is False


def test_verify_rejects_malformed_hash() -> None:
    assert verify_password("123456", "không-phải-hash") is False


def test_access_token_round_trip() -> None:
    token = create_access_token(42, {"role": "ADMIN"})
    payload = decode_access_token(token)

    assert payload["sub"] == "42"
    assert payload["role"] == "ADMIN"
    assert payload["exp"] > payload["iat"]


def test_token_with_wrong_secret_is_rejected() -> None:
    token = create_access_token(1)

    with pytest.raises(jwt.InvalidSignatureError):
        jwt.decode(token, "khoa-sai", algorithms=["HS256"])
