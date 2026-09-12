"""Per-site analytics endpoints.

Everything is parameterised by (site, scenario) so the whole dashboard
re-computes coherently when the operator changes either one.
"""

from fastapi import APIRouter, HTTPException, Query

from backend.app.data.ore_sites import SITE_INDEX, get_site
from backend.app.engine import site_engine as eng

router = APIRouter()


def _resolve(site_id: str):
    if site_id and site_id.lower() not in SITE_INDEX:
        raise HTTPException(status_code=404, detail=f"Unknown ore site '{site_id}'")
    return get_site(site_id)


@router.get("/scenarios")
async def scenarios(site: str = Query(None)):
    s = _resolve(site)
    return {
        "scenarios": [
            {
                "id": v["id"], "label": v["label"], "summary": v["summary"],
                "detail": v["detail"], "severity": v["severity"],
                "capacity_loss_pct": round(v["capacity_loss"] * 100, 1),
                "root_cause": v["root_cause"],
                "risk_pct": eng.risk_profile(s, v["id"])["shortfall_probability"],
            }
            for v in eng.SCENARIOS.values()
        ]
    }


@router.get("/snapshot")
async def snapshot(site: str = Query(None), scenario: str = Query(None)):
    _resolve(site)
    return eng.full_snapshot(site, scenario)


@router.get("/reserve")
async def reserve(site: str = Query(None)):
    return eng.reserve_profile(_resolve(site))


@router.get("/production")
async def production(site: str = Query(None), scenario: str = Query(None),
                     history: int = Query(14, ge=7, le=60),
                     horizon: int = Query(7, ge=3, le=14)):
    return eng.production_series(_resolve(site), scenario or eng.DEFAULT_SCENARIO,
                                 history_days=history, forecast_days=horizon)


@router.get("/risk")
async def risk(site: str = Query(None), scenario: str = Query(None)):
    return eng.risk_profile(_resolve(site), scenario or eng.DEFAULT_SCENARIO)


@router.get("/actions")
async def actions(site: str = Query(None), scenario: str = Query(None)):
    return eng.action_plan(_resolve(site), scenario or eng.DEFAULT_SCENARIO)


@router.get("/roi")
async def roi(site: str = Query(None), scenario: str = Query(None)):
    return eng.roi_profile(_resolve(site), scenario or eng.DEFAULT_SCENARIO)


@router.get("/alerts")
async def alerts(site: str = Query(None), scenario: str = Query(None), limit: int = 12):
    return {"alerts": eng.alert_feed(_resolve(site), scenario or eng.DEFAULT_SCENARIO, limit)}


@router.get("/telemetry")
async def telemetry(site: str = Query(None), scenario: str = Query(None)):
    return {"signals": eng.telemetry(_resolve(site), scenario or eng.DEFAULT_SCENARIO)}


@router.get("/compare")
async def compare(sites: str = Query(..., description="Comma-separated site ids"),
                  scenario: str = Query(None)):
    """Side-by-side comparison used by the enterprise view."""
    ids = [i.strip() for i in sites.split(",") if i.strip()][:24]
    out = []
    for sid in ids:
        s = _resolve(sid)
        series = eng.production_series(s, scenario or eng.DEFAULT_SCENARIO)
        r = eng.risk_profile(s, scenario or eng.DEFAULT_SCENARIO)
        rz = eng.reserve_profile(s)
        roi_p = eng.roi_profile(s, scenario or eng.DEFAULT_SCENARIO)
        out.append({
            "id": s["id"], "name": s["name"], "belt": s["belt"], "state": s["state"],
            "tier": s["tier"], "target_t": series["target"],
            "risk_pct": r["shortfall_probability"], "deficit_t": r["deficit_t"],
            "grade_pct": rz["totals"]["weighted_mn_grade"],
            "indicated_t": rz["totals"]["total_indicated_t"],
            "roi_cr": roi_p["total_cr"], "colour": s["belt_colour"],
        })
    return {"rows": out}
