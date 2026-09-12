/* MANGENESIS — visualisation primitives.
   Every chart is hand-drawn SVG on one scale, with labels kept inside the
   viewBox and colours taken from the theme tokens so both themes read. */

import { fmt } from './core.js';

const SVG = (w, h, inner, cls = 'chart') =>
  `<svg viewBox="0 0 ${w} ${h}" class="${cls}" preserveAspectRatio="xMidYMid meet" role="img">${inner}</svg>`;

const path = (pts) => pts.map((p, i) => `${i ? 'L' : 'M'}${p[0].toFixed(1)} ${p[1].toFixed(1)}`).join(' ');

/* Catmull-Rom → cubic Bézier, so series read as trends not zig-zags */
function smooth(pts) {
  if (pts.length < 3) return path(pts);
  let d = `M${pts[0][0].toFixed(1)} ${pts[0][1].toFixed(1)}`;
  for (let i = 0; i < pts.length - 1; i++) {
    const p0 = pts[i - 1] || pts[i], p1 = pts[i], p2 = pts[i + 1], p3 = pts[i + 2] || p2;
    const c1 = [p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6];
    const c2 = [p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6];
    d += ` C${c1[0].toFixed(1)} ${c1[1].toFixed(1)}, ${c2[0].toFixed(1)} ${c2[1].toFixed(1)}, ${p2[0].toFixed(1)} ${p2[1].toFixed(1)}`;
  }
  return d;
}

/* ---------- Production forecast --------------------------------------- */

export function forecastChart(prod, { w = 900, h = 300, compact = false } = {}) {
  const hist = prod.history, fc = prod.forecast, target = prod.target;
  const pad = { l: compact ? 42 : 52, r: 14, t: 16, b: compact ? 26 : 32 };
  const iw = w - pad.l - pad.r, ih = h - pad.t - pad.b;

  const vals = [...hist.map(d => d.actual), ...fc.map(d => d.forecast), ...fc.map(d => d.lower), ...fc.map(d => d.upper), target];
  const lo = Math.min(...vals) * 0.94, hi = Math.max(...vals) * 1.05, rng = Math.max(hi - lo, 1);
  const n = hist.length + fc.length;
  const X = i => pad.l + iw * (i / (n - 1));
  const Y = v => pad.t + ih * (1 - (v - lo) / rng);

  let g = '';
  for (let k = 0; k <= 4; k++) {
    const v = lo + rng * k / 4, y = Y(v);
    g += `<line x1="${pad.l}" y1="${y.toFixed(1)}" x2="${w - pad.r}" y2="${y.toFixed(1)}" class="grid-line"/>`;
    g += `<text x="${pad.l - 8}" y="${(y + 3.5).toFixed(1)}" text-anchor="end" class="axis">${fmt.compact(v)}</text>`;
  }

  const histPts = hist.map((d, i) => [X(i), Y(d.actual)]);
  const fcPts = fc.map((d, j) => [X(hist.length + j), Y(d.forecast)]);
  const bridge = [histPts[histPts.length - 1], ...fcPts];
  const band = [
    ...fc.map((d, j) => [X(hist.length + j), Y(d.upper)]),
    ...fc.map((d, j) => [X(hist.length + j), Y(d.lower)]).reverse(),
  ];

  const areaHist = `${smooth(histPts)} L${X(hist.length - 1).toFixed(1)} ${(pad.t + ih).toFixed(1)} L${pad.l} ${(pad.t + ih).toFixed(1)} Z`;
  const splitX = X(hist.length - 1);

  const ticks = compact
    ? [0, Math.floor(n / 2), n - 1]
    : [0, Math.floor(n * 0.25), Math.floor(n * 0.5), hist.length - 1, n - 1];
  const labelAt = i => (i < hist.length ? hist[i].label : fc[i - hist.length].label);

  return SVG(w, h, `
    <defs>
      <linearGradient id="fcArea" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stop-color="var(--violet-hi)" stop-opacity=".30"/>
        <stop offset="100%" stop-color="var(--violet-hi)" stop-opacity="0"/>
      </linearGradient>
      <linearGradient id="histArea" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stop-color="var(--s2)" stop-opacity=".20"/>
        <stop offset="100%" stop-color="var(--s2)" stop-opacity="0"/>
      </linearGradient>
    </defs>
    ${g}
    <rect x="${splitX.toFixed(1)}" y="${pad.t}" width="${(w - pad.r - splitX).toFixed(1)}" height="${ih}"
          fill="var(--wash)" />
    <line x1="${splitX.toFixed(1)}" y1="${pad.t}" x2="${splitX.toFixed(1)}" y2="${pad.t + ih}"
          stroke="var(--hairline-2)" stroke-width="1" stroke-dasharray="3 3"/>
    <line x1="${pad.l}" y1="${Y(target).toFixed(1)}" x2="${w - pad.r}" y2="${Y(target).toFixed(1)}" class="target-line"/>
    <text x="${pad.l + 6}" y="${(Y(target) - 6).toFixed(1)}" class="axis" style="font-size:9px">TARGET ${fmt.n(target)} T</text>
    <path d="${areaHist}" fill="url(#histArea)"/>
    <path d="${path(band)} Z" fill="url(#fcArea)"/>
    <path d="${smooth(histPts)}" fill="none" stroke="var(--s2)" stroke-width="2" stroke-linecap="round"/>
    <path d="${smooth(bridge)}" fill="none" stroke="var(--violet-hi)" stroke-width="2.6" stroke-linecap="round"/>
    ${histPts.filter((_, i) => i % 2 === 0 || i === histPts.length - 1)
      .map(p => `<circle cx="${p[0].toFixed(1)}" cy="${p[1].toFixed(1)}" r="2.6" fill="var(--s2)"/>`).join('')}
    ${fcPts.map((p, j) => `<circle cx="${p[0].toFixed(1)}" cy="${p[1].toFixed(1)}" r="3.4"
        fill="var(--violet-hi)" stroke="var(--surface)" stroke-width="1.6">
        <title>${fc[j].label}: ${fmt.n(fc[j].forecast)} T</title></circle>`).join('')}
    ${ticks.map(i => `<text x="${X(i).toFixed(1)}" y="${h - 10}" text-anchor="middle" class="axis">${labelAt(i)}</text>`).join('')}
  `);
}

/* ---------- Risk donut ------------------------------------------------ */

export function riskDonut(pct, factors, { size = 250 } = {}) {
  const c = size / 2, R = size * 0.38, sw = size * 0.115;
  const circ = 2 * Math.PI * R;
  let off = 0;
  const arcs = factors.map((f) => {
    const len = circ * f.weight;
    const seg = `<circle cx="${c}" cy="${c}" r="${R}" fill="none" stroke="${f.colour}"
       stroke-width="${sw}" stroke-dasharray="${(len - 3).toFixed(2)} ${(circ - len + 3).toFixed(2)}"
       stroke-dashoffset="${(-off).toFixed(2)}" stroke-linecap="butt"
       transform="rotate(-90 ${c} ${c})"><title>${f.label}: ${f.weight_pct}%</title></circle>`;
    off += len;
    return seg;
  }).join('');
  const tone = pct >= 70 ? 'var(--crit)' : pct >= 40 ? 'var(--warn)' : 'var(--good)';

  return SVG(size, size, `
    <circle cx="${c}" cy="${c}" r="${R}" fill="none" stroke="var(--surface-3)" stroke-width="${sw}"/>
    ${arcs}
    <text x="${c}" y="${c - 2}" class="donut__center donut__num" fill="${tone}">${pct}%</text>
    <text x="${c}" y="${c + 16}" class="donut__center donut__cap">SHORTFALL RISK</text>
  `);
}

/* ---------- Horizontal weighted bars ---------------------------------- */

export function hbars(items, { valueKey = 'weight_pct', suffix = '%' } = {}) {
  const max = Math.max(...items.map(i => i[valueKey])) || 1;
  return `<div class="stack stack--sm">${items.map(i => `
    <div class="metric">
      <div class="metric__top">
        <span class="metric__k">${i.label}</span>
        <span class="metric__v" style="color:${i.colour || 'var(--text)'}">${i[valueKey]}${suffix}</span>
      </div>
      <div class="meter"><div class="meter__fill" style="width:${(i[valueKey] / max * 100).toFixed(1)}%;background:${i.colour || 'var(--violet-hi)'}"></div></div>
    </div>`).join('')}</div>`;
}

/* ---------- Sparkline ------------------------------------------------- */

export function sparkline(values, { w = 120, h = 34, colour = 'var(--violet-hi)' } = {}) {
  const lo = Math.min(...values), hi = Math.max(...values), rng = Math.max(hi - lo, 1e-6);
  const pts = values.map((v, i) => [2 + (w - 4) * (i / (values.length - 1)), 3 + (h - 6) * (1 - (v - lo) / rng)]);
  const last = pts[pts.length - 1];
  return SVG(w, h, `
    <path d="${smooth(pts)} L${(w - 2).toFixed(1)} ${h - 3} L2 ${h - 3} Z" fill="${colour}" opacity=".14"/>
    <path d="${smooth(pts)}" fill="none" stroke="${colour}" stroke-width="1.8" stroke-linecap="round"/>
    <circle cx="${last[0].toFixed(1)}" cy="${last[1].toFixed(1)}" r="2.8" fill="${colour}"/>
  `);
}

/* ---------- Recovery gauge -------------------------------------------- */

export function gauge(pct, { size = 190, label = 'RESTORED' } = {}) {
  const c = size / 2, R = size * 0.40, sw = size * 0.10;
  const sweep = Math.PI * 1.32, start = Math.PI * 0.84;
  const P = (t) => [c + R * Math.cos(start + sweep * t), c + R * Math.sin(start + sweep * t)];
  const arc = (t0, t1, stroke, width) => {
    const a = P(t0), b = P(t1);
    return `<path d="M${a[0].toFixed(1)} ${a[1].toFixed(1)} A${R} ${R} 0 ${t1 - t0 > 0.5 ? 1 : 0} 1 ${b[0].toFixed(1)} ${b[1].toFixed(1)}"
       fill="none" stroke="${stroke}" stroke-width="${width}" stroke-linecap="round"/>`;
  };
  const f = Math.max(0.001, Math.min(1, pct / 100));
  return SVG(size, size * 0.82, `
    ${arc(0, 1, 'var(--surface-3)', sw)}
    ${arc(0, f, 'var(--good)', sw)}
    <text x="${c}" y="${c + 4}" class="donut__center donut__num" fill="var(--good)">${Math.round(pct)}%</text>
    <text x="${c}" y="${c + 22}" class="donut__center donut__cap">${label}</text>
  `);
}

/* ---------- Value pillars: stacked share bar -------------------------- */

export function shareBar(pillars) {
  let x = 0;
  const segs = pillars.map(p => {
    const wdt = p.share_pct;
    const s = `<div title="${p.label}: ${fmt.cr(p.value_cr)}" style="width:${wdt}%;background:${p.colour};
       height:100%;${x ? 'border-left:1px solid var(--surface);' : ''}"></div>`;
    x += wdt;
    return s;
  }).join('');
  return `<div style="display:flex;height:14px;border-radius:99px;overflow:hidden;background:var(--surface-3)">${segs}</div>`;
}

/* ---------- Grouped column chart (enterprise comparison) -------------- */

const RISK_COLOUR = (p) => (p >= 70 ? 'var(--crit)' : p >= 40 ? 'var(--warn)' : 'var(--good)');

export function columns(rows, { w = 880, h = 280, key = 'roi_cr', unit = ' Cr', label = 'Annual value' } = {}) {
  const pad = { l: 52, r: 14, t: 20, b: 62 };
  const iw = w - pad.l - pad.r, ih = h - pad.t - pad.b;
  const max = Math.max(...rows.map(r => r[key])) * 1.14 || 1;
  const step = iw / rows.length, bw = Math.min(52, step * 0.56);

  let grid = '';
  for (let k = 0; k <= 4; k++) {
    const v = max * k / 4, y = pad.t + ih * (1 - k / 4);
    grid += `<line x1="${pad.l}" y1="${y.toFixed(1)}" x2="${w - pad.r}" y2="${y.toFixed(1)}" class="grid-line"/>
             <text x="${pad.l - 8}" y="${(y + 3.5).toFixed(1)}" text-anchor="end" class="axis">${v.toFixed(0)}</text>`;
  }

  const bars = rows.map((r, i) => {
    const bh = ih * (r[key] / max);
    const x = pad.l + step * i + (step - bw) / 2;
    const y = pad.t + ih - bh;
    const words = r.name.replace(/ Mine$/, '');
    return `<g>
      <rect x="${x.toFixed(1)}" y="${y.toFixed(1)}" width="${bw.toFixed(1)}" height="${Math.max(bh, 2).toFixed(1)}"
            rx="5" fill="${RISK_COLOUR(r.risk_pct)}" opacity=".85"><title>${r.name}: ${r[key]}${unit} · ${r.risk_pct}% shortfall risk</title></rect>
      <text x="${(x + bw / 2).toFixed(1)}" y="${(y - 7).toFixed(1)}" text-anchor="middle" class="axis"
            style="fill:var(--text);font-size:10.5px;font-weight:600">${r[key]}</text>
      <text x="${(x + bw / 2).toFixed(1)}" y="${(pad.t + ih + 16).toFixed(1)}" text-anchor="middle" class="axis"
            style="font-size:9.5px">${words.length > 11 ? words.slice(0, 10) + '…' : words}</text>
      <text x="${(x + bw / 2).toFixed(1)}" y="${(pad.t + ih + 29).toFixed(1)}" text-anchor="middle" class="axis"
            style="font-size:8.5px;fill:var(--faint)">${r.state.slice(0, 3)}</text>
    </g>`;
  }).join('');

  return SVG(w, h, `${grid}${bars}
    <text x="${pad.l}" y="${h - 8}" class="axis" style="font-size:9px">${label} (₹ crore, modelled)</text>`);
}

/* ---------- Scatter: grade vs tonnage --------------------------------- */

export function scatter(zones, { w = 420, h = 240 } = {}) {
  const pad = { l: 46, r: 16, t: 16, b: 36 };
  const iw = w - pad.l - pad.r, ih = h - pad.t - pad.b;
  const gs = zones.map(z => z.mn_grade_pct), ts = zones.map(z => z.tonnage_t);
  const gLo = Math.min(...gs) * 0.96, gHi = Math.max(...gs) * 1.04;
  const tHi = Math.max(...ts) * 1.12;
  const X = v => pad.l + iw * ((v - gLo) / Math.max(gHi - gLo, 0.01));
  const Y = v => pad.t + ih * (1 - v / tHi);

  let grid = '';
  for (let k = 0; k <= 3; k++) {
    const y = pad.t + ih * (1 - k / 3), v = tHi * k / 3;
    grid += `<line x1="${pad.l}" y1="${y.toFixed(1)}" x2="${w - pad.r}" y2="${y.toFixed(1)}" class="grid-line"/>
             <text x="${pad.l - 7}" y="${(y + 3.5).toFixed(1)}" text-anchor="end" class="axis">${fmt.compact(v)}</text>`;
  }
  const dots = zones.map(z => {
    const col = z.class === 'high' ? 'var(--good)' : z.class === 'medium' ? 'var(--warn)' : 'var(--muted)';
    const r = 5 + z.probability * 9;
    return `<circle cx="${X(z.mn_grade_pct).toFixed(1)}" cy="${Y(z.tonnage_t).toFixed(1)}" r="${r.toFixed(1)}"
       fill="${col}" opacity=".28"/>
      <circle cx="${X(z.mn_grade_pct).toFixed(1)}" cy="${Y(z.tonnage_t).toFixed(1)}" r="3.4" fill="${col}">
      <title>${z.name} — ${z.mn_grade_pct}% Mn, ${fmt.n(z.tonnage_t)} T, ${z.probability_pct}% probability</title></circle>`;
  }).join('');

  return SVG(w, h, `${grid}${dots}
    <text x="${(pad.l + iw / 2).toFixed(1)}" y="${h - 8}" text-anchor="middle" class="axis">Mn grade (%) →</text>
    <text x="12" y="${(pad.t + ih / 2).toFixed(1)}" class="axis" transform="rotate(-90 12 ${(pad.t + ih / 2).toFixed(1)})" text-anchor="middle">Tonnage (T)</text>`);
}

/* ---------- 3D ore-body lattice (canvas) -------------------------------
   A rotating block-model section: drill collars dropped to their logged
   depth, coloured by Mn grade, wrapped in the target-sector envelopes.
   This is the view a mine geologist actually works from, so it earns the
   3D rather than decorating with it. ----------------------------------- */

export function orebody(canvas, reserve, site) {
  if (!canvas) return () => {};
  const ctx = canvas.getContext('2d');
  const zones = reserve.zones, drills = reserve.drill_holes;

  const lats = [...zones.map(z => z.centroid[0]), ...drills.map(d => d.lat)];
  const lons = [...zones.map(z => z.centroid[1]), ...drills.map(d => d.lon)];
  const cLat = (Math.min(...lats) + Math.max(...lats)) / 2;
  const cLon = (Math.min(...lons) + Math.max(...lons)) / 2;
  const spanLat = Math.max(Math.max(...lats) - Math.min(...lats), 0.004);
  const spanLon = Math.max(Math.max(...lons) - Math.min(...lons), 0.004);
  const span = Math.max(spanLat, spanLon);
  const maxDepth = Math.max(...drills.map(d => d.depth_m), 120);

  const gradeColour = (g) => {
    const t = Math.max(0, Math.min(1, (g - 18) / 30));
    if (t > 0.66) return '#3DDC97';
    if (t > 0.36) return '#FFC24B';
    return '#FF5C7A';
  };

  let yaw = -0.55, pitch = 0.62, raf = 0, dragging = false, lastX = 0, lastY = 0, spin = true;

  const project = (x, y, z, w, h) => {
    // x,y ground plane (normalised -1..1), z depth downwards 0..1
    const cy = Math.cos(yaw), sy = Math.sin(yaw);
    const cp = Math.cos(pitch), sp = Math.sin(pitch);
    const rx = x * cy - y * sy;
    const rz = x * sy + y * cy;
    const ry = -z;
    const py = ry * cp - rz * sp;
    const pz = ry * sp + rz * cp;
    const scale = Math.min(w, h) * 0.30 / (1 + pz * 0.16);
    return [w / 2 + rx * scale, h / 2 + py * scale * 0.92 + h * 0.06, pz];
  };

  const toLocal = (lat, lon) => [
    (lon - cLon) / span * 1.7,
    (lat - cLat) / span * 1.7,
  ];

  function draw() {
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const w = canvas.clientWidth, h = canvas.clientHeight;
    if (!w || !h) return;
    if (canvas.width !== w * dpr) { canvas.width = w * dpr; canvas.height = h * dpr; }
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, w, h);

    // ground grid
    ctx.lineWidth = 1;
    for (let i = -3; i <= 3; i++) {
      for (const axis of [0, 1]) {
        const a = axis ? [i / 2.2, -1.5] : [-1.5, i / 2.2];
        const b = axis ? [i / 2.2, 1.5] : [1.5, i / 2.2];
        const p1 = project(a[0], a[1], 0, w, h), p2 = project(b[0], b[1], 0, w, h);
        ctx.strokeStyle = i === 0 ? 'rgba(160,132,255,.28)' : 'rgba(160,132,255,.10)';
        ctx.beginPath(); ctx.moveTo(p1[0], p1[1]); ctx.lineTo(p2[0], p2[1]); ctx.stroke();
      }
    }

    // sector envelopes, drawn as prisms from surface to mean lode depth
    const ordered = [...zones].sort((a, b) => {
      const pa = project(...toLocal(a.centroid[0], a.centroid[1]), 0, w, h);
      const pb = project(...toLocal(b.centroid[0], b.centroid[1]), 0, w, h);
      return pb[2] - pa[2];
    });
    ordered.forEach(z => {
      const dz = Math.min(1, z.depth_extent_m / maxDepth) * 1.15;
      const ring = z.polygon.map(pt => toLocal(pt[0], pt[1]));
      const top = ring.map(p => project(p[0], p[1], 0, w, h));
      const bot = ring.map(p => project(p[0], p[1], dz, w, h));
      const col = z.class === 'high' ? '61,220,151' : z.class === 'medium' ? '255,194,75' : '139,129,159';

      for (let i = 0; i < ring.length; i++) {
        const j = (i + 1) % ring.length;
        ctx.beginPath();
        ctx.moveTo(top[i][0], top[i][1]); ctx.lineTo(top[j][0], top[j][1]);
        ctx.lineTo(bot[j][0], bot[j][1]); ctx.lineTo(bot[i][0], bot[i][1]); ctx.closePath();
        ctx.fillStyle = `rgba(${col},${0.05 + z.probability * 0.08})`;
        ctx.fill();
        ctx.strokeStyle = `rgba(${col},.30)`; ctx.stroke();
      }
      ctx.beginPath();
      bot.forEach((p, i) => (i ? ctx.lineTo(p[0], p[1]) : ctx.moveTo(p[0], p[1])));
      ctx.closePath();
      ctx.fillStyle = `rgba(${col},${0.10 + z.probability * 0.14})`;
      ctx.fill();
      ctx.strokeStyle = `rgba(${col},.62)`; ctx.lineWidth = 1.4; ctx.stroke();
      ctx.lineWidth = 1;
    });

    // drill traces
    drills.forEach(d => {
      const [lx, ly] = toLocal(d.lat, d.lon);
      const dz = (d.depth_m / maxDepth) * 1.15;
      const top = project(lx, ly, 0, w, h);
      const bot = project(lx, ly, dz, w, h);
      const col = gradeColour(d.mn_grade_pct);

      ctx.strokeStyle = 'rgba(239,235,250,.24)'; ctx.lineWidth = 1.2;
      ctx.beginPath(); ctx.moveTo(top[0], top[1]); ctx.lineTo(bot[0], bot[1]); ctx.stroke();

      // logged intercept, drawn thick at the bottom of the hole
      const iz = dz * (1 - Math.min(0.42, d.intercept_m / d.depth_m * 2.4));
      const ip = project(lx, ly, iz, w, h);
      ctx.strokeStyle = col; ctx.lineWidth = 3.4;
      ctx.beginPath(); ctx.moveTo(ip[0], ip[1]); ctx.lineTo(bot[0], bot[1]); ctx.stroke();

      ctx.fillStyle = col;
      ctx.beginPath(); ctx.arc(top[0], top[1], 3, 0, Math.PI * 2); ctx.fill();
      ctx.fillStyle = 'rgba(239,235,250,.62)';
      ctx.font = '600 9px ui-monospace, monospace';
      ctx.fillText(d.hole_id, top[0] + 6, top[1] - 4);
    });

    // depth scale
    ctx.fillStyle = 'rgba(139,129,159,.85)';
    ctx.font = '600 9px ui-monospace, monospace';
    ctx.fillText(`0 m`, 12, h - 44);
    ctx.fillText(`${Math.round(maxDepth)} m`, 12, h - 30);
    ctx.fillText(`${site.hostrock} · strike ${reserve.strike_azimuth}°`, 12, h - 14);
  }

  function loop() {
    if (spin && !dragging) yaw += 0.0026;
    draw();
    raf = requestAnimationFrame(loop);
  }

  const onDown = (e) => { dragging = true; lastX = e.clientX ?? e.touches[0].clientX; lastY = e.clientY ?? e.touches[0].clientY; };
  const onMove = (e) => {
    if (!dragging) return;
    const x = e.clientX ?? e.touches[0].clientX, y = e.clientY ?? e.touches[0].clientY;
    yaw += (x - lastX) * 0.008;
    pitch = Math.max(0.12, Math.min(1.28, pitch + (y - lastY) * 0.005));
    lastX = x; lastY = y;
    if (e.cancelable) e.preventDefault();
  };
  const onUp = () => { dragging = false; };

  canvas.addEventListener('pointerdown', onDown);
  window.addEventListener('pointermove', onMove);
  window.addEventListener('pointerup', onUp);
  canvas.style.cursor = 'grab';

  const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  if (reduce) { spin = false; draw(); } else loop();

  return () => {
    cancelAnimationFrame(raf);
    canvas.removeEventListener('pointerdown', onDown);
    window.removeEventListener('pointermove', onMove);
    window.removeEventListener('pointerup', onUp);
  };
}
