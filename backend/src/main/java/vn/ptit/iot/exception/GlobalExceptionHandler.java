package vn.ptit.iot.exception;

import jakarta.validation.ConstraintViolationException;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.http.ResponseEntity;
import org.springframework.http.converter.HttpMessageNotReadableException;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.method.annotation.MethodArgumentTypeMismatchException;
import vn.ptit.iot.dto.ApiDtos.*;

@RestControllerAdvice
public class GlobalExceptionHandler {
  public static ErrorOut error(String code, String message) {
    return new ErrorOut(new ErrorDetail(code, message));
  }

  @ExceptionHandler(ApiException.class)
  public ResponseEntity<ErrorOut> api(ApiException e) {
    return ResponseEntity.status(e.status).body(error(e.code, e.getMessage()));
  }

  @ExceptionHandler({
    MethodArgumentNotValidException.class,
    HttpMessageNotReadableException.class,
    MethodArgumentTypeMismatchException.class,
    com.fasterxml.jackson.core.JsonProcessingException.class,
    ConstraintViolationException.class,
    IllegalArgumentException.class
  })
  public ResponseEntity<ErrorOut> invalid(Exception e) {
    return ResponseEntity.unprocessableEntity()
        .body(
            error(
                "VALIDATION_ERROR",
                "Dữ liệu không hợp lệ. Kiểm tra giá trị, kiểu dữ liệu và độ dài các trường."));
  }

  @ExceptionHandler(DataIntegrityViolationException.class)
  public ResponseEntity<ErrorOut> conflict(Exception e) {
    return ResponseEntity.status(409)
        .body(error("DATA_CONFLICT", "Dữ liệu bị trùng hoặc không thoả mãn ràng buộc."));
  }
}
