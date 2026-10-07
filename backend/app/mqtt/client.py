"""Kết nối tới MQTT Broker.

Dùng `paho-mqtt` với `loop_start()` — thư viện tự quản một thread nền lo việc
đọc socket, tự kết nối lại và gọi callback. Xem docs/04-MQTT-CONTRACT.md §4.
"""

from __future__ import annotations

import json
import logging
import uuid
from typing import Any

import paho.mqtt.client as mqtt

from app.core.config import settings
from app.mqtt import topics
from app.mqtt.handlers import (
    handle_feedback_message,
    handle_sensor_message,
    handle_status_message,
)

logger = logging.getLogger(__name__)


class MqttService:
    """Bọc paho-mqtt: kết nối, subscribe, publish và theo dõi tình trạng."""

    def __init__(self) -> None:
        self._client = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2,
            client_id=f"fastapi-{uuid.uuid4().hex[:8]}",
            clean_session=False,
        )
        self._connected = False
        self._messages_received = 0

        if settings.mqtt_username:
            self._client.username_pw_set(settings.mqtt_username, settings.mqtt_password)

        # Tự kết nối lại với backoff 1 → 30 giây.
        self._client.reconnect_delay_set(min_delay=1, max_delay=30)

        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect
        self._client.on_message = self._on_message

    # ─── Vòng đời ────────────────────────────────────────────
    def start(self) -> None:
        """Kết nối không chặn — nếu broker chưa sẵn sàng, paho sẽ tự thử lại."""
        try:
            self._client.connect_async(settings.mqtt_host, settings.mqtt_port, keepalive=60)
            self._client.loop_start()
            logger.info(
                "Đang kết nối MQTT Broker %s:%s", settings.mqtt_host, settings.mqtt_port
            )
        except Exception:
            logger.exception("Không khởi động được MQTT client")

    def stop(self) -> None:
        try:
            self._client.disconnect()
            self._client.loop_stop()
        except Exception:  # noqa: BLE001
            logger.warning("Lỗi khi dừng MQTT client", exc_info=True)
        self._connected = False

    # ─── Trạng thái ──────────────────────────────────────────
    @property
    def connected(self) -> bool:
        return self._connected

    @property
    def messages_received(self) -> int:
        return self._messages_received

    # ─── Gửi lệnh ────────────────────────────────────────────
    def publish(self, topic: str, payload: dict[str, Any], qos: int = 1) -> bool:
        """Publish một payload JSON. Trả về False nếu chưa kết nối được broker."""
        if not self._connected:
            logger.warning("Bỏ qua publish lên %s: chưa kết nối MQTT Broker", topic)
            return False

        body = json.dumps(payload, default=str, ensure_ascii=False)
        info = self._client.publish(topic, body, qos=qos)
        if info.rc != mqtt.MQTT_ERR_SUCCESS:
            logger.error("Publish lên %s thất bại (rc=%s)", topic, info.rc)
            return False

        logger.debug("→ %s %s", topic, body)
        return True

    # ─── Callback của paho ───────────────────────────────────
    def _on_connect(self, client: mqtt.Client, userdata, flags, reason_code, properties=None):
        if reason_code != 0:
            logger.error("Kết nối MQTT thất bại: %s", reason_code)
            return

        self._connected = True
        subscriptions = [(topic, 1) for topic in topics.SUBSCRIBE_TOPICS]

        # Bộ topic của bài kiểm thử terminal ở SRS Chương 2 — xem OQ-01.
        if settings.mqtt_legacy_topics:
            subscriptions += [(topic, 1) for topic in topics.LEGACY_SUBSCRIBE_TOPICS]

        client.subscribe(subscriptions)
        logger.info(
            "Đã kết nối MQTT Broker, subscribe: %s",
            ", ".join(topic for topic, _ in subscriptions),
        )

    def _on_disconnect(self, client, userdata, flags, reason_code, properties=None):
        self._connected = False
        logger.warning("Mất kết nối MQTT Broker (%s), đang thử lại...", reason_code)

    def _on_message(self, client, userdata, message: mqtt.MQTTMessage) -> None:
        self._messages_received += 1
        try:
            self._dispatch(message.topic, message.payload)
        except Exception:
            # Một bản tin lỗi không được làm chết thread nhận tin.
            logger.exception("Lỗi khi xử lý bản tin từ %s", message.topic)

    def _dispatch(self, topic: str, payload: bytes) -> None:
        if topic in (topics.TOPIC_SENSOR, topics.LEGACY_TOPIC_SENSOR):
            handle_sensor_message(payload)
        elif topic in (topics.TOPIC_FEEDBACK, topics.LEGACY_TOPIC_FEEDBACK):
            handle_feedback_message(payload)
        elif topic == topics.TOPIC_STATUS:
            handle_status_message(payload)
        else:
            logger.debug("Bỏ qua bản tin từ topic không quan tâm: %s", topic)


# Một instance dùng chung, khởi động trong lifespan của FastAPI.
mqtt_service = MqttService()
