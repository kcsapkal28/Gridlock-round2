#!/usr/bin/env python3
"""Routing Cost Penalty (RCP) — quantify a hotspot's impact on traffic FLOW as a measured delay.

For each top hotspot corridor:
  1. Build an origin/destination pair spanning the cell (~550 m each side of centroid).
  2. Query MapMyIndia **Distance Matrix** (allowed mapping-infra API) for the free-flow drive time T_base.
  3. Derive a capacity-reduction fraction from the cell's OWN data (Tier-3 + heavy-vehicle share).
  4. Delay = T_base * (cap_reduction / (1 - cap_reduction))   [bottleneck / BPR-style].

Free-tier-careful: top-N only, every Distance Matrix response disk-cached (re-runs cost ZERO calls).
Compliance (ADR-007): Distance Matrix is mapping infrastructure; NO live-traffic API is used — T_base is
a routing baseline, not a live speed stream.

Usage: python rcp.py [TOP_N]   (default 12)
"""
import os, json, sys, time
import requests
import pandas as pd

CACHE = ".mappls_cache"
SECRETS = ".mappls_secrets"
SCORES = "fe_work/cell_scores.parquet"
DELTA = 0.005          # ~550 m offset each side of the centroid
os.makedirs(CACHE, exist_ok=True)


def _key():
    for line in open(SECRETS):
        k, _, v = line.strip().partition("=")
        if k == "MAPPLS_KEY":
            return v
    raise SystemExit("MAPPLS_KEY not found in .mappls_secrets")


def capacity_reduction(tier3_share, heavy_share):
    """Fraction of effective road capacity lost to illegal parking, from the cell's own violation mix.
    Heuristic (documented): base 0.10 + Tier-3 (lane-blocking) + heavy-vehicle footprint; capped 0.60."""
    return min(0.60, 0.10 + 0.35 * float(tier3_share) + 0.20 * float(heavy_share))


def delay_minutes(t_base_s, cap_red):
    """Added travel time (minutes) from the capacity loss: T_base * cap/(1-cap)."""
    cap = min(max(cap_red, 0.0), 0.95)
    return (t_base_s * (cap / (1.0 - cap))) / 60.0


def distance_matrix(gh7, o_lat, o_lng, d_lat, d_lng, key):
    """Cached Distance Matrix call. Returns (distance_m, duration_s) for O->D, or (None,None)."""
    cf = os.path.join(CACHE, f"dm_{gh7}.json")
    if os.path.exists(cf):
        j = json.load(open(cf))
    else:
        coords = f"{o_lng},{o_lat};{d_lng},{d_lat}"
        r = requests.get(f"https://apis.mappls.com/advancedmaps/v1/{key}/distance_matrix/driving/{coords}",
                         timeout=20)
        j = r.json() if r.status_code == 200 else {}
        json.dump(j, open(cf, "w"))
        time.sleep(0.1)
    try:
        res = j["results"]
        return res["distances"][0][1], res["durations"][0][1]
    except Exception:
        return None, None


def run(top_n=12):
    key = _key()
    df = pd.read_parquet(SCORES)
    top = df[df["ranked"]].sort_values("impact", ascending=False).head(top_n).copy()
    rows, calls = [], 0
    for _, r in top.iterrows():
        cf = os.path.join(CACHE, f"dm_{r['gh7']}.json")
        if not os.path.exists(cf):
            calls += 1
        dist, t_base = distance_matrix(r["gh7"], r["lat"] - DELTA, r["lon"] - DELTA,
                                       r["lat"] + DELTA, r["lon"] + DELTA, key)
        if t_base is None:
            continue
        cap = capacity_reduction(r["tier3_share"], r["heavy_share"])
        dly = delay_minutes(t_base, cap)
        rows.append({
            "rank": int(r["rank"]), "gh7": r["gh7"], "lat": float(r["lat"]), "lon": float(r["lon"]),
            "impact": round(float(r["impact"]), 2), "tier3_share": round(float(r["tier3_share"]), 3),
            "heavy_share": round(float(r["heavy_share"]), 3),
            "segment_m": round(float(dist), 1), "t_base_s": round(float(t_base), 1),
            "capacity_reduction": round(cap, 3), "delay_min": round(dly, 2),
        })
    out = pd.DataFrame(rows).sort_values("delay_min", ascending=False)
    os.makedirs("fe_work/fe_out", exist_ok=True)
    out.to_csv("fe_work/fe_out/rcp.csv", index=False)
    feats = [{"type": "Feature", "geometry": {"type": "Point", "coordinates": [x["lon"], x["lat"]]},
              "properties": {k: x[k] for k in x if k not in ("lat", "lon")}}
             for x in out.to_dict("records")]
    json.dump({"type": "FeatureCollection", "features": feats},
              open("fe_work/fe_out/rcp.geojson", "w"))
    print(f"RCP computed for {len(out)} corridors | NEW Distance-Matrix calls: {calls} (rest cached)")
    return out


# --- pure-function sanity guards (no network) ---
assert abs(delay_minutes(600, 0.5) - 10.0) < 1e-9, "delay math wrong"          # 600s*1.0/60=10min
assert capacity_reduction(0, 0) == 0.10 and capacity_reduction(1, 1) == 0.60   # bounds

if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 12
    out = run(n)
    print(out.head(12)[["rank", "gh7", "impact", "tier3_share", "heavy_share",
                        "t_base_s", "capacity_reduction", "delay_min"]].to_string(index=False))
