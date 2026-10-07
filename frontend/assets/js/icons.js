// icons.js — icon SVG inline (kế thừa màu qua currentColor)

const svg = (size, body) =>
  `<svg width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" ` +
  `stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" ` +
  `aria-hidden="true">${body}</svg>`;

export const icons = {
  user: (s = 16) => svg(s, '<circle cx="12" cy="8" r="4"/><path d="M4 22v-2a8 8 0 0 1 16 0v2"/>'),
  branch: (s = 24) => svg(s, '<circle cx="6" cy="18" r="3"/><circle cx="18" cy="6" r="3"/><path d="M6 3v12M6 12c6 0 12-1 12-3"/>'),
  palette: (s = 24) => svg(s, '<path d="M12 3a9 9 0 1 0 0 18h1a2 2 0 0 0 0-4h-1a2 2 0 0 1 0-4h4a5 5 0 0 0 5-5c0-3-4-5-9-5z"/><circle cx="7" cy="9" r=".5"/><circle cx="10" cy="6" r=".5"/><circle cx="15" cy="6" r=".5"/>'),
  book: (s = 24) => svg(s, '<path d="M12 5v16M12 5C8 2 4 3 2 4v16c3-1 7-1 10 1 3-2 7-2 10-1V4c-2-1-6-2-10 1z"/>'),
  code: (s = 24) => svg(s, '<path d="m8 6-6 6 6 6m8-12 6 6-6 6m-3-16-2 20"/>'),
  external: (s = 18) => svg(s, '<path d="M15 3h6v6m0-6L10 14M9 3H3v18h18v-6"/>'),
  dashboard: (s = 16) => svg(s, '<rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/>'),
  activity:  (s = 16) => svg(s, '<polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>'),
  power:     (s = 16) => svg(s, '<path d="M18.36 6.64a9 9 0 1 1-12.73 0"/><line x1="12" y1="2" x2="12" y2="12"/>'),
  history:   (s = 16) => svg(s, '<polyline points="12 8 12 12 14 14"/><path d="M3.05 11a9 9 0 1 0 .5-3.5"/><polyline points="3 3 3 9 9 9"/>'),
  file:      (s = 16) => svg(s, '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/>'),
  server:    (s = 16) => svg(s, '<rect x="2" y="2" width="20" height="8" rx="2"/><rect x="2" y="14" width="20" height="8" rx="2"/><line x1="6" y1="6" x2="6.01" y2="6"/><line x1="6" y1="18" x2="6.01" y2="18"/>'),
  menu:      (s = 18) => svg(s, '<line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="18" x2="21" y2="18"/>'),
  iot:       (s = 18) => svg(s, '<circle cx="12" cy="12" r="3"/><path d="M6.3 6.3a8 8 0 0 0 0 11.4"/><path d="M17.7 6.3a8 8 0 0 1 0 11.4"/><path d="M3.5 3.5a14 14 0 0 0 0 17"/><path d="M20.5 3.5a14 14 0 0 1 0 17"/>'),
};
