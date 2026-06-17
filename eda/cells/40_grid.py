import pandas as pd, numpy as np, matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
plt.close("all")
df=pd.read_parquet("/kaggle/working/cleaned.parquet")
df["glat"]=df["latitude"].round(3); df["glon"]=df["longitude"].round(3)  # ~110m cells
grid=df.groupby(["glat","glon"]).size().rename("n").reset_index()
# GUARD: binning conserves all rows
assert grid["n"].sum()==len(df), "grid lost rows"
print("GUARD OK: %d rows -> %d cells"%(len(df),len(grid)))
grid.to_parquet("/kaggle/working/derived/grid_counts.parquet")
gs=grid.sort_values("n",ascending=False)
cells_50=(gs["n"].cumsum()<=0.5*len(df)).sum()+1
print("top cell count:", int(grid["n"].max()),
      "| cells holding 50%% of tickets: %d (%.2f%% of cells)"%(cells_50,cells_50/len(grid)*100))
print("top 10 cells:")
print(gs.head(10).to_string(index=False))
plt.figure(figsize=(10,10))
hb=plt.hexbin(df["longitude"],df["latitude"],gridsize=120,cmap="inferno",bins="log")
plt.colorbar(hb,label="log10(tickets)"); plt.title("Parking-violation density — Bengaluru")
plt.xlabel("longitude"); plt.ylabel("latitude")
plt.savefig("/kaggle/working/eda_out/40_density.png",dpi=120)
print("saved 40_density.png")
