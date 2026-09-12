"""Ore-site register endpoints — the data behind the map's location selector."""

from fastapi import APIRouter, HTTPException, Query

from backend.app.data.ore_sites import (
    ORE_SITES, SITE_INDEX, belts, get_site, registry_stats,
)
from backend.app.engine.site_engine import daily_target, reserve_profile

router = APIRouter()


@router.get("/sites")
async def list_sites(
    belt: str = Query(None, description="Filter by metallogenic belt"),
    state: str = Query(None, description="Filter by state"),
    tier: str = Query(None, description="operating | exploration | occurrence"),
    q: str = Query(None, description="Free-text search on locality or host rock"),
):
    rows = ORE_SITES
    if belt:
        rows = [s for s in rows if s["belt"].lower() == belt.lower()]
    if state:
        rows = [s for s in rows if s["state"].lower() == state.lower()]
    if tier:
        rows = [s for s in rows if s["tier"] == tier.lower()]
    if q:
        needle = q.lower()
        rows = [
            s for s in rows
            if needle in s["locality"].lower()
            or needle in s["name"].lower()
            or needle in s["hostrock"].lower()
            or needle in s["belt"].lower()
            or needle in s["state"].lower()
        ]
    return {
        "count": len(rows),
        "stats": registry_stats(),
        "sites": [
            {
                "id": s["id"], "name": s["name"], "display": s["display"],
                "locality": s["locality"], "belt": s["belt"], "state": s["state"],
                "district": s["district"], "tier": s["tier"], "source": s["source"],
                "lat": s["lat"], "lon": s["lon"], "toposheet": s["toposheet"],
                "hostrock": s["hostrock"], "formation": s["formation"],
                "morphogenesis": s["morphogenesis"],
                "rated_tpd": s["rated_tpd"] or int(daily_target(s)),
                "belt_colour": s["belt_colour"],
                "coord_precision": s["coord_precision"],
            }
            for s in rows
        ],
    }


@router.get("/sites/belts")
async def list_belts():
    """Grouped register used to build the map location dropdown."""
    return {"belts": belts(), "stats": registry_stats()}


@router.get("/sites/geojson")
async def sites_geojson():
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [s["lon"], s["lat"]]},
                "properties": {
                    "id": s["id"], "name": s["name"], "belt": s["belt"],
                    "state": s["state"], "tier": s["tier"], "hostrock": s["hostrock"],
                    "formation": s["formation"], "colour": s["belt_colour"],
                    "toposheet": s["toposheet"], "lat_dms": s["lat_dms"], "lon_dms": s["lon_dms"],
                },
            }
            for s in ORE_SITES
        ],
    }


@router.get("/sites/{site_id}")
async def site_detail(site_id: str):
    if site_id.lower() not in SITE_INDEX:
        raise HTTPException(status_code=404, detail=f"Unknown ore site '{site_id}'")
    site = get_site(site_id)
    return {"site": site, "daily_target_t": daily_target(site), "reserve": reserve_profile(site)}
