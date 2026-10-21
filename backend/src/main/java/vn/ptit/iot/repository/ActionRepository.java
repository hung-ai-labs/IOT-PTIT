package vn.ptit.iot.repository;

import java.time.Instant;
import java.util.*;
import org.springframework.data.jpa.repository.*;
import org.springframework.data.repository.query.Param;
import org.springframework.transaction.annotation.Transactional;
import vn.ptit.iot.entity.DeviceAction;

public interface ActionRepository
    extends JpaRepository<DeviceAction, Long>, JpaSpecificationExecutor<DeviceAction> {
  Optional<DeviceAction> findByCmdId(UUID cmdId);

  Optional<DeviceAction> findFirstByDeviceIdAndTargetOrderByTimestampDescIdDesc(
      String deviceId, String target);

  boolean existsByDeviceIdAndTargetAndResult(String deviceId, String target, String result);

  List<DeviceAction> findByResult(String result);

  @Modifying
  @Transactional
  @Query(
      "update DeviceAction a set a.result=:result, a.errorMsg=:error, a.respondedAt=:at where a.id=:id and a.result='Pending'")
  int complete(
      @Param("id") Long id,
      @Param("result") String result,
      @Param("error") String error,
      @Param("at") Instant at);
}
