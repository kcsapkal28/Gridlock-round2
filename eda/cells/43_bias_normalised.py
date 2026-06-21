import pandas as pd, numpy as np, matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
plt.close("all")
df=pd.read_parquet("/kaggle/working/cleaned.parquet")
df["glat"]=df["latitude"].round(3); df["glon"]=df["longitude"].round(3)
# per-cell: raw count, distinct devices, distinct officers
g=df.groupby(["glat","glon"]).agg(n=("id","size"),
                                  n_dev=("device_id","nunique"),
                                  n_off=("created_by_id","nunique")).reset_index()
# a genuine hotspot is seen by MANY devices; a patrol artifact is one device hammering a spot
g["tickets_per_device"]=g["n"]/g["n_dev"]
g=g[g["n"]>=50]  # focus on real cells
g["rank_raw"]=g["n"].rank(ascending=False)
g["rank_perdev"]=g["tickets_per_device"].rank(ascending=False)
g["rank_shift"]=g["rank_raw"]-g["rank_perdev"]   # +ve: looks smaller once normalised
print("cells with >=50 tickets:",len(g))
print("\nTOP 10 by RAW count:")
print(g.sort_values("n",ascending=False).head(10)[["glat","glon","n","n_dev","tickets_per_device"]].round(1).to_string(index=False))
print("\nTOP 10 by TICKETS-PER-DEVICE (single-device-dominated = likely patrol artifact):")
print(g.sort_values("tickets_per_device",ascending=False).head(10)[["glat","glon","n","n_dev","tickets_per_device"]].round(1).to_string(index=False))
print("\ncorrelation(raw count, distinct devices): %.3f"%g["n"].corr(g["n_dev"]))
g.to_parquet("/kaggle/working/derived/grid_bias.parquet")
fig,ax=plt.subplots(1,2,figsize=(15,7))
sc0=ax[0].scatter(g["glon"],g["glat"],c=np.log10(g["n"]),cmap="inferno",s=8)
ax[0].set_title("Raw ticket density (log)"); plt.colorbar(sc0,ax=ax[0])
sc1=ax[1].scatter(g["glon"],g["glat"],c=g["n_dev"],cmap="viridis",s=8)
ax[1].set_title("Distinct devices per cell (breadth)"); plt.colorbar(sc1,ax=ax[1])
plt.tight_layout(); plt.savefig("/kaggle/working/eda_out/43_bias_normalised.png",dpi=110)
print("saved 43_bias_normalised.png")
