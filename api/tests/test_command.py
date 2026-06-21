from fastapi.testclient import TestClient
from api.main import create_app
from api.command import _confidence


def test_confidence_tiers():
    assert _confidence(20, 23)["tier"] == "Persistent"
    assert _confidence(9, 23)["tier"] == "Recurring"
    assert _confidence(2, 23)["tier"] == "Intermittent"
    assert "of 23 weeks" in _confidence(20, 23)["phrase"]


def test_command_today_shape(mini_scores):
    c = TestClient(create_app(scores_parquet=mini_scores))
    j = c.get("/api/v1/command/today?n=3&units=3").json()
    assert j["span_weeks"] >= 1
    assert 1 <= len(j["cards"]) <= 3
    assert j["shift_order"] and "ENFORCEMENT ORDER" in j["shift_order"]
    for card in j["cards"]:
        for k in ("area", "station", "action", "impact", "confidence", "spots", "lat", "lon"):
            assert k in card, f"missing {k}"
        assert isinstance(card["confidence"]["phrase"], str)


def test_command_today_distinct_areas(mini_scores):
    c = TestClient(create_app(scores_parquet=mini_scores))
    cards = c.get("/api/v1/command/today?n=3").json()["cards"]
    areas = [x["area"] for x in cards]
    assert len(areas) == len(set(areas))      # each card is a distinct place


def test_command_today_area_filter(mini_scores):
    c = TestClient(create_app(scores_parquet=mini_scores))
    j = c.get("/api/v1/command/today?area=koramangala&n=2").json()
    assert "error" not in j and len(j["cards"]) >= 1
