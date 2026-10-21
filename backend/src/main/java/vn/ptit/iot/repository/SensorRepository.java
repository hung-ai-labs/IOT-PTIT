package vn.ptit.iot.repository;

import java.util.Optional;
import org.springframework.data.jpa.repository.*;
import vn.ptit.iot.entity.SensorReading;

public interface SensorRepository
    extends JpaRepository<SensorReading, Long>, JpaSpecificationExecutor<SensorReading> {
  Optional<SensorReading> findFirstBySensorTypeOrderByTimestampDescIdDesc(String type);

  Optional<SensorReading> findFirstBySensorTypeAndDeviceIdOrderByTimestampDescIdDesc(
      String type, String deviceId);
}
