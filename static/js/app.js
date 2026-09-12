/* MANGENESIS — application shell: navigation, selectors, routing, telemetry. */

import { $, $$, allSites, api, fmt, icon, store, toast } from './core.js';
import { VIEWS } from './views.js';

const NAV = [
  {
    group: 'Control', items: [
      { id: 'command', label: 'Command Centre', ic: 'grid' },
      { id: 'explorer', label: 'Geospatial Explorer', ic: 'map' },
      { id: 'enterprise', label: 'Enterprise Portfolio', ic: 'building' },
    ],
  },
  {
    group: 'Intelligence', items: [
      { id: 'reserve', label: 'Reserve Intelligence', ic: 'target' },
      { id: 'forecast', label: 'Production Forecast', ic: 'trend' },
      { id: 'risk', label: 'Risk Analysis', ic: 'shield' },
    ],
  },
  {
    group: 'Response', items: [
      { id: 'actions', label: 'Action Centre', ic: 'bolt' },
      { id: 'alerts', label: 'Alert Centre', ic: 'bell', badge: 'alerts' },
    ],
  },
  {
    group: 'Business', items: [
      { id: 'roi', label: 'ROI & Cost-Benefit', ic: 'rupee' },
      { id: 'reports', label: 'Reports & Exports', ic: 'file' },
      { id: 'register', label: 'Data Register', ic: 'db' },
    ],
  },
];

const TITLES = Object.fromEntries(NAV.flatMap(g => g.items.map(i => [i.id, i.label])));

/* ---------- Rail ------------------------------------------------------- */

function renderRail() {
  const nav = $('#rail-nav');
  nav.innerHTML = NAV.map(g => `
    <div class="navgroup">
      <div class="navgroup__label"><span>${g.group}</span></div>
      ${g.items.map(i => `
        <button class="navitem" data-view="${i.id}" type="button">
          ${icon(i.ic)}<span>${i.label}</span>
          ${i.badge ? `<span class="navitem__badge" data-badge="${i.badge}"></span>` : ''}
        </button>`).join('')}
    </div>`).join('');

  $$('[data-view]', nav).forEach(b => b.addEventListener('click', () => {
    go(b.dataset.view);
    $('#rail').classList.remove('is-open');
    $('#scrim').hidden = true;
  }));
}

function syncRail() {
  $$('#rail-nav [data-view]').forEach(b => b.classList.toggle('is-active', b.dataset.view === store.view));
  const badge = $('[data-badge="alerts"]');
  if (badge && store.snapshot) {
    const n = store.snapshot.alerts.filter(a => a.severity === 'CRITICAL').length;
    badge.textContent = n || '';
    badge.style.display = n ? '' : 'none';
  }
}

/* ---------- Selectors -------------------------------------------------- */

function popover(btn, pop) {
  const close = () => { pop.classList.remove('is-open'); btn.setAttribute('aria-expanded', 'false'); };
  const open = () => {
    $$('.pop.is-open').forEach(p => p.classList.remove('is-open'));
    $$('[aria-expanded="true"]').forEach(b => b.setAttribute('aria-expanded', 'false'));
    pop.classList.add('is-open');
    btn.setAttribute('aria-expanded', 'true');
    const s = pop.querySelector('.pop__search');
    if (s) setTimeout(() => s.focus(), 40);
  };
  btn.addEventListener('click', (e) => {
    e.stopPropagation();
    pop.classList.contains('is-open') ? close() : open();
  });
  pop.addEventListener('click', e => e.stopPropagation());
  document.addEventListener('click', close);
  document.addEventListener('keydown', e => { if (e.key === 'Escape') close(); });
  return { close };
}

let siteFilter = 'all';
let siteQuery = '';

function renderSiteList() {
  const body = $('#site-pop-body');
  if (!store.registry) return;
  const q = siteQuery.toLowerCase();
  const belts = store.registry.belts
    .map(b => ({
      ...b,
      sites: b.sites.filter(s =>
        (siteFilter === 'all' || s.tier === siteFilter) &&
        (!q || s.display.toLowerCase().includes(q) || s.state.toLowerCase().includes(q) || b.belt.toLowerCase().includes(q))),
    }))
    .filter(b => b.sites.length);

  if (!belts.length) {
    body.innerHTML = `<div class="pop__empty">No ore site matches this filter.</div>`;
    return;
  }

  body.innerHTML = belts.map(b => `
    <div class="pop__group"><b style="color:${b.colour}">${fmt.title(b.belt)}</b><i></i><em>${b.sites.length}</em></div>
    ${b.sites.map(s => `
      <button class="optrow ${s.id === store.site ? 'is-sel' : ''}" data-site="${s.id}" type="button">
        <span class="optrow__dot" style="background:${b.colour}"></span>
        <span style="min-width:0">
          <span class="optrow__n">${s.display}</span>
          <span class="optrow__m">${fmt.title(s.state)} · ${fmt.dms(s.lat, 'lat')} ${fmt.dms(s.lon, 'lon')}</span>
        </span>
        <span class="tier tier--${s.tier}">${s.tier}</span>
      </button>`).join('')}`).join('');

  $$('[data-site]', body).forEach(b => b.addEventListener('click', async () => {
    $('#site-pop').classList.remove('is-open');
    $('#site-btn').setAttribute('aria-expanded', 'false');
    await store.setSite(b.dataset.site);
  }));
}

function renderScenarioList() {
  const body = $('#sc-pop-body');
  if (!store.snapshot) return;
  body.innerHTML = store.snapshot.scenarios.map(s => `
    <button class="optrow ${s.id === store.scenario ? 'is-sel' : ''}" data-sc="${s.id}" type="button"
            style="grid-template-columns:8px 1fr auto">
      <span class="optrow__dot" style="background:${s.risk_pct >= 70 ? 'var(--crit)' : s.risk_pct >= 40 ? 'var(--warn)' : 'var(--good)'}"></span>
      <span style="min-width:0">
        <span class="optrow__n">${s.label}</span>
        <span class="optrow__m" style="white-space:normal;font-family:var(--ff-body);font-size:11px">${s.summary}</span>
      </span>
      <span class="tag tag--${s.risk_pct >= 70 ? 'crit' : s.risk_pct >= 40 ? 'warn' : 'good'}">${s.risk_pct}%</span>
    </button>`).join('');

  $$('[data-sc]', body).forEach(b => b.addEventListener('click', async () => {
    $('#sc-pop').classList.remove('is-open');
    $('#sc-btn').setAttribute('aria-expanded', 'false');
    await store.setScenario(b.dataset.sc);
  }));
}

function syncTopbar() {
  const snap = store.snapshot;
  if (!snap) return;
  $('#site-lead').textContent = snap.site.name;
  $('#site-sub').textContent = `${snap.site.district || fmt.title(snap.site.state)} · ${fmt.title(snap.site.belt)}`;
  $('#sc-lead').textContent = snap.scenario.label;
  $('#sc-sub').textContent = `${snap.risk.shortfall_probability}% shortfall risk`;
  const badge = $('#sc-risk');
  badge.textContent = `${snap.risk.shortfall_probability}%`;
  badge.className = `tag tag--${snap.risk.shortfall_probability >= 70 ? 'crit' : snap.risk.shortfall_probability >= 40 ? 'warn' : 'good'}`;
  const pdf = api.reportURL('brief.pdf', store.site, store.scenario);
  const link = $('#report-link');
  if (pdf) { link.href = pdf; link.setAttribute('download', ''); }
  else { link.href = '#reports'; link.removeAttribute('download'); }
  $('#alert-count').textContent = snap.alerts.filter(a => a.severity === 'CRITICAL').length;
}

/* ---------- Router ----------------------------------------------------- */

let cleanup = null;

async function render() {
  const host = $('#view');
  if (cleanup) { try { cleanup(); } catch { /* noop */ } cleanup = null; }

  const fn = VIEWS[store.view] || VIEWS.command;
  host.innerHTML = `<div class="empty">${icon('cpu')}<p>Loading ${TITLES[store.view] || 'view'}…</p></div>`;
  try {
    const res = await fn(host, store);
    if (typeof res === 'function') cleanup = res;
  } catch (err) {
    host.innerHTML = `<div class="empty">${icon('alert')}
      <p><b>${TITLES[store.view] || 'This view'} could not render.</b></p>
      <p class="tiny mono">${String(err.message || err)}</p></div>`;
    console.error(err);
  }
  syncRail();

  /* Scenario buttons and cross-view links are declared inside views */
  $$('[data-scenario]').forEach(b => b.addEventListener('click', () => store.setScenario(b.dataset.scenario)));
  $$('[data-goto]').forEach(b => b.addEventListener('click', () => go(b.dataset.goto)));
}

function go(view) {
  if (!VIEWS[view]) view = 'command';
  store.view = view;
  history.replaceState(null, '', `#${view}`);
  document.title = `${TITLES[view]} · MANGENESIS`;
  window.scrollTo({ top: 0, behavior: 'instant' });
  render();
}

/* ---------- Live telemetry -------------------------------------------- */

function clock() {
  const node = $('#clock');
  const tick = () => {
    node.textContent = new Date().toLocaleTimeString('en-IN', { hour12: false });
  };
  tick();
  setInterval(tick, 1000);
}

function telemetry() {
  const chip = $('#tele-state'), sub = $('#tele-sub');
  /* No live backend (static build) means no telemetry socket to open. */
  if (!api.reportURL('brief.pdf', store.site, store.scenario)) {
    chip.textContent = 'Snapshot';
    chip.className = 'tag tag--plain';
    sub.textContent = 'Pre-computed · Sentinel-2 archive';
    return;
  }
  let ws, ticks = 0;
  try {
    ws = new WebSocket(`${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}/ws/telemetry`);
  } catch { return; }

  ws.onopen = () => { chip.textContent = 'Synced'; chip.className = 'tag tag--good'; };
  ws.onmessage = (e) => {
    ticks++;
    try {
      const d = JSON.parse(e.data);
      const fleet = (d.fleet || []).length;
      const rain = d.weather?.rainfall_mm_hr;
      sub.textContent = fleet
        ? `${fleet} units · ${rain !== undefined ? rain.toFixed(1) + ' mm/hr' : 'nominal'}`
        : `tick ${ticks}`;
    } catch { /* ignore malformed frame */ }
  };
  ws.onclose = () => { chip.textContent = 'Offline'; chip.className = 'tag tag--plain'; sub.textContent = 'Sentinel-2 · 10 m archive'; };
  ws.onerror = () => ws.close();
}

/* ---------- Boot ------------------------------------------------------- */

async function boot() {
  document.documentElement.setAttribute('data-theme', store.theme);
  renderRail();
  clock();

  popover($('#site-btn'), $('#site-pop'));
  popover($('#sc-btn'), $('#sc-pop'));

  $('#site-q').addEventListener('input', e => { siteQuery = e.target.value; renderSiteList(); });
  $$('#site-pop [data-filter]').forEach(b => b.addEventListener('click', () => {
    siteFilter = b.dataset.filter;
    $$('#site-pop [data-filter]').forEach(x => x.classList.toggle('is-on', x === b));
    renderSiteList();
  }));

  $('#theme-btn').addEventListener('click', () => {
    const next = store.theme === 'dark' ? 'light' : 'dark';
    store.setTheme(next);
    $('#theme-btn').innerHTML = icon(next === 'dark' ? 'sun' : 'moon');
    $('#theme-btn').setAttribute('aria-label', `Switch to ${next === 'dark' ? 'light' : 'dark'} theme`);
  });
  $('#theme-btn').innerHTML = icon(store.theme === 'dark' ? 'sun' : 'moon');

  $('#menu-btn').addEventListener('click', () => {
    $('#rail').classList.add('is-open');
    $('#scrim').hidden = false;
  });
  $('#scrim').addEventListener('click', () => {
    $('#rail').classList.remove('is-open');
    $('#scrim').hidden = true;
  });
  $('#alert-btn').addEventListener('click', () => go('alerts'));

  store.on((s, reason) => {
    syncTopbar();
    renderSiteList();
    renderScenarioList();
    syncRail();
    if (reason === 'site' || reason === 'scenario') {
      render();
      if (reason === 'site') toast(`Loaded ${s.snapshot.site.name} — ${fmt.title(s.snapshot.site.belt)}`, 'pin');
      if (reason === 'scenario') toast(`Scenario: ${s.snapshot.scenario.label} — models re-computed`, 'sliders');
    }
    if (reason === 'theme') render();
  });

  window.addEventListener('hashchange', () => {
    const v = location.hash.replace('#', '');
    if (v && v !== store.view) go(v);
  });

  try {
    await store.load('init');
  } catch (err) {
    $('#view').innerHTML = `<div class="empty">${icon('alert')}
      <p><b>Could not reach the MANGENESIS API.</b></p>
      <p class="tiny">Start the platform with <code class="mono">python run.py</code> and reload.</p>
      <p class="tiny mono muted">${String(err.message || err)}</p></div>`;
    return;
  }

  syncTopbar();
  renderSiteList();
  renderScenarioList();
  go(store.view);
  telemetry();
}

boot();
