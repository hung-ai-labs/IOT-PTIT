package vn.ptit.iot.service;

import java.time.Instant;
import java.util.*;
import org.springframework.data.domain.Page;
import org.springframework.data.jpa.domain.Specification;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import vn.ptit.iot.config.DeviceRegistry;
import vn.ptit.iot.dto.ApiDtos.*;
import vn.ptit.iot.entity.DeviceAction;
import vn.ptit.iot.exception.ApiException;
import vn.ptit.iot.repository.*;

@Service
public class ActionService {
  private final ActionRepository actions;
  private final UserRepository users;

  public ActionService(ActionRepository actions, UserRepository users) {
    this.actions = actions;
    this.users = users;
  }

  public ActionOut out(DeviceAction a) {
    IssuerOut issuer =
        a.getIssuedBy() == null
            ? null
            : users
                .findById(a.getIssuedBy())
                .map(u -> new IssuerOut(u.getId(), u.getFullName()))
                .orElse(null);
    return new ActionOut(
        a.getId(),
        a.getDeviceId(),
        a.getTarget(),
        DeviceRegistry.label(a.getTarget()),
        a.getAction(),
        issuer,
        a.getResult(),
        a.getTimestamp(),
        a.getRespondedAt(),
        a.getErrorMsg());
  }

  public ActionOut get(Long id) {
    return out(
        actions
            .findById(id)
            .orElseThrow(
                () ->
                    new ApiException(404, "ACTION_NOT_FOUND", "Không tìm thấy lệnh #" + id + ".")));
  }

  @Transactional
  public DeviceAction create(String device, String target, String action, Long issuer) {
    DeviceAction row = new DeviceAction();
    row.setDeviceId(device);
    row.setTarget(target);
    row.setAction(action);
    row.setIssuedBy(issuer);
    row.setResult("Pending");
    row.setCmdId(UUID.randomUUID());
    return actions.saveAndFlush(row);
  }

  public boolean complete(Long id, String result, String error) {
    return actions.complete(id, result, error, Instant.now()) == 1;
  }

  /** Search only the timestamp formatted in Vietnam time. */
  private Specification<DeviceAction> search(String q) {
    String needle = QueryService.keyword(q);
    if (needle == null) return null;
    return (root, query, cb) -> QueryService.like(cb, root.get("searchTime"), needle);
  }

  public PageOut<ActionOut> records(
      String device,
      String target,
      String action,
      String result,
      String q,
      Instant from,
      Instant to,
      int page,
      int size,
      String sort) {
    QueryService.choice(target, DeviceRegistry.DEVICES.keySet());
    QueryService.choice(action, Set.of("ON", "OFF"));
    QueryService.choice(result, Set.of("Pending", "Success", "Failed", "Timeout"));
    Page<DeviceAction> rows =
        actions.findAll(
            QueryService.<DeviceAction>filters(
                    QueryService.values(
                        "deviceId", device, "target", target, "action", action, "result", result),
                    from,
                    to)
                .and(search(q)),
            QueryService.page(
                page,
                size,
                sort,
                Set.of("id", "deviceId", "target", "action", "result", "timestamp")));
    return new PageOut<>(
        rows.map(this::out).getContent(),
        page,
        size,
        rows.getTotalElements(),
        Math.max(1, rows.getTotalPages()));
  }
}
