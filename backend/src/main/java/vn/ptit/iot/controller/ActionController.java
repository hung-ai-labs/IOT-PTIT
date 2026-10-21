package vn.ptit.iot.controller;

import java.time.Instant;
import org.springframework.web.bind.annotation.*;
import vn.ptit.iot.dto.ApiDtos.*;
import vn.ptit.iot.service.ActionService;

@RestController
@RequestMapping("/api/v1/device-actions")
public class ActionController {
  private final ActionService actions;

  public ActionController(ActionService actions) {
    this.actions = actions;
  }

  @GetMapping("/{id}")
  public ActionOut get(@PathVariable Long id) {
    return actions.get(id);
  }

  @GetMapping
  public PageOut<ActionOut> list(
      @RequestParam(required = false, name = "device_id") String device,
      @RequestParam(required = false) String target,
      @RequestParam(required = false) String action,
      @RequestParam(required = false) String result,
      @RequestParam(required = false, name = "q") String q,
      @RequestParam(required = false, name = "from") Instant from,
      @RequestParam(required = false, name = "to") Instant to,
      @RequestParam(defaultValue = "1") int page,
      @RequestParam(defaultValue = "20") int size,
      @RequestParam(defaultValue = "timestamp:desc") String sort) {
    return actions.records(device, target, action, result, q, from, to, page, size, sort);
  }
}
