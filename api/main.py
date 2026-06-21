import os, uuid
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from api.config import settings
from api.schemas import ScoreRequest, ScoreResult, Health
from api.scoring import ScoringService
from api.mappls import MapplsClient
from api.schemas import ImpedanceRequest
from api.logistics import impedance, load_rcp
from api.patrol import build_plan
from api.places import build_gazetteer, resolve as resolve_place
import json as _json

def _load_json(path, default):
    try:
        return _json.load(open(path))
    except Exception:
        return default

def _key(path):
    env = __import__("os").environ.get("MAPPLS_KEY")   # prefer env (Render secret) over the file
    if env: return env.strip()
    try:
        for l in open(path):
            if l.startswith("MAPPLS_KEY"): return l.split("=",1)[1].strip()
    except Exception: pass
    return ""

def create_app(scores_parquet=None):
    sp = scores_parquet or settings.SCORES_PARQUET
    # On a fresh clone the scored artifacts are not in git — pull them from Drive on first run.
    if not os.path.exists(sp):
        try:
            from fetch_assets import ensure_assets
            ensure_assets()
        except Exception as _e:  # noqa: BLE001 - never block startup on the fetch helper
            print(f"[startup] asset auto-fetch skipped: {_e}")
    app=FastAPI(title="GridLock API", version=settings.VERSION)
    app.add_middleware(CORSMiddleware, allow_origins=settings.CORS_ORIGINS,
                       allow_methods=["*"], allow_headers=["*"])
    svc=ScoringService(sp, settings.IMPACT_MODEL)
    mappls=MapplsClient(settings.MAPPLS_CACHE, _key(settings.MAPPLS_SECRETS),
                        breaker_fails=settings.BREAKER_FAILS, cooldown=settings.BREAKER_COOLDOWN)
    rcp_lookup=load_rcp(settings.RCP_CSV)
    stations=_load_json(settings.STATIONS_JSON, [])
    gazetteer=build_gazetteer(stations)
    _mappls_bykey={}   # judge-supplied keys → per-key client (preserves cache/breaker per key)

    def mappls_for(request):
        """Use a judge's X-Mappls-Key header (per-request) when present, else the default client."""
        k=(request.headers.get("x-mappls-key") or "").strip() if request else ""
        if not k:
            return mappls
        c=_mappls_bykey.get(k)
        if c is None:
            c=MapplsClient(settings.MAPPLS_CACHE, k, breaker_fails=settings.BREAKER_FAILS,
                           cooldown=settings.BREAKER_COOLDOWN)
            _mappls_bykey[k]=c
        return c

    @app.middleware("http")
    async def reqid(request: Request, call_next):
        rid=request.headers.get("X-Request-ID", uuid.uuid4().hex)
        request.state.rid=rid
        resp=await call_next(request); resp.headers["X-Request-ID"]=rid; return resp

    def err(status, code, msg, rid):
        return JSONResponse(status_code=status, content={"error":{"code":code,"message":msg,"request_id":rid}})

    @app.get("/api/v1/health", response_model=Health)
    def health(request: Request):
        return Health(status="ok", version=settings.VERSION, artifacts_version=settings.VERSION,
                      model_loaded=svc.model_loaded, mappls=mappls_for(request).status())

    @app.post("/api/v1/score", response_model=ScoreResult)
    def score(req: ScoreRequest):
        return svc.score(req.lat, req.lon)

    @app.get("/api/v1/zones/{gh7}")
    def zone(gh7:str, request:Request):
        i=svc.by_gh7.get(gh7)
        if i is None: return err(404,"not_found",f"zone {gh7} not found", request.state.rid)
        return svc._row(i)

    @app.get("/api/v1/mappls/revgeocode")
    def revgeocode(lat:float, lng:float, request:Request):
        return mappls_for(request).revgeocode(lat,lng)

    @app.get("/api/v1/triage/hotspots")
    def triage(min_impact: float = 0.0, limit: int = 500):
        d = svc.df[(svc.df["ranked"]) & (svc.df["impact"] >= min_impact)] \
                 .sort_values("impact", ascending=False).head(limit)
        feats=[]
        for r in d.itertuples():
            feats.append({"type":"Feature","geometry":{"type":"Point","coordinates":[float(r.lon),float(r.lat)]},
                "properties":{"gh7":r.gh7,"impact":round(float(r.impact),2),"rank":int(r.rank),
                    "n":int(r.n),"tier3_share":round(float(r.tier3_share),3),
                    "heavy_share":round(float(r.heavy_share),3),
                    "dominant_vehicle_class":str(getattr(r,"dominant_vehicle_class","")),
                    "primary_infraction_type":str(getattr(r,"primary_infraction_type",""))}})
        return {"type":"FeatureCollection","features":feats}

    @app.get("/api/v1/triage/patrol-plan")
    def patrol_plan(request: Request, units: int = 3, topk: int = 15, priority: str = "impact",
                    start_from_station: bool = True):
        return build_plan(svc.df, mappls_for(request), units=units, topk=topk, priority=priority,
                          start_from_station=start_from_station, stations=stations)

    @app.get("/api/v1/geocode")
    def geocode(q: str):
        """Forgiving area-name → coordinate resolver (typos / abbreviations / partials OK)."""
        return resolve_place(q, gazetteer)

    @app.post("/api/v1/logistics/impedance-loop")
    def impedance_loop(req: ImpedanceRequest, request: Request):
        wps=[{"lat":w.lat,"lng":w.lng} for w in req.waypoints]
        return impedance(wps, svc.df, rcp_lookup, mappls_for(request), min_impact=req.min_impact)

    @app.get("/api/v1/logistics/route-by-name")
    def route_by_name(origin: str, dest: str, min_impact: float = 80.0, request: Request = None):
        """Resolve two free-typed area names, then analyse the route between them.
        Works without the AI proxy — the fuzzy gazetteer handles spelling slips."""
        o=resolve_place(origin, gazetteer); d=resolve_place(dest, gazetteer)
        if "error" in o:
            return err(422,"geocode_failed",f"origin: {o['error']}", getattr(request.state,"rid",""))
        if "error" in d:
            return err(422,"geocode_failed",f"dest: {d['error']}", getattr(request.state,"rid",""))
        wps=[{"lat":o["lat"],"lng":o["lon"]},{"lat":d["lat"],"lng":d["lon"]}]
        res=impedance(wps, svc.df, rcp_lookup, mappls_for(request), min_impact=min_impact)
        res["origin_name"]=o["name"]; res["dest_name"]=d["name"]
        return res

    # AI copilot (Claude via local proxy). Isolated router; degrades to "offline" if unreachable.
    try:
        from api.ai.routes import build_ai_router
        app.include_router(build_ai_router(svc, mappls))
    except Exception as _e:
        print(f"[startup] AI copilot not mounted: {_e}")

    return app

app=create_app()
