package vn.ptit.iot.config;

import java.io.IOException;
import java.net.URI;
import java.net.URLDecoder;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;

public final class Dotenv {
  private Dotenv() {}

  public static void load() {
    Path file = Files.exists(Path.of(".env")) ? Path.of(".env") : Path.of("backend/.env");
    if (Files.exists(file)) {
      try {
        for (String line : Files.readAllLines(file)) {
          String text = line.strip();
          if (text.isEmpty() || text.startsWith("#") || !text.contains("=")) continue;
          String[] parts = text.split("=", 2);
          String key = parts[0].strip(), value = parts[1].strip();
          if (value.length() >= 2
              && ((value.startsWith("\"") && value.endsWith("\""))
                  || (value.startsWith("'") && value.endsWith("'"))))
            value = value.substring(1, value.length() - 1);
          if (key.equals("DEBUG")) continue;
          if (System.getenv(key) == null && System.getProperty(key) == null)
            System.setProperty(key, value);
        }
      } catch (IOException e) {
        throw new IllegalStateException("Không đọc được .env", e);
      }
    }
    String legacy = get("DATABASE_URL");
    if (legacy != null) {
      URI uri = URI.create(legacy.replace("postgresql+psycopg://", "postgresql://"));
      if (get("DB_URL") == null)
        System.setProperty(
            "DB_URL",
            "jdbc:postgresql://"
                + uri.getHost()
                + ":"
                + (uri.getPort() < 0 ? 5432 : uri.getPort())
                + uri.getPath());
      if (uri.getRawUserInfo() != null) {
        String[] credentials = uri.getRawUserInfo().split(":", 2);
        if (get("DB_USERNAME") == null) System.setProperty("DB_USERNAME", decode(credentials[0]));
        if (get("DB_PASSWORD") == null && credentials.length > 1)
          System.setProperty("DB_PASSWORD", decode(credentials[1]));
      }
    }
  }

  private static String decode(String value) {
    return URLDecoder.decode(value.replace("+", "%2B"), StandardCharsets.UTF_8);
  }

  private static String get(String key) {
    return System.getenv(key) != null ? System.getenv(key) : System.getProperty(key);
  }
}
