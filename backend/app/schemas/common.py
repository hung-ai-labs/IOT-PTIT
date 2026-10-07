"""Schema dùng chung cho toàn bộ API."""

from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ErrorDetail(BaseModel):
    """Nội dung lỗi thống nhất — xem docs/03-API-SPEC.md §1."""

    code: str = Field(examples=["INVALID_CREDENTIALS"])
    message: str = Field(examples=["Email hoặc mật khẩu không chính xác."])


class ErrorResponse(BaseModel):
    detail: ErrorDetail


class Page(BaseModel, Generic[T]):
    """Kết quả phân trang."""

    items: list[T]
    page: int
    size: int
    total: int
    total_pages: int
