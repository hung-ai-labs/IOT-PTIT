"""API trạng thái hệ thống — SRS §4.3.7."""

from fastapi import APIRouter, Request

from app.core.deps import CurrentUser
from app.schemas.system import SystemStatusOut
from app.services import status_service

router = APIRouter(prefix="/system", tags=["system"])


@router.get("/status", response_model=SystemStatusOut, summary="Trạng thái toàn hệ thống")
def get_status(request: Request, _user: CurrentUser) -> SystemStatusOut:
    """Trạng thái ESP, MQTT, API và cơ sở dữ liệu (F09)."""
    return status_service.get_system_status(request.app.state.started_at)
