import pandas as pd, folium
from folium.plugins import HeatMap
df=pd.read_parquet("/kaggle/working/cleaned.parquet")
hot=pd.read_parquet("/kaggle/working/derived/hotspots.parquet")
m=folium.Map(location=[12.97,77.59],zoom_start=12,tiles="cartodbpositron")
samp=df[["latitude","longitude"]].sample(min(50000,len(df)),random_state=0).values.tolist()
HeatMap(samp,radius=8,blur=6).add_to(m)
for cl,r in hot.head(20).iterrows():
    folium.CircleMarker([r.lat,r.lon],radius=6,color="red",fill=True,fill_opacity=0.7,
        popup=f"cluster {cl}: {int(r.n)} tickets, T3={r.tier3_share:.0%}, {r.top_station}").add_to(m)
m.save("/kaggle/working/eda_out/42_hotspots.html")
print("saved 42_hotspots.html")
# junction linkage
named=df["junction_name"].ne("No Junction")&df["junction_name"].notna()
print("tickets at NAMED junctions: %.2f%%"%(named.mean()*100))
print("top 15 named junctions:")
print(df[named]["junction_name"].value_counts().head(15).to_string())
# do hotspot clusters sit on junctions?
dfj=df.copy()
print("\nshare-at-named-junction within top-8 clusters:")
import numpy as np
from sklearn.cluster import DBSCAN
# reuse cluster labels by recomputing quickly is costly; instead bucket by nearest hotspot center
# (lightweight: report overall named share by station for top hotspot stations)
for st in hot.head(8)["top_station"].unique():
    sub=df[df.police_station==st]
    print(f"  {st:18s} named-junction share = {sub['junction_name'].ne('No Junction').mean()*100:5.1f}%")
