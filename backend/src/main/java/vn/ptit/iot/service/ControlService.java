package vn.ptit.iot.service;

import jakarta.annotation.PreDestroy;
import java.time.Instant;
import java.util.*;
import java.util.concurrent.*;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.context.event.ApplicationReadyEvent;
import org.springframework.context.event.EventListener;
import org.springframework.stereotype.Service;
import vn.ptit.iot.config.DeviceRegistry;
import vn.ptit.iot.dto.ApiDtos.*;
import vn.ptit.iot.entity.DeviceAction;
import vn.ptit.iot.exception.ApiException;
import vn.ptit.iot.repository.ActionRepository;

@Service
public class ControlService {
  private final ActionService service;
  private final ActionRepository actions;
  private final DeviceStateService states;
  private final MqttService mqtt;
  private final WebSocketService sockets;
  private final double timeout;
  private final boolean enabled;
  private final ScheduledExecutorService timer =
      Executors.newSingleThreadScheduledExecutor(
          r -> {
            Thread t = new Thread(r, "iot-command-timeouts");
            t.setDaemon(true);
            return t;
          });
  private final Map<UUID, ScheduledFuture<?>> pending = new ConcurrentHashMap<>();

  public ControlService(
      ActionService service,
      ActionRepository actions,
      DeviceStateService states,
      MqttService mqtt,
      WebSocketService sockets,
      @Value("${iot.command-timeout-seconds}") double timeout,
      @Value("${iot.mqtt-enabled}") boolean enabled) {
    this.service = service;
    this.actions = actions;
    this.states = states;
    this.mqtt = mqtt;
    this.sockets = sockets;
    this.timeout = timeout;
    this.enabled = enabled;
  }

  public List<DeviceOut> devices(String id) {
    String resolved = id == null ? states.defaultId() : id;
    return DeviceRegistry.DEVICES.keySet().stream()
        .map(target -> device(resolved, target))
        .toList();
  }

  private DeviceOut device(String id, String target) {
    var definition = DeviceRegistry.DEVICES.get(target);
    var state = states.get(id);
    var last = actions.findFirstByDeviceIdAndTargetOrderByTimestampDescIdDesc(id, target);
    return new DeviceOut(
        id,
        target,
        definition.name(),
        definition.gpio(),
        definition.icon(),
        state != null && Boolean.TRUE.equals(state.targets().get(target)) ? "ON" : "OFF",
        states.online(state) ? "online" : "offline",
        last.map(DeviceAction::getTimestamp).orElse(null),
        state == null ? null : state.lastSeen());
  }

  public DeviceTargetDetailOut targetDetail(String id, String target) {
    if (!DeviceRegistry.DEVICES.containsKey(target))
      throw new ApiException(404, "TARGET_NOT_FOUND", "Không tìm thấy đèn yêu cầu.");
    var lamp = device(id, target);
    var state = states.get(id);
    return new DeviceTargetDetailOut(
        id, target, lamp.name(), lamp.gpio(), lamp.icon(), lamp.state(), lamp.connection(),
        lamp.lastCommand(), lamp.lastSeen(),
        state == null ? null : state.ip(),
        state == null ? null : state.rssi(),
        state == null ? null : state.uptime(),
        "iot/control", "iot/feedback");
  }

  public DeviceDetailOut detail(String id) {
    var state = states.get(id);
    return new DeviceDetailOut(
        id,
        states.online(state) ? "online" : "offline",
        state == null ? null : state.ip(),
        state == null ? null : state.rssi(),
        state == null ? null : state.uptime(),
        state == null ? null : state.lastSeen(),
        "iot/control",
        "iot/feedback",
        devices(id));
  }

  public synchronized AcceptedOut send(String id, ActionRequest p, Long issuer) {
    if (!DeviceRegistry.DEVICES.containsKey(p.target()))
      throw new ApiException(422, "VALIDATION_ERROR", "Thiết bị không hợp lệ.");
    if (!mqtt.connected())
      throw new ApiException(
          503, "MQTT_UNAVAILABLE", "Chưa kết nối được MQTT Broker. Không thể gửi lệnh điều khiển.");
    if (!states.online(states.get(id)))
      throw new ApiException(409, "DEVICE_OFFLINE", "Thiết bị " + id + " đang mất kết nối.");
    if (actions.existsByDeviceIdAndTargetAndResult(id, p.target(), "Pending"))
      throw new ApiException(
          409, "COMMAND_IN_PROGRESS", "Đang có lệnh chờ xử lý. Vui lòng đợi kết quả.");
    DeviceAction row = service.create(id, p.target(), p.action(), issuer);
    ScheduledFuture<?> deadline =
        timer.schedule(
            () -> finish(row, "Timeout", "Thiết bị không phản hồi trong thời gian quy định.", null),
            Math.max(1, (long) (timeout * 1000)),
            TimeUnit.MILLISECONDS);
    pending.put(row.getCmdId(), deadline);
    boolean published =
        mqtt.publish(
            "iot/control",
            Map.of(
                "cmd_id",
                row.getCmdId(),
                "device_id",
                id,
                "target",
                p.target(),
                "action",
                p.action(),
                "issued_at",
                Instant.now()));
    if (!published) {
      finish(row, "Failed", "Không publish được lệnh lên MQTT Broker", null);
      throw new ApiException(503, "MQTT_UNAVAILABLE", "Không gửi được lệnh lên MQTT Broker.");
    }
    return new AcceptedOut(
        row.getId(), row.getCmdId(), id, p.target(), p.action(), "Pending", timeout);
  }

  public void feedback(FeedbackPayload p) {
    states.touch(p.deviceId(), null, null, null);
    String result = p.result() == null ? "Success" : p.result();
    if (p.cmdId() == null) {
      if ("Success".equals(result)) states.set(p.deviceId(), p.target(), "ON".equals(p.state()));
      return;
    }
    var found = actions.findByCmdId(p.cmdId());
    if (found.isEmpty()) {
      if ("Success".equals(result)) states.set(p.deviceId(), p.target(), "ON".equals(p.state()));
      return;
    }
    DeviceAction row = found.get();
    if (!row.getDeviceId().equals(p.deviceId()) || !row.getTarget().equals(p.target())) return;
    finish(row, result, p.error(), p.state());
  }

  private void finish(DeviceAction row, String result, String error, String newState) {
    if (!service.complete(row.getId(), result, error)) return;
    var future = pending.remove(row.getCmdId());
    if (future != null) future.cancel(false);
    if ("Success".equals(result) && newState != null)
      states.set(row.getDeviceId(), row.getTarget(), "ON".equals(newState));
    var state = states.get(row.getDeviceId());
    Map<String, Object> event = new HashMap<>();
    event.put("action_id", row.getId());
    event.put("cmd_id", row.getCmdId());
    event.put("device_id", row.getDeviceId());
    event.put("target", row.getTarget());
    event.put(
        "state",
        state != null && Boolean.TRUE.equals(state.targets().get(row.getTarget())) ? "ON" : "OFF");
    event.put("result", result);
    event.put("error_msg", error);
    event.put("timestamp", Instant.now());
    sockets.broadcast("device_state", event);
  }

  @EventListener(ApplicationReadyEvent.class)
  public void restore() {
    if (!enabled) return;
    for (DeviceAction row : actions.findByResult("Pending"))
      finish(row, "Timeout", "Máy chủ khởi động lại trước khi nhận phản hồi.", null);
    Map<String, DeviceAction> latest = new HashMap<>();
    for (DeviceAction row : actions.findByResult("Success")) {
      String key = row.getDeviceId() + ":" + row.getTarget();
      DeviceAction old = latest.get(key);
      if (old == null || row.getId() > old.getId()) latest.put(key, row);
    }
    latest
        .values()
        .forEach(
            row -> states.set(row.getDeviceId(), row.getTarget(), "ON".equals(row.getAction())));
  }

  public void requestStatus(String id) {
    for (String target : DeviceRegistry.DEVICES.keySet())
      mqtt.publish(
          "iot/control",
          Map.of(
              "cmd_id",
              UUID.randomUUID(),
              "device_id",
              id,
              "target",
              target,
              "action",
              "STATUS",
              "issued_at",
              Instant.now()));
  }

  @PreDestroy
  public void close() {
    pending.values().forEach(f -> f.cancel(false));
    pending.clear();
    timer.shutdownNow();
  }
}
