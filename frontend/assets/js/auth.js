// auth.js — chặn truy cập trang khi chưa đăng nhập

import { getToken, clearToken, clearCurrentUser, logout as apiLogout } from './api.js';

export const isAuthenticated = () => Boolean(getToken());

export async function signOut() {
  await apiLogout();
  sessionStorage.removeItem('smart_iot_state');
}

/** Xoá dấu vết đăng nhập mà không gọi API (dùng khi token đã hỏng). */
export function clearAuthentication() {
  clearToken();
  clearCurrentUser();
  sessionStorage.removeItem('smart_iot_state');
}

/** Gọi ở đầu mỗi trang cần đăng nhập. Trả về false nếu đã chuyển hướng. */
export function requireAuth() {
  if (isAuthenticated()) return true;
  window.location.replace('login.html');
  return false;
}

/** Gọi ở trang đăng nhập: nếu đã đăng nhập thì vào thẳng dashboard. */
export function redirectIfAuthenticated() {
  if (isAuthenticated()) {
    window.location.replace('index.html');
    return true;
  }
  return false;
}
