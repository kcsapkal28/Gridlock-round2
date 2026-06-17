import pandas as pd, json, matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt, seaborn as sns
plt.close("all")
df=pd.read_parquet("/kaggle/working/cleaned.parquet")
sev=pd.read_parquet("/kaggle/working/derived/severity.parquet")
df=df.merge(sev[["id","max_sev","sev_sum"]],on="id")
# vehicle x severity (use sev_sum bucket since max_sev is near-binary)
ct=pd.crosstab(df["vehicle_type"],df["max_sev"],normalize="index")
assert (ct.sum(axis=1).round(3)==1).all(), "crosstab rows don't normalise"
print("GUARD OK crosstab normalised")
topveh=df["vehicle_type"].value_counts().head(15).index
plt.figure(figsize=(9,8)); sns.heatmap(ct.loc[topveh],annot=True,fmt=".3f",cmap="mako")
plt.title("Vehicle type x max severity tier (row-normalised)"); plt.tight_layout()
plt.savefig("/kaggle/working/eda_out/50_vehicle_severity.png",dpi=110)
print("saved 50_vehicle_severity.png")
# which vehicle types most often cause Tier-3
print("\nTier-3 rate by vehicle (top by rate, min 500 tickets):")
g=df.groupby("vehicle_type").agg(n=("id","size"),t3=("max_sev",lambda s:(s>=3).mean()))
print((g[g.n>=500].sort_values("t3",ascending=False).assign(t3pct=lambda d:(d.t3*100).round(1))[["n","t3pct"]]).head(12).to_string())
# per-station mean severity ranking
print("\nstations by mean sev_sum (min 2000 tickets):")
sg=df.groupby("police_station").agg(n=("id","size"),msev=("sev_sum","mean"))
print(sg[sg.n>=2000].sort_values("msev",ascending=False).assign(msev=lambda d:d.msev.round(2)).head(12).to_string())
