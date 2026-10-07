"""Gom toàn bộ router của API v1."""

from fastapi import APIRouter

from app.api.v1 import auth, device_actions, devices, sensors, system

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(sensors.router)
api_router.include_router(devices.router)
api_router.include_router(device_actions.router)
api_router.include_router(system.router)

# Giai đoạn 6 sẽ thêm reports.
