import os; os.makedirs("/kaggle/working/derived", exist_ok=True)
import pandas as pd, json
df = pd.read_parquet("/kaggle/working/raw.parquet")
def parse(x):
    try: return json.loads(x) if isinstance(x,str) else []
    except Exception: return None
viol = df["violation_type"].map(parse)
offc = df["offence_code"].map(parse)

# GUARD 1: every row parses (no None)
assert viol.isna().sum()==0 and offc.isna().sum()==0, "unparseable array rows exist"
# GUARD 2: parallel arrays have equal length row-wise
mismatch = (viol.map(len) != offc.map(len))
print("length-mismatch rows:", int(mismatch.sum()))
assert mismatch.sum()==0, "violation_type and offence_code lengths differ"

# Build the code<->label map and check it's 1:1
pairs = set()
for vs,os_ in zip(viol,offc):
    for v,o in zip(vs,os_): pairs.add((o,v))
code2label = {}; ambig = []
for o,v in sorted(pairs):
    if o in code2label and code2label[o]!=v: ambig.append((o,v,code2label[o]))
    code2label[o]=v
print("distinct offence codes:", len(code2label), "| ambiguous mappings:", ambig)
print("CODE->LABEL:")
for o in sorted(code2label): print(f"  {o}: {code2label[o]}")
df_arr = df[["id"]].copy(); df_arr["viol"]=viol; df_arr["offc"]=offc
df_arr["n_violations"]=viol.map(len)
df_arr.to_parquet("/kaggle/working/derived/arrays.parquet")
print("n_violations distribution:")
print(df_arr["n_violations"].value_counts().sort_index().to_string())
print("rows with >1 violation: %.2f%%" % ((df_arr["n_violations"]>1).mean()*100))
