import pandas as pd, numpy as np, sys
sys.path.insert(0,"/kaggle/working")
import scorelib; import importlib; importlib.reload(scorelib)
from scorelib import ensemble_impact, hand_composite, pct
f=pd.read_parquet("/kaggle/working/cell_features_full.parquet")
f["impact"]=ensemble_impact(f["gi_z"].values,f["pca_composite"].values,alpha=0.5)  # alpha tuned in 30
f["hand_score"]=hand_composite(f)
f["rank"]=f["impact"].rank(ascending=False).astype(int)
# GUARD: impact in [0,100]
assert f["impact"].between(0,100).all(), "impact out of range"
f.to_parquet("/kaggle/working/cell_scores.parquet")
top=f[f["ranked"]].sort_values("impact",ascending=False).head(15)
print(top[["gh7","n","tier3_share","heavy_share","gi_z","impact","hand_score"]].round(2).to_string(index=False))
