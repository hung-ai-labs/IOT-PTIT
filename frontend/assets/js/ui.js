// ui.js — toast, modal, drawer và các mảnh HTML dùng lại

import { escapeHtml } from './format.js';
import { initialsOf } from './api.js';

/* ─── Avatar ─────────────────────────────────────────────── */
/** Ảnh đại diện. Nếu ảnh không tải được thì tự lùi về chữ cái đầu bên dưới. */
export function avatar(fullName, size = 'md') {
  const name = escapeHtml(fullName ?? '');
  return `<span class="avatar avatar--${size}">` +
    `<span class="avatar__initials">${escapeHtml(initialsOf(fullName))}</span>` +
    `<img class="avatar__img" src="assets/img/avatar.jpg" alt="Ảnh đại diện của ${name}"` +
    ` onerror="this.remove()">` +
    `</span>`;
}

/* ─── Toast ──────────────────────────────────────────────── */
const TOAST_ICONS = { success: '✓', error: '✕', info: 'ℹ', warning: '⚠' };
let toastStack = null;

function ensureToastStack() {
  if (toastStack && document.body.contains(toastStack)) return toastStack;
  toastStack = document.createElement('div');
  toastStack.className = 'toast-stack';
  toastStack.setAttribute('role', 'status');
  toastStack.setAttribute('aria-live', 'polite');
  document.body.appendChild(toastStack);
  return toastStack;
}

export function toast(message, type = 'info', timeout = 4000) {
  const stack = ensureToastStack();
  const el = document.createElement('div');
  el.className = `toast toast--${type}`;
  el.innerHTML =
    `<span class="toast__icon">${TOAST_ICONS[type] ?? 'ℹ'}</span>` +
    `<span class="toast__msg">${escapeHtml(message)}</span>` +
    `<button class="toast__close" type="button" aria-label="Đóng thông báo">×</button>`;
  el.querySelector('.toast__close').addEventListener('click', () => el.remove());
  stack.appendChild(el);
  if (timeout) setTimeout(() => el.remove(), timeout);
  return el;
}

/* ─── Lớp phủ (modal / drawer) ───────────────────────────── */
let openLayer = null;

/**
 * Mở một lớp phủ. `render` trả về chuỗi HTML của panel.
 * Trả về đối tượng { root, close } để trang chủ động cập nhật/đóng.
 */
export function openLayerWith(html, { panelClass = 'modal', strong = false, onClose } = {}) {
  closeLayer();

  const root = document.createElement('div');
  root.innerHTML =
    `<div class="overlay${strong ? ' overlay--strong' : ''}" data-close></div>` +
    `<div class="${panelClass}" role="dialog" aria-modal="true">${html}</div>`;
  document.body.appendChild(root);

  const close = () => {
    root.remove();
    document.removeEventListener('keydown', onKey);
    if (openLayer === layer) openLayer = null;
    onClose?.();
  };
  const onKey = (e) => { if (e.key === 'Escape') close(); };
  document.addEventListener('keydown', onKey);
  root.querySelector('[data-close]').addEventListener('click', close);
  root.addEventListener('click', (e) => { if (e.target.closest('[data-dismiss]')) close(); });

  const panel = root.querySelector(`.${panelClass.split(' ')[0]}`);
  panel.querySelector('button, [href], input, select')?.focus();

  const layer = { root, panel, close };
  openLayer = layer;
  return layer;
}

export function closeLayer() {
  openLayer?.close();
}

/* ─── Mảnh HTML dùng lại ─────────────────────────────────── */
export const statusDot = (isUp, pulse = false) =>
  `<span class="status-dot${isUp ? ' is-up' : ''}${pulse ? ' status-dot--pulse' : ''}"></span>`;

export const badge = (type, text) =>
  `<span class="badge badge--${type}">${escapeHtml(text)}</span>`;

export const mono = (text) =>
  `<span class="mono" style="font-size:var(--text-sm)">${escapeHtml(text)}</span>`;

/** Công tắc ON/OFF kèm nhãn. `index` dùng để nhận diện khi bắt sự kiện. */
export function switchControl({ on, disabled = false, loading = false, index = 0, label = true, unknown = false }) {
  const cls = ['switch', loading ? 'is-loading' : ''].filter(Boolean).join(' ');
  const button =
    `<button type="button" class="${cls}" role="switch" aria-checked="${on}" ` +
    `data-switch="${index}" ${disabled ? 'disabled' : ''} title="${unknown ? 'Chưa hiển thị trạng thái' : on ? 'ON' : 'OFF'}">` +
    `<span class="switch__knob"></span><span class="switch__spinner"></span></button>`;
  if (!label) return button;
  return (
    `<div class="switch-group">${button}` +
    `<span class="switch-group__label${on ? ' is-on' : ''}">${unknown ? '—' : on ? 'ON' : 'OFF'}</span></div>`
  );
}

/** Trạng thái rỗng của bảng/danh sách */
export const emptyState = (icon, title, hint) =>
  `<div class="empty-state"><div class="empty-state__icon">${icon}</div>` +
  `<div class="empty-state__title">${escapeHtml(title)}</div>` +
  `<div class="empty-state__hint">${escapeHtml(hint)}</div></div>`;

/** Hàng "nhãn — giá trị" trong modal/drawer */
export const detailRow = (label, valueHtml, { mono: isMono = false, size = '' } = {}) =>
  `<div class="detail-row${size ? ` detail-row--${size}` : ''}">` +
  `<span class="detail-row__label">${escapeHtml(label)}</span>` +
  `<span class="detail-row__value${isMono ? ' mono' : ''}">${valueHtml}</span></div>`;

/** Thanh phân trang. Bắt sự kiện qua [data-page]. */
export function pagination({ page, perPage, total }) {
  const totalPages = Math.max(1, Math.ceil(total / perPage));
  const from = total === 0 ? 0 : (page - 1) * perPage + 1;
  const to = Math.min(page * perPage, total);
  const shown = Math.min(5, totalPages);

  const numbers = Array.from({ length: shown }, (_, i) => i + 1)
    .map((p) => `<button type="button" class="page-btn${p === page ? ' is-active' : ''}" data-page="${p}">${p}</button>`)
    .join('');

  return (
    `<div class="pagination">` +
    `<span class="pagination__info">Hiển thị ${from}–${to} trong ${total} bản ghi</span>` +
    `<div class="pagination__pages">` +
    `<button type="button" class="page-btn" data-page="${page - 1}" ${page === 1 ? 'disabled' : ''} aria-label="Trang trước">‹</button>` +
    numbers +
    (totalPages > 5 ? `<span class="pagination__ellipsis">...</span>` : '') +
    `<button type="button" class="page-btn" data-page="${page + 1}" ${page >= totalPages ? 'disabled' : ''} aria-label="Trang sau">›</button>` +
    `</div></div>`
  );
}

/** Gắn handler cho mọi nút [data-page] bên trong `container`. */
export function bindPagination(container, totalPages, onChange) {
  container.querySelectorAll('[data-page]').forEach((btn) => {
    btn.addEventListener('click', () => {
      const next = Number(btn.dataset.page);
      if (next >= 1 && next <= totalPages) onChange(next);
    });
  });
}
