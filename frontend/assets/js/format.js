// format.js — định dạng ngày giờ, số, đơn vị

export const pad2 = (n) => String(n).padStart(2, '0');

/** 22:15:32 */
export function formatTime(date = new Date()) {
  const d = date instanceof Date ? date : new Date(date);
  return `${pad2(d.getHours())}:${pad2(d.getMinutes())}:${pad2(d.getSeconds())}`;
}

/** 22:15 */
export function formatHourMinute(date = new Date()) {
  const d = date instanceof Date ? date : new Date(date);
  return `${pad2(d.getHours())}:${pad2(d.getMinutes())}`;
}

/** 18/08/2026 22:15:32 */
export function formatDateTime(date = new Date()) {
  const d = date instanceof Date ? date : new Date(date);
  return `${pad2(d.getDate())}/${pad2(d.getMonth() + 1)}/${d.getFullYear()} ${formatTime(d)}`;
}

/** 2026-08-18 — dùng cho <input type="date"> */
export function toDateInputValue(date = new Date()) {
  const d = date instanceof Date ? date : new Date(date);
  return `${d.getFullYear()}-${pad2(d.getMonth() + 1)}-${pad2(d.getDate())}`;
}

/** "vừa xong" | "12 giây trước" */
export function formatAgo(seconds) {
  if (seconds <= 0) return 'vừa xong';
  if (seconds < 60) return `${seconds} giây trước`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes} phút trước`;
  return `${Math.floor(minutes / 60)} giờ trước`;
}

export const formatTemp     = (v) => `${Number(v).toFixed(1)} °C`;
export const formatHumidity = (v) => `${Math.round(v)} %`;
export const formatLight    = (v) => `${Math.round(v)} lux`;

/** Chặn XSS khi ghép chuỗi HTML */
export function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>"']/g, (c) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
  })[c]);
}
