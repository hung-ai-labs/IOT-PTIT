package vn.ptit.iot.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import jakarta.annotation.PostConstruct;
import jakarta.annotation.PreDestroy;
import java.util.*;
import java.util.concurrent.atomic.AtomicLong;
import org.eclipse.paho.client.mqttv3.*;
import org.eclipse.paho.client.mqttv3.persist.MemoryPersistence;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.ApplicationEventPublisher;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;

@Service
public class MqttService {
  public record Incoming(String topic, byte[] payload) {}

  private static final Logger log = LoggerFactory.getLogger(MqttService.class);
  public static final List<String> TOPICS =
      List.of("iot/sensor", "iot/control", "iot/feedback", "iot/status");
  private final ApplicationEventPublisher events;
  private final ObjectMapper mapper;
  private final boolean enabled, legacy;
  private final String host, user, password;
  private final int port;
  private MqttAsyncClient client;
  private final AtomicLong count = new AtomicLong();

  public MqttService(
      ApplicationEventPublisher events,
      ObjectMapper mapper,
      @Value("${iot.mqtt-enabled}") boolean enabled,
      @Value("${iot.legacy-topics}") boolean legacy,
      @Value("${iot.mqtt-host}") String host,
      @Value("${iot.mqtt-port}") int port,
      @Value("${iot.mqtt-username}") String user,
      @Value("${iot.mqtt-password}") String password) {
    this.events = events;
    this.mapper = mapper;
    this.enabled = enabled;
    this.legacy = legacy;
    this.host = host;
    this.port = port;
    this.user = user;
    this.password = password;
  }

  @PostConstruct
  void initialize() throws MqttException {
    if (!enabled) return;
    client =
        new MqttAsyncClient(
            "tcp://" + host + ":" + port,
            "spring-iot-" + UUID.randomUUID(),
            new MemoryPersistence());
    client.setCallback(
        new MqttCallbackExtended() {
          public void connectComplete(boolean reconnect, String uri) {
            try {
              List<String> topics =
                  new ArrayList<>(List.of("iot/sensor", "iot/feedback", "iot/status"));
              if (legacy) topics.addAll(List.of("Sensor_data", "device_response"));
              int[] qos = new int[topics.size()];
              Arrays.fill(qos, 1);
              client.subscribe(topics.toArray(new String[0]), qos);
              log.info("MQTT connected");
            } catch (MqttException e) {
              log.warn("MQTT subscription failed", e);
            }
          }

          public void connectionLost(Throwable cause) {
            log.warn("MQTT disconnected");
          }

          public void messageArrived(String topic, MqttMessage message) {
            count.incrementAndGet();
            try {
              events.publishEvent(new Incoming(topic, message.getPayload()));
            } catch (Exception e) {
              log.warn("MQTT message processing failed", e);
            }
          }

          public void deliveryComplete(IMqttDeliveryToken token) {}
        });
  }

  @Scheduled(fixedDelay = 5000, initialDelay = 1000)
  public void connect() {
    if (client == null || client.isConnected()) return;
    try {
      MqttConnectOptions options = new MqttConnectOptions();
      options.setAutomaticReconnect(true);
      options.setCleanSession(false);
      options.setConnectionTimeout(3);
      if (!user.isBlank()) options.setUserName(user);
      if (!password.isEmpty()) options.setPassword(password.toCharArray());
      client.connect(options);
    } catch (MqttException e) {
      log.debug("Waiting for MQTT broker");
    }
  }

  public boolean connected() {
    return client != null && client.isConnected();
  }

  public boolean publish(String topic, Object payload) {
    if (!connected()) return false;
    try {
      client.publish(topic, mapper.writeValueAsBytes(payload), 1, false);
      return true;
    } catch (Exception e) {
      log.warn("MQTT publish failed");
      return false;
    }
  }

  public long messagesReceived() {
    return count.get();
  }

  public String broker() {
    return host + ":" + port;
  }

  @PreDestroy
  void close() {
    if (client != null)
      try {
        if (client.isConnected()) client.disconnect().waitForCompletion(1000);
        client.close(true);
      } catch (MqttException e) {
        log.debug("MQTT shutdown", e);
      }
  }
}
