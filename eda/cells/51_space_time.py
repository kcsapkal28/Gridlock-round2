import pandas as pd, numpy as np, matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.cluster import DBSCAN
plt.close("all")
df=pd.read_parquet("/kaggle/working/cleaned.parquet")
ist=pd.to_datetime(df["created_dt"]).dt.tz_convert("Asia/Kolkata")
df["hour"]=ist.dt.hour
# recompute clusters (cheap enough) to attach hour profiles to top hotspots
coords=np.radians(df[["latitude","longitude"]].values)
df["cluster"]=DBSCAN(eps=150/6371000.0,min_samples=30,metric="haversine",algorithm="ball_tree").fit(coords).labels_
top=df[df.cluster>=0]["cluster"].value_counts().head(8).index
plt.figure(figsize=(12,6))
for cl in top:
    sub=df[df.cluster==cl]
    prof=sub["hour"].value_counts(normalize=True).sort_index().reindex(range(24),fill_value=0)
    st=sub["police_station"].mode().iat[0]
    plt.plot(range(24),prof.values,marker=".",label=f"cl{cl} ({st}, n={len(sub)})")
plt.legend(fontsize=7); plt.xlabel("hour (IST)"); plt.ylabel("share of cluster's tickets")
plt.title("ENFORCEMENT-ACTIVITY hour profile by top-8 hotspot (NOT congestion timing)")
plt.tight_layout(); plt.savefig("/kaggle/working/eda_out/51_space_time.png",dpi=110)
print("saved 51_space_time.png")
# quantify how different the hotspots' peak enforcement hours are
for cl in top:
    sub=df[df.cluster==cl]
    pk=int(sub["hour"].value_counts().idxmax())
    print(f"cluster {int(cl):3d} ({sub['police_station'].mode().iat[0]:16s}) peak enforcement hour = {pk:02d}:00 IST, n={len(sub)}")
