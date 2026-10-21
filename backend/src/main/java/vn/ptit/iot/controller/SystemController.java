package vn.ptit.iot.controller;

import java.util.Map;
import org.springframework.web.bind.annotation.*;
import vn.ptit.iot.dto.ApiDtos.SystemOut;
import vn.ptit.iot.service.StatusService;

@RestController
public class SystemController {
  private final StatusService status;

  public SystemController(StatusService status) {
    this.status = status;
  }

  @GetMapping("/api/v1/system/status")
  public SystemOut system() {
    return status.status();
  }

  @GetMapping("/health")
  public Map<String, Object> health() {
    SystemOut s = status.status();
    return Map.of(
        "status",
        "ok",
        "app",
        "Smart IoT — Monitoring & Control",
        "version",
        "1.0.0",
        "database",
        s.database().status(),
        "mqtt",
        Map.of(
            "connected",
            s.mqtt().status().equals("connected"),
            "messages_received",
            s.mqtt().messagesReceived()));
  }
}
