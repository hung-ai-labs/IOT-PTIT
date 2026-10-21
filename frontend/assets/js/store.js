// store.js — trạng thái hệ thống dùng chung giữa các trang.
//
// Từ Giai đoạn 4, dữ liệu ở đây LẤY TỪ SERVER chứ không còn tự bịa:
//   • devices        ← GET /api/v1/devices
//   • esp32Online / mqttConnected ← GET /system/status rồi nhận WebSocket
// Các trang đăng ký `subscribe()` để vẽ lại khi trạng thái đổi.

import { SHOW_IOT_DATA } from './config.js';
import { getDevices, getSystemStatus } from './api.js';
import { connectWebSocket, onConnectionState, onMessage } from './ws.js';

const listeners = new Set();

let state = {
  devices: [],
  esp32Online: false,
  mqttConnected: false,
  deviceId: null,
  systemStatus: null,
  loaded: false,
  deviceError: null,
};

let statusPollingTimer = null;
let statusSyncStarted = false;

export const getState = () => state;

export function setState(patch) {
  state = { ...state, ...patch };
  listeners.forEach((listener) => listener(state));
}

export function subscribe(listener) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

/** Có được phép gửi lệnh không (F13). */
export const canControl = () => state.esp32Online && state.mqttConnected;

/** Thiết bị theo mã đối tượng ('red' | 'green' | 'yellow'). */
export const getDevice = (target) => state.devices.find((device) => device.target === target);

/** Đồng bộ trạng thái với server. Gọi lúc mở trang và định kỳ. */
export async function refreshStatus() {
  try {
    if (!SHOW_IOT_DATA) {
      setState({ devices: await getDevices(), esp32Online: false, mqttConnected: false, systemStatus: null, loaded: true, deviceError: null });
      return state;
    }
    const [devices, systemStatus] = await Promise.all([getDevices(), getSystemStatus()]);
    setState({
      devices,
      deviceError: null,
      mqttConnected: systemStatus.mqtt.status === 'connected',
      esp32Online: systemStatus.esp.status === 'online',
      deviceId: systemStatus.esp.device_id,
      systemStatus,
      loaded: true,
    });
  } catch (error) {
    // Không tới được server: coi như mất kết nối, giữ nguyên danh sách thiết bị cũ.
    setState({ esp32Online: false, mqttConnected: false, loaded: true, deviceError: error.message });
  }
  return state;
}

onMessage('system_status', (systemStatus) => {
  const online = systemStatus.esp.status === 'online';
  setState({
    systemStatus,
    mqttConnected: systemStatus.mqtt.status === 'connected',
    esp32Online: online,
    deviceId: systemStatus.esp.device_id,
    devices: state.devices.map((device) => ({
      ...device,
      connection: device.previewOnly ? null : device.device_id === systemStatus.esp.device_id && online ? 'online' : 'offline',
      last_seen: systemStatus.esp.last_seen,
    })),
    loaded: true,
  });
});

onMessage('device_state', (event) => {
  if (event.result !== 'Success') return;
  setState({
    devices: state.devices.map((device) => (
      !device.previewOnly && device.device_id === event.device_id && device.target === event.target
        ? { ...device, state: event.state }
        : device
    )),
  });
});

function updateFallbackPolling({ fallbackActive }) {
  if (fallbackActive && statusPollingTimer === null) {
    refreshStatus();
    statusPollingTimer = window.setInterval(refreshStatus, 10_000);
  } else if (!fallbackActive && statusPollingTimer !== null) {
    window.clearInterval(statusPollingTimer);
    statusPollingTimer = null;
  }
}

/** Tải trạng thái ban đầu, sau đó chỉ poll nếu WebSocket lỗi ba lần liên tiếp. */
export function startStatusSync() {
  if (statusSyncStarted) return;
  statusSyncStarted = true;
  refreshStatus();
  if (!SHOW_IOT_DATA) return;
  onConnectionState(updateFallbackPolling);
  connectWebSocket();
}
