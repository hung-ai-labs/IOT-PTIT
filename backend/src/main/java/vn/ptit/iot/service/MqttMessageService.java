package vn.ptit.iot.service;

import com.fasterxml.jackson.databind.*;
import jakarta.validation.Validator;
import java.util.*;
import org.slf4j.*;
import org.springframework.context.event.EventListener;
import org.springframework.stereotype.Service;
import vn.ptit.iot.dto.ApiDtos.*;

@Service
public class MqttMessageService {
  private static final Logger log = LoggerFactory.getLogger(MqttMessageService.class);
  private final ObjectMapper mapper;
  private final Validator validator;
  private final SensorService sensors;
  private final DeviceStateService states;
  private final ControlService controls;
  private final WebSocketService sockets;

  public MqttMessageService(
      ObjectMapper mapper,
      Validator validator,
      SensorService sensors,
      DeviceStateService states,
      ControlService controls,
      WebSocketService sockets) {
    this.mapper = mapper;
    this.validator = validator;
    this.sensors = sensors;
    this.states = states;
    this.controls = controls;
    this.sockets = sockets;
  }

  private <T> T parse(byte[] raw, Class<T> type) throws Exception {
    T value =
        mapper
            .readerFor(type)
            .without(DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES)
            .readValue(raw);
    if (value == null || !validator.validate(value).isEmpty())
      throw new IllegalArgumentException("Invalid MQTT payload");
    return value;
  }

  @EventListener
  public void incoming(MqttService.Incoming message) {
    try {
      switch (message.topic()) {
        case "iot/sensor", "Sensor_data" -> {
          var p = parse(message.payload(), SensorPayload.class);
          states.touch(p.deviceId(), null, null, null);
          var event = sensors.ingest(p);
          if (event.get("temperature") != null
              || event.get("humidity") != null
              || event.get("light") != null) sockets.broadcast("sensor", event);
        }
        case "iot/feedback", "device_response" ->
            controls.feedback(parse(message.payload(), FeedbackPayload.class));
        case "iot/status" -> {
          var p = parse(message.payload(), StatusPayload.class);
          if ("offline".equals(p.status())) states.offline(p.deviceId());
          else {
            boolean newlyOnline = !states.online(states.get(p.deviceId()));
            states.touch(p.deviceId(), p.ip(), p.rssi(), p.uptime());
            if (newlyOnline) controls.requestStatus(p.deviceId());
          }
        }
        default -> {}
      }
    } catch (Exception e) {
      log.warn("Ignored invalid or unprocessable MQTT message on {}", message.topic());
    }
  }
}
