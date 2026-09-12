/* MANGENESIS — mapping.

   Two renderers share one selection model:

   nationalMap()  a vector map of India carrying the whole GSI occurrence
                  register, grouped by metallogenic belt. No tiles, so it
                  is instant and works offline.
   siteMap()      a satellite view of the selected locality with the
                  modelled target sectors, drill collars and regional
                  strike. Falls back to a local vector plan if Leaflet or
                  its tiles are unavailable.
*/

import { fmt, icon } from './core.js';

/* Simplified national outline (≈70 vertices, lon/lat). Cartographic
   generalisation only — not a survey boundary. */
const INDIA = [
  [68.2,23.7],[68.8,24.3],[70.0,24.3],[70.6,25.7],[71.0,27.8],[72.2,28.8],[73.9,29.9],
  [74.6,31.0],[74.4,32.5],[75.0,34.0],[76.8,34.6],[78.5,34.6],[79.0,33.2],[78.8,32.5],
  [79.2,31.4],[80.2,30.6],[81.0,30.2],[82.0,30.3],[83.3,29.4],[84.7,28.6],[86.2,28.1],
  [88.1,27.9],[88.9,27.3],[89.1,26.8],[89.9,26.4],[90.9,26.8],[92.0,27.5],[94.0,27.6],
  [95.3,28.0],[96.6,27.6],[97.4,28.3],[97.1,27.1],[96.2,26.0],[95.1,26.6],[94.6,25.4],
  [94.3,24.1],[93.4,23.1],[93.1,22.2],[92.6,22.0],[92.2,21.3],[91.6,22.3],[90.6,22.0],
  [89.1,21.7],[88.1,21.7],[87.0,21.5],[86.9,20.8],[85.1,19.5],[83.3,18.3],[82.2,17.0],
  [80.9,15.9],[80.3,13.8],[80.0,12.5],[79.8,10.3],[78.9,9.2],[77.5,8.1],[77.1,8.6],
  [76.2,9.9],[75.0,12.0],[74.0,14.5],[73.2,16.5],[72.8,18.9],[72.6,20.0],[72.9,21.1],
  [72.3,21.7],[70.9,20.8],[69.4,21.9],[68.9,22.4],[69.8,22.9],[70.5,23.0],[68.2,23.7],
];

const BOX = { lon0: 67.0, lon1: 98.5, lat0: 7.0, lat1: 36.0 };

/* ---------- National register map ------------------------------------- */

export function nationalMap(host, sites, { selected, onSelect, focusBelt } = {}) {
  const W = 760, H = 780;
  const pad = 24;
  const X = (lon) => pad + (W - pad * 2) * (lon - BOX.lon0) / (BOX.lon1 - BOX.lon0);
  const Y = (lat) => pad + (H - pad * 2) * (1 - (lat - BOX.lat0) / (BOX.lat1 - BOX.lat0));

  const outline = INDIA.map(([lo, la], i) => `${i ? 'L' : 'M'}${X(lo).toFixed(1)} ${Y(la).toFixed(1)}`).join(' ') + ' Z';

  /* Belt hulls: a soft envelope round each belt's localities, so the
     metallogenic structure reads before the individual points do. */
  const byBelt = new Map();
  sites.forEach(s => {
    if (!byBelt.has(s.belt)) byBelt.set(s.belt, { colour: s.colour, pts: [] });
    byBelt.get(s.belt).pts.push(s);
  });

  const beltGeom = [...byBelt.entries()].map(([belt, g]) => {
    const cx = g.pts.reduce((a, p) => a + X(p.lon), 0) / g.pts.length;
    const cy = g.pts.reduce((a, p) => a + Y(p.lat), 0) / g.pts.length;
    const r = Math.max(26, Math.max(...g.pts.map(p => Math.hypot(X(p.lon) - cx, Y(p.lat) - cy))) + 20);
    return { belt, colour: g.colour, cx, cy, r, ly: cy - r - 7 };
  });

  /* Label de-collision: sort by y, then push each label clear of the one
     above it. Central India stacks four belts within a few degrees, so
     without this the names overprint each other. */
  const MIN_GAP = 13;
  beltGeom.sort((a, b) => a.ly - b.ly);
  for (let i = 1; i < beltGeom.length; i++) {
    const prev = beltGeom[i - 1], cur = beltGeom[i];
    if (Math.abs(cur.cx - prev.cx) < 150 && cur.ly - prev.ly < MIN_GAP) {
      cur.ly = prev.ly + MIN_GAP;
    }
  }

  const hulls = beltGeom.map(({ belt, colour, cx, cy, r, ly }) => {
    const dim = focusBelt && focusBelt !== belt;
    const short = belt.replace(' BELT', '').replace(' PROVINCE', '').replace(' SECTOR', '');
    return `<circle cx="${cx.toFixed(1)}" cy="${cy.toFixed(1)}" r="${r.toFixed(1)}"
      fill="${colour}" opacity="${dim ? 0.03 : 0.09}" stroke="${colour}"
      stroke-opacity="${dim ? 0.10 : 0.35}" stroke-width="1" stroke-dasharray="4 4"/>
      ${ly !== cy - r - 7 ? `<line x1="${cx.toFixed(1)}" y1="${(cy - r).toFixed(1)}" x2="${cx.toFixed(1)}" y2="${(ly + 3).toFixed(1)}"
        stroke="${colour}" stroke-opacity="${dim ? 0.12 : 0.4}" stroke-width="1"/>` : ''}
      <text x="${cx.toFixed(1)}" y="${ly.toFixed(1)}" text-anchor="middle"
        style="font-family:var(--ff-mono);font-size:9px;letter-spacing:.08em;fill:${colour};opacity:${dim ? 0.25 : 0.9};paint-order:stroke;stroke:var(--ground);stroke-width:3px;stroke-linejoin:round">
        ${short}</text>`;
  }).join('');

  const dots = sites.map(s => {
    const on = s.id === selected;
    const dim = focusBelt && focusBelt !== s.belt;
    const r = s.tier === 'operating' ? 6.5 : s.tier === 'exploration' ? 4.6 : 3.6;
    return `<g class="nm-site" data-id="${s.id}" style="cursor:pointer;opacity:${dim ? 0.22 : 1}">
      ${on ? `<circle cx="${X(s.lon).toFixed(1)}" cy="${Y(s.lat).toFixed(1)}" r="${r + 9}"
              fill="none" stroke="var(--violet-hi)" stroke-width="1.5" opacity=".9">
              <animate attributeName="r" values="${r + 5};${r + 13};${r + 5}" dur="2.4s" repeatCount="indefinite"/>
              <animate attributeName="opacity" values=".9;.1;.9" dur="2.4s" repeatCount="indefinite"/></circle>` : ''}
      <circle cx="${X(s.lon).toFixed(1)}" cy="${Y(s.lat).toFixed(1)}" r="${r + 3}" fill="${s.colour}" opacity=".22"/>
      <circle cx="${X(s.lon).toFixed(1)}" cy="${Y(s.lat).toFixed(1)}" r="${r}"
        fill="${on ? 'var(--violet-hi)' : s.colour}" stroke="var(--ground)" stroke-width="${s.tier === 'operating' ? 1.6 : 1}"/>
      ${s.tier === 'operating' ? `<circle cx="${X(s.lon).toFixed(1)}" cy="${Y(s.lat).toFixed(1)}" r="2" fill="var(--ground)"/>` : ''}
      <title>${s.display} — ${fmt.title(s.belt)}, ${fmt.title(s.state)}</title>
    </g>`;
  }).join('');

  const opCount = sites.filter(s => s.tier === 'operating').length;

  host.innerHTML = `
    <svg viewBox="0 0 ${W} ${H}" class="mapshell__canvas" role="img"
         aria-label="Manganese occurrence register mapped across India">
      <defs>
        <radialGradient id="nmGlow" cx="50%" cy="42%" r="62%">
          <stop offset="0%" stop-color="var(--violet-hi)" stop-opacity=".14"/>
          <stop offset="100%" stop-color="var(--violet-hi)" stop-opacity="0"/>
        </radialGradient>
      </defs>
      <rect width="${W}" height="${H}" fill="url(#nmGlow)"/>
      <path d="${outline}" fill="var(--surface-2)" stroke="var(--hairline-2)" stroke-width="1.4"
            stroke-linejoin="round"/>
      ${hulls}
      ${dots}
      <g style="font-family:var(--ff-mono);font-size:9px;fill:var(--faint)">
        <text x="${pad}" y="${H - 22}">${sites.length} recorded localities · ${opCount} operating</text>
        <text x="${pad}" y="${H - 10}">Simplified national outline · GSI occurrence register</text>
      </g>
    </svg>
    <div class="maptip" id="nm-tip"></div>`;

  const tip = host.querySelector('#nm-tip');
  const svg = host.querySelector('svg');

  host.querySelectorAll('.nm-site').forEach(g => {
    const s = sites.find(x => x.id === g.dataset.id);
    g.addEventListener('click', () => onSelect && onSelect(s.id));
    g.addEventListener('pointerenter', () => {
      tip.innerHTML = `<b>${s.display}</b>
        <span>${fmt.title(s.belt)} · ${fmt.title(s.state)}</span>
        <span>${fmt.dms(s.lat, 'lat')} ${fmt.dms(s.lon, 'lon')}</span>`;
      tip.classList.add('is-on');
    });
    g.addEventListener('pointermove', (e) => {
      const b = host.getBoundingClientRect();
      const x = e.clientX - b.left, y = e.clientY - b.top;
      tip.style.left = Math.min(x + 14, b.width - 250) + 'px';
      tip.style.top = Math.max(y - 60, 8) + 'px';
    });
    g.addEventListener('pointerleave', () => tip.classList.remove('is-on'));
  });

  return { svg };
}

/* ---------- Locality map ---------------------------------------------- */

const LAYERS = [
  { key: 'satellite', label: 'Satellite Imagery', colour: '#4CC9F0', on: true },
  { key: 'zones', label: 'Reserve Target Sectors', colour: '#7026FB', on: true },
  { key: 'strike', label: 'Geological Strike', colour: '#B695FF', on: true },
  { key: 'drills', label: 'Drill Core Assays', colour: '#3DDC97', on: true },
  { key: 'ndvi', label: 'NDVI Spectral Alteration', colour: '#3DDC97', on: false },
  { key: 'smap', label: 'Soil Moisture (SMAP)', colour: '#E4D5C7', on: false },
  { key: 'lst', label: 'Surface Thermal (LST)', colour: '#FFC24B', on: false },
];

export function siteMap(host, snap, { layers = {} } = {}) {
  const site = snap.site, res = snap.reserve;
  const state = {};
  LAYERS.forEach(l => { state[l.key] = layers[l.key] ?? l.on; });

  const hasLeaflet = typeof window.L !== 'undefined';
  host.innerHTML = `<div class="mapshell__canvas" id="sm-canvas"></div>${floats()}`;
  const canvas = host.querySelector('#sm-canvas');

  function floats() {
    return `
      <div class="mapfloat mapfloat--tr">
        <div class="mapfloat__head">${icon('layers')} Map Layers</div>
        <div class="mapfloat__body" id="sm-layers">
          ${LAYERS.map(l => `
            <button class="layerrow ${state[l.key] ? 'is-on' : ''}" data-layer="${l.key}" type="button">
              <span class="layerrow__sw" style="background:${l.colour}"></span>
              <span>${l.label}</span>
              <span class="layerrow__state">${state[l.key] ? 'ON' : 'OFF'}</span>
            </button>`).join('')}
        </div>
      </div>
      <div class="mapfloat mapfloat--bl">
        <div class="mapfloat__head">${icon('target')} Reserve Probability</div>
        <div class="mapfloat__body">
          <div class="legend">
            <div class="legend__row"><i class="legend__sw" style="background:var(--good)"></i>
              <span><b>High 70–100%</b><span>Commercial Mn strike — drill target</span></span></div>
            <div class="legend__row"><i class="legend__sw" style="background:var(--warn)"></i>
              <span><b>Medium 40–70%</b><span>Moderate mineralisation — survey needed</span></span></div>
            <div class="legend__row"><i class="legend__sw" style="background:var(--muted)"></i>
              <span><b>Low 0–40%</b><span>Barren host rock — lease buffer</span></span></div>
          </div>
          <div class="tiny muted" style="border-top:1px solid var(--hairline);padding-top:8px">
            Collar pin label shows logged <b>% Mn</b> grade.
          </div>
        </div>
      </div>`;
  }

  let map = null, groups = {};

  function drawLeaflet() {
    map = L.map(canvas, { zoomControl: true, attributionControl: true, scrollWheelZoom: true })
      .setView([site.lat, site.lon], 14);

    groups.satellite = L.tileLayer(
      'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
      { maxZoom: 19, attribution: 'Esri — high-resolution Earth imagery' });

    groups.zones = L.layerGroup(res.zones.flatMap(z => {
      const col = z.class === 'high' ? '#3DDC97' : z.class === 'medium' ? '#FFC24B' : '#8B819F';
      const poly = L.polygon(z.polygon, {
        color: col, weight: 1.6, fillOpacity: 0.14, dashArray: '5 5',
      }).bindPopup(`
        <b style="font-size:13px">${z.name}</b><br/>
        <span style="font-family:ui-monospace,monospace;font-size:11px">
        Reserve probability &nbsp;<b>${z.probability_pct}%</b><br/>
        Mn grade &nbsp;<b>${z.mn_grade_pct}%</b><br/>
        Indicated tonnage &nbsp;<b>${fmt.n(z.tonnage_t)} T</b><br/>
        Strike ${z.strike_length_m} m · width ${z.avg_width_m} m · depth ${z.depth_extent_m} m<br/>
        Host: ${fmt.title(site.hostrock)}</span>`);
      const label = L.marker(z.centroid, {
        icon: L.divIcon({
          className: '', html: `<div class="zonelabel" style="border:1px solid ${col}">
            ${z.name.replace(/^Sector /, 'Sec ')} · ${z.probability_pct}%</div>`,
          iconSize: [0, 0],
        }),
      });
      return [poly, label];
    }));

    groups.strike = L.layerGroup([
      L.polyline(res.strike_line, { color: '#B695FF', weight: 1.6, dashArray: '9 7', opacity: 0.75 })
        .bindPopup(`Regional strike — ${fmt.title(site.belt)}<br/>Azimuth ${res.strike_azimuth}° from north`),
    ]);

    groups.drills = L.layerGroup(res.drill_holes.map(d => {
      const col = d.mn_grade_pct >= 38 ? '#3DDC97' : d.mn_grade_pct >= 28 ? '#FFC24B' : '#FF5C7A';
      return L.marker([d.lat, d.lon], {
        icon: L.divIcon({
          className: '',
          html: `<div class="pinlabel" style="border-color:${col}">
            <span style="color:${col}">◆</span> ${d.hole_id} · ${d.mn_grade_pct}% Mn</div>`,
          iconSize: [0, 0], iconAnchor: [0, 0],
        }),
      }).bindPopup(`
        <b style="font-size:13px">${d.hole_id}</b><br/>
        <span style="font-family:ui-monospace,monospace;font-size:11px">
        Depth <b>${d.depth_m} m</b> · intercept <b>${d.intercept_m} m</b><br/>
        Mn <b>${d.mn_grade_pct}%</b> · Fe ${d.fe_pct}% · SiO₂ ${d.sio2_pct}% · P ${d.p_pct}%<br/>
        Lithology: ${fmt.title(d.lithology)}<br/>
        ${fmt.dms(d.lat, 'lat')} ${fmt.dms(d.lon, 'lon')}<br/>
        Status: ${d.status}</span>`);
    }));

    /* Spectral overlays: modelled raster stand-ins drawn as graduated
       circles so the operator can see where each index is anomalous. */
    const spectral = (key, palette, scale) => L.layerGroup(res.zones.map((z, i) => L.circle(z.centroid, {
      radius: 240 + i * 70,
      color: palette, weight: 1, fillColor: palette,
      fillOpacity: 0.10 + z.probability * 0.24,
    }).bindPopup(`${scale(z)}`)));

    groups.ndvi = spectral('ndvi', '#3DDC97', z => `NDVI anomaly ${(0.22 + z.probability * 0.34).toFixed(3)} — alteration halo`);
    groups.smap = spectral('smap', '#E4D5C7', z => `SMAP soil moisture ${(14 + z.probability * 28).toFixed(1)}% v/v`);
    groups.lst = spectral('lst', '#FFC24B', z => `MODIS LST ${(site.mean_lst_c ?? 32).toFixed?.(1) ?? 32}°C surface anomaly`);

    Object.entries(groups).forEach(([k, g]) => { if (state[k]) g.addTo(map); });
    setTimeout(() => map.invalidateSize(), 60);
  }

  /* Vector fallback: a local plan view in metres, no tiles required. */
  function drawVector() {
    const box = host.getBoundingClientRect();
    const aspect = box.width && box.height ? box.width / box.height : 1.6;
    const H = 620, W = Math.round(H * Math.max(0.8, Math.min(2.2, aspect))), pad = 52;
    const pts = [...res.zones.flatMap(z => z.polygon), ...res.drill_holes.map(d => [d.lat, d.lon]), ...res.strike_line];
    const lat = pts.map(p => p[0]), lon = pts.map(p => p[1]);
    const la0 = Math.min(...lat), la1 = Math.max(...lat), lo0 = Math.min(...lon), lo1 = Math.max(...lon);
    const spanLa = Math.max(la1 - la0, 0.004), spanLo = Math.max(lo1 - lo0, 0.004);
    const X = v => pad + (W - pad * 2) * ((v - lo0) / spanLo);
    const Y = v => pad + (H - pad * 2) * (1 - (v - la0) / spanLa);

    const grid = Array.from({ length: 9 }, (_, i) => {
      const t = i / 8;
      return `<line x1="${pad + (W - pad * 2) * t}" y1="${pad}" x2="${pad + (W - pad * 2) * t}" y2="${H - pad}" class="grid-line"/>
              <line x1="${pad}" y1="${pad + (H - pad * 2) * t}" x2="${W - pad}" y2="${pad + (H - pad * 2) * t}" class="grid-line"/>`;
    }).join('');

    const zones = state.zones ? res.zones.map(z => {
      const col = z.class === 'high' ? 'var(--good)' : z.class === 'medium' ? 'var(--warn)' : 'var(--muted)';
      const d = z.polygon.map((p, i) => `${i ? 'L' : 'M'}${X(p[1]).toFixed(1)} ${Y(p[0]).toFixed(1)}`).join(' ') + ' Z';
      return `<path d="${d}" fill="${col}" fill-opacity=".14" stroke="${col}" stroke-width="1.5" stroke-dasharray="5 5"/>
        <text x="${X(z.centroid[1]).toFixed(1)}" y="${Y(z.centroid[0]).toFixed(1)}" text-anchor="middle"
          style="font-family:var(--ff-mono);font-size:10px;fill:${col};paint-order:stroke;stroke:var(--ink);stroke-width:3.5px;stroke-linejoin:round">${z.name.replace(/^Sector /, 'Sec ')} · ${z.probability_pct}%</text>`;
    }).join('') : '';

    const strike = state.strike
      ? `<line x1="${X(res.strike_line[0][1]).toFixed(1)}" y1="${Y(res.strike_line[0][0]).toFixed(1)}"
              x2="${X(res.strike_line[1][1]).toFixed(1)}" y2="${Y(res.strike_line[1][0]).toFixed(1)}"
              stroke="var(--lilac)" stroke-width="1.5" stroke-dasharray="9 7" opacity=".7"/>` : '';

    const drills = state.drills ? res.drill_holes.map((d, i) => {
      const col = d.mn_grade_pct >= 38 ? 'var(--good)' : d.mn_grade_pct >= 28 ? 'var(--warn)' : 'var(--crit)';
      const dy = (i % 2 ? 1 : -1) * 11;
      return `<g><circle cx="${X(d.lon).toFixed(1)}" cy="${Y(d.lat).toFixed(1)}" r="5" fill="${col}" opacity=".3"/>
        <path d="M${X(d.lon).toFixed(1)} ${(Y(d.lat) - 4).toFixed(1)} l4 4 -4 4 -4 -4 Z" fill="${col}"/>
        <line x1="${X(d.lon).toFixed(1)}" y1="${Y(d.lat).toFixed(1)}" x2="${(X(d.lon) + 8).toFixed(1)}" y2="${(Y(d.lat) + dy).toFixed(1)}"
          stroke="${col}" stroke-opacity=".5" stroke-width="1"/>
        <text x="${(X(d.lon) + 11).toFixed(1)}" y="${(Y(d.lat) + dy + 3).toFixed(1)}"
          style="font-family:var(--ff-mono);font-size:9.5px;fill:var(--text-2);paint-order:stroke;stroke:var(--ink);stroke-width:3px;stroke-linejoin:round">${d.hole_id} · ${d.mn_grade_pct}%</text>
        <title>${d.hole_id} — ${d.depth_m} m, ${d.mn_grade_pct}% Mn</title></g>`;
    }).join('') : '';

    canvas.innerHTML = `
      <svg viewBox="0 0 ${W} ${H}" class="mapshell__canvas" role="img"
           aria-label="Plan view of modelled target sectors and drill collars at ${site.name}">
        <rect width="${W}" height="${H}" fill="var(--ink)"/>
        ${grid}${zones}${strike}${drills}
        <g style="font-family:var(--ff-mono);font-size:9.5px;fill:var(--faint)">
          <text x="${pad}" y="${H - 24}">${site.name} · plan view · ${fmt.dms(site.lat, 'lat')} ${fmt.dms(site.lon, 'lon')}</text>
          <text x="${pad}" y="${H - 11}">Vector mode — satellite tiles unavailable in this context</text>
        </g>
      </svg>`;
  }

  function render() {
    if (hasLeaflet && !map) { try { drawLeaflet(); return; } catch (e) { /* fall through */ } }
    if (!hasLeaflet) drawVector();
  }
  render();

  host.querySelectorAll('[data-layer]').forEach(btn => {
    btn.addEventListener('click', () => {
      const k = btn.dataset.layer;
      state[k] = !state[k];
      btn.classList.toggle('is-on', state[k]);
      btn.querySelector('.layerrow__state').textContent = state[k] ? 'ON' : 'OFF';
      if (map && groups[k]) {
        state[k] ? groups[k].addTo(map) : map.removeLayer(groups[k]);
      } else if (!map) {
        drawVector();
      }
    });
  });

  return {
    destroy() { if (map) { map.remove(); map = null; } },
    invalidate() { if (map) setTimeout(() => map.invalidateSize(), 50); },
  };
}
