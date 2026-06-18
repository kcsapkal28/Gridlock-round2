from api.scoring import ScoringService
def svc(fix): return ScoringService(scores_parquet=fix, model_path="___nonexistent___")
def test_grid_hit(mini_scores):
    s=svc(mini_scores); r=s.score(12.97,77.59)
    assert set(["gh7","impact","source","degraded","nearest"]).issubset(r)
    assert 0<=r["impact"]<=100
def test_offgrid_returns_nearest_when_no_model(mini_scores):
    s=svc(mini_scores); r=s.score(0.0,0.0)
    assert r["source"]=="nearest" and r["degraded"] is True
    assert len(r["nearest"])>=1
def test_never_raises_on_valid_coords(mini_scores):
    s=svc(mini_scores); assert s.score(13.2,77.8)["impact"] is not None
