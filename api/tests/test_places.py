from fastapi.testclient import TestClient
from api.main import create_app
from api.places import build_gazetteer, resolve, nearest_area, nearest_station

STATIONS = [{"name": "Indiranagar", "lat": 12.971, "lon": 77.641},
            {"name": "No Station", "lat": 0, "lon": 0}]


def test_resolve_exact_and_typo():
    g = build_gazetteer(STATIONS)
    assert resolve("koramangala", g)["name"] == "koramangala"
    # typo still resolves (fuzzy/substring)
    r = resolve("electronc city", g)
    assert "error" not in r and "electronic city" in (r["name"] + " ".join(r["candidates"]))
    # abbreviation
    assert "error" not in resolve("ecity", g)


def test_resolve_gibberish_returns_candidates():
    g = build_gazetteer(STATIONS)
    r = resolve("zzzqqq nowhere", g)
    assert "error" in r and isinstance(r["candidates"], list)


def test_nearest_area_and_station():
    g = build_gazetteer(STATIONS)
    assert isinstance(nearest_area(12.935, 77.622, g, STATIONS), str)
    st = nearest_station(12.971, 77.641, STATIONS)
    assert st and st["name"] == "Indiranagar" and "No Station" != st["name"]


def test_geocode_endpoint(mini_scores):
    c = TestClient(create_app(scores_parquet=mini_scores))
    r = c.get("/api/v1/geocode?q=koramangla")  # typo
    assert r.status_code == 200 and "error" not in r.json()


def test_patrol_plan_has_steps_and_station(mini_scores):
    c = TestClient(create_app(scores_parquet=mini_scores))
    j = c.get("/api/v1/triage/patrol-plan?units=2&topk=6&priority=heavy").json()
    assert j["priority"] == "heavy"
    for u in j["units"]:
        assert u["steps"] and u["stops"]
        assert all("area" in s and "action" in s for s in u["stops"])
        assert "shift_time_min" in u
