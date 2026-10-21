package vn.ptit.iot.service;

import javax.sql.DataSource;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;
import vn.ptit.iot.dto.ApiDtos.*;

@Service
public class StatusService {
  private final DataSource db;
  private final DeviceStateService states;
  private final MqttService mqtt;
  private final WebSocketService sockets;
  private final boolean enabled;
  private final long started = System.nanoTime();

  public StatusService(
      DataSource db,
      DeviceStateService states,
      MqttService mqtt,
      WebSocketService sockets,
      @Value("${iot.mqtt-enabled}") boolean enabled) {
    this.db = db;
    this.states = states;
    this.mqtt = mqtt;
    this.sockets = sockets;
    this.enabled = enabled;
  }

  public DatabaseOut database() {
    long now = System.nanoTime();
    try (var connection = db.getConnection();
        var statement = connection.createStatement()) {
      statement.execute("SELECT 1");
      return new DatabaseOut("connected", (System.nanoTime() - now) / 1000000.0);
    } catch (Exception e) {
      return new DatabaseOut("disconnected", null);
    }
  }

  public SystemOut status() {
    var state = states.get(states.defaultId());
    return new SystemOut(
        new EspOut(
            states.online(state) ? "online" : "offline",
            states.defaultId(),
            state == null ? null : state.lastSeen(),
            state == null ? null : state.ip(),
            state == null ? null : state.rssi(),
            state == null ? null : state.uptime()),
        new MqttOut(
            mqtt.connected() ? "connected" : "disconnected",
            mqtt.broker(),
            MqttService.TOPICS,
            mqtt.messagesReceived()),
        new ApiOut("running", "1.0.0", (System.nanoTime() - started) / 1000000000.0),
        database());
  }

  @Scheduled(fixedDelayString = "${iot.heartbeat-seconds}000")
  public void broadcast() {
    if (enabled) sockets.broadcast("system_status", status());
  }
}
