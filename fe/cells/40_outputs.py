import pandas as pd, numpy as np, json
import pygeohash as pgh
f=pd.read_parquet("/kaggle/working/cell_scores.parquet")
def cell_polygon(gh):
    la,lo,dla,dlo=pgh.decode_exactly(gh)
    return [[lo-dlo,la-dla],[lo+dlo,la-dla],[lo+dlo,la+dla],[lo-dlo,la+dla],[lo-dlo,la-dla]]
feats=[]
for _,r in f.iterrows():
    feats.append({"type":"Feature","geometry":{"type":"Polygon","coordinates":[cell_polygon(r["gh7"])]},
        "properties":{"gh7":r["gh7"],"impact":round(float(r["impact"]),2),"rank":int(r["rank"]),
            "n":int(r["n"]),"tier3_share":round(float(r["tier3_share"]),3),
            "heavy_share":round(float(r["heavy_share"]),3),"gi_z":round(float(r["gi_z"]),2),
            "ranked":bool(r["ranked"])}})
gj={"type":"FeatureCollection","features":feats}
json.dump(gj,open("/kaggle/working/fe_out/cells.geojson","w"))
# GUARD: feature count == cell count
assert len(gj["features"])==len(f), "geojson feature count mismatch"
for k in ["gh6","gh5"]:
    roll=f.groupby(k).agg(impact_mean=("impact","mean"),impact_max=("impact","max"),
                          n=("n","sum"),lat=("lat","mean"),lon=("lon","mean")).reset_index()
    roll.to_csv(f"/kaggle/working/fe_out/rollup_{k}.csv",index=False)
prio=f[f["ranked"]].sort_values("impact",ascending=False).head(100)[
    ["rank","gh7","lat","lon","impact","n","tier3_share","heavy_share","f_main_road","f_junction","gi_z","distinct_devices"]]
prio.to_csv("/kaggle/working/fe_out/priority_table.csv",index=False)
f[["lon","lat","kde_sev","impact"]].to_csv("/kaggle/working/fe_out/kde_points.csv",index=False)
print("wrote cells.geojson (%d features), rollup_gh6/gh5.csv, priority_table.csv, kde_points.csv"%len(feats))
print("\nTOP-10 PRIORITY ZONES:")
print(prio.head(10)[["rank","gh7","lat","lon","impact","n","tier3_share","heavy_share"]].round(3).to_string(index=False))
