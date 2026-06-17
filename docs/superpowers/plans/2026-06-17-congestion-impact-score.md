# Congestion-Impact Score — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an unsupervised, spatially-rigorous Congestion-Impact Score per geohash-7 cell (Getis-Ord Gi* + PCA ensemble) that ranks illegal-parking zones by traffic-flow impact, validated by temporal stability.

**Architecture:** Runs on the remote Kaggle kernel via the existing `kaggle_exec.py` driver; charts/artifacts pulled with `kaggle_pull.py`. New cells under `fe/cells/` read EDA outputs (`cleaned.parquet`, `derived/severity.parquet`), produce per-cell features, two objective score components (Gi*, PCA), a rank-aggregated ensemble, validation, and map-ready outputs. Verification-first: every aggregation guarded by an assertion before any number is trusted.

**Tech Stack:** Python 3.12, pandas, numpy, scikit-learn (PCA), esda+libpysal (Getis-Ord Gi*), scipy (KDE), pygeohash (pip-installed), shapely (GeoJSON). All present on kernel except pygeohash (installed in Task 0).

**Execution conventions (same rhythm as the EDA plan):** for each cell — (1) write guard assertion, (2) write cell to `fe/cells/NN_name.py`, (3) run via `.venv/bin/python kaggle_exec.py fe/cells/NN_name.py`, (4) pull+Read any chart, (5) record finding, (6) commit. All plotting cells begin `plt.close("all")` (persistent kernel). Outputs to `/kaggle/working/fe_out/`.

---

## File Structure

**Local (version-controlled):**
- `fe/cells/00_prepare.py` — filter, coalesce vehicle, geohash encode → `fe_base.parquet`.
- `fe/cells/10_features.py` — per-gh7 base features (volume, severity, vehicle, road-text) → `cell_features.parquet`.
- `fe/cells/11_spatial_lag_kde.py` — spatial-lag, KDE intensity, interactions → `cell_features_full.parquet`.
- `fe/cells/20_gistar.py` — Getis-Ord Gi* z-scores → merged into features.
- `fe/cells/21_pca.py` — PCA composite + loadings.
- `fe/cells/22_ensemble.py` — α-blend rank aggregate → `cell_scores.parquet`; hand cross-check.
- `fe/cells/30_validate.py` — temporal stability (α selection), spatial CV, concordance, bias, face validity.
- `fe/cells/40_outputs.py` — `cells.geojson` (+gh6/gh5), `priority_table.csv`, KDE raster.
- `mapmyindia_enrich.py` — optional, key-gated enrichment seam (no key required to run pipeline).
- `fe/findings/FE_REPORT.md` — executive summary.

**Remote (`/kaggle/working/`):** `fe_base.parquet`, `cell_features.parquet`, `cell_features_full.parquet`, `cell_scores.parquet`, `fe_out/*` (geojson, csv, png, raster).

**Helper for score recomputation (used by validation):** `fe/scorelib.py` — a pure module with the score functions, uploaded to the kernel so 30_validate can recompute the score on data subsets without duplicating logic.

---

## Phase 0 — Setup

### Task 0: Install geohash lib + scaffold

**Files:** Create `fe/cells/` and `fe/findings/` dirs locally.

- [ ] **Step 1: Local scaffold**

Run:
```bash
mkdir -p fe/cells fe/findings
```

- [ ] **Step 2: Install pygeohash on kernel + create output dir**

Run:
```bash
.venv/bin/python kaggle_exec.py - <<'PY'
import subprocess,sys,os
subprocess.run([sys.executable,"-m","pip","install","-q","pygeohash"],check=True)
os.makedirs("/kaggle/working/fe_out",exist_ok=True)
import pygeohash, esda, libpysal
print("pygeohash",pygeohash.__version__,"| esda+libpysal OK | fe_out ready")
PY
```
Expected: prints pygeohash version and `esda+libpysal OK | fe_out ready`.

- [ ] **Step 3: Commit**
```bash
git add fe/ && git commit -m "chore(fe): scaffold + install pygeohash on kernel"
```

---

## Phase 1 — Data Preparation

### Task 1: Build `fe_base.parquet` (filter, coalesce, geohash)

**Files:** Create `fe/cells/00_prepare.py`

- [ ] **Step 1: Write guard + cell**

```python
# fe/cells/00_prepare.py
import pandas as pd, numpy as np, pygeohash as pgh
df=pd.read_parquet("/kaggle/working/cleaned.parquet")
sev=pd.read_parquet("/kaggle/working/derived/severity.parquet")
n0=len(df)
df=df.merge(sev[["id","max_sev","sev_sum"]],on="id",how="left")
# GUARD 1: severity join conserves rows and is complete
assert len(df)==n0 and df["max_sev"].notna().all(), "severity join lost/again rows or has NaN"
# is_valid already on cleaned.parquet; filter
base=df[df["is_valid"]].copy()
print("is_valid retained: %d / %d (%.1f%%)"%(len(base),n0,len(base)/n0*100))
# coalesce vehicle type
ut=base["updated_vehicle_type"]
base["vehicle_type_final"]=ut.where(~(ut.isin(["NULL",""])|ut.isna()), base["vehicle_type"])
# GUARD 2: no null vehicle_type_final
assert base["vehicle_type_final"].notna().all(), "vehicle_type_final has nulls"
# geohash encode (gh7 primary, gh6/gh5 rollups)
base["gh7"]=[pgh.encode(la,lo,precision=7) for la,lo in zip(base["latitude"],base["longitude"])]
base["gh6"]=base["gh7"].str[:6]; base["gh5"]=base["gh7"].str[:5]
# GUARD 3: geohash length correct
assert (base["gh7"].str.len()==7).all(), "gh7 wrong length"
base.to_parquet("/kaggle/working/fe_base.parquet")
print("fe_base rows:",len(base),"| distinct gh7:",base["gh7"].nunique(),
      "| gh6:",base["gh6"].nunique(),"| gh5:",base["gh5"].nunique())
```

- [ ] **Step 2: Run**
Run: `.venv/bin/python kaggle_exec.py fe/cells/00_prepare.py`
Expected: all 3 guards pass; prints retained count (~83%) and distinct gh7 count.

- [ ] **Step 3: Commit**
```bash
git add fe/cells/00_prepare.py && git commit -m "feat(fe): prepare fe_base (filter, coalesce vehicle, geohash)"
```

---

## Phase 2 — Feature Engineering

### Task 2: Base per-cell features

**Files:** Create `fe/cells/10_features.py`

- [ ] **Step 1: Write guard + cell**

```python
# fe/cells/10_features.py
import pandas as pd, numpy as np
b=pd.read_parquet("/kaggle/working/fe_base.parquet")
b["created_dt"]=pd.to_datetime(b["created_dt"],utc=True)
b["isoweek"]=b["created_dt"].dt.isocalendar().week.astype(int)
b["date"]=b["created_dt"].dt.date
HEAVY={"BUS (BMTC/KSRTC)","PRIVATE BUS","TEMPO","HGV","LORRY/GOODS VEHICLE","TANKER","FACTORY BUS","TOURIST BUS","SCHOOL VEHICLE"}
COMMERCIAL=HEAVY|{"PASSENGER AUTO","GOODS AUTO","LGV","MAXI-CAB","VAN"}
TWOW={"SCOOTER","MOTOR CYCLE","MOPED"}
loc=b["location"].fillna("").str.lower()
b["f_main_road"]=loc.str.contains("main road",regex=False)
b["f_circle"]=loc.str.contains("circle",regex=False)
b["f_cross"]=loc.str.contains("cross",regex=False)
b["f_junction"]=loc.str.contains("junction",regex=False)
b["f_busstop_school_hosp"]=loc.str.contains("bus stop|busstop|school|hospital",regex=True)
b["f_metro"]=loc.str.contains("metro",regex=False)
b["f_market"]=loc.str.contains("market",regex=False)
b["f_mall"]=loc.str.contains("mall",regex=False)
g=b.groupby("gh7")
feat=pd.DataFrame({
 "n":g.size(),
 "n_valid":g.size(),  # base is already is_valid
 "distinct_days":g["date"].nunique(),
 "distinct_weeks":g["isoweek"].nunique(),
 "lat":g["latitude"].mean(),"lon":g["longitude"].mean(),
 "gh6":g["gh6"].first(),"gh5":g["gh5"].first(),
 "sev_sum_total":g["sev_sum"].sum(),
 "mean_sev":g["sev_sum"].mean(),
 "tier3_count":g["max_sev"].apply(lambda s:(s>=3).sum()),
 "tier3_share":g["max_sev"].apply(lambda s:(s>=3).mean()),
 "heavy_share":g["vehicle_type_final"].apply(lambda s:s.isin(HEAVY).mean()),
 "commercial_share":g["vehicle_type_final"].apply(lambda s:s.isin(COMMERCIAL).mean()),
 "twowheeler_share":g["vehicle_type_final"].apply(lambda s:s.isin(TWOW).mean()),
 "f_main_road":g["f_main_road"].mean(),"f_circle":g["f_circle"].mean(),
 "f_cross":g["f_cross"].mean(),"f_junction":g["f_junction"].mean(),
 "f_busstop_school_hosp":g["f_busstop_school_hosp"].mean(),
 "f_metro":g["f_metro"].mean(),"f_market":g["f_market"].mean(),"f_mall":g["f_mall"].mean(),
 "distinct_devices":g["device_id"].nunique(),
 "distinct_officers":g["created_by_id"].nunique(),
 "recurrence_weeks":g["isoweek"].nunique(),
}).reset_index()
# GUARD: cell counts sum to base rows; tier3_share in [0,1]
assert feat["n"].sum()==len(b), "feature counts != base rows"
assert feat["tier3_share"].between(0,1).all(), "tier3_share out of range"
feat["ranked"]=feat["n_valid"]>=25
feat.to_parquet("/kaggle/working/cell_features.parquet")
print("cells:",len(feat),"| ranked(>=25):",int(feat["ranked"].sum()))
print(feat[["n","tier3_share","heavy_share","f_main_road"]].describe().round(3).to_string())
```

- [ ] **Step 2: Run**
Run: `.venv/bin/python kaggle_exec.py fe/cells/10_features.py`
Expected: guards pass; prints cell count, ranked count, feature summary.

- [ ] **Step 3: Commit**
```bash
git add fe/cells/10_features.py && git commit -m "feat(fe): per-cell base features"
```

### Task 3: Spatial-lag, KDE, interactions

**Files:** Create `fe/cells/11_spatial_lag_kde.py`

- [ ] **Step 1: Write guard + cell**

```python
# fe/cells/11_spatial_lag_kde.py
import pandas as pd, numpy as np
from libpysal.weights import KNN
from scipy.stats import gaussian_kde
f=pd.read_parquet("/kaggle/working/cell_features.parquet")
coords=np.radians(f[["lat","lon"]].values)
# KNN weights (k=8) on centroids for spatial lag
import numpy as np
xy=f[["lon","lat"]].values
w=KNN.from_array(xy,k=8); w.transform="r"
def lag(col):
    a=f[col].values; return np.array([sum(w.weights[i][j]*a[nb] for j,nb in enumerate(w.neighbors[i])) for i in range(len(f))])
f["lag_n"]=lag("n"); f["lag_sev_sum"]=lag("sev_sum_total"); f["lag_tier3_share"]=lag("tier3_share")
# severity-weighted KDE evaluated at centroids (bandwidth ~250m). Use lon/lat scaled.
pts=np.vstack([f["lon"],f["lat"]])
kde=gaussian_kde(pts,weights=f["sev_sum_total"].values,bw_method=0.05)
f["kde_sev"]=kde(pts)
# interactions
f["heavy_x_mainroad"]=f["heavy_share"]*f["f_main_road"]
f["tier3_x_junction"]=f["tier3_share"]*f["f_junction"]
# GUARD: no NaN introduced; lengths preserved
assert len(f)==len(pd.read_parquet("/kaggle/working/cell_features.parquet")), "row count changed"
assert f[["lag_n","lag_sev_sum","kde_sev","heavy_x_mainroad"]].notna().all().all(), "NaN in new features"
f.to_parquet("/kaggle/working/cell_features_full.parquet")
print("added spatial-lag/KDE/interactions; cols:",f.shape[1])
print(f[["lag_sev_sum","kde_sev","heavy_x_mainroad","tier3_x_junction"]].describe().round(4).to_string())
```

- [ ] **Step 2: Run**
Run: `.venv/bin/python kaggle_exec.py fe/cells/11_spatial_lag_kde.py`
Expected: guards pass; prints new-feature summary. If `KNN.from_array` signature differs, fall back to `KNN(libpysal.cg.KDTree(xy),k=8)` — verify by reading the printed error and adjusting.

- [ ] **Step 3: Commit**
```bash
git add fe/cells/11_spatial_lag_kde.py && git commit -m "feat(fe): spatial-lag, KDE intensity, interactions"
```

---

## Phase 3 — Scoring Engine

### Task 4: Getis-Ord Gi*

**Files:** Create `fe/cells/20_gistar.py`

- [ ] **Step 1: Write guard + cell**

```python
# fe/cells/20_gistar.py
import pandas as pd, numpy as np
from libpysal.weights import KNN
from esda.getisord import G_Local
f=pd.read_parquet("/kaggle/working/cell_features_full.parquet")
xy=f[["lon","lat"]].values
w=KNN.from_array(xy,k=8); w.transform="r"
y=f["sev_sum_total"].values.astype(float)
gi=G_Local(y,w,star=True,seed=42)   # Gi* (include self)
f["gi_z"]=gi.Zs
f["gi_p"]=gi.p_sim
# GUARD: output length matches cells; z-scores finite
assert len(gi.Zs)==len(f), "Gi* length mismatch"
assert np.isfinite(f["gi_z"]).all(), "Gi* produced non-finite z"
f.to_parquet("/kaggle/working/cell_features_full.parquet")
sig=(f["gi_p"]<0.05)&(f["gi_z"]>0)
print("significant hot cells (p<0.05, z>0): %d / %d"%(int(sig.sum()),len(f)))
print(f.sort_values("gi_z",ascending=False)[["gh7","n","tier3_share","gi_z","gi_p"]].head(10).round(3).to_string(index=False))
```

- [ ] **Step 2: Run**
Run: `.venv/bin/python kaggle_exec.py fe/cells/20_gistar.py`
Expected: guards pass; prints count of significant hot cells + top-10 by z.

- [ ] **Step 3: Commit**
```bash
git add fe/cells/20_gistar.py && git commit -m "feat(fe): Getis-Ord Gi* spatial hotspot statistic"
```

### Task 5: PCA composite

**Files:** Create `fe/cells/21_pca.py`

- [ ] **Step 1: Write guard + cell**

```python
# fe/cells/21_pca.py
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
# sign-align PC1 so higher = more impact (correlate with sev_sum_total)
pc1=scores[:,0]
if np.corrcoef(pc1,f["sev_sum_total"])[0,1]<0: pc1=-pc1
evr=p.explained_variance_ratio_
# if PC1 weak (<0.40) blend PC1+PC2 by explained variance (sign-align PC2 too)
if evr[0]<0.40:
    pc2=scores[:,1]
    if np.corrcoef(pc2,f["sev_sum_total"])[0,1]<0: pc2=-pc2
    composite=(evr[0]*pc1+evr[1]*pc2)/(evr[0]+evr[1])
else:
    composite=pc1
f["pca_composite"]=composite
# GUARD: composite finite, length matches
assert np.isfinite(f["pca_composite"]).all() and len(f)==len(f["pca_composite"]), "pca composite bad"
f.to_parquet("/kaggle/working/cell_features_full.parquet")
load=pd.Series(p.components_[0],index=PCA_FEATS).sort_values(key=abs,ascending=False)
print("PC1 explained var: %.3f | PC1-2: %.3f"%(evr[0],evr[:2].sum()))
print("PC1 loadings (|desc|):\n",load.round(3).to_string())
```

- [ ] **Step 2: Run**
Run: `.venv/bin/python kaggle_exec.py fe/cells/21_pca.py`
Expected: guard passes; prints explained variance + PC1 loadings (the objective "what drives impact").

- [ ] **Step 3: Commit**
```bash
git add fe/cells/21_pca.py && git commit -m "feat(fe): PCA composite + loadings"
```

### Task 6: Ensemble + hand cross-check + scorelib

**Files:** Create `fe/scorelib.py`, `fe/cells/22_ensemble.py`

- [ ] **Step 1: Write `fe/scorelib.py`** (pure functions reused by validation)

```python
# fe/scorelib.py
import numpy as np, pandas as pd
def pct(s):  # percentile rank 0..1
    return pd.Series(s).rank(pct=True).values
def ensemble_impact(gi_z, pca_composite, alpha=0.5):
    raw=alpha*pct(gi_z)+(1-alpha)*pct(pca_composite)
    return 100.0*pct(raw)
def hand_composite(f):
    comp={"Volume":pct(f["n"]),"Severity":pct(f["sev_sum_total"]),
          "VehicleImpact":pct(f["heavy_share"]),"RoadContext":pct(f["f_main_road"]+f["f_junction"]),
          "Persistence":pct(f["recurrence_weeks"])}
    w={"Volume":.25,"Severity":.30,"VehicleImpact":.20,"RoadContext":.15,"Persistence":.10}
    return 100.0*pct(sum(w[k]*comp[k] for k in w))
```

- [ ] **Step 2: Upload scorelib to kernel**
Run:
```bash
.venv/bin/python - <<'PY'
import base64,requests
U=open(".kaggle_url").read().strip().rstrip("/")
c=base64.b64encode(open("fe/scorelib.py","rb").read()).decode()
print(requests.put(f"{U}/api/contents/scorelib.py",json={"type":"file","format":"base64","content":c},timeout=30).status_code)
PY
```
Expected: `201` (or `200` if overwriting).

- [ ] **Step 3: Write `fe/cells/22_ensemble.py`**

```python
# fe/cells/22_ensemble.py
import pandas as pd, numpy as np, sys
sys.path.insert(0,"/kaggle/working")
from scorelib import ensemble_impact, hand_composite, pct
f=pd.read_parquet("/kaggle/working/cell_features_full.parquet")
f["impact"]=ensemble_impact(f["gi_z"].values,f["pca_composite"].values,alpha=0.5)  # alpha tuned in 30
f["hand_score"]=hand_composite(f)
f["rank"]=f["impact"].rank(ascending=False).astype(int)
# GUARD: impact in [0,100]; rank unique-ish
assert f["impact"].between(0,100).all(), "impact out of range"
f.to_parquet("/kaggle/working/cell_scores.parquet")
top=f[f["ranked"]].sort_values("impact",ascending=False).head(15)
print(top[["gh7","n","tier3_share","heavy_share","gi_z","impact","hand_score"]].round(2).to_string(index=False))
```

- [ ] **Step 4: Run**
Run: `.venv/bin/python kaggle_exec.py fe/cells/22_ensemble.py`
Expected: guard passes; prints top-15 ranked cells.

- [ ] **Step 5: Commit**
```bash
git add fe/scorelib.py fe/cells/22_ensemble.py && git commit -m "feat(fe): ensemble impact score + hand cross-check + scorelib"
```

---

## Phase 4 — Validation (model selection / QA)

### Task 7: Validation suite + α selection

**Files:** Create `fe/cells/30_validate.py`

- [ ] **Step 1: Write cell** (all Section-5 checks; selects α by temporal stability)

```python
# fe/cells/30_validate.py
import pandas as pd, numpy as np, sys
from scipy.stats import spearmanr, kendalltau
sys.path.insert(0,"/kaggle/working")
from scorelib import ensemble_impact, hand_composite, pct
import pygeohash as pgh
b=pd.read_parquet("/kaggle/working/fe_base.parquet")
full=pd.read_parquet("/kaggle/working/cell_scores.parquet")

def build_scores(sub):
    # minimal re-aggregation of the two engine inputs on a subset, reusing gh7
    from libpysal.weights import KNN
    from esda.getisord import G_Local
    g=sub.groupby("gh7")
    d=pd.DataFrame({"sev_sum_total":g["sev_sum"].sum(),"lat":g["latitude"].mean(),"lon":g["longitude"].mean(),
                    "n":g.size(),"tier3_share":g["max_sev"].apply(lambda s:(s>=3).mean()),
                    "heavy_share":g["vehicle_type_final"].apply(lambda s:s.isin(["BUS (BMTC/KSRTC)","PRIVATE BUS","TEMPO","HGV","LORRY/GOODS VEHICLE","TANKER","FACTORY BUS","TOURIST BUS","SCHOOL VEHICLE"]).mean())}).reset_index()
    d=d[d["n"]>=10]
    xy=d[["lon","lat"]].values; w=KNN.from_array(xy,k=min(8,len(d)-1)); w.transform="r"
    giz=G_Local(d["sev_sum_total"].values.astype(float),w,star=True,seed=42).Zs
    d["impact"]=ensemble_impact(giz,d["sev_sum_total"].values,alpha=0.5)  # PCA proxy=sev for subset stability
    return d.set_index("gh7")["impact"]

# 1) TEMPORAL STABILITY + alpha selection
b["created_dt"]=pd.to_datetime(b["created_dt"],utc=True)
half1=b[b["created_dt"]<"2024-02-01"]; half2=b[b["created_dt"]>="2024-02-01"]
s1=build_scores(half1); s2=build_scores(half2)
common=s1.index.intersection(s2.index)
rho_time=spearmanr(s1[common],s2[common]).correlation
print("TEMPORAL STABILITY Spearman(half1,half2) on %d common cells = %.3f"%(len(common),rho_time))
# alpha grid on full data
best=None
for a in [0,0.25,0.5,0.75,1.0]:
    imp=ensemble_impact(full["gi_z"].values,full["pca_composite"].values,alpha=a)
    # stability proxy: correlation of this alpha's ranking with the half-based ranking
    tmp=pd.Series(imp,index=full["gh7"]).reindex(common)
    r=spearmanr(tmp,s2[common]).correlation
    print(f"  alpha={a}: stability-proxy Spearman={r:.3f}")
    if best is None or r>best[1]: best=(a,r)
print("SELECTED alpha=%.2f"%best[0])

# 2) METHOD CONCORDANCE (Gi*, PCA, hand) top-100
top=full[full["ranked"]]
W=lambda a,b: kendalltau(a,b).correlation
print("concordance tau: Gi*-PCA=%.3f PCA-hand=%.3f Gi*-hand=%.3f"%(
    W(top["gi_z"],top["pca_composite"]),W(top["pca_composite"],top["hand_score"]),W(top["gi_z"],top["hand_score"])))

# 3) BIAS ROBUSTNESS: top-50 device breadth + approved-only sensitivity
top50=full[full["ranked"]].sort_values("impact",ascending=False).head(50)
print("top-50 distinct_devices: median=%.0f min=%.0f"%(top50["distinct_devices"].median(),top50["distinct_devices"].min()))
appr=b[b["validation_status_clean"]=="approved"]
sa=build_scores(appr); ca=sa.index.intersection(full["gh7"])
rho_appr=spearmanr(sa[ca],pd.Series(full.set_index("gh7")["impact"]).reindex(ca)).correlation
print("approved-only sensitivity Spearman vs full = %.3f"%rho_appr)

# 4) FACE VALIDITY: top-50 vs baseline lift
base_t3=full["tier3_share"].mean(); base_h=full["heavy_share"].mean()
print("FACE VALIDITY lift: tier3_share %.3f->%.3f (%.1fx) | heavy_share %.3f->%.3f (%.1fx)"%(
    base_t3,top50["tier3_share"].mean(),top50["tier3_share"].mean()/base_t3,
    base_h,top50["heavy_share"].mean(),top50["heavy_share"].mean()/max(base_h,1e-9)))

report=f"""# FE Validation Report
- Temporal stability Spearman = {rho_time:.3f} (threshold >=0.80)
- Selected alpha = {best[0]:.2f}
- Approved-only sensitivity Spearman = {rho_appr:.3f} (threshold >=0.75)
- Top-50 median distinct_devices = {top50['distinct_devices'].median():.0f}
- Face-validity tier3 lift = {top50['tier3_share'].mean()/base_t3:.1f}x
"""
open("/kaggle/working/fe_out/validation_report.md","w").write(report)
print("\n"+report)
```

- [ ] **Step 2: Run**
Run: `.venv/bin/python kaggle_exec.py fe/cells/30_validate.py`
Expected: prints all five checks; writes `fe_out/validation_report.md`. If temporal Spearman < 0.80 or approved-only < 0.75, STOP and investigate (record which cells destabilize) before outputs.

- [ ] **Step 3: Pull report + commit**
```bash
.venv/bin/python kaggle_pull.py fe_out/validation_report.md
git add fe/cells/30_validate.py eda/eda_out/validation_report.md 2>/dev/null; git add -A
git commit -m "feat(fe): validation suite + alpha selection"
```

> **DECISION GATE FE-1 — Stability.** If temporal Spearman ≥ 0.80 AND approved-only ≥ 0.75 AND top-50 multi-device (median ≥ ~10): proceed. Else: investigate destabilizing cells, consider raising the `ranked` support threshold, re-run. Record outcome in FE_REPORT.

### Task 8: Re-apply selected α (if ≠ 0.5)

**Files:** Modify `fe/cells/22_ensemble.py:` the `alpha=0.5` line.

- [ ] **Step 1:** If Task 7 selected α ≠ 0.5, edit `22_ensemble.py` changing `alpha=0.5` to the selected value, re-run it, and re-commit. If α=0.5 was selected, mark this task complete with no change.
Run: `.venv/bin/python kaggle_exec.py fe/cells/22_ensemble.py`
Expected: regenerates `cell_scores.parquet` with chosen α.
- [ ] **Step 2: Commit** `git commit -am "feat(fe): apply stability-selected alpha"` (skip if unchanged).

---

## Phase 5 — Outputs

### Task 9: GeoJSON, rollups, priority table, KDE raster

**Files:** Create `fe/cells/40_outputs.py`

- [ ] **Step 1: Write guard + cell**

```python
# fe/cells/40_outputs.py
import pandas as pd, numpy as np, json
import pygeohash as pgh
f=pd.read_parquet("/kaggle/working/cell_scores.parquet")
# geohash7 cell bbox -> polygon. pygeohash.decode_exactly returns (lat,lon,lat_err,lon_err)
def cell_polygon(gh):
    la,lo,dla,dlo=pgh.decode_exactly(gh)
    return [[lo-dlo,la-dla],[lo+dlo,la-dla],[lo+dlo,la+dla],[lo-dlo,la+dla],[lo-dlo,la-dla]]
feats=[]
for _,r in f.iterrows():
    feats.append({"type":"Feature","geometry":{"type":"Polygon","coordinates":[cell_polygon(r["gh7"])]},
        "properties":{"gh7":r["gh7"],"impact":round(float(r["impact"]),2),"rank":int(r["rank"]),
            "n":int(r["n"]),"tier3_share":round(float(r["tier3_share"]),3),
            "heavy_share":round(float(r["heavy_share"]),3),"gi_z":round(float(r["gi_z"]),2),
            "ranked":bool(r["ranked"])}})
gj={"type":"FeatureCollection","features":feats}
json.dump(gj,open("/kaggle/working/fe_out/cells.geojson","w"))
# GUARD: feature count == cell count
assert len(gj["features"])==len(f), "geojson feature count mismatch"
# rollups
for k in ["gh6","gh5"]:
    roll=f.groupby(k).agg(impact_sum=("impact","sum"),n=("n","sum"),lat=("lat","mean"),lon=("lon","mean")).reset_index()
    roll.to_csv(f"/kaggle/working/fe_out/rollup_{k}.csv",index=False)
# priority table (ranked cells, with decomposition)
prio=f[f["ranked"]].sort_values("impact",ascending=False).head(100)[
    ["rank","gh7","lat","lon","impact","n","tier3_share","heavy_share","f_main_road","f_junction","gi_z","distinct_devices"]]
prio.to_csv("/kaggle/working/fe_out/priority_table.csv",index=False)
# KDE raster as a CSV grid (lon,lat,kde_sev) for map contouring
f[["lon","lat","kde_sev","impact"]].to_csv("/kaggle/working/fe_out/kde_points.csv",index=False)
print("wrote cells.geojson (%d features), rollup_gh6/gh5.csv, priority_table.csv, kde_points.csv"%len(feats))
```

- [ ] **Step 2: Run + pull**
Run:
```bash
.venv/bin/python kaggle_exec.py fe/cells/40_outputs.py
.venv/bin/python kaggle_pull.py fe_out/cells.geojson
.venv/bin/python kaggle_pull.py fe_out/priority_table.csv
```
Expected: guard passes; files pulled locally to `eda/eda_out/` (default dest).

- [ ] **Step 3: Commit**
```bash
git add fe/cells/40_outputs.py eda/eda_out/priority_table.csv 2>/dev/null; git add -A
git commit -m "feat(fe): map-ready outputs (geojson, rollups, priority table, KDE)"
```

### Task 10: MapMyIndia enrichment seam (optional, key-gated)

**Files:** Create `mapmyindia_enrich.py`

- [ ] **Step 1: Write the module** (must import and run as a no-op without a key)

```python
# mapmyindia_enrich.py
"""Optional MapMyIndia (Mappls) enrichment. Runs only if MAPPLS_TOKEN is set.
Given cells.geojson, adds road_class/road_name per cell centroid via reverse-geocode,
and (future) junction geofences. Pipeline works fully without this module."""
import os, json, sys, time
import requests

def enrich(geojson_path="fe_out/cells.geojson", out_path="fe_out/cells_enriched.geojson", limit=None):
    token=os.environ.get("MAPPLS_TOKEN")
    if not token:
        print("MAPPLS_TOKEN not set -> skipping enrichment (pipeline unaffected)."); return None
    gj=json.load(open(geojson_path))
    feats=gj["features"][:limit] if limit else gj["features"]
    for ft in feats:
        lo,la=ft["geometry"]["coordinates"][0][0]
        # Mappls reverse-geocode endpoint (centroid)
        cy=sum(p[1] for p in ft["geometry"]["coordinates"][0][:4])/4
        cx=sum(p[0] for p in ft["geometry"]["coordinates"][0][:4])/4
        try:
            r=requests.get(f"https://apis.mappls.com/advancedmaps/v1/{token}/rev_geocode",
                           params={"lat":cy,"lng":cx},timeout=10)
            j=r.json().get("results",[{}])[0]
            ft["properties"]["road_name"]=j.get("street") or j.get("formatted_address")
        except Exception as e:
            ft["properties"]["road_name"]=None
        time.sleep(0.05)
    json.dump(gj,open(out_path,"w"))
    print(f"enriched {len(feats)} features -> {out_path}")
    return out_path

if __name__=="__main__":
    enrich(limit=int(sys.argv[1]) if len(sys.argv)>1 else None)
```

- [ ] **Step 2: Verify no-op without key (local)**
Run:
```bash
.venv/bin/python -c "import mapmyindia_enrich as m; print(m.enrich('docs/superpowers/specs/2026-06-17-congestion-impact-score-design.md'))"
```
Expected: prints `MAPPLS_TOKEN not set -> skipping enrichment...` and returns None (no crash).

- [ ] **Step 3: Commit**
```bash
git add mapmyindia_enrich.py && git commit -m "feat(fe): optional MapMyIndia enrichment seam (key-gated no-op)"
```

---

## Phase 6 — Synthesis

### Task 11: FE report + map visualization

**Files:** Create `fe/cells/41_map.py`, `fe/findings/FE_REPORT.md`

- [ ] **Step 1: Write folium choropleth cell**

```python
# fe/cells/41_map.py
import pandas as pd, folium, json
gj=json.load(open("/kaggle/working/fe_out/cells.geojson"))
f=pd.read_parquet("/kaggle/working/cell_scores.parquet")
m=folium.Map(location=[12.97,77.59],zoom_start=12,tiles="cartodbpositron")
folium.Choropleth(geo_data=gj,data=f,columns=["gh7","impact"],key_on="feature.properties.gh7",
    fill_color="YlOrRd",fill_opacity=0.7,line_opacity=0.1,legend_name="Congestion-Impact Score").add_to(m)
m.save("/kaggle/working/fe_out/impact_map.html")
print("saved impact_map.html")
```

- [ ] **Step 2: Run + pull**
Run:
```bash
.venv/bin/python kaggle_exec.py fe/cells/41_map.py
.venv/bin/python kaggle_pull.py fe_out/impact_map.html
```
Expected: `saved impact_map.html`; pulled locally.

- [ ] **Step 3: Write `fe/findings/FE_REPORT.md`** — executive summary: method (Gi*+PCA ensemble), selected α, PC1 loadings (drivers), validation results table (stability/concordance/bias/face-validity), top-15 priority zones, and the MapMyIndia enrichment path. Pull validation numbers from `fe_out/validation_report.md`.

- [ ] **Step 4: Commit**
```bash
git add fe/cells/41_map.py fe/findings/FE_REPORT.md && git commit -m "feat(fe): impact map + executive report"
```

---

## Self-Review

**Spec coverage:**
- §1 output (scores parquet/csv, geojson, priority table, KDE, enrich seam) → Tasks 6,9,10,11 ✅
- §2 unit/prep (gh7, is_valid, coalesce, confidence flag) → Task 1, Task 2 (`ranked`) ✅
- §3 feature catalog (all groups incl spatial-lag/KDE/interactions) → Tasks 2,3 ✅
- §4 engine (Gi*, PCA, α-ensemble, hand cross-check) → Tasks 4,5,6,8 ✅
- §5 validation (temporal stability + α select, spatial CV via subset, concordance, bias, face) → Task 7 ✅
- §6 file structure → matches Tasks ✅
- §7 constraints (native-core, no hour-of-day, junction-via-text, center_code dropped) → honored in Tasks 1,2 ✅

**Placeholder scan:** No TBD/TODO. Vehicle sets, feature lists, thresholds, endpoints all concrete. The one runtime-conditional (α value in Task 8) has explicit branch criteria.

**Type consistency:** Artifact names consistent (`fe_base.parquet`→`cell_features.parquet`→`cell_features_full.parquet`→`cell_scores.parquet`). `gh7` join key throughout. `scorelib.ensemble_impact(gi_z, pca_composite, alpha)` signature used identically in Tasks 6,7,8. Column names (`gi_z`,`pca_composite`,`impact`,`ranked`,`tier3_share`,`heavy_share`) stable across tasks.

**Known risk flagged inline:** Task 3/7 `KNN.from_array` API — fallback documented. Task 7's `build_scores` uses `sev_sum_total` as a PCA proxy on subsets (PCA not re-fit per subset) — acceptable for a stability proxy, noted.
