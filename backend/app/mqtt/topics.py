"""Hằng số MQTT topic — xem docs/04-MQTT-CONTRACT.md."""

# Bộ topic chuẩn (SRS §4.3.8)
TOPIC_SENSOR = "iot/sensor"
TOPIC_CONTROL = "iot/control"
TOPIC_FEEDBACK = "iot/feedback"
TOPIC_STATUS = "iot/status"

# Bộ topic của bài kiểm thử terminal (SRS Chương 2).
# Chỉ subscribe khi settings.mqtt_legacy_topics = True — xem OQ-01.
LEGACY_TOPIC_SENSOR = "Sensor_data"
LEGACY_TOPIC_CONTROL = "Device_control"
LEGACY_TOPIC_FEEDBACK = "device_response"

SUBSCRIBE_TOPICS = (TOPIC_SENSOR, TOPIC_FEEDBACK, TOPIC_STATUS)
LEGACY_SUBSCRIBE_TOPICS = (LEGACY_TOPIC_SENSOR, LEGACY_TOPIC_FEEDBACK)
