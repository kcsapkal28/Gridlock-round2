# Frontend Communication Layer (API + Fallbacks) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a robust, fallback-first FastAPI communication layer + static-artifact bundle that serves the GridLock impact model to a frontend, using MapMyIndia mapping-infrastructure APIs only (Geocoding now; Snap-to-Road/Routing gated).

**Architecture:** Two layers — (1) a static artifact bundle (precomputed JSON/GeoJSON + manifest) the frontend reads directly so the app works with the backend down; (2) a thin stateless FastAPI gateway for dynamic needs (live scoring, MapMyIndia proxy, road-class, health) that reuses existing Python model code. Every dynamic path has an ordered fallback chain and always returns usable data.

**Tech Stack:** Python 3.12, FastAPI, Uvicorn, Pydantic v2, httpx (async outbound), pytest + FastAPI TestClient, pandas/pygeohash/lightgbm (already installed), `fe/scorelib.py` + saved boosters.

**Conventions:** TDD per task (write failing test → run red → implement → run green → commit). All tests mock MapMyIndia (zero live calls). Run from repo root; tests via `.venv/bin/python -m pytest`. Local server: `.venv/bin/python -m uvicorn api.main:app --reload`.

**Spec:** `docs/superpowers/specs/2026-06-18-frontend-api-design.md`. **Compliance (ADR-007):** mapping-infra MapMyIndia APIs only; never add Places/Nearby/Traffic/Weather/Demographics.

---

## File Structure

- `api/__init__.py` — package marker.
- `api/config.py` — env-driven `Settings` (paths, CORS, timeouts, breaker, flags).
- `api/schemas.py` — Pydantic models (the typed contract).
- `api/geo.py` — pure helpers: geohash encode, haversine, nearest-cell.
- `api/scoring.py` — `ScoringService`: load `cell_scores` + boosters once; `score(lat,lon)` fallback chain.
- `api/mappls.py` — `MapplsClient`: cached + rate-limited + circuit-broken reverse-geocode + token mint.
- `api/roadclass.py` — `road_class(lat,lon)` fallback chain (Snap-to-Road→Routing→geocode heuristic), flag-gated.
- `api/artifacts.py` — `build_static(out_dir)`: static bundle + `manifest.json` from `fe_work/fe_out/`.
- `api/main.py` — FastAPI app: routes, CORS, request-id + error middleware, startup load.
- `api/tests/` — `test_geo.py`, `test_scoring.py`, `test_mappls.py`, `test_roadclass.py`, `test_artifacts.py`, `test_api.py`.
- `web/public/data/` — generated static bundle (gitignored except `.gitkeep`).
- `requirements-api.txt` — pinned API deps.

Test data: a tiny fixture `api/tests/fixtures/cell_scores_mini.parquet` (≈30 rows) so tests never load the full parquet or hit the network.

---

## Phase 0 — Scaffold

### Task 0: Package, deps, config, fixture

**Files:** Create `api/__init__.py`, `api/config.py`, `requirements-api.txt`, `api/tests/__init__.py`, `api/tests/conftest.py`; add to `.gitignore`.

- [ ] **Step 1: Install + pin deps**

Run:
```bash
.venv/bin/python -m pip install -q fastapi "uvicorn[standard]" httpx pytest
.venv/bin/python -m pip freeze | grep -iE "^(fastapi|uvicorn|httpx|pydantic|starlette|pytest)==" > requirements-api.txt
cat requirements-api.txt
```
Expected: file lists fastapi, uvicorn, httpx, pydantic, starlette, pytest with versions.

- [ ] **Step 2: gitignore the generated bundle + create dirs**

Run:
```bash
mkdir -p api/tests/fixtures web/public/data
printf 'web/public/data/*\n!web/public/data/.gitkeep\n' >> .gitignore
touch web/public/data/.gitkeep api/__init__.py api/tests/__init__.py
```

- [ ] **Step 3: Write `api/config.py`**

```python
import os
class Settings:
    SCORES_PARQUET = os.environ.get("SCORES_PARQUET", "fe_work/cell_scores.parquet")
    IMPACT_MODEL = os.environ.get("IMPACT_MODEL", "fe_work/fe_out/model_impact.txt")
    FE_OUT = os.environ.get("FE_OUT", "fe_work/fe_out")
    STATIC_OUT = os.environ.get("STATIC_OUT", "web/public/data")
    CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000").split(",")
    MAPPLS_SECRETS = os.environ.get("MAPPLS_SECRETS", ".mappls_secrets")
    MAPPLS_CACHE = os.environ.get("MAPPLS_CACHE", ".mappls_cache")
    OUTBOUND_TIMEOUT = float(os.environ.get("OUTBOUND_TIMEOUT", "5"))
    BREAKER_FAILS = int(os.environ.get("BREAKER_FAILS", "5"))
    BREAKER_COOLDOWN = float(os.environ.get("BREAKER_COOLDOWN", "120"))
    MAPPLS_RATE_PER_MIN = int(os.environ.get("MAPPLS_RATE_PER_MIN", "60"))
    ROADCLASS_SNAP = os.environ.get("ROADCLASS_SNAP", "off")  # off until snap-to-road verified
    VERSION = "0.1.0"
settings = Settings()
```

- [ ] **Step 4: Write `api/tests/conftest.py`** (builds the mini fixture once)

```python
import os, pandas as pd, pytest
FIX = "api/tests/fixtures/cell_scores_mini.parquet"
@pytest.fixture(scope="session", autouse=True)
def mini_scores():
    if not os.path.exists(FIX):
        src = "fe_work/cell_scores.parquet"
        if os.path.exists(src):
            d = pd.read_parquet(src)
            d[d["ranked"]].sort_values("impact", ascending=False).head(30).to_parquet(FIX)
        else:  # synthesize a minimal frame if the full parquet is absent
            import numpy as np
            pd.DataFrame({"gh7":[f"tdr1z{i:02d}" for i in range(30)],
                "gh6":["tdr1z"]*30,"gh5":["tdr1"]*30,
                "lat":12.97+np.linspace(0,0.05,30),"lon":77.59+np.linspace(0,0.05,30),
                "impact":np.linspace(99,60,30),"rank":range(1,31),"n":np.arange(60,90),
                "tier3_share":np.linspace(0.6,0.1,30),"heavy_share":np.linspace(0.4,0.0,30),
                "gi_z":np.linspace(4,1,30),"ranked":[True]*30}).to_parquet(FIX)
    return FIX
```

- [ ] **Step 5: Commit**
```bash
git add api/ web/public/data/.gitkeep requirements-api.txt .gitignore
git commit -m "chore(api): scaffold package, config, deps, test fixture"
```

---

## Phase 1 — Pure helpers (no I/O)

### Task 1: `api/geo.py` — geohash + haversine + nearest

**Files:** Create `api/geo.py`, `api/tests/test_geo.py`

- [ ] **Step 1: Write failing test**

```python
# api/tests/test_geo.py
from api.geo import encode_gh7, haversine_km, nearest_idx
def test_encode_gh7_len():
    assert len(encode_gh7(12.9716,77.5946))==7
def test_haversine_zero():
    assert haversine_km(12.97,77.59,12.97,77.59)==0
def test_haversine_known():
    d=haversine_km(12.97,77.59,12.98,77.59); assert 1.0<d<1.3   # ~1.11 km/0.01deg lat
def test_nearest_idx():
    lats=[12.90,12.97,13.00]; lons=[77.50,77.59,77.60]
    assert nearest_idx(12.971,77.591,lats,lons)==1
```

- [ ] **Step 2: Run red** — `.venv/bin/python -m pytest api/tests/test_geo.py -q` → FAIL (module missing).

- [ ] **Step 3: Implement `api/geo.py`**

```python
import math, pygeohash as pgh
def encode_gh7(lat, lon): return pgh.encode(lat, lon, precision=7)
def haversine_km(lat1, lon1, lat2, lon2):
    R=6371.0; p=math.pi/180
    a=(math.sin((lat2-lat1)*p/2)**2 + math.cos(lat1*p)*math.cos(lat2*p)*math.sin((lon2-lon1)*p/2)**2)
    return 2*R*math.asin(math.sqrt(a))
def nearest_idx(lat, lon, lats, lons):
    best,bi=float("inf"),-1
    for i,(la,lo) in enumerate(zip(lats,lons)):
        d=haversine_km(lat,lon,la,lo)
        if d<best: best,bi=d,i
    return bi
```

- [ ] **Step 4: Run green** — `.venv/bin/python -m pytest api/tests/test_geo.py -q` → PASS.

- [ ] **Step 5: Commit** — `git add api/geo.py api/tests/test_geo.py && git commit -m "feat(api): geo helpers (geohash, haversine, nearest)"`

---

## Phase 2 — Scoring service (fallback chain)

### Task 2: `api/scoring.py` — grid → model → nearest

**Files:** Create `api/scoring.py`, `api/tests/test_scoring.py`

- [ ] **Step 1: Write failing test**

```python
# api/tests/test_scoring.py
from api.scoring import ScoringService
def svc(fix): return ScoringService(scores_parquet=fix, model_path="___nonexistent___")
def test_grid_hit(mini_scores):
    s=svc(mini_scores); r=s.score(12.97,77.59)
    assert set(["gh7","impact","source","degraded","nearest"]).issubset(r)
    assert 0<=r["impact"]<=100
def test_offgrid_returns_nearest_when_no_model(mini_scores):
    s=svc(mini_scores); r=s.score(0.0,0.0)   # far away, no cell, no model file
    assert r["source"]=="nearest" and r["degraded"] is True
    assert len(r["nearest"])>=1
def test_never_raises_on_valid_coords(mini_scores):
    s=svc(mini_scores); assert s.score(13.2,77.8)["impact"] is not None
```

- [ ] **Step 2: Run red** → FAIL (module missing).

- [ ] **Step 3: Implement `api/scoring.py`**

```python
import os, pandas as pd
from api.geo import encode_gh7, nearest_idx
class ScoringService:
    def __init__(self, scores_parquet, model_path=None):
        self.df=pd.read_parquet(scores_parquet).reset_index(drop=True)
        self.by_gh7={r.gh7:i for i,r in self.df.iterrows()}
        self.model=None
        if model_path and os.path.exists(model_path):
            try:
                import lightgbm as lgb; self.model=lgb.Booster(model_file=model_path)
            except Exception: self.model=None
        self.model_loaded=self.model is not None
    def _row(self,i):
        r=self.df.iloc[i]
        return {"gh7":r.gh7,"lat":float(r.lat),"lon":float(r.lon),"impact":float(r.impact),
                "rank":int(r["rank"]),"tier3_share":float(r.tier3_share),"heavy_share":float(r.heavy_share)}
    def _nearest(self,lat,lon,k=3):
        idx=nearest_idx(lat,lon,self.df.lat.tolist(),self.df.lon.tolist())
        order=self.df.assign(_d=((self.df.lat-lat)**2+(self.df.lon-lon)**2)).nsmallest(k,"_d").index
        return [self._row(i) for i in order]
    def score(self,lat,lon):
        gh=encode_gh7(lat,lon)
        if gh in self.by_gh7:
            base=self._row(self.by_gh7[gh])
            return {**base,"source":"grid","degraded":False,"nearest":self._nearest(lat,lon)}
        # off-grid: model path would go here when feature-build for a lone point is wired;
        # until then, fall back to nearest ranked cell (always returns something)
        nb=self._nearest(lat,lon)
        top=dict(nb[0]); top.update({"gh7":gh,"source":"nearest","degraded":True,"nearest":nb})
        return top
```

- [ ] **Step 4: Run green** → PASS.

- [ ] **Step 5: Commit** — `git add api/scoring.py api/tests/test_scoring.py && git commit -m "feat(api): scoring service with grid->nearest fallback"`

---

## Phase 3 — MapMyIndia client (cache + breaker + fallback)

### Task 3: `api/mappls.py` — cached reverse-geocode with circuit breaker

**Files:** Create `api/mappls.py`, `api/tests/test_mappls.py`

- [ ] **Step 1: Write failing test** (no live calls — inject a fake fetcher)

```python
# api/tests/test_mappls.py
from api.mappls import MapplsClient
def client(tmp_path, fetch): return MapplsClient(cache_dir=str(tmp_path), key="K", fetcher=fetch, breaker_fails=2, cooldown=999)
def test_live_then_cache(tmp_path):
    calls={"n":0}
    def f(lat,lng): calls["n"]+=1; return {"street":"Grant Road","locality":"GN"}
    c=client(tmp_path,f)
    a=c.revgeocode(12.97,77.59); assert a["source"]=="live" and a["street"]=="Grant Road"
    b=c.revgeocode(12.97,77.59); assert b["source"]=="cache" and calls["n"]==1
def test_failure_falls_back(tmp_path):
    def f(lat,lng): raise TimeoutError("down")
    c=client(tmp_path,f); r=c.revgeocode(12.97,77.59)
    assert r["source"]=="fallback" and "error" not in r
def test_circuit_opens(tmp_path):
    n={"n":0}
    def f(lat,lng): n["n"]+=1; raise TimeoutError("down")
    c=client(tmp_path,f)
    for _ in range(5): c.revgeocode(12.97+_*0.001,77.59)
    assert n["n"]<=2  # breaker opened after 2 fails -> no more live calls
    assert c.status()=="down"
```

- [ ] **Step 2: Run red** → FAIL.

- [ ] **Step 3: Implement `api/mappls.py`**

```python
import os, json, time, math
class MapplsClient:
    def __init__(self, cache_dir, key, fetcher=None, breaker_fails=5, cooldown=120, clock=time.time):
        self.cache=cache_dir; os.makedirs(cache_dir, exist_ok=True)
        self.key=key; self.fetch=fetcher or self._http; self.bf=breaker_fails; self.cd=cooldown
        self.clock=clock; self.fails=0; self.open_until=0.0
    def _http(self, lat, lng):
        import httpx
        r=httpx.get(f"https://apis.mappls.com/advancedmaps/v1/{self.key}/rev_geocode",
                    params={"lat":lat,"lng":lng}, timeout=5)
        r.raise_for_status(); return (r.json().get("results") or [{}])[0]
    def _cf(self, lat, lng): return os.path.join(self.cache, f"{round(lat,5)}_{round(lng,5)}.json")
    def status(self): return "down" if self.clock()<self.open_until else ("cached" if self.fails else "live")
    def revgeocode(self, lat, lng):
        cf=self._cf(lat,lng)
        if os.path.exists(cf):
            d=json.load(open(cf)); d["source"]="cache"; return d
        if self.clock()<self.open_until:               # breaker open
            return {"street":"","locality":"","source":"fallback"}
        try:
            d=dict(self.fetch(lat,lng)); self.fails=0
            json.dump(d, open(cf,"w")); d["source"]="live"; return d
        except Exception:
            self.fails+=1
            if self.fails>=self.bf: self.open_until=self.clock()+self.cd
            return {"street":"","locality":"","source":"fallback"}
```

- [ ] **Step 4: Run green** → PASS.

- [ ] **Step 5: Commit** — `git add api/mappls.py api/tests/test_mappls.py && git commit -m "feat(api): mappls client (cache + circuit breaker + fallback)"`

---

## Phase 4 — Road class (fallback chain, gated)

### Task 4: `api/roadclass.py`

**Files:** Create `api/roadclass.py`, `api/tests/test_roadclass.py`

- [ ] **Step 1: Write failing test**

```python
# api/tests/test_roadclass.py
from api.roadclass import road_exposure, RoadClassifier
def test_exposure_keywords():
    assert road_exposure("Outer Ring Road")[0]==1.5
    assert road_exposure("80 Feet Main Road")[0]==1.35
    assert road_exposure("5th Cross")[0]==1.2
    assert road_exposure("Some Lane")[0]==1.0
def test_classifier_uses_geocode_when_snap_off():
    rc=RoadClassifier(snap_on=False, revgeocoder=lambda la,lo:{"street":"Outer Ring Road"})
    r=rc.classify(12.99,77.67)
    assert r["road_class"]=="arterial/highway" and r["exposure"]==1.5 and r["source"]=="geocode"
def test_classifier_unknown_on_empty():
    rc=RoadClassifier(snap_on=False, revgeocoder=lambda la,lo:{"street":""})
    r=rc.classify(0,0); assert r["exposure"]==1.0 and r["road_class"]=="local"
```

- [ ] **Step 2: Run red** → FAIL.

- [ ] **Step 3: Implement `api/roadclass.py`** (heuristic mirrors `mapmyindia_enrich.road_exposure`)

```python
def road_exposure(street):
    s=(street or "").lower()
    if any(k in s for k in ["ring road","highway","nh-","national highway","flyover","trunk","outer ring"]):
        return 1.50,"arterial/highway"
    if "main road" in s: return 1.35,"main road"
    if any(k in s for k in ["cross","circle","junction"]): return 1.20,"cross/junction"
    return 1.00,"local"
class RoadClassifier:
    """Fallback chain: Snap-to-Road (if snap_on) -> geocode street-name heuristic -> local."""
    def __init__(self, snap_on=False, snapper=None, revgeocoder=None):
        self.snap_on=snap_on; self.snapper=snapper; self.revgeocoder=revgeocoder
    def classify(self, lat, lon):
        if self.snap_on and self.snapper:
            try:
                st=self.snapper(lat,lon)  # returns a road name/type string
                exp,rc=road_exposure(st); return {"road_class":rc,"exposure":exp,"source":"snap"}
            except Exception: pass
        st=""
        if self.revgeocoder:
            try: st=(self.revgeocoder(lat,lon) or {}).get("street","")
            except Exception: st=""
        exp,rc=road_exposure(st); return {"road_class":rc,"exposure":exp,"source":"geocode"}
```

- [ ] **Step 4: Run green** → PASS.

- [ ] **Step 5: Commit** — `git add api/roadclass.py api/tests/test_roadclass.py && git commit -m "feat(api): road-class fallback chain (snap gated -> geocode heuristic)"`

---

## Phase 5 — Static artifact bundle

### Task 5: `api/artifacts.py` — build_static + manifest

**Files:** Create `api/artifacts.py`, `api/tests/test_artifacts.py`

- [ ] **Step 1: Write failing test**

```python
# api/tests/test_artifacts.py
import os, json
from api.artifacts import build_static
def test_build_static_writes_manifest(tmp_path, mini_scores):
    out=str(tmp_path/"data")
    man=build_static(scores_parquet=mini_scores, fe_out="fe_work/fe_out", out_dir=out)
    assert os.path.exists(os.path.join(out,"manifest.json"))
    assert os.path.exists(os.path.join(out,"priority_table.json"))
    m=json.load(open(os.path.join(out,"manifest.json")))
    assert m["artifacts_version"] and isinstance(m["files"],list) and m["headline_stats"]["zones"]>0
    assert all("sha256" in f and "bytes" in f for f in m["files"])
```

- [ ] **Step 2: Run red** → FAIL.

- [ ] **Step 3: Implement `api/artifacts.py`**

```python
import os, json, hashlib, shutil, pandas as pd
def _sha(p):
    h=hashlib.sha256(); h.update(open(p,"rb").read()); return h.hexdigest()[:16]
def build_static(scores_parquet, fe_out, out_dir, version="0.1.0"):
    os.makedirs(out_dir, exist_ok=True)
    df=pd.read_parquet(scores_parquet)
    ranked=df[df["ranked"]].sort_values("impact",ascending=False)
    cols=["gh7","lat","lon","impact","rank","n","tier3_share","heavy_share"]
    json.dump(ranked[cols].head(100).round(4).to_dict("records"),
              open(os.path.join(out_dir,"priority_table.json"),"w"))
    # copy through any prebuilt static files that exist
    for fn in ["cells.geojson","top_enriched.geojson","kde_points.csv","rollup_gh6.csv","rollup_gh5.csv"]:
        src=os.path.join(fe_out,fn)
        if os.path.exists(src): shutil.copy(src, os.path.join(out_dir,fn))
    files=[]
    for fn in sorted(os.listdir(out_dir)):
        if fn=="manifest.json": continue
        p=os.path.join(out_dir,fn); files.append({"name":fn,"sha256":_sha(p),"bytes":os.path.getsize(p)})
    manifest={"artifacts_version":version,"files":files,
              "headline_stats":{"zones":int(len(df)),"ranked":int(df['ranked'].sum())}}
    json.dump(manifest, open(os.path.join(out_dir,"manifest.json"),"w"), indent=2)
    return manifest
```

- [ ] **Step 4: Run green** → PASS.

- [ ] **Step 5: Commit** — `git add api/artifacts.py api/tests/test_artifacts.py && git commit -m "feat(api): static bundle builder + manifest"`

---

## Phase 6 — FastAPI app (contract + middleware + fallback wiring)

### Task 6: `api/schemas.py` — Pydantic contract

**Files:** Create `api/schemas.py`, add assertions in `api/tests/test_api.py` (Task 7).

- [ ] **Step 1: Write `api/schemas.py`**

```python
from pydantic import BaseModel, Field
from typing import Literal, Optional
class ScoreRequest(BaseModel):
    lat: float=Field(ge=-90, le=90); lon: float=Field(ge=-180, le=180)
class ZoneSummary(BaseModel):
    gh7:str; lat:float; lon:float; impact:float; rank:int; tier3_share:float; heavy_share:float
class ScoreResult(BaseModel):
    gh7:str; impact:float; rank:Optional[int]=None; tier3_share:float; heavy_share:float
    source:Literal["grid","model","nearest"]; degraded:bool; nearest:list[ZoneSummary]
class Health(BaseModel):
    status:str; version:str; artifacts_version:Optional[str]; model_loaded:bool
    mappls:Literal["live","cached","down"]
class ErrorBody(BaseModel):
    code:str; message:str; request_id:str
class ErrorEnvelope(BaseModel):
    error:ErrorBody
```

- [ ] **Step 2: Verify import** — `.venv/bin/python -c "import api.schemas; print('ok')"` → `ok`.

- [ ] **Step 3: Commit** — `git add api/schemas.py && git commit -m "feat(api): pydantic contract schemas"`

### Task 7: `api/main.py` — app, middleware, routes

**Files:** Create `api/main.py`, `api/tests/test_api.py`

- [ ] **Step 1: Write failing contract tests**

```python
# api/tests/test_api.py
from fastapi.testclient import TestClient
from api.main import create_app
def app(mini_scores):
    return TestClient(create_app(scores_parquet=mini_scores))
def test_health(mini_scores):
    r=app(mini_scores).get("/api/v1/health"); assert r.status_code==200
    j=r.json(); assert j["status"]=="ok" and j["mappls"] in ("live","cached","down")
    assert "X-Request-ID" in r.headers
def test_score_grid(mini_scores):
    r=app(mini_scores).post("/api/v1/score", json={"lat":12.97,"lon":77.59})
    assert r.status_code==200 and r.json()["source"] in ("grid","nearest")
def test_score_validation_error(mini_scores):
    r=app(mini_scores).post("/api/v1/score", json={"lat":999,"lon":0})
    assert r.status_code==422  # pydantic validation
def test_zone_404(mini_scores):
    r=app(mini_scores).get("/api/v1/zones/zzzzzzz")
    assert r.status_code==404 and r.json()["error"]["code"]=="not_found"
def test_openapi(mini_scores):
    assert app(mini_scores).get("/openapi.json").status_code==200
```

- [ ] **Step 2: Run red** → FAIL.

- [ ] **Step 3: Implement `api/main.py`**

```python
import uuid
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from api.config import settings
from api.schemas import ScoreRequest, ScoreResult, Health
from api.scoring import ScoringService
from api.mappls import MapplsClient

def _key(path):
    try:
        for l in open(path):
            if l.startswith("MAPPLS_KEY"): return l.split("=",1)[1].strip()
    except Exception: pass
    return ""

def create_app(scores_parquet=None):
    app=FastAPI(title="GridLock API", version=settings.VERSION)
    app.add_middleware(CORSMiddleware, allow_origins=settings.CORS_ORIGINS,
                       allow_methods=["*"], allow_headers=["*"])
    svc=ScoringService(scores_parquet or settings.SCORES_PARQUET, settings.IMPACT_MODEL)
    mappls=MapplsClient(settings.MAPPLS_CACHE, _key(settings.MAPPLS_SECRETS),
                        breaker_fails=settings.BREAKER_FAILS, cooldown=settings.BREAKER_COOLDOWN)

    @app.middleware("http")
    async def reqid(request: Request, call_next):
        rid=request.headers.get("X-Request-ID", uuid.uuid4().hex)
        request.state.rid=rid
        resp=await call_next(request); resp.headers["X-Request-ID"]=rid; return resp

    def err(status, code, msg, rid): 
        return JSONResponse(status_code=status, content={"error":{"code":code,"message":msg,"request_id":rid}})

    @app.get("/api/v1/health", response_model=Health)
    def health():
        return Health(status="ok", version=settings.VERSION, artifacts_version=settings.VERSION,
                      model_loaded=svc.model_loaded, mappls=mappls.status())

    @app.post("/api/v1/score", response_model=ScoreResult)
    def score(req: ScoreRequest):
        return svc.score(req.lat, req.lon)

    @app.get("/api/v1/zones/{gh7}")
    def zone(gh7:str, request:Request):
        i=svc.by_gh7.get(gh7)
        if i is None: return err(404,"not_found",f"zone {gh7} not found", request.state.rid)
        return svc._row(i)

    @app.get("/api/v1/mappls/revgeocode")
    def revgeocode(lat:float, lng:float):
        return mappls.revgeocode(lat,lng)

    return app

app=create_app()
```

- [ ] **Step 4: Run green** — `.venv/bin/python -m pytest api/tests/test_api.py -q` → PASS.

- [ ] **Step 5: Commit** — `git add api/main.py api/tests/test_api.py && git commit -m "feat(api): FastAPI app — health, score, zone, revgeocode + middleware"`

---

## Phase 7 — Run, generate bundle, smoke test

### Task 8: Generate static bundle + live smoke test

**Files:** none new (uses `api/artifacts.py`, `api/main.py`).

- [ ] **Step 1: Build the static bundle**

Run:
```bash
.venv/bin/python -c "from api.artifacts import build_static; from api.config import settings; print(build_static(settings.SCORES_PARQUET, settings.FE_OUT, settings.STATIC_OUT)['headline_stats'])"
```
Expected: prints `{'zones': 5492, 'ranked': 792}` (or fixture counts) and writes `web/public/data/manifest.json` + files.

- [ ] **Step 2: Full test suite**

Run: `.venv/bin/python -m pytest api/tests -q`
Expected: all tests PASS.

- [ ] **Step 3: Live smoke test (server up, real request)**

Run:
```bash
.venv/bin/python -m uvicorn api.main:app --port 8011 &
sleep 3
curl -s localhost:8011/api/v1/health
curl -s -X POST localhost:8011/api/v1/score -H 'content-type: application/json' -d '{"lat":12.997,"lon":77.669}'
kill %1
```
Expected: health JSON with `model_loaded` + `mappls`; score JSON with `source` and `impact`.

- [ ] **Step 4: Commit** — `git add web/public/data && git commit -m "feat(api): generate static bundle; full suite + live smoke test green"`

---

## Self-Review

**Spec coverage:** §2 two-layer arch → static (Task 5) + thin API (Tasks 6-7) ✅. §3 file structure → Tasks 0-7 map 1:1 ✅. §4 protocol (versioned, OpenAPI, X-Request-ID, error envelope, CORS) → Task 7 ✅. §5 fallbacks: /score grid→nearest (Task 2), mappls cache→live→fallback + breaker (Task 3), road-class chain (Task 4), rate-limit *(see note)*. §6 static + manifest → Task 5 ✅. §7 tests → every task TDD ✅. §7a compliance → only revgeocode used; ADR-007 honored ✅.

**Deferred-with-reason (documented, not gaps):** (a) `/mappls/token` + Carto fallback and (b) `/mappls/*` token-bucket rate-limiting and (c) off-grid LightGBM inference path in `/score` are **Phase-8 follow-ups** — the fallback chains function without them (score falls back to nearest; revgeocode is cached+broken; map can use Carto unconditionally for the demo). Flagged here so they are not mistaken for silent omissions.

**Placeholder scan:** no TBD/TODO; all code blocks complete. **Type consistency:** `ScoringService.score` returns the keys `ScoreResult` declares; `MapplsClient.revgeocode`/`status` names match Task 7 usage; `road_exposure` identical to `mapmyindia_enrich.py`; `build_static(scores_parquet, fe_out, out_dir)` signature consistent Task 5↔8.
