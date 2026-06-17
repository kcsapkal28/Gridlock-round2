import pandas as pd, numpy as np, sys
from scipy.stats import spearmanr, kendalltau
sys.path.insert(0,"/kaggle/working")
import scorelib, importlib; importlib.reload(scorelib)
from scorelib import ensemble_impact, hand_composite, pct
b=pd.read_parquet("/kaggle/working/fe_base.parquet")
full=pd.read_parquet("/kaggle/working/cell_scores.parquet")
HEAVY=["BUS (BMTC/KSRTC)","PRIVATE BUS","TEMPO","HGV","LORRY/GOODS VEHICLE","TANKER","FACTORY BUS","TOURIST BUS","SCHOOL VEHICLE"]

def build_scores(sub, min_n=10):
    from libpysal.weights import KNN
    from esda.getisord import G_Local
    import warnings; warnings.filterwarnings("ignore")
    g=sub.groupby("gh7")
    d=pd.DataFrame({"sev_sum_total":g["sev_sum"].sum(),"lat":g["latitude"].mean(),"lon":g["longitude"].mean(),
                    "n":g.size()}).reset_index()
    d=d[d["n"]>=min_n].reset_index(drop=True)
    xy=d[["lon","lat"]].values; w=KNN.from_array(xy,k=min(8,len(d)-1)); w.transform="r"
    giz=G_Local(d["sev_sum_total"].values.astype(float),w,star=True,seed=42).Zs
    d["impact"]=ensemble_impact(giz,d["sev_sum_total"].values,alpha=0.5)
    return d.set_index("gh7")["impact"]

b["created_dt"]=pd.to_datetime(b["created_dt"],utc=True)
half1=b[b["created_dt"]<"2024-02-01"]; half2=b[b["created_dt"]>="2024-02-01"]
s1=build_scores(half1); s2=build_scores(half2)
common=s1.index.intersection(s2.index)
rho_time=spearmanr(s1[common],s2[common]).correlation
print("TEMPORAL STABILITY Spearman(half1,half2) on %d common cells = %.3f"%(len(common),rho_time))

best=None
for a in [0,0.25,0.5,0.75,1.0]:
    imp=ensemble_impact(full["gi_z"].values,full["pca_composite"].values,alpha=a)
    tmp=pd.Series(imp,index=full["gh7"]).reindex(common)
    r=spearmanr(tmp,s2[common]).correlation
    print(f"  alpha={a}: stability-proxy Spearman={r:.3f}")
    if best is None or r>best[1]: best=(a,r)
print("SELECTED alpha=%.2f"%best[0])

top=full[full["ranked"]]
W=lambda a,b: kendalltau(a,b).correlation
print("concordance tau: Gi*-PCA=%.3f PCA-hand=%.3f Gi*-hand=%.3f"%(
    W(top["gi_z"],top["pca_composite"]),W(top["pca_composite"],top["hand_score"]),W(top["gi_z"],top["hand_score"])))

top50=full[full["ranked"]].sort_values("impact",ascending=False).head(50)
print("top-50 distinct_devices: median=%.0f min=%.0f"%(top50["distinct_devices"].median(),top50["distinct_devices"].min()))
appr=b[b["validation_status_clean"]=="approved"]
sa=build_scores(appr); ca=sa.index.intersection(full["gh7"])
rho_appr=spearmanr(sa[ca],pd.Series(full.set_index("gh7")["impact"]).reindex(ca)).correlation
print("approved-only sensitivity Spearman vs full = %.3f"%rho_appr)

base_t3=full["tier3_share"].mean(); base_h=full["heavy_share"].mean()
print("FACE VALIDITY lift: tier3_share %.3f->%.3f (%.2fx) | heavy_share %.3f->%.3f (%.2fx)"%(
    base_t3,top50["tier3_share"].mean(),top50["tier3_share"].mean()/base_t3,
    base_h,top50["heavy_share"].mean(),top50["heavy_share"].mean()/max(base_h,1e-9)))

report=f"""# FE Validation Report
- Temporal stability Spearman = {rho_time:.3f} (threshold >=0.80)
- Selected alpha = {best[0]:.2f}
- Method concordance tau Gi*-PCA = {W(top['gi_z'],top['pca_composite']):.3f}
- Approved-only sensitivity Spearman = {rho_appr:.3f} (threshold >=0.75)
- Top-50 median distinct_devices = {top50['distinct_devices'].median():.0f}
- Face-validity tier3 lift = {top50['tier3_share'].mean()/base_t3:.2f}x | heavy lift = {top50['heavy_share'].mean()/max(base_h,1e-9):.2f}x
"""
open("/kaggle/working/fe_out/validation_report.md","w").write(report)
print("\n"+report)
