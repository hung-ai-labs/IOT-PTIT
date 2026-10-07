// ws.js — một kết nối WebSocket dùng chung cho mỗi trang.

const TOKEN_KEY = 'smart_iot_token';
const MAX_BACKOFF_MS = 30_000;
const FALLBACK_AFTER_ATTEMPTS = 3;

const messageHandlers = new Map();
const stateHandlers = new Set();
const recentMessages = new Map();

let socket = null;
let retryTimer = null;
let retryAttempts = 0;
let connected = false;
let fallbackActive = false;
let closedByPage = false;

function connectionState() {
  return { connected, fallbackActive, retryAttempts };
}

function notifyState() {
  const snapshot = connectionState();
  stateHandlers.forEach((handler) => handler(snapshot));
}

function remember(type, data) {
  const messages = recentMessages.get(type) ?? [];
  messages.push({ data, receivedAt: Date.now() });
  recentMessages.set(type, messages.slice(-50));
}

function dispatch(type, data) {
  remember(type, data);
  (messageHandlers.get(type) ?? new Set()).forEach((handler) => {
    try {
      handler(data);
    } catch (error) {
      console.error(`Không xử lý được sự kiện WebSocket ${type}:`, error);
    }
  });
}

function websocketUrl(token) {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  return `${protocol}//${window.location.host}/ws?token=${encodeURIComponent(token)}`;
}

export function connectWebSocket() {
  if (closedByPage || socket?.readyState === WebSocket.OPEN ||
      socket?.readyState === WebSocket.CONNECTING) return;

  const token = localStorage.getItem(TOKEN_KEY);
  if (!token) {
    fallbackActive = true;
    notifyState();
    return;
  }

  socket = new WebSocket(websocketUrl(token));

  socket.addEventListener('open', () => {
    connected = true;
    fallbackActive = false;
    retryAttempts = 0;
    notifyState();
  });

  socket.addEventListener('message', (event) => {
    try {
      const message = JSON.parse(event.data);
      if (typeof message.type === 'string') dispatch(message.type, message.data);
    } catch {
      console.warn('Bỏ qua bản tin WebSocket không hợp lệ.');
    }
  });

  socket.addEventListener('close', (event) => {
    connected = false;
    socket = null;
    if (closedByPage) return;

    retryAttempts += 1;
    fallbackActive = retryAttempts >= FALLBACK_AFTER_ATTEMPTS;
    notifyState();

    // Token bị từ chối sẽ không tự hợp lệ trở lại nếu chưa đăng nhập lại.
    if (event.code === 1008) {
      fallbackActive = true;
      notifyState();
      return;
    }

    const delay = Math.min(1000 * (2 ** Math.max(0, retryAttempts - 1)), MAX_BACKOFF_MS);
    retryTimer = window.setTimeout(connectWebSocket, delay);
  });
}

export function onMessage(type, handler) {
  const handlers = messageHandlers.get(type) ?? new Set();
  handlers.add(handler);
  messageHandlers.set(type, handlers);
  return () => handlers.delete(handler);
}

export function onConnectionState(handler) {
  stateHandlers.add(handler);
  handler(connectionState());
  return () => stateHandlers.delete(handler);
}

export const isWebSocketConnected = () => connected;
export const isFallbackActive = () => fallbackActive;

export function waitForMessage(type, predicate, timeoutMs) {
  const cached = (recentMessages.get(type) ?? []).findLast(
    (message) => Date.now() - message.receivedAt < timeoutMs && predicate(message.data)
  );
  if (cached) return Promise.resolve(cached.data);

  if (fallbackActive) {
    return Promise.reject(new Error('WS_FALLBACK'));
  }

  return new Promise((resolve, reject) => {
    let removeMessage;
    let removeState;
    const cleanup = () => {
      window.clearTimeout(timer);
      removeMessage?.();
      removeState?.();
    };
    const timer = window.setTimeout(() => {
      cleanup();
      reject(new Error('WS_WAIT_TIMEOUT'));
    }, timeoutMs);

    removeMessage = onMessage(type, (data) => {
      if (!predicate(data)) return;
      cleanup();
      resolve(data);
    });
    removeState = onConnectionState((state) => {
      if (!state.fallbackActive) return;
      cleanup();
      reject(new Error('WS_FALLBACK'));
    });
  });
}

export function closeWebSocket() {
  closedByPage = true;
  window.clearTimeout(retryTimer);
  socket?.close(1000, 'Trang đã đóng.');
  socket = null;
  connected = false;
}

window.addEventListener('pagehide', closeWebSocket, { once: true });
