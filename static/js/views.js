/* MANGENESIS — view renderers. Each takes (host, store) and may return a
   cleanup function for anything it attaches outside the host element. */

import { $, $$, api, allSites, fmt, icon, store, toast, toneOf } from './core.js';
import { columns, forecastChart, gauge, hbars, orebody, riskDonut, scatter, shareBar, sparkline } from './viz.js';
import { nationalMap, siteMap } from './geomap.js';

/* ---------- shared fragments ------------------------------------------ */

const head = (eyebrow, title, sub) => `
  <header class="pagehead rise">
    <div class="eyebrow">${eyebrow}</div>
    <h1>${title}</h1>
    ${sub ? `<p>${sub}</p>` : ''}
  </header>`;

const panel = (title, body, { sub = '', tag = '', foot = '', cls = '', bodyCls = '', ic = '' } = {}) => `
  <section class="panel ${cls}">
    <div class="panel__head">
      <h2 class="panel__title">${ic ? icon(ic) : ''}${title}</h2>
      ${sub ? `<span class="panel__sub">${sub}</span>` : ''}
      ${tag ? `<span class="push">${tag}</span>` : ''}
    </div>
    <div class="panel__body ${bodyCls}">${body}</div>
    ${foot ? `<div class="panel__foot">${foot}</div>` : ''}
  </section>`;

const kpiTile = (k) => {
  const tone = k.tone === 'high' ? 'crit' : k.tone === 'medium' ? 'warn' : k.tone === 'low' ? 'good' : k.tone;
  return `<article class="kpi kpi--${tone === 'good' ? 'good' : tone === 'crit' ? 'crit' : tone === 'warn' ? 'warn' : 'v'}">
    <div class="kpi__label">${k.label}</div>
    <div class="kpi__val">${k.value}<span class="kpi__unit">${k.unit}</span></div>
    <div class="kpi__foot">
      ${k.delta !== null && k.delta !== undefined
        ? `<span class="delta delta--${k.delta >= 0 ? 'up' : 'down'}">${fmt.signed(k.delta)}</span>` : ''}
      <span>${k.sub}</span>
    </div>
  </article>`;
};

const scenarioBar = (snap, { compact = false } = {}) => `
  <section class="panel">
    <div class="panel__head">
      <h2 class="panel__title">${icon('sliders')}Operational Scenario Simulator</h2>
      <span class="panel__sub push">${compact ? 'Switch to re-run every model' : 'Simulate extraction bottlenecks and watch the forecast, diagnostics, action plan and ROI re-compute together'}</span>
    </div>
    <div class="panel__body">
      <div class="scenarios">
        ${snap.scenarios.map(s => `
          <button class="scenario ${s.id === snap.scenario.id ? 'is-on' : ''}" data-scenario="${s.id}" type="button">
            <div class="scenario__top">
              <span class="scenario__name">${s.label}</span>
              <span class="tag tag--${s.risk_pct >= 70 ? 'crit' : s.risk_pct >= 40 ? 'warn' : 'good'}">${s.risk_pct}% risk</span>
            </div>
            <p class="scenario__desc">${s.summary}</p>
          </button>`).join('')}
      </div>
    </div>
  </section>`;

const telemetryList = (signals) => `
  <div class="stack stack--sm">
    ${signals.map(t => `
      <div class="row row--between" style="padding:11px 13px;border-radius:var(--r-md);background:var(--surface-2);border:1px solid var(--hairline)">
        <span class="row" style="gap:11px">
          <span class="channel__icon" style="width:32px;height:32px;border-radius:9px">${icon(t.icon)}</span>
          <span>
            <b style="font-size:12.5px">${t.label}</b>
            <span class="mono muted" style="display:block;font-size:11px">${fmt.n(t.value, Number.isInteger(t.value) ? 0 : 1)} ${t.value === 1 ? t.unit.replace(/e?s$/, '') : t.unit}</span>
          </span>
        </span>
        <span class="tag tag--${toneOf(t.status)}">${t.status}</span>
      </div>`).join('')}
  </div>`;

const geologyList = (site) => `
  <dl class="deflist">
    <div><dt>Metallogenic belt</dt><dd>${fmt.title(site.belt)}</dd></div>
    <div><dt>Host lithology</dt><dd>${fmt.title(site.hostrock)}</dd></div>
    <div><dt>Morphogenesis</dt><dd>${fmt.title(site.morphogenesis)}</dd></div>
    <div><dt>Stratigraphic formation</dt><dd>${site.formation}</dd></div>
    <div><dt>Survey toposheet</dt><dd class="mono">${site.toposheet}</dd></div>
    <div><dt>Coordinates</dt><dd class="mono">${fmt.dms(site.lat, 'lat')} ${fmt.dms(site.lon, 'lon')}</dd></div>
    <div><dt>Register source</dt><dd>${site.source}${site.coord_precision === 'approximate' ? ' · approx.' : ''}</dd></div>
  </dl>`;

/* ---------- 1. Command Centre ----------------------------------------- */

export function command(host, s) {
  const snap = s.snapshot, { production: p, risk, plan, reserve: res, roi } = snap;

  host.innerHTML = `
    ${head('Live control plane', `${snap.site.name}`,
      `${fmt.title(snap.site.belt)} · ${snap.site.district || fmt.title(snap.site.state)}. Reserve targeting, shortfall prediction and corrective dispatch on one surface.`)}

    <div class="grid grid--kpi">${snap.kpis.map(kpiTile).join('')}</div>

    <div class="grid grid--main">
      <div class="stack">
        <section class="panel panel--raised">
          <div class="panel__head">
            <h2 class="panel__title">${icon('pin')}Geospatial Reserve Map</h2>
            <span class="panel__sub">${snap.site.district || fmt.title(snap.site.state)} · live telemetry</span>
            <span class="push tag">${res.zones.length} target sectors</span>
          </div>
          <div class="mapshell mapshell--tall" id="cmd-map" style="border:none;border-radius:0"></div>
        </section>

        ${panel('Operational Diagnostic', `
          <div class="callout ${risk.shortfall_probability >= 70 ? '' : risk.shortfall_probability >= 40 ? 'callout--warn' : 'callout--good'}">
            <span class="callout__icon">${icon('alert')}</span>
            <div class="callout__body">
              <div class="callout__title">${risk.root_cause}</div>
              <p class="callout__sub">${snap.scenario.detail}</p>
            </div>
            <div class="callout__stats">
              <div class="callout__stat"><b>${fmt.n(risk.deficit_t)}</b><span>Deficit T/day</span></div>
              <div class="callout__stat"><b>${risk.shortfall_probability}%</b><span>Probability</span></div>
              <div class="callout__stat"><b>+${fmt.n(plan.recovered_t)}</b><span>Recoverable T</span></div>
            </div>
          </div>`, { ic: 'cpu', bodyCls: '' })}
      </div>

      <div class="stack">
        ${panel('7-Day Production Forecast', `
          <div id="cmd-fc"></div>
          <div class="chart__legend" style="margin-top:12px">
            <span><i style="background:var(--s2)"></i>Recorded extraction</span>
            <span><i style="background:var(--violet-hi)"></i>AI forecast</span>
            <span><i style="background:var(--muted)"></i>Daily target</span>
          </div>`, { tag: `<span class="tag">${p.model.architecture.split('(')[0].trim()}</span>`, ic: 'trend' })}

        ${panel('Shortfall Projection', `
          <div class="row row--between" style="margin-bottom:14px">
            <div>
              <div class="mono muted tiny">EXPECTED DEFICIT</div>
              <div style="font-family:var(--ff-display);font-size:30px;font-weight:800;letter-spacing:-.03em">${fmt.n(risk.deficit_t)}<span style="font-size:.5em;color:var(--muted)"> T</span></div>
            </div>
            <div style="text-align:right">
              <div class="mono muted tiny">PROBABILITY</div>
              <div style="font-family:var(--ff-display);font-size:30px;font-weight:800;letter-spacing:-.03em;color:var(--${risk.shortfall_probability >= 70 ? 'crit' : 'warn'})">${risk.shortfall_probability}%</div>
            </div>
          </div>
          <div class="mono muted tiny" style="margin-bottom:9px">PRIMARY RISK FACTORS</div>
          ${hbars(risk.factors.slice(0, 4))}`, { ic: 'alert' })}

        ${panel('Live Telemetry Signals', telemetryList(risk.telemetry), {
          tag: `<span class="tag tag--good"><span class="dot dot--pulse"></span> Connected</span>`, ic: 'radio' })}
      </div>
    </div>

    <div class="grid grid--2">
      ${panel('Reserve Position', `
        <div class="grid grid--3" style="gap:12px;margin-bottom:16px">
          <div><div class="mono muted tiny">INDICATED</div><b style="font-size:19px">${(res.totals.total_indicated_t / 1e6).toFixed(2)} Mt</b></div>
          <div><div class="mono muted tiny">WEIGHTED Mn</div><b style="font-size:19px">${res.totals.weighted_mn_grade}%</b></div>
          <div><div class="mono muted tiny">CONTAINED Mn</div><b style="font-size:19px">${(res.totals.contained_mn_t / 1e6).toFixed(2)} Mt</b></div>
        </div>
        ${geologyList(snap.site)}`, { ic: 'target', tag: `<span class="tag tag--info">ROC-AUC ${res.model.roc_auc}</span>` })}

      ${panel('Decision Pipeline', `
        <div class="pipeline">
          ${plan.pipeline.map(st => `
            <div class="pipestep">
              <span class="pipestep__n">${st.step}</span>
              <div>
                <div class="pipestep__st">${st.stage}</div>
                <div class="pipestep__tx">${st.text}</div>
              </div>
            </div>`).join('')}
        </div>`, {
        ic: 'bolt',
        foot: `<div class="row row--between">
          <span class="muted tiny">MILP solver · ${plan.solver.status} · ${plan.solver.selected}/${plan.solver.candidates} interventions</span>
          <button class="btn btn--primary btn--sm" data-goto="actions">Open action centre ${icon('arrow')}</button>
        </div>` })}
    </div>`;

  $('#cmd-fc').innerHTML = forecastChart(p, { w: 520, h: 220, compact: true });
  const m = siteMap($('#cmd-map'), snap);
  return () => m.destroy();
}

/* ---------- 2. Reserve Intelligence ------------------------------------ */

export function reserve(host, s) {
  const snap = s.snapshot, res = snap.reserve, t = res.totals;

  host.innerHTML = `
    ${head('Surface & sub-surface targeting', 'Reserve Intelligence',
      `AI-assisted identification of manganese exploration targets by fusing multi-band satellite data with the ${fmt.title(snap.site.belt)} lithostratigraphy at ${snap.site.name}.`)}

    <div class="grid grid--kpi">
      ${kpiTile({ label: 'Indicated tonnage', value: (t.total_indicated_t / 1e6).toFixed(2), unit: 'Mt', delta: null, sub: `${res.zones.length} target sectors`, tone: 'v' })}
      ${kpiTile({ label: 'Best sector', value: t.best_zone_probability, unit: '% prob.', delta: null, sub: `${t.high_potential_zones} of ${res.zones.length} sectors ≥ 70%`, tone: t.best_zone_probability >= 70 ? 'good' : 'warn' })}
      ${kpiTile({ label: 'Weighted Mn grade', value: t.weighted_mn_grade, unit: '%', delta: null, sub: res.geology.grade_window + ' window', tone: 'good' })}
      ${kpiTile({ label: 'Contained metal', value: (t.contained_mn_t / 1e6).toFixed(2), unit: 'Mt', delta: null, sub: 'Mn content', tone: 'v' })}
      ${kpiTile({ label: 'Drilling', value: t.drill_holes, unit: 'holes', delta: null, sub: `${fmt.n(t.total_metres)} m logged`, tone: 'v' })}
    </div>

    <div class="grid grid--main">
      <section class="panel panel--raised">
        <div class="panel__head">
          <h2 class="panel__title">${icon('sat')}Spectral Fusion Map</h2>
          <span class="panel__sub">Click any sector or collar to inspect assay grades</span>
        </div>
        <div class="mapshell mapshell--tall" id="res-map" style="border:none;border-radius:0"></div>
      </section>

      <div class="stack">
        ${panel('Data Fusion Streams', `
          <div class="stack stack--sm">
            ${res.fusion_streams.map(f => `
              <div class="row row--between" style="padding:10px 12px;border-radius:var(--r-md);background:var(--surface-2);border:1px solid var(--hairline)">
                <span class="row" style="gap:9px;min-width:0">
                  <i class="legend__sw" style="background:${f.colour};margin:0"></i>
                  <span style="min-width:0">
                    <b style="font-size:12.5px;display:block">${f.label}</b>
                    <span class="mono muted" style="font-size:10.5px">${f.value}${f.unit ? ' ' + f.unit : ''}</span>
                  </span>
                </span>
                <span class="tag tag--good">${f.status}</span>
              </div>`).join('')}
          </div>`, { ic: 'layers' })}

        ${panel('Reserve Model Status', `
          <dl class="deflist">
            <div><dt>Architecture</dt><dd>${res.model.architecture}</dd></div>
            <div><dt>ROC-AUC</dt><dd class="mono" style="color:var(--good)">${res.model.roc_auc}</dd></div>
            <div><dt>Precision / recall</dt><dd class="mono">${res.model.precision} / ${res.model.recall}</dd></div>
            <div><dt>Fused features</dt><dd class="mono">${res.model.features}</dd></div>
            <div><dt>Calibration site</dt><dd>${res.model.calibration_site}</dd></div>
            <div><dt>Assay logs linked</dt><dd class="mono">${res.model.assay_logs} holes</dd></div>
            <div><dt>Regional strike</dt><dd class="mono">${res.strike_azimuth}° from N</dd></div>
          </dl>`, { ic: 'cpu' })}

        ${panel('Grade vs Tonnage', `<div id="res-scatter"></div>
          <p class="tiny muted" style="margin-top:10px">Bubble size is reserve probability. ${res.geology.note}.</p>`, { ic: 'scale' })}
      </div>
    </div>

    <div class="grid grid--main">
      ${panel('Ore-Body Block Model', `
        <canvas id="res-3d" style="width:100%;height:400px;display:block;border-radius:var(--r-md);background:var(--ink)"></canvas>
        <div class="row row--between" style="margin-top:12px">
          <div class="chart__legend">
            <span><i style="background:var(--good)"></i>High grade ≥38% Mn</span>
            <span><i style="background:var(--warn)"></i>Medium 28–38%</span>
            <span><i style="background:var(--crit)"></i>Low &lt;28%</span>
          </div>
          <span class="tiny muted">Drag to rotate</span>
        </div>`, { ic: 'compass', sub: 'Drill collars projected to logged depth inside the modelled sector envelopes', cls: 'panel--raised' })}

      ${panel('Target Sector Register', `
        <div class="tablewrap">
          <table class="data">
            <thead><tr><th>Sector</th><th>Probability</th><th>Mn</th><th>Tonnage</th><th>Strike</th><th>Depth</th></tr></thead>
            <tbody>${res.zones.map(z => `
              <tr>
                <td class="strong">${z.name}<span class="sub mono">${z.id}</span></td>
                <td class="num"><span class="tag tag--${z.class === 'high' ? 'good' : z.class === 'medium' ? 'warn' : 'plain'}">${z.probability_pct}%</span></td>
                <td class="num">${z.mn_grade_pct}%</td>
                <td class="num">${fmt.n(z.tonnage_t)} T</td>
                <td class="num">${z.strike_length_m} m</td>
                <td class="num">${z.depth_extent_m} m</td>
              </tr>`).join('')}</tbody>
          </table>
        </div>`, { ic: 'table', bodyCls: 'panel__body--flush' })}
    </div>

    ${panel('Drill Core Assay Register', `
      <div class="tablewrap">
        <table class="data">
          <thead><tr><th>Hole</th><th>Coordinates</th><th>Depth</th><th>Intercept</th><th>Mn %</th><th>Fe %</th><th>SiO₂ %</th><th>P %</th><th>Lithology</th><th>Status</th></tr></thead>
          <tbody>${res.drill_holes.map(d => `
            <tr>
              <td class="strong mono">${d.hole_id}</td>
              <td class="mono tiny muted">${fmt.dms(d.lat, 'lat')} ${fmt.dms(d.lon, 'lon')}</td>
              <td class="num">${d.depth_m} m</td>
              <td class="num">${d.intercept_m} m</td>
              <td class="num" style="color:var(--${d.mn_grade_pct >= 38 ? 'good' : d.mn_grade_pct >= 28 ? 'warn' : 'crit'});font-weight:700">${d.mn_grade_pct}</td>
              <td class="num">${d.fe_pct}</td>
              <td class="num">${d.sio2_pct}</td>
              <td class="num">${d.p_pct}</td>
              <td>${fmt.title(d.lithology)}</td>
              <td><span class="tag tag--${d.status === 'Assayed' ? 'good' : 'plain'}">${d.status}</span></td>
            </tr>`).join('')}</tbody>
        </table>
      </div>`, { ic: 'drill', bodyCls: 'panel__body--flush', tag: `<span class="tag">${t.drill_holes} holes · ${fmt.n(t.total_metres)} m</span>` })}`;

  $('#res-scatter').innerHTML = scatter(res.zones, { w: 420, h: 230 });
  const m = siteMap($('#res-map'), snap);
  const stop3d = orebody($('#res-3d'), res, snap.site);
  return () => { m.destroy(); stop3d(); };
}

/* ---------- 3. Geospatial Explorer ------------------------------------ */

export function explorer(host, s) {
  const sites = allSites(s.registry);
  const stats = s.registry.stats;
  let focusBelt = null;
  let query = '';

  host.innerHTML = `
    ${head('National occurrence register', 'Geospatial Explorer',
      `All ${stats.total_sites} recorded manganese localities across ${stats.belts} metallogenic belts and ${stats.states} states. Select any site to load its reserve model, forecast and action plan across the platform.`)}

    <div class="grid grid--kpi">
      ${kpiTile({ label: 'Localities', value: stats.total_sites, unit: '', delta: null, sub: 'GSI + MOIL register', tone: 'v' })}
      ${kpiTile({ label: 'Operating mines', value: stats.operating_mines, unit: '', delta: null, sub: `${fmt.n(stats.combined_rated_tpd)} T/day rated`, tone: 'good' })}
      ${kpiTile({ label: 'Exploration targets', value: stats.exploration_targets, unit: '', delta: null, sub: 'Inside MOIL lease belts', tone: 'warn' })}
      ${kpiTile({ label: 'Metallogenic belts', value: stats.belts, unit: '', delta: null, sub: `${stats.host_lithologies} host lithologies`, tone: 'v' })}
    </div>

    <div class="grid grid--main">
      <section class="panel panel--raised">
        <div class="panel__head">
          <h2 class="panel__title">${icon('map')}Manganese Belts of India</h2>
          <span class="panel__sub">Click a locality to select it</span>
          <span class="push"><button class="btn btn--ghost btn--sm" id="ex-clear">Show all belts</button></span>
        </div>
        <div class="mapshell mapshell--tall" id="ex-map" style="border:none;border-radius:0"></div>
      </section>

      <div class="stack">
        ${panel('Filter by Belt', `
          <div class="stack stack--sm" id="ex-belts">
            ${s.registry.belts.map(b => `
              <button class="layerrow" data-belt="${b.belt}" type="button">
                <span class="layerrow__sw" style="background:${b.colour}"></span>
                <span style="min-width:0">
                  <b style="display:block;font-size:12.5px">${fmt.title(b.belt)}</b>
                  <span class="tiny muted">${b.states.map(fmt.title).join(' · ')}</span>
                </span>
                <span class="layerrow__state">${b.count}</span>
              </button>`).join('')}
          </div>`, { ic: 'layers' })}

        ${panel('Localities', `
          <input class="pop__search" id="ex-q" type="search" placeholder="Search locality, host rock or state…" aria-label="Search localities"/>
          <div class="stack stack--sm" id="ex-list" style="margin-top:12px;max-height:520px;overflow-y:auto"></div>`,
          { ic: 'search', tag: `<span class="tag" id="ex-count"></span>` })}
      </div>
    </div>

    ${panel('Full Register', `
      <div class="tablewrap">
        <table class="data" id="ex-table">
          <thead><tr>
            <th class="sortable" data-k="display">Locality <span class="arrow">↕</span></th>
            <th class="sortable" data-k="belt">Belt <span class="arrow">↕</span></th>
            <th class="sortable" data-k="state">State <span class="arrow">↕</span></th>
            <th>Toposheet</th><th>Latitude</th><th>Longitude</th>
            <th>Host rock</th><th>Formation</th><th>Class</th>
          </tr></thead>
          <tbody></tbody>
        </table>
      </div>`, { ic: 'table', bodyCls: 'panel__body--flush', sub: 'Sortable · click a row to select that site' })}`;

  let full = [];
  api.sites().then(d => { full = d.sites; renderTable(); });

  const listHost = $('#ex-list'), countTag = $('#ex-count');

  function filtered() {
    const q = query.toLowerCase();
    return sites.filter(x =>
      (!focusBelt || x.belt === focusBelt) &&
      (!q || x.display.toLowerCase().includes(q) || x.state.toLowerCase().includes(q) || x.belt.toLowerCase().includes(q)));
  }

  function renderList() {
    const rows = filtered();
    countTag.textContent = `${rows.length} sites`;
    listHost.innerHTML = rows.length ? rows.map(x => `
      <button class="optrow ${x.id === s.site ? 'is-sel' : ''}" data-id="${x.id}" type="button">
        <span class="optrow__dot" style="background:${x.colour}"></span>
        <span style="min-width:0">
          <span class="optrow__n">${x.display}</span>
          <span class="optrow__m">${fmt.title(x.state)} · ${fmt.dms(x.lat, 'lat')}</span>
        </span>
        <span class="tier tier--${x.tier}">${x.tier}</span>
      </button>`).join('') : `<div class="pop__empty">No locality matches “${query}”.</div>`;
    $$('[data-id]', listHost).forEach(b => b.addEventListener('click', () => store.setSite(b.dataset.id)));
  }

  function renderMap() {
    nationalMap($('#ex-map'), sites, {
      selected: s.site, focusBelt,
      onSelect: (id) => store.setSite(id),
    });
  }

  let sortK = 'display', sortDir = 1;
  function renderTable() {
    const tb = $('#ex-table tbody');
    if (!tb) return;
    const rows = full
      .filter(r => (!focusBelt || r.belt === focusBelt))
      .filter(r => !query || `${r.display} ${r.state} ${r.hostrock} ${r.belt}`.toLowerCase().includes(query.toLowerCase()))
      .sort((a, b) => String(a[sortK]).localeCompare(String(b[sortK])) * sortDir);
    tb.innerHTML = rows.map(r => `
      <tr class="is-click ${r.id === s.site ? 'is-sel' : ''}" data-id="${r.id}">
        <td class="strong">${r.display}${r.rated_tpd && r.tier === 'operating' ? `<span class="sub">${fmt.n(r.rated_tpd)} T/day rated</span>` : ''}</td>
        <td>${fmt.title(r.belt)}</td>
        <td>${fmt.title(r.state)}</td>
        <td class="mono tiny">${r.toposheet}</td>
        <td class="num tiny">${fmt.dms(r.lat, 'lat')}</td>
        <td class="num tiny">${fmt.dms(r.lon, 'lon')}</td>
        <td class="tiny">${fmt.title(r.hostrock)}</td>
        <td class="tiny">${r.formation}</td>
        <td><span class="tier tier--${r.tier}">${r.tier}</span></td>
      </tr>`).join('');
    $$('#ex-table tbody tr').forEach(tr => tr.addEventListener('click', () => store.setSite(tr.dataset.id)));
    $$('#ex-table th.sortable').forEach(th => {
      th.classList.toggle('is-sorted', th.dataset.k === sortK);
      th.onclick = () => { sortDir = th.dataset.k === sortK ? -sortDir : 1; sortK = th.dataset.k; renderTable(); };
    });
  }

  $$('#ex-belts [data-belt]').forEach(b => b.addEventListener('click', () => {
    focusBelt = focusBelt === b.dataset.belt ? null : b.dataset.belt;
    $$('#ex-belts [data-belt]').forEach(x => x.classList.toggle('is-on', x.dataset.belt === focusBelt));
    renderMap(); renderList(); renderTable();
  }));
  $('#ex-clear').addEventListener('click', () => {
    focusBelt = null; query = ''; $('#ex-q').value = '';
    $$('#ex-belts [data-belt]').forEach(x => x.classList.remove('is-on'));
    renderMap(); renderList(); renderTable();
  });
  $('#ex-q').addEventListener('input', (e) => { query = e.target.value; renderList(); renderTable(); });

  renderMap(); renderList();
}

/* ---------- 4. Production Forecast ------------------------------------ */

export function forecast(host, s) {
  const snap = s.snapshot, p = snap.production, sum = p.summary;

  host.innerHTML = `
    ${head('7-day shortfall prediction', 'Production Continuity Forecast',
      `Predicting production shortfalls up to ${p.model.horizon_days} days ahead at ${snap.site.name}, before they reach the processing plant's feed rate.`)}

    ${scenarioBar(snap)}

    <section class="panel panel--raised">
      <div class="panel__head">
        <h2 class="panel__title">${icon('trend')}14-Day Recorded Extraction &amp; 7-Day Prediction</h2>
        <span class="panel__sub">Calibrated on ${p.model.calibration.toLowerCase()}</span>
        <span class="push chart__legend">
          <span><i style="background:var(--s2)"></i>Actual</span>
          <span><i style="background:var(--violet-hi)"></i>AI forecast</span>
          <span><i style="background:var(--muted)"></i>${fmt.n(p.target)} T target</span>
        </span>
      </div>
      <div class="panel__body"><div id="fc-main"></div></div>
      <div class="panel__foot">
        <div class="row row--between">
          <span class="mono tiny muted">${sum.history_window} recorded &nbsp;→&nbsp; ${sum.forecast_window} forecast</span>
          <span class="tag tag--crit">Projected deficit −${fmt.n(sum.peak_deficit_t)} T on ${fmt.date(sum.peak_deficit_date)}</span>
        </div>
      </div>
    </section>

    <div class="grid grid--kpi">
      ${kpiTile({ label: 'Current output', value: fmt.n(sum.current_output), unit: 'T', delta: sum.current_vs_target_pct, sub: 'vs daily target', tone: sum.current_vs_target_pct < -5 ? 'crit' : 'v' })}
      ${kpiTile({ label: 'Peak deficit', value: fmt.n(sum.peak_deficit_t), unit: 'T', delta: null, sub: fmt.date(sum.peak_deficit_date), tone: 'crit' })}
      ${kpiTile({ label: 'Cumulative deficit', value: fmt.n(sum.cumulative_deficit_t), unit: 'T', delta: null, sub: `Over ${p.model.horizon_days} days`, tone: 'warn' })}
      ${kpiTile({ label: 'Forecast attainment', value: sum.attainment_pct, unit: '%', delta: null, sub: 'Of planned output', tone: sum.attainment_pct >= 95 ? 'good' : 'warn' })}
      ${kpiTile({ label: '14-day mean', value: fmt.n(sum.history_mean), unit: 'T', delta: null, sub: 'Recorded baseline', tone: 'v' })}
    </div>

    <div class="grid grid--2">
      ${panel('Daily Forecast Detail', `
        <div class="tablewrap">
          <table class="data">
            <thead><tr><th>Date</th><th>Forecast</th><th>Lower</th><th>Upper</th><th>Target</th><th>Gap</th></tr></thead>
            <tbody>${p.forecast.map(f => {
              const gap = f.target - f.forecast;
              return `<tr>
                <td class="strong">${f.label}</td>
                <td class="num">${fmt.n(f.forecast)}</td>
                <td class="num muted">${fmt.n(f.lower)}</td>
                <td class="num muted">${fmt.n(f.upper)}</td>
                <td class="num muted">${fmt.n(f.target)}</td>
                <td class="num" style="color:var(--${gap > 0 ? 'crit' : 'good'});font-weight:700">${gap > 0 ? '−' : '+'}${fmt.n(Math.abs(gap))}</td>
              </tr>`;
            }).join('')}</tbody>
          </table>
        </div>`, { ic: 'table', bodyCls: 'panel__body--flush' })}

      <div class="stack">
        ${panel('Forecast Model', `
          <dl class="deflist">
            <div><dt>Architecture</dt><dd>${p.model.architecture}</dd></div>
            <div><dt>Horizon</dt><dd class="mono">${p.model.horizon_days} days</dd></div>
            <div><dt>Backtested MAPE</dt><dd class="mono" style="color:var(--good)">${p.model.mape}%</dd></div>
            <div><dt>Input features</dt><dd class="mono">${p.model.features}</dd></div>
            <div><dt>Calibration inputs</dt><dd>${p.model.calibration}</dd></div>
            <div><dt>Daily planned output</dt><dd class="mono">${fmt.n(p.target)} T</dd></div>
          </dl>`, { ic: 'cpu' })}

        ${panel('Recorded Extraction Trend', `
          <div id="fc-spark" style="margin-bottom:14px"></div>
          <dl class="deflist">
            ${p.history.slice(-5).reverse().map(h => `
              <div><dt class="mono">${h.label}</dt><dd class="mono">${fmt.n(h.actual)} T
                <span style="color:var(--${h.actual >= h.target ? 'good' : 'crit'});font-size:11px">
                ${h.actual >= h.target ? '+' : ''}${fmt.n(h.actual - h.target)}</span></dd></div>`).join('')}
          </dl>`, { ic: 'clock' })}
      </div>
    </div>`;

  $('#fc-main').innerHTML = forecastChart(p, { w: 1180, h: 340 });
  $('#fc-spark').innerHTML = sparkline(p.history.map(h => h.actual), { w: 380, h: 60, colour: 'var(--s2)' });
}

/* ---------- 5. Risk Analysis ------------------------------------------- */

export function risk(host, s) {
  const snap = s.snapshot, r = snap.risk;

  host.innerHTML = `
    ${head('Game-theoretic attribution', 'Root Cause Diagnostics',
      `Decomposing shortfall risk at ${snap.site.name} into its operational drivers using TreeSHAP feature attribution, so the control room acts on the cause rather than the symptom.`)}

    ${scenarioBar(snap, { compact: true })}

    <section class="callout ${r.shortfall_probability >= 70 ? '' : r.shortfall_probability >= 40 ? 'callout--warn' : 'callout--good'}">
      <span class="callout__icon">${icon('alert')}</span>
      <div class="callout__body">
        <div class="mono tiny" style="letter-spacing:.12em;opacity:.75">ACTIVE SCENARIO SHORTFALL STATUS · ${r.severity}</div>
        <div class="callout__title" style="margin-top:5px">Projected output deficit −${fmt.n(r.deficit_t)} tonnes / day</div>
        <p class="callout__sub">Primary root cause: <b>${r.root_cause}</b></p>
      </div>
      <div class="callout__stats">
        <div class="callout__stat"><b>${r.shortfall_probability}%</b><span>Shortfall prob.</span></div>
        <div class="callout__stat"><b>${fmt.n(r.deficit_t)}</b><span>Deficit gap T</span></div>
        <div class="callout__stat"><b>${fmt.n(r.cumulative_deficit_t)}</b><span>7-day total T</span></div>
      </div>
    </section>

    <div class="grid grid--main">
      ${panel('TreeSHAP Risk Attribution', `
        <div class="grid" style="grid-template-columns:minmax(200px,250px) 1fr;gap:24px;align-items:center">
          <div id="rk-donut"></div>
          <div>${hbars(r.factors)}</div>
        </div>`, {
        ic: 'shield', tag: `<span class="tag tag--info">${r.model.architecture}</span>`, cls: 'panel--raised' })}

      ${panel('Live Telemetry Signals', telemetryList(r.telemetry), {
        ic: 'radio', tag: `<span class="tag tag--good"><span class="dot dot--pulse"></span> Connected</span>` })}
    </div>

    <div class="grid grid--2">
      ${panel('Factor Contribution', `
        <div class="tablewrap">
          <table class="data">
            <thead><tr><th>Risk factor</th><th>SHAP weight</th><th>Value</th><th>Tonnage impact</th></tr></thead>
            <tbody>${r.factors.map(f => `
              <tr>
                <td class="strong"><span class="row" style="gap:8px"><i class="legend__sw" style="background:${f.colour};margin:0"></i>${f.label}</span></td>
                <td class="num">${f.weight_pct}%</td>
                <td class="num mono">${f.shap_value}</td>
                <td class="num" style="color:var(--crit);font-weight:700">−${fmt.n(f.contribution_t)} T</td>
              </tr>`).join('')}</tbody>
          </table>
        </div>`, { ic: 'table', bodyCls: 'panel__body--flush' })}

      ${panel('Scenario Sensitivity', `
        <p class="tiny muted" style="margin-bottom:14px">Shortfall probability under each modelled operating scenario at this site, holding geology and rated capacity constant.</p>
        ${hbars(snap.scenarios.map(x => ({
          label: x.label, weight_pct: x.risk_pct,
          colour: x.risk_pct >= 70 ? 'var(--crit)' : x.risk_pct >= 40 ? 'var(--warn)' : 'var(--good)',
        })))}
        <dl class="deflist" style="margin-top:16px">
          <div><dt>Model base value</dt><dd class="mono">${r.model.base_value}</dd></div>
          <div><dt>Explained variance</dt><dd class="mono" style="color:var(--good)">${r.model.explained_variance}</dd></div>
          <div><dt>Daily planned output</dt><dd class="mono">${fmt.n(r.target)} T</dd></div>
        </dl>`, { ic: 'sliders' })}
    </div>`;

  $('#rk-donut').innerHTML = riskDonut(r.shortfall_probability, r.factors, { size: 240 });
}

/* ---------- 6. Action Centre ------------------------------------------ */

export function actions(host, s) {
  const snap = s.snapshot, plan = snap.plan, sv = plan.solver;

  host.innerHTML = `
    ${head('Constrained optimisation', 'Corrective Action Optimisation',
      `Interventions selected by Mixed Integer Linear Programming to recover the projected deficit at ${snap.site.name} within the crew and shift-hour budget actually available.`)}

    ${scenarioBar(snap, { compact: true })}

    <div class="grid grid--main">
      <div class="stack">
        <div class="row row--between">
          <h2 class="panel__title">${icon('bolt')}Ranked Operational Interventions</h2>
          <span class="tiny muted">Sequenced by recovered tonnage</span>
        </div>
        ${plan.actions.map(a => `
          <article class="action ${a.priority === 1 ? 'action--top' : ''}">
            <div class="action__head">
              <span class="action__pri">PRIORITY ${String(a.priority).padStart(2, '0')}</span>
              <span class="tag tag--${a.impact === 'HIGH' ? 'crit' : a.impact === 'MEDIUM' ? 'warn' : 'plain'}">${a.impact} IMPACT</span>
              <span class="push tiny muted">Feasibility: <b style="color:var(--${a.feasibility === 'HIGH' ? 'good' : a.feasibility === 'MEDIUM' ? 'warn' : 'crit'})">${a.feasibility}</b></span>
            </div>
            <div>
              <h3 class="action__title">${a.title}</h3>
              <p class="action__detail">${a.detail}</p>
            </div>
            <div class="action__grid">
              <div class="action__cell"><span>Recovers</span><b style="color:var(--good)">+${fmt.n(a.recover_t)} T</b></div>
              <div class="action__cell"><span>Yield score</span><b>${a.yield_score}/100</b></div>
              <div class="action__cell"><span>Crew</span><b>${a.crew}</b></div>
              <div class="action__cell"><span>Lead time</span><b>${a.lead_time_hrs} h</b></div>
              <div class="action__cell"><span>Cost / tonne</span><b>₹${fmt.n(a.cost_per_tonne)}</b></div>
            </div>
            <div class="action__foot">
              <div class="meter" style="flex:1;min-width:140px"><div class="meter__fill" style="width:${a.yield_score}%"></div></div>
              <button class="btn btn--primary btn--sm" data-dispatch="${a.title.replace(/"/g, '')}">Dispatch command ${icon('arrow')}</button>
            </div>
          </article>`).join('')}
      </div>

      <div class="stack">
        ${panel('Recovery Potential', `
          <div class="grid" style="grid-template-columns:1fr 1fr;gap:12px;margin-bottom:16px">
            <div style="padding:13px 15px;border-radius:var(--r-md);background:var(--crit-bg)">
              <div class="mono tiny muted">PROJECTED SHORTFALL</div>
              <b style="font-family:var(--ff-display);font-size:26px;color:var(--crit);letter-spacing:-.03em">${fmt.n(plan.deficit_t)} T</b>
              <div class="tiny muted">Unmitigated gap</div>
            </div>
            <div style="padding:13px 15px;border-radius:var(--r-md);background:var(--good-bg)">
              <div class="mono tiny muted">RECOVERABLE</div>
              <b style="font-family:var(--ff-display);font-size:26px;color:var(--good);letter-spacing:-.03em">+${fmt.n(plan.recovered_t)} T</b>
              <div class="tiny muted">${plan.recovery_pct}% restored</div>
            </div>
          </div>
          <div id="ac-gauge" class="center" style="max-width:230px;margin:0 auto"></div>
          <div class="mono tiny muted" style="margin:14px 0 9px">SHORTFALL PROBABILITY REDUCTION</div>
          <div class="metric"><div class="metric__top"><span class="metric__k">Before intervention</span><span class="metric__v" style="color:var(--crit)">${plan.risk_before}%</span></div>
            <div class="meter"><div class="meter__fill" style="width:${plan.risk_before}%;background:var(--crit)"></div></div></div>
          <div class="center" style="padding:11px 0"><span class="tag tag--good">↓ ${plan.risk_reduction_pct} pts via optimised dispatch</span></div>
          <div class="metric"><div class="metric__top"><span class="metric__k">After intervention</span><span class="metric__v" style="color:var(--good)">${plan.risk_after}%</span></div>
            <div class="meter"><div class="meter__fill" style="width:${plan.risk_after}%;background:var(--good)"></div></div></div>`,
          { ic: 'target', cls: 'panel--accent' })}

        ${panel('MILP Solver', `
          <dl class="deflist">
            <div><dt>Method</dt><dd style="font-size:11.5px">${sv.method}</dd></div>
            <div><dt>Objective</dt><dd style="font-size:11.5px">${sv.objective}</dd></div>
            <div><dt>Status</dt><dd><span class="tag tag--good">${sv.status}</span></dd></div>
            <div><dt>Selected</dt><dd class="mono">${sv.selected} of ${sv.candidates} candidates</dd></div>
            <div><dt>Committed cost</dt><dd class="mono">₹${fmt.n(sv.total_cost_inr)}</dd></div>
          </dl>
          <div class="stack stack--sm" style="margin-top:16px">
            <div class="metric">
              <div class="metric__top"><span class="metric__k">Crew utilisation</span><span class="metric__v">${sv.crew_used}/${sv.crew_budget}</span></div>
              <div class="meter"><div class="meter__fill" style="width:${sv.crew_utilisation_pct}%"></div></div>
            </div>
            <div class="metric">
              <div class="metric__top"><span class="metric__k">Shift-hour utilisation</span><span class="metric__v">${sv.hours_used}/${sv.hours_budget} h</span></div>
              <div class="meter"><div class="meter__fill" style="width:${sv.hours_utilisation_pct}%;background:var(--s2)"></div></div>
            </div>
          </div>`, { ic: 'cpu' })}

        ${panel('Operational Decision Pipeline', `
          <div class="pipeline">
            ${plan.pipeline.map(st => `
              <div class="pipestep">
                <span class="pipestep__n">${st.step}</span>
                <div>
                  <div class="row row--between"><span class="pipestep__st">${st.stage}</span>
                    <button class="btn btn--ghost btn--sm" data-goto="${st.link}">View ${icon('arrow')}</button></div>
                  <div class="pipestep__tx">${st.text}</div>
                </div>
              </div>`).join('')}
          </div>`, { ic: 'bolt' })}
      </div>
    </div>`;

  $('#ac-gauge').innerHTML = gauge(plan.recovery_pct, { size: 200, label: 'GAP RESTORED' });
  $$('[data-dispatch]').forEach(b => b.addEventListener('click', () => {
    b.textContent = 'Dispatched';
    b.disabled = true;
    toast(`Command dispatched to ${snap.site.name} control room — ${b.dataset.dispatch}`);
  }));
}

/* ---------- 7. Alert Centre ------------------------------------------- */

export function alerts(host, s) {
  const snap = s.snapshot;
  const critical = snap.alerts.filter(a => a.severity === 'CRITICAL').length;
  const numbers = ['+91-9876543210', '+91-9123456789'];
  const emails = ['controlroom@moil.nic.in', 'shift.engineer@moil.nic.in'];

  host.innerHTML = `
    ${head('Early warning', 'Multi-Channel Alert System',
      `Cellular SMS to the mine controller, email shift briefings carrying the full diagnostic, and in-dashboard push for operators on shift at ${snap.site.name}.`)}

    <div class="grid grid--kpi">
      ${kpiTile({ label: 'Active alerts', value: snap.alerts.length, unit: '', delta: null, sub: 'Current scenario', tone: 'v' })}
      ${kpiTile({ label: 'Critical', value: critical, unit: '', delta: null, sub: 'Immediate escalation', tone: 'crit' })}
      ${kpiTile({ label: 'Channels', value: 3, unit: '', delta: null, sub: 'SMS · email · push', tone: 'good' })}
      ${kpiTile({ label: 'Recipients', value: numbers.length + emails.length, unit: '', delta: null, sub: '控 Control room + supervisors'.replace('控 ', ''), tone: 'v' })}
    </div>

    <div class="grid grid--main">
      <div class="stack">
        ${panel('Active Notification Channels', `
          <div class="stack stack--sm">
            <div class="channel">
              <span class="channel__icon">${icon('phone')}</span>
              <div style="flex:1">
                <div class="channel__t">SMS Direct Cellular Alert <span class="tag tag--warn">FAST PATH</span></div>
                <p class="channel__d">Direct GSM alert to the mine controller and equipment supervisors whenever shortfall probability crosses the critical threshold.</p>
              </div>
              <span class="toggle is-on" role="switch" aria-checked="true" tabindex="0"></span>
            </div>
            <div class="channel">
              <span class="channel__icon">${icon('mail')}</span>
              <div style="flex:1">
                <div class="channel__t">Email Incident &amp; Shift Briefing</div>
                <p class="channel__d">Full diagnostic breakdown: TreeSHAP factor weights, the MILP recovery plan and the attached PDF operations brief.</p>
              </div>
              <span class="toggle is-on" role="switch" aria-checked="true" tabindex="0"></span>
            </div>
            <div class="channel">
              <span class="channel__icon">${icon('bell')}</span>
              <div style="flex:1">
                <div class="channel__t">In-Dashboard Push</div>
                <p class="channel__d">Low-latency updates for operators with the control platform open on shift.</p>
              </div>
              <span class="toggle is-on" role="switch" aria-checked="true" tabindex="0"></span>
            </div>
          </div>

          <div class="grid grid--2" style="margin-top:18px">
            <div>
              <div class="mono tiny muted" style="margin-bottom:9px">${icon('phone')} SMS ALERT NUMBERS (${numbers.length})</div>
              <div class="chiplist" id="al-nums">${numbers.map(n => `<span class="chip">${n}<button aria-label="Remove ${n}">${icon('x')}</button></span>`).join('')}</div>
              <div class="field" style="margin-top:10px"><input id="al-num-in" placeholder="+91 98765 43210" aria-label="Add SMS number"/><button class="btn btn--ghost btn--sm" id="al-num-add">Add</button></div>
            </div>
            <div>
              <div class="mono tiny muted" style="margin-bottom:9px">${icon('mail')} EMAIL BRIEFING LIST (${emails.length})</div>
              <div class="chiplist" id="al-mails">${emails.map(n => `<span class="chip">${n}<button aria-label="Remove ${n}">${icon('x')}</button></span>`).join('')}</div>
              <div class="field" style="margin-top:10px"><input id="al-mail-in" placeholder="supervisor@moil.nic.in" aria-label="Add email"/><button class="btn btn--ghost btn--sm" id="al-mail-add">Add</button></div>
            </div>
          </div>`, { ic: 'radio', tag: `<span class="tag tag--good">3 channels operational</span>` })}

        ${panel('Incident Escalation Log', `
          <div>${snap.alerts.map(a => `
            <div class="alertrow alertrow--${a.severity}">
              <span class="alertrow__sev"></span>
              <div>
                <div class="row" style="gap:8px;margin-bottom:4px">
                  <span class="tag tag--${a.severity === 'CRITICAL' ? 'crit' : a.severity === 'WARNING' ? 'warn' : 'info'}">${a.severity}</span>
                  <span class="mono tiny muted">${a.category}</span>
                  <span class="mono tiny muted">${a.id}</span>
                </div>
                <div class="alertrow__msg">${a.message}</div>
                <div class="alertrow__act">↳ ${a.corrective_action}</div>
              </div>
              <span class="alertrow__t">${a.timestamp}</span>
            </div>`).join('')}</div>`,
          { ic: 'bell', bodyCls: 'panel__body--flush', tag: `<span class="tag tag--good"><span class="dot dot--pulse"></span> Live</span>` })}
      </div>

      <div class="stack">
        ${panel('Cellular Broadcast Preview', `
          <div class="phone">
            <div class="phone__bar"><span>09:41</span><span class="phone__notch"></span><span>5G 100%</span></div>
            <div class="row row--between">
              <span class="row" style="gap:9px">
                <span class="mark" style="width:32px;height:32px;font-size:14px;border-radius:9px">M</span>
                <span><b style="font-size:12.5px;display:block">MOIL-ALERT (SMS)</b><span class="mono tiny muted">Connected · high priority</span></span>
              </span>
              <button class="btn btn--primary btn--sm" id="al-sim">Simulate</button>
            </div>
            <div id="al-sms">
              <div class="sms">
                <div class="row row--between"><span class="sms__from">MOIL-ALERT</span><span class="sms__time">just now</span></div>
                <p class="sms__body">[CRITICAL] ${snap.site.name}: ${snap.risk.root_cause}. Shortfall gap ${fmt.n(snap.risk.deficit_t)} T expected (${snap.risk.shortfall_probability}% prob). Priority action: ${snap.plan.actions[0]?.title || 'review action centre'}.</p>
              </div>
            </div>
            <div class="mono tiny muted center">Cellular broadcast emulator · instant trigger</div>
          </div>`, { ic: 'phone' })}

        ${panel('Escalation Thresholds', `
          <div class="stack">
            <div class="metric"><div class="metric__top"><span class="metric__k">SMS trigger</span><span class="metric__v" style="color:var(--crit)">≥ 70%</span></div>
              <div class="meter"><div class="meter__fill" style="width:70%;background:var(--crit)"></div></div></div>
            <div class="metric"><div class="metric__top"><span class="metric__k">Email briefing</span><span class="metric__v" style="color:var(--warn)">≥ 40%</span></div>
              <div class="meter"><div class="meter__fill" style="width:40%;background:var(--warn)"></div></div></div>
            <div class="metric"><div class="metric__top"><span class="metric__k">Dashboard push</span><span class="metric__v" style="color:var(--info)">≥ 20%</span></div>
              <div class="meter"><div class="meter__fill" style="width:20%;background:var(--info)"></div></div></div>
          </div>
          <div class="callout ${snap.risk.shortfall_probability >= 70 ? '' : 'callout--warn'}" style="margin-top:16px;padding:14px 16px">
            <div class="callout__body">
              <div class="mono tiny" style="letter-spacing:.1em">CURRENT STATE</div>
              <div style="font-size:13px;margin-top:5px">Shortfall probability <b>${snap.risk.shortfall_probability}%</b> — ${snap.risk.shortfall_probability >= 70 ? 'all three channels firing' : snap.risk.shortfall_probability >= 40 ? 'email and push firing' : 'push only'}.</div>
            </div>
          </div>`, { ic: 'sliders' })}
      </div>
    </div>`;

  const chipAdd = (listSel, inputSel, btnSel, validate) => {
    const list = $(listSel), input = $(inputSel);
    const bind = () => $$('button', list).forEach(b => b.onclick = () => b.parentElement.remove());
    bind();
    $(btnSel).addEventListener('click', () => {
      const v = input.value.trim();
      if (!v || !validate(v)) { toast('Enter a valid recipient', 'alert'); return; }
      list.insertAdjacentHTML('beforeend', `<span class="chip">${v}<button aria-label="Remove ${v}">${icon('x')}</button></span>`);
      input.value = ''; bind(); toast(`${v} added to the alert list`);
    });
    input.addEventListener('keydown', e => { if (e.key === 'Enter') $(btnSel).click(); });
  };
  chipAdd('#al-nums', '#al-num-in', '#al-num-add', v => /[0-9]{6,}/.test(v.replace(/\D/g, '')));
  chipAdd('#al-mails', '#al-mail-in', '#al-mail-add', v => /^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(v));

  $$('.toggle').forEach(t => {
    const flip = () => {
      t.classList.toggle('is-on');
      t.setAttribute('aria-checked', t.classList.contains('is-on'));
    };
    t.addEventListener('click', flip);
    t.addEventListener('keydown', e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); flip(); } });
  });

  $('#al-sim').addEventListener('click', () => {
    const a = snap.alerts[Math.floor(Math.random() * snap.alerts.length)];
    $('#al-sms').insertAdjacentHTML('afterbegin', `
      <div class="sms rise" style="margin-bottom:9px">
        <div class="row row--between"><span class="sms__from">MOIL-ALERT</span><span class="sms__time">just now</span></div>
        <p class="sms__body">[${a.severity}] ${snap.site.name}: ${a.message}</p>
      </div>`);
    toast('SMS broadcast simulated to 2 recipients', 'phone');
  });
}

/* ---------- 8. ROI ----------------------------------------------------- */

export function roi(host, s) {
  const snap = s.snapshot, r = snap.roi, h = r.headline, a = r.assumptions;

  host.innerHTML = `
    ${head('Value realisation', 'ROI &amp; Cost-Benefit Intelligence',
      `What the platform is worth at ${snap.site.name} under the ${snap.scenario.label.toLowerCase()} scenario — derived from the MILP recovered tonnage, not asserted.`)}

    <section class="panel panel--accent">
      <div class="panel__body">
        <div class="row" style="gap:10px;margin-bottom:14px">
          <span class="tag tag--good">Pilot validated</span>
          <span class="tag">${snap.site.name}, ${snap.site.district || fmt.title(snap.site.state)}</span>
          <span class="tag tag--info">${snap.scenario.label}</span>
        </div>
        <h2 style="font-size:clamp(20px,2.3vw,28px);max-width:34ch">From “what AI can do” to what it demonstrably recovers in a working mine</h2>
        <p class="muted" style="margin-top:11px;max-width:76ch">
          Calibrated against the ${fmt.title(snap.site.hostrock)} host lithology, ${snap.reserve.model.assay_logs} linked drill logs and
          Sentinel-2 band ratios over ${snap.site.name}. Financials follow ${a.basis}.
          Production value flows straight from the ${fmt.n(snap.plan.recovered_t)} T/day the solver recovers, so every figure below
          moves when the scenario changes.
        </p>
      </div>
      <div class="panel__foot">
        <div class="row" style="gap:26px">
          <span><span class="mono tiny muted">MODEL ROC-AUC</span><br/><b style="font-size:18px;color:var(--good)">${snap.reserve.model.roc_auc}</b></span>
          <span><span class="mono tiny muted">RECOVERY RATE</span><br/><b style="font-size:18px;color:var(--s2)">${h.recovery_rate_pct}%</b></span>
          <span><span class="mono tiny muted">PAYBACK</span><br/><b style="font-size:18px">${h.payback_months} months</b></span>
          <span><span class="mono tiny muted">BENEFIT : COST</span><br/><b style="font-size:18px">${h.benefit_cost_ratio}×</b></span>
          <span class="push"><button class="btn btn--primary" data-goto="reports">${icon('down')} Export full brief</button></span>
        </div>
      </div>
    </section>

    <div class="grid grid--kpi">
      ${kpiTile({ label: 'Estimated annual value', value: `₹${h.annual_value_cr}`, unit: 'Cr', delta: null, sub: 'Single-mine realisation', tone: 'good' })}
      ${kpiTile({ label: 'Production recovered', value: fmt.n(h.production_recovered_t), unit: 'T/yr', delta: null, sub: `${a.disruption_days} disrupted days`, tone: 'v' })}
      ${kpiTile({ label: 'Fuel & haulage saved', value: fmt.n(h.fuel_saved_l), unit: 'L/yr', delta: null, sub: `@ ₹${a.diesel_inr_l}/L diesel`, tone: 'warn' })}
      ${kpiTile({ label: 'Drilling avoided', value: `₹${h.drilling_avoided_lakh}`, unit: 'lakh', delta: null, sub: `@ ₹${fmt.n(a.core_drilling_inr_m)}/m core`, tone: 'v' })}
      ${kpiTile({ label: 'Net margin lift', value: h.margin_lift_pct, unit: '%', delta: null, sub: 'On recovered output', tone: 'good' })}
    </div>

    <div class="grid grid--main">
      ${panel('Annual Value Breakdown', `
        ${shareBar(r.pillars)}
        <div class="tablewrap" style="margin-top:18px">
          <table class="data">
            <thead><tr><th>Value pillar</th><th>Physical metric</th><th>Basis</th><th>Value</th><th>Share</th></tr></thead>
            <tbody>
              ${r.pillars.map(p => `
                <tr>
                  <td class="strong"><span class="row" style="gap:8px"><i class="legend__sw" style="background:${p.colour};margin:0"></i>${p.label}</span></td>
                  <td class="mono tiny">${p.metric}</td>
                  <td class="tiny muted">${p.note}</td>
                  <td class="num strong">₹${p.value_cr} Cr</td>
                  <td class="num">${p.share_pct}%</td>
                </tr>`).join('')}
              <tr style="background:var(--wash)">
                <td class="strong">TOTAL</td><td></td><td></td>
                <td class="num strong" style="color:var(--good)">₹${r.total_cr} Cr</td>
                <td class="num strong">100%</td>
              </tr>
            </tbody>
          </table>
        </div>`, { ic: 'rupee', cls: 'panel--raised', bodyCls: '' })}

      <div class="stack">
        ${panel('Enterprise Rollout', `
          <div class="row row--between" style="margin-bottom:14px">
            <div><div class="mono tiny muted">MOIL OPERATING BASE</div><b style="font-size:22px">${r.enterprise.mines} mines</b></div>
            <div style="text-align:right"><div class="mono tiny muted">COMBINED VALUE</div><b style="font-size:22px;color:var(--good)">₹${r.enterprise.combined_value_cr} Cr</b></div>
          </div>
          <p class="tiny muted" style="margin-bottom:16px">${fmt.n(r.enterprise.combined_tpd)} T/day combined rated capacity across the Sausar and Balaghat belts.</p>
          ${r.enterprise.rollout_phases.map(p => `
            <div class="phase phase--${p.status}">
              <span class="phase__mark"></span>
              <div>
                <div class="row row--between">
                  <span class="phase__w">${p.phase} · ${p.window}</span>
                  <span class="tag tag--${p.status === 'complete' ? 'good' : p.status === 'active' ? 'info' : 'plain'}">${p.status}</span>
                </div>
                <div class="phase__t">${p.title}</div>
                <p class="phase__s">${p.scope}</p>
                <div class="mono tiny" style="margin-top:7px;color:var(--violet-hi)">₹${p.value_cr} Cr cumulative value</div>
              </div>
            </div>`).join('')}`, { ic: 'building' })}

        ${panel('Model Assumptions', `
          <dl class="deflist">
            <div><dt>Mn ore realisation</dt><dd class="mono">₹${fmt.n(a.mn_ore_realisation_inr_t)}/T</dd></div>
            <div><dt>Diesel</dt><dd class="mono">₹${a.diesel_inr_l}/L</dd></div>
            <div><dt>Diamond core drilling</dt><dd class="mono">₹${fmt.n(a.core_drilling_inr_m)}/m</dd></div>
            <div><dt>Working days</dt><dd class="mono">${a.working_days}/yr</dd></div>
            <div><dt>Modelled disruption days</dt><dd class="mono">${a.disruption_days}/yr</dd></div>
            <div><dt>Platform deployment cost</dt><dd class="mono">₹${(a.platform_cost_inr / 1e7).toFixed(2)} Cr/mine</dd></div>
            <div><dt>Cost basis</dt><dd style="font-size:11.5px">${a.basis}</dd></div>
          </dl>
          <p class="tiny muted" style="margin-top:14px">These are decision-support estimates, not a statutory reserve or financial statement.</p>`,
          { ic: 'sliders' })}
      </div>
    </div>`;
}

/* ---------- 9. Enterprise portfolio ------------------------------------ */

export async function enterprise(host, s) {
  const operating = allSites(s.registry).filter(x => x.tier === 'operating');
  const ids = operating.map(x => x.id);

  host.innerHTML = `
    ${head('Multi-mine control plane', 'Enterprise Portfolio',
      `Every MOIL operating mine scored on the same models under the ${s.snapshot.scenario.label.toLowerCase()} scenario, so planners can see where the next tonne is most at risk.`)}
    <div class="empty">${icon('building')}<p>Scoring ${ids.length} operating mines…</p></div>`;

  const { rows } = await api.compare(ids, s.scenario);
  rows.sort((a, b) => b.risk_pct - a.risk_pct);

  const totalValue = rows.reduce((a, r) => a + r.roi_cr, 0);
  const totalTpd = rows.reduce((a, r) => a + r.target_t, 0);
  const totalDeficit = rows.reduce((a, r) => a + r.deficit_t, 0);
  const totalIndicated = rows.reduce((a, r) => a + r.indicated_t, 0);
  const atRisk = rows.filter(r => r.risk_pct >= 70).length;

  host.innerHTML = `
    ${head('Multi-mine control plane', 'Enterprise Portfolio',
      `Every MOIL operating mine scored on the same models under the ${s.snapshot.scenario.label.toLowerCase()} scenario, so planners can see where the next tonne is most at risk.`)}

    ${scenarioBar(s.snapshot, { compact: true })}

    <div class="grid grid--kpi">
      ${kpiTile({ label: 'Operating mines', value: rows.length, unit: '', delta: null, sub: 'Sausar + Balaghat belts', tone: 'v' })}
      ${kpiTile({ label: 'Combined capacity', value: fmt.n(totalTpd), unit: 'T/day', delta: null, sub: 'Rated output', tone: 'v' })}
      ${kpiTile({ label: 'Mines at high risk', value: atRisk, unit: `of ${rows.length}`, delta: null, sub: '≥70% shortfall probability', tone: 'crit' })}
      ${kpiTile({ label: 'Portfolio deficit', value: fmt.n(totalDeficit), unit: 'T/day', delta: null, sub: 'Unmitigated across the base', tone: 'crit' })}
      ${kpiTile({ label: 'Indicated reserve', value: (totalIndicated / 1e6).toFixed(1), unit: 'Mt', delta: null, sub: 'All modelled sectors', tone: 'good' })}
      ${kpiTile({ label: 'Portfolio value', value: `₹${totalValue.toFixed(1)}`, unit: 'Cr', delta: null, sub: 'Annual realisation', tone: 'good' })}
    </div>

    ${panel('Modelled Annual Value by Mine', `<div id="ent-cols"></div>
      <div class="chart__legend" style="margin-top:10px">
        <span><i style="background:var(--crit)"></i>Shortfall risk ≥70%</span>
        <span><i style="background:var(--warn)"></i>40–70%</span>
        <span><i style="background:var(--good)"></i>Below 40%</span>
      </div>`, {
      ic: 'trend', cls: 'panel--raised',
      sub: 'Value scales with rated capacity and the deficit each mine carries under this scenario' })}

    ${panel('Mine-by-Mine Comparison', `
      <div class="tablewrap">
        <table class="data">
          <thead><tr><th>Mine</th><th>Belt / state</th><th>Rated</th><th>Shortfall risk</th><th>Deficit</th><th>Mn grade</th><th>Indicated</th><th>Annual value</th><th></th></tr></thead>
          <tbody>${rows.map(r => `
            <tr class="is-click" data-id="${r.id}">
              <td class="strong">${r.name}${r.id === s.site ? ' <span class="tag tag--info">active</span>' : ''}</td>
              <td class="tiny muted">${fmt.title(r.belt)}<span class="sub">${fmt.title(r.state)}</span></td>
              <td class="num">${fmt.n(r.target_t)} T</td>
              <td class="num"><span class="tag tag--${r.risk_pct >= 70 ? 'crit' : r.risk_pct >= 40 ? 'warn' : 'good'}">${r.risk_pct}%</span></td>
              <td class="num" style="color:var(--crit)">−${fmt.n(r.deficit_t)} T</td>
              <td class="num">${r.grade_pct}%</td>
              <td class="num">${(r.indicated_t / 1e6).toFixed(2)} Mt</td>
              <td class="num strong">₹${r.roi_cr} Cr</td>
              <td><span class="tiny" style="color:var(--violet-hi)">Select ${icon('arrow')}</span></td>
            </tr>`).join('')}</tbody>
        </table>
      </div>`, { ic: 'table', bodyCls: 'panel__body--flush' })}`;

  $('#ent-cols').innerHTML = columns(rows, { w: 1080, h: 300 });
  $$('#view tbody tr[data-id]').forEach(tr => tr.addEventListener('click', () => store.setSite(tr.dataset.id)));
}

/* ---------- 10. Reports ------------------------------------------------ */

export function reports(host, s) {
  const snap = s.snapshot;
  const live = typeof api.reportURL(  'brief.pdf', s.site, s.scenario) === 'string';
  const url = (k) => api.reportURL(k, s.site, s.scenario) || '#reports';

  /* Client-side fallbacks so CSV and JSON still work with no backend. */
  const blobLink = (label, kind) =>
    `<button class="btn btn--ghost btn--sm" data-blob="${kind}">${icon('table')} ${label}</button>`;

  host.innerHTML = `
    ${head('Exports', 'Reports &amp; Data Exports',
      `Every export is generated from the same snapshot the dashboard is showing, so a printed brief and the screen never disagree.`)}

    <div class="grid grid--main">
      <div class="stack">
        ${panel('Operations &amp; Reserve Intelligence Brief', `
          <div class="row" style="gap:20px;align-items:flex-start;flex-wrap:wrap">
            <div style="flex:1;min-width:260px">
              <p style="font-size:13.5px;line-height:1.6">A seven-section A4 brief for the mine controller and planning cell, built with vector charts and typeset tables — no screenshots.</p>
              <ol class="stack stack--sm mono tiny" style="margin:16px 0 0;padding-left:20px;color:var(--muted);line-height:1.9">
                <li>Executive summary &amp; site identity</li>
                <li>Production continuity forecast with quantile bands</li>
                <li>Root-cause diagnostics &amp; telemetry envelope</li>
                <li>Reserve intelligence — sectors and drill assay register</li>
                <li>Recommended corrective actions with MILP solver report</li>
                <li>Value realisation &amp; enterprise rollout roadmap</li>
                <li>Nearest occurrences from the GSI register</li>
              </ol>
            </div>
            <div style="width:190px;flex:none;border-radius:var(--r-md);overflow:hidden;border:1px solid var(--hairline-2);background:#fff;padding:14px;box-shadow:var(--shadow-2)">
              <div style="height:5px;background:#0B0714;margin:-14px -14px 12px;position:relative">
                <span style="position:absolute;inset:0 auto 0 0;width:38%;background:#7026FB"></span>
              </div>
              <div style="font:700 6px/1.4 system-ui;color:#7026FB;letter-spacing:.08em">OPERATIONS BRIEF</div>
              <div style="font:800 13px/1.1 system-ui;color:#0B0714;margin:3px 0 4px">${snap.site.name}</div>
              <div style="font:400 5.5px/1.4 system-ui;color:#6B6580">${fmt.title(snap.site.belt)} · ${snap.site.toposheet}</div>
              <div style="display:flex;gap:4px;margin:9px 0 8px">
                ${['DAILY TARGET', 'RISK', 'DEFICIT'].map((l, i) => `
                  <div style="flex:1;background:#F6F3FE;border-bottom:1.5px solid #7026FB;padding:5px 4px">
                    <div style="font:700 3.6px/1 system-ui;color:#6B6580">${l}</div>
                    <div style="font:800 7px/1.2 system-ui;color:#0B0714;margin-top:2px">${[fmt.n(snap.production.target), snap.risk.shortfall_probability + '%', fmt.n(snap.risk.deficit_t)][i]}</div>
                  </div>`).join('')}
              </div>
              ${Array.from({ length: 6 }, (_, i) => `<div style="height:2px;background:#E4E0EC;margin-bottom:3.5px;width:${[100, 96, 88, 100, 72, 92][i]}%"></div>`).join('')}
              <div style="height:26px;background:linear-gradient(90deg,#EFEBF9,#7026FB33);margin:7px 0;border-radius:2px"></div>
              ${Array.from({ length: 3 }, (_, i) => `<div style="height:2px;background:#E4E0EC;margin-bottom:3.5px;width:${[94, 100, 66][i]}%"></div>`).join('')}
            </div>
          </div>`, {
          ic: 'file', cls: 'panel--accent',
          tag: `<span class="tag">A4 · 6 pages</span>`,
          foot: live
            ? `<div class="row" style="gap:10px">
                 <a class="btn btn--primary" href="${url('brief.pdf')}" download>${icon('down')} Download PDF brief</a>
                 <span class="tiny muted">${snap.site.name} · ${snap.scenario.label} · generated on request</span>
               </div>`
            : `<div class="row" style="gap:10px">
                 <span class="tag tag--warn">Static preview</span>
                 <span class="tiny muted">The PDF is rendered by the platform's ReportLab service —
                 run <code class="mono">python run.py</code> and open the Reports screen to generate it.
                 The CSV and JSON exports below work here.</span>
               </div>` })}

        <div class="grid grid--2">
          ${panel('Analytics Extract (CSV)', `
            <p class="tiny muted" style="line-height:1.7">Six labelled sections in one flat file: the 21-day production series, target sectors, the drill assay register, TreeSHAP attribution, MILP actions and the value breakdown. Opens straight in Excel.</p>`, {
            ic: 'table',
            foot: live ? `<a class="btn btn--ghost btn--sm" href="${url('data.csv')}" download>${icon('down')} Download CSV</a>`
                       : blobLink('Preview & copy CSV', 'csv') })}

          ${panel('Full Snapshot (JSON)', `
            <p class="tiny muted" style="line-height:1.7">The complete analytical state — site register entry, geology, every model output and the alert feed — for ingestion into MOIL's ERP, statutory reporting or a downstream notebook.</p>`, {
            ic: 'db',
            foot: live ? `<a class="btn btn--ghost btn--sm" href="${url('data.json')}" download>${icon('down')} Download JSON</a>`
                       : blobLink('Preview & copy JSON', 'json') })}
        </div>

        ${panel('API Endpoints', `
          <div class="tablewrap">
            <table class="data">
              <thead><tr><th>Endpoint</th><th>Returns</th></tr></thead>
              <tbody>
                ${[
                  ['GET /api/sites', 'Full occurrence register with filters'],
                  ['GET /api/sites/belts', 'Register grouped by metallogenic belt'],
                  ['GET /api/sites/geojson', 'Register as a GeoJSON FeatureCollection'],
                  ['GET /api/analytics/snapshot', 'Everything the dashboard renders, for one site + scenario'],
                  ['GET /api/analytics/reserve', 'Target sectors, drill assays, model quality'],
                  ['GET /api/analytics/production', 'History + forecast with quantile bands'],
                  ['GET /api/analytics/risk', 'Shortfall probability + TreeSHAP attribution'],
                  ['GET /api/analytics/actions', 'MILP corrective-action plan'],
                  ['GET /api/analytics/roi', 'Value realisation model'],
                  ['GET /api/analytics/compare', 'Side-by-side scoring across mines'],
                  ['GET /api/report/brief.pdf', 'This operations brief'],
                  ['WS  /ws/telemetry', '1 Hz fleet, equipment and weather telemetry'],
                ].map(([e, d]) => `<tr><td class="mono tiny strong">${e}</td><td class="tiny muted">${d}</td></tr>`).join('')}
              </tbody>
            </table>
          </div>`, { ic: 'cpu', bodyCls: 'panel__body--flush',
            foot: live ? `<a class="btn btn--ghost btn--sm" href="/docs" target="_blank" rel="noopener">Open interactive API docs ${icon('arrow')}</a>`
                       : `<span class="tiny muted">Interactive OpenAPI docs are served at <code class="mono">/docs</code> when the platform is running.</span>` })}
      </div>

      <div class="stack">
        ${panel('Report Scope', `
          <dl class="deflist">
            <div><dt>Site</dt><dd>${snap.site.name}</dd></div>
            <div><dt>Belt</dt><dd>${fmt.title(snap.site.belt)}</dd></div>
            <div><dt>Toposheet</dt><dd class="mono">${snap.site.toposheet}</dd></div>
            <div><dt>Coordinates</dt><dd class="mono">${fmt.dms(snap.site.lat, 'lat')} ${fmt.dms(snap.site.lon, 'lon')}</dd></div>
            <div><dt>Scenario</dt><dd>${snap.scenario.label}</dd></div>
            <div><dt>Daily target</dt><dd class="mono">${fmt.n(snap.production.target)} T</dd></div>
            <div><dt>Shortfall risk</dt><dd><span class="tag tag--${snap.risk.shortfall_probability >= 70 ? 'crit' : 'warn'}">${snap.risk.shortfall_probability}%</span></dd></div>
            <div><dt>Sectors modelled</dt><dd class="mono">${snap.reserve.zones.length}</dd></div>
            <div><dt>Drill logs</dt><dd class="mono">${snap.reserve.drill_holes.length}</dd></div>
            <div><dt>Actions selected</dt><dd class="mono">${snap.plan.actions.length}</dd></div>
            <div><dt>Snapshot taken</dt><dd class="mono tiny">${new Date(snap.generated_at).toLocaleString('en-IN')}</dd></div>
          </dl>
          <p class="tiny muted" style="margin-top:14px">Change the site or scenario in the top bar and every export regenerates against the new state.</p>`,
          { ic: 'target' })}

        ${panel('Nearest Occurrences', `
          <div class="stack stack--sm">
            ${snap.nearby.map(n => `
              <button class="optrow" data-id="${n.id}" type="button">
                <span class="optrow__dot" style="background:var(--violet-hi)"></span>
                <span style="min-width:0">
                  <span class="optrow__n">${n.display}</span>
                  <span class="optrow__m">${fmt.title(n.hostrock)}</span>
                </span>
                <span class="optrow__r mono muted">${n.distance_km} km</span>
              </button>`).join('')}
          </div>
          <p class="tiny muted" style="margin-top:12px">Great-circle distance from ${snap.site.name}, from the GSI register.</p>`,
          { ic: 'compass' })}
      </div>
    </div>`;

  $$('#view .optrow[data-id]').forEach(b => b.addEventListener('click', () => store.setSite(b.dataset.id)));
  $$('#view a[download]').forEach(a => a.addEventListener('click', () => toast('Generating export…', 'down')));

  $$('#view [data-blob]').forEach(b => b.addEventListener('click', () => {
    const kind = b.dataset.blob;
    const body = kind === 'json' ? JSON.stringify(snap, null, 2) : snapshotToCSV(snap);
    const name = `mangenesis-${snap.site.id}-${snap.scenario.id}.${kind}`;
    const panel = b.closest('.panel');
    let box = panel.querySelector('.exportbox');
    if (box) { box.remove(); return; }
    box = el(`<div class="exportbox">
      <div class="row row--between" style="margin-bottom:9px">
        <span class="mono tiny muted">${name} · ${(body.length / 1024).toFixed(1)} KB</span>
        <button class="btn btn--ghost btn--sm" data-copy>Copy to clipboard</button>
      </div>
      <pre class="exportbox__pre"></pre>
    </div>`);
    box.querySelector('pre').textContent = body;
    panel.querySelector('.panel__body').appendChild(box);
    box.querySelector('[data-copy]').addEventListener('click', async () => {
      try {
        await navigator.clipboard.writeText(body);
        toast(`${kind.toUpperCase()} export copied — paste into a file named ${name}`, 'check');
      } catch {
        const r = document.createRange();
        r.selectNodeContents(box.querySelector('pre'));
        const sel = window.getSelection(); sel.removeAllRanges(); sel.addRange(r);
        toast('Export selected — press Ctrl/Cmd+C to copy', 'file');
      }
    });
  }));
}

/* Mirrors the server's /api/report/data.csv layout, so the two exports
   are interchangeable. */
function snapshotToCSV(snap) {
  const q = (v) => (/[",\n]/.test(String(v)) ? `"${String(v).replace(/"/g, '""')}"` : String(v));
  const rows = [];
  const push = (...cells) => rows.push(cells.map(q).join(','));

  push('MANGENESIS — Manganese Reserve & Production Continuity Extract');
  push('Generated', snap.generated_at);
  push('Site', snap.site.name, 'Belt', snap.site.belt, 'State', snap.site.state);
  push('Latitude', snap.site.lat, 'Longitude', snap.site.lon, 'Toposheet', snap.site.toposheet);
  push('Host rock', snap.site.hostrock, 'Formation', snap.site.formation, 'Morphogenesis', snap.site.morphogenesis);
  push('Scenario', snap.scenario.label, 'Root cause', snap.scenario.root_cause);
  push('');

  push('SECTION', 'PRODUCTION SERIES');
  push('date', 'label', 'series', 'tonnes', 'lower', 'upper', 'target');
  snap.production.history.forEach(h => push(h.date, h.label, 'actual', h.actual, '', '', h.target));
  snap.production.forecast.forEach(f => push(f.date, f.label, 'forecast', f.forecast, f.lower, f.upper, f.target));
  push('');

  push('SECTION', 'RESERVE ZONES');
  push('zone_id', 'name', 'probability_pct', 'class', 'mn_grade_pct', 'tonnage_t', 'strike_length_m', 'avg_width_m', 'depth_extent_m', 'lat', 'lon');
  snap.reserve.zones.forEach(z => push(z.id, z.name, z.probability_pct, z.class, z.mn_grade_pct, z.tonnage_t, z.strike_length_m, z.avg_width_m, z.depth_extent_m, z.centroid[0], z.centroid[1]));
  push('');

  push('SECTION', 'DRILL HOLES');
  push('hole_id', 'lat', 'lon', 'depth_m', 'mn_pct', 'fe_pct', 'sio2_pct', 'p_pct', 'intercept_m', 'zone', 'lithology', 'status');
  snap.reserve.drill_holes.forEach(d => push(d.hole_id, d.lat, d.lon, d.depth_m, d.mn_grade_pct, d.fe_pct, d.sio2_pct, d.p_pct, d.intercept_m, d.zone, d.lithology, d.status));
  push('');

  push('SECTION', 'RISK ATTRIBUTION (TreeSHAP)');
  push('factor', 'weight_pct', 'shap_value', 'contribution_t');
  snap.risk.factors.forEach(f => push(f.label, f.weight_pct, f.shap_value, f.contribution_t));
  push('');

  push('SECTION', 'CORRECTIVE ACTIONS (MILP)');
  push('priority', 'action', 'recover_t', 'yield_score', 'feasibility', 'crew', 'lead_time_hrs', 'cost_inr', 'cost_per_tonne');
  snap.plan.actions.forEach(a => push(a.priority, a.title, a.recover_t, a.yield_score, a.feasibility, a.crew, a.lead_time_hrs, a.cost_inr, a.cost_per_tonne));
  push('');

  push('SECTION', 'VALUE REALISATION');
  push('pillar', 'metric', 'value_inr', 'value_cr', 'share_pct');
  snap.roi.pillars.forEach(p => push(p.label, p.metric, Math.round(p.value_inr), p.value_cr, p.share_pct));
  push('TOTAL', '', Math.round(snap.roi.total_inr), snap.roi.total_cr, 100);
  return rows.join('\n');
}

/* ---------- 11. Data register ----------------------------------------- */

export function register(host, s) {
  const stats = s.registry.stats;

  host.innerHTML = `
    ${head('Source data', 'Occurrence Data Register',
      `The GSI manganese occurrence table exactly as supplied, extended with MOIL's operating-mine portfolio. This is the ground truth every model in the platform is built on.`)}

    <div class="grid grid--kpi">
      ${kpiTile({ label: 'Total records', value: stats.total_sites, unit: '', delta: null, sub: 'Localities', tone: 'v' })}
      ${kpiTile({ label: 'Metallogenic belts', value: stats.belts, unit: '', delta: null, sub: 'Across India', tone: 'v' })}
      ${kpiTile({ label: 'States', value: stats.states, unit: '', delta: null, sub: 'Represented', tone: 'v' })}
      ${kpiTile({ label: 'Host lithologies', value: stats.host_lithologies, unit: '', delta: null, sub: 'Distinct hosts', tone: 'good' })}
      ${kpiTile({ label: 'Rated capacity', value: fmt.n(stats.combined_rated_tpd), unit: 'T/day', delta: null, sub: `${stats.operating_mines} operating mines`, tone: 'good' })}
    </div>

    <div class="grid grid--2">
      ${panel('How the Register Drives the Models', `
        <div class="pipeline">
          <div class="pipestep"><span class="pipestep__n">01</span><div>
            <div class="pipestep__st">HOST LITHOLOGY</div>
            <div class="pipestep__tx">Each host rock carries a Mn grade window and a continuity factor — gondite runs 42–48.5% Mn with high lateral persistence, khondalite 24–34%. These set the reserve model's prior before any satellite data is fused in.</div></div></div>
          <div class="pipestep"><span class="pipestep__n">02</span><div>
            <div class="pipestep__st">MORPHOGENESIS</div>
            <div class="pipestep__tx">Bedded-concordant bodies are structurally predictable and score a 1.12× multiplier; supergene-enriched laterite caps are erratic and score 0.86×.</div></div></div>
          <div class="pipestep"><span class="pipestep__n">03</span><div>
            <div class="pipestep__st">BELT &amp; COORDINATES</div>
            <div class="pipestep__tx">The metallogenic belt fixes regional strike, so modelled sectors follow the real structural grain; latitude and longitude drive the monsoon, NDVI and land-surface-temperature climatology behind the weather risk factor.</div></div></div>
          <div class="pipestep"><span class="pipestep__n">04</span><div>
            <div class="pipestep__st">RATED CAPACITY</div>
            <div class="pipestep__tx">For MOIL's operating mines the published rated output sets the daily target — the denominator of every shortfall figure on the platform.</div></div></div>
        </div>`, { ic: 'cpu' })}

      ${panel('Belt Composition', `
        <div class="stack stack--sm">
          ${s.registry.belts.map(b => `
            <div class="metric">
              <div class="metric__top">
                <span class="metric__k"><span class="row" style="gap:8px"><i class="legend__sw" style="background:${b.colour};margin:0"></i>${fmt.title(b.belt)}</span></span>
                <span class="metric__v">${b.count}</span>
              </div>
              <div class="meter"><div class="meter__fill" style="width:${b.count / stats.total_sites * 100 * 3}%;background:${b.colour}"></div></div>
              <span class="tiny muted">${b.states.map(fmt.title).join(' · ')}</span>
            </div>`).join('')}
        </div>`, { ic: 'layers' })}
    </div>

    ${panel('Complete Occurrence Table', `
      <div class="row" style="padding:12px 18px;border-bottom:1px solid var(--hairline)">
        <input class="pop__search" id="rg-q" style="max-width:340px" type="search" placeholder="Filter records…" aria-label="Filter records"/>
        <span class="push tiny muted" id="rg-count"></span>
      </div>
      <div class="tablewrap">
        <table class="data" id="rg-table">
          <thead><tr>
            <th>Metallogenesis</th><th>Locality</th><th>State</th><th>Toposheet</th>
            <th>Lat (DD)</th><th>Lon (DD)</th><th>Commodity</th>
            <th>Host rock</th><th>Morphogenesis</th><th>Formation</th><th>Source</th>
          </tr></thead>
          <tbody></tbody>
        </table>
      </div>`, { ic: 'db', bodyCls: 'panel__body--flush' })}`;

  api.sites().then(({ sites }) => {
    const tb = $('#rg-table tbody'), count = $('#rg-count');
    const draw = (q = '') => {
      const rows = sites.filter(r => !q || `${r.display} ${r.belt} ${r.state} ${r.hostrock} ${r.formation} ${r.morphogenesis}`.toLowerCase().includes(q.toLowerCase()));
      count.textContent = `${rows.length} of ${sites.length} records`;
      tb.innerHTML = rows.map(r => `
        <tr class="is-click" data-id="${r.id}">
          <td class="tiny">${fmt.title(r.belt)}</td>
          <td class="strong">${r.display}</td>
          <td class="tiny">${fmt.title(r.state)}</td>
          <td class="mono tiny">${r.toposheet}</td>
          <td class="num tiny">${r.lat.toFixed(5)}</td>
          <td class="num tiny">${r.lon.toFixed(5)}</td>
          <td class="tiny muted">Manganese</td>
          <td class="tiny">${fmt.title(r.hostrock)}</td>
          <td class="tiny">${fmt.title(r.morphogenesis)}</td>
          <td class="tiny">${r.formation}</td>
          <td><span class="tier tier--${r.tier}">${r.source}</span></td>
        </tr>`).join('');
      $$('#rg-table tbody tr').forEach(tr => tr.addEventListener('click', () => store.setSite(tr.dataset.id)));
    };
    draw();
    $('#rg-q').addEventListener('input', e => draw(e.target.value));
  });
}

export const VIEWS = { command, reserve, explorer, forecast, risk, actions, alerts, roi, enterprise, reports, register };
