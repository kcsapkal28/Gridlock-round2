import pandas as pd, matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt, json
plt.close("all")
df=pd.read_parquet("/kaggle/working/cleaned.parquet")
viol=df["violation_type"].map(lambda x: json.loads(x) if isinstance(x,str) else [])
exploded=viol.explode()
# GUARD: explode conserves total tags
assert exploded.notna().sum()==viol.map(len).sum(), "explode lost tags"
print("GUARD OK: tag conservation")
fig,axes=plt.subplots(2,2,figsize=(16,12))
df["vehicle_type"].value_counts().head(15).plot.bar(ax=axes[0,0],title="vehicle_type (top15)")
exploded.value_counts().head(15).plot.bar(ax=axes[0,1],title="violation_type (top15)")
df["police_station"].value_counts().head(15).plot.bar(ax=axes[1,0],title="police_station (top15)")
df["center_code"].value_counts().head(15).plot.bar(ax=axes[1,1],title="center_code (top15)")
for ax in axes.flat: ax.tick_params(axis="x",labelsize=7,rotation=90)
plt.tight_layout(); plt.savefig("/kaggle/working/eda_out/20_univariate.png",dpi=110)
print("saved 20_univariate.png")
print("\nvehicle_type top:", df["vehicle_type"].value_counts().head(8).to_dict())
print("violation top:", exploded.value_counts().head(8).to_dict())
