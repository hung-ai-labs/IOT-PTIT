package vn.ptit.iot.config;

import java.nio.file.Path;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.CacheControl;
import org.springframework.web.servlet.config.annotation.*;
import org.springframework.web.socket.config.annotation.*;
import vn.ptit.iot.service.WebSocketService;

@org.springframework.boot.autoconfigure.condition.ConditionalOnWebApplication
@Configuration
@EnableWebSocket
public class WebConfig implements WebMvcConfigurer, WebSocketConfigurer {
  private final WebSocketService sockets;
  private final String origins, frontend;

  public WebConfig(
      WebSocketService sockets,
      @Value("${iot.cors-origins}") String origins,
      @Value("${iot.frontend-dir}") String frontend) {
    this.sockets = sockets;
    this.origins = origins;
    this.frontend = frontend;
  }

  public void registerWebSocketHandlers(WebSocketHandlerRegistry registry) {
    registry.addHandler(sockets, "/ws").setAllowedOrigins(origins.split(","));
  }

  public void addResourceHandlers(ResourceHandlerRegistry registry) {
    registry
        .addResourceHandler("/**")
        .addResourceLocations(
            frontendPath().toAbsolutePath().toUri().toString(), "classpath:/static/")
        .setCacheControl(CacheControl.noCache());
  }

  private Path frontendPath() {
    Path configured = Path.of(frontend);
    return !java.nio.file.Files.isDirectory(configured)
            && java.nio.file.Files.isDirectory(Path.of("frontend"))
        ? Path.of("frontend")
        : configured;
  }

  public void addViewControllers(ViewControllerRegistry registry) {
    registry.addViewController("/").setViewName("forward:/index.html");
  }
}
