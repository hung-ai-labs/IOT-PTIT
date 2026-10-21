package vn.ptit.iot.config;

import java.util.*;

public final class DeviceRegistry {
  public record DeviceDefinition(String name, String gpio, String icon) {}

  public static final Map<String, DeviceDefinition> DEVICES;

  static {
    LinkedHashMap<String, DeviceDefinition> map = new LinkedHashMap<>();
    map.put("red", new DeviceDefinition("Đèn đỏ", "GPIO 25", "💡"));
    map.put("green", new DeviceDefinition("Đèn xanh", "GPIO 26", "💡"));
    map.put("yellow", new DeviceDefinition("Đèn vàng", "GPIO 27", "💡"));
    DEVICES = Collections.unmodifiableMap(map);
  }

  private DeviceRegistry() {}

  public static String label(String target) {
    return DEVICES.containsKey(target) ? DEVICES.get(target).name() : target;
  }
}
