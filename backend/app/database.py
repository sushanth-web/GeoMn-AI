import os
from sqlalchemy import text
from sqlmodel import SQLModel, create_engine, Session

# Ensure data directory exists
os.makedirs('./data', exist_ok=True)

DATABASE_URL = 'sqlite:///./data/mining_ops.db'

# SQLite WAL mode and other performance settings
connect_args = {
    "check_same_thread": False,
    "timeout": 15
}

engine = create_engine(
    DATABASE_URL, 
    echo=False, 
    connect_args=connect_args
)

def init_db():
    from backend.app.models import DrillHole, DrillAssay, BlastEvent, Equipment, ProductionShift, WeatherReading, Alert
    SQLModel.metadata.create_all(engine)
    
    # Set Pragmas
    with engine.connect() as conn:
        conn.execute(text("PRAGMA journal_mode=WAL;"))
        conn.execute(text("PRAGMA synchronous=NORMAL;"))
        conn.execute(text("PRAGMA cache_size=-64000;"))

def get_session():
    with Session(engine) as session:
        yield session
