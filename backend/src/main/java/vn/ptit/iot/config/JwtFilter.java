package vn.ptit.iot.config;

import com.fasterxml.jackson.databind.ObjectMapper;
import jakarta.servlet.*;
import jakarta.servlet.http.*;
import java.io.IOException;
import java.util.List;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.web.filter.OncePerRequestFilter;
import vn.ptit.iot.exception.*;
import vn.ptit.iot.service.*;

public class JwtFilter extends OncePerRequestFilter {
  private final TokenService tokens;
  private final AuthService auth;
  private final ObjectMapper mapper;

  public JwtFilter(TokenService tokens, AuthService auth, ObjectMapper mapper) {
    this.tokens = tokens;
    this.auth = auth;
    this.mapper = mapper;
  }

  @Override
  protected boolean shouldNotFilter(HttpServletRequest request) {
    String path = request.getRequestURI().substring(request.getContextPath().length());
    return !path.startsWith("/api/v1/")
        || path.equals("/api/v1/auth/register")
        || path.equals("/api/v1/auth/login");
  }

  @Override
  protected void doFilterInternal(
      HttpServletRequest req, HttpServletResponse res, FilterChain chain)
      throws ServletException, IOException {
    try {
      String header = req.getHeader("Authorization");
      if (header == null || !header.startsWith("Bearer "))
        throw new ApiException(401, "UNAUTHORIZED", "Chưa đăng nhập.");
      String raw = header.substring(7);
      Long id = Long.valueOf(tokens.verify(raw).get("sub").toString());
      auth.current(id);
      SecurityContextHolder.getContext()
          .setAuthentication(new UsernamePasswordAuthenticationToken(id, raw, List.of()));
    } catch (ApiException e) {
      res.setStatus(401);
      res.setContentType("application/json;charset=UTF-8");
      res.setHeader("WWW-Authenticate", "Bearer");
      mapper.writeValue(res.getWriter(), GlobalExceptionHandler.error(e.code, e.getMessage()));
      return;
    }
    chain.doFilter(req, res);
  }
}
