# MANGENESIS

**AI/ML + Space Technology for Manganese Reserve Identification and Production Continuity**
Smart India Hackathon · Problem Statement **26009** · Ministry of Steel / MOIL Limited

A control platform that does three things the problem statement asks for, on one surface:

1. **Identifies and maps manganese reserves** from surface and sub-surface indicators — host lithology, morphogenesis, regional strike, and fused multi-band satellite data.
2. **Predicts production shortfalls** seven days ahead from equipment downtime, weather and blasting-clearance constraints.
3. **Recommends corrective actions** — re-deploying equipment, re-sequencing benches, adjusting blast design — chosen by a constrained optimiser rather than a fixed list, and quantifies what each one recovers.

---

## Quick start

```bash
pip install -r requirements.txt
python run.py
```

Then open **http://localhost:8000**. Interactive API docs are at **/docs**.

The database seeds itself on first run. If a heavy ML dependency (`xgboost`, `lightgbm`) will not install on your machine, the platform still boots — the live-telemetry simulation is skipped and everything else works, because reserve targeting, forecasting, optimisation and reporting run on the pure-Python engine.

### Offline demo

```bash
python tools/build_static_demo.py
```

Writes `dist/mangenesis-demo.html` — the entire platform in one file with all 40 sites × 4 scenarios pre-computed. No server, no network. Open it from disk or put it on any static host.

---

## The data

Everything is built on the GSI manganese occurrence table supplied with the problem statement (`manganese ore loc.pdf`), transcribed verbatim into `backend/app/data/ore_sites.py`:

| Field | Use in the platform |
|---|---|
| `METALLOGENESIS` | Belt → regional strike azimuth and climatology |
| `LOCALITY`, `STATE`, `TOPOSHEET` | Site identity |
| `LATDD`, `LONDD` | Map position, monsoon/NDVI/LST climatology |
| `HOSTROCK` | Mn grade window + ore-body continuity prior |
| `MORPHOGENESIS` | Structural predictability multiplier |
| `FORMATION` | Stratigraphic context |

**33 GSI localities** across 11 metallogenic belts, plus **7 MOIL operating mines** not in that table (Kandri, Munsar, Beldongri, Chikla, Dongri Buzurg, Sitapatore, Parsoda) added with district-level coordinates so the shortfall half of the problem covers MOIL's real production base — **40 sites in total, 11 of them operating**.

Where the GSI register and MOIL's own district data disagree (the register places Balaghat in Chhattisgarh; the district is in Madhya Pradesh), the district wins and the register value is preserved in `register_state`. Coordinates carried at district precision are flagged `coord_precision: "approximate"`.

---

## How the analytics work

`backend/app/engine/site_engine.py` is one deterministic model that every screen reads from, so no two screens can disagree. Each `(site, scenario)` pair seeds its own PRNG, which is why a refresh never reshuffles the numbers and the printed PDF always matches the screen.

The headline figures form a single chain — change the scenario and the change propagates all the way to the rupee number:

```
rated capacity + scenario  →  daily deficit (T)
deficit                    →  shortfall probability (logistic)
deficit + crew/hour budget →  MILP recovered tonnage
recovered tonnage          →  annual value realisation
```

**Reserve targeting.** Target sectors are generated along the belt's regional strike, so the polygons follow real structural grain rather than scattering randomly. Reserve probability combines lithological continuity, a morphogenesis multiplier and a spectral-fusion term; tonnage comes from a tabular-lode volume (strike × width × depth × specific gravity) with SG derived from grade.

**Shortfall prediction.** A 14-day recorded series plus a 7-day forecast with quantile bands, shaped by the scenario's capacity loss and the site's monsoon climatology. Shortfall probability is a logistic function of the deficit as a share of target, nudged by how structurally predictable the ore body is.

**Root cause.** TreeSHAP-style attribution decomposes the probability into equipment downtime, weather, blasting clearance, haulage cycle time and grade variability.

**Corrective actions.** A **0/1 knapsack with two resource dimensions** (crew, shift-hours) — the exact structure a MILP solver is handed. The candidate set is small enough to solve exactly by enumeration rather than approximately by a heuristic. Concurrent interventions interfere with each other, so returns diminish and no combination fully closes a same-day gap.

**Value realisation.** Six pillars derived from the recovered tonnage, priced on Indian Bureau of Mines cost indices, against a stated per-mine deployment cost so the payback figure can be checked rather than believed.

Every model output is a decision-support estimate, not a statutory reserve statement under the Mineral Conservation and Development Rules. The platform says so on the ROI screen and in the report footer.

---

## Screens

| Screen | What it is for |
|---|---|
| **Command Centre** | The one-screen operating picture: KPIs, satellite reserve map, forecast, live risk factors |
| **Geospatial Explorer** | All 40 localities on a vector map of India, filterable by belt, searchable, click to select |
| **Enterprise Portfolio** | Every MOIL operating mine scored on the same models — where is the next tonne most at risk |
| **Reserve Intelligence** | Spectral fusion map, target sectors, drill assay register, rotating 3-D block model |
| **Production Forecast** | 14-day recorded extraction + 7-day prediction with quantile bands, day-by-day gap table |
| **Risk Analysis** | Shortfall donut, TreeSHAP attribution, live telemetry envelope, scenario sensitivity |
| **Action Centre** | MILP-ranked interventions with recovery, cost, crew and lead time; solver utilisation |
| **Alert Centre** | SMS / email / push channels, recipient lists, escalation thresholds, incident log |
| **ROI & Cost-Benefit** | Six value pillars, enterprise rollout roadmap, transparent assumptions |
| **Reports & Exports** | PDF brief, CSV extract, JSON snapshot, API reference |
| **Data Register** | The source occurrence table, searchable, and how each column drives the models |

The **ore-site selector** and **scenario selector** in the top bar drive every screen. Changing either re-computes the whole platform.

---

## Reports

`GET /api/report/brief.pdf?site=<id>&scenario=<id>` renders a five-page A4 operations brief with ReportLab — vector charts and typeset tables, no screenshots — covering executive summary, forecast, diagnostics, reserve register, corrective actions, value realisation and nearby occurrences.

`data.csv` gives a six-section flat extract for Excel; `data.json` gives the complete snapshot for ERP ingestion.

---

## API

| Endpoint | Returns |
|---|---|
| `GET /api/sites` | Occurrence register, filterable by belt / state / tier / free text |
| `GET /api/sites/belts` | Register grouped by metallogenic belt |
| `GET /api/sites/geojson` | Register as a GeoJSON FeatureCollection |
| `GET /api/sites/{id}` | One site with its full reserve profile |
| `GET /api/analytics/snapshot` | Everything the dashboard renders, for one site + scenario |
| `GET /api/analytics/{reserve,production,risk,actions,roi,alerts,telemetry}` | Individual model outputs |
| `GET /api/analytics/compare?sites=a,b,c` | Side-by-side scoring across mines |
| `GET /api/report/{brief.pdf,data.csv,data.json}` | Exports |
| `WS /ws/telemetry` | 1 Hz fleet, equipment and weather simulation |

---

## Layout

```
backend/app/
  data/ore_sites.py        GSI register + MOIL overlay, geochemistry priors
  engine/site_engine.py    the analytical core — one model, every screen
  routers/                 sites · analytics · reports · legacy telemetry
  simulators/, ml/         1 Hz fleet/weather/equipment simulation (optional)
static/
  css/mangenesis.css       design system — tokens, both themes
  js/core.js               icons, formatting, state store, API client
  js/viz.js                SVG charts + the 3-D ore-body canvas
  js/geomap.js             national vector map + Leaflet locality map
  js/views.js              the eleven screens
  js/app.js                shell, navigation, routing, telemetry socket
tools/build_static_demo.py offline single-file build
```

---

## Design

Dark-first control-room identity on Fuselab Creative's electric violet (`#7026FB`), with a full light theme that follows the viewer's system setting or the in-app toggle. Bricolage Grotesque for display, Manrope for body, JetBrains Mono for coordinates, assay values and identifiers — mining data is full of numbers that need to line up.

Semantic colour (good / warning / critical) is kept deliberately outside the accent hue, so "this needs attention" never reads as "this is branded". The map renders satellite imagery through Leaflet where tiles are reachable and falls back to a vector plan view where they are not, without changing what it shows.
