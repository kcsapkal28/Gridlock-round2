# mapmyindia_enrich.py
"""MapMyIndia (Mappls) enrichment for the top-ranked impact cells — free-tier-careful.
- Auth: REST key (in URL path) from .mappls_secrets (gitignored).
- Reverse-geocodes each cell centroid -> authoritative street + locality.
- Disk-caches every response in .mappls_cache/ keyed by gh7 -> re-runs cost ZERO calls.
- Derives a coarse road-EXPOSURE weight from the street type (heuristic, not lane data),
  and an optional capacity-adjusted impact layer. Native `impact` stays primary.

Usage: python mapmyindia_enrich.py [TOP_N]   (default 50)
"""
import os, json, sys, time, math
import requests
import pandas as pd

CACHE = ".mappls_cache"
SECRETS = ".mappls_secrets"
SCORES = "fe_work/cell_scores.parquet"
os.makedirs(CACHE, exist_ok=True)


def _key():
    for line in open(SECRETS):
        k, _, v = line.strip().partition("=")
        if k == "MAPPLS_KEY":
            return v
    raise SystemExit("MAPPLS_KEY not found in .mappls_secrets")


def rev_geocode(gh7, lat, lng, key):
    """Cached reverse-geocode. Returns results[0] dict (or {})."""
    cf = os.path.join(CACHE, f"{gh7}.json")
    if os.path.exists(cf):
        return json.load(open(cf))
    r = requests.get(f"https://apis.mappls.com/advancedmaps/v1/{key}/rev_geocode",
                     params={"lat": lat, "lng": lng}, timeout=20)
    res = (r.json().get("results") or [{}])[0] if r.status_code == 200 else {}
    json.dump(res, open(cf, "w"))
    time.sleep(0.05)
    return res


def road_exposure(street):
    """Coarse traffic-exposure weight from street type (heuristic; free tier has no lane data)."""
    s = (street or "").lower()
    if any(k in s for k in ["ring road", "highway", "nh-", "national highway", "flyover", "trunk", "outer ring"]):
        return 1.50, "arterial/highway"
    if "main road" in s:
        return 1.35, "main road"
    if any(k in s for k in ["cross", "circle", "junction"]):
        return 1.20, "cross/junction"
    return 1.00, "local"


def enrich(top_n=50):
    key = _key()
    df = pd.read_parquet(SCORES)
    top = df[df["ranked"]].sort_values("impact", ascending=False).head(top_n).copy()
    rows = []
    calls = 0
    for _, r in top.iterrows():
        cf = os.path.join(CACHE, f"{r['gh7']}.json")
        if not os.path.exists(cf):
            calls += 1
        g = rev_geocode(r["gh7"], r["lat"], r["lon"], key)
        street = g.get("street") or g.get("subLocality") or ""
        exp, rclass = road_exposure(street)
        rows.append({
            "rank": int(r["rank"]), "gh7": r["gh7"], "lat": r["lat"], "lon": r["lon"],
            "impact": round(float(r["impact"]), 2), "n": int(r["n"]),
            "tier3_share": round(float(r["tier3_share"]), 3),
            "heavy_share": round(float(r["heavy_share"]), 3),
            "mappls_street": g.get("street", ""), "mappls_subLocality": g.get("subLocality", ""),
            "mappls_locality": g.get("locality", ""), "mappls_district": g.get("district", ""),
            "road_class": rclass, "road_exposure": exp,
            "impact_capacity_raw": round(float(r["impact"]) * exp, 2),
        })
    out = pd.DataFrame(rows).sort_values("impact_capacity_raw", ascending=False)
    # bound to 0-100 (order-preserving max-normalization) for UI consistency
    mx = out["impact_capacity_raw"].max() or 1.0
    out["impact_capacity"] = (100.0 * out["impact_capacity_raw"] / mx).round(2)
    os.makedirs("fe_work/fe_out", exist_ok=True)
    out.to_csv("fe_work/fe_out/top_enriched.csv", index=False)
    # GeoJSON points for the front-end
    feats = [{"type": "Feature",
              "geometry": {"type": "Point", "coordinates": [x["lon"], x["lat"]]},
              "properties": {k: x[k] for k in x if k not in ("lat", "lon")}}
             for x in out.to_dict("records")]
    json.dump({"type": "FeatureCollection", "features": feats},
              open("fe_work/fe_out/top_enriched.geojson", "w"))
    print(f"enriched {len(out)} cells | NEW API calls this run: {calls} (rest cached)")
    return out


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 50
    out = enrich(n)
    print(out.head(12)[["rank", "impact", "mappls_street", "mappls_locality",
                        "road_class", "road_exposure", "impact_capacity"]].to_string(index=False))
