import pandas as pd, numpy as np, matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
plt.close("all")   # guard: persistent kernel retains figure state across cells
df=pd.read_parquet("/kaggle/working/cleaned.parquet")
def gini(counts):
    x=np.sort(np.asarray(counts,float)); n=len(x); cum=np.cumsum(x)
    return (n+1-2*np.sum(cum)/cum[-1])/n
for col in ["device_id","created_by_id","police_station"]:
    c=df[col].value_counts()
    share_top10=c.head(max(1,int(len(c)*0.1))).sum()/c.sum()
    print(f"{col}: {len(c)} unique | top-10% make {share_top10*100:.1f}% of tickets | Gini={gini(c.values):.3f}")
fig,ax=plt.subplots(figsize=(11,4))
top=df["device_id"].value_counts().head(30)
ax.bar(range(len(top)), top.values)
ax.set_xticks(range(len(top))); ax.set_xticklabels(top.index, rotation=90, fontsize=7)
ax.set_ylabel("tickets"); ax.set_xlabel("device_id")
ax.set_title("Tickets per device (top 30 of %d)"%df['device_id'].nunique())
plt.tight_layout()
plt.savefig("/kaggle/working/eda_out/14_device_concentration.png",dpi=120)
print("saved 14_device_concentration.png")
# how many devices/officers produce 80% of tickets?
for col in ["device_id","created_by_id"]:
    c=df[col].value_counts().sort_values(ascending=False)
    k=(c.cumsum()<=0.8*c.sum()).sum()+1
    print(f"{col}: {k} of {len(c)} ({k/len(c)*100:.1f}%) produce 80% of tickets")
