import pandas as pd, numpy as np
from sklearn.model_selection import GroupKFold
from sklearn.metrics import roc_auc_score, average_precision_score
import lightgbm as lgb
f=pd.read_parquet("/kaggle/working/cell_scores.parquet")
d=f[f["n"]>=20].reset_index(drop=True)
groups=d["gh5"].astype("category").cat.codes.values
# label: high-IMPACT hotspot = top quartile of impact among busy cells
thr=d["impact"].quantile(0.75)
y=(d["impact"]>=thr).astype(int).values
print("hotspot label: impact>=%.1f | positives=%d/%d (%.1f%%) | gh5 groups=%d"%(
    thr,y.sum(),len(y),y.mean()*100,len(set(groups))))

SCORE_INTERNAL={"impact","gi_z","gi_p","pca_composite","impact_char","hand_score","rank","ranked",
                "gh7","gh6","gh5","lat","lon"}
SPATIAL={"lag_n","lag_sev_sum","lag_tier3_share","kde_sev"}
allfeat=[c for c in d.columns if c not in SCORE_INTERNAL and d[c].dtype!=object]
FULL=allfeat; TRANSFER=[c for c in allfeat if c not in SPATIAL]

def cv(feats,label):
    oof=np.zeros(len(d)); gkf=GroupKFold(n_splits=5)
    for tr,te in gkf.split(d,y,groups):
        m=lgb.LGBMClassifier(n_estimators=400,learning_rate=0.05,num_leaves=31,subsample=0.8,
            colsample_bytree=0.8,min_child_samples=20,reg_lambda=1.0,random_state=42,verbose=-1)
        m.fit(d.iloc[tr][feats],y[tr]); oof[te]=m.predict_proba(d.iloc[te][feats])[:,1]
    auc=roc_auc_score(y,oof); ap=average_precision_score(y,oof)
    print(f"  [{label:9s}] spatial-CV ROC-AUC={auc:.3f}  PR-AUC={ap:.3f}")
    return oof,auc,ap

oof_v,auc_v,_=cv(["n"],"volume")
oof_t,auc_t,ap_t=cv(TRANSFER,"transfer")
oof_f,auc_f,ap_f=cv(FULL,"full")

m=lgb.LGBMClassifier(n_estimators=400,learning_rate=0.05,num_leaves=31,subsample=0.8,
    colsample_bytree=0.8,min_child_samples=20,reg_lambda=1.0,random_state=42,verbose=-1)
m.fit(d[FULL],y)
imp=pd.Series(m.booster_.feature_importance(importance_type="gain"),index=FULL).sort_values(ascending=False)
imp.to_csv("/kaggle/working/fe_out/model_detect_importance.csv")
d.assign(p_hotspot=oof_f)[["gh7","impact","p_hotspot"]].to_csv("/kaggle/working/fe_out/model_detect_oof.csv",index=False)
m.booster_.save_model("/kaggle/working/fe_out/model_detect.txt")
print("\nTOP 10 DETECTION FEATURES (gain):"); print(imp.head(10).round(0).to_string())
print("\nSUMMARY ROC-AUC: volume=%.3f | transferable=%.3f | full=%.3f"%(auc_v,auc_t,auc_f))
