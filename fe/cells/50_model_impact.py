import pandas as pd, numpy as np
from sklearn.model_selection import GroupKFold
from sklearn.metrics import r2_score
from scipy.stats import spearmanr
import lightgbm as lgb
f=pd.read_parquet("/kaggle/working/cell_scores.parquet")  # features + impact/gi_z/impact_char
# train/eval on cells with enough evidence for a reliable target
d=f[f["n"]>=20].reset_index(drop=True)
groups=d["gh5"].astype("category").cat.codes.values
y=d["impact"].values

SCORE_INTERNAL={"impact","gi_z","gi_p","pca_composite","impact_char","hand_score","rank","ranked",
                "gh7","gh6","gh5","lat","lon"}
SPATIAL={"lag_n","lag_sev_sum","lag_tier3_share","kde_sev"}
allfeat=[c for c in d.columns if c not in SCORE_INTERNAL and d[c].dtype!=object]
FULL=allfeat
TRANSFER=[c for c in allfeat if c not in SPATIAL]   # cell-intrinsic only (no spatial leakage)
print("FULL feats:",len(FULL),"| TRANSFER feats:",len(TRANSFER),"| eval cells:",len(d),"| gh5 groups:",len(set(groups)))

def cv(feats,label):
    oof=np.zeros(len(d)); gkf=GroupKFold(n_splits=5)
    for tr,te in gkf.split(d,y,groups):
        m=lgb.LGBMRegressor(n_estimators=400,learning_rate=0.05,num_leaves=31,
            subsample=0.8,colsample_bytree=0.8,min_child_samples=20,reg_lambda=1.0,
            random_state=42,verbose=-1)
        m.fit(d.iloc[tr][feats],y[tr])
        oof[te]=m.predict(d.iloc[te][feats])
    r2=r2_score(y,oof); rho=spearmanr(y,oof).correlation
    print(f"  [{label:9s}] spatial-CV R2={r2:.3f}  Spearman={rho:.3f}")
    return oof,r2,rho

# baseline: volume only
oof_v,r2_v,_=cv(["n"],"volume")
oof_t,r2_t,rho_t=cv(TRANSFER,"transfer")
oof_f,r2_f,rho_f=cv(FULL,"full")

# feature importance from a full-data model (gain)
m=lgb.LGBMRegressor(n_estimators=400,learning_rate=0.05,num_leaves=31,subsample=0.8,
    colsample_bytree=0.8,min_child_samples=20,reg_lambda=1.0,random_state=42,verbose=-1)
m.fit(d[FULL],y)
imp=pd.Series(m.booster_.feature_importance(importance_type="gain"),index=FULL).sort_values(ascending=False)
imp.to_csv("/kaggle/working/fe_out/model_impact_importance.csv")
d.assign(pred_full=oof_f)[["gh7","impact","pred_full"]].to_csv("/kaggle/working/fe_out/model_impact_oof.csv",index=False)
m.booster_.save_model("/kaggle/working/fe_out/model_impact.txt")
print("\nTOP 12 IMPACT DRIVERS (gain):")
print(imp.head(12).round(0).to_string())
print("\nSUMMARY: volume-only R2=%.3f | transferable R2=%.3f | full R2=%.3f"%(r2_v,r2_t,r2_f))
