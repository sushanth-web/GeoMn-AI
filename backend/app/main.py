import asyncio
import json
import os
import time
from datetime import datetime

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlmodel import Session, select

from backend.app.database import init_db, engine, get_session
from backend.app.models import (
    DrillHole, DrillAssay, BlastEvent, Equipment,
    ProductionShift, WeatherReading, Alert
)

app = FastAPI(
    title="MANGENESIS — MOIL Manganese Reserve & Production Continuity Platform",
    version="2.4.0",
    description=(
        "AI/ML + space-technology control platform for MOIL Limited.\n\n"
        "* **Ore Site Register** — 40 manganese localities across 11 metallogenic belts, "
        "from the GSI occurrence table plus MOIL's operating mine portfolio.\n"
        "* **Site Analytics** — reserve targeting, 7-day production forecasting, TreeSHAP "
        "root-cause attribution, MILP corrective-action optimisation and value realisation, "
        "all parameterised by (site, scenario).\n"
        "* **Reports** — downloadable PDF brief, CSV extract and JSON snapshot.\n"
        "* **Live telemetry** — 1 Hz fleet, equipment and weather simulation over WebSocket."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
def read_root():
    return FileResponse("static/index.html")


# --- Import routers ---
from backend.app.routers import satellite, geology, operations, predictions, sites, analytics, reports
from backend.app.routers.websocket import manager, websocket_telemetry

app.include_router(satellite.router, prefix="/api/layers", tags=["Satellite Layers"])
app.include_router(geology.router, prefix="/api", tags=["Geology"])
app.include_router(operations.router, prefix="/api", tags=["Operations"])
app.include_router(predictions.router, prefix="/api/predict", tags=["Predictions"])
app.include_router(sites.router, prefix="/api", tags=["Ore Site Register"])
app.include_router(analytics.router, prefix="/api/analytics", tags=["Site Analytics"])
app.include_router(reports.router, prefix="/api/report", tags=["Reports"])


@app.get("/api/health")
def health():
    from backend.app.data.ore_sites import registry_stats
    return {
        "status": "ok",
        "service": "MANGENESIS",
        "version": app.version,
        "registry": registry_stats(),
        "simulation": {
            "telemetry_loop": bool(getattr(app.state, "tick_count", 0)),
            "ticks": getattr(app.state, "tick_count", 0),
        },
    }

# WebSocket endpoint
app.add_api_websocket_route("/ws/telemetry", websocket_telemetry)


import sys
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# --- Startup ---
@app.on_event("startup")
async def on_startup():
    """Initialise database, simulators, ML models and the telemetry loop.

    The legacy simulation stack is optional: if a heavy ML dependency is not
    installed, the platform still boots and every site-analytics and report
    endpoint keeps working, because those run on the pure-Python engine in
    `backend/app/engine/site_engine.py`.
    """
    os.makedirs("data", exist_ok=True)
    app.state.tick_count = 0
    app.state.telemetry_enabled = False
    print("=" * 64)
    print("  MANGENESIS  ·  MOIL Limited / Ministry of Steel")
    print("=" * 64)

    from backend.app.data.ore_sites import registry_stats
    st = registry_stats()
    print(f"  [+] Ore register  : {st['total_sites']} localities · "
          f"{st['operating_mines']} operating mines · {st['belts']} belts")

    try:
        print("  [-] Creating database tables...")
        init_db()

        with Session(engine) as session:
            hole = session.exec(select(DrillHole)).first()
            if not hole:
                print("  [-] Seeding database...")
                from backend.seed_database import seed_all
                seed_all(engine)
            else:
                print("  [+] Database already seeded.")
    except Exception as e:
        print(f"  [!] Database bootstrap skipped: {e}")

    try:
        print("  [-] Starting simulators and ML models...")
        from backend.app.simulators.satellite_sim import SatelliteSimulator
        from backend.app.simulators.fleet_sim import FleetSimulator
        from backend.app.simulators.equipment_sim import EquipmentSimulator
        from backend.app.simulators.weather_sim import WeatherSimulator
        from backend.app.ml.reserve_model import ReserveModel
        from backend.app.ml.shortfall_model import ShortfallModel
        from backend.app.ml.health_model import HealthModel

        app.state.satellite_sim = SatelliteSimulator(width=512, height=512, seed=42)
        app.state.fleet_sim = FleetSimulator(num_trucks=12)
        app.state.equipment_sim = EquipmentSimulator(
            equipment_ids=[f"HT-{101 + i}" for i in range(12)])
        app.state.weather_sim = WeatherSimulator(seed=42)

        app.state.reserve_model = ReserveModel()
        with Session(engine) as session:
            holes = session.exec(select(DrillHole)).all()
            assays = session.exec(select(DrillAssay)).all()
            app.state.reserve_model.train(holes, assays)

        app.state.shortfall_model = ShortfallModel()
        with Session(engine) as session:
            shifts = session.exec(select(ProductionShift)).all()
            app.state.shortfall_model.train([
                {
                    "shift_number": s_.shift_number,
                    "active_trucks": s_.active_trucks,
                    "active_shovels": s_.active_shovels,
                    "rainfall_mm": s_.rainfall_mm,
                    "blast_downtime_hrs": s_.blast_downtime_hrs,
                    "equipment_downtime_hrs": s_.equipment_downtime_hrs,
                    "target_tonnes": s_.target_tonnes,
                    "actual_tonnes": s_.actual_tonnes,
                }
                for s_ in shifts
            ])

        app.state.health_model = HealthModel()
        app.state.health_model.train([])
        app.state.telemetry_enabled = True
        print("  [+] Simulators and ML models ready.")
    except Exception as e:
        print(f"  [!] Live telemetry stack unavailable ({type(e).__name__}: {e})")
        print("      Site analytics, reserve targeting and reports are unaffected.")

    app.state.ws_manager = manager
    app.state.current_fleet_state = []
    app.state.current_telemetry = []
    app.state.current_weather = {}
    app.state.current_production = {
        "shift_number": 1, "shift_elapsed_hrs": 0.0, "shift_actual_tonnes": 0.0,
        "shift_target_tonnes": 1350.0, "crusher_tph": 0.0,
        "shortfall_risk_pct": 0.0, "top_risk_factors": [],
    }
    app.state.shift_start_time = time.time()
    app.state.shift_tonnes_accumulated = 0.0

    if app.state.telemetry_enabled:
        asyncio.create_task(simulation_loop())

    print("=" * 64)
    print("  Ready  ->  http://localhost:8000        API docs -> /docs")
    print("=" * 64)


async def simulation_loop():
    """Main simulation loop running at 1 Hz."""
    while True:
        try:
            if not getattr(app.state, "telemetry_enabled", False):
                await asyncio.sleep(2.0)
                continue
            app.state.tick_count += 1

            # 1. Tick weather
            weather = app.state.weather_sim.tick(dt=1.0)
            app.state.current_weather = weather
            rain_factor = app.state.weather_sim.get_rain_factor()

            # 2. Tick fleet (affected by rain)
            fleet_state = app.state.fleet_sim.tick(dt=1.0, rain_factor=rain_factor)
            app.state.current_fleet_state = fleet_state

            # 3. Tick equipment telemetry
            telemetry = app.state.equipment_sim.tick(fleet_state)
            app.state.current_telemetry = telemetry

            # 4. Update production tracking
            production_rate = app.state.fleet_sim.get_production_rate()
            elapsed = time.time() - app.state.shift_start_time
            elapsed_hrs = elapsed / 3600.0

            # Accumulate tonnes (production_rate is tonnes/hour, tick is 1 second)
            # Speed up simulation: 1 real second = ~30 simulated seconds for demo
            sim_speed = 30.0
            app.state.shift_tonnes_accumulated += (production_rate / 3600.0) * sim_speed
            
            # Determine shift number (8-hour shifts, accelerated)
            shift_num = int((elapsed_hrs * sim_speed) / 8.0) % 3 + 1
            shift_elapsed = (elapsed_hrs * sim_speed) % 8.0

            # Reset tonnes on shift change
            if shift_num != app.state.current_production.get("shift_number", 1):
                app.state.shift_tonnes_accumulated = 0.0

            target_tonnes = 1350.0
            app.state.current_production = {
                "shift_number": shift_num,
                "shift_elapsed_hrs": round(shift_elapsed, 2),
                "shift_actual_tonnes": round(app.state.shift_tonnes_accumulated, 1),
                "shift_target_tonnes": target_tonnes,
                "crusher_tph": round(production_rate, 1),
                "shortfall_risk_pct": 0.0,
                "top_risk_factors": [],
            }

            # 5. Run ML predictions every 5 seconds
            alerts = []
            corrective_actions = []

            if app.state.tick_count % 5 == 0:
                # Shortfall prediction
                avg_health = 100.0
                if telemetry:
                    avg_health = sum(t.get("health_pct", 100) for t in telemetry) / len(telemetry)
                
                shortfall_input = {
                    "shift_number": shift_num,
                    "shift_elapsed_hrs": shift_elapsed,
                    "current_tonnes": app.state.shift_tonnes_accumulated,
                    "active_trucks": sum(1 for t in fleet_state if t.get("status") not in ("QUEUING",)),
                    "active_shovels": 3,
                    "rainfall_mm_hr": weather.get("rainfall_mm_hr", 0),
                    "queue_length": app.state.fleet_sim.get_queue_length(),
                    "equipment_health_avg": avg_health,
                    "blast_today": False,
                    "target_tonnes": target_tonnes,
                }
                shortfall_pred = app.state.shortfall_model.predict(shortfall_input)
                app.state.current_production["shortfall_risk_pct"] = shortfall_pred["shortfall_risk_pct"]
                app.state.current_production["top_risk_factors"] = shortfall_pred["top_risk_factors"]
                corrective_actions = shortfall_pred.get("corrective_actions", [])

                # Equipment health prediction
                if telemetry:
                    health_results = app.state.health_model.predict(telemetry)
                    for hr in health_results:
                        if hr.get("is_anomaly"):
                            alerts.append({
                                "id": f"ALT-{app.state.tick_count}-{hr['equipment_id']}",
                                "severity": "CRITICAL" if hr["health_pct"] < 40 else "WARNING",
                                "category": "EQUIPMENT",
                                "message": hr.get("alert_message", f"{hr['equipment_id']} anomaly detected"),
                                "corrective_action": hr.get("recommended_action", "Schedule maintenance"),
                                "timestamp": datetime.now().strftime("%H:%M:%S"),
                            })

                # Weather alerts
                tarp = weather.get("tarp_level", "GREEN")
                if tarp == "RED":
                    alerts.append({
                        "id": f"ALT-WEATHER-{app.state.tick_count}",
                        "severity": "CRITICAL",
                        "category": "WEATHER",
                        "message": f"TARP RED: Rainfall {weather.get('rainfall_mm_hr', 0):.1f} mm/hr — Full pit evacuation required",
                        "corrective_action": "Evacuate all HEMM to stable ground; suspend blasting; activate dewatering pumps",
                        "timestamp": datetime.now().strftime("%H:%M:%S"),
                    })
                elif tarp == "AMBER":
                    alerts.append({
                        "id": f"ALT-WEATHER-{app.state.tick_count}",
                        "severity": "WARNING",
                        "category": "WEATHER",
                        "message": f"TARP AMBER: Rainfall {weather.get('rainfall_mm_hr', 0):.1f} mm/hr — Haulage restricted",
                        "corrective_action": "Suspend haulage on steep grades; reduce speed limits to 20 km/h",
                        "timestamp": datetime.now().strftime("%H:%M:%S"),
                    })

            # 6. Build WebSocket broadcast packet
            broadcast_data = {
                "timestamp": datetime.now().isoformat(),
                "fleet": fleet_state,
                "equipment_health": [
                    {
                        "equipment_id": t.get("equipment_id", ""),
                        "health_pct": t.get("health_pct", 100),
                        "engine_temp_c": t.get("engine_temp_c", 0),
                        "hydraulic_temp_c": t.get("hydraulic_temp_c", 0),
                        "vibration_rms": t.get("vibration_rms", 0),
                    }
                    for t in telemetry
                ],
                "production": app.state.current_production,
                "weather": weather,
                "alerts": alerts,
                "corrective_actions": corrective_actions,
            }

            # 7. Broadcast to all connected WebSocket clients
            await manager.broadcast(broadcast_data)

        except Exception as e:
            print(f"  [!] Simulation loop error: {e}")

        await asyncio.sleep(1.0)
