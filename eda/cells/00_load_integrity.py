import pandas as pd, numpy as np, hashlib, json, os
SRC = "/kaggle/input/datasets/kartikeysapkal/gridlock-round2-csv/jan to may police violation_anonymized791b166.csv"
df = pd.read_csv(SRC, dtype=str)            # read raw as str; we cast deliberately later
print("RAW shape:", df.shape)

# GUARD 1: expected row/col count (locally profiled = 298450 rows, 24 cols)
assert df.shape == (298450, 24), f"unexpected shape {df.shape}"

# GUARD 2: id is unique (primary key sanity)
assert df["id"].is_unique, "id not unique!"

# GUARD 3: lat/lon parse to float and sit inside Bengaluru bbox (allow tiny margin)
lat = pd.to_numeric(df["latitude"], errors="coerce")
lon = pd.to_numeric(df["longitude"], errors="coerce")
inbox = lat.between(12.7, 13.35) & lon.between(77.3, 77.9)
print("coords parseable:", round(lat.notna().mean()*100, 4), "% ; in-bbox:", round(inbox.mean()*100, 4), "%")

# Persist an immutable raw checkpoint as parquet (fast reload on token expiry)
os.makedirs("/kaggle/working", exist_ok=True)
df.to_parquet("/kaggle/working/raw.parquet")
print("checkpoint raw.parquet written")
print("DTYPES:", df.dtypes.astype(str).to_dict())
print("HEAD2:", json.dumps(df.head(2).to_dict(orient="records"), default=str)[:1500])
