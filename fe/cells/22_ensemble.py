import pandas as pd, numpy as np, sys
sys.path.insert(0,"/kaggle/working")
import scorelib, importlib; importlib.reload(scorelib)
from scorelib import ensemble_impact, impact_character, hand_composite, pct
f=pd.read_parquet("/kaggle/working/cell_features_full.parquet")
BETA=0.75  # blend weight Gi*-significance vs impact-character; selected in 30_validate
           # (max ranked-cell stability s.t. tier3>=2.5 & heavy>=1.2; EB-smoothed rates, K=40)
f["impact_char"]=impact_character(f)
f["impact"]=ensemble_impact(f["gi_z"].values,f["impact_char"].values,beta=BETA)
f["hand_score"]=hand_composite(f)
f["rank"]=f["impact"].rank(ascending=False).astype(int)
# GUARD: impact in [0,100]
assert f["impact"].between(0,100).all(), "impact out of range"
f.to_parquet("/kaggle/working/cell_scores.parquet")
top=f[f["ranked"]].sort_values("impact",ascending=False).head(15)
print(top[["gh7","n","tier3_share","heavy_share","gi_z","impact_char","impact"]].round(3).to_string(index=False))
