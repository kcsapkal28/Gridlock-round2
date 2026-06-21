import pandas as pd, matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
df = pd.read_parquet("/kaggle/working/raw.parquet")
NULLTOK = df.isin(["NULL","null","",None]) | df.isna()
nullpct = (NULLTOK.mean()*100).sort_values(ascending=False)
print(nullpct.round(2).to_string())

# GUARD: known-dead columns are 100% null (from local profiling)
for c in ["description","closed_datetime","action_taken_timestamp"]:
    assert round(nullpct[c],1) == 100.0, f"{c} not fully null: {nullpct[c]}"
print("GUARD OK: dead columns 100% null")

ax = nullpct.plot.barh(figsize=(8,9)); ax.invert_yaxis()
ax.set_title("Null % by column"); ax.set_xlabel("% null")
plt.tight_layout(); plt.savefig("/kaggle/working/eda_out/10_nullmap.png", dpi=120)
print("saved 10_nullmap.png")
