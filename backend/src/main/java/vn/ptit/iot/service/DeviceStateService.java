package vn.ptit.iot.service;

import java.time.Instant;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

@Service
public class DeviceStateService {
  public record State(
      String deviceId,
      Instant lastSeen,
      String ip,
      Integer rssi,
      Long uptime,
      Map<String, Boolean> targets) {}

  private final Map<String, State> states = new ConcurrentHashMap<>();
  private final long offlineSeconds;

  public DeviceStateService(@Value("${iot.offline-seconds}") long seconds) {
    offlineSeconds = seconds;
  }

  public void touch(String id, String ip, Integer rssi, Long uptime) {
    states.compute(
        id,
        (key, old) ->
            new State(
                id,
                Instant.now(),
                ip != null ? ip : old == null ? null : old.ip(),
                rssi != null ? rssi : old == null ? null : old.rssi(),
                uptime != null ? uptime : old == null ? null : old.uptime(),
                old == null ? Map.of() : old.targets()));
  }

  public void offline(String id) {
    states.compute(
        id,
        (key, old) ->
            new State(
                id,
                null,
                old == null ? null : old.ip(),
                old == null ? null : old.rssi(),
                old == null ? null : old.uptime(),
                old == null ? Map.of() : old.targets()));
  }

  public void set(String id, String target, boolean on) {
    states.compute(
        id,
        (key, old) -> {
          Map<String, Boolean> values = new HashMap<>(old == null ? Map.of() : old.targets());
          values.put(target, on);
          return new State(
              id,
              old == null ? null : old.lastSeen(),
              old == null ? null : old.ip(),
              old == null ? null : old.rssi(),
              old == null ? null : old.uptime(),
              Map.copyOf(values));
        });
  }

  public State get(String id) {
    return states.get(id);
  }

  public List<State> all() {
    return states.values().stream().sorted(Comparator.comparing(State::deviceId)).toList();
  }

  public boolean online(State state) {
    return state != null
        && state.lastSeen() != null
        && state.lastSeen().plusSeconds(offlineSeconds).isAfter(Instant.now());
  }

  public String defaultId() {
    return all().isEmpty() ? "ESP32-01" : all().get(0).deviceId();
  }

  public void clear() {
    states.clear();
  }
}
