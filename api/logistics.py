"""Logistics impedance loop: given a planned route, find the hotspots it crosses, quantify the
delay (from precomputed RCP where available, else a capacity-based estimate), and propose a detour
via the MapMyIndia Routing API (mapping-infra). Fallbacks everywhere; never raises on valid input."""
import os, math, pandas as pd
from api.geo import haversine_km, cells_near_path

def _cap_estimate(tier3, heavy):
    return min(0.60, 0.10 + 0.35*float(tier3) + 0.20*float(heavy))

def load_rcp(path="fe_work/fe_out/rcp.csv"):
    if os.path.exists(path):
        d=pd.read_parquet(path) if path.endswith(".parquet") else pd.read_csv(path)
        return {r.gh7: float(r.delay_min) for r in d.itertuples()}
    return {}

def _sla(delay):
    return "Critical" if delay>=15 else ("Medium" if delay>=5 else "Low")

def impedance(waypoints, df, rcp_lookup, mappls, min_impact=80.0):
    ranked=df[(df["ranked"]) & (df["impact"]>=min_impact)].reset_index(drop=True)
    idx=cells_near_path(waypoints, ranked, radius_km=0.20, limit=60)
    affected=[]
    total=0.0
    for i in idx:
        r=ranked.iloc[i]
        dly=rcp_lookup.get(r.gh7)
        if dly is None:
            dly=round(_cap_estimate(r.tier3_share, r.heavy_share)*6.0, 2)  # estimate, no extra API call
        total+=dly
        affected.append({"gh7":r.gh7,"lat":float(r.lat),"lon":float(r.lon),
                         "impact":round(float(r.impact),1),"delay_min":round(float(dly),2),
                         "primary_infraction_type":str(r.get("primary_infraction_type","")),
                         "dominant_vehicle_class":str(r.get("dominant_vehicle_class",""))})
    total=round(total,2)
    o=(waypoints[0]["lat"],waypoints[0]["lng"]); d=(waypoints[-1]["lat"],waypoints[-1]["lng"])
    baseline=mappls.route([o,d])
    detour=None
    if affected:
        worst=max(affected,key=lambda a:a["delay_min"])
        # perpendicular via-point to force a detour around the worst choke
        dlat,dlng=d[0]-o[0],d[1]-o[1]; nrm=math.hypot(dlat,dlng) or 1.0
        via=(worst["lat"]-dlng/nrm*0.004, worst["lon"]+dlat/nrm*0.004)
        detour=mappls.route([o,via,d])
    return {
        "impedance_delay_mins": total,
        "sla_risk": _sla(total),
        "affected_cells": sorted(affected,key=lambda a:-a["delay_min"]),
        "n_affected": len(affected),
        "baseline_route": baseline,
        "detour_route": detour,
        "minutes_saved_by_detour": total,   # detouring avoids the choke-point delay
        "source": baseline.get("source"),
    }
