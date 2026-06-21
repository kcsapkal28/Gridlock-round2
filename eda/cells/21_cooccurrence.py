import pandas as pd, numpy as np, json, itertools, matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt, seaborn as sns
plt.close("all")
df=pd.read_parquet("/kaggle/working/cleaned.parquet")
viol=df["violation_type"].map(lambda x: json.loads(x) if isinstance(x,str) else [])
labels=sorted({v for vs in viol for v in vs})
idx={l:i for i,l in enumerate(labels)}
M=np.zeros((len(labels),len(labels)),int)
for vs in viol:
    for a,b in itertools.combinations(set(vs),2):
        M[idx[a],idx[b]]+=1; M[idx[b],idx[a]]+=1
top=pd.Series([v for vs in viol for v in vs]).value_counts().head(12).index.tolist()
sub=[idx[t] for t in top]
plt.figure(figsize=(12,10))
sns.heatmap(pd.DataFrame(M[np.ix_(sub,sub)],index=top,columns=top),annot=True,fmt="d",cmap="rocket_r")
plt.title("Violation co-occurrence (top 12, same ticket)"); plt.tight_layout()
plt.savefig("/kaggle/working/eda_out/21_cooccurrence.png",dpi=110)
print("saved 21_cooccurrence.png")
# strongest pairs
pairs=[]
for a,b in itertools.combinations(top,2):
    pairs.append((M[idx[a],idx[b]],a,b))
print("top co-occurring pairs:")
for c,a,b in sorted(pairs,reverse=True)[:8]: print(f"  {c:6d}  {a}  +  {b}")
