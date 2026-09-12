"""Downloadable reporting.

    GET /api/report/brief.pdf   — branded multi-section operations brief
    GET /api/report/data.csv    — flat analytics extract
    GET /api/report/data.json   — full snapshot for downstream systems

The PDF is generated with ReportLab so it needs no headless browser, and it
is built from exactly the same `full_snapshot()` the dashboard renders, so
the printed figures always agree with the screen.
"""

from __future__ import annotations

import csv
import io
import json
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response

from backend.app.data.ore_sites import SITE_INDEX
from backend.app.engine import site_engine as eng

router = APIRouter()

INK = "#0B0714"
PURPLE = "#7026FB"
LILAC = "#9D5CFF"
MUTED = "#6B6580"
LINE = "#E4E0EC"


def _guard(site_id: str):
    if site_id and site_id.lower() not in SITE_INDEX:
        raise HTTPException(status_code=404, detail=f"Unknown ore site '{site_id}'")


@router.get("/data.json")
async def report_json(site: str = Query(None), scenario: str = Query(None)):
    _guard(site)
    snap = eng.full_snapshot(site, scenario)
    name = snap["site"]["id"]
    body = json.dumps(snap, indent=2, default=str)
    return Response(
        content=body, media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="mangenesis-{name}-snapshot.json"'},
    )


@router.get("/data.csv")
async def report_csv(site: str = Query(None), scenario: str = Query(None)):
    _guard(site)
    snap = eng.full_snapshot(site, scenario)
    buf = io.StringIO()
    w = csv.writer(buf)

    s, sc = snap["site"], snap["scenario"]
    w.writerow(["MANGENESIS — Manganese Reserve & Production Continuity Extract"])
    w.writerow(["Generated", snap["generated_at"]])
    w.writerow(["Site", s["name"], "Belt", s["belt"], "State", s["state"]])
    w.writerow(["Latitude", s["lat"], "Longitude", s["lon"], "Toposheet", s["toposheet"]])
    w.writerow(["Host rock", s["hostrock"], "Formation", s["formation"], "Morphogenesis", s["morphogenesis"]])
    w.writerow(["Scenario", sc["label"], "Root cause", sc["root_cause"]])
    w.writerow([])

    w.writerow(["SECTION", "PRODUCTION SERIES"])
    w.writerow(["date", "label", "series", "tonnes", "lower", "upper", "target"])
    for h in snap["production"]["history"]:
        w.writerow([h["date"], h["label"], "actual", h["actual"], "", "", h["target"]])
    for f in snap["production"]["forecast"]:
        w.writerow([f["date"], f["label"], "forecast", f["forecast"], f["lower"], f["upper"], f["target"]])
    w.writerow([])

    w.writerow(["SECTION", "RESERVE ZONES"])
    w.writerow(["zone_id", "name", "probability_pct", "class", "mn_grade_pct",
                "tonnage_t", "strike_length_m", "avg_width_m", "depth_extent_m", "lat", "lon"])
    for z in snap["reserve"]["zones"]:
        w.writerow([z["id"], z["name"], z["probability_pct"], z["class"], z["mn_grade_pct"],
                    z["tonnage_t"], z["strike_length_m"], z["avg_width_m"], z["depth_extent_m"],
                    z["centroid"][0], z["centroid"][1]])
    w.writerow([])

    w.writerow(["SECTION", "DRILL HOLES"])
    w.writerow(["hole_id", "lat", "lon", "depth_m", "mn_pct", "fe_pct", "sio2_pct", "p_pct",
                "intercept_m", "zone", "lithology", "status"])
    for d in snap["reserve"]["drill_holes"]:
        w.writerow([d["hole_id"], d["lat"], d["lon"], d["depth_m"], d["mn_grade_pct"], d["fe_pct"],
                    d["sio2_pct"], d["p_pct"], d["intercept_m"], d["zone"], d["lithology"], d["status"]])
    w.writerow([])

    w.writerow(["SECTION", "RISK ATTRIBUTION (TreeSHAP)"])
    w.writerow(["factor", "weight_pct", "shap_value", "contribution_t"])
    for f in snap["risk"]["factors"]:
        w.writerow([f["label"], f["weight_pct"], f["shap_value"], f["contribution_t"]])
    w.writerow([])

    w.writerow(["SECTION", "CORRECTIVE ACTIONS (MILP)"])
    w.writerow(["priority", "action", "recover_t", "yield_score", "feasibility",
                "crew", "lead_time_hrs", "cost_inr", "cost_per_tonne"])
    for a in snap["plan"]["actions"]:
        w.writerow([a["priority"], a["title"], a["recover_t"], a["yield_score"], a["feasibility"],
                    a["crew"], a["lead_time_hrs"], a["cost_inr"], a["cost_per_tonne"]])
    w.writerow([])

    w.writerow(["SECTION", "VALUE REALISATION"])
    w.writerow(["pillar", "metric", "value_inr", "value_cr", "share_pct"])
    for p in snap["roi"]["pillars"]:
        w.writerow([p["label"], p["metric"], round(p["value_inr"]), p["value_cr"], p["share_pct"]])
    w.writerow(["TOTAL", "", round(snap["roi"]["total_inr"]), snap["roi"]["total_cr"], 100.0])

    return Response(
        content=buf.getvalue(), media_type="text/csv",
        headers={"Content-Disposition":
                 f'attachment; filename="mangenesis-{snap["site"]["id"]}-analytics.csv"'},
    )


@router.get("/brief.pdf")
async def report_pdf(site: str = Query(None), scenario: str = Query(None)):
    _guard(site)
    try:
        from reportlab.lib import colors
        from reportlab.lib.enums import TA_LEFT
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import mm
        from reportlab.platypus import (
            BaseDocTemplate, Frame, KeepTogether, PageBreak, PageTemplate,
            Paragraph, Spacer, Table, TableStyle,
        )
        from reportlab.graphics.shapes import Drawing, Line, Polygon, Rect, String
    except ImportError:
        raise HTTPException(
            status_code=503,
            detail="PDF export needs ReportLab. Install it with: pip install reportlab",
        )

    snap = eng.full_snapshot(site, scenario)
    s, sc = snap["site"], snap["scenario"]
    prod, res, risk, plan, roi = (snap["production"], snap["reserve"],
                                  snap["risk"], snap["plan"], snap["roi"])

    C_INK = colors.HexColor(INK)
    C_PURPLE = colors.HexColor(PURPLE)
    C_LILAC = colors.HexColor(LILAC)
    C_MUTED = colors.HexColor(MUTED)
    C_LINE = colors.HexColor(LINE)
    C_WASH = colors.HexColor("#F6F3FE")

    base = getSampleStyleSheet()
    H1 = ParagraphStyle("H1", parent=base["Title"], fontName="Helvetica-Bold",
                        fontSize=26, leading=30, textColor=C_INK, alignment=TA_LEFT, spaceAfter=2)
    H2 = ParagraphStyle("H2", parent=base["Heading2"], fontName="Helvetica-Bold",
                        fontSize=13, leading=17, textColor=C_INK, spaceBefore=16, spaceAfter=7)
    EYEBROW = ParagraphStyle("EB", parent=base["Normal"], fontName="Helvetica-Bold",
                             fontSize=7.5, leading=11, textColor=C_PURPLE, spaceAfter=3)
    BODY = ParagraphStyle("BODY", parent=base["Normal"], fontName="Helvetica",
                          fontSize=9.2, leading=13.6, textColor=colors.HexColor("#2A2438"))
    SMALL = ParagraphStyle("SM", parent=BODY, fontSize=7.6, leading=10.6, textColor=C_MUTED)
    CELL = ParagraphStyle("CELL", parent=BODY, fontSize=8, leading=11)
    CELLB = ParagraphStyle("CELLB", parent=CELL, fontName="Helvetica-Bold")

    PW, PH = A4
    M = 16 * mm
    CW = PW - 2 * M

    def decorate(canvas, doc):
        canvas.saveState()
        canvas.setFillColor(C_INK)
        canvas.rect(0, PH - 15 * mm, PW, 15 * mm, stroke=0, fill=1)
        canvas.setFillColor(C_PURPLE)
        canvas.rect(0, PH - 15 * mm, 42 * mm, 15 * mm, stroke=0, fill=1)
        canvas.setFillColor(colors.white)
        canvas.setFont("Helvetica-Bold", 9)
        canvas.drawString(M, PH - 9.6 * mm, "MANGENESIS")
        canvas.setFont("Helvetica", 7.4)
        canvas.setFillColor(colors.HexColor("#CFC4E8"))
        canvas.drawString(M + 30 * mm, PH - 9.6 * mm, "MOIL Limited  ·  Ministry of Steel")
        canvas.drawRightString(PW - M, PH - 9.6 * mm,
                               f"{s['name']}  ·  {sc['label']}")
        canvas.setStrokeColor(C_LINE)
        canvas.setLineWidth(0.5)
        canvas.line(M, 13 * mm, PW - M, 13 * mm)
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(C_MUTED)
        canvas.drawString(M, 9 * mm,
                          "AI/ML + Space Technology for Manganese Reserve Identification & Production Continuity  ·  SIH PS 26009")
        canvas.drawRightString(PW - M, 9 * mm, f"Page {doc.page}")
        canvas.restoreState()

    buf = io.BytesIO()
    doc = BaseDocTemplate(buf, pagesize=A4, leftMargin=M, rightMargin=M,
                          topMargin=21 * mm, bottomMargin=18 * mm,
                          title=f"MANGENESIS Operations Brief — {s['name']}",
                          author="MANGENESIS · MOIL Limited")
    doc.addPageTemplates([PageTemplate(
        id="main",
        frames=[Frame(M, 18 * mm, CW, PH - 39 * mm, id="body",
                      leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)],
        onPage=decorate)])

    def rule():
        d = Drawing(CW, 3)
        d.add(Line(0, 1.5, CW, 1.5, strokeColor=C_LINE, strokeWidth=0.7))
        return d

    def stat_row(items):
        cells, styles = [], [
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 8), ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 9), ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
        ]
        for i, (label, value, sub) in enumerate(items):
            cells.append([
                Paragraph(label.upper(), ParagraphStyle("l", parent=SMALL, fontName="Helvetica-Bold",
                                                        fontSize=6.6, textColor=C_MUTED)),
            ])
            styles.append(("BACKGROUND", (i, 0), (i, 0), C_WASH))
            styles.append(("LINEBELOW", (i, 0), (i, 0), 2, C_PURPLE))
        def _fit(v):
            n = len(str(v))
            return 16 if n <= 9 else (13.5 if n <= 12 else 11.5)

        data = [[
            Paragraph(
                f'<font size="6.6" color="{MUTED}"><b>{label.upper()}</b></font><br/>'
                f'<font size="{_fit(value)}" color="{INK}"><b>{value}</b></font><br/>'
                f'<font size="7" color="{MUTED}">{sub}</font>', BODY)
            for label, value, sub in items
        ]]
        t = Table(data, colWidths=[CW / len(items)] * len(items))
        t.setStyle(TableStyle(styles))
        return t

    def bar_chart(rows, width=CW, height=None, unit=""):
        """Horizontal bars: rows = [(label, value, pct_of_max, hexcolour)]"""
        h = height or (len(rows) * 17 + 6)
        d = Drawing(width, h)
        lab_w, val_w = width * 0.34, width * 0.14
        track = width - lab_w - val_w - 8
        for i, (label, value, frac, col) in enumerate(rows):
            y = h - 14 - i * 17
            d.add(String(0, y, label[:44], fontName="Helvetica", fontSize=8,
                         fillColor=colors.HexColor("#2A2438")))
            d.add(Rect(lab_w, y - 1, track, 7, fillColor=colors.HexColor("#EFEBF9"),
                       strokeColor=None, rx=3, ry=3))
            d.add(Rect(lab_w, y - 1, max(2, track * max(0.0, min(1.0, frac))), 7,
                       fillColor=colors.HexColor(col), strokeColor=None, rx=3, ry=3))
            d.add(String(width, y, f"{value}{unit}", fontName="Helvetica-Bold", fontSize=8,
                         fillColor=C_INK, textAnchor="end"))
        return d

    def production_chart(width=CW, height=118):
        d = Drawing(width, height)
        hist, fc = prod["history"], prod["forecast"]
        target = prod["target"]
        vals = [h["actual"] for h in hist] + [f["forecast"] for f in fc] + [target]
        lo, hi = min(vals) * 0.92, max(vals) * 1.06
        rng = max(hi - lo, 1)
        pad_l, pad_b, pad_t = 34, 16, 8
        pw, ph = width - pad_l - 6, height - pad_b - pad_t
        n = len(hist) + len(fc)

        def X(i): return pad_l + pw * (i / max(n - 1, 1))
        def Y(v): return pad_b + ph * ((v - lo) / rng)

        # grid + axis labels
        for k in range(4):
            v = lo + rng * k / 3
            yy = Y(v)
            d.add(Line(pad_l, yy, pad_l + pw, yy, strokeColor=colors.HexColor("#EFEBF9"), strokeWidth=0.6))
            d.add(String(pad_l - 4, yy - 2.5, f"{v/1000:.1f}k", fontName="Helvetica", fontSize=6,
                         fillColor=C_MUTED, textAnchor="end"))
        # target line
        d.add(Line(pad_l, Y(target), pad_l + pw, Y(target),
                   strokeColor=C_MUTED, strokeWidth=0.8, strokeDashArray=[3, 3]))
        d.add(String(pad_l + 3, Y(target) + 3, f"TARGET {target:,.0f} T", fontName="Helvetica-Bold",
                     fontSize=5.6, fillColor=C_MUTED))
        # forecast confidence band
        band = []
        for j, f in enumerate(fc):
            band.append((X(len(hist) + j), Y(f["upper"])))
        for j in range(len(fc) - 1, -1, -1):
            band.append((X(len(hist) + j), Y(fc[j]["lower"])))
        d.add(Polygon([c for p in band for c in p],
                      fillColor=colors.Color(0.44, 0.15, 0.98, alpha=0.13), strokeColor=None))
        # actual line
        for i in range(len(hist) - 1):
            d.add(Line(X(i), Y(hist[i]["actual"]), X(i + 1), Y(hist[i + 1]["actual"]),
                       strokeColor=C_LILAC, strokeWidth=1.5))
        # bridge + forecast line
        pts = [(X(len(hist) - 1), Y(hist[-1]["actual"]))] + \
              [(X(len(hist) + j), Y(f["forecast"])) for j, f in enumerate(fc)]
        for i in range(len(pts) - 1):
            d.add(Line(pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1],
                       strokeColor=C_PURPLE, strokeWidth=1.9))
        for j, f in enumerate(fc):
            d.add(Rect(X(len(hist) + j) - 1.6, Y(f["forecast"]) - 1.6, 3.2, 3.2,
                       fillColor=C_PURPLE, strokeColor=None))
        for i, lbl in ((0, hist[0]["label"]), (len(hist) - 1, hist[-1]["label"]), (n - 1, fc[-1]["label"])):
            d.add(String(X(i), 4, lbl, fontName="Helvetica", fontSize=6,
                         fillColor=C_MUTED, textAnchor="middle"))
        return d

    def kv_table(pairs, col=2):
        rows, buf_row = [], []
        for k, v in pairs:
            buf_row += [Paragraph(k, ParagraphStyle("k", parent=SMALL, fontSize=7.4)),
                        Paragraph(str(v), CELLB)]
            if len(buf_row) == col * 2:
                rows.append(buf_row); buf_row = []
        if buf_row:
            buf_row += [""] * (col * 2 - len(buf_row))
            rows.append(buf_row)
        w = CW / (col * 2)
        t = Table(rows, colWidths=[w * 0.85, w * 1.15] * col)
        t.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 3.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
            ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("LINEBELOW", (0, 0), (-1, -2), 0.4, C_LINE),
        ]))
        return t

    def data_table(header, rows, widths, aligns=None):
        data = [[Paragraph(f'<font color="#FFFFFF"><b>{h}</b></font>',
                           ParagraphStyle("h", parent=CELL, fontSize=7.2)) for h in header]]
        for r in rows:
            data.append([Paragraph(str(c), CELL) for c in r])
        t = Table(data, colWidths=widths, repeatRows=1)
        st = [
            ("BACKGROUND", (0, 0), (-1, 0), C_INK),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 5), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("LINEBELOW", (0, 1), (-1, -1), 0.4, C_LINE),
        ]
        for i in range(1, len(data)):
            if i % 2 == 0:
                st.append(("BACKGROUND", (0, i), (-1, i), colors.HexColor("#FAF8FF")))
        for col, al in (aligns or []):
            st.append(("ALIGN", (col, 0), (col, -1), al))
        t.setStyle(TableStyle(st))
        return t

    story = []

    # ---------------- Cover block ----------------
    story.append(Paragraph("OPERATIONS &amp; RESERVE INTELLIGENCE BRIEF", EYEBROW))
    story.append(Paragraph(s["name"], H1))
    story.append(Paragraph(
        f'<font color="{MUTED}">{s["belt"].title()} · {s["district"] or s["state"].title()} · '
        f'Toposheet {s["toposheet"]} · {s["lat"]:.4f}°N, {s["lon"]:.4f}°E</font>', BODY))
    story.append(Spacer(1, 5))
    story.append(rule())
    story.append(Spacer(1, 9))

    sev = risk["severity"]
    story.append(stat_row([
        ("Daily target", f"{prod['target']:,.0f} T", "Planned output"),
        ("Shortfall risk", f"{risk['shortfall_probability']}%", f"{sev} severity"),
        ("Projected deficit", f"{risk['deficit_t']:,.0f} T", "Peak day"),
        ("Recoverable", f"+{plan['recovered_t']:,.0f} T", f"{plan['recovery_pct']:.0f}% restored"),
        ("Annual value", f"Rs {roi['total_cr']:.2f} Cr", "Modelled realisation"),
    ]))
    story.append(Spacer(1, 12))

    story.append(Paragraph("1 · Executive summary", H2))
    story.append(Paragraph(
        f"Under the <b>{sc['label']}</b> scenario, {s['name']} is projected to miss its planned daily output of "
        f"<b>{prod['target']:,.0f} T</b> by up to <b>{risk['deficit_t']:,.0f} T</b>, with a modelled shortfall "
        f"probability of <b>{risk['shortfall_probability']}%</b> over the {prod['model']['horizon_days']}-day horizon "
        f"({prod['summary']['forecast_window']}). TreeSHAP attribution identifies "
        f"<b>{risk['factors'][0]['label']}</b> as the dominant driver at {risk['factors'][0]['weight_pct']}% of "
        f"explained risk; the stated root cause is <b>{sc['root_cause']}</b>. "
        f"The MILP scheduler selects <b>{len(plan['actions'])} of {plan['solver']['candidates']}</b> candidate "
        f"interventions within a {plan['solver']['crew_budget']}-person, {plan['solver']['hours_budget']:.0f}-hour "
        f"shift envelope, recovering <b>{plan['recovered_t']:,.0f} T</b> "
        f"({plan['recovery_pct']:.0f}% of the gap) and cutting shortfall probability from "
        f"{plan['risk_before']}% to <b>{plan['risk_after']}%</b>. "
        f"Cumulative deficit across the horizon is {prod['summary']['cumulative_deficit_t']:,.0f} T; "
        f"forecast attainment is {prod['summary']['attainment_pct']}% of target.", BODY))
    story.append(Spacer(1, 8))
    story.append(kv_table([
        ("Metallogenic belt", s["belt"].title()),
        ("Host lithology", s["hostrock"].title()),
        ("Formation", s["formation"]),
        ("Morphogenesis", s["morphogenesis"].title()),
        ("Register source", f"{s['source']} ({s['coord_precision']} coordinates)"),
        ("Site classification", s["tier"].title()),
    ]))

    # ---------------- Production ----------------
    story.append(Paragraph("2 · Production continuity forecast", H2))
    story.append(Paragraph(
        f"{prod['model']['architecture']} over {prod['model']['features']} features, calibrated on "
        f"{prod['model']['calibration'].lower()}. Backtested MAPE {prod['model']['mape']}%. "
        f"Solid line is recorded extraction ({prod['summary']['history_window']}); "
        f"the shaded corridor is the {prod['model']['horizon_days']}-day forecast with quantile bands.", SMALL))
    story.append(Spacer(1, 6))
    story.append(production_chart())
    story.append(Spacer(1, 8))
    story.append(kv_table([
        ("Current output", f"{prod['summary']['current_output']:,.0f} T ({prod['summary']['current_vs_target_pct']:+.1f}% vs target)"),
        ("14-day mean", f"{prod['summary']['history_mean']:,.0f} T/day"),
        ("Peak deficit", f"{prod['summary']['peak_deficit_t']:,.0f} T on {prod['summary']['peak_deficit_date']}"),
        ("Cumulative deficit", f"{prod['summary']['cumulative_deficit_t']:,.0f} T over the horizon"),
    ]))

    # ---------------- Risk ----------------
    mx = max(f["weight_pct"] for f in risk["factors"]) or 1
    story.append(KeepTogether([
        Paragraph("3 · Root-cause diagnostics", H2),
        Paragraph(
            f"{risk['model']['architecture']}; base value {risk['model']['base_value']}, "
            f"explained variance {risk['model']['explained_variance']}. Factor weights are the normalised "
            f"mean absolute SHAP contributions to the shortfall probability.", SMALL),
        Spacer(1, 6),
        bar_chart([
            (f["label"], f"{f['weight_pct']}%", f["weight_pct"] / mx, f["colour"])
            for f in risk["factors"]
        ]),
    ]))
    story.append(Spacer(1, 6))
    story.append(data_table(
        ["Telemetry signal", "Reading", "Status"],
        [[t["label"], f"{t['value']} {t['unit']}".strip(), t["status"]] for t in risk["telemetry"]],
        [CW * 0.5, CW * 0.28, CW * 0.22],
        aligns=[(1, "RIGHT"), (2, "CENTER")],
    ))

    story.append(PageBreak())

    # ---------------- Reserve ----------------
    story.append(Paragraph("4 · Reserve intelligence", H2))
    t = res["totals"]
    story.append(Paragraph(
        f"{res['model']['architecture']}; ROC-AUC {res['model']['roc_auc']}, precision "
        f"{res['model']['precision']}, recall {res['model']['recall']} across {res['model']['features']} fused "
        f"features. Zones are generated along the {s['belt'].title()} regional strike "
        f"({res['strike_azimuth']}° from north) and constrained by the {s['hostrock'].lower()} grade window "
        f"({res['geology']['grade_window']}). {res['geology']['note']}.", SMALL))
    story.append(Spacer(1, 7))
    story.append(stat_row([
        ("Indicated tonnage", f"{t['total_indicated_t']/1e6:.2f} Mt", "All target sectors"),
        ("Best sector", f"{t['best_zone_probability']}%", f"{t['high_potential_zones']}/{len(res['zones'])} sectors ≥70%"),
        ("Weighted grade", f"{t['weighted_mn_grade']}%", "Mn, tonnage-weighted"),
        ("Contained Mn", f"{t['contained_mn_t']/1e6:.2f} Mt", "Metal content"),
    ]))
    story.append(Spacer(1, 10))
    story.append(data_table(
        ["Sector", "Reserve prob.", "Mn grade", "Tonnage", "Strike", "Width", "Depth"],
        [[z["name"], f"{z['probability_pct']}%", f"{z['mn_grade_pct']}%", f"{z['tonnage_t']:,} T",
          f"{z['strike_length_m']} m", f"{z['avg_width_m']} m", f"{z['depth_extent_m']} m"]
         for z in res["zones"]],
        [CW * 0.26, CW * 0.13, CW * 0.12, CW * 0.17, CW * 0.11, CW * 0.10, CW * 0.11],
        aligns=[(1, "RIGHT"), (2, "RIGHT"), (3, "RIGHT"), (4, "RIGHT"), (5, "RIGHT"), (6, "RIGHT")],
    ))
    story.append(Spacer(1, 9))
    story.append(Paragraph("Drill core assay register", ParagraphStyle(
        "h3", parent=BODY, fontName="Helvetica-Bold", fontSize=9.6, spaceAfter=5)))
    story.append(data_table(
        ["Hole", "Depth", "Mn %", "Fe %", "SiO2 %", "P %", "Intercept", "Status"],
        [[d["hole_id"], f"{d['depth_m']} m", d["mn_grade_pct"], d["fe_pct"], d["sio2_pct"],
          d["p_pct"], f"{d['intercept_m']} m", d["status"]] for d in res["drill_holes"]],
        [CW * 0.13, CW * 0.11, CW * 0.10, CW * 0.10, CW * 0.11, CW * 0.10, CW * 0.13, CW * 0.22],
        aligns=[(1, "RIGHT"), (2, "RIGHT"), (3, "RIGHT"), (4, "RIGHT"), (5, "RIGHT"), (6, "RIGHT")],
    ))

    # ---------------- Actions ----------------
    story.append(Paragraph("5 · Recommended corrective actions", H2))
    sv = plan["solver"]
    story.append(Paragraph(
        f"{sv['method']}. Objective: {sv['objective'].lower()}. Solver status <b>{sv['status']}</b> — "
        f"{sv['selected']} of {sv['candidates']} candidate interventions selected, consuming "
        f"{sv['crew_used']}/{sv['crew_budget']} crew ({sv['crew_utilisation_pct']}%) and "
        f"{sv['hours_used']}/{sv['hours_budget']:.0f} shift-hours ({sv['hours_utilisation_pct']}%) "
        f"at a committed cost of Rs {sv['total_cost_inr']:,.0f}.", SMALL))
    story.append(Spacer(1, 6))
    story.append(data_table(
        ["#", "Intervention", "Recovers", "Yield", "Feasibility", "Crew", "Lead", "Rs/T"],
        [[a["priority"], f"<b>{a['title']}</b><br/><font size=7 color='{MUTED}'>{a['detail']}</font>",
          f"{a['recover_t']:,.0f} T", f"{a['yield_score']}/100", a["feasibility"],
          a["crew"], f"{a['lead_time_hrs']} h", f"{a['cost_per_tonne']:,.0f}"]
         for a in plan["actions"]],
        [CW * 0.05, CW * 0.40, CW * 0.11, CW * 0.09, CW * 0.12, CW * 0.07, CW * 0.07, CW * 0.09],
        aligns=[(0, "CENTER"), (2, "RIGHT"), (3, "RIGHT"), (4, "CENTER"), (5, "CENTER"), (6, "RIGHT"), (7, "RIGHT")],
    ))
    story.append(Spacer(1, 8))
    story.append(KeepTogether(kv_table([
        ("Shortfall risk before", f"{plan['risk_before']}%"),
        ("Shortfall risk after", f"{plan['risk_after']}%  (−{plan['risk_reduction_pct']} pts)"),
        ("Gap recovered", f"{plan['recovered_t']:,.0f} T of {plan['deficit_t']:,.0f} T"),
        ("Residual exposure", f"{plan['residual_t']:,.0f} T"),
    ])))

    # ---------------- ROI ----------------
    story.append(Paragraph("6 · Value realisation &amp; cost-benefit", H2))
    a = roi["assumptions"]
    h = roi["headline"]
    story.append(Paragraph(
        f"Modelled on {a['basis']}. Mn ore realisation Rs {a['mn_ore_realisation_inr_t']:,.0f}/T; "
        f"diesel Rs {a['diesel_inr_l']:.0f}/L; diamond core drilling Rs {a['core_drilling_inr_m']:,.0f}/m; "
        f"{a['working_days']} working days of which {a['disruption_days']} carry a modelled disruption; "
        f"per-mine platform deployment Rs {a['platform_cost_inr']/1e7:.2f} Cr, giving a benefit-to-cost ratio of "
        f"{h['benefit_cost_ratio']}:1. "
        f"Production value flows directly from the MILP recovered tonnage in section 5, so the figures below "
        f"move with the selected scenario.", SMALL))
    story.append(Spacer(1, 7))
    story.append(stat_row([
        ("Annual value", f"Rs {h['annual_value_cr']:.2f} Cr", "Single mine"),
        ("Production", f"{h['production_recovered_t']:,} T", "Recovered per year"),
        ("Fuel saved", f"{h['fuel_saved_l']:,} L", "Idle-hour reduction"),
        ("Drilling avoided", f"Rs {h['drilling_avoided_lakh']:.1f} lakh", "De-risked targets"),
        ("Payback", f"{h['payback_months']} mo", f"On Rs {h['platform_cost_cr']} Cr cost"),
    ]))
    story.append(Spacer(1, 10))
    mxv = max(p["value_inr"] for p in roi["pillars"]) or 1
    story.append(bar_chart([
        (p["label"], f"Rs {p['value_cr']:.2f} Cr", p["value_inr"] / mxv, p["colour"])
        for p in roi["pillars"]
    ]))
    story.append(Spacer(1, 6))
    story.append(data_table(
        ["Value pillar", "Physical metric", "Basis", "Value", "Share"],
        [[p["label"], p["metric"], p["note"], f"Rs {p['value_cr']:.2f} Cr", f"{p['share_pct']}%"]
         for p in roi["pillars"]] +
        [[f"<b>TOTAL</b>", "", "", f"<b>Rs {roi['total_cr']:.2f} Cr</b>", "<b>100%</b>"]],
        [CW * 0.24, CW * 0.19, CW * 0.27, CW * 0.16, CW * 0.14],
        aligns=[(3, "RIGHT"), (4, "RIGHT")],
    ))
    story.append(Spacer(1, 10))
    story.append(Paragraph("Enterprise rollout roadmap", ParagraphStyle(
        "h3b", parent=BODY, fontName="Helvetica-Bold", fontSize=9.6, spaceAfter=5)))
    story.append(data_table(
        ["Phase", "Window", "Scope", "Value", "Status"],
        [[p["phase"], p["window"], f"<b>{p['title']}</b><br/><font size=7 color='{MUTED}'>{p['scope']}</font>",
          f"Rs {p['value_cr']} Cr", p["status"].title()] for p in roi["enterprise"]["rollout_phases"]],
        [CW * 0.10, CW * 0.15, CW * 0.50, CW * 0.13, CW * 0.12],
        aligns=[(3, "RIGHT"), (4, "CENTER")],
    ))
    story.append(Spacer(1, 8))
    story.append(Paragraph(
        f"Scaled across MOIL's {roi['enterprise']['mines']} operating mines "
        f"({roi['enterprise']['combined_tpd']:,} T/day combined rated capacity), the modelled realisation is "
        f"<b>Rs {roi['enterprise']['combined_value_cr']:.1f} Cr per year</b>.", BODY))

    # ---------------- Register context ----------------
    story.append(Paragraph("7 · Register context", H2))
    story.append(Paragraph(
        "Nearest recorded manganese occurrences from the GSI register supplied with the problem statement, "
        "by great-circle distance. These are the natural next targets for the reserve model once this site "
        "is fully calibrated.", SMALL))
    story.append(Spacer(1, 6))
    story.append(data_table(
        ["Locality", "Belt", "State", "Host rock", "Class", "Distance"],
        [[n["display"], n["belt"].title(), n["state"].title(), n["hostrock"].title(),
          n["tier"].title(), f"{n['distance_km']:,.1f} km"] for n in snap["nearby"]],
        [CW * 0.20, CW * 0.20, CW * 0.16, CW * 0.24, CW * 0.10, CW * 0.10],
        aligns=[(5, "RIGHT")],
    ))
    story.append(Spacer(1, 14))
    story.append(rule())
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        f"Generated {datetime.fromisoformat(snap['generated_at']).strftime('%d %B %Y at %H:%M')} by MANGENESIS "
        f"v2.4. Reserve, forecast, attribution and optimisation outputs are model estimates produced from the "
        f"GSI occurrence register, published MOIL capacity data and simulated operational telemetry; they are "
        f"decision-support inputs and are not a substitute for a statutory reserve statement under the "
        f"Mineral Conservation and Development Rules.", SMALL))

    doc.build(story)
    pdf = buf.getvalue()
    fname = f"MANGENESIS-{s['id']}-{sc['id']}-brief.pdf"
    return Response(
        content=pdf, media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{fname}"'},
    )
