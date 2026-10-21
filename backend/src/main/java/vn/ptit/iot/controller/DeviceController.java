package vn.ptit.iot.controller;

import jakarta.validation.Valid;
import jakarta.validation.constraints.Size;
import java.util.List;
import org.springframework.http.HttpStatus;
import org.springframework.security.core.Authentication;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;
import vn.ptit.iot.dto.ApiDtos.*;
import vn.ptit.iot.service.ControlService;

@RestController
@RequestMapping("/api/v1/devices")
@Validated
public class DeviceController {
  private final ControlService controls;

  public DeviceController(ControlService controls) {
    this.controls = controls;
  }

  @GetMapping
  @io.swagger.v3.oas.annotations.Operation(summary = "Danh sách ba đèn trên ESP32")
  public List<DeviceOut> list(@RequestParam(required = false, name = "device_id") String id) {
    return controls.devices(id);
  }

  @GetMapping("/{id}")
  @io.swagger.v3.oas.annotations.Hidden
  public DeviceDetailOut detail(@PathVariable @Size(min = 1, max = 50) String id) {
    return controls.detail(id);
  }

  @GetMapping("/{id}/targets/{target}")
  @io.swagger.v3.oas.annotations.Operation(summary = "Chi tiết một đèn trên ESP32")
  public DeviceTargetDetailOut targetDetail(
      @io.swagger.v3.oas.annotations.Parameter(description = "Mã ESP32", example = "ESP32-01")
          @PathVariable @Size(min = 1, max = 50) String id,
      @io.swagger.v3.oas.annotations.Parameter(
              description = "Đèn: red, green hoặc yellow", example = "red")
          @PathVariable @Size(min = 1, max = 30) String target) {
    return controls.targetDetail(id, target);
  }

  @PostMapping("/{id}/actions")
  @ResponseStatus(HttpStatus.ACCEPTED)
  public AcceptedOut send(
      @PathVariable @Size(min = 1, max = 50) String id,
      @Valid @RequestBody ActionRequest p,
      Authentication a) {
    return controls.send(id, p, (Long) a.getPrincipal());
  }
}
