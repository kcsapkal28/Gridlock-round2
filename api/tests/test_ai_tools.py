import json, math
import numpy as np
from api.scoring import ScoringService
from api.ai.tools import ToolExecutor
from api.config import settings

FIX = "api/tests/fixtures/cell_scores_mini.parquet"


class FakeM:
    def distance_matrix_many(self, coords):
        return [[math.dist(a, b) * 1000 for b in coords] for a in coords]
    def route(self, coords):
        return {"geometry": [[c[1], c[0]] for c in coords] * 50, "duration_s": 300, "distance_m": 900, "source": "live"}


def _ex(mini_scores):
    svc = ScoringService(FIX)
    blind = [{"properties": {"gh7": "z0", "predicted_impact": 90, "blind_gap": 0.8, "primary_infraction_type": "X"}}]
    return ToolExecutor(svc, FakeM(), {}, blind, [{"name": "Koramangala", "lat": 12.93, "lon": 77.62}])


def test_query_hotspots_compact(mini_scores):
    s, actions = _ex(mini_scores).query_hotspots({"limit": 50})
    assert len(s["top"]) <= 10                       # hard-capped
    assert set(s["top"][0]) == {"gh7", "impact", "tier3_pct", "heavy_pct", "n"}
    assert "geometry" not in json.dumps(s)


def test_geocode_area(mini_scores):
    s, _ = _ex(mini_scores).geocode({"place": "around HSR tonight"})
    assert s["matched_name"] == "hsr" and "lat" in s


def test_patrol_summary_has_no_geometry_but_artifact_does(mini_scores):
    summary, actions = _ex(mini_scores).make_patrol_plan({"units": 2, "topk": 8})
    blob = json.dumps(summary)
    assert "geometry" not in blob and "route_geometry" not in blob
    assert len(blob) <= settings.AI_MODEL_SUMMARY_MAX_CHARS
    plan_action = [a for a in actions if a["type"] == "showPatrolPlan"][0]
    assert plan_action["plan"]["units"][0]["route_geometry"]   # full geometry rides in the ui_action


def test_route_summary_has_no_geometry(mini_scores):
    summary, actions = _ex(mini_scores).analyze_route(
        {"origin": {"lat": 12.97, "lng": 77.59}, "dest": {"lat": 12.99, "lng": 77.62}})
    blob = json.dumps(summary)
    assert "geometry" not in blob and len(blob) <= settings.AI_MODEL_SUMMARY_MAX_CHARS
    assert set(summary) >= {"total_delay_min", "sla_risk", "recoverable_min", "n_chokes"}
    assert any(a["type"] == "showRoute" for a in actions)


def test_set_map_view_count_matches_data(mini_scores):
    ex = _ex(mini_scores)
    summary, actions = ex.set_map_view({"min_impact": 85})
    expected = int((ex.svc.df["impact"] >= 85).sum())
    assert summary["zones_shown_on_map"] == expected
    assert any(a["type"] == "setFilter" and a.get("min_impact") == 85 for a in actions)


def test_find_blindspots(mini_scores):
    s, _ = _ex(mini_scores).find_blindspots({"limit": 5})
    assert s["top"][0]["gh7"] == "z0" and "geometry" not in json.dumps(s)


def test_unknown_tool(mini_scores):
    s, a = _ex(mini_scores).dispatch("nope", {})
    assert "error" in s and a == []
