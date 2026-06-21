import pandas as pd, numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
f=pd.read_parquet("/kaggle/working/cell_features_full.parquet")
PCA_FEATS=["n","sev_sum_total","tier3_share","heavy_share","commercial_share",
           "f_main_road","f_circle","f_junction","f_busstop_school_hosp",
           "lag_sev_sum","lag_tier3_share","kde_sev","heavy_x_mainroad","tier3_x_junction",
           "distinct_devices","recurrence_weeks"]
X=StandardScaler().fit_transform(f[PCA_FEATS].fillna(0).values)
p=PCA(n_components=5,random_state=42).fit(X)
scores=p.transform(X)
pc1=scores[:,0]
if np.corrcoef(pc1,f["sev_sum_total"])[0,1]<0: pc1=-pc1
evr=p.explained_variance_ratio_
if evr[0]<0.40:
    pc2=scores[:,1]
    if np.corrcoef(pc2,f["sev_sum_total"])[0,1]<0: pc2=-pc2
    composite=(evr[0]*pc1+evr[1]*pc2)/(evr[0]+evr[1])
    print("PC1 weak (<0.40) -> blended PC1+PC2")
else:
    composite=pc1
f["pca_composite"]=composite
# GUARD: composite finite, length matches
assert np.isfinite(f["pca_composite"]).all() and len(f)==len(f), "pca composite bad"
f.to_parquet("/kaggle/working/cell_features_full.parquet")
load=pd.Series(p.components_[0],index=PCA_FEATS).sort_values(key=abs,ascending=False)
print("PC1 explained var: %.3f | PC1-2: %.3f"%(evr[0],evr[:2].sum()))
print("PC1 loadings (|desc|):")
print(load.round(3).to_string())
