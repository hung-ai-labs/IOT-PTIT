// api.js — điểm gọi dữ liệu duy nhất của frontend.
//
// Xác thực, cảm biến, thiết bị, lịch sử và trạng thái hệ thống đã dùng FastAPI thật.

import { SHOW_IOT_DATA } from './config.js';
import { isFallbackActive, waitForMessage } from './ws.js';

/** Bỏ các tham số rỗng rồi tạo query string đã URL-encode. */
function query(params) {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== '' && value !== 'all') {
      search.set(key, value);
    }
  }
  const text = search.toString();
  return text ? `?${text}` : '';
}

const BASE_URL = '/api/v1';
const TOKEN_KEY = 'smart_iot_token';
const USER_KEY = 'smart_iot_user';

/* ─── Token & người dùng hiện tại ────────────────────────── */
export const getToken = () => localStorage.getItem(TOKEN_KEY);
export const setToken = (token) => localStorage.setItem(TOKEN_KEY, token);
export const clearToken = () => localStorage.removeItem(TOKEN_KEY);

export function setCurrentUser(user) {
  localStorage.setItem(USER_KEY, JSON.stringify(user));
}

export function getCurrentUser() {
  try {
    return JSON.parse(localStorage.getItem(USER_KEY)) ?? null;
  } catch {
    return null;
  }
}

export const clearCurrentUser = () => localStorage.removeItem(USER_KEY);

/** Chữ cái đầu của họ và tên, dùng cho avatar. */
export function initialsOf(fullName = '') {
  const parts = fullName.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return '?';
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts.at(-1)[0]).toUpperCase();
}

/* ─── fetch wrapper ──────────────────────────────────────── */
/**
 * Gọi API, tự gắn Bearer token và chuyển 401 về trang đăng nhập.
 * @param {object} options.skipAuthRedirect bỏ qua chuyển hướng (dùng ở trang đăng nhập)
 */
async function request(path, { method = 'GET', body, skipAuthRedirect = false, timeoutMs = 15000 } = {}) {
  const headers = { 'Content-Type': 'application/json' };
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;

  let response;
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);
  try {
    response = await fetch(`${BASE_URL}${path}`, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
      signal: controller.signal,
    });
  } catch {
    if (controller.signal.aborted) {
      throw new Error('Máy chủ phản hồi quá lâu. Kiểm tra Docker Desktop và kết nối PostgreSQL, rồi bấm Thử lại.');
    }
    throw new Error('Không kết nối được tới máy chủ. Kiểm tra backend đã chạy chưa.');
  } finally {
    clearTimeout(timeout);
  }

  if (response.status === 401 && !skipAuthRedirect) {
    clearToken();
    clearCurrentUser();
    window.location.replace('login.html');
    throw new Error('Phiên đăng nhập đã hết hạn.');
  }

  if (!response.ok) {
    const data = await response.json().catch(() => null);
    throw new Error(data?.detail?.message || `Lỗi ${response.status}`);
  }

  return response.status === 204 ? null : response.json();
}

const delay = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

/* ─── Xác thực (API thật) ────────────────────────────────── */
export async function login(email, password) {
  const result = await request('/auth/login', {
    method: 'POST',
    body: { email, password },
    skipAuthRedirect: true,
  });
  setToken(result.access_token);
  setCurrentUser(result.user);
  return result;
}

export async function register({ fullName, email, password }) {
  return request('/auth/register', {
    method: 'POST',
    body: { full_name: fullName, email, password },
    skipAuthRedirect: true,
  });
}

export async function logout() {
  // Thu hồi token phía server; kể cả khi lỗi vẫn xoá phía client.
  await request('/auth/logout', { method: 'POST', skipAuthRedirect: true }).catch(() => {});
  clearToken();
  clearCurrentUser();
}

export async function getProfile() {
  return request('/auth/me', { timeoutMs: 8000 });
}

export async function updateProfile(payload) {
  const user = await request('/auth/me', { method: 'PATCH', body: payload });
  setCurrentUser(user);
  window.dispatchEvent(new CustomEvent('profile-updated', { detail: user }));
  return user;
}

/* ─── Cảm biến ───────────────────────────────────────────── */
/** Giá trị mới nhất mỗi loại → `{temp, humidity, light}` cho 3 thẻ Dashboard. */
export async function getLatestSensor(deviceId) {
  if (!SHOW_IOT_DATA) return { deviceId: null, temp: null, humidity: null, light: null, updatedAt: null };
  const data = await request(`/sensors/latest${query({ device_id: deviceId })}`);
  return {
    deviceId: data.device_id,
    temp: data.temperature?.value ?? null,
    humidity: data.humidity?.value ?? null,
    light: data.light?.value ?? null,
    updatedAt: data.temperature?.timestamp ?? data.humidity?.timestamp ?? data.light?.timestamp ?? null,
  };
}

/** Dữ liệu đã gom nhóm cho biểu đồ. */
export async function getSensorSeries({ deviceId, bucket = '1m', points = 30 } = {}) {
  if (!SHOW_IOT_DATA) return [];
  return request(`/sensors/series${query({ device_id: deviceId, bucket, points })}`);
}

/**
 * Tra cứu bảng `data_sensor` — mỗi bản ghi là MỘT phép đo của MỘT loại cảm biến
 * (SRS §2.6). Trả về `{items, page, size, total, totalPages}`.
 */
export async function getSensorRecords({
  deviceId, sensorType, q, field, from, to, page = 1, size = 20, sort = 'timestamp:desc',
} = {}) {
  if (!SHOW_IOT_DATA) return { items: [], page: 1, size, total: 0, totalPages: 1 };
  const data = await request(
    `/sensors${query({ device_id: deviceId, sensor_type: sensorType, q, field, from, to, page, size, sort })}`
  );
  return {
    items: data.items,
    page: data.page,
    size: data.size,
    total: data.total,
    totalPages: data.total_pages,
  };
}

let deviceOptionsPromise;
const inlineDeviceOptions = document.getElementById('deviceOptionsTemplate')?.content.querySelector('select')?.innerHTML;

/** Shared HTML options drive the device cards and history filter. */
export function getDeviceOptions() {
  if (!deviceOptionsPromise) {
    deviceOptionsPromise = loadDeviceOptions().catch((error) => {
      deviceOptionsPromise = null;
      throw error;
    });
  }
  return deviceOptionsPromise;
}

async function loadDeviceOptions() {
  let markup = inlineDeviceOptions;
  if (!markup) {
    const response = await fetch(new URL('../../index.html', import.meta.url), { cache: 'no-cache' });
    if (!response.ok) throw new Error('Không tải được danh sách đèn.');
    const source = new DOMParser().parseFromString(await response.text(), 'text/html');
    markup = source.getElementById('deviceOptionsTemplate')?.content.querySelector('select')?.innerHTML;
  }
  if (!markup) throw new Error('Thiếu danh sách đèn trong index.html.');
  const select = document.createElement('select');
  select.innerHTML = markup;
  const seen = new Set();
  return [...select.options].map((option) => {
    const target = option.value.trim();
    if (seen.has(target)) throw new Error(`Mã đèn "${target}" bị trùng. Mỗi đèn cần một value riêng.`);
    seen.add(target);
    return { target, name: option.textContent.trim() };
  });
}

/* ─── Thiết bị ───────────────────────────────────────────── */
/** Ba thiết bị chấp hành kèm trạng thái ON/OFF và kết nối. */
export async function getDevices(deviceId) {
  const options = await getDeviceOptions();
  const serverDevices = SHOW_IOT_DATA
    ? await request(`/devices${query({ device_id: deviceId })}`)
    : [];
  return options.filter((option) => option.target).map((option) => {
    const registered = serverDevices.find((device) => device.target === option.target);
    const device = registered
      ? { ...registered, name: option.name, previewOnly: false }
      : {
          target: option.target, name: option.name, icon: '💡',
          device_id: 'Chỉ hiển thị', gpio: '—', state: null, connection: null,
          last_command: null, last_seen: null, previewOnly: true,
        };
    return SHOW_IOT_DATA ? device : {
      ...device, state: null, connection: null, last_command: null, last_seen: null,
    };
  });
}

/** Chi tiết một đèn và thông tin ESP chứa đèn đó (F10). */
export async function getDeviceDetail(deviceId, target) {
  const device = await request(`/devices/${encodeURIComponent(deviceId)}/targets/${encodeURIComponent(target)}`);
  return SHOW_IOT_DATA ? device : {
    ...device, state: null, connection: null, ip: null, rssi: null, uptime: null,
    last_command: null, last_seen: null,
  };
}

/**
 * Gửi lệnh điều khiển. Server trả 202 ngay với `result = "Pending"`;
 * kết quả thật lấy bằng `waitForAction()`.
 */
export async function sendDeviceAction(deviceId, target, action) {
  if (!SHOW_IOT_DATA) throw new Error('Chưa bật dữ liệu IoT để gửi lệnh điều khiển.');
  return request(`/devices/${encodeURIComponent(deviceId)}/actions`, {
    method: 'POST',
    body: { target, action },
  });
}

/** Trạng thái hiện tại của một lệnh. */
export async function getDeviceAction(actionId) {
  return request(`/device-actions/${actionId}`);
}

/**
 * Chờ tới khi lệnh có kết quả cuối cùng (Success | Failed | Timeout).
 *
 * WebSocket là đường chính; polling 0,5 giây chỉ chạy khi kết nối đã lỗi 3 lần.
 * `onTick` được gọi khi có trạng thái mới để giao diện cập nhật tiến trình.
 */
export async function waitForAction(actionId, { timeoutSeconds = 5, interval = 500, onTick } = {}) {
  const timeoutMs = (timeoutSeconds + 2) * 1000;

  if (!isFallbackActive()) {
    try {
      const event = await waitForMessage(
        'device_state',
        (data) => Number(data.action_id) === Number(actionId),
        timeoutMs,
      );
      onTick?.(event);
      return {
        id: event.action_id,
        ...event,
      };
    } catch {
      if (!isFallbackActive()) {
        return { id: actionId, result: 'Timeout', error_msg: 'Hết thời gian chờ phản hồi.' };
      }
    }
  }

  // Cộng thêm 2 giây so với ngưỡng của server để chắc chắn thấy được kết quả Timeout.
  const deadline = Date.now() + timeoutMs;

  while (Date.now() < deadline) {
    await delay(interval);
    const action = await getDeviceAction(actionId);
    onTick?.(action);
    if (action.result !== 'Pending') return action;
  }

  return { id: actionId, result: 'Timeout', error_msg: 'Hết thời gian chờ phản hồi.' };
}

/* ─── Lịch sử thao tác ───────────────────────────────────── */
export async function getDeviceActions({
  deviceId, target, action, result, q, from, to, page = 1, size = 20, sort = 'timestamp:desc',
} = {}) {
  if (!SHOW_IOT_DATA) return { items: [], page: 1, size, total: 0, totalPages: 1 };
  const data = await request(
    `/device-actions${query({ device_id: deviceId, target, action, result, q, from, to, page, size, sort })}`
  );
  return {
    items: data.items,
    page: data.page,
    size: data.size,
    total: data.total,
    totalPages: data.total_pages,
  };
}

/* ─── Trạng thái hệ thống (Giai đoạn 5) ──────────────────── */
export async function getSystemStatus() {
  return request('/system/status');
}
