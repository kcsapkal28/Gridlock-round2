import pandas as pd, numpy as np, sys, warnings; warnings.filterwarnings("ignore")
from scipy.stats import spearmanr, kendalltau
sys.path.insert(0,"/kaggle/working")
import scorelib, importlib; importlib.reload(scorelib)
from scorelib import ensemble_impact, impact_character, hand_composite, pct
from libpysal.weights import KNN
from esda.getisord import G_Local
b=pd.read_parquet("/kaggle/working/fe_base.parquet")
full=pd.read_parquet("/kaggle/working/cell_scores.parquet")
HEAVY=["BUS (BMTC/KSRTC)","PRIVATE BUS","TEMPO","HGV","LORRY/GOODS VEHICLE","TANKER","FACTORY BUS","TOURIST BUS","SCHOOL VEHICLE"]
COMM=HEAVY+["PASSENGER AUTO","GOODS AUTO","LGV","MAXI-CAB","VAN"]
TIER_W={0:0.0,1:0.5,2:1.0,3:6.0}

def build_scores(sub,beta=0.5,min_n=10):
    sub=sub.copy()
    sub["_ii"]=sub["max_sev"].map(TIER_W)*np.where(sub["vehicle_type_final"].isin(HEAVY),2.0,
                  np.where(sub["vehicle_type_final"].isin(COMM),1.3,1.0))
    loc=sub["location"].fillna("").str.lower()
    sub["_mr"]=loc.str.contains("main road",regex=False); sub["_jn"]=loc.str.contains("junction",regex=False)
    sub["_ci"]=loc.str.contains("circle",regex=False)
    g=sub.groupby("gh7")
    d=pd.DataFrame({"impact_intensity_total":g["_ii"].sum(),"lat":g["latitude"].mean(),"lon":g["longitude"].mean(),
        "n":g.size(),"tier3_share":g["max_sev"].apply(lambda s:(s>=3).mean()),
        "heavy_share":g["vehicle_type_final"].apply(lambda s:s.isin(HEAVY).mean()),
        "f_main_road":g["_mr"].mean(),"f_junction":g["_jn"].mean(),"f_circle":g["_ci"].mean()}).reset_index()
    d=d[d["n"]>=min_n].reset_index(drop=True)
    # EB smoothing (match 10_features): shrink rates toward global mean, K=25
    K=25; t3c=d["tier3_share"]*d["n"]; hvc=d["heavy_share"]*d["n"]
    mt3=t3c.sum()/d["n"].sum(); mh=hvc.sum()/d["n"].sum()
    d["tier3_share_eb"]=(t3c+K*mt3)/(d["n"]+K); d["heavy_share_eb"]=(hvc+K*mh)/(d["n"]+K)
    xy=d[["lon","lat"]].values; w=KNN.from_array(xy,k=min(8,len(d)-1)); w.transform="r"
    giz=G_Local(d["impact_intensity_total"].values.astype(float),w,star=True,seed=42).Zs
    d["impact"]=ensemble_impact(giz,impact_character(d),beta=beta)
    return d.set_index("gh7")["impact"]

b["created_dt"]=pd.to_datetime(b["created_dt"],utc=True)
half1=b[b["created_dt"]<"2024-02-01"]; half2=b[b["created_dt"]>="2024-02-01"]

# beta tuning: stability (Spearman half1 vs half2 at that beta) + face validity per beta
ranked_gh=set(full[full["ranked"]]["gh7"])   # well-supported cells (n>=50) — the ones we act on
print("beta | stab_all | stab_ranked | tier3_lift | heavy_lift")
base_t3=full["tier3_share"].mean(); base_h=full["heavy_share"].mean()
best=None
for beta in [0.25,0.4,0.5,0.6,0.75]:
    s1=build_scores(half1,beta); s2=build_scores(half2,beta)
    common=s1.index.intersection(s2.index); rho=spearmanr(s1[common],s2[common]).correlation
    rc=[g for g in common if g in ranked_gh]; rho_r=spearmanr(s1[rc],s2[rc]).correlation
    imp=ensemble_impact(full["gi_z"].values,full["impact_char"].values,beta=beta)
    t50=full.assign(_i=imp)[full["ranked"]].sort_values("_i",ascending=False).head(50)
    t3l=t50["tier3_share"].mean()/base_t3; hl=t50["heavy_share"].mean()/max(base_h,1e-9)
    print(f"{beta:.2f} |  {rho:.3f}  |   {rho_r:.3f}    |   {t3l:.2f}x   |  {hl:.2f}x")
    # select: max RANKED-cell stability among betas that deliver impact (tier3>=2.5, heavy>=1.2)
    if t3l>=2.5 and hl>=1.2 and (best is None or rho_r>best[1]): best=(beta,rho_r,t3l,hl)
print("SELECTED beta=%.2f (max ranked-stability s.t. tier3>=2.5 & heavy>=1.2): stab_ranked=%.3f, tier3=%.2fx, heavy=%.2fx"%best)

# concordance / bias on shipped score
top=full[full["ranked"]]; W=lambda a,c: kendalltau(a,c).correlation
print("concordance tau: Gi*-char=%.3f char-hand=%.3f Gi*-hand=%.3f"%(
    W(top["gi_z"],top["impact_char"]),W(top["impact_char"],top["hand_score"]),W(top["gi_z"],top["hand_score"])))
top50=full[full["ranked"]].sort_values("impact",ascending=False).head(50)
print("top-50 distinct_devices median=%.0f min=%.0f"%(top50["distinct_devices"].median(),top50["distinct_devices"].min()))
appr=b[b["validation_status_clean"]=="approved"]
sa=build_scores(appr,best[0]); ca=sa.index.intersection(full["gh7"])
rho_appr=spearmanr(sa[ca],pd.Series(full.set_index("gh7")["impact"]).reindex(ca)).correlation
print("approved-only sensitivity Spearman = %.3f"%rho_appr)
print("FACE VALIDITY (shipped): tier3 %.3f->%.3f (%.2fx) | heavy %.3f->%.3f (%.2fx)"%(
    base_t3,top50["tier3_share"].mean(),top50["tier3_share"].mean()/base_t3,
    base_h,top50["heavy_share"].mean(),top50["heavy_share"].mean()/max(base_h,1e-9)))
report=f"""# FE Validation Report (impact-intensity engine, EB-smoothed)
- Selected beta = {best[0]:.2f}
- Temporal stability (ranked cells, n>=50) Spearman = {best[1]:.3f}
- Approved-only sensitivity Spearman = {rho_appr:.3f} (threshold >=0.75)
- Top-50 median distinct_devices = {top50['distinct_devices'].median():.0f}
- Face validity: tier3 lift {top50['tier3_share'].mean()/base_t3:.2f}x | heavy lift {top50['heavy_share'].mean()/max(base_h,1e-9):.2f}x
- Concordance tau Gi*-char = {W(top['gi_z'],top['impact_char']):.3f}
"""
open("/kaggle/working/fe_out/validation_report.md","w").write(report)
print("\n"+report)
