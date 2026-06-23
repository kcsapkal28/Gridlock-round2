"""Decision engine: turn the scored zones into a plain-language deployment decision an
Inspector can act on — area + nearest station + recommended action + a confidence cue, plus a
shareable shift order. Fully deterministic (no AI, no external calls)."""
import datetime
import numpy as np
from api.places import nearest_area, nearest_station, resolve as resolve_place
from api.patrol import _action

def _f(row, col, default=0.0):
    # rows here are itertuples namedtuples → attribute access (row[col] would fail)
    v = getattr(row, col, None)
    if v is None:
        try:
            v = row[col]
        except Exception:
            v = None
    try:
        return float(v) if v is not None and not (isinstance(v, float) and np.isnan(v)) else default
    except Exception:
        return default

def _confidence(weeks, span):
    """Plain-language persistence cue from enforcement recurrence (NOT time-of-day)."""
    frac = (weeks / span) if span else 0.0
    if frac >= 0.6:
        tier = "Persistent"
    elif frac >= 0.3:
        tier = "Recurring"
    else:
        tier = "Intermittent"
    phrase = f"{tier} — cited for lane-blocking in {int(weeks)} of {int(span)} weeks on record"
    return {"tier": tier, "weeks": int(weeks), "span": int(span), "phrase": phrase}

def _haversine_km(a, b, c, d):
    from math import radians, sin, cos, asin, sqrt
    p = radians
    h = sin((p(c)-p(a))/2)**2 + cos(p(a))*cos(p(c))*sin((p(d)-p(b))/2)**2
    return 2*6371.0*asin(sqrt(h))

def build_today(df, rcp_lookup, gazetteer, stations, n=3, units=3, area=None):
    span = int(df["distinct_weeks"].max()) if "distinct_weeks" in df.columns else 23
    # Authoritative priority = the model's `rank` (impact has many ties at 100).
    ranked = df[df["ranked"]].sort_values("rank")
    area_match = None
    if area:
        res = resolve_place(area, gazetteer)
        if "error" not in res:
            area_match = {"name": res["name"], "lat": res["lat"], "lon": res["lon"]}
            la, lo = res["lat"], res["lon"]
            d = ranked.copy()
            d["_d"] = [_haversine_km(la, lo, a, b) for a, b in zip(d["lat"], d["lon"])]
            near = d[d["_d"] <= 3.0]
            ranked = near if len(near) >= 1 else ranked   # fall back citywide if area empty

    # Pick n DISTINCT places by nearest-area label (worst cell per area), so each card is a
    # different deployment target. Track how many ranked cells fall in that area ("spots").
    by_area, order = {}, []
    for r in ranked.itertuples():                      # rank order; first hit per area = worst cell
        a = nearest_area(float(r.lat), float(r.lon), gazetteer, stations)
        if a not in by_area:
            by_area[a] = {"row": r, "spots": 0}; order.append(a)
        by_area[a]["spots"] += 1

    cards = []
    for a in order[:n]:
        r = by_area[a]["row"]; spots = by_area[a]["spots"]
        lat, lon = float(r.lat), float(r.lon)
        tier3, heavy = _f(r, "tier3_share"), _f(r, "heavy_share")
        commercial = _f(r, "commercial_share")
        weeks = _f(r, "distinct_weeks", 1)
        delay = rcp_lookup.get(r.gh7)
        cards.append({
            "gh7": r.gh7, "lat": lat, "lon": lon, "area": a, "spots": spots,
            "station": (nearest_station(lat, lon, stations) or {}).get("name", "—"),
            "impact": round(float(r.impact), 0), "rank": int(r.rank),
            "n": int(_f(r, "n")), "tier3_pct": round(tier3 * 100), "heavy_pct": round(heavy * 100),
            "delay_min": round(float(delay), 1) if delay is not None else None,
            "action": _action(tier3, heavy, commercial),
            "confidence": _confidence(weeks, span),
        })

    scope = f"around {area_match['name'].title()}" if area_match else "citywide"
    summary = (f"Top {len(cards)} congestion-impact parking zones {scope}. "
               f"Deploy {min(units, max(1,len(cards)))} unit(s) to the locations below, worst first.")
    return {
        "generated_for": {"n": n, "units": units, "area": (area_match["name"] if area_match else None)},
        "span_weeks": span, "scope": scope, "summary": summary,
        "cards": cards, "shift_order": _order_text(cards, units, scope),
    }

def _order_text(cards, units, scope):
    today = datetime.date.today().isoformat()
    lines = [
        "BENGALURU TRAFFIC POLICE — PARKING ENFORCEMENT ORDER",
        f"Date: {today}    Coverage: {scope}    Units: {min(units, max(1, len(cards)))}",
        "Priority deployment (ranked by traffic-flow impact):", "",
    ]
    for i, c in enumerate(cards, 1):
        dly = f"; ~{c['delay_min']} min delay on the corridor" if c.get("delay_min") else ""
        lines.append(f"{i}. {c['area']}  (station: {c['station']})")
        lines.append(f"   Action: {c['action']}")
        lines.append(f"   Why: impact {int(c['impact'])}/100, {c['tier3_pct']}% lane-blocking, "
                     f"{c['heavy_pct']}% heavy{dly}.")
        lines.append(f"   Confidence: {c['confidence']['phrase']}.")
        lines.append("")
    lines.append("Prioritise by impact, not ticket volume. Generated by GridLock.")
    return "\n".join(lines)
