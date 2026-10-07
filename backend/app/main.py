"""Điểm khởi động ứng dụng FastAPI."""

import asyncio
import logging
import threading
import time
from contextlib import asynccontextmanager, suppress
from pathlib import Path

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from app.api.v1.router import api_router
from app.core import token_store
from app.core.config import settings
from app.core.security import decode_access_token
from app.db.session import SessionLocal, engine
from app.mqtt.client import mqtt_service
from app.mqtt.registry import pending_commands
from app.services import control_service, status_service
from app.state.device_cache import device_cache
from app.ws.hub import clear_event_loop, set_event_loop, websocket_hub

logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s  %(levelname)-8s %(name)s  %(message)s",
)
logger = logging.getLogger(__name__)

# Thư mục frontend nằm cạnh backend/ trong repo.
FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"

# Thời điểm khởi động, dùng cho uptime ở GET /system/status.
STARTED_AT = time.monotonic()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Khởi tạo và dọn dẹp các tài nguyên chạy nền (docs/01-ARCHITECTURE.md §2)."""
    logger.info("Khởi động %s v%s", settings.app_name, settings.app_version)

    database = status_service.check_database()
    if database.status == "connected":
        logger.info("Kết nối PostgreSQL thành công.")
    else:
        logger.warning("Chưa kết nối được PostgreSQL.")

    set_event_loop(asyncio.get_running_loop())
    status_task: asyncio.Task | None = None

    if settings.enable_mqtt:
        # DeviceStateCache nằm trong RAM nên mất sau mỗi lần restart. Nạp tạm từ
        # lệnh thành công gần nhất, rồi hỏi lại phần cứng để có trạng thái thật.
        _restore_device_states()

        # Không chặn khởi động nếu broker chưa sẵn sàng: paho tự kết nối lại.
        mqtt_service.start()
        _request_status_refresh()
        status_task = asyncio.create_task(_broadcast_system_status())
    else:
        logger.info("ENABLE_MQTT=false — bỏ qua kết nối MQTT và khôi phục trạng thái.")

    try:
        yield
    finally:
        if status_task is not None:
            status_task.cancel()
            with suppress(asyncio.CancelledError):
                await status_task
        clear_event_loop()
        websocket_hub.clear()
        pending_commands.clear()
        if settings.enable_mqtt:
            mqtt_service.stop()
        engine.dispose()
        logger.info("Đã dừng ứng dụng.")


async def _broadcast_system_status() -> None:
    """Phát trạng thái định kỳ mà không chặn event loop bằng truy vấn DB đồng bộ."""
    while True:
        try:
            snapshot = await asyncio.to_thread(status_service.get_system_status, STARTED_AT)
            await websocket_hub.broadcast(
                {"type": "system_status", "data": snapshot.model_dump(mode="json")}
            )
        except asyncio.CancelledError:
            raise
        except Exception:  # noqa: BLE001 — task nền phải sống qua lỗi phụ thuộc tạm thời
            logger.warning("Không phát được trạng thái hệ thống", exc_info=True)
        await asyncio.sleep(settings.heartbeat_seconds)


def _restore_device_states() -> None:
    db = SessionLocal()
    try:
        control_service.restore_device_states(db)
    except Exception:  # noqa: BLE001 — không chặn khởi động
        logger.warning("Không khôi phục được trạng thái thiết bị", exc_info=True)
    finally:
        db.close()


def _request_status_refresh() -> None:
    """Hỏi các ESP đã biết về trạng thái ON/OFF thật của chúng.

    Chạy nền vì `mqtt_service.start()` kết nối bất đồng bộ — cần đợi vài giây
    để phiên MQTT sẵn sàng rồi mới publish.
    """
    device_ids = [device.device_id for device in device_cache.all()]
    if not device_ids:
        return

    def ask() -> None:
        control_service.request_status_refresh(device_ids)

    timer = threading.Timer(3.0, ask)
    timer.daemon = True
    timer.start()


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=(
            "REST API cho Hệ thống Giám sát và Điều khiển IoT. "
            "Đặc tả đầy đủ: docs/03-API-SPEC.md"
        ),
        lifespan=lifespan,
    )
    app.state.started_at = STARTED_AT

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health", tags=["system"], summary="Kiểm tra sức khoẻ dịch vụ")
    def health() -> dict[str, object]:
        """Trả về trạng thái API và kết nối cơ sở dữ liệu."""
        database = status_service.check_database()

        return {
            "status": "ok" if database.status == "connected" else "degraded",
            "version": settings.app_version,
            "uptime_seconds": round(time.monotonic() - STARTED_AT, 1),
            "database": database.model_dump(),
            "mqtt": {
                "status": "connected" if mqtt_service.connected else "disconnected",
                "broker": f"{settings.mqtt_host}:{settings.mqtt_port}",
                "messages_received": mqtt_service.messages_received,
            },
        }

    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket, token: str = "") -> None:
        try:
            payload = decode_access_token(token)
            if not payload.get("sub") or not payload.get("jti"):
                raise ValueError("missing claims")
            if token_store.is_revoked(payload.get("jti")):
                raise ValueError("revoked")
        except Exception:  # noqa: BLE001 — mọi lỗi xác thực WS đều dùng policy violation
            await websocket.accept()
            await websocket.close(code=1008, reason="Token không hợp lệ hoặc đã hết hạn.")
            return

        await websocket_hub.connect(websocket)
        try:
            while True:
                await websocket.receive_text()
        except WebSocketDisconnect:
            websocket_hub.disconnect(websocket)
        except Exception:  # noqa: BLE001
            websocket_hub.disconnect(websocket)
            logger.warning("Kết nối WebSocket kết thúc bất thường", exc_info=True)

    _register_error_handlers(app)

    app.include_router(api_router, prefix=settings.api_prefix)

    # Phải mount SAU khi gắn router, vì Mount("/") khớp mọi đường dẫn còn lại.
    _mount_frontend(app)
    return app


def _register_error_handlers(app: FastAPI) -> None:
    """Đưa lỗi 422 về cùng định dạng {"detail": {"code", "message"}} như các lỗi khác."""

    @app.exception_handler(RequestValidationError)
    async def on_validation_error(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        first = exc.errors()[0] if exc.errors() else {}
        field = ".".join(str(part) for part in first.get("loc", ())[1:]) or "dữ liệu"
        return JSONResponse(
            status_code=422,
            content={
                "detail": {
                    "code": "VALIDATION_ERROR",
                    "message": f"Trường '{field}' không hợp lệ: {first.get('msg', '')}",
                }
            },
        )


class _NoCacheStaticFiles(StaticFiles):
    """StaticFiles buộc trình duyệt kiểm tra lại file mỗi lần tải.

    Khi DEBUG=true, sửa CSS/JS xong mà trình duyệt vẫn dùng bản cũ trong cache
    là chuyện thường gặp. "no-cache" không tắt cache — nó chỉ bắt trình duyệt
    hỏi lại server, nên ETag vẫn trả 304 và không tốn thêm băng thông.
    """

    def file_response(self, *args: object, **kwargs: object) -> Response:
        response = super().file_response(*args, **kwargs)  # type: ignore[arg-type]
        response.headers["Cache-Control"] = "no-cache"
        return response


def _mount_frontend(app: FastAPI) -> None:
    """Phục vụ Web Dashboard tĩnh ngay từ FastAPI (không cần server riêng)."""
    if not FRONTEND_DIR.is_dir():
        logger.warning("Không tìm thấy thư mục frontend tại %s", FRONTEND_DIR)
        return

    @app.get("/", include_in_schema=False)
    def index() -> FileResponse:
        return FileResponse(FRONTEND_DIR / "index.html")

    static_cls = _NoCacheStaticFiles if settings.debug else StaticFiles
    app.mount("/", static_cls(directory=FRONTEND_DIR, html=True), name="frontend")
    logger.info("Phục vụ frontend từ %s", FRONTEND_DIR)


app = create_app()
