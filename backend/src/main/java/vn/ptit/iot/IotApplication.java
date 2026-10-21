package vn.ptit.iot;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.scheduling.annotation.EnableScheduling;
import vn.ptit.iot.config.Dotenv;

@SpringBootApplication(
    exclude =
        org.springframework.boot.autoconfigure.security.servlet.UserDetailsServiceAutoConfiguration
            .class)
@EnableScheduling
public class IotApplication {
  public static void main(String[] args) {
    Dotenv.load();
    SpringApplication.run(IotApplication.class, args);
  }
}
