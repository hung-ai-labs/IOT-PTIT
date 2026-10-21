package vn.ptit.iot.controller;

import java.time.Instant;
import java.util.List;
import org.springframework.web.bind.annotation.*;
import vn.ptit.iot.dto.ApiDtos.*;
import vn.ptit.iot.service.SensorService;

@RestController
@RequestMapping("/api/v1/sensors")
public class SensorController {
  private final SensorService service;

  public SensorController(SensorService service) {
    this.service = service;
  }

  @GetMapping("/latest")
  public LatestOut latest(@RequestParam(required = false, name = "device_id") String device) {
    return service.latest(device);
  }

  @GetMapping("/series")
  public List<SeriesOut> series(
      @RequestParam(required = false, name = "device_id") String device,
      @RequestParam(required = false, name = "from") Instant from,
      @RequestParam(required = false, name = "to") Instant to,
      @RequestParam(defaultValue = "1m") String bucket,
      @RequestParam(defaultValue = "30") int points) {
    return service.series(device, from, to, bucket, points);
  }

  @GetMapping
  public PageOut<SensorOut> records(
      @RequestParam(required = false, name = "device_id") String device,
      @RequestParam(required = false, name = "sensor_type") String type,
      @RequestParam(required = false, name = "q") String q,
      @RequestParam(required = false, name = "field") String field,
      @RequestParam(required = false, name = "from") Instant from,
      @RequestParam(required = false, name = "to") Instant to,
      @RequestParam(defaultValue = "1") int page,
      @RequestParam(defaultValue = "20") int size,
      @RequestParam(defaultValue = "timestamp:desc") String sort) {
    return service.records(device, type, q, field, from, to, page, size, sort);
  }
}
