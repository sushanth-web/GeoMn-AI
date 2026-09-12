from fastapi import APIRouter, Request, HTTPException, Depends
from sqlmodel import Session, select
from pydantic import BaseModel
from backend.app.database import get_session
from backend.app.models import BlastEvent, ProductionShift, WeatherReading

router = APIRouter()

class AnomalyPayload(BaseModel):
    equipment_id: str
    anomaly_type: str

class ClearAnomalyPayload(BaseModel):
    equipment_id: str

class RainPayload(BaseModel):
    intensity: str

@router.get("/fleet")
async def get_fleet(request: Request):
    return request.app.state.current_fleet_state

@router.get("/fleet/summary")
async def get_fleet_summary(request: Request):
    fleet = request.app.state.current_fleet_state
    if not fleet:
        return {"active_count": 0, "avg_speed": 0, "total_payload": 0, "production_rate": 0}
    active = [f for f in fleet if f.get("status") == "Active"]
    avg_spd = sum(f.get("speed", 0) for f in active) / max(len(active), 1)
    return {
        "active_count": len(active),
        "avg_speed": avg_spd,
        "total_payload": sum(f.get("payload", 0) for f in active),
        "production_rate": request.app.state.fleet_sim.get_production_rate()
    }

@router.get("/blasts")
async def get_blasts(session: Session = Depends(get_session)):
    blasts = session.exec(select(BlastEvent).order_by(BlastEvent.timestamp.desc()).limit(20)).all()
    return blasts

@router.get("/blasts/upcoming")
async def get_upcoming_blasts(session: Session = Depends(get_session)):
    blasts = session.exec(select(BlastEvent).where(BlastEvent.status == "Planned")).all()
    return blasts

@router.get("/production/shifts")
async def get_production_shifts(session: Session = Depends(get_session)):
    shifts = session.exec(select(ProductionShift).order_by(ProductionShift.shift_date.desc()).limit(30)).all()
    return shifts

@router.get("/production/current")
async def get_current_production(request: Request):
    return request.app.state.current_production

@router.get("/weather/current")
async def get_current_weather(request: Request):
    return request.app.state.current_weather

@router.get("/weather/history")
async def get_weather_history(session: Session = Depends(get_session)):
    history = session.exec(select(WeatherReading).order_by(WeatherReading.timestamp.desc()).limit(168)).all()
    return history

@router.post("/simulate/anomaly")
async def inject_anomaly(payload: AnomalyPayload, request: Request):
    request.app.state.equipment_sim.inject_anomaly(payload.equipment_id, payload.anomaly_type)
    return {"status": "injected", "equipment_id": payload.equipment_id, "anomaly_type": payload.anomaly_type}

@router.post("/simulate/rain")
async def trigger_rain(payload: RainPayload, request: Request):
    request.app.state.weather_sim.trigger_rain_event(payload.intensity)
    return {"status": "triggered", "intensity": payload.intensity}

@router.post("/simulate/clear-anomaly")
async def clear_anomaly(payload: ClearAnomalyPayload, request: Request):
    request.app.state.equipment_sim.clear_anomaly(payload.equipment_id)
    return {"status": "cleared", "equipment_id": payload.equipment_id}
