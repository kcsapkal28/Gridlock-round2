import math, pandas as pd, numpy as np
from api.mappls import MapplsClient
from api.patrol import build_plan
from fastapi.testclient import TestClient
from api.main import create_app

def test_dmm_fallback_haversine(tmp_path):
    c=MapplsClient(cache_dir=str(tmp_path), key="K", fetcher=lambda a,b:{})
    m=c.distance_matrix_many([(12.97,77.59),(12.98,77.60)], _fail=True)
    assert len(m)==2 and len(m[0])==2 and m[0][0]==0 and m[0][1]>0

class FakeM:
    def distance_matrix_many(self, coords):
        return [[math.dist(a,b) for b in coords] for a in coords]
    def route(self, coords):
        return {"geometry":[[c[1],c[0]] for c in coords],"duration_s":300,"distance_m":900,"source":"live"}

def _df(n=9):
    return pd.DataFrame({"gh7":[f"z{i}" for i in range(n)],"lat":12.96+np.linspace(0,.06,n),
        "lon":77.58+np.linspace(0,.06,n),"impact":np.linspace(99,80,n),"rank":range(1,n+1),
        "ranked":[True]*n})

def test_build_plan_units():
    plan=build_plan(_df(9), FakeM(), units=3, topk=9)
    assert len(plan["units"])==3
    assert sum(u["n_zones"] for u in plan["units"])==9
    for u in plan["units"]:
        assert u["route_geometry"] and u["drive_time_min"]>=0 and len(u["stops"])>=1

def test_patrol_endpoint(mini_scores):
    c=TestClient(create_app(scores_parquet=mini_scores))
    r=c.get("/api/v1/triage/patrol-plan?units=2&topk=6")
    assert r.status_code==200
    j=r.json(); assert len(j["units"])<=2 and j["topk"]==6
