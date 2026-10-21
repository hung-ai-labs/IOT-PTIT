package vn.ptit.iot.entity;

import jakarta.persistence.*;
import java.time.Instant;
import java.util.UUID;
import org.hibernate.annotations.Formula;

@Entity
@Table(name = "device_actions")
public class DeviceAction {
  @Id
  @GeneratedValue(strategy = GenerationType.IDENTITY)
  private Long id;

  public Long getId() {
    return id;
  }

  @Column(name = "device_id", nullable = false, length = 50)
  private String deviceId;

  @Column(name = "target", nullable = false, length = 20)
  private String target;

  @Column(name = "action", nullable = false, length = 20)
  private String action;

  @Column(name = "issued_by", nullable = true)
  private Long issuedBy;

  @Column(name = "result", nullable = false, length = 20)
  private String result;

  @Column(name = "timestamp", nullable = false)
  private Instant timestamp;

  @Column(name = "cmd_id", nullable = false, unique = true)
  private UUID cmdId;

  @Column(name = "responded_at", nullable = true)
  private Instant respondedAt;

  @Column(name = "error_msg", nullable = true, length = 255)
  private String errorMsg;

  /* Cột dẫn xuất chỉ phục vụ ô TÌM KIẾM. Người dùng gõ đúng chuỗi họ nhìn thấy trên
     bảng ("16:25", "07/10/2026 16:25"), nên phép so khớp phải chạy trên bản đã định
     dạng theo giờ Việt Nam chứ không phải trên TIMESTAMPTZ gốc (UTC). */
  @Formula("to_char(timestamp AT TIME ZONE 'Asia/Ho_Chi_Minh', 'DD/MM/YYYY HH24:MI:SS')")
  private String searchTime;

  public String getSearchTime() {
    return searchTime;
  }

  public String getDeviceId() {
    return deviceId;
  }

  public void setDeviceId(String value) {
    this.deviceId = value;
  }

  public String getTarget() {
    return target;
  }

  public void setTarget(String value) {
    this.target = value;
  }

  public String getAction() {
    return action;
  }

  public void setAction(String value) {
    this.action = value;
  }

  public Long getIssuedBy() {
    return issuedBy;
  }

  public void setIssuedBy(Long value) {
    this.issuedBy = value;
  }

  public String getResult() {
    return result;
  }

  public void setResult(String value) {
    this.result = value;
  }

  public Instant getTimestamp() {
    return timestamp;
  }

  public void setTimestamp(Instant value) {
    this.timestamp = value;
  }

  public UUID getCmdId() {
    return cmdId;
  }

  public void setCmdId(UUID value) {
    this.cmdId = value;
  }

  public Instant getRespondedAt() {
    return respondedAt;
  }

  public void setRespondedAt(Instant value) {
    this.respondedAt = value;
  }

  public String getErrorMsg() {
    return errorMsg;
  }

  public void setErrorMsg(String value) {
    this.errorMsg = value;
  }

  @PrePersist
  void onCreate() {
    if (timestamp == null) timestamp = Instant.now();
  }
}
