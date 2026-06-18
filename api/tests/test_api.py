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
    assert r.status_code==422
def test_zone_404(mini_scores):
    r=app(mini_scores).get("/api/v1/zones/zzzzzzz")
    assert r.status_code==404 and r.json()["error"]["code"]=="not_found"
def test_openapi(mini_scores):
    assert app(mini_scores).get("/openapi.json").status_code==200
