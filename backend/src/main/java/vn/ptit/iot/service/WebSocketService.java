package vn.ptit.iot.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import java.io.IOException;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import org.springframework.stereotype.Component;
import org.springframework.web.socket.*;
import org.springframework.web.socket.handler.ConcurrentWebSocketSessionDecorator;
import org.springframework.web.socket.handler.TextWebSocketHandler;
import org.springframework.web.util.UriComponentsBuilder;

@Component
public class WebSocketService extends TextWebSocketHandler {
  private record Connection(WebSocketSession session, String token) {}

  private final Map<String, Connection> clients = new ConcurrentHashMap<>();
  private final TokenService tokens;
  private final AuthService auth;
  private final ObjectMapper mapper;

  public WebSocketService(TokenService tokens, AuthService auth, ObjectMapper mapper) {
    this.tokens = tokens;
    this.auth = auth;
    this.mapper = mapper;
  }

  @Override
  public void afterConnectionEstablished(WebSocketSession session) throws Exception {
    String token =
        session.getUri() == null
            ? null
            : UriComponentsBuilder.fromUri(session.getUri())
                .build()
                .getQueryParams()
                .getFirst("token");
    try {
      auth.current(Long.valueOf(tokens.verify(token == null ? "" : token).get("sub").toString()));
      clients.put(
          session.getId(),
          new Connection(new ConcurrentWebSocketSessionDecorator(session, 5000, 65536), token));
    } catch (Exception e) {
      session.close(CloseStatus.POLICY_VIOLATION.withReason("Token không hợp lệ hoặc đã hết hạn."));
    }
  }

  @Override
  public void afterConnectionClosed(WebSocketSession s, CloseStatus status) {
    clients.remove(s.getId());
  }

  @Override
  public void handleTransportError(WebSocketSession s, Throwable exception) throws Exception {
    clients.remove(s.getId());
    if (s.isOpen()) s.close(CloseStatus.SERVER_ERROR);
  }

  public void broadcast(String type, Object data) {
    String message;
    try {
      message = mapper.writeValueAsString(Map.of("type", type, "data", data));
    } catch (Exception e) {
      throw new IllegalStateException(e);
    }
    clients.forEach(
        (id, connection) -> {
          try {
            tokens.verify(connection.token());
            connection.session().sendMessage(new TextMessage(message));
          } catch (Exception e) {
            clients.remove(id);
            try {
              connection.session().close(CloseStatus.POLICY_VIOLATION);
            } catch (IOException ignored) {
            }
          }
        });
  }
}
