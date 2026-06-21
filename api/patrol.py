"""Patrol optimiser → a *practical, step-by-step* deployment plan.

Each unit is anchored to its nearest police station (the depot it rolls out from), visits a
cluster of high-impact zones in a sensible order, and gets a human-readable itinerary with an
area name and a recommended enforcement action per stop. Area names come from the native
gazetteer (zero API cost — always returns a label); drive times use live MapMyIndia routing
when a key is present, else a haversine estimate. Never raises on valid input.
"""
import numpy as np
from sklearn.cluster import KMeans
from api.places import build_gazetteer, nearest_area, nearest_station

COLORS = ["#ffb23e", "#36d6c3", "#f0463c", "#7aa2ff"]

# Priority modes: how to pick & order the zones a patrol covers.
PRIORITY_KEYS = {
    "impact": "impact",            # overall congestion-impact score (default)
    "carriageway": "tier3_share",  # lane-blocking severity
    "heavy": "heavy_share",        # heavy / commercial vehicle share
}


def _order(idxs, dm):
    """Greedy nearest-neighbour visiting order over indices given a duration matrix dm."""
    if len(idxs) <= 2:
        return list(idxs)
    remaining = list(idxs); path = [remaining.pop(0)]
    while remaining:
        last = path[-1]
        nxt = min(remaining, key=lambda j: dm[last][j]); path.append(nxt); remaining.remove(nxt)
    return path


def _action(tier3, heavy, commercial):
    """The single most useful enforcement action for a stop, from its citation mix."""
    if heavy >= 0.30:
        return "Heavy-vehicle intercept + tow-away (commercial operators first)"
    if tier3 >= 0.60:
        return "Clear carriageway-blocking; tow-away repeat offenders"
    if commercial >= 0.30:
        return "Penalise repeat commercial / loading-bay violations"
    if tier3 >= 0.30:
        return "Active ticketing; deter lane-encroachment"
    return "Routine ticketing; deter repeat parking"


def _dwell_min(n, tier3, heavy):
    """Rough on-site enforcement time per stop (minutes). Estimate, scaled by load + severity."""
    base = 8.0 + min(12.0, float(n) / 60.0)        # busier zones take longer to clear
    return round(base * (1.0 + 0.4 * float(tier3) + 0.3 * float(heavy)), 0)


def _f(row, col, default=0.0):
    try:
        v = row[col]
        return float(v) if v is not None and not (isinstance(v, float) and np.isnan(v)) else default
    except Exception:
        return default


def build_plan(df, mappls, units=3, topk=15, priority="impact", start_from_station=True, stations=None):
    sort_col = PRIORITY_KEYS.get(priority, "impact")
    ranked = df[df["ranked"]]
    if sort_col not in ranked.columns:
        sort_col = "impact"
    top = ranked.sort_values(sort_col, ascending=False).head(topk).reset_index(drop=True)
    if len(top) == 0:
        return {"units": [], "topk": int(topk), "priority": priority,
                "generated_for": {"units": units, "topk": int(topk), "priority": priority}}
    units = max(1, min(units, len(top)))
    gaz = build_gazetteer(stations)
    km = KMeans(n_clusters=units, n_init=10, random_state=42).fit(top[["lat", "lon"]].values)

    out = []
    for u in range(units):
        members = [i for i in range(len(top)) if km.labels_[i] == u]
        if not members:
            continue
        coords = [(top.lat[i], top.lon[i]) for i in members]
        dm = mappls.distance_matrix_many(coords)
        local_order = _order(list(range(len(members))), dm)
        ordered = [members[k] for k in local_order]

        # Depot = nearest police station to the cluster centroid.
        cen_lat = float(np.mean([top.lat[i] for i in ordered]))
        cen_lon = float(np.mean([top.lon[i] for i in ordered]))
        station = nearest_station(cen_lat, cen_lon, stations) if start_from_station else None

        # Route geometry: station -> ordered stops (so the drawn path leaves the depot).
        rc = [(top.lat[i], top.lon[i]) for i in ordered]
        route_coords = ([(station["lat"], station["lon"])] + rc) if station else rc
        rt = mappls.route(route_coords) if len(route_coords) >= 2 else {
            "geometry": [[route_coords[0][1], route_coords[0][0]]], "duration_s": None, "source": "single"}

        # Drive time: live if available, else haversine estimate along the visiting order
        # (+ the station->first-stop leg when starting from a depot).
        est_secs = sum(dm[local_order[k]][local_order[k + 1]] for k in range(len(local_order) - 1))
        if station and ordered:
            from api.geo import haversine_km
            est_secs += haversine_km(station["lat"], station["lon"], top.lat[ordered[0]], top.lon[ordered[0]]) / 20.0 * 3600.0
        live_secs = rt.get("duration_s")
        drive_secs = live_secs if live_secs is not None else est_secs

        stops, steps, dwell_total = [], [], 0.0
        if station:
            steps.append({"kind": "depart", "text": f"Roll out from {station['name']} police station"})
        for seq, i in enumerate(ordered, start=1):
            tier3, heavy = _f(top.iloc[i], "tier3_share"), _f(top.iloc[i], "heavy_share")
            commercial = _f(top.iloc[i], "commercial_share")
            area = nearest_area(float(top.lat[i]), float(top.lon[i]), gaz, stations)
            act = _action(tier3, heavy, commercial)
            dwell = _dwell_min(_f(top.iloc[i], "n"), tier3, heavy); dwell_total += dwell
            stop = {
                "seq": seq, "gh7": top.gh7[i], "lat": float(top.lat[i]), "lon": float(top.lon[i]),
                "area": area, "impact": round(float(top.impact[i]), 1), "rank": int(top["rank"][i]),
                "n": int(_f(top.iloc[i], "n")), "tier3_share": round(tier3, 3), "heavy_share": round(heavy, 3),
                "action": act, "dwell_min": dwell,
            }
            stops.append(stop)
            steps.append({"kind": "stop", "seq": seq, "area": area, "gh7": stop["gh7"],
                          "impact": stop["impact"], "dwell_min": dwell, "action": act,
                          "text": f"Stop {seq} — {area}: {act} (~{int(dwell)} min, impact {stop['impact']}/100)"})
        if station:
            steps.append({"kind": "return", "text": f"Return to {station['name']} police station"})

        out.append({
            "unit_id": u + 1, "color": COLORS[u % len(COLORS)],
            "station": station,
            "stops": stops, "steps": steps,
            "route_geometry": rt.get("geometry", []),
            "drive_time_min": round(drive_secs / 60.0, 1),
            "dwell_time_min": round(dwell_total, 0),
            "shift_time_min": round(drive_secs / 60.0 + dwell_total, 0),
            "routing": "live" if rt.get("source") in ("live", "cache") else "estimated",
            "total_impact": round(float(sum(top.impact[i] for i in ordered)), 1),
            "n_zones": len(ordered),
        })
    return {"units": out, "topk": int(topk), "priority": priority,
            "generated_for": {"units": units, "topk": int(topk), "priority": priority}}
