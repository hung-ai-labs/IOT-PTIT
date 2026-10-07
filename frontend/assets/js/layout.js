// layout.js — dựng khung ứng dụng (sidebar + header) cho mọi trang.
// Gọi initLayout('<pageId>') ở đầu file JS của từng trang.

import { SHOW_IOT_DATA } from './config.js';
import { icons } from './icons.js';
import { formatTime, escapeHtml } from './format.js';
import { statusDot, avatar } from './ui.js';
import { getState, subscribe, startStatusSync } from './store.js';
import { signOut } from './auth.js';
import { getCurrentUser } from './api.js';

// Người dùng đăng nhập, đọc từ localStorage (đã lưu khi login thành công).
let currentUser = getCurrentUser() ?? { full_name: 'Người dùng', role: 'USER' };

const NAV = [
  { id: 'dashboard', label: 'Tổng quan',           href: 'index.html',    icon: 'dashboard' },
  { id: 'sensors',   label: 'Dữ liệu cảm biến',    href: 'sensors.html',  icon: 'activity' },
  { id: 'devices',   label: 'Điều khiển thiết bị', href: 'devices.html',  icon: 'power' },
  { id: 'history',   label: 'Lịch sử thao tác',    href: 'history.html',  icon: 'history' },
  { id: 'profile',   label: 'Thông tin cá nhân',  href: 'profile.html',  icon: 'user' },
];

const PAGE_META = {
  dashboard: { title: 'Tổng quan',           subtitle: 'Giám sát môi trường và điều khiển thiết bị IoT' },
  sensors:   { title: 'Dữ liệu cảm biến',    subtitle: 'Theo dõi các dữ liệu được gửi từ thiết bị IoT' },
  devices:   { title: 'Điều khiển thiết bị', subtitle: 'Quản lý trạng thái các thiết bị được kết nối với ESP32' },
  history:   { title: 'Lịch sử thao tác',    subtitle: 'Theo dõi các lệnh điều khiển thiết bị' },
  profile:   { title: 'Thông tin cá nhân',   subtitle: 'Quản lý và cập nhật hồ sơ của bạn' },
};

function sidebarHtml(pageId) {
  const items = NAV.map((item) =>
    `<a class="nav-item${item.id === pageId ? ' is-active' : ''}" href="${item.href}"` +
    `${item.id === pageId ? ' aria-current="page"' : ''}>` +
    `${icons[item.icon]()}<span>${item.label}</span></a>`
  ).join('');

  return `
    <aside class="sidebar" id="sidebar">
      <div class="sidebar__brand">
        <div class="sidebar__logo">${icons.iot()}</div>
        <div>
          <div class="sidebar__title">Smart IoT</div>
          <div class="sidebar__subtitle">Monitoring &amp; Control</div>
        </div>
      </div>

      <nav class="sidebar__nav" aria-label="Điều hướng chính">${items}</nav>

      <div class="sidebar__user">
        <button type="button" class="user-button" id="userButton" aria-expanded="false" aria-haspopup="true">
          ${avatar(currentUser.full_name, 'sm')}
          <span class="user-button__meta">
            <span class="user-button__name">${escapeHtml(currentUser.full_name)}</span>
            <span class="user-button__role">${escapeHtml(currentUser.role)}</span>
          </span>
          <span class="user-button__caret" id="userCaret">▼</span>
        </button>
        <div class="user-menu hidden" id="userMenu">
          <a class="user-menu__item" href="profile.html">👤 Hồ sơ</a>
          <div class="user-menu__divider"></div>
          <button type="button" class="user-menu__item user-menu__item--danger" id="logoutButton">🚪 Đăng xuất</button>
        </div>
      </div>
    </aside>`;
}

function headerHtml(pageId) {
  const meta = PAGE_META[pageId] ?? PAGE_META.dashboard;
  return `
    <header class="header">
      <button type="button" class="sidebar-toggle" id="sidebarToggle"
              aria-label="Mở menu điều hướng" aria-expanded="false" aria-controls="sidebar">
        ${icons.menu()}
      </button>
      <div>
        <h1 class="header__title">${meta.title}</h1>
        <p class="header__subtitle">${meta.subtitle}</p>
      </div>
      <div class="header__meta">
        <div class="status-inline" id="headerMqtt"></div>
        <div class="header__divider"></div>
        <div class="status-inline" id="headerEsp"></div>
        <div class="header__divider"></div>
        <span class="header__clock" id="headerClock">--:--:--</span>
        <div class="header__divider"></div>
        <button type="button" class="icon-button" aria-label="Thông báo">🔔</button>
        ${avatar(currentUser.full_name, 'md')}
      </div>
    </header>`;
}

function renderHeaderStatus() {
  if (!SHOW_IOT_DATA) {
    document.getElementById('headerMqtt').textContent = 'MQTT —';
    document.getElementById('headerEsp').textContent = 'ESP32 —';
    return;
  }
  const { esp32Online, mqttConnected } = getState();

  document.getElementById('headerMqtt').innerHTML =
    `${statusDot(mqttConnected)}<span class="status-inline__label">MQTT</span>` +
    `<span class="status-inline__value ${mqttConnected ? 'is-up' : 'is-down'}">` +
    `${mqttConnected ? 'Connected' : 'Disconnected'}</span>`;

  document.getElementById('headerEsp').innerHTML =
    `${statusDot(esp32Online)}<span class="status-inline__label">ESP32</span>` +
    `<span class="status-inline__value ${esp32Online ? 'is-up' : 'is-down'}">` +
    `${esp32Online ? 'Online' : 'Offline'}</span>`;

}

function bindUserMenu() {
  const button = document.getElementById('userButton');
  const menu = document.getElementById('userMenu');
  const caret = document.getElementById('userCaret');

  const setOpen = (open) => {
    menu.classList.toggle('hidden', !open);
    button.setAttribute('aria-expanded', String(open));
    caret.textContent = open ? '▲' : '▼';
  };

  button.addEventListener('click', (e) => {
    e.stopPropagation();
    setOpen(menu.classList.contains('hidden'));
  });
  document.addEventListener('click', () => setOpen(false));
  menu.addEventListener('click', (e) => e.stopPropagation());

  document.getElementById('logoutButton').addEventListener('click', () => {
    setOpen(false);
    confirmLogout();
  });
}

function confirmLogout() {
  import('./ui.js').then(({ openLayerWith }) => {
    const layer = openLayerWith(
      `<div class="modal__icon">🚪</div>
       <h3 class="modal__title">Đăng xuất khỏi hệ thống?</h3>
       <p class="modal__text">Bạn sẽ cần đăng nhập lại để tiếp tục sử dụng Smart IoT.</p>
       <div class="modal__actions">
         <button type="button" class="btn btn--secondary" data-dismiss>Hủy</button>
         <button type="button" class="btn btn--danger" id="confirmLogout">Đăng xuất</button>
       </div>`,
      { panelClass: 'modal modal--sm modal--center' }
    );
    layer.panel.querySelector('#confirmLogout').addEventListener('click', async (event) => {
      const button = event.currentTarget;
      button.disabled = true;
      button.textContent = 'Đang đăng xuất...';
      await signOut();
      window.location.replace('login.html');
    });
  });
}

/* Dưới 900px sidebar bị đẩy ra ngoài màn hình (layout.css §media 900px).
   Không có nút này thì không còn cách nào mở menu để chuyển trang. */
function bindSidebarToggle() {
  const button = document.getElementById('sidebarToggle');
  const sidebar = document.getElementById('sidebar');
  const backdrop = document.getElementById('sidebarBackdrop');

  const setOpen = (open) => {
    sidebar.classList.toggle('is-open', open);
    backdrop.hidden = !open;
    button.setAttribute('aria-expanded', String(open));
  };

  button.addEventListener('click', () => setOpen(!sidebar.classList.contains('is-open')));
  backdrop.addEventListener('click', () => setOpen(false));
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') setOpen(false);
  });
  // Quay lại desktop khi menu đang mở: dọn trạng thái để lớp phủ không kẹt lại.
  window.matchMedia('(min-width: 901px)').addEventListener('change', (e) => {
    if (e.matches) setOpen(false);
  });
}

function startClock() {
  const el = document.getElementById('headerClock');
  const tick = () => { el.textContent = formatTime(); };
  tick();
  setInterval(tick, 1000);
}

/**
 * Dựng khung và trả về phần tử chứa nội dung trang.
 * @param {string} pageId khoá trong PAGE_META
 */
export function initLayout(pageId) {
  document.body.innerHTML = `
    <div class="app">
      ${sidebarHtml(pageId)}
      <div class="sidebar-backdrop" id="sidebarBackdrop" hidden></div>
      <div class="main">
        ${headerHtml(pageId)}
        <div class="content" id="content"></div>
      </div>
    </div>`;

  window.addEventListener('profile-updated', ({ detail }) => {
    currentUser = detail;
    document.querySelector('.user-button__name').textContent = detail.full_name;
    document.querySelector('.user-button .avatar').outerHTML = avatar(detail.full_name, 'sm');
    document.querySelector('.header__meta .avatar').outerHTML = avatar(detail.full_name, 'md');
  });
  bindUserMenu();
  bindSidebarToggle();
  startClock();
  renderHeaderStatus();
  subscribe(renderHeaderStatus);

  startStatusSync();

  return document.getElementById('content');
}
