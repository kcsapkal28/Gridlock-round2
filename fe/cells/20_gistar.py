import pandas as pd, numpy as np
from libpysal.weights import KNN
from esda.getisord import G_Local
f=pd.read_parquet("/kaggle/working/cell_features_full.parquet")
xy=f[["lon","lat"]].values
w=KNN.from_array(xy,k=8); w.transform="r"
y=f["impact_intensity_total"].values.astype(float)   # Gi* on IMPACT intensity, not volume
gi=G_Local(y,w,star=True,seed=42)   # Gi* (include self)
f["gi_z"]=gi.Zs
f["gi_p"]=gi.p_sim
# GUARD: output length matches cells; z-scores finite
assert len(gi.Zs)==len(f), "Gi* length mismatch"
assert np.isfinite(f["gi_z"]).all(), "Gi* produced non-finite z"
f.to_parquet("/kaggle/working/cell_features_full.parquet")
sig=(f["gi_p"]<0.05)&(f["gi_z"]>0)
print("significant hot cells (p<0.05, z>0): %d / %d"%(int(sig.sum()),len(f)))
print(f.sort_values("gi_z",ascending=False)[["gh7","n","tier3_share","gi_z","gi_p"]].head(10).round(3).to_string(index=False))
