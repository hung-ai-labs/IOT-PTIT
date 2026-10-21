package vn.ptit.iot.service;

import jakarta.persistence.criteria.Predicate;
import java.math.*;
import java.time.*;
import java.time.format.DateTimeFormatter;
import java.util.*;
import org.springframework.data.domain.*;
import org.springframework.data.jpa.domain.Specification;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import vn.ptit.iot.dto.ApiDtos.*;
import vn.ptit.iot.entity.SensorReading;
import vn.ptit.iot.exception.ApiException;
import vn.ptit.iot.repository.SensorRepository;

@Service
public class SensorService {
  public static final Set<String> TYPES = Set.of("temperature", "humidity", "light");
  private final SensorRepository readings;

  public SensorService(SensorRepository readings) {
    this.readings = readings;
  }

  public SensorOut out(SensorReading r) {
    return new SensorOut(
        r.getId(),
        r.getDeviceId(),
        r.getSensorType(),
        r.getValue().doubleValue(),
        r.getUnit(),
        r.getTimestamp());
  }

  /** Phạm vi của ô "Tìm" trên màn Dữ liệu cảm biến; rỗng = tìm trong mọi thông tin. */
  public static final Set<String> FIELDS = Set.of("time", "temperature", "humidity", "light");

  /**
   * Ô tìm kiếm tự do. Ý nghĩa của từ khoá do `field` quyết định:
   * `time` → chuỗi thời gian, một loại cảm biến → giá trị đo, bỏ trống → tìm khắp nơi.
   */
  private Specification<SensorReading> search(String q, String field) {
    String needle = QueryService.keyword(q);
    if (needle == null) return null;
    return (root, query, cb) -> {
      Predicate time = QueryService.like(cb, root.get("searchTime"), needle);
      Predicate value = QueryService.like(cb, root.get("searchValue"), needle);
      if ("time".equals(field)) return time;
      if (field != null && TYPES.contains(field)) return value;
      return cb.or(time, value, QueryService.like(cb, root.get("deviceId"), needle));
    };
  }

  public PageOut<SensorOut> records(
      String device,
      String type,
      String q,
      String field,
      Instant from,
      Instant to,
      int page,
      int size,
      String sort) {
    QueryService.choice(type, TYPES);
    QueryService.choice(field, FIELDS);
    // Chọn "Nhiệt độ" / "Độ ẩm" / "Ánh sáng" vừa thu hẹp loại cảm biến, vừa đổi ý nghĩa
    // của từ khoá thành "giá trị đo" — đúng như người dùng trông đợi khi gõ "27".
    String resolvedType = field != null && TYPES.contains(field) ? field : type;
    Page<SensorReading> result =
        readings.findAll(
            QueryService.<SensorReading>filters(
                    QueryService.values("deviceId", device, "sensorType", resolvedType), from, to)
                .and(search(q, field)),
            QueryService.page(
                page, size, sort, Set.of("id", "deviceId", "sensorType", "value", "timestamp")));
    return new PageOut<>(
        result.map(this::out).getContent(),
        page,
        size,
        result.getTotalElements(),
        Math.max(1, result.getTotalPages()));
  }

  public LatestOut latest(String device) {
    Map<String, ReadingOut> values = new HashMap<>();
    String resolved = device;
    for (String type : List.of("temperature", "humidity", "light")) {
      Optional<SensorReading> found =
          device == null
              ? readings.findFirstBySensorTypeOrderByTimestampDescIdDesc(type)
              : readings.findFirstBySensorTypeAndDeviceIdOrderByTimestampDescIdDesc(type, device);
      if (found.isPresent()) {
        SensorReading r = found.get();
        values.put(type, new ReadingOut(r.getValue().doubleValue(), r.getUnit(), r.getTimestamp()));
        if (resolved == null) resolved = r.getDeviceId();
      }
    }
    return new LatestOut(
        resolved, values.get("temperature"), values.get("humidity"), values.get("light"));
  }

  public List<SeriesOut> series(
      String device, Instant from, Instant to, String bucket, int points) {
    QueryService.choice(bucket, Set.of("1m", "5m", "1h"));
    if (points < 5 || points > 200)
      throw new ApiException(422, "VALIDATION_ERROR", "Số điểm không hợp lệ.");
    long seconds = Map.of("1m", 60L, "5m", 300L, "1h", 3600L).get(bucket);
    Instant end = to == null ? Instant.now() : to;
    Instant start = from == null ? end.minusSeconds(seconds * points) : from;
    var rows =
        readings
            .findAll(
                QueryService.<SensorReading>filters(
                    QueryService.values("deviceId", device), start, end),
                PageRequest.of(0, 20000, Sort.by("timestamp")))
            .getContent();
    TreeMap<Long, Map<String, List<Double>>> groups = new TreeMap<>();
    for (SensorReading r : rows)
      groups
          .computeIfAbsent(r.getTimestamp().getEpochSecond() / seconds, k -> new HashMap<>())
          .computeIfAbsent(r.getSensorType(), k -> new ArrayList<>())
          .add(r.getValue().doubleValue());
    List<SeriesOut> result = new ArrayList<>();
    groups.forEach(
        (index, values) -> {
          Instant time = Instant.ofEpochSecond(index * seconds);
          result.add(
              new SeriesOut(
                  DateTimeFormatter.ofPattern("HH:mm")
                      .withZone(ZoneId.of("Asia/Ho_Chi_Minh"))
                      .format(time),
                  time,
                  average(values.get("temperature")),
                  average(values.get("humidity")),
                  average(values.get("light"))));
        });
    return result.subList(Math.max(0, result.size() - points), result.size());
  }

  private Double average(List<Double> values) {
    return values == null
        ? null
        : Math.round(values.stream().mapToDouble(v -> v).average().orElse(0) * 100) / 100.0;
  }

  @Transactional
  public Map<String, Object> ingest(SensorPayload p) {
    Instant time = p.ts() == null ? Instant.now() : p.ts();
    Map<String, Object> event = new HashMap<>();
    event.put("device_id", p.deviceId());
    event.put("timestamp", time);
    Double[] values = {p.temp(), p.humid(), p.light()};
    String[] types = {"temperature", "humidity", "light"}, units = {"°C", "%", "lux"};
    double[] low = {-40, 0, 0}, high = {85, 100, 100000};
    for (int i = 0; i < 3; i++) {
      Double v = values[i];
      if (v == null || !Double.isFinite(v) || v < low[i] || v > high[i]) {
        event.put(types[i], null);
        continue;
      }
      SensorReading r = new SensorReading();
      r.setDeviceId(p.deviceId());
      r.setSensorType(types[i]);
      r.setValue(BigDecimal.valueOf(v).setScale(2, RoundingMode.HALF_UP));
      r.setUnit(units[i]);
      r.setTimestamp(time);
      readings.save(r);
      event.put(types[i], r.getValue().doubleValue());
    }
    return event;
  }
}
