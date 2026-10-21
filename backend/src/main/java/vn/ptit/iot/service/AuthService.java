package vn.ptit.iot.service;

import java.nio.charset.StandardCharsets;
import java.util.*;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import vn.ptit.iot.dto.ApiDtos.*;
import vn.ptit.iot.entity.User;
import vn.ptit.iot.exception.ApiException;
import vn.ptit.iot.repository.UserRepository;

@Service
public class AuthService {
  private final UserRepository users;
  private final TokenService tokens;
  private final BCryptPasswordEncoder passwords = new BCryptPasswordEncoder(12);
  private final String dummyHash = passwords.encode("khong-ton-tai");

  public AuthService(UserRepository users, TokenService tokens) {
    this.users = users;
    this.tokens = tokens;
  }

  private String email(String s) {
    return s.strip().toLowerCase(Locale.ROOT);
  }

  private String name(String s) {
    String value = s.strip();
    if (value.length() < 2)
      throw new ApiException(422, "VALIDATION_ERROR", "Họ và tên cần ít nhất 2 ký tự.");
    return value;
  }

  private String nullable(String s) {
    return s == null || s.isBlank() ? null : s.strip();
  }

  public UserOut out(User u) {
    return new UserOut(
        u.getId(),
        u.getFullName(),
        u.getEmail(),
        u.getStudentId(),
        u.getSchool(),
        u.getContactEmail(),
        u.getRole(),
        u.getCreatedAt());
  }

  public User current(Long id) {
    return users
        .findById(id)
        .orElseThrow(() -> new ApiException(401, "UNAUTHORIZED", "Tài khoản không còn tồn tại."));
  }

  @Transactional
  public UserOut register(RegisterRequest p) {
    String address = email(p.email());
    if (users.existsByEmail(address))
      throw new ApiException(409, "EMAIL_EXISTS", "Email này đã được đăng ký.");
    if (p.password().getBytes(StandardCharsets.UTF_8).length > 72)
      throw new ApiException(422, "VALIDATION_ERROR", "Mật khẩu không được vượt quá 72 byte.");
    User u = new User();
    u.setFullName(name(p.fullName()));
    u.setEmail(address);
    u.setPasswordHash(passwords.encode(p.password()));
    u.setRole("USER");
    return out(users.saveAndFlush(u));
  }

  public TokenOut login(LoginRequest p) {
    Optional<User> existing = users.findByEmail(email(p.email()));
    boolean matches;
    try {
      matches =
          passwords.matches(p.password(), existing.map(User::getPasswordHash).orElse(dummyHash));
    } catch (IllegalArgumentException e) {
      matches = false;
    }
    if (existing.isEmpty() || !matches)
      throw new ApiException(401, "INVALID_CREDENTIALS", "Email hoặc mật khẩu không chính xác.");
    User u = existing.get();
    return new TokenOut(tokens.create(u.getId(), u.getRole()), "bearer", tokens.lifetime(), out(u));
  }

  @Transactional
  public UserOut update(Long id, ProfileRequest p, Set<String> present) {
    User u = current(id);
    u.setFullName(name(p.fullName()));
    if (present.contains("student_id")) u.setStudentId(nullable(p.studentId()));
    if (present.contains("school")) u.setSchool(nullable(p.school()));
    if (present.contains("contact_email")) u.setContactEmail(nullable(p.contactEmail()));
    return out(users.saveAndFlush(u));
  }
}
