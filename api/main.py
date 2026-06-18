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
