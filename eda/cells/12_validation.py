import pandas as pd
df = pd.read_parquet("/kaggle/working/raw.parquet")
isnull = lambda s: df[s].isin(["NULL",""]) | df[s].isna()
vs = df["validation_status"].where(~isnull("validation_status"), "NULL")
print("validation_status counts:")
print(vs.value_counts(dropna=False).to_string())
print("share:", (vs.value_counts(normalize=True)*100).round(2).to_dict())

# GUARD: the 42%-null block is co-null (one review event populates all four)
block = ["validation_status","updated_vehicle_number","updated_vehicle_type","validation_timestamp"]
conull = pd.DataFrame({c: isnull(c) for c in block})
print("\nco-null agreement matrix:")
print(conull.corr().round(3).to_string())

# scita send vs validation outcome
print("\nvalidation_status x data_sent_to_scita (row-normalised):")
print(pd.crosstab(vs, df["data_sent_to_scita"], normalize="index").round(3).to_string())

# is 'rejected'/'duplicate' spatially/station concentrated?
df["_vs"]=vs
bad = df["_vs"].isin(["rejected","duplicate"])
print("\nrejected+duplicate share: %.2f%%" % (bad.mean()*100))
print("top stations by rejected+duplicate RATE (min 1000 tickets):")
g = df.groupby("police_station")["_vs"].agg(lambda s: s.isin(["rejected","duplicate"]).mean())
cnt = df["police_station"].value_counts()
g = g[cnt[g.index]>=1000].sort_values(ascending=False)
print((g*100).round(1).head(10).to_string())
