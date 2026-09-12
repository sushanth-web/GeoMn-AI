from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime

class DrillHole(SQLModel, table=True):
    __tablename__ = 'drill_holes'
    id: Optional[int] = Field(default=None, primary_key=True)
    hole_id: str = Field(unique=True, index=True)
    latitude: float
    longitude: float
    elevation: float
    total_depth: float
    azimuth: float = 0.0
    dip: float = -90.0

class DrillAssay(SQLModel, table=True):
    __tablename__ = 'drill_assays'
    id: Optional[int] = Field(default=None, primary_key=True)
    hole_id: str = Field(index=True)
    from_m: float
    to_m: float
    mn_pct: float
    fe_pct: float
    sio2_pct: float
    p_pct: float
    lithology: str

class BlastEvent(SQLModel, table=True):
    __tablename__ = 'blast_events'
    id: Optional[int] = Field(default=None, primary_key=True)
    blast_id: str = Field(unique=True, index=True)
    timestamp: str
    latitude: float
    longitude: float
    bench_id: str
    num_holes: int
    bench_height: float
    burden: float
    spacing: float
    powder_factor: float
    explosive_type: str
    fragmentation_x50: float
    ppv: float
    status: str = 'Fired'

class Equipment(SQLModel, table=True):
    __tablename__ = 'equipment'
    id: Optional[int] = Field(default=None, primary_key=True)
    equipment_id: str = Field(unique=True, index=True)
    equipment_type: str
    make: str
    model_name: str
    capacity: str
    status: str = 'Active'

class ProductionShift(SQLModel, table=True):
    __tablename__ = 'production_shifts'
    id: Optional[int] = Field(default=None, primary_key=True)
    shift_date: str
    shift_number: int
    target_tonnes: float
    actual_tonnes: float
    ore_tonnes: float
    ob_tonnes: float
    active_trucks: int
    active_shovels: int
    rainfall_mm: float
    blast_downtime_hrs: float
    equipment_downtime_hrs: float
    shortfall_risk: float = 0.0

class WeatherReading(SQLModel, table=True):
    __tablename__ = 'weather_readings'
    id: Optional[int] = Field(default=None, primary_key=True)
    timestamp: str
    rainfall_mm_hr: float
    cumulative_24h_mm: float
    temperature_c: float
    humidity_pct: float
    wind_speed_kmh: float
    tarp_level: str = 'GREEN'

class Alert(SQLModel, table=True):
    __tablename__ = 'alerts'
    id: Optional[int] = Field(default=None, primary_key=True)
    timestamp: str
    severity: str
    category: str
    source: str
    message: str
    corrective_action: str
    acknowledged: bool = False
