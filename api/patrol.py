import numpy as np
from sklearn.cluster import KMeans
COLORS = ["#ffb23e", "#36d6c3", "#f0463c", "#7aa2ff"]

def _order(idxs, dm):
    """Greedy nearest-neighbour order over indices given a duration matrix dm."""
    if len(idxs) <= 2:
        return list(idxs)
    remaining = list(idxs); path = [remaining.pop(0)]
    while remaining:
        last = path[-1]
        nxt = min(remaining, key=lambda j: dm[last][j]); path.append(nxt); remaining.remove(nxt)
    return path

def build_plan(df, mappls, units=3, topk=15):
    top = df[df["ranked"]].sort_values("impact", ascending=False).head(topk).reset_index(drop=True)
    units = max(1, min(units, len(top)))
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
        rc = [(top.lat[i], top.lon[i]) for i in ordered]
        rt = mappls.route(rc) if len(rc) >= 2 else {
            "geometry": [[top.lon[ordered[0]], top.lat[ordered[0]]]], "duration_s": None, "source": "single"}
        # Drive time: prefer live routing; else estimate from the (haversine) duration matrix
        # along the visiting order — so the card never shows a misleading 0 min.
        est_secs = sum(dm[local_order[k]][local_order[k + 1]] for k in range(len(local_order) - 1))
        live_secs = rt.get("duration_s")
        drive_secs = live_secs if live_secs is not None else est_secs
        out.append({
            "unit_id": u + 1, "color": COLORS[u % len(COLORS)],
            "stops": [{"gh7": top.gh7[i], "lat": float(top.lat[i]), "lon": float(top.lon[i]),
                       "impact": round(float(top.impact[i]), 1), "rank": int(top["rank"][i])} for i in ordered],
            "route_geometry": rt.get("geometry", []),
            "drive_time_min": round(drive_secs / 60.0, 1),
            "routing": "live" if rt.get("source") in ("live", "cache") else "estimated",
            "total_impact": round(float(sum(top.impact[i] for i in ordered)), 1),
            "n_zones": len(ordered),
        })
    return {"units": out, "topk": int(topk), "generated_for": {"units": units, "topk": int(topk)}}
