import pandas as pd, numpy as np
from libpysal.weights import KNN
from scipy.stats import gaussian_kde
f=pd.read_parquet("/kaggle/working/cell_features.parquet")
n_in=len(f)
xy=f[["lon","lat"]].values
w=KNN.from_array(xy,k=8); w.transform="r"
def lag(col):
    a=f[col].values
    return np.array([sum(wt*a[nb] for wt,nb in zip(w.weights[i],w.neighbors[i])) for i in range(len(f))])
f["lag_n"]=lag("n"); f["lag_sev_sum"]=lag("sev_sum_total"); f["lag_tier3_share"]=lag("tier3_share")
# severity-weighted KDE evaluated at centroids
pts=np.vstack([f["lon"],f["lat"]])
kde=gaussian_kde(pts,weights=f["sev_sum_total"].values,bw_method=0.05)
f["kde_sev"]=kde(pts)
# interactions
f["heavy_x_mainroad"]=f["heavy_share"]*f["f_main_road"]
f["tier3_x_junction"]=f["tier3_share"]*f["f_junction"]
# GUARD: no NaN introduced; lengths preserved
assert len(f)==n_in, "row count changed"
assert f[["lag_n","lag_sev_sum","kde_sev","heavy_x_mainroad"]].notna().all().all(), "NaN in new features"
f.to_parquet("/kaggle/working/cell_features_full.parquet")
print("added spatial-lag/KDE/interactions; cells:",len(f),"cols:",f.shape[1])
print(f[["lag_sev_sum","kde_sev","heavy_x_mainroad","tier3_x_junction"]].describe().round(4).to_string())
