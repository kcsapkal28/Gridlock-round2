import pandas as pd, folium, json
gj=json.load(open("/kaggle/working/fe_out/cells.geojson"))
f=pd.read_parquet("/kaggle/working/cell_scores.parquet")
# only render ranked cells (confidence) to keep the map meaningful
ranked_gh=set(f[f["ranked"]]["gh7"])
gj_r={"type":"FeatureCollection","features":[ft for ft in gj["features"] if ft["properties"]["gh7"] in ranked_gh]}
m=folium.Map(location=[12.97,77.59],zoom_start=12,tiles="cartodbpositron")
folium.Choropleth(geo_data=gj_r,data=f[f["ranked"]],columns=["gh7","impact"],
    key_on="feature.properties.gh7",fill_color="YlOrRd",fill_opacity=0.75,line_opacity=0.15,
    legend_name="Congestion-Impact Score (0-100)").add_to(m)
# markers for top-15 with decomposition popups
for _,r in f[f["ranked"]].sort_values("impact",ascending=False).head(15).iterrows():
    folium.CircleMarker([r["lat"],r["lon"]],radius=6,color="black",fill=True,fill_color="red",fill_opacity=0.9,
        popup=f"#{int(r['rank'])} {r['gh7']}: impact={r['impact']:.1f}, n={int(r['n'])}, T3={r['tier3_share']:.0%}, heavy={r['heavy_share']:.0%}").add_to(m)
m.save("/kaggle/working/fe_out/impact_map.html")
print("saved impact_map.html with %d ranked cells"%len(gj_r["features"]))
