"""Schema cho các API xác thực — docs/03-API-SPEC.md §2."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

# bcrypt chỉ xử lý 72 byte đầu; chặn ngay ở tầng API để mật khẩu dài
# không bị cắt âm thầm.
PASSWORD_MIN = 6
PASSWORD_MAX = 72


class RegisterRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=100, examples=["Nguyễn Xuân Hùng"])
    email: EmailStr = Field(max_length=150, examples=["nxhung@student.ptit.edu.vn"])
    password: str = Field(min_length=PASSWORD_MIN, max_length=PASSWORD_MAX, examples=["123456"])


class LoginRequest(BaseModel):
    email: EmailStr = Field(max_length=150, examples=["admin@ptit.edu.vn"])
    password: str = Field(min_length=1, max_length=PASSWORD_MAX, examples=["123456"])


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    email: EmailStr
    student_id: str | None = None
    school: str | None = None
    contact_email: EmailStr | None = None
    role: Literal["USER", "ADMIN"]
    created_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int = Field(description="Số giây còn hiệu lực của token")
    user: UserOut


class ProfileUpdateRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    full_name: str = Field(min_length=2, max_length=100)
    student_id: str | None = Field(default=None, max_length=30)
    school: str | None = Field(default=None, max_length=200)
    contact_email: EmailStr | None = Field(default=None, max_length=150)
