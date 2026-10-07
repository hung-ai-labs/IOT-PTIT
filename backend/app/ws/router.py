"""Endpoint WebSocket realtime của dashboard."""

import jwt
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core import token_store
from app.core.security import decode_access_token
from app.ws.hub import websocket_hub

router = APIRouter()


async def _reject(websocket: WebSocket) -> None:
    # Chấp nhận trước để trình duyệt nhận đúng close code 1008 thay vì HTTP 403.
    await websocket.accept()
    await websocket.close(code=1008, reason="Token không hợp lệ hoặc đã hết hạn.")


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str | None = None) -> None:
    try:
        payload = decode_access_token(token or "")
        if not payload.get("sub") or token_store.is_revoked(payload.get("jti")):
            await _reject(websocket)
            return
    except jwt.PyJWTError:
        await _reject(websocket)
        return

    await websocket_hub.connect(websocket)
    try:
        while True:
            # Client không cần gửi dữ liệu; receive giữ endpoint sống và phát hiện đóng tab.
            await websocket.receive_text()
    except WebSocketDisconnect:
        websocket_hub.disconnect(websocket)
