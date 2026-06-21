import pandas as pd, numpy as np, json, os
# Blind spot = zone whose VOLUME-INDEPENDENT impact character is high but enforcement coverage is low.
# We use `impact_char` (EB-smoothed Tier-3 + heavy + road context; built in 22_ensemble) as the predictor.
# The shipped intrinsic model includes volume features (n), so its prediction tracks coverage and can't
# surface blind spots — impact_char is the leakage-free signal for "looks high-impact but under-ticketed".
f=pd.read_parquet("/kaggle/working/cell_scores.parquet")
f["char_pct"]=f["impact_char"].rank(pct=True)
f["cov_pct"]=f["n"].rank(pct=True)
f["blind_gap"]=f["char_pct"]-f["cov_pct"]
bs=f[(f["char_pct"]>=0.80)&(f["cov_pct"]<=0.45)].sort_values("blind_gap",ascending=False).head(80)
# GUARD: some but not all cells flagged
assert 0 < len(bs) < len(f), f"blind-spot count off: {len(bs)} of {len(f)}"
def g(r,k): return str(getattr(r,k,"")) if hasattr(r,k) else ""
feats=[{"type":"Feature","geometry":{"type":"Point","coordinates":[float(r.lon),float(r.lat)]},
        "properties":{"gh7":r.gh7,"predicted_impact":round(float(r.char_pct*100),1),"n":int(r.n),
            "distinct_devices":int(r.distinct_devices),"blind_gap":round(float(r.blind_gap),3),
            "dominant_vehicle_class":g(r,"dominant_vehicle_class"),
            "primary_infraction_type":g(r,"primary_infraction_type")}} for r in bs.itertuples()]
os.makedirs("/kaggle/working/fe_out",exist_ok=True)
json.dump({"type":"FeatureCollection","features":feats}, open("/kaggle/working/fe_out/blindspots.geojson","w"))
print("blind spots:",len(feats),"of",len(f),"cells")
