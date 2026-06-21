import pandas as pd, numpy as np
from sklearn.cluster import DBSCAN
df=pd.read_parquet("/kaggle/working/cleaned.parquet")
sev=pd.read_parquet("/kaggle/working/derived/severity.parquet")
df=df.merge(sev[["id","max_sev","sev_sum"]],on="id",how="left")
coords=np.radians(df[["latitude","longitude"]].values)
eps=150/6371000.0  # 150m in radians (haversine)
db=DBSCAN(eps=eps,min_samples=30,metric="haversine",algorithm="ball_tree").fit(coords)
df["cluster"]=db.labels_
n_clusters=int(df["cluster"].nunique()-(1 if -1 in df["cluster"].values else 0))
noise=(df["cluster"]==-1).mean()*100
print("clusters: %d | noise: %.1f%%"%(n_clusters,noise))
agg=(df[df.cluster>=0].groupby("cluster")
     .agg(n=("id","size"),n_valid=("is_valid","sum"),
          lat=("latitude","mean"),lon=("longitude","mean"),
          tier3_share=("max_sev",lambda s:(s>=3).mean()),
          sev_sum=("sev_sum","sum"),
          top_station=("police_station",lambda s:s.mode().iat[0]))
     .sort_values("n",ascending=False))
agg.to_parquet("/kaggle/working/derived/hotspots.parquet")
print("top 20 hotspots by ticket count:")
print(agg.head(20).round(3).to_string())
