from fastapi import APIRouter, Request, HTTPException, Depends
from sqlmodel import Session, select

from backend.app.database import get_session
from backend.app.models import ProductionShift

router = APIRouter()


@router.get("/shortfall")
async def get_shortfall(request: Request):
    try:
        prod = request.app.state.current_production or {}
        weather = request.app.state.current_weather or {}

        fleet_sim = getattr(request.app.state, "fleet_sim", None)
        health_model = getattr(request.app.state, "health_model", None)
        telemetry = getattr(request.app.state, "current_telemetry", [])

        health_scores = []
        if health_model:
            health_scores = health_model.predict(telemetry)

        avg_health = sum(h["health_pct"] for h in health_scores) / max(len(health_scores), 1) if health_scores else 100

        active_trucks = 0
        if fleet_sim and hasattr(fleet_sim, "trucks"):
            active_trucks = len([t for t in fleet_sim.trucks if getattr(t, "status", "Active") == "Active"])
            queue_length = fleet_sim.get_queue_length()
        else:
            queue_length = 0

        current_state = {
            "shift_number": prod.get("shift_number", 1),
            "shift_elapsed_hrs": prod.get("shift_elapsed_hrs", 4.0),
            "current_tonnes": prod.get("actual_tonnes", 0),
            "target_tonnes": prod.get("target_tonnes", 10000),
            "active_trucks": active_trucks,
            "active_shovels": 3,
            "rainfall_mm_hr": weather.get("rainfall_mm_hr", 0),
            "queue_length": queue_length,
            "equipment_health_avg": avg_health,
            "blast_today": False
        }

        return request.app.state.shortfall_model.predict(current_state)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/forecast")
async def get_forecast(request: Request, session: Session = Depends(get_session), n_ahead: int = 3):
    """Multi-shift production outlook: recent actual/target history (for
    charting) plus the next N shifts projected with confidence bands."""
    try:
        n_ahead = max(1, min(n_ahead, 10))

        history = session.exec(
            select(ProductionShift)
            .order_by(ProductionShift.shift_date.desc(), ProductionShift.shift_number.desc())
            .limit(15)
        ).all()
        history = list(reversed(history))  # chronological order for charting

        historical = [
            {
                "label": f"{h.shift_date} S{h.shift_number}",
                "actual_tonnes": round(h.actual_tonnes, 1),
                "target_tonnes": round(h.target_tonnes, 1),
            }
            for h in history
        ]

        forecast = request.app.state.shortfall_model.forecast_shifts(n_ahead=n_ahead)

        return {"historical": historical, "forecast": forecast}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/accuracy")
async def get_accuracy(request: Request):
    """Backtested accuracy of the shortfall/forecast model, for a trust
    indicator in the UI (walk-forward MAPE + shortfall-call accuracy)."""
    try:
        return request.app.state.shortfall_model.get_accuracy_report()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/reserves")
async def get_reserves(request: Request):
    try:
        return request.app.state.reserve_model.get_reserve_summary()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/equipment-health")
async def get_equipment_health(request: Request):
    try:
        return request.app.state.health_model.predict(request.app.state.current_telemetry)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/corrective-actions")
async def get_corrective_actions(request: Request):
    try:
        shortfall_pred = await get_shortfall(request)
        health = await get_equipment_health(request)

        actions = shortfall_pred.get("corrective_actions", [])
        for h in health:
            if h.get("is_anomaly"):
                actions.append(f"Equipment {h['equipment_id']}: {h['recommended_action']}")

        return {"actions": actions}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
