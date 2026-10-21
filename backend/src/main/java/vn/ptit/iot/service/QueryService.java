package vn.ptit.iot.service;

import jakarta.persistence.criteria.CriteriaBuilder;
import jakarta.persistence.criteria.Path;
import jakarta.persistence.criteria.Predicate;
import java.time.Instant;
import java.util.*;
import org.springframework.data.domain.*;
import org.springframework.data.jpa.domain.Specification;
import vn.ptit.iot.exception.ApiException;

public final class QueryService {
  private QueryService() {}

  public static <T> Specification<T> filters(Map<String, String> values, Instant from, Instant to) {
    return (root, query, cb) -> {
      List<Predicate> predicates = new ArrayList<>();
      values.forEach(
          (key, value) -> {
            if (value != null && !value.isBlank()) predicates.add(cb.equal(root.get(key), value));
          });
      if (from != null) predicates.add(cb.greaterThanOrEqualTo(root.get("timestamp"), from));
      if (to != null) predicates.add(cb.lessThanOrEqualTo(root.get("timestamp"), to));
      return cb.and(predicates.toArray(new Predicate[0]));
    };
  }

  public static Map<String, String> values(String... pairs) {
    Map<String, String> map = new HashMap<>();
    for (int i = 0; i < pairs.length; i += 2) map.put(pairs[i], pairs[i + 1]);
    return map;
  }

  public static Pageable page(int page, int size, String sort, Set<String> allowed) {
    if (page < 1 || size < 1 || size > 100)
      throw new ApiException(422, "VALIDATION_ERROR", "Phân trang không hợp lệ.");
    String[] parts = sort.split(":");
    String field = parts[0];
    Map<String, String> names = Map.of("device_id", "deviceId", "sensor_type", "sensorType");
    String property = names.getOrDefault(field, field);
    if (!allowed.contains(property)) property = "timestamp";
    Sort.Direction direction =
        parts.length > 1 && "asc".equals(parts[1]) ? Sort.Direction.ASC : Sort.Direction.DESC;
    return PageRequest.of(
        page - 1, size, Sort.by(direction, property).and(Sort.by(Sort.Direction.DESC, "id")));
  }

  /** Chuẩn hoá từ khoá ô tìm kiếm; `null` nghĩa là người dùng chưa gõ gì. */
  public static String keyword(String raw) {
    return raw == null || raw.isBlank() ? null : raw.trim().toLowerCase();
  }

  /** So khớp chuỗi con, không phân biệt hoa thường. Dùng cùng `keyword` ở trên. */
  public static Predicate like(CriteriaBuilder cb, Path<String> column, String keyword) {
    return cb.like(cb.lower(column), "%" + keyword + "%");
  }

  public static void choice(String value, Set<String> allowed) {
    if (value != null && !allowed.contains(value))
      throw new ApiException(422, "VALIDATION_ERROR", "Giá trị bộ lọc không hợp lệ.");
  }
}
