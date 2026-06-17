import pandas as pd, numpy as np
df = pd.read_parquet("/kaggle/working/raw.parquet")
n0=len(df)
for c in ["latitude","longitude"]: df[c]=pd.to_numeric(df[c],errors="coerce")
df["created_dt"]=pd.to_datetime(df["created_datetime"],errors="coerce",utc=True)

# duplicate key: same vehicle, same ~location (5dp), same minute
df["_dupkey"]=(df["vehicle_number"].astype(str)+"|"+df["latitude"].round(5).astype(str)
              +"|"+df["longitude"].round(5).astype(str)+"|"+df["created_dt"].dt.floor("min").astype(str))
dups=df["_dupkey"].duplicated().sum()
print("exact-ish duplicate rows:", dups, f"({dups/n0*100:.2f}%)")
clean=df.drop_duplicates("_dupkey").copy()

# bbox filter (Gate 0 branch: expected ~0 dropped)
inbox=clean["latitude"].between(12.7,13.35)&clean["longitude"].between(77.3,77.9)
print("dropping out-of-bbox:", int((~inbox).sum()))
clean=clean[inbox]

# is_valid flag (Gate 1A): exclude rejected/duplicate; keep approved/created1/processing/NULL
isnull = clean["validation_status"].isin(["NULL",""]) | clean["validation_status"].isna()
vs = clean["validation_status"].where(~isnull, "NULL")
clean["validation_status_clean"]=vs
clean["is_valid"]= ~vs.isin(["rejected","duplicate"])
print("is_valid share: %.2f%%" % (clean["is_valid"].mean()*100))

clean=clean.drop(columns=["description","closed_datetime","action_taken_timestamp","_dupkey"])
# GUARD: monotonic shrink only, never grew, and lost < 5% total
assert len(clean)<=n0 and len(clean)>=0.95*n0, f"cleaning removed too much: {n0}->{len(clean)}"
clean.to_parquet("/kaggle/working/cleaned.parquet")
print("CLEANED rows:", len(clean), "from", n0, "| cols:", clean.shape[1])
