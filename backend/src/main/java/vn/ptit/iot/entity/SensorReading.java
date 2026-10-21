package vn.ptit.iot.entity;

import jakarta.persistence.*;
import java.math.BigDecimal;
import java.time.Instant;
import org.hibernate.annotations.Formula;

@Entity
@Table(name = "data_sensor")
public class SensorReading {
  @Id
  @GeneratedValue(strategy = GenerationType.IDENTITY)
  private Long id;

  public Long getId() {
    return id;
  }

  @Column(name = "device_id", nullable = false, length = 50)
  private String deviceId;

  @Column(name = "sensor_type", nullable = false, length = 20)
  private String sensorType;

  @Column(name = "value", nullable = false, precision = 10, scale = 2)
  private BigDecimal value;

  @Column(name = "unit", nullable = false, length = 10)
  private String unit;

  @Column(name = "timestamp", nullable = false)
  private Instant timestamp;

  /* Cột dẫn xuất chỉ phục vụ ô TÌM KIẾM. Người dùng gõ đúng chuỗi họ nhìn thấy trên
     bảng ("16:25", "07/10/2026 16:25"), nên phép so khớp phải chạy trên bản đã định
     dạng theo giờ Việt Nam chứ không phải trên TIMESTAMPTZ gốc (UTC). */
  @Formula("to_char(timestamp AT TIME ZONE 'Asia/Ho_Chi_Minh', 'DD/MM/YYYY HH24:MI:SS')")
  private String searchTime;

  public String getSearchTime() {
    return searchTime;
  }

  /* Giá trị dạng chữ ("27.60") để tìm theo tiền tố mà không phải ép kiểu ở mọi câu truy vấn. */
  @Formula("cast(value as varchar)")
  private String searchValue;

  public String getSearchValue() {
    return searchValue;
  }

  public String getDeviceId() {
    return deviceId;
  }

  public void setDeviceId(String value) {
    this.deviceId = value;
  }

  public String getSensorType() {
    return sensorType;
  }

  public void setSensorType(String value) {
    this.sensorType = value;
  }

  public BigDecimal getValue() {
    return value;
  }

  public void setValue(BigDecimal value) {
    this.value = value;
  }

  public String getUnit() {
    return unit;
  }

  public void setUnit(String value) {
    this.unit = value;
  }

  public Instant getTimestamp() {
    return timestamp;
  }

  public void setTimestamp(Instant value) {
    this.timestamp = value;
  }

  @PrePersist
  void onCreate() {
    if (timestamp == null) timestamp = Instant.now();
  }
}
