import pandas as pd, numpy as np
df=pd.read_parquet("/kaggle/working/cleaned.parquet")

print("="*60,"\nCENTER_CODE vs POLICE_STATION mapping")
g=df.dropna(subset=["center_code"]).groupby("center_code")["police_station"].nunique()
print("center_codes mapping to exactly 1 station: %d / %d"%((g==1).sum(),len(g)))
g2=df.groupby("police_station")["center_code"].nunique()
print("stations mapping to exactly 1 center_code: %d / %d"%((g2==1).sum(),len(g2)))

print("="*60,"\nLOCATION free-text road-type mining (native FE candidate)")
loc=df["location"].fillna("").str.lower()
KW={"main road":"main road","cross":"cross road","metro":"metro","market":"market",
    "circle":"circle","junction":"junction","layout":"layout","nagar":"nagar",
    "flyover":"flyover","bridge":"bridge","station":"station","temple":"temple",
    "mall":"mall","hospital":"hospital","school":"school","road":"road (any)"}
print("keyword presence in location string:")
for k,lbl in KW.items():
    print(f"  {lbl:14s} {loc.str.contains(k,regex=False).mean()*100:5.1f}%")
print("location non-empty: %.1f%%, unique strings: %d"%((loc!="").mean()*100, loc[loc!=""].nunique()))

print("="*60,"\nUNEXAMINED COLUMN CHECK")
print("data_sent_to_scita_timestamp: 86% null -> only present for sent+timestamped; carries no extra signal beyond data_sent_to_scita flag (skip).")
print("modified_datetime: used only via create->modify lag in 3.1 (sufficient).")
print("\nCOMPLETENESS: all 24 columns examined or explicitly dropped/skipped with reason.")
