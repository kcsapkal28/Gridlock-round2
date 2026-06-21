import pandas as pd, numpy as np, warnings; warnings.filterwarnings("ignore")
from libpysal.weights import KNN
from esda.getisord import G_Local
from scipy.stats import spearmanr
b=pd.read_parquet("/kaggle/working/fe_base.parquet")[["gh7","max_sev","vehicle_type_final"]]
s=pd.read_parquet("/kaggle/working/cell_scores.parquet")
HEAVY={"BUS (BMTC/KSRTC)","PRIVATE BUS","TEMPO","HGV","LORRY/GOODS VEHICLE","TANKER","FACTORY BUS","TOURIST BUS","SCHOOL VEHICLE"}
COMM=HEAVY|{"PASSENGER AUTO","GOODS AUTO","LGV","MAXI-CAB","VAN"}
order=s["gh7"].values; charr=s["impact_char"].values; ranked=s["ranked"].values.astype(bool)
gh=b["gh7"].values; ms=b["max_sev"].values; veh=b["vehicle_type_final"]
ish=veh.isin(HEAVY).values; isc=veh.isin(COMM).values
# build spatial weights ONCE (reused across all configs — the efficiency fix)
w=KNN.from_array(s[["lon","lat"]].values,k=8); w.transform="r"

def score(w1,w2,w3,hm,cm,beta=0.75):
    tw=np.array([0.0,w1,w2,w3])
    ii=tw[ms]*np.where(ish,hm,np.where(isc,cm,1.0))
    it=pd.Series(ii).groupby(gh).sum().reindex(order).fillna(0).values.astype(float)
    giz=G_Local(it,w,star=True).Zs
    raw=beta*pd.Series(giz).rank(pct=True).values+(1-beta)*charr
    return 100*pd.Series(raw).rank(pct=True).values

base=score(0.5,1,6,2.0,1.3)  # shipped config
def cmp(imp):
    rho=spearmanr(base[ranked],imp[ranked]).correlation
    o=np.array(order)[ranked]
    t50b=set(o[np.argsort(-base[ranked])[:50]]); t50=set(o[np.argsort(-imp[ranked])[:50]])
    t20b=set(o[np.argsort(-base[ranked])[:20]]); t20=set(o[np.argsort(-imp[ranked])[:20]])
    return rho,len(t50b&t50),len(t20b&t20)

configs=[
 ("baseline (w3=6,hm=2.0)",(0.5,1,6,2.0,1.3)),
 ("Tier3 wt=3",(0.5,1,3,2.0,1.3)), ("Tier3 wt=4",(0.5,1,4,2.0,1.3)),
 ("Tier3 wt=8",(0.5,1,8,2.0,1.3)), ("Tier3 wt=10",(0.5,1,10,2.0,1.3)),
 ("heavy mult=1.0 (off)",(0.5,1,6,1.0,1.0)), ("heavy mult=1.5",(0.5,1,6,1.5,1.2)),
 ("heavy mult=3.0",(0.5,1,6,3.0,1.5)),
 ("Tier2 floor=0.5",(0.5,0.5,6,2.0,1.3)), ("Tier2 floor=1.5",(0.5,1.5,6,2.0,1.3)),
 ("Tier1=0",(0.0,1,6,2.0,1.3)), ("Tier1=1.0",(1.0,1,6,2.0,1.3)),
 ("extreme: w3=10,hm=3",(0.5,1,10,3.0,1.5)), ("flat-ish: w3=3,hm=1",(0.5,1,3,1.0,1.0)),
]
rows=[]
print(f"{'config':28s} {'Spearman':>9s} {'top50':>6s} {'top20':>6s}")
for name,p in configs:
    imp=score(*p); rho,o50,o20=cmp(imp)
    rows.append({"config":name,"spearman":round(rho,3),"top50_overlap":o50,"top20_overlap":o20})
    print(f"{name:28s} {rho:9.3f} {o50:5d}/50 {o20:4d}/20")
df=pd.DataFrame(rows); df.to_csv("/kaggle/working/fe_out/sensitivity.csv",index=False)
non=df[df.config!="baseline (w3=6,hm=2.0)"]
print("\nAcross %d perturbations: Spearman min=%.3f mean=%.3f | top50 overlap min=%d mean=%.1f | top20 min=%d"%(
    len(non),non.spearman.min(),non.spearman.mean(),non.top50_overlap.min(),non.top50_overlap.mean(),non.top20_overlap.min()))
