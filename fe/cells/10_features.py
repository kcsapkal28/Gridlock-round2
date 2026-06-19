import pandas as pd, numpy as np
b=pd.read_parquet("/kaggle/working/fe_base.parquet")
b["created_dt"]=pd.to_datetime(b["created_dt"],utc=True)
b["isoweek"]=b["created_dt"].dt.isocalendar().week  # nullable UInt32; nunique ignores NaT
b["date"]=b["created_dt"].dt.date
HEAVY={"BUS (BMTC/KSRTC)","PRIVATE BUS","TEMPO","HGV","LORRY/GOODS VEHICLE","TANKER","FACTORY BUS","TOURIST BUS","SCHOOL VEHICLE"}
COMMERCIAL=HEAVY|{"PASSENGER AUTO","GOODS AUTO","LGV","MAXI-CAB","VAN"}
TWOW={"SCOOTER","MOTOR CYCLE","MOPED"}
# per-ticket impact intensity: steep tier weights x vehicle multiplier (impact, not volume)
TIER_W={0:0.0,1:0.5,2:1.0,3:6.0}
b["_tw"]=b["max_sev"].map(TIER_W)
b["_vmult"]=np.where(b["vehicle_type_final"].isin(HEAVY),2.0,
              np.where(b["vehicle_type_final"].isin(COMMERCIAL),1.3,1.0))
b["impact_intensity"]=b["_tw"]*b["_vmult"]
loc=b["location"].fillna("").str.lower()
b["f_main_road"]=loc.str.contains("main road",regex=False)
b["f_circle"]=loc.str.contains("circle",regex=False)
b["f_cross"]=loc.str.contains("cross",regex=False)
b["f_junction"]=loc.str.contains("junction",regex=False)
b["f_busstop_school_hosp"]=loc.str.contains("bus stop|busstop|school|hospital",regex=True)
b["f_metro"]=loc.str.contains("metro",regex=False)
b["f_market"]=loc.str.contains("market",regex=False)
b["f_mall"]=loc.str.contains("mall",regex=False)
# context fields for the front-end (derivable; clearance latency is NOT derivable — closure cols 100% null)
def _vclass(v):
    if v in TWOW: return "TWO-WHEELER"
    if v in HEAVY: return "FREIGHT/HEAVY"
    if v in {"PASSENGER AUTO","GOODS AUTO"}: return "AUTO"
    if v in {"CAR","MAXI-CAB","JEEP","VAN"}: return "CAR/LV"
    return "OTHER"
b["_vclass"]=b["vehicle_type_final"].map(_vclass)
_mode=lambda s: s.mode().iat[0] if len(s.mode()) else ""
g=b.groupby("gh7")
feat=pd.DataFrame({
 "n":g.size(),
 "n_valid":g.size(),
 "distinct_days":g["date"].nunique(),
 "distinct_weeks":g["isoweek"].nunique(),
 "lat":g["latitude"].mean(),"lon":g["longitude"].mean(),
 "gh6":g["gh6"].first(),"gh5":g["gh5"].first(),
 "sev_sum_total":g["sev_sum"].sum(),
 "impact_intensity_total":g["impact_intensity"].sum(),
 "mean_sev":g["sev_sum"].mean(),
 "tier3_count":g["max_sev"].apply(lambda s:(s>=3).sum()),
 "tier3_share":g["max_sev"].apply(lambda s:(s>=3).mean()),
 "heavy_share":g["vehicle_type_final"].apply(lambda s:s.isin(HEAVY).mean()),
 "commercial_share":g["vehicle_type_final"].apply(lambda s:s.isin(COMMERCIAL).mean()),
 "twowheeler_share":g["vehicle_type_final"].apply(lambda s:s.isin(TWOW).mean()),
 "f_main_road":g["f_main_road"].mean(),"f_circle":g["f_circle"].mean(),
 "f_cross":g["f_cross"].mean(),"f_junction":g["f_junction"].mean(),
 "f_busstop_school_hosp":g["f_busstop_school_hosp"].mean(),
 "f_metro":g["f_metro"].mean(),"f_market":g["f_market"].mean(),"f_mall":g["f_mall"].mean(),
 "distinct_devices":g["device_id"].nunique(),
 "distinct_officers":g["created_by_id"].nunique(),
 "recurrence_weeks":g["isoweek"].nunique(),
 "dominant_vehicle_class":g["_vclass"].agg(_mode),
}).reset_index()
# primary_infraction_type: most common violation label per cell (explode multi-label JSON)
import json as _json
_viol=b["violation_type"].map(lambda x:_json.loads(x) if isinstance(x,str) else [])
_ex=pd.DataFrame({"gh7":b["gh7"].values,"v":_viol.values}).explode("v").dropna(subset=["v"])
_prim=_ex.groupby("gh7")["v"].agg(_mode).rename("primary_infraction_type")
feat=feat.merge(_prim,on="gh7",how="left")
feat["primary_infraction_type"]=feat["primary_infraction_type"].fillna("")
# GUARD: cell counts sum to base rows; tier3_share in [0,1]
assert feat["n"].sum()==len(b), "feature counts != base rows"
assert feat["tier3_share"].between(0,1).all(), "tier3_share out of range"
# Empirical-Bayes shrinkage of small-cell rates toward the global mean (K pseudo-tickets):
# reduces noise from tiny cells whose tier3/heavy rates are unreliable (improves stability).
K_EB=40
m_t3=feat["tier3_count"].sum()/feat["n"].sum()
heavy_count=feat["heavy_share"]*feat["n"]
m_h=heavy_count.sum()/feat["n"].sum()
feat["tier3_share_eb"]=(feat["tier3_count"]+K_EB*m_t3)/(feat["n"]+K_EB)
feat["heavy_share_eb"]=(heavy_count+K_EB*m_h)/(feat["n"]+K_EB)
feat["ranked"]=feat["n_valid"]>=50   # headline ranking needs real evidence
feat.to_parquet("/kaggle/working/cell_features.parquet")
print("cells:",len(feat),"| ranked(>=25):",int(feat["ranked"].sum()))
print(feat[["n","tier3_share","heavy_share","f_main_road"]].describe().round(3).to_string())
