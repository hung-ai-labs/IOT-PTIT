"""Giả lập ESP32 để chạy hệ thống khi chưa có phần cứng.

    cd backend && .venv/bin/python ../scripts/mock_device.py
    cd backend && .venv/bin/python ../scripts/mock_device.py --fail-rate 0.3
    cd backend && .venv/bin/python ../scripts/mock_device.py --timeout-rate 0.2

Việc nó làm — đúng như một ESP32 thật (docs/04-MQTT-CONTRACT.md):
  • publish `iot/sensor` mỗi 5 giây
  • publish `iot/status` mỗi 10 giây (heartbeat), đặt Last Will khi mất kết nối
  • subscribe `iot/control`, thực thi lệnh rồi phản hồi qua `iot/feedback`

Các cờ `--fail-rate` / `--timeout-rate` dùng để thử luồng Failed và Timeout
của Giai đoạn 4 mà không cần rút dây thiết bị.
"""

from __future__ import annotations

import argparse
import json
import logging
import random
import signal
import sys
import threading
import time
from datetime import UTC, datetime
from pathlib import Path

import paho.mqtt.client as mqtt

BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import settings  # noqa: E402
from app.mqtt import topics  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger("mock-device")

DEVICE_ID = "ESP32-01"
SENSOR_INTERVAL = 5
HEARTBEAT_INTERVAL = 10

# Trạng thái GPIO của 3 thiết bị chấp hành, giống biến toàn cục trong sketch Arduino.
GPIO_STATE = {"led": True, "fan": False, "ac": True}


class MockDevice:
    def __init__(self, fail_rate: float, timeout_rate: float) -> None:
        self.fail_rate = fail_rate
        self.timeout_rate = timeout_rate
        # Event báo hiệu DỪNG: khởi tạo ở trạng thái chưa set, nên `wait(n)`
        # dùng được như một sleep có thể ngắt ngay khi cần dừng.
        self._stop = threading.Event()
        self._started_at = time.monotonic()

        # Giá trị nền, mỗi chu kỳ đi lang thang một chút cho giống cảm biến thật.
        self.temp = 27.0
        self.humidity = 62.0
        self.light = 243.0

        self.client = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2, client_id=f"mock-{DEVICE_ID.lower()}"
        )
        if settings.mqtt_username:
            self.client.username_pw_set(settings.mqtt_username, settings.mqtt_password)

        # Last Will: broker tự gửi hộ khi thiết bị mất kết nối đột ngột.
        self.client.will_set(
            topics.TOPIC_STATUS,
            json.dumps({"device_id": DEVICE_ID, "status": "offline"}),
            qos=1,
            retain=True,
        )
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message

    # ─── Kết nối ─────────────────────────────────────────────
    def start(self) -> None:
        self.client.connect(settings.mqtt_host, settings.mqtt_port, keepalive=30)
        self.client.loop_start()

        threading.Thread(target=self._sensor_loop, daemon=True).start()
        threading.Thread(target=self._heartbeat_loop, daemon=True).start()

    def stop(self) -> None:
        self._stop.set()
        self._publish(
            topics.TOPIC_STATUS, {"device_id": DEVICE_ID, "status": "offline"}, retain=True
        )
        time.sleep(0.2)
        self.client.disconnect()
        self.client.loop_stop()

    def _on_connect(self, client, userdata, flags, reason_code, properties=None):
        if reason_code != 0:
            logger.error("Không kết nối được broker: %s", reason_code)
            return
        client.subscribe(topics.TOPIC_CONTROL, qos=1)
        logger.info(
            "Đã kết nối %s:%s — subscribe %s",
            settings.mqtt_host, settings.mqtt_port, topics.TOPIC_CONTROL,
        )
        self._publish_status()

    def _publish(self, topic: str, payload: dict, retain: bool = False) -> None:
        self.client.publish(topic, json.dumps(payload, ensure_ascii=False), qos=1, retain=retain)

    # ─── Cảm biến ────────────────────────────────────────────
    def _drift(self, value: float, step: float, low: float, high: float) -> float:
        return min(high, max(low, value + random.uniform(-step, step)))

    def _sensor_loop(self) -> None:
        while not self._stop.is_set():
            self.temp = self._drift(self.temp, 0.4, 20.0, 35.0)
            self.humidity = self._drift(self.humidity, 1.5, 40.0, 80.0)
            self.light = self._drift(self.light, 15.0, 80.0, 400.0)

            payload = {
                "device_id": DEVICE_ID,
                "temp": round(self.temp, 1),
                "humid": round(self.humidity),
                "light": round(self.light),
                "ts": datetime.now(UTC).isoformat(),
            }
            self._publish(topics.TOPIC_SENSOR, payload)
            logger.info(
                "→ sensor  %.1f°C  %d%%  %d lux",
                payload["temp"], payload["humid"], payload["light"],
            )
            self._stop.wait(SENSOR_INTERVAL)

    # ─── Heartbeat ───────────────────────────────────────────
    def _publish_status(self) -> None:
        self._publish(
            topics.TOPIC_STATUS,
            {
                "device_id": DEVICE_ID,
                "status": "online",
                "ip": "192.168.1.105",
                "rssi": random.randint(-70, -45),
                "uptime": int(time.monotonic() - self._started_at),
            },
            retain=True,
        )

    def _heartbeat_loop(self) -> None:
        while not self._stop.wait(HEARTBEAT_INTERVAL):
            self._publish_status()

    # ─── Nhận lệnh điều khiển ────────────────────────────────
    def _on_message(self, client, userdata, message: mqtt.MQTTMessage) -> None:
        try:
            command = json.loads(message.payload)
        except json.JSONDecodeError:
            logger.warning("← control  bỏ qua payload không phải JSON")
            return

        if command.get("device_id") not in (None, DEVICE_ID):
            return

        target = command.get("target")
        action = command.get("action")
        if target not in GPIO_STATE:
            logger.warning("← control  thiết bị lạ: %s", target)
            return

        logger.info("← control  %s %s", target, action)

        # Giả lập thời gian đóng/ngắt relay.
        time.sleep(random.uniform(0.2, 1.0))

        if random.random() < self.timeout_rate:
            logger.warning("   (giả lập TIMEOUT — không phản hồi)")
            return

        if random.random() < self.fail_rate:
            self._publish(
                topics.TOPIC_FEEDBACK,
                {
                    "cmd_id": command.get("cmd_id"),
                    "device_id": DEVICE_ID,
                    "target": target,
                    "state": "ON" if GPIO_STATE[target] else "OFF",
                    "result": "Failed",
                    "error": "Relay không đóng được",
                    "ts": datetime.now(UTC).isoformat(),
                },
            )
            logger.warning("   → feedback Failed")
            return

        if action in ("ON", "OFF"):
            GPIO_STATE[target] = action == "ON"

        self._publish(
            topics.TOPIC_FEEDBACK,
            {
                "cmd_id": command.get("cmd_id"),
                "device_id": DEVICE_ID,
                "target": target,
                "state": "ON" if GPIO_STATE[target] else "OFF",
                "result": "Success",
                "ts": datetime.now(UTC).isoformat(),
            },
        )
        logger.info("   → feedback Success (%s = %s)", target, GPIO_STATE[target])


def main() -> None:
    parser = argparse.ArgumentParser(description="Giả lập thiết bị ESP32 qua MQTT.")
    parser.add_argument(
        "--fail-rate", type=float, default=0.0,
        help="Xác suất trả kết quả Failed (0.0–1.0)",
    )
    parser.add_argument(
        "--timeout-rate", type=float, default=0.0,
        help="Xác suất không phản hồi để thử luồng Timeout (0.0–1.0)",
    )
    args = parser.parse_args()

    device = MockDevice(args.fail_rate, args.timeout_rate)

    def shutdown(*_):
        logger.info("Đang dừng...")
        device.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    logger.info(
        "Giả lập %s — sensor mỗi %ds, heartbeat mỗi %ds. Ctrl+C để dừng.",
        DEVICE_ID, SENSOR_INTERVAL, HEARTBEAT_INTERVAL,
    )
    device.start()

    while True:
        time.sleep(1)


if __name__ == "__main__":
    main()
