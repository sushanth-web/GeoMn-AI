"""
Build a single self-contained HTML demo of MANGENESIS.

The live platform is a FastAPI app: the browser calls /api/... and the
Python engine answers. For a demo that has to run with no server at all —
a hosted page, a USB stick, a projector in a room with no network — this
script pre-computes every (site, scenario) answer the API would give,
embeds them, and stubs the fetch layer so the exact same front-end code
reads from the bundle instead of the network.

Nothing about the UI is forked. One codebase, two delivery modes.

    python tools/build_static_demo.py [outfile]
"""

from __future__ import annotations

import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.app.data.ore_sites import ORE_SITES, belts, registry_stats  # noqa: E402
from backend.app.engine import site_engine as eng  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC = os.path.join(ROOT, "static")

# Modules in dependency order. They are concatenated into one module script,
# so the import/export lines are stripped — every exported name is unique
# across the four files, which is what makes the flattening safe.
MODULES = ["core.js", "viz.js", "geomap.js", "views.js", "app.js"]


def flatten_modules() -> str:
    out = []
    for name in MODULES:
        src = open(os.path.join(STATIC, "js", name), encoding="utf-8").read()
        src = re.sub(r"^\s*import\s+[^;]+;\s*$", "", src, flags=re.M)
        src = re.sub(r"^export\s+(?=(const|let|var|function|async|class))", "", src, flags=re.M)
        src = re.sub(r"^export\s*\{[^}]*\};?\s*$", "", src, flags=re.M)
        out.append(f"\n/* ==== {name} ==== */\n{src}")
    return "\n".join(out)


def build_bundle() -> dict:
    """Reserve profiles do not vary with scenario, so they are stored once
    per site and re-attached at read time. That alone removes ~40% of the
    payload."""
    reserve = {}
    snaps = {}

    for site in ORE_SITES:
        sid = site["id"]
        reserve[sid] = eng.reserve_profile(site)
        snaps[sid] = {}
        for scen in eng.SCENARIOS:
            snap = eng.full_snapshot(sid, scen)
            snap.pop("reserve", None)
            snaps[sid][scen] = snap

    sites_payload = {
        "count": len(ORE_SITES),
        "stats": registry_stats(),
        "sites": [
            {
                "id": s["id"], "name": s["name"], "display": s["display"],
                "locality": s["locality"], "belt": s["belt"], "state": s["state"],
                "district": s["district"], "tier": s["tier"], "source": s["source"],
                "lat": s["lat"], "lon": s["lon"], "toposheet": s["toposheet"],
                "hostrock": s["hostrock"], "formation": s["formation"],
                "morphogenesis": s["morphogenesis"],
                "rated_tpd": s["rated_tpd"] or int(eng.daily_target(s)),
                "belt_colour": s["belt_colour"], "coord_precision": s["coord_precision"],
            }
            for s in ORE_SITES
        ],
    }

    return {
        "belts": {"belts": belts(), "stats": registry_stats()},
        "sites": sites_payload,
        "reserve": reserve,
        "snapshots": snaps,
    }


SHIM = """
/* ---- Static demo shim -------------------------------------------------
   Re-implements the handful of API calls the UI makes, reading from the
   embedded bundle. Same shapes, same field names, so no view code changes.
   A live deployment (python run.py) skips this file entirely and talks to
   the FastAPI backend over HTTP. */
(function () {
  const B = window.__MANGENESIS_BUNDLE__;

  function snapshot(site, scenario) {
    const bySite = B.snapshots[site] || B.snapshots[Object.keys(B.snapshots)[0]];
    const snap = bySite[scenario] || bySite[Object.keys(bySite)[0]];
    return Object.assign({}, snap, { reserve: B.reserve[snap.site.id] });
  }

  window.__MANGENESIS_API__ = {
    belts: () => Promise.resolve(B.belts),
    sites: () => Promise.resolve(B.sites),
    site: (id) => Promise.resolve({ site: B.sites.sites.find(s => s.id === id), reserve: B.reserve[id] }),
    snapshot: (site, scenario) => Promise.resolve(snapshot(site, scenario)),
    compare: (ids, scenario) => Promise.resolve({
      rows: ids.map(id => {
        const s = snapshot(id, scenario);
        return {
          id: s.site.id, name: s.site.name, belt: s.site.belt, state: s.site.state,
          tier: s.site.tier, target_t: s.production.target,
          risk_pct: s.risk.shortfall_probability, deficit_t: s.risk.deficit_t,
          grade_pct: s.reserve.totals.weighted_mn_grade,
          indicated_t: s.reserve.totals.total_indicated_t,
          roi_cr: s.roi.total_cr, colour: s.site.belt_colour,
        };
      }),
    }),
    health: () => Promise.resolve({ status: 'static-demo' }),
    reportURL: () => null,
  };
})();
"""

PAGE = """<style>
{css}
</style>

<div class="aurora" aria-hidden="true"></div>

<div class="shell">
  <aside class="rail" id="rail">
    <div class="rail__brand">
      <span class="mark" aria-hidden="true">M</span>
      <div>
        <div class="rail__name">MANGENESIS <span class="tag" style="font-size:9px;padding:2px 6px">v2.4</span></div>
        <div class="rail__org">MOIL Limited &middot; Ministry of Steel</div>
      </div>
    </div>
    <nav class="rail__scroll" id="rail-nav" aria-label="Platform sections"></nav>
    <div class="rail__foot">
      <div class="telemetry-chip">
        <span class="dot" style="color:var(--good)"></span>
        <span style="flex:1;min-width:0">
          <span class="telemetry-chip__t">Space Telemetry</span>
          <span class="telemetry-chip__s" id="tele-sub">Sentinel-2 &middot; 10 m archive</span>
        </span>
        <span class="tag tag--plain" id="tele-state">Snapshot</span>
      </div>
    </div>
  </aside>

  <div class="scrim" id="scrim" hidden></div>

  <main>
    <div class="topbar">
      <button class="iconbtn railtoggle" id="menu-btn" aria-label="Open navigation">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"><path d="M3 12h18M3 6h18M3 18h18"/></svg>
      </button>

      <div class="selector">
        <button class="selector__btn" id="site-btn" aria-expanded="false" aria-haspopup="listbox">
          <span class="selector__icon" aria-hidden="true">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">
              <path d="M3 21h18M5 21V7l7-4 7 4v14M9 21v-4h6v4M9 10h.01M15 10h.01"/></svg>
          </span>
          <span class="selector__txt">
            <span class="selector__lead" id="site-lead">Loading&hellip;</span>
            <span class="selector__sub" id="site-sub">Ore site register</span>
          </span>
          <svg class="selector__caret" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M6 9l6 6 6-6"/></svg>
        </button>
        <div class="pop" id="site-pop" role="listbox" aria-label="Select ore site">
          <div class="pop__head">
            <input class="pop__search" id="site-q" type="search" placeholder="Search locality, belt or state&hellip;" aria-label="Search ore sites"/>
            <div class="pop__filters">
              <button class="chipbtn is-on" data-filter="all" type="button">All sites</button>
              <button class="chipbtn" data-filter="operating" type="button">Operating mines</button>
              <button class="chipbtn" data-filter="exploration" type="button">Exploration</button>
              <button class="chipbtn" data-filter="occurrence" type="button">Occurrences</button>
            </div>
          </div>
          <div class="pop__body" id="site-pop-body"></div>
        </div>
      </div>

      <div class="selector">
        <button class="selector__btn" id="sc-btn" aria-expanded="false" aria-haspopup="listbox">
          <span class="selector__icon" aria-hidden="true" style="background:var(--crit-bg);color:var(--crit)">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">
              <path d="M4 21v-7M4 10V3M12 21v-9M12 8V3M20 21v-5M20 12V3M1 14h6M9 8h6M17 16h6"/></svg>
          </span>
          <span class="selector__txt">
            <span class="selector__lead" id="sc-lead">Scenario</span>
            <span class="selector__sub" id="sc-sub">&mdash;</span>
          </span>
          <span class="tag" id="sc-risk">&mdash;</span>
          <svg class="selector__caret" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M6 9l6 6 6-6"/></svg>
        </button>
        <div class="pop" id="sc-pop" role="listbox" aria-label="Select operating scenario">
          <div class="pop__head">
            <span class="tiny muted">Every model on the platform re-computes when the scenario changes.</span>
          </div>
          <div class="pop__body" id="sc-pop-body"></div>
        </div>
      </div>

      <span class="topbar__spacer"></span>
      <span class="pill pill--mono" id="clock" aria-label="Local time">--:--:--</span>
      <a class="btn btn--primary" id="report-link" href="#reports">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
          <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M7 10l5 5 5-5M12 15V3"/></svg>
        Download report
      </a>
      <button class="iconbtn" id="alert-btn" aria-label="Open alert centre">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">
          <path d="M18 8a6 6 0 10-12 0c0 7-3 9-3 9h18s-3-2-3-9M13.7 21a2 2 0 01-3.4 0"/></svg>
        <span class="iconbtn__count" id="alert-count">0</span>
      </button>
      <button class="iconbtn" id="theme-btn" aria-label="Switch theme"></button>
    </div>

    <div class="view" id="view">
      <div class="empty">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
          <path d="M4 4h16v16H4zM9 9h6v6H9z"/></svg>
        <p>Initialising the control platform&hellip;</p>
      </div>
    </div>
  </main>
</div>

<script id="mangenesis-bundle" type="application/json">{bundle}</script>
<script>
window.__MANGENESIS_BUNDLE__ = JSON.parse(document.getElementById('mangenesis-bundle').textContent);
{shim}
</script>
<script type="module">
{js}
</script>
"""


DOC_HEAD = """<!DOCTYPE html>
<html lang="en" data-theme="dark">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<meta name="theme-color" content="#7026FB"/>
<meta name="description" content="MANGENESIS — AI/ML and space-technology control platform for identifying manganese reserves and pre-empting production shortfalls across MOIL Limited's mines."/>
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect width='32' height='32' rx='8' fill='%237026FB'/%3E%3Ctext x='16' y='23' font-family='system-ui' font-size='19' font-weight='800' fill='white' text-anchor='middle'%3EM%3C/text%3E%3C/svg%3E"/>
<style>html,body{margin:0}</style>
</head>
<body>
"""
DOC_TAIL = "\n</body>\n</html>\n"


def main():
    """Writes two files from one build:

    dist/mangenesis-demo.html  a complete HTML document — opens from disk,
                               a USB stick, or any static host.
    dist/mangenesis-page.html  the same page as a body fragment, for hosts
                               that supply their own document skeleton.
    """
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "dist", "mangenesis-demo.html")
    os.makedirs(os.path.dirname(out), exist_ok=True)

    css = open(os.path.join(STATIC, "css", "mangenesis.css"), encoding="utf-8").read()
    css = ('@import url("https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,600;'
           '12..96,700;12..96,800&family=Manrope:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600;700'
           '&display=swap");\n' + css)

    js = flatten_modules()
    # In the static build the API layer is the embedded bundle.
    js = js.replace("export const api = {", "const api = window.__MANGENESIS_API__ || {")
    js = js.replace("const api = {", "const api = window.__MANGENESIS_API__ || {", 1)

    bundle = json.dumps(build_bundle(), separators=(",", ":"), default=str)
    bundle = bundle.replace("</script>", "<\\/script>")

    page = PAGE.replace("{css}", css).replace("{bundle}", bundle) \
               .replace("{shim}", SHIM).replace("{js}", js)
    page = "<title>MANGENESIS Control Platform</title>\n" + page

    with open(out, "w", encoding="utf-8") as f:
        f.write(DOC_HEAD + page + DOC_TAIL)

    frag = os.path.join(os.path.dirname(out), "mangenesis-page.html")
    with open(frag, "w", encoding="utf-8") as f:
        f.write(page)

    for f_ in (out, frag):
        print(f"[+] {f_}  ({os.path.getsize(f_) / 1024:,.0f} KB)")
    print(f"    {len(ORE_SITES)} sites x {len(eng.SCENARIOS)} scenarios pre-computed")


if __name__ == "__main__":
    main()
