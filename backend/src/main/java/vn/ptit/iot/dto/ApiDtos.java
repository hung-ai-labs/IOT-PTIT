package vn.ptit.iot.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import jakarta.validation.constraints.*;
import java.time.Instant;
import java.util.*;

public final class ApiDtos {
  private ApiDtos() {}

  public record RegisterRequest(
      @NotBlank @Size(min = 2, max = 100) @JsonProperty("full_name") String fullName,
      @NotBlank @Email @Size(max = 150) String email,
      @NotBlank @Size(min = 6, max = 72) String password) {
    public RegisterRequest {
      fullName = fullName == null ? null : fullName.strip();
      email = email == null ? null : email.strip();
    }
  }

  public record LoginRequest(
      @NotBlank @Email @Size(max = 150) String email, @NotBlank @Size(max = 72) String password) {
    public LoginRequest {
      email = email == null ? null : email.strip();
    }
  }

  public record ProfileRequest(
      @NotBlank @Size(min = 2, max = 100) @JsonProperty("full_name") String fullName,
      @Size(max = 30) @JsonProperty("student_id") String studentId,
      @Size(max = 200) String school,
      @Email @Size(max = 150) @JsonProperty("contact_email") String contactEmail) {}

  public record UserOut(
      Long id,
      @JsonProperty("full_name") String fullName,
      String email,
      @JsonProperty("student_id") String studentId,
      String school,
      @JsonProperty("contact_email") String contactEmail,
      String role,
      @JsonProperty("created_at") Instant createdAt) {}

  public record TokenOut(
      @JsonProperty("access_token") String accessToken,
      @JsonProperty("token_type") String tokenType,
      @JsonProperty("expires_in") long expiresIn,
      UserOut user) {}

  public record PageOut<T>(
      List<T> items, int page, int size, long total, @JsonProperty("total_pages") int totalPages) {}

  public record SensorOut(
      Long id,
      @JsonProperty("device_id") String deviceId,
      @JsonProperty("sensor_type") String sensorType,
      double value,
      String unit,
      Instant timestamp) {}

  public record ReadingOut(double value, String unit, Instant timestamp) {}

  public record LatestOut(
      @JsonProperty("device_id") String deviceId,
      ReadingOut temperature,
      ReadingOut humidity,
      ReadingOut light) {}

  public record SeriesOut(
      String time, Instant timestamp, Double temp, Double humidity, Double light) {}

  public record ActionRequest(
      @NotBlank @Pattern(regexp = "red|green|yellow") String target,
      @NotBlank @Pattern(regexp = "ON|OFF") String action) {}

  public record DeviceOut(
      @JsonProperty("device_id") String deviceId,
      String target,
      String name,
      String gpio,
      String icon,
      String state,
      String connection,
      @JsonProperty("last_command") Instant lastCommand,
      @JsonProperty("last_seen") Instant lastSeen) {}

  public record DeviceTargetDetailOut(
      @JsonProperty("device_id") String deviceId,
      String target,
      String name,
      String gpio,
      String icon,
      String state,
      String connection,
      @JsonProperty("last_command") Instant lastCommand,
      @JsonProperty("last_seen") Instant lastSeen,
      String ip,
      Integer rssi,
      Long uptime,
      @JsonProperty("command_topic") String commandTopic,
      @JsonProperty("feedback_topic") String feedbackTopic) {}

  public record DeviceDetailOut(
      @JsonProperty("device_id") String deviceId,
      String connection,
      String ip,
      Integer rssi,
      Long uptime,
      @JsonProperty("last_seen") Instant lastSeen,
      @JsonProperty("command_topic") String commandTopic,
      @JsonProperty("feedback_topic") String feedbackTopic,
      List<DeviceOut> targets) {}

  public record IssuerOut(Long id, @JsonProperty("full_name") String fullName) {}

  public record ActionOut(
      Long id,
      @JsonProperty("device_id") String deviceId,
      String target,
      @JsonProperty("target_label") String targetLabel,
      String action,
      @JsonProperty("issued_by") IssuerOut issuedBy,
      String result,
      Instant timestamp,
      @JsonProperty("responded_at") Instant respondedAt,
      @JsonProperty("error_msg") String errorMsg) {}

  public record AcceptedOut(
      @JsonProperty("action_id") Long actionId,
      @JsonProperty("cmd_id") UUID cmdId,
      @JsonProperty("device_id") String deviceId,
      String target,
      String action,
      String result,
      @JsonProperty("timeout_seconds") double timeoutSeconds) {}

  public record ErrorOut(ErrorDetail detail) {}

  public record ErrorDetail(String code, String message) {}

  public record SensorPayload(
      @NotBlank @Size(max = 50) @JsonProperty("device_id") String deviceId,
      Double temp,
      Double humid,
      Double light,
      Instant ts) {}

  public record FeedbackPayload(
      @NotBlank @Size(max = 50) @JsonProperty("device_id") String deviceId,
      @NotBlank @Pattern(regexp = "red|green|yellow") String target,
      @NotBlank @Pattern(regexp = "ON|OFF") String state,
      @Pattern(regexp = "Success|Failed") String result,
      @JsonProperty("cmd_id") UUID cmdId,
      @Size(max = 255) String error,
      Instant ts) {}

  public record StatusPayload(
      @NotBlank @Size(max = 50) @JsonProperty("device_id") String deviceId,
      @Pattern(regexp = "online|offline") String status,
      @Size(max = 100) String ip,
      Integer rssi,
      Long uptime) {}

  public record EspOut(
      String status,
      @JsonProperty("device_id") String deviceId,
      @JsonProperty("last_seen") Instant lastSeen,
      String ip,
      Integer rssi,
      Long uptime) {}

  public record MqttOut(
      String status,
      String broker,
      List<String> topics,
      @JsonProperty("messages_received") long messagesReceived) {}

  public record ApiOut(
      String status, String version, @JsonProperty("uptime_seconds") double uptimeSeconds) {}

  public record DatabaseOut(String status, @JsonProperty("latency_ms") Double latencyMs) {}

  public record SystemOut(EspOut esp, MqttOut mqtt, ApiOut api, DatabaseOut database) {}
}
