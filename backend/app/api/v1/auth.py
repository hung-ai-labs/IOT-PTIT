"""API xác thực người dùng — SRS §2.1, §4.3.2."""

from datetime import UTC, datetime
from typing import Annotated

import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import func, select

from app.core import token_store
from app.core.deps import CurrentUser, DbSession
from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    token_lifetime_seconds,
    verify_password,
)
from app.db.models.user import User
from app.schemas.auth import LoginRequest, RegisterRequest, ProfileUpdateRequest, TokenResponse, UserOut
from app.schemas.common import ErrorResponse

router = APIRouter(prefix="/auth", tags=["auth"])

bearer_scheme = HTTPBearer(auto_error=False)


def _normalize_email(email: str) -> str:
    return email.strip().lower()


@router.post(
    "/register",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
    summary="Đăng ký tài khoản",
    responses={409: {"model": ErrorResponse, "description": "Email đã được sử dụng"}},
)
def register(payload: RegisterRequest, db: DbSession) -> User:
    """Tạo tài khoản mới với vai trò USER."""
    email = _normalize_email(payload.email)

    exists = db.scalar(select(func.count()).select_from(User).where(User.email == email))
    if exists:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "EMAIL_EXISTS", "message": "Email này đã được đăng ký."},
        )

    user = User(
        full_name=payload.full_name.strip(),
        email=email,
        password_hash=hash_password(payload.password),
        role="USER",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Đăng nhập",
    responses={401: {"model": ErrorResponse, "description": "Sai thông tin đăng nhập"}},
)
def login(payload: LoginRequest, db: DbSession) -> TokenResponse:
    """Xác thực và cấp JWT."""
    email = _normalize_email(payload.email)
    user = db.scalar(select(User).where(User.email == email))

    # Vẫn băm một lần khi không tìm thấy tài khoản để thời gian phản hồi
    # không tiết lộ email nào tồn tại.
    password_hash = user.password_hash if user else hash_password("khong-ton-tai")
    if not verify_password(payload.password, password_hash) or user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "INVALID_CREDENTIALS",
                "message": "Email hoặc mật khẩu không chính xác.",
            },
        )

    token = create_access_token(user.id, {"role": user.role})
    return TokenResponse(
        access_token=token,
        expires_in=token_lifetime_seconds(),
        user=UserOut.model_validate(user),
    )


@router.get("/me", response_model=UserOut, summary="Thông tin người dùng hiện tại")
def me(user: CurrentUser) -> User:
    return user


@router.patch("/me", response_model=UserOut, summary="Cập nhật thông tin cá nhân")
def update_profile(payload: ProfileUpdateRequest, user: CurrentUser, db: DbSession) -> User:
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(user, field, str(value) if value else None)
    db.commit()
    db.refresh(user)
    return user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, summary="Đăng xuất")
def logout(
    user: CurrentUser,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> None:
    """Thu hồi token hiện tại để nó không dùng lại được."""
    if credentials is None:
        return
    try:
        payload = decode_access_token(credentials.credentials)
    except jwt.PyJWTError:
        return  # token đã hỏng thì cũng coi như đã vô hiệu

    jti = payload.get("jti")
    if jti:
        token_store.revoke(jti, datetime.fromtimestamp(payload["exp"], tz=UTC))
