"""Copilot tools. Each executor returns (model_summary, ui_actions):
- model_summary: tiny grounded dict the model sees (scalars/short lists, NO geometry).
- ui_actions:    list of {type, ...} applied by the frontend (full plan/route w/ geometry rides here).
"""
from api.geo import haversine_km
from api.places import build_gazetteer, resolve as resolve_place


def _rows(df, n):
    out = []
    for r in df.head(n).itertuples():
        out.append({"gh7": r.gh7, "impact": round(float(r.impact), 1),
                    "tier3_pct": round(float(r.tier3_share) * 100), "heavy_pct": round(float(r.heavy_share) * 100),
                    "n": int(r.n)})
    return out


class ToolExecutor:
    def __init__(self, svc, mappls, rcp_lookup, blindspots, stations):
        self.svc = svc
        self.mappls = mappls
        self.rcp = rcp_lookup
        self.blind = blindspots or []
        self.stations = stations or []
        self.gaz = build_gazetteer(stations)

    # ---- geocode (forgiving: typos / abbreviations / partial names all resolve) ----
    def geocode(self, inp):
        q = (inp.get("place") or "").strip()
        if not q:
            return {"error": "no place given"}, []
        res = resolve_place(q, self.gaz)
        if "error" in res:
            return {"error": res["error"], "did_you_mean": res.get("candidates", [])[:3]}, []
        return {"matched_name": res["name"], "lat": res["lat"], "lon": res["lon"]}, []

    def _near_filter(self, df, near):
        if not near:
            return df
        la, lo, rad = near.get("lat"), near.get("lon"), near.get("radius_km", 2.0)
        if la is None or lo is None:
            return df
        d = df.copy()
        d["_d"] = [haversine_km(la, lo, a, b) for a, b in zip(d["lat"], d["lon"])]
        return d[d["_d"] <= rad].sort_values("impact", ascending=False)

    def query_hotspots(self, inp):
        df = self.svc.df[self.svc.df["ranked"]].sort_values("impact", ascending=False)
        mi = inp.get("min_impact")
        if mi is not None:
            df = df[df["impact"] >= float(mi)]
        df = self._near_filter(df, inp.get("near"))
        limit = min(int(inp.get("limit", 8)), 10)
        rows = _rows(df, limit)
        return {"count": len(df), "top": rows}, []

    def get_zone(self, inp):
        if inp.get("gh7"):
            i = self.svc.by_gh7.get(inp["gh7"])
            if i is None:
                return {"error": f"zone {inp['gh7']} not found"}, []
            row = self.svc._row(i)
        elif inp.get("lat") is not None and inp.get("lon") is not None:
            row = self.svc.score(float(inp["lat"]), float(inp["lon"]))
        else:
            return {"error": "need gh7 or lat/lon"}, []
        keep = {k: row[k] for k in ("gh7", "impact", "rank", "tier3_share", "heavy_share") if k in row}
        return keep, [{"type": "focusZone", "gh7": row.get("gh7"), "lat": row.get("lat"), "lon": row.get("lon")}]

    def make_patrol_plan(self, inp):
        from api.patrol import build_plan
        units = max(1, min(int(inp.get("units", 3)), 4))
        topk = min(int(inp.get("topk", 15)), 25)
        df = self.svc.df
        near = inp.get("near")
        if near:
            df = self._near_filter(df[df["ranked"]], near)
            if len(df) < units:
                df = self.svc.df  # not enough local zones; fall back to citywide
        plan = build_plan(df, self.mappls, units=units, topk=topk, stations=self.stations)
        summary = {"units": len(plan["units"]),
                   "drive_mins": [u["drive_time_min"] for u in plan["units"]],
                   "zones_per_unit": [u["n_zones"] for u in plan["units"]],
                   "routing": plan["units"][0]["routing"] if plan["units"] else "n/a"}
        actions = [{"type": "setPersona", "persona": "btp"}, {"type": "setMode", "mode": "patrol"},
                   {"type": "showPatrolPlan", "plan": plan}]
        return summary, actions

    def analyze_route(self, inp):
        from api.logistics import impedance
        o, d = inp.get("origin"), inp.get("dest")
        if not (o and d):
            return {"error": "need origin and dest {lat,lng}"}, []
        wps = [{"lat": o["lat"], "lng": o.get("lng", o.get("lon"))},
               {"lat": d["lat"], "lng": d.get("lng", d.get("lon"))}]
        route = impedance(wps, self.svc.df, self.rcp, self.mappls, min_impact=inp.get("min_impact", 80))
        summary = {"total_delay_min": route["impedance_delay_mins"], "sla_risk": route["sla_risk"],
                   "recoverable_min": route["minutes_saved_by_detour"], "n_chokes": route["n_affected"],
                   "worst_gh7": (route.get("worst_choke") or {}).get("gh7")}
        actions = [{"type": "setPersona", "persona": "logistics"}, {"type": "showRoute", "route": route}]
        return summary, actions

    def set_map_view(self, inp):
        actions = []
        shown = None
        if inp.get("show_all") is not None:
            actions.append({"type": "setFilter", "show_all": bool(inp["show_all"])})
        if inp.get("min_impact") is not None:
            mi = int(inp["min_impact"])
            actions.append({"type": "setFilter", "show_all": False, "min_impact": mi})
            # count over ALL scored cells, matching exactly what the map then displays
            shown = int((self.svc.df["impact"] >= mi).sum())
        if inp.get("focus_gh7"):
            i = self.svc.by_gh7.get(inp["focus_gh7"])
            if i is not None:
                r = self.svc._row(i)
                actions.append({"type": "focusZone", "gh7": r["gh7"], "lat": r["lat"], "lon": r["lon"]})
        if inp.get("persona"):
            actions.append({"type": "setPersona", "persona": inp["persona"]})
        if inp.get("mode"):
            actions.append({"type": "setMode", "mode": inp["mode"]})
        if inp.get("stations") is not None:
            actions.append({"type": "toggleStations", "on": bool(inp["stations"])})
        summary = {"ok": True, "applied": len(actions)}
        if shown is not None:
            summary["zones_shown_on_map"] = shown
        return summary, actions

    def find_blindspots(self, inp):
        limit = min(int(inp.get("limit", 8)), 10)
        rows = []
        for f in self.blind[:limit]:
            p = f.get("properties", {})
            rows.append({"gh7": p.get("gh7"), "predicted_impact": p.get("predicted_impact"),
                         "gap": p.get("blind_gap"), "infraction": p.get("primary_infraction_type")})
        return {"count": len(self.blind), "top": rows}, []

    def dispatch(self, name, inp):
        fn = getattr(self, name, None)
        if not fn:
            return {"error": f"unknown tool {name}"}, []
        return fn(inp)


TOOLS = [
    {"name": "geocode", "description": "Resolve a Bengaluru place/area name to lat/lon. Call this before any spatial action that takes coordinates.",
     "input_schema": {"type": "object", "properties": {"place": {"type": "string"}}, "required": ["place"]}},
    {"name": "query_hotspots", "description": "List the highest congestion-impact zones. Optionally filter by min_impact (0-100) and/or an area via near{lat,lon,radius_km}.",
     "input_schema": {"type": "object", "properties": {"min_impact": {"type": "number"}, "limit": {"type": "integer"},
        "near": {"type": "object", "properties": {"lat": {"type": "number"}, "lon": {"type": "number"}, "radius_km": {"type": "number"}}}}}},
    {"name": "get_zone", "description": "Get one zone's impact details by gh7 geohash or by lat/lon. Focuses the map on it.",
     "input_schema": {"type": "object", "properties": {"gh7": {"type": "string"}, "lat": {"type": "number"}, "lon": {"type": "number"}}}},
    {"name": "make_patrol_plan", "description": "Build an optimised patrol plan over the top impact zones. units 1-4, topk zones, optional near{lat,lon,radius_km} to focus an area. Renders on the map.",
     "input_schema": {"type": "object", "properties": {"units": {"type": "integer"}, "topk": {"type": "integer"},
        "near": {"type": "object", "properties": {"lat": {"type": "number"}, "lon": {"type": "number"}, "radius_km": {"type": "number"}}}}}},
    {"name": "analyze_route", "description": "Analyze a delivery route for parking-induced delay and a reroute. origin/dest are {lat,lng}. Renders on the map.",
     "input_schema": {"type": "object", "properties": {
        "origin": {"type": "object", "properties": {"lat": {"type": "number"}, "lng": {"type": "number"}}},
        "dest": {"type": "object", "properties": {"lat": {"type": "number"}, "lng": {"type": "number"}}}}, "required": ["origin", "dest"]}},
    {"name": "set_map_view", "description": "Change the map view: show_all (bool), min_impact (filter >=N), focus_gh7, persona (btp|logistics), mode (hotspots|patrol|whatif|blind), stations (bool).",
     "input_schema": {"type": "object", "properties": {"show_all": {"type": "boolean"}, "min_impact": {"type": "integer"},
        "focus_gh7": {"type": "string"}, "persona": {"type": "string"}, "mode": {"type": "string"}, "stations": {"type": "boolean"}}}},
    {"name": "find_blindspots", "description": "List under-enforced zones: high impact-character but low current enforcement.",
     "input_schema": {"type": "object", "properties": {"limit": {"type": "integer"}}}},
]
