# Targeted-Enforcement Features (A+B+C) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Patrol Route Optimizer (A), Enforcement What-If Simulator (B), and Under-Enforced Blind-Spot Finder (C) to the BTP console — completing the "reactive→targeted, systematic, proactive" arc.

**Architecture:** A = new FastAPI endpoint (`/triage/patrol-plan`) that clusters top-K zones into N units, orders each via MapMyIndia Distance Matrix, and draws routes via Routing (all cached + fallbacks). B = client-only React panel over data already served. C = offline scorer (`53_blindspots.py`) writing `blindspots.geojson` into the static bundle + a map layer. A BTP sidebar mode-switcher (Hotspots · Patrol Plan · What-If · Blind Spots) swaps panels + Deck.gl layers.

**Tech Stack:** FastAPI/Pydantic v2, httpx, scikit-learn (KMeans), lightgbm (load shipped intrinsic booster), React/Deck.gl, pytest. All MapMyIndia usage = Distance Matrix + Routing (mapping-infra, ADR-007).

**Conventions:** TDD; tests mock MapMyIndia (zero live calls). Backend tests: `.venv/bin/python -m pytest api/tests -q`. Frontend check: `npm --prefix web run build`. Verify UI with the preview tool (screenshots) after each frontend mode. Commit per task.

---

## File Structure
- Create: `api/patrol.py` (cluster→order→assemble), `api/tests/test_patrol.py`, `fe/cells/53_blindspots.py`.
- Modify: `api/mappls.py` (+`distance_matrix_many`), `api/schemas.py` (+patrol models), `api/main.py` (+route), `api/artifacts.py` (+copy blindspots), `api/config.py` (+thresholds).
- Frontend create: `web/src/components/panels/{HotspotsPanel,PatrolPanel,WhatIfPanel,BlindSpotsPanel}.jsx`.
- Frontend modify: `web/src/components/BTPSidebar.jsx` (mode switcher), `web/src/components/MapView.jsx` (mode-driven layers), `web/src/api.js` (+patrolPlan, +blindspots), `web/src/App.jsx` (btpMode state).

---

## Phase A — Patrol Route Optimizer (backend)

### Task A1: `distance_matrix_many` on MapplsClient

**Files:** Modify `api/mappls.py`; Test `api/tests/test_patrol.py` (created here).

- [ ] **Step 1: Write failing test**
```python
# api/tests/test_patrol.py
from api.mappls import MapplsClient
def test_dmm_fallback_haversine(tmp_path):
    c=MapplsClient(cache_dir=str(tmp_path), key="K", fetcher=lambda a,b:{})
    # force live path to fail -> haversine fallback matrix is square, zero diagonal
    c.open_until=0
    m=c.distance_matrix_many([(12.97,77.59),(12.98,77.60)], _fail=True)
    assert len(m)==2 and len(m[0])==2 and m[0][0]==0 and m[0][1]>0
```

- [ ] **Step 2: Run red** — `.venv/bin/python -m pytest api/tests/test_patrol.py::test_dmm_fallback_haversine -q` → FAIL.

- [ ] **Step 3: Implement** (append to `api/mappls.py`, inside `MapplsClient`):
```python
    def distance_matrix_many(self, coords, _fail=False):
        """Durations matrix (seconds) for coords=[(lat,lng)...] via Distance Matrix.
        Fallback = haversine-time matrix (assume 20 km/h). _fail forces fallback (tests)."""
        from api.geo import haversine_km
        def hav():
            out=[]
            for a in coords:
                row=[haversine_km(a[0],a[1],b[0],b[1])/20.0*3600.0 for b in coords]
                out.append(row)
            return out
        ck="dm_"+"_".join(f"{a:.4f},{b:.4f}" for a,b in coords)
        cf=__import__("os").path.join(self.cache, ck+".json")
        if __import__("os").path.exists(cf):
            return __import__("json").load(open(cf))
        if _fail or self.clock()<self.open_until:
            return hav()
        try:
            import httpx
            cstr=";".join(f"{b},{a}" for a,b in coords)
            r=httpx.get(f"https://apis.mappls.com/advancedmaps/v1/{self.key}/distance_matrix/driving/{cstr}",
                        timeout=8); r.raise_for_status()
            m=r.json()["results"]["durations"]; self.fails=0
            __import__("json").dump(m, open(cf,"w")); return m
        except Exception:
            self.fails+=1
            if self.fails>=self.bf: self.open_until=self.clock()+self.cd
            return hav()
```

- [ ] **Step 4: Run green** → PASS.
- [ ] **Step 5: Commit** — `git add api/mappls.py api/tests/test_patrol.py && git commit -m "feat(api): Mappls distance_matrix_many (+haversine fallback)"`

### Task A2: patrol plan assembly (`api/patrol.py`)

**Files:** Create `api/patrol.py`; Test extends `api/tests/test_patrol.py`.

- [ ] **Step 1: Write failing test**
```python
# add to api/tests/test_patrol.py
import pandas as pd
from api.patrol import build_plan
class FakeM:
    def distance_matrix_many(self, coords): 
        import math; return [[math.dist(a,b) for b in coords] for a in coords]
    def route(self, coords): return {"geometry":[[c[1],c[0]] for c in coords],"duration_s":300,"distance_m":900,"source":"live"}
def _df(n=9):
    import numpy as np
    return pd.DataFrame({"gh7":[f"z{i}" for i in range(n)],"lat":12.96+np.linspace(0,.06,n),
        "lon":77.58+np.linspace(0,.06,n),"impact":np.linspace(99,80,n),"rank":range(1,n+1),
        "ranked":[True]*n})
def test_build_plan_units():
    plan=build_plan(_df(9), FakeM(), units=3, topk=9)
    assert len(plan["units"])==3
    assert sum(u["n_zones"] for u in plan["units"])==9
    for u in plan["units"]:
        assert u["route_geometry"] and u["drive_time_min"]>=0 and len(u["stops"])>=1
```

- [ ] **Step 2: Run red** → FAIL.

- [ ] **Step 3: Implement `api/patrol.py`**
```python
import numpy as np
from sklearn.cluster import KMeans
COLORS=["#ffb23e","#36d6c3","#f0463c","#7aa2ff"]
def _order(idxs, dm):
    """Greedy nearest-neighbour order over a sublist of indices given full duration matrix dm."""
    if len(idxs)<=2: return list(idxs)
    remaining=list(idxs); path=[remaining.pop(0)]
    while remaining:
        last=path[-1]
        nxt=min(remaining, key=lambda j: dm[last][j]); path.append(nxt); remaining.remove(nxt)
    return path
def build_plan(df, mappls, units=3, topk=15):
    top=df[df["ranked"]].sort_values("impact",ascending=False).head(topk).reset_index(drop=True)
    units=max(1,min(units,len(top)))
    km=KMeans(n_clusters=units, n_init=10, random_state=42).fit(top[["lat","lon"]].values)
    out=[]
    for u in range(units):
        members=[i for i in range(len(top)) if km.labels_[i]==u]
        if not members: continue
        coords=[(top.lat[i],top.lon[i]) for i in members]
        dm=mappls.distance_matrix_many(coords)
        order_local=_order(list(range(len(members))), dm)
        ordered=[members[k] for k in order_local]
        rc=[(top.lat[i],top.lon[i]) for i in ordered]
        rt=mappls.route(rc) if len(rc)>=2 else {"geometry":[[top.lon[ordered[0]],top.lat[ordered[0]]]],"duration_s":0}
        out.append({"unit_id":u+1,"color":COLORS[u%len(COLORS)],
            "stops":[{"gh7":top.gh7[i],"lat":float(top.lat[i]),"lon":float(top.lon[i]),
                      "impact":round(float(top.impact[i]),1),"rank":int(top["rank"][i])} for i in ordered],
            "route_geometry":rt.get("geometry",[]),
            "drive_time_min":round((rt.get("duration_s") or 0)/60.0,1),
            "total_impact":round(float(sum(top.impact[i] for i in ordered)),1),
            "n_zones":len(ordered)})
    return {"units":out,"topk":int(topk),"generated_for":{"units":units,"topk":int(topk)}}
```

- [ ] **Step 4: Run green** → PASS.
- [ ] **Step 5: Commit** — `git add api/patrol.py api/tests/test_patrol.py && git commit -m "feat(api): patrol plan (kmeans clusters + NN order + routes)"`

### Task A3: `/triage/patrol-plan` endpoint

**Files:** Modify `api/schemas.py`, `api/main.py`; Test extends `api/tests/test_patrol.py`.

- [ ] **Step 1: Write failing test**
```python
# add to api/tests/test_patrol.py
from fastapi.testclient import TestClient
from api.main import create_app
def test_patrol_endpoint(mini_scores):
    c=TestClient(create_app(scores_parquet=mini_scores))
    r=c.get("/api/v1/triage/patrol-plan?units=2&topk=6")
    assert r.status_code==200
    j=r.json(); assert len(j["units"])<=2 and j["topk"]==6
```

- [ ] **Step 2: Run red** → FAIL (404).

- [ ] **Step 3: Implement** — in `api/main.py`, add import `from api.patrol import build_plan` and the route inside `create_app` (near other triage routes):
```python
    @app.get("/api/v1/triage/patrol-plan")
    def patrol_plan(units: int = 3, topk: int = 15):
        return build_plan(svc.df, mappls, units=units, topk=topk)
```

- [ ] **Step 4: Run green** — `.venv/bin/python -m pytest api/tests/test_patrol.py -q` → PASS.
- [ ] **Step 5: Commit** — `git add api/main.py api/tests/test_patrol.py && git commit -m "feat(api): /triage/patrol-plan endpoint"`

---

## Phase C — Blind-Spot Finder (offline + bundle)

### Task C1: `fe/cells/53_blindspots.py`

**Files:** Create `fe/cells/53_blindspots.py`; Modify `api/config.py` (thresholds doc only — optional).

- [ ] **Step 1: Write the cell**
```python
# fe/cells/53_blindspots.py
import pandas as pd, numpy as np, json, os, lightgbm as lgb
f=pd.read_parquet("/kaggle/working/cell_scores.parquet")
INTR=["n","sev_sum_total","impact_intensity_total","mean_sev","tier3_count","tier3_share",
      "tier3_share_eb","heavy_share","heavy_share_eb","commercial_share","twowheeler_share",
      "f_main_road","f_circle","f_cross","f_junction","f_busstop_school_hosp","f_metro","f_market","f_mall",
      "distinct_days","distinct_weeks","distinct_devices","distinct_officers","recurrence_weeks"]
INTR=[c for c in INTR if c in f.columns]
m=lgb.Booster(model_file="/kaggle/working/fe_out/model_impact.txt")
# align to the model's training features
feat=[c for c in m.feature_name() if c in f.columns]
f["pred_impact"]=m.predict(f[feat])
f["pred_pct"]=f["pred_impact"].rank(pct=True)
f["cov_pct"]=f["n"].rank(pct=True)
f["blind_gap"]=f["pred_pct"]-f["cov_pct"]
bs=f[(f["pred_pct"]>=0.80)&(f["cov_pct"]<=0.35)].sort_values("blind_gap",ascending=False).head(80)
# GUARD: some but not all
assert 0 < len(bs) < len(f), f"blind-spot count off: {len(bs)}"
feats=[{"type":"Feature","geometry":{"type":"Point","coordinates":[float(r.lon),float(r.lat)]},
        "properties":{"gh7":r.gh7,"predicted_impact":round(float(r.pred_impact),1),"n":int(r.n),
            "distinct_devices":int(r.distinct_devices),"blind_gap":round(float(r.blind_gap),3),
            "dominant_vehicle_class":str(getattr(r,"dominant_vehicle_class","")),
            "primary_infraction_type":str(getattr(r,"primary_infraction_type",""))}} for r in bs.itertuples()]
os.makedirs("/kaggle/working/fe_out",exist_ok=True)
json.dump({"type":"FeatureCollection","features":feats}, open("/kaggle/working/fe_out/blindspots.geojson","w"))
print("blind spots:",len(feats),"of",len(f),"cells")
```

- [ ] **Step 2: Run** — `.venv/bin/python run_local.py fe/cells/53_blindspots.py` → prints a blind-spot count >0 and < total; writes `fe_work/fe_out/blindspots.geojson`. (If the booster's `feature_name()` mismatches, the `feat` intersection handles it; guard asserts validity.)
- [ ] **Step 3: Commit** — `git add fe/cells/53_blindspots.py && git commit -m "feat(fe): blind-spot finder (predicted-vs-observed enforcement gap)"`

### Task C2: include blindspots in the static bundle

**Files:** Modify `api/artifacts.py`; Test `api/tests/test_artifacts.py` already asserts manifest; extend copy list.

- [ ] **Step 1: Modify** `api/artifacts.py` copy list:
```python
    for fn in ["cells.geojson","top_enriched.geojson","rcp.geojson","rcp.csv","blindspots.geojson","kde_points.csv","rollup_gh6.csv","rollup_gh5.csv"]:
```
- [ ] **Step 2: Rebuild + test** — `.venv/bin/python -c "from api.artifacts import build_static; from api.config import settings; build_static(settings.SCORES_PARQUET, settings.FE_OUT, settings.STATIC_OUT)"` then `.venv/bin/python -m pytest api/tests/test_artifacts.py -q` → PASS; confirm `web/public/data/blindspots.geojson` exists.
- [ ] **Step 3: Commit** — `git add api/artifacts.py && git commit -m "feat(api): bundle blindspots.geojson"`

---

## Phase F — Frontend (mode switcher + 4 panels + layers)

### Task F1: api.js helpers + App btpMode state

**Files:** Modify `web/src/api.js`, `web/src/App.jsx`.

- [ ] **Step 1:** add to `web/src/api.js`:
```javascript
export async function patrolPlan(units, topk) {
  const r = await fetch(`/api/v1/triage/patrol-plan?units=${units}&topk=${topk}`);
  if (!r.ok) throw new Error(`patrol ${r.status}`); return r.json();
}
```
- [ ] **Step 2:** in `web/src/App.jsx` add `const [btpMode,setBtpMode]=useState("hotspots");` and load blindspots: in the initial `useEffect`, `loadStatic("blindspots.geojson").then(setBlind).catch(()=>{});` with `const [blind,setBlind]=useState(null);`. Pass `btpMode,setBtpMode,blind` to `BTPSidebar` and `btpMode,blind` to `MapView`.
- [ ] **Step 3: Commit** — `git add web/src/api.js web/src/App.jsx && git commit -m "feat(web): btpMode state + patrolPlan/blindspots data"`

### Task F2: BTPSidebar mode switcher + panels

**Files:** Create `web/src/components/panels/{HotspotsPanel,PatrolPanel,WhatIfPanel,BlindSpotsPanel}.jsx`; Modify `web/src/components/BTPSidebar.jsx`.

- [ ] **Step 1:** Move the current ranked-list/stats markup from `BTPSidebar.jsx` into `panels/HotspotsPanel.jsx` (same JSX, props `stats, tops, rcp, selected, onSelect`).
- [ ] **Step 2:** Create `panels/PatrolPanel.jsx`:
```jsx
import React, { useState } from "react";
import { patrolPlan } from "../../api.js";
export default function PatrolPanel({ onPlan, plan }) {
  const [units,setUnits]=useState(3),[topk,setTopk]=useState(15),[busy,setBusy]=useState(false);
  async function gen(){ setBusy(true); try{ onPlan(await patrolPlan(units,topk)); }catch{ onPlan(null);} finally{ setBusy(false);} }
  return (<div>
    <div className="banner"><b>Optimized patrol deployment.</b><br/><span className="muted">Cover the highest-impact zones with the fewest unit-minutes.</span></div>
    <div className="section-title">Units</div>
    <div>{[1,2,3,4].map(n=><button key={n} className={"pill"+(n===units?" on":"")} style={{cursor:"pointer"}} onClick={()=>setUnits(n)}>{n}</button>)}</div>
    <div className="section-title">Coverage depth</div>
    <div>{[10,15,20].map(k=><button key={k} className={"pill"+(k===topk?" on":"")} style={{cursor:"pointer"}} onClick={()=>setTopk(k)}>top {k}</button>)}</div>
    <button className="btn" style={{marginTop:12}} disabled={busy} onClick={gen}>{busy?"Optimizing…":"Generate patrol plan"}</button>
    {plan?.units?.map(u=>(<div key={u.unit_id} className="card" style={{marginTop:8}}>
      <div className="row"><span className="name" style={{color:u.color}}>Unit {u.unit_id}</span><span className="score">{u.drive_time_min} min</span></div>
      <div className="meta">{u.n_zones} zones · total impact {u.total_impact}</div></div>))}
  </div>);
}
```
- [ ] **Step 3:** Create `panels/WhatIfPanel.jsx`:
```jsx
import React, { useMemo } from "react";
export default function WhatIfPanel({ tops, rcp, selected, onTogglePreset }) {
  const rcpBy=useMemo(()=>{const m={};(rcp?.features||[]).forEach(f=>m[f.properties.gh7]=f.properties.delay_min);return m;},[rcp]);
  const totT3=useMemo(()=> (tops||[]).reduce((s,z)=>s+ (z.tier3_share*z.n),0)||1,[tops]);
  const sel=(tops||[]).filter(z=>selected.includes(z.gh7));
  const delay=Math.round(sel.reduce((s,z)=>s+(rcpBy[z.gh7]|| (Math.min(0.6,0.10+0.35*z.tier3_share+0.20*z.heavy_share)*6)),0));
  const t3=Math.round(sel.reduce((s,z)=>s+z.tier3_share*z.n,0)/totT3*100);
  const cites=sel.reduce((s,z)=>s+z.n,0);
  return (<div>
    <div className="banner"><b>What-if: clear these zones.</b><br/><span className="muted">See the payoff before you deploy.</span></div>
    <div>{[5,10,15].map(n=><button key={n} className="pill" style={{cursor:"pointer"}} onClick={()=>onTogglePreset(n)}>top {n}</button>)}</div>
    <div className="stats" style={{marginTop:12}}>
      <div className="stat"><div className="v" style={{color:"var(--hot)"}}>{delay}<span style={{fontSize:13}}> min</span></div><div className="k">Delay relieved</div></div>
      <div className="stat"><div className="v" style={{color:"var(--amber)"}}>{t3}%</div><div className="k">Carriageway-blocking removed</div></div>
      <div className="stat"><div className="v">{sel.length}</div><div className="k">Zones selected</div></div>
      <div className="stat"><div className="v">{cites.toLocaleString()}</div><div className="k">Citations covered</div></div>
    </div>
    <div className="muted" style={{marginTop:8}}>Click zones on the map to add/remove.</div>
  </div>);
}
```
- [ ] **Step 4:** Create `panels/BlindSpotsPanel.jsx`:
```jsx
import React from "react";
export default function BlindSpotsPanel({ blind, onSelect }) {
  const fs=blind?.features||[];
  return (<div>
    <div className="banner"><b>Under-enforced blind spots.</b><br/><span className="muted">High predicted impact, low current enforcement — what patrols miss.</span></div>
    <div className="section-title">{fs.length} candidate zones</div>
    {fs.slice(0,40).map(f=>{const p=f.properties;return (
      <div key={p.gh7} className="card" onClick={()=>onSelect({gh7:p.gh7,lat:f.geometry.coordinates[1],lon:f.geometry.coordinates[0]})}>
        <div className="row"><span className="name mono">{p.gh7}</span><span className="score" style={{color:"#e85bd0"}}>{p.predicted_impact}</span></div>
        <div className="meta">{p.n} citations · {p.distinct_devices} devices · gap {p.blind_gap}</div></div>);})}
  </div>);
}
```
- [ ] **Step 5:** Rewrite `BTPSidebar.jsx` to host the switcher + dispatch:
```jsx
import React from "react";
import HotspotsPanel from "./panels/HotspotsPanel.jsx";
import PatrolPanel from "./panels/PatrolPanel.jsx";
import WhatIfPanel from "./panels/WhatIfPanel.jsx";
import BlindSpotsPanel from "./panels/BlindSpotsPanel.jsx";
const MODES=[["hotspots","Hotspots"],["patrol","Patrol Plan"],["whatif","What-If"],["blind","Blind Spots"]];
export default function BTPSidebar(p){
  return (<div className="sidebar">
    <div className="toggle" style={{marginBottom:14,flexWrap:"wrap"}}>
      {MODES.map(([k,l])=><button key={k} className={p.btpMode===k?"on":""} onClick={()=>p.setBtpMode(k)}>{l}</button>)}
    </div>
    {p.btpMode==="hotspots" && <HotspotsPanel stats={p.stats} tops={p.tops} rcp={p.rcp} selected={p.selected} onSelect={p.onSelect}/>}
    {p.btpMode==="patrol" && <PatrolPanel onPlan={p.onPlan} plan={p.plan}/>}
    {p.btpMode==="whatif" && <WhatIfPanel tops={p.tops} rcp={p.rcp} selected={p.multi} onTogglePreset={p.onPreset}/>}
    {p.btpMode==="blind" && <BlindSpotsPanel blind={p.blind} onSelect={p.onSelect}/>}
  </div>);
}
```
- [ ] **Step 6:** Wire new props in `App.jsx`: `plan` state (`useState(null)`, setter passed as `onPlan`), `multi` state (array of gh7 for What-If), `onPreset(n)` sets `multi` to top-n gh7s from `tops`, and a `toggleCell(gh7)` for map clicks in what-if mode. Pass `btpMode, setBtpMode, plan, onPlan:setPlan, multi, onPreset, blind` to `BTPSidebar`.
- [ ] **Step 7: Build** — `npm --prefix web run build` → succeeds.
- [ ] **Step 8: Commit** — `git add web/src && git commit -m "feat(web): BTP mode switcher + patrol/what-if/blindspots panels"`

### Task F3: MapView mode-driven layers

**Files:** Modify `web/src/components/MapView.jsx`.

- [ ] **Step 1:** Accept `btpMode, plan, blind, multi, onToggleCell` props. Add layers conditioned on `persona==="btp" && btpMode`:
  - `patrol`: for each `plan.units[*]`, a `PathLayer` (getColor from `u.color` hex→rgb) + numbered `ScatterplotLayer` of `u.stops`.
  - `whatif`: GeoJsonLayer cells already drawn; add a highlight `ScatterplotLayer` for `multi`-selected zones (amber ring); make cell `onClick` call `onToggleCell(f.properties.gh7)` when `btpMode==="whatif"`.
  - `blind`: `ScatterplotLayer` from `blind.features` with hollow magenta markers (`stroked:true, filled:false, getLineColor:[232,91,208]`).
- [ ] **Step 2:** Add a hex→rgb helper at top of file:
```javascript
const hexRgb = (h) => [1,3,5].map((i)=>parseInt(h.slice(i,i+2),16));
```
- [ ] **Step 3: Build** — `npm --prefix web run build` → succeeds.
- [ ] **Step 4: Commit** — `git add web/src/components/MapView.jsx && git commit -m "feat(web): mode-driven map layers (patrol routes, what-if select, blind spots)"`

---

## Phase V — Verify (run + screenshot each mode)

### Task V1: live verification

- [ ] **Step 1:** ensure backend running (`uvicorn api.main:app --port 8011`) and `preview_start web`.
- [ ] **Step 2:** screenshot each BTP mode (Hotspots, Patrol Plan after Generate, What-If after a top-N preset, Blind Spots); pull console logs (expect 0 errors) and API logs (expect 200s on `/triage/patrol-plan`).
- [ ] **Step 3:** if a mode renders wrong, read source, fix, rebuild, re-screenshot.
- [ ] **Step 4: Commit** any fixes — `git commit -am "fix(web): verified all BTP modes via screenshots/logs"`

---

## Self-Review

**Spec coverage:** A (patrol) → A1–A3 + F2/F3 ✅; B (what-if, client-only) → WhatIfPanel + App wiring + MapView select ✅; C (blind spots) → C1/C2 + BlindSpotsPanel + MapView layer ✅; console mode switcher → F2 ✅; MapMyIndia Distance Matrix + Routing only → A1/A2 ✅; fallbacks → A1 (haversine), A2 (route() already has straight-line) ✅; tests mock Mappls → test_patrol uses FakeM ✅.

**Placeholder scan:** no TBD/TODO; all code blocks complete; thresholds (0.80/0.35), defaults (units 3, topk 15), colors are concrete.

**Type consistency:** `distance_matrix_many(coords)` signature used identically A1↔A2; `build_plan(df, mappls, units, topk)` consistent A2↔A3; plan shape (`units[].{unit_id,color,stops,route_geometry,drive_time_min,total_impact,n_zones}`) consistent A2↔PatrolPanel↔MapView; `blindspots.geojson` props consistent C1↔BlindSpotsPanel↔MapView; `multi` (gh7 array) consistent App↔WhatIfPanel↔MapView.
