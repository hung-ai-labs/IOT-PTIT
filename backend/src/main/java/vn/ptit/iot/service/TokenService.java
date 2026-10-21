package vn.ptit.iot.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.time.Instant;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import vn.ptit.iot.exception.ApiException;

@Service
public class TokenService {
  private final ObjectMapper mapper;
  private final byte[] secret;
  private final long lifetime;
  private final Map<String, Long> revoked = new ConcurrentHashMap<>();

  public TokenService(
      ObjectMapper mapper,
      @Value("${iot.secret}") String secret,
      @Value("${iot.token-hours}") long hours) {
    if (secret.isBlank())
      throw new IllegalStateException("Cần cấu hình SECRET_KEY trong .env hoặc biến môi trường.");
    this.mapper = mapper;
    this.secret = secret.getBytes(StandardCharsets.UTF_8);
    lifetime = hours * 3600;
  }

  private String encode(byte[] value) {
    return Base64.getUrlEncoder().withoutPadding().encodeToString(value);
  }

  private byte[] sign(String value) throws Exception {
    Mac mac = Mac.getInstance("HmacSHA256");
    mac.init(new SecretKeySpec(secret, "HmacSHA256"));
    return mac.doFinal(value.getBytes(StandardCharsets.US_ASCII));
  }

  public String create(Long id, String role) {
    try {
      long now = Instant.now().getEpochSecond();
      String header = encode(mapper.writeValueAsBytes(Map.of("alg", "HS256", "typ", "JWT")));
      String payload =
          encode(
              mapper.writeValueAsBytes(
                  Map.of(
                      "sub",
                      id.toString(),
                      "role",
                      role,
                      "iat",
                      now,
                      "exp",
                      now + lifetime,
                      "jti",
                      UUID.randomUUID().toString().replace("-", ""))));
      String input = header + "." + payload;
      return input + "." + encode(sign(input));
    } catch (Exception e) {
      throw new IllegalStateException("Không tạo được token", e);
    }
  }

  public Map<String, Object> verify(String token) {
    try {
      String[] parts = token.split("\\.");
      if (parts.length != 3) throw new IllegalArgumentException();
      Map<?, ?> header = mapper.readValue(Base64.getUrlDecoder().decode(parts[0]), Map.class);
      if (!"HS256".equals(header.get("alg"))
          || !MessageDigest.isEqual(
              sign(parts[0] + "." + parts[1]), Base64.getUrlDecoder().decode(parts[2])))
        throw new IllegalArgumentException();
      @SuppressWarnings("unchecked")
      Map<String, Object> claims =
          mapper.readValue(Base64.getUrlDecoder().decode(parts[1]), Map.class);
      long now = Instant.now().getEpochSecond();
      revoked.entrySet().removeIf(entry -> entry.getValue() <= now);
      if (!(claims.get("exp") instanceof Number exp)
          || exp.longValue() <= now
          || claims.get("sub") == null
          || claims.get("jti") == null
          || revoked.containsKey(claims.get("jti").toString()))
        throw new IllegalArgumentException();
      Long.parseLong(claims.get("sub").toString());
      return claims;
    } catch (Exception e) {
      throw new ApiException(
          401, "UNAUTHORIZED", "Token không hợp lệ, đã hết hạn hoặc đã bị thu hồi.");
    }
  }

  public void revoke(String token) {
    Map<String, Object> c = verify(token);
    revoked.put(c.get("jti").toString(), ((Number) c.get("exp")).longValue());
  }

  public long lifetime() {
    return lifetime;
  }
}
