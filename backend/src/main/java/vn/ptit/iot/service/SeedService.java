package vn.ptit.iot.service;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.ApplicationArguments;
import org.springframework.boot.ApplicationRunner;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.context.ConfigurableApplicationContext;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.stereotype.Service;
import vn.ptit.iot.entity.User;
import vn.ptit.iot.repository.UserRepository;

@Service
@ConditionalOnProperty(name = "iot.seed-accounts", havingValue = "true")
public class SeedService implements ApplicationRunner {
  private final UserRepository users;
  private final ConfigurableApplicationContext context;
  private final String password;

  public SeedService(
      UserRepository users,
      ConfigurableApplicationContext context,
      @Value("${SEED_PASSWORD:}") String password) {
    this.users = users;
    this.context = context;
    this.password = password;
  }

  public void run(ApplicationArguments args) {
    if (password.length() < 6
        || password.getBytes(java.nio.charset.StandardCharsets.UTF_8).length > 72)
      throw new IllegalArgumentException("Đặt SEED_PASSWORD từ 6 ký tự và không vượt quá 72 byte.");
    for (String email : java.util.List.of("admin@ptit.edu.vn", "user@ptit.edu.vn")) {
      if (users.existsByEmail(email)) continue;
      boolean admin = email.startsWith("admin@");
      User user = new User();
      user.setFullName(admin ? "Nguyễn Xuân Hùng" : "Người dùng thử nghiệm");
      user.setEmail(email);
      user.setPasswordHash(new BCryptPasswordEncoder(12).encode(password));
      user.setRole(admin ? "ADMIN" : "USER");
      if (admin) {
        user.setStudentId("B23DCCN361");
        user.setSchool("Học Viện Công Nghệ Bưu Chính Viễn Thông");
        user.setContactEmail("Hungmk2005@gmail.com");
      }
      users.saveAndFlush(user);
    }
    System.out.println("Đã khởi tạo tài khoản. Không tạo dữ liệu cảm biến hoặc lịch sử mẫu.");
    System.exit(SpringApplication.exit(context));
  }
}
