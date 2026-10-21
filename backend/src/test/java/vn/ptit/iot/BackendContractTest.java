package vn.ptit.iot;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

import com.fasterxml.jackson.databind.*;
import java.net.URI;
import java.nio.charset.StandardCharsets;
import java.util.*;
import org.junit.jupiter.api.*;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.test.web.servlet.*;
import org.springframework.web.socket.*;
import vn.ptit.iot.dto.ApiDtos.*;
import vn.ptit.iot.entity.User;
import vn.ptit.iot.repository.*;
import vn.ptit.iot.service.*;

@SpringBootTest
@AutoConfigureMockMvc
@ActiveProfiles("test")
class BackendContractTest {
  @Autowired MockMvc mvc;
  @Autowired ObjectMapper json;
  @Autowired UserRepository users;
  @Autowired SensorRepository sensors;
  @Autowired ActionRepository actions;
  @Autowired DeviceStateService states;
  @Autowired MqttMessageService messages;
  @Autowired TokenService tokens;
  @Autowired WebSocketService sockets;
  @MockitoBean MqttService mqtt;
  @Autowired javax.sql.DataSource testDatabase;
  private String token;

  @BeforeEach
  void setup() throws Exception {
    try (var connection = testDatabase.getConnection()) {
      assertTrue(
          connection.getMetaData().getURL().startsWith("jdbc:h2:"),
          "Tests must use H2, never the application database");
    }
    actions.deleteAll();
    sensors.deleteAll();
    users.deleteAll();
    states.clear();
    reset(mqtt);
    mvc.perform(
            post("/api/v1/auth/register")
                .contentType("application/json")
                .content(
                    "{\"full_name\":\"Nguyễn Xuân Hùng\",\"email\":\"Hung@example.com\",\"password\":\"123456\"}"))
        .andExpect(status().isCreated())
        .andExpect(jsonPath("$.email").value("hung@example.com"));
    token =
        json.readTree(
                mvc.perform(
                        post("/api/v1/auth/login")
                            .contentType("application/json")
                            .content("{\"email\":\"hung@example.com\",\"password\":\"123456\"}"))
                    .andReturn()
                    .getResponse()
                    .getContentAsString())
            .get("access_token")
            .asText();
  }

  private String bearer() {
    return "Bearer " + token;
  }

  private void message(String topic, String payload) {
    messages.incoming(new MqttService.Incoming(topic, payload.getBytes(StandardCharsets.UTF_8)));
  }

  @Test
  void deviceListAndSingleTargetDetailStayDistinct() throws Exception {
    states.touch("ESP32-01", "192.168.1.50", -55, 3600L);
    states.set("ESP32-01", "red", true);
    states.set("ESP32-02", "red", false);
    mvc.perform(get("/api/v1/devices").param("device_id", "ESP32-01")
            .header("Authorization", bearer()))
        .andExpect(status().isOk()).andExpect(jsonPath("$.length()").value(3));
    for (String target : List.of("red", "green", "yellow")) {
      mvc.perform(get("/api/v1/devices/ESP32-01/targets/" + target)
              .header("Authorization", bearer()))
          .andExpect(status().isOk())
          .andExpect(jsonPath("$.device_id").value("ESP32-01"))
          .andExpect(jsonPath("$.target").value(target))
          .andExpect(jsonPath("$.state").value(target.equals("red") ? "ON" : "OFF"))
          .andExpect(jsonPath("$.ip").value("192.168.1.50"))
          .andExpect(jsonPath("$.targets").doesNotExist());
    }
    mvc.perform(get("/api/v1/devices/ESP32-02/targets/red")
            .header("Authorization", bearer()))
        .andExpect(status().isOk()).andExpect(jsonPath("$.state").value("OFF"));
    mvc.perform(get("/api/v1/devices/ESP32-01/targets/unknown")
            .header("Authorization", bearer()))
        .andExpect(status().isNotFound())
        .andExpect(jsonPath("$.detail.code").value("TARGET_NOT_FOUND"));
    mvc.perform(get("/api/v1/devices/ESP32-01/targets/red"))
        .andExpect(status().isUnauthorized());
    mvc.perform(get("/api/v1/devices/ESP32-01").header("Authorization", bearer()))
        .andExpect(status().isOk()).andExpect(jsonPath("$.targets.length()").value(3));
    var spec = json.readTree(mvc.perform(get("/openapi.json"))
        .andExpect(status().isOk()).andReturn().getResponse().getContentAsString());
    assertTrue(spec.path("paths").has("/api/v1/devices/{id}/targets/{target}"));
    assertFalse(spec.path("paths").has("/api/v1/devices/{id}"));
  }

  @Test
  void authProfileAndRevocation() throws Exception {
    mvc.perform(get("/api/v1/auth/me"))
        .andExpect(status().isUnauthorized())
        .andExpect(jsonPath("$.detail.code").value("UNAUTHORIZED"));
    mvc.perform(
            patch("/api/v1/auth/me")
                .header("Authorization", bearer())
                .contentType("application/json")
                .content(
                    "{\"full_name\":\"Nguyễn Xuân Hùng\",\"student_id\":\"B23DCCN361\",\"school\":\"PTIT\",\"contact_email\":\"Hungmk2005@gmail.com\"}"))
        .andExpect(status().isOk())
        .andExpect(jsonPath("$.student_id").value("B23DCCN361"));
    mvc.perform(
            patch("/api/v1/auth/me")
                .header("Authorization", bearer())
                .contentType("application/json")
                .content("{\"full_name\":\"Tên mới\"}"))
        .andExpect(status().isOk())
        .andExpect(jsonPath("$.school").value("PTIT"));
    mvc.perform(
            patch("/api/v1/auth/me")
                .header("Authorization", bearer())
                .contentType("application/json")
                .content("{\"full_name\":\"Tên mới\",\"role\":\"ADMIN\"}"))
        .andExpect(status().isUnprocessableEntity());
    mvc.perform(get("/api/v1/auth/me").header("Authorization", bearer()))
        .andExpect(jsonPath("$.role").value("USER"))
        .andExpect(jsonPath("$.password_hash").doesNotExist());
    mvc.perform(post("/api/v1/auth/logout").header("Authorization", bearer()))
        .andExpect(status().isNoContent());
    mvc.perform(get("/api/v1/auth/me").header("Authorization", bearer()))
        .andExpect(status().isUnauthorized());
  }

  @Test
  void validationAndAccountIsolation() throws Exception {
    mvc.perform(
            post("/api/v1/auth/register")
                .contentType("application/json")
                .content(
                    "{\"full_name\":\"Người khác\",\"email\":\"other@example.com\",\"password\":\"123456\"}"))
        .andExpect(status().isCreated());
    mvc.perform(
            post("/api/v1/auth/register")
                .contentType("application/json")
                .content(
                    "{\"full_name\":\"Trùng\",\"email\":\"HUNG@example.com\",\"password\":\"123456\"}"))
        .andExpect(status().isConflict());
    mvc.perform(
            post("/api/v1/auth/login")
                .contentType("application/json")
                .content("{\"email\":\"hung@example.com\",\"password\":\"bad\"}"))
        .andExpect(status().isUnauthorized());
    mvc.perform(
            patch("/api/v1/auth/me")
                .header("Authorization", bearer())
                .contentType("application/json")
                .content("{\"full_name\":\"Hùng\",\"contact_email\":\"invalid\"}"))
        .andExpect(status().isUnprocessableEntity());
    mvc.perform(
            patch("/api/v1/auth/me")
                .header("Authorization", bearer())
                .contentType("application/json")
                .content("{\"full_name\":\"Hùng\"}"))
        .andExpect(status().isOk());
    assertEquals("Người khác", users.findByEmail("other@example.com").orElseThrow().getFullName());
  }

  @Test
  void emptySensorAndHistoryContracts() throws Exception {
    mvc.perform(get("/api/v1/sensors/latest").header("Authorization", bearer()))
        .andExpect(status().isOk())
        .andExpect(jsonPath("$.temperature").isEmpty());
    mvc.perform(get("/api/v1/sensors/series").header("Authorization", bearer()))
        .andExpect(content().json("[]"));
    mvc.perform(get("/api/v1/sensors").header("Authorization", bearer()))
        .andExpect(jsonPath("$.total").value(0))
        .andExpect(jsonPath("$.total_pages").value(1));
    mvc.perform(get("/api/v1/device-actions").header("Authorization", bearer()))
        .andExpect(jsonPath("$.items").isEmpty());
    mvc.perform(
            get("/api/v1/sensors")
                .param("sensor_type", "invalid")
                .header("Authorization", bearer()))
        .andExpect(status().isUnprocessableEntity());
    mvc.perform(get("/api/v1/sensors").param("size", "101").header("Authorization", bearer()))
        .andExpect(status().isUnprocessableEntity());
  }

  @Test
  void mqttSensorsValidatePersistAndFilter() throws Exception {
    message("iot/sensor", "{\"device_id\":\"ESP32-01\",\"temp\":27.5,\"humid\":68,\"light\":420}");
    assertEquals(3, sensors.count());
    assertTrue(states.online(states.get("ESP32-01")));
    message("iot/sensor", "{\"device_id\":\"ESP32-02\",\"temp\":999,\"humid\":-1,\"light\":10}");
    assertEquals(4, sensors.count());
    message("iot/sensor", "{\"temp\":10}");
    message("iot/sensor", "bad-json");
    assertEquals(4, sensors.count());
    mvc.perform(
            get("/api/v1/sensors/latest")
                .param("device_id", "ESP32-01")
                .header("Authorization", bearer()))
        .andExpect(jsonPath("$.temperature.value").value(27.5));
    mvc.perform(
            get("/api/v1/sensors")
                .param("sensor_type", "light")
                .param("size", "1")
                .header("Authorization", bearer()))
        .andExpect(jsonPath("$.total").value(2))
        .andExpect(jsonPath("$.total_pages").value(2));
    mvc.perform(
            get("/api/v1/sensors/series")
                .param("device_id", "ESP32-01")
                .header("Authorization", bearer()))
        .andExpect(jsonPath("$[0].temp").value(27.5));
  }

  @Test
  void freeTextSearchMatchesWhatTheTableShows() throws Exception {
    message("iot/sensor", "{\"device_id\":\"ESP32-01\",\"temp\":27.5,\"humid\":68,\"light\":420}");
    message("iot/sensor", "{\"device_id\":\"ESP32-02\",\"temp\":31.5,\"humid\":55,\"light\":90}");

    // Gõ "27" khi đang chọn "Nhiệt độ" → chỉ còn phép đo nhiệt độ bắt đầu bằng 27.
    mvc.perform(
            get("/api/v1/sensors")
                .param("q", "27")
                .param("field", "temperature")
                .header("Authorization", bearer()))
        .andExpect(jsonPath("$.total").value(1))
        .andExpect(jsonPath("$.items[0].value").value(27.5));

    // Cùng từ khoá nhưng phạm vi "Độ ẩm" thì không có kết quả.
    mvc.perform(
            get("/api/v1/sensors")
                .param("q", "27")
                .param("field", "humidity")
                .header("Authorization", bearer()))
        .andExpect(jsonPath("$.total").value(0));

    // Bỏ trống phạm vi thì tìm cả ở device_id.
    mvc.perform(
            get("/api/v1/sensors").param("q", "ESP32-02").header("Authorization", bearer()))
        .andExpect(jsonPath("$.total").value(3));

    // Ngày hôm nay theo giờ Việt Nam, đúng chuỗi bảng hiển thị.
    String today =
        java.time.format.DateTimeFormatter.ofPattern("dd/MM/yyyy")
            .withZone(java.time.ZoneId.of("Asia/Ho_Chi_Minh"))
            .format(java.time.Instant.now());
    mvc.perform(
            get("/api/v1/sensors")
                .param("q", today)
                .param("field", "time")
                .header("Authorization", bearer()))
        .andExpect(jsonPath("$.total").value(6));

    // Phạm vi lạ phải bị từ chối chứ không âm thầm bỏ qua.
    mvc.perform(
            get("/api/v1/sensors")
                .param("q", "27")
                .param("field", "khong-ton-tai")
                .header("Authorization", bearer()))
        .andExpect(status().isUnprocessableEntity());

    // History keyword searches timestamps only; other columns use dedicated filters.
    when(mqtt.connected()).thenReturn(true);
    when(mqtt.publish(anyString(), any())).thenReturn(true);
    states.touch("ESP32-01", null, null, null);
    send("red");
    mvc.perform(get("/api/v1/device-actions").param("q", today).header("Authorization", bearer()))
        .andExpect(jsonPath("$.total").value(1))
        .andExpect(jsonPath("$.items[0].target").value("red"));
    mvc.perform(get("/api/v1/device-actions").param("q", "Bật").header("Authorization", bearer()))
        .andExpect(jsonPath("$.total").value(0));
    mvc.perform(get("/api/v1/device-actions").param("q", "Đèn đỏ").header("Authorization", bearer()))
        .andExpect(jsonPath("$.total").value(0));
    mvc.perform(get("/api/v1/device-actions").param("target", "red").param("action", "ON")
            .header("Authorization", bearer()))
        .andExpect(jsonPath("$.total").value(1));
  }

  private JsonNode send(String target) throws Exception {
    return json.readTree(
        mvc.perform(
                post("/api/v1/devices/ESP32-01/actions")
                    .header("Authorization", bearer())
                    .contentType("application/json")
                    .content("{\"target\":\"" + target + "\",\"action\":\"ON\"}"))
            .andExpect(status().isAccepted())
            .andReturn()
            .getResponse()
            .getContentAsString());
  }

  @Test
  void deviceControlFeedbackAndDuplicateGuard() throws Exception {
    when(mqtt.connected()).thenReturn(true);
    when(mqtt.publish(anyString(), any())).thenReturn(true);
    states.touch("ESP32-01", null, null, null);
    mvc.perform(get("/api/v1/devices").header("Authorization", bearer()))
        .andExpect(jsonPath("$[0].name").value("Đèn đỏ"))
        .andExpect(jsonPath("$[1].name").value("Đèn xanh"));
    JsonNode accepted = send("green");
    mvc.perform(
            post("/api/v1/devices/ESP32-01/actions")
                .header("Authorization", bearer())
                .contentType("application/json")
                .content("{\"target\":\"green\",\"action\":\"OFF\"}"))
        .andExpect(status().isConflict());
    message(
        "iot/feedback",
        "{\"cmd_id\":\""
            + accepted.get("cmd_id").asText()
            + "\",\"device_id\":\"ESP32-01\",\"target\":\"green\",\"state\":\"ON\",\"result\":\"Success\"}");
    mvc.perform(
            get("/api/v1/device-actions/" + accepted.get("action_id").asLong())
                .header("Authorization", bearer()))
        .andExpect(jsonPath("$.result").value("Success"))
        .andExpect(jsonPath("$.target_label").value("Đèn xanh"));
    assertEquals(true, states.get("ESP32-01").targets().get("green"));
  }

  @Test
  void timeoutCannotBeOverwrittenByLateFeedback() throws Exception {
    when(mqtt.connected()).thenReturn(true);
    when(mqtt.publish(anyString(), any())).thenReturn(true);
    states.touch("ESP32-01", null, null, null);
    JsonNode accepted = send("red");
    Thread.sleep(800);
    message(
        "iot/feedback",
        "{\"cmd_id\":\""
            + accepted.get("cmd_id").asText()
            + "\",\"device_id\":\"ESP32-01\",\"target\":\"red\",\"state\":\"ON\"}");
    assertEquals(
        "Timeout", actions.findById(accepted.get("action_id").asLong()).orElseThrow().getResult());
    assertNull(states.get("ESP32-01").targets().get("red"));
  }

  @Test
  void controlFailuresAndStatus() throws Exception {
    mvc.perform(
            post("/api/v1/devices/ESP32-01/actions")
                .header("Authorization", bearer())
                .contentType("application/json")
                .content("{\"target\":\"yellow\",\"action\":\"ON\"}"))
        .andExpect(status().isServiceUnavailable());
    when(mqtt.connected()).thenReturn(true);
    mvc.perform(
            post("/api/v1/devices/ESP32-01/actions")
                .header("Authorization", bearer())
                .contentType("application/json")
                .content("{\"target\":\"yellow\",\"action\":\"ON\"}"))
        .andExpect(status().isConflict());
    states.touch("ESP32-01", null, null, null);
    mvc.perform(
            post("/api/v1/devices/ESP32-01/actions")
                .header("Authorization", bearer())
                .contentType("application/json")
                .content("{\"target\":\"yellow\",\"action\":\"ON\"}"))
        .andExpect(status().isServiceUnavailable());
    assertEquals("Failed", actions.findAll().get(0).getResult());
    mvc.perform(get("/api/v1/system/status").header("Authorization", bearer()))
        .andExpect(jsonPath("$.database.status").value("connected"))
        .andExpect(jsonPath("$.esp.status").value("online"));
    mvc.perform(get("/health")).andExpect(status().isOk());
  }

  @Test
  void legacyBcryptAndJwtRemainCompatible() throws Exception {
    User u = users.findByEmail("hung@example.com").orElseThrow();
    String hash = u.getPasswordHash().replaceFirst("\\$2a\\$", "\\$2b\\$");
    u.setPasswordHash(hash);
    users.save(u);
    mvc.perform(
            post("/api/v1/auth/login")
                .contentType("application/json")
                .content("{\"email\":\"hung@example.com\",\"password\":\"123456\"}"))
        .andExpect(status().isOk());
    String[] parts = token.split("\\.");
    assertEquals(
        "HS256", json.readTree(Base64.getUrlDecoder().decode(parts[0])).get("alg").asText());
    assertEquals(u.getId().toString(), tokens.verify(token).get("sub"));
  }

  @Test
  void webSocketAuthenticationBroadcastAndRevocation() throws Exception {
    WebSocketSession bad = mock(WebSocketSession.class);
    when(bad.getUri()).thenReturn(URI.create("ws://localhost/ws?token=bad"));
    sockets.afterConnectionEstablished(bad);
    verify(bad).close(any(CloseStatus.class));
    WebSocketSession good = mock(WebSocketSession.class);
    when(good.getId()).thenReturn("test-session");
    when(good.getUri()).thenReturn(URI.create("ws://localhost/ws?token=" + token));
    when(good.isOpen()).thenReturn(true);
    sockets.afterConnectionEstablished(good);
    sockets.broadcast("sensor", Map.of("temperature", 20));
    verify(good).sendMessage(any(TextMessage.class));
    tokens.revoke(token);
    sockets.broadcast("sensor", Map.of("temperature", 21));
    verify(good).close(CloseStatus.POLICY_VIOLATION);
  }
}
