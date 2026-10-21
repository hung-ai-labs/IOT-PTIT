package vn.ptit.iot.controller;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import jakarta.validation.*;
import java.util.*;
import org.springframework.http.HttpStatus;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.*;
import vn.ptit.iot.dto.ApiDtos.*;
import vn.ptit.iot.exception.ApiException;
import vn.ptit.iot.service.*;

@RestController
@RequestMapping("/api/v1/auth")
public class AuthController {
  private final AuthService auth;
  private final TokenService tokens;
  private final ObjectMapper mapper;
  private final Validator validator;

  public AuthController(
      AuthService auth, TokenService tokens, ObjectMapper mapper, Validator validator) {
    this.auth = auth;
    this.tokens = tokens;
    this.mapper = mapper;
    this.validator = validator;
  }

  @PostMapping("/register")
  @ResponseStatus(HttpStatus.CREATED)
  public UserOut register(@Valid @RequestBody RegisterRequest p) {
    return auth.register(p);
  }

  @PostMapping("/login")
  public TokenOut login(@Valid @RequestBody LoginRequest p) {
    return auth.login(p);
  }

  @GetMapping("/me")
  public UserOut me(Authentication a) {
    return auth.out(auth.current((Long) a.getPrincipal()));
  }

  @io.swagger.v3.oas.annotations.Operation(
      requestBody =
          @io.swagger.v3.oas.annotations.parameters.RequestBody(
              content =
                  @io.swagger.v3.oas.annotations.media.Content(
                      schema =
                          @io.swagger.v3.oas.annotations.media.Schema(
                              implementation = ProfileRequest.class))))
  @PatchMapping("/me")
  public UserOut update(Authentication a, @RequestBody JsonNode node) throws Exception {
    Set<String> fields = new HashSet<>();
    node.fieldNames().forEachRemaining(fields::add);
    if (!node.isObject()
        || !Set.of("full_name", "student_id", "school", "contact_email").containsAll(fields))
      throw new ApiException(422, "VALIDATION_ERROR", "Trường cập nhật không hợp lệ.");
    ProfileRequest p = mapper.treeToValue(node, ProfileRequest.class);
    if (!validator.validate(p).isEmpty())
      throw new ApiException(422, "VALIDATION_ERROR", "Thông tin cá nhân không hợp lệ.");
    return auth.update((Long) a.getPrincipal(), p, fields);
  }

  @PostMapping("/logout")
  @ResponseStatus(HttpStatus.NO_CONTENT)
  public void logout(Authentication a) {
    tokens.revoke(a.getCredentials().toString());
  }
}
