package vn.ptit.iot.config;

import io.swagger.v3.oas.models.Components;
import io.swagger.v3.oas.models.OpenAPI;
import io.swagger.v3.oas.models.info.Info;
import io.swagger.v3.oas.models.security.SecurityRequirement;
import io.swagger.v3.oas.models.security.SecurityScheme;
import org.springdoc.core.customizers.OpenApiCustomizer;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
public class OpenApiConfig {
  @Bean
  OpenAPI documentation() {
    return new OpenAPI()
        .info(new Info().title("Smart IoT — PTIT").version("1.0.0"))
        .components(
            new Components()
                .addSecuritySchemes(
                    "bearerAuth",
                    new SecurityScheme()
                        .type(SecurityScheme.Type.HTTP)
                        .scheme("bearer")
                        .bearerFormat("JWT")));
  }

  @Bean
  OpenApiCustomizer securedOperations() {
    return api ->
        api.getPaths()
            .forEach(
                (path, item) -> {
                  if (path.startsWith("/api/v1/")
                      && !path.equals("/api/v1/auth/login")
                      && !path.equals("/api/v1/auth/register"))
                    item.readOperations()
                        .forEach(
                            operation ->
                                operation.addSecurityItem(
                                    new SecurityRequirement().addList("bearerAuth")));
                });
  }
}
