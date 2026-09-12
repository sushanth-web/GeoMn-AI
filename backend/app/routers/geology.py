from fastapi import APIRouter, Request, HTTPException, Depends
from sqlmodel import Session, select
from backend.app.database import get_session
from backend.app.models import DrillHole, DrillAssay

router = APIRouter()

@router.get("/drillholes")
async def get_drillholes(session: Session = Depends(get_session)):
    try:
        holes = session.exec(select(DrillHole)).all()
        features = []
        for h in holes:
            features.append({
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [h.longitude, h.latitude]
                },
                "properties": {
                    "hole_id": h.hole_id,
                    "elevation": h.elevation,
                    "total_depth": h.total_depth
                }
            })
        return {"type": "FeatureCollection", "features": features}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/drillholes/{hole_id}/assays")
async def get_assays(hole_id: str, session: Session = Depends(get_session)):
    try:
        assays = session.exec(select(DrillAssay).where(DrillAssay.hole_id == hole_id)).all()
        assays = sorted(assays, key=lambda x: x.from_m)
        return assays
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/summary")
async def get_geology_summary(request: Request):
    try:
        return request.app.state.reserve_model.get_reserve_summary()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/mine-boundary")
async def get_mine_boundary():
    return {
        "type": "Feature",
        "geometry": {
            "type": "Polygon",
            "coordinates": [[
                [79.6750, 21.5440],
                [79.6917, 21.5440],
                [79.6917, 21.5560],
                [79.6750, 21.5560],
                [79.6750, 21.5440]
            ]]
        },
        "properties": {
            "name": "MOIL Mine Boundary"
        }
    }
