package vn.ptit.iot.entity;

import jakarta.persistence.*;
import java.time.Instant;

@Entity
@Table(name = "users")
public class User {
  @Id
  @GeneratedValue(strategy = GenerationType.IDENTITY)
  private Long id;

  public Long getId() {
    return id;
  }

  @Column(name = "full_name", nullable = false, length = 100)
  private String fullName;

  @Column(name = "email", nullable = false, length = 150, unique = true)
  private String email;

  @Column(name = "password_hash", nullable = false, length = 255)
  private String passwordHash;

  @Column(name = "role", nullable = false, length = 20)
  private String role;

  @Column(name = "student_id", nullable = true, length = 30)
  private String studentId;

  @Column(name = "school", nullable = true, length = 200)
  private String school;

  @Column(name = "contact_email", nullable = true, length = 150)
  private String contactEmail;

  @Column(name = "created_at", nullable = false)
  private Instant createdAt;

  @Column(name = "updated_at", nullable = false)
  private Instant updatedAt;

  public String getFullName() {
    return fullName;
  }

  public void setFullName(String value) {
    this.fullName = value;
  }

  public String getEmail() {
    return email;
  }

  public void setEmail(String value) {
    this.email = value;
  }

  public String getPasswordHash() {
    return passwordHash;
  }

  public void setPasswordHash(String value) {
    this.passwordHash = value;
  }

  public String getRole() {
    return role;
  }

  public void setRole(String value) {
    this.role = value;
  }

  public String getStudentId() {
    return studentId;
  }

  public void setStudentId(String value) {
    this.studentId = value;
  }

  public String getSchool() {
    return school;
  }

  public void setSchool(String value) {
    this.school = value;
  }

  public String getContactEmail() {
    return contactEmail;
  }

  public void setContactEmail(String value) {
    this.contactEmail = value;
  }

  public Instant getCreatedAt() {
    return createdAt;
  }

  public void setCreatedAt(Instant value) {
    this.createdAt = value;
  }

  public Instant getUpdatedAt() {
    return updatedAt;
  }

  public void setUpdatedAt(Instant value) {
    this.updatedAt = value;
  }

  @PrePersist
  void onCreate() {
    Instant now = Instant.now();
    if (createdAt == null) createdAt = now;
    updatedAt = now;
    if (role == null) role = "USER";
  }

  @PreUpdate
  void onUpdate() {
    updatedAt = Instant.now();
  }
}
