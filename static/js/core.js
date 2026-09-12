/* MANGENESIS — core: icons, formatting, DOM helpers, state store, API client */

/* ---------- Icons (24×24 stroke set, drawn once) ---------------------- */
export const ICON = {
  grid: 'M3 3h7v7H3zM14 3h7v7h-7zM14 14h7v7h-7zM3 14h7v7H3z',
  map: 'M9 20l-6 2V6l6-2m0 16l6 2m-6-2V4m6 18l6-2V4l-6 2m0 16V6m0 0L9 4',
  trend: 'M3 17l6-6 4 4 8-8M21 7v5h-5',
  shield: 'M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z M12 8v4M12 16h.01',
  bolt: 'M13 2L4.5 13H11l-1 9 8.5-11H12l1-9z',
  bell: 'M18 8a6 6 0 10-12 0c0 7-3 9-3 9h18s-3-2-3-9M13.7 21a2 2 0 01-3.4 0',
  rupee: 'M6 3h12M6 8h12M9 3c4 0 6 2 6 5s-2 5-6 5H6l7 8',
  building: 'M3 21h18M5 21V7l7-4 7 4v14M9 21v-4h6v4M9 10h.01M15 10h.01M9 14h.01M15 14h.01',
  file: 'M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8zM14 2v6h6M9 13h6M9 17h6',
  db: 'M12 8c4.4 0 8-1.3 8-3s-3.6-3-8-3-8 1.3-8 3 3.6 3 8 3zM4 5v14c0 1.7 3.6 3 8 3s8-1.3 8-3V5M4 12c0 1.7 3.6 3 8 3s8-1.3 8-3',
  layers: 'M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5',
  pin: 'M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 1116 0z M12 10a2 2 0 100-4 2 2 0 000 4z',
  down: 'M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M7 10l5 5 5-5M12 15V3',
  chev: 'M6 9l6 6 6-6',
  search: 'M11 19a8 8 0 100-16 8 8 0 000 16zM21 21l-4.3-4.3',
  alert: 'M10.3 3.9L1.8 18a2 2 0 001.7 3h17a2 2 0 001.7-3L14.7 3.9a2 2 0 00-3.4 0zM12 9v4M12 17h.01',
  check: 'M20 6L9 17l-5-5',
  x: 'M18 6L6 18M6 6l12 12',
  arrow: 'M5 12h14M12 5l7 7-7 7',
  wrench: 'M14.7 6.3a4 4 0 105.4 5.4l-9.4 9.4a2.1 2.1 0 01-3-3l9.4-9.4z',
  rain: 'M20 16.6A5 5 0 0018 7h-1.3A8 8 0 104 15.3M8 19v2M12 21v2M16 19v2',
  droplet: 'M12 2.7l5.7 5.6A8 8 0 116.3 8.3z',
  thermo: 'M14 14.8V4a2 2 0 10-4 0v10.8a4 4 0 104 0z',
  leaf: 'M11 20A7 7 0 019.8 6.1C15.5 5 17 4.5 19 2c1 2 2 4.2 2 8a7 7 0 01-10 10zM2 21c0-3 1.9-5.7 4.3-7',
  blast: 'M12 2v4M12 18v4M4.9 4.9l2.9 2.9M16.2 16.2l2.9 2.9M2 12h4M18 12h4M4.9 19.1l2.9-2.9M16.2 7.8l2.9-2.9',
  cpu: 'M4 4h16v16H4zM9 9h6v6H9zM9 1v3M15 1v3M9 20v3M15 20v3M1 9h3M1 15h3M20 9h3M20 15h3',
  target: 'M12 22a10 10 0 100-20 10 10 0 000 20zM12 18a6 6 0 100-12 6 6 0 000 12zM12 14a2 2 0 100-4 2 2 0 000 4z',
  drill: 'M12 2v6M9 8h6l-1.5 6h-3zM10.5 14v4a1.5 1.5 0 003 0v-4M12 22v-2',
  mail: 'M4 4h16a2 2 0 012 2v12a2 2 0 01-2 2H4a2 2 0 01-2-2V6a2 2 0 012-2zM22 6l-10 7L2 6',
  phone: 'M7 2h10a2 2 0 012 2v16a2 2 0 01-2 2H7a2 2 0 01-2-2V4a2 2 0 012-2zM12 18h.01',
  radio: 'M12 14a2 2 0 100-4 2 2 0 000 4zM8.5 15.5a5 5 0 010-7M15.5 8.5a5 5 0 010 7M5.6 18.4a9 9 0 010-12.8M18.4 5.6a9 9 0 010 12.8',
  sat: 'M13 7l3-3 4 4-3 3M10 10L7 7 3 11l3 3M12.5 12.5l4 4M2 22l6-6M17 14a5 5 0 01-5 5',
  menu: 'M3 12h18M3 6h18M3 18h18',
  sun: 'M12 17a5 5 0 100-10 5 5 0 000 10zM12 1v2M12 21v2M4.2 4.2l1.4 1.4M18.4 18.4l1.4 1.4M1 12h2M21 12h2M4.2 19.8l1.4-1.4M18.4 5.6l1.4-1.4',
  moon: 'M21 12.8A9 9 0 1111.2 3a7 7 0 009.8 9.8z',
  clock: 'M12 22a10 10 0 100-20 10 10 0 000 20zM12 6v6l4 2',
  sliders: 'M4 21v-7M4 10V3M12 21v-9M12 8V3M20 21v-5M20 12V3M1 14h6M9 8h6M17 16h6',
  table: 'M3 3h18v18H3zM3 9h18M3 15h18M9 3v18',
  scale: 'M12 3v18M5 7l-3 7h6zM19 7l-3 7h6zM5 7h14M8 21h8',
  compass: 'M12 22a10 10 0 100-20 10 10 0 000 20zM16.2 7.8l-2.1 6.3-6.3 2.1 2.1-6.3z',
};

export function icon(name, cls = '') {
  return `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"
    stroke-linecap="round" stroke-linejoin="round" class="${cls}" aria-hidden="true"><path d="${ICON[name] || ''}"/></svg>`;
}

/* ---------- Formatting ------------------------------------------------ */
export const fmt = {
  n(v, d = 0) {
    if (v === null || v === undefined || Number.isNaN(v)) return '—';
    return Number(v).toLocaleString('en-IN', { minimumFractionDigits: d, maximumFractionDigits: d });
  },
  t(v) { return fmt.n(v) + ' T'; },
  pct(v, d = 1) { return (v === null || v === undefined) ? '—' : `${Number(v).toFixed(d)}%`; },
  signed(v, d = 1) { return `${v > 0 ? '+' : ''}${Number(v).toFixed(d)}%`; },
  cr(v) { return `₹${Number(v).toFixed(2)} Cr`; },
  lakh(v) { return `₹${Number(v).toFixed(1)} L`; },
  /* Indian numbering: 1,00,00,000 = 1 crore */
  inr(v) {
    if (v >= 1e7) return `₹${(v / 1e7).toFixed(2)} Cr`;
    if (v >= 1e5) return `₹${(v / 1e5).toFixed(2)} L`;
    return `₹${fmt.n(v)}`;
  },
  compact(v) {
    if (Math.abs(v) >= 1e6) return (v / 1e6).toFixed(2) + 'M';
    if (Math.abs(v) >= 1e3) return (v / 1e3).toFixed(1) + 'k';
    return String(Math.round(v));
  },
  title(s) {
    return String(s || '').toLowerCase().replace(/(^|[\s\-/(])([a-z])/g, (_, a, b) => a + b.toUpperCase());
  },
  /* 21.383333 -> 21°23'00"N. Rounds seconds first, then carries into
     minutes and degrees, so 59.6" never prints as 60". */
  dms(v, axis) {
    const hemi = axis === 'lat' ? (v >= 0 ? 'N' : 'S') : (v >= 0 ? 'E' : 'W');
    let total = Math.round(Math.abs(v) * 3600);
    const s = total % 60; total = (total - s) / 60;
    const m = total % 60; const d = (total - m) / 60;
    return `${d}°${String(m).padStart(2, '0')}'${String(s).padStart(2, '0')}"${hemi}`;
  },
  date(iso) {
    return new Date(iso).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' });
  },
};

export const toneOf = (sev) => ({ HIGH: 'crit', CRITICAL: 'crit', MEDIUM: 'warn', ALERT: 'warn', LOW: 'good', NORMAL: 'good' }[sev] || 'plain');

/* ---------- DOM ------------------------------------------------------- */
export const $ = (sel, root = document) => root.querySelector(sel);
export const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

export function el(html) {
  const t = document.createElement('template');
  t.innerHTML = html.trim();
  return t.content.firstElementChild;
}

export function toast(msg, iconName = 'check') {
  let node = $('#toast');
  if (!node) {
    node = el(`<div class="toast" id="toast" role="status" aria-live="polite"></div>`);
    document.body.appendChild(node);
  }
  node.innerHTML = `${icon(iconName)}<span></span>`;
  node.querySelector('span').textContent = msg;
  requestAnimationFrame(() => node.classList.add('is-on'));
  clearTimeout(node._t);
  node._t = setTimeout(() => node.classList.remove('is-on'), 3400);
}

/* ---------- API ------------------------------------------------------- */
const cache = new Map();

async function getJSON(path, { fresh = false } = {}) {
  if (!fresh && cache.has(path)) return cache.get(path);
  const res = await fetch(path, { headers: { Accept: 'application/json' } });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText} — ${path}`);
  const data = await res.json();
  cache.set(path, data);
  return data;
}

export const api = {
  belts: () => getJSON('/api/sites/belts'),
  sites: () => getJSON('/api/sites'),
  site: (id) => getJSON(`/api/sites/${id}`),
  geojson: () => getJSON('/api/sites/geojson'),
  snapshot: (site, scenario) => getJSON(`/api/analytics/snapshot?site=${site}&scenario=${scenario}`),
  compare: (ids, scenario) => getJSON(`/api/analytics/compare?sites=${ids.join(',')}&scenario=${scenario}`),
  health: () => getJSON('/api/health', { fresh: true }),
  reportURL: (kind, site, scenario) => `/api/report/${kind}?site=${site}&scenario=${scenario}`,
};

/* ---------- Store ----------------------------------------------------- */
const KEY = 'mangenesis.prefs.v1';

function readPrefs() {
  try { return JSON.parse(localStorage.getItem(KEY)) || {}; } catch { return {}; }
}
function writePrefs(p) {
  try { localStorage.setItem(KEY, JSON.stringify(p)); } catch { /* private mode */ }
}

const prefs = readPrefs();

export const store = {
  site: prefs.site || 'gumgaon',
  scenario: prefs.scenario || 'equipment',
  view: (location.hash || '').replace('#', '') || 'command',
  theme: prefs.theme || 'dark',
  snapshot: null,
  registry: null,
  _subs: new Set(),

  on(fn) { this._subs.add(fn); return () => this._subs.delete(fn); },
  emit(reason) { this._subs.forEach((fn) => fn(this, reason)); },

  persist() { writePrefs({ site: this.site, scenario: this.scenario, theme: this.theme }); },

  async load(reason = 'init') {
    const [snap, registry] = await Promise.all([
      api.snapshot(this.site, this.scenario),
      this.registry ? Promise.resolve(this.registry) : api.belts(),
    ]);
    this.snapshot = snap;
    this.registry = registry;
    this.persist();
    this.emit(reason);
    return snap;
  },

  async setSite(id) {
    if (id === this.site) return;
    this.site = id;
    await this.load('site');
  },

  async setScenario(id) {
    if (id === this.scenario) return;
    this.scenario = id;
    await this.load('scenario');
  },

  setTheme(t) {
    this.theme = t;
    document.documentElement.setAttribute('data-theme', t);
    this.persist();
    this.emit('theme');
  },
};

/* Flatten the belt register into a lookup once it is loaded */
export function allSites(registry) {
  return (registry?.belts || []).flatMap((b) => b.sites.map((s) => ({ ...s, belt: b.belt, colour: b.colour })));
}
