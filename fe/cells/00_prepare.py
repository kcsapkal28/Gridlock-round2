import pandas as pd, numpy as np, pygeohash as pgh
df=pd.read_parquet("/kaggle/working/cleaned.parquet")
sev=pd.read_parquet("/kaggle/working/derived/severity.parquet")
n0=len(df)
df=df.merge(sev[["id","max_sev","sev_sum"]],on="id",how="left")
# GUARD 1: severity join conserves rows and is complete
assert len(df)==n0 and df["max_sev"].notna().all(), "severity join lost rows or has NaN"
# is_valid already on cleaned.parquet; filter
base=df[df["is_valid"]].copy()
print("is_valid retained: %d / %d (%.1f%%)"%(len(base),n0,len(base)/n0*100))
# coalesce vehicle type
ut=base["updated_vehicle_type"]
base["vehicle_type_final"]=ut.where(~(ut.isin(["NULL",""])|ut.isna()), base["vehicle_type"])
# GUARD 2: no null vehicle_type_final
assert base["vehicle_type_final"].notna().all(), "vehicle_type_final has nulls"
# geohash encode (gh7 primary, gh6/gh5 rollups)
base["gh7"]=[pgh.encode(la,lo,precision=7) for la,lo in zip(base["latitude"],base["longitude"])]
base["gh6"]=base["gh7"].str[:6]; base["gh5"]=base["gh7"].str[:5]
# GUARD 3: geohash length correct
assert (base["gh7"].str.len()==7).all(), "gh7 wrong length"
base.to_parquet("/kaggle/working/fe_base.parquet")
print("fe_base rows:",len(base),"| distinct gh7:",base["gh7"].nunique(),
      "| gh6:",base["gh6"].nunique(),"| gh5:",base["gh5"].nunique())
