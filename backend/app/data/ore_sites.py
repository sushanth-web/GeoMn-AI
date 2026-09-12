"""
MANGENESIS — National Manganese Ore Occurrence Register
=======================================================

Primary source
--------------
GSI / IBM manganese occurrence table supplied with the problem statement
("manganese ore loc.pdf"), 33 recorded localities across 10 metallogenic
belts, with:

    METALLOGENESIS | LOCALITY | STATE | TOPOSHEET | LAT (DMS) | LON (DMS)
    LATDD | LONDD | COMMODITY | HOSTROCK | MORPHOGENESIS | FORMATION

Every field below is transcribed verbatim from that table. Decimal degrees
are the LATDD / LONDD columns of the source, not re-derived.

Secondary layer
---------------
MOIL Limited's operating mine portfolio (Sausar Belt, Nagpur & Bhandara
districts of Maharashtra and Balaghat district of Madhya Pradesh). Four of
MOIL's mines — BALAGHAT, GUMGAON, TIRODI and UKWA — appear directly in the
GSI table. The remaining operating mines are appended with `source="MOIL"`
and approximate district-level coordinates so the platform covers MOIL's
full production base, which is what the shortfall-prediction half of the
problem statement acts on.

`tier` semantics
----------------
    operating   — MOIL producing mine; full telemetry + shortfall modelling
    exploration — GSI occurrence inside/adjacent to a MOIL lease belt
    occurrence  — GSI-recorded national occurrence; reserve targeting only
"""

from __future__ import annotations

import math
import re
import unicodedata
from typing import Dict, List, Optional

# ---------------------------------------------------------------------------
# 1. GSI occurrence table — verbatim transcription (33 rows)
#    Column order: belt, locality, state, toposheet, lat_dms, lon_dms,
#                  lat, lon, hostrock, morphogenesis, formation
# ---------------------------------------------------------------------------

_GSI_ROWS = [
    ("BALAGHAT BELT", "BALAGHAT", "CHHATTISGARH", "64 C", "21 49N", "80 10E",
     21.8166666667, 80.1666666667, "PHYLLITE, QUARTZITE", "BEDDED-CONCORDANT", "LOHANGI Fm."),
    ("CHITRADURGA BELT", "HARENABALLI", "KARNATAKA", "57 C", "13 19N", "76 43E",
     13.3166666667, 76.7166666667, "METAVOLCANICS-METASEDIMENTS", "VOLCANOSEDIMENTARY-BEDDED", "BABABUDAN (DHARWAR)"),
    ("CHITRADURGA BELT", "HULLIKATTE", "KARNATAKA", "57 B", "14 30N", "76 07E",
     14.5000000000, 76.1166666667, "BFQ, PHYLLITE", "VOLCANOSEDIMENTARY-BEDDED", "BABABUDAN (DHARWAR)"),
    ("CHITRADURGA BELT", "KAREKUCHI", "KARNATAKA", "57 C", "13 20N", "76 42 10E",
     13.3333333300, 76.7027777800, "BHQ, METAPELITE, METAVOLCANICS", "VOLCANOSEDIMENTARY-BEDDED", "BABABUDAN (DHARWAR)"),
    ("EASTERN GHAT BELT", "DEVADA", "ANDHRA PRADESH", "65 N", "18 16N", "83 33E",
     18.2666666667, 83.5500000000, "KHONDALITE", "SEDIMENTARY-BEDDED", "EASTERN GHAT Sgp."),
    ("EASTERN GHAT BELT", "GARBHAM", "ANDHRA PRADESH", "65 N", "18 22-18 23N", "83 27-83 30E",
     18.3666666667, 83.4833333333, "KHONDALITE", "SEDIMENTARY-BEDDED", "EASTERN GHAT Sgp."),
    ("EASTERN GHAT BELT", "NISHIKHAL", "ODISHA", "65 M", "19 13N", "83 13E",
     19.2166666667, 83.2166666667, "KHONDALITE", "SEDIMENTARY-BEDDED", "EASTERN GHAT Sgp."),
    ("GOA Fe-Mn PROVINCE", "CODGUI", "GOA", "48 I", "15 30 30N", "74 08E",
     15.5083333333, 74.1333333333, "LATERITE", "SUPERGENE ENRICHMENT", "DHARWAR Sgp."),
    ("GOA Fe-Mn PROVINCE", "COLAMBA", "GOA", "48 I", "15 07-15 09N", "74 07 00-42E",
     15.1333333333, 74.1166666667, "MANGANIFEROUS PHYLLITE", "LATERITISED", "DHARWAR Sgp."),
    ("GOA Fe-Mn PROVINCE", "SULKORNA", "GOA", "48 I", "15 05-06N", "74 10-11E",
     15.0000000000, 74.1666666667, "MANGANIFEROUS PHYLLITE", "BEDDED-SEDIMENTARY", "DHARWAR Sgp."),
    ("GODAVARI RIFT BELT", "PIMPERGUDA-PIMPERKUNTA", "TELANGANA", "56 I", "19 44N", "78 28E",
     19.7333333333, 78.4666666667, "LIMESTONE, SHALE, CHERT", "BEDDED-SEDIMENTARY", "PENGANGA Gp."),
    ("GODAVARI RIFT BELT", "PIMPERKUNTA", "TELANGANA", "56 I", "19 45N", "78 28E",
     19.7500000000, 78.4666666667, "LIMESTONE, SHALE, CHERT", "BEDDED-SEDIMENTARY", "PENGANGA Gp."),
    ("JAMDA-KOIRA BELT", "KOIRA", "ODISHA", "73 G", "21 54N", "85 15E",
     21.9000000000, 85.2500000000, "SHALE, TUFFACEOUS SHALE", "VOLCANOSEDIMENTARY-BEDDED", "BONAI Gp."),
    ("NOAMUNDI-JAMDA BELT", "KATSAI", "ODISHA", "73 G", "21 50N", "85 21E",
     21.8333333333, 85.3500000000, "TUFFACEOUS SHALE", "BEDDED-VOLCANOSEDIMENTARY", "BONAI Gp."),
    ("NOAMUNDI-JAMDA SECTOR", "ROIDA", "ODISHA", "73 F", "22 01N", "85 22E",
     22.0166666667, 85.3666666667, "TUFFACEOUS SHALE", "BEDDED-VOLCANOSEDIMENTARY", "BONAI Gp."),
    ("NOAMUNDI-JAMDA SECTOR", "SARAMDAH-BHADRASAI", "ODISHA", "73 F", "22 03N", "85 24E",
     22.0500000000, 85.4000000000, "TUFFACEOUS SHALE", "BEDDED-VOLCANOSEDIMENTARY", "BONAI Gp."),
    ("NOAMUNDI-JAMDA SECTOR", "SARKUNDA", "ODISHA", "73 G", "21 49N", "85 09E",
     21.8166666667, 85.1500000000, "METASEDIMENTS-METAVOLCANICS", "BEDDED-VOLCANOSEDIMENTARY", "IRON ORE GROUP"),
    ("SANDUR SCHIST BELT", "KANIVENALLI", "KARNATAKA", "57 B", "14 57N", "76 32-76 35E",
     14.9500000000, 76.5666666667, "METASEDIMENTS-METAVOLCANICS", "CONCORDANT", "EASTERN GREENSTONE"),
    ("SANDUR SCHIST BELT", "RAMGAD", "KARNATAKA", "57 A", "15 09N", "76 26E",
     15.1500000000, 76.4333333333, "METASEDIMENTS-METAVOLCANICS", "STRATABOUND", "EASTERN GREENSTONE"),
    ("SAUSAR BELT", "BHANDARBOLI", "MAHARASHTRA", "55 O", "21 23N", "79 27E",
     21.3833333333, 79.4500000000, "GONDITE", "CONCORDANT", "SAUSAR Gp."),
    ("SAUSAR BELT", "DHANSUA-LAUGHAR-JAGANTOLI", "MADHYA PRADESH", "64 B, 64 C", "22 00N", "80 12-80 15E",
     22.0000000000, 80.2333333333, "SCHIST, PHYLLITE", "CONCORDANT", "LOHANGI Fm."),
    ("SAUSAR BELT", "GUMGAON", "MAHARASHTRA", "55 O", "21 19-21 29N", "79 03-79 31E",
     21.3833333333, 79.3333333333, "SCHIST", "CONCORDANT", "SAUSAR Gp."),
    ("SAUSAR BELT", "JUNEWANI", "MAHARASHTRA", "55 O", "21 27N", "79 16E",
     21.4500000000, 79.2666666667, "CALC GNEISS AND SCHIST", "CONCORDANT", "SAUSAR Gp."),
    ("SAUSAR BELT", "NETRA", "MAHARASHTRA", "55 O", "21 32N", "79 59E",
     21.5333333333, 79.9833333333, "SCHIST", "CONCORDANT", "LOHANGI Fm."),
    ("SAUSAR BELT", "PANCHALA", "MAHARASHTRA", "55 O", "21 27N", "79 46E",
     21.4500000000, 79.7666666667, "GONDITE", "CONCORDANT", "SAUSAR Gp."),
    ("SAUSAR BELT", "PAWNIA", "MADHYA PRADESH", "55 O", "21 43N", "79 45E",
     21.7166666667, 79.7500000000, "GONDITE-QUARTZITE", "CONCORDANT", "LOHANGI Fm."),
    ("SAUSAR BELT", "TIRODI", "MADHYA PRADESH", "55 O", "21 41N", "79 44E",
     21.6833333333, 79.7333333333, "GONDITE, QUARTZITE", "BEDDED-CONCORDANT", "LOHANGI Fm."),
    ("SAUSAR BELT", "UKWA", "MADHYA PRADESH", "64 C", "21 58N", "80 28E",
     21.9666666667, 80.4666666667, "SCHIST AND PHYLLITE", "CONCORDANT-TABULAR", "LOHANGI Fm."),
    ("SAUSAR BELT", "LAUGHAR-KAMHATOLA", "MADHYA PRADESH", "64 C", "21 50N", "80 22E",
     21.8333333333, 80.3666666667, "SCHISTS", "CONCORDANT", "LOHANGI Fm."),
    ("SHIMOGA-GOA BELT", "ANMOD", "GOA", "48 I", "15 26N", "74 18E",
     15.4333333333, 74.3000000000, "LATERITE ON VOLCANICS OF GREENSTONE", "VOLCANOGENIC-ENRICHED", "CHITRADURGA BELT Gp."),
    ("SHIMOGA-GOA BELT", "HATTIKAMBA", "KARNATAKA", "48 I", "15 16N", "74 27E",
     15.2666666667, 74.4500000000, "LATERITE IN VOLCANOSEDIMENTARY SEQUENCE", "SUPERGENE ENRICHMENT", "CHITRADURGA BELT Gp."),
    ("SHIMOGA-GOA BELT", "TERALI-BISGOD", "GOA", "48 I", "15 10N", "74 22E",
     15.1666666667, 74.3666666667, "LATERITE ON VOLCANOSEDIMENTS OF GREENSTONE", "SUPERGENE ENRICHMENT", "CHITRADURGA BELT Gp."),
    ("SHIMOGA-GOA BELT", "YOGIMALAI", "KARNATAKA", "48 O", "13 52N", "75 19E",
     13.8666666667, 75.3166666667, "METASEDIMENTS-METAVOLCANICS", "CONCORDANT", "CHITRADURGA BELT Gp."),
]

# ---------------------------------------------------------------------------
# 2. MOIL operating-mine overlay
#    Localities already present in the GSI table are upgraded in place;
#    the rest are appended. Coordinates for appended mines are district-level
#    approximations (flagged via `coord_precision`).
# ---------------------------------------------------------------------------

# locality -> (mine_name, district, mine_type, rated_tpd, opened, workforce)
_MOIL_UPGRADE = {
    "BALAGHAT":  ("Balaghat Mine",  "Balaghat, MP",  "Underground + Opencast", 3400, 1907, 1180),
    "GUMGAON":   ("Gumgaon Mine",   "Nagpur, MH",    "Underground",            1150, 1900,  410),
    "TIRODI":    ("Tirodi Mine",    "Balaghat, MP",  "Opencast",               1050, 1917,  365),
    "UKWA":      ("Ukwa Mine",      "Balaghat, MP",  "Underground",             900, 1908,  330),
}

# name, district, state, lat, lon, mine_type, rated_tpd, opened, workforce,
# hostrock, morphogenesis, formation
_MOIL_EXTRA = [
    ("KANDRI",         "Kandri Mine",         "Nagpur, MH",   21.2833, 79.1500, "Underground",  980, 1900, 355,
     "GONDITE", "CONCORDANT", "SAUSAR Gp."),
    ("MUNSAR",         "Munsar Mine",         "Nagpur, MH",   21.3000, 79.2000, "Underground",  920, 1900, 340,
     "GONDITE, QUARTZITE", "CONCORDANT", "SAUSAR Gp."),
    ("BELDONGRI",      "Beldongri Mine",      "Nagpur, MH",   21.2700, 79.1300, "Underground",  610, 1961, 225,
     "GONDITE", "CONCORDANT", "SAUSAR Gp."),
    ("CHIKLA",         "Chikla Mine",         "Bhandara, MH", 21.2000, 79.7200, "Opencast + UG", 840, 1917, 300,
     "GONDITE, SCHIST", "CONCORDANT", "SAUSAR Gp."),
    ("DONGRI BUZURG",  "Dongri Buzurg Mine",  "Bhandara, MH", 21.3400, 79.8500, "Opencast",     1450, 1954, 480,
     "GONDITE, MANGANIFEROUS SCHIST", "BEDDED-CONCORDANT", "SAUSAR Gp."),
    ("SITAPATORE",     "Sitapatore/Sitasaongi Mine", "Bhandara, MH", 21.3800, 79.9000, "Underground", 520, 1948, 190,
     "SCHIST", "CONCORDANT", "SAUSAR Gp."),
    ("PARSODA",        "Parsoda Mine",        "Nagpur, MH",   21.3200, 79.2800, "Opencast",      360, 1962, 130,
     "GONDITE", "CONCORDANT", "SAUSAR Gp."),
]

# ---------------------------------------------------------------------------
# 3. Geochemistry priors keyed by host lithology
#    Mn grade window (%) and typical ore-body continuity, used by the
#    reserve model as a physically-grounded prior before satellite fusion.
# ---------------------------------------------------------------------------

_LITHO_PRIORS = {
    "GONDITE":            (42.0, 48.5, 0.88, "Braunite-spessartite gondite; the classic Sausar high-grade host"),
    "GONDITE-QUARTZITE":  (38.0, 45.0, 0.82, "Gondite interbanded with quartzite; grade dilutes with silica"),
    "GONDITE, QUARTZITE": (38.5, 45.5, 0.83, "Bedded gondite-quartzite couplets, laterally persistent"),
    "SCHIST":             (34.0, 42.0, 0.74, "Mn-silicate schist; grade tracks braunite modal abundance"),
    "SCHISTS":            (33.0, 41.0, 0.72, "Foliated Mn-schist, moderate continuity"),
    "SCHIST, PHYLLITE":   (31.0, 39.5, 0.70, "Schist-phyllite package; structurally repeated lodes"),
    "SCHIST AND PHYLLITE":(31.5, 40.0, 0.71, "Tabular concordant lodes in schist-phyllite"),
    "CALC GNEISS AND SCHIST": (29.0, 37.0, 0.66, "Calc-gneiss host; carbonate dilution lowers recoverable grade"),
    "PHYLLITE, QUARTZITE":(30.0, 38.0, 0.69, "Bedded concordant Mn horizons in phyllite-quartzite"),
    "LATERITE":           (28.0, 40.0, 0.58, "Supergene lateritic Mn cap; high grade, low tonnage continuity"),
    "MANGANIFEROUS PHYLLITE": (26.0, 36.0, 0.62, "Lateritised Mn-phyllite, weathering-controlled"),
    "KHONDALITE":         (24.0, 34.0, 0.60, "Khondalite-hosted Mn; gondite-equivalent of the Eastern Ghats"),
    "TUFFACEOUS SHALE":   (22.0, 32.0, 0.64, "Volcanosedimentary Mn in tuffaceous shale, bedded"),
    "SHALE, TUFFACEOUS SHALE": (22.5, 32.5, 0.65, "Shale-tuff Mn horizons of the Iron Ore Group"),
    "LIMESTONE, SHALE, CHERT": (20.0, 30.0, 0.55, "Penganga sedimentary Mn; cherty, siliceous"),
    "METASEDIMENTS-METAVOLCANICS": (25.0, 35.0, 0.63, "Greenstone-hosted Mn, stratabound"),
    "METAVOLCANICS-METASEDIMENTS": (25.0, 35.0, 0.63, "Volcanosedimentary Mn horizons"),
    "BFQ, PHYLLITE":      (23.0, 33.0, 0.60, "Banded ferruginous quartzite association; Fe-Mn mixed"),
    "BHQ, METAPELITE, METAVOLCANICS": (23.5, 33.5, 0.61, "BHQ-metapelite association, Fe-rich"),
    "LATERITE ON VOLCANICS OF GREENSTONE": (26.0, 37.0, 0.56, "Volcanogenic-enriched laterite cap"),
    "LATERITE IN VOLCANOSEDIMENTARY SEQUENCE": (25.5, 36.0, 0.55, "Supergene laterite over volcanosediments"),
    "LATERITE ON VOLCANOSEDIMENTS OF GREENSTONE": (25.0, 35.5, 0.55, "Supergene Mn laterite blanket"),
}

_DEFAULT_PRIOR = (25.0, 35.0, 0.62, "Mixed metasedimentary Mn host")

# Morphogenesis → structural predictability multiplier for the reserve model
_MORPHO_FACTOR = {
    "BEDDED-CONCORDANT": 1.12,
    "CONCORDANT": 1.08,
    "CONCORDANT-TABULAR": 1.10,
    "STRATABOUND": 1.06,
    "BEDDED-SEDIMENTARY": 1.04,
    "SEDIMENTARY-BEDDED": 1.02,
    "VOLCANOSEDIMENTARY-BEDDED": 0.98,
    "BEDDED-VOLCANOSEDIMENTARY": 0.97,
    "SUPERGENE ENRICHMENT": 0.86,
    "LATERITISED": 0.84,
    "VOLCANOGENIC-ENRICHED": 0.88,
}

# Belt → agro-climatic profile driving the space-technology inputs.
# (annual rainfall mm, monsoon peak month, mean LST °C, baseline NDVI)
_BELT_CLIMATE = {
    "SAUSAR BELT":           (1180, 7, 32.4, 0.41),
    "BALAGHAT BELT":         (1310, 7, 31.8, 0.47),
    "CHITRADURGA BELT":      ( 620, 9, 33.9, 0.28),
    "EASTERN GHAT BELT":     (1240, 7, 32.1, 0.52),
    "GOA Fe-Mn PROVINCE":    (2980, 7, 30.2, 0.68),
    "GODAVARI RIFT BELT":    ( 980, 7, 34.6, 0.33),
    "JAMDA-KOIRA BELT":      (1420, 7, 31.4, 0.58),
    "NOAMUNDI-JAMDA BELT":   (1440, 7, 31.2, 0.59),
    "NOAMUNDI-JAMDA SECTOR": (1450, 7, 31.1, 0.59),
    "SANDUR SCHIST BELT":    ( 590, 9, 34.2, 0.26),
    "SHIMOGA-GOA BELT":      (2640, 7, 30.6, 0.66),
}

_BELT_COLOURS = {
    "SAUSAR BELT":           "#7026FB",
    "BALAGHAT BELT":         "#9D5CFF",
    "CHITRADURGA BELT":      "#22D3EE",
    "EASTERN GHAT BELT":     "#34D399",
    "GOA Fe-Mn PROVINCE":    "#FBBF24",
    "GODAVARI RIFT BELT":    "#F472B6",
    "JAMDA-KOIRA BELT":      "#60A5FA",
    "NOAMUNDI-JAMDA BELT":   "#818CF8",
    "NOAMUNDI-JAMDA SECTOR": "#A78BFA",
    "SANDUR SCHIST BELT":    "#FB923C",
    "SHIMOGA-GOA BELT":      "#2DD4BF",
}


def _slug(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    text = re.sub(r"[^A-Za-z0-9]+", "-", text).strip("-").lower()
    return text


def _title(text: str) -> str:
    """BHANDARBOLI -> Bhandarboli ; DHANSUA-LAUGHAR-JAGANTOLI -> Dhansua-Laughar-Jagantoli"""
    return "-".join(
        " ".join(w.capitalize() for w in part.split(" "))
        for part in text.split("-")
    )


def _build_registry() -> List[Dict]:
    sites: List[Dict] = []

    for (belt, locality, state, toposheet, lat_dms, lon_dms,
         lat, lon, hostrock, morpho, formation) in _GSI_ROWS:

        upgrade = _MOIL_UPGRADE.get(locality)
        lo, hi, continuity, litho_note = _LITHO_PRIORS.get(hostrock, _DEFAULT_PRIOR)
        rain, peak, lst, ndvi = _BELT_CLIMATE.get(belt, (1000, 7, 32.0, 0.40))

        # The GSI register's STATE column places Balaghat in Chhattisgarh;
        # the district is in fact in Madhya Pradesh. Where MOIL operating-mine
        # data gives an authoritative district, that wins — the register value
        # is preserved in `register_state` so nothing is silently lost.
        register_state = state
        if upgrade:
            state = {"MH": "MAHARASHTRA", "MP": "MADHYA PRADESH"}.get(
                upgrade[1].split(", ")[-1], state)

        site = {
            "id": _slug(locality),
            "locality": locality,
            "name": upgrade[0] if upgrade else _title(locality),
            "display": _title(locality),
            "belt": belt,
            "state": state,
            "register_state": register_state,
            "district": upgrade[1] if upgrade else None,
            "toposheet": toposheet,
            "lat_dms": lat_dms,
            "lon_dms": lon_dms,
            "lat": round(lat, 6),
            "lon": round(lon, 6),
            "commodity": "Manganese",
            "hostrock": hostrock,
            "morphogenesis": morpho,
            "formation": formation,
            "source": "GSI",
            "coord_precision": "toposheet",
            "tier": "operating" if upgrade else (
                "exploration" if belt in ("SAUSAR BELT", "BALAGHAT BELT") else "occurrence"
            ),
            "mine_type": upgrade[2] if upgrade else None,
            "rated_tpd": upgrade[3] if upgrade else None,
            "opened": upgrade[4] if upgrade else None,
            "workforce": upgrade[5] if upgrade else None,
            "grade_lo": lo,
            "grade_hi": hi,
            "continuity": continuity,
            "litho_note": litho_note,
            "morpho_factor": _MORPHO_FACTOR.get(morpho, 1.0),
            "annual_rainfall_mm": rain,
            "monsoon_peak_month": peak,
            "mean_lst_c": lst,
            "baseline_ndvi": ndvi,
            "belt_colour": _BELT_COLOURS.get(belt, "#7026FB"),
        }
        sites.append(site)

    for (locality, name, district, lat, lon, mine_type, tpd, opened, workforce,
         hostrock, morpho, formation) in _MOIL_EXTRA:
        belt = "SAUSAR BELT"
        lo, hi, continuity, litho_note = _LITHO_PRIORS.get(hostrock, _DEFAULT_PRIOR)
        rain, peak, lst, ndvi = _BELT_CLIMATE[belt]
        state = "MAHARASHTRA" if district.endswith("MH") else "MADHYA PRADESH"
        sites.append({
            "id": _slug(locality),
            "locality": locality,
            "name": name,
            "display": _title(locality),
            "belt": belt,
            "state": state,
            "register_state": state,
            "district": district,
            "toposheet": "55 O",
            "lat_dms": None,
            "lon_dms": None,
            "lat": lat,
            "lon": lon,
            "commodity": "Manganese",
            "hostrock": hostrock,
            "morphogenesis": morpho,
            "formation": formation,
            "source": "MOIL",
            "coord_precision": "approximate",
            "tier": "operating",
            "mine_type": mine_type,
            "rated_tpd": tpd,
            "opened": opened,
            "workforce": workforce,
            "grade_lo": lo,
            "grade_hi": hi,
            "continuity": continuity,
            "litho_note": litho_note,
            "morpho_factor": _MORPHO_FACTOR.get(morpho, 1.0),
            "annual_rainfall_mm": rain,
            "monsoon_peak_month": peak,
            "mean_lst_c": lst,
            "baseline_ndvi": ndvi,
            "belt_colour": _BELT_COLOURS[belt],
        })

    # Deterministic ordering: operating mines first, then belt, then locality
    tier_rank = {"operating": 0, "exploration": 1, "occurrence": 2}
    sites.sort(key=lambda s: (tier_rank[s["tier"]], s["belt"], s["locality"]))
    return sites


ORE_SITES: List[Dict] = _build_registry()
SITE_INDEX: Dict[str, Dict] = {s["id"]: s for s in ORE_SITES}

DEFAULT_SITE_ID = "gumgaon"


def get_site(site_id: Optional[str]) -> Dict:
    if not site_id:
        return SITE_INDEX[DEFAULT_SITE_ID]
    return SITE_INDEX.get(site_id.lower(), SITE_INDEX[DEFAULT_SITE_ID])


def belts() -> List[Dict]:
    """Grouped view used by the map's location selector."""
    out: Dict[str, Dict] = {}
    for s in ORE_SITES:
        b = out.setdefault(s["belt"], {
            "belt": s["belt"],
            "colour": s["belt_colour"],
            "states": set(),
            "sites": [],
        })
        b["states"].add(s["state"])
        b["sites"].append({
            "id": s["id"], "name": s["name"], "display": s["display"],
            "state": s["state"], "tier": s["tier"],
            "lat": s["lat"], "lon": s["lon"],
        })
    result = []
    for b in out.values():
        b["states"] = sorted(b["states"])
        b["sites"].sort(key=lambda x: x["display"])
        b["count"] = len(b["sites"])
        result.append(b)
    result.sort(key=lambda b: (-sum(1 for s in b["sites"] if s["tier"] == "operating"), b["belt"]))
    return result


def registry_stats() -> Dict:
    operating = [s for s in ORE_SITES if s["tier"] == "operating"]
    return {
        "total_sites": len(ORE_SITES),
        "operating_mines": len(operating),
        "exploration_targets": sum(1 for s in ORE_SITES if s["tier"] == "exploration"),
        "occurrences": sum(1 for s in ORE_SITES if s["tier"] == "occurrence"),
        "belts": len({s["belt"] for s in ORE_SITES}),
        "states": len({s["state"] for s in ORE_SITES}),
        "combined_rated_tpd": sum(s["rated_tpd"] or 0 for s in operating),
        "host_lithologies": len({s["hostrock"] for s in ORE_SITES}),
    }


def haversine_km(a: Dict, b: Dict) -> float:
    r = 6371.0
    p1, p2 = math.radians(a["lat"]), math.radians(b["lat"])
    dp = p2 - p1
    dl = math.radians(b["lon"] - a["lon"])
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(h))
