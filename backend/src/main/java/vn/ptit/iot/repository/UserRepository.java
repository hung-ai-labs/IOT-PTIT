package vn.ptit.iot.repository;

import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;
import vn.ptit.iot.entity.User;

public interface UserRepository extends JpaRepository<User, Long> {
  Optional<User> findByEmail(String email);

  boolean existsByEmail(String email);
}
