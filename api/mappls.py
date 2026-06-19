import os, json, time
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
    def route(self, coords):
        """Routing via route_adv (mapping-infra). coords=[(lat,lng),...].
        Returns {geometry:[[lng,lat],...], duration_s, distance_m, source}. Fallback = straight line."""
        from api.geo import decode_polyline
        ck = "rt_" + "_".join(f"{a:.4f},{b:.4f}" for a,b in coords)
        cf = os.path.join(self.cache, ck + ".json")
        straight = {"geometry":[[b,a] for a,b in coords], "duration_s":None, "distance_m":None, "source":"fallback"}
        if os.path.exists(cf):
            d=json.load(open(cf)); d["source"]="cache"; return d
        if self.clock()<self.open_until:
            return straight
        try:
            import httpx
            cstr=";".join(f"{b},{a}" for a,b in coords)  # lng,lat
            r=httpx.get(f"https://apis.mappls.com/advancedmaps/v1/{self.key}/route_adv/driving/{cstr}",
                        params={"geometries":"polyline6","overview":"full"}, timeout=8)
            r.raise_for_status(); j=r.json(); rt=(j.get("routes") or [{}])[0]
            geom=decode_polyline(rt.get("geometry",""), precision=6)
            out={"geometry":geom or straight["geometry"], "duration_s":rt.get("duration"),
                 "distance_m":rt.get("distance"), "source":"live"}
            self.fails=0; json.dump(out, open(cf,"w")); return out
        except Exception:
            self.fails+=1
            if self.fails>=self.bf: self.open_until=self.clock()+self.cd
            return straight

    def distance_matrix_many(self, coords, _fail=False):
        """Durations matrix (seconds) for coords=[(lat,lng)...] via Distance Matrix.
        Fallback = haversine-time matrix (assume 20 km/h). _fail forces fallback (tests)."""
        from api.geo import haversine_km
        n=len(coords)
        def hav():
            return [[haversine_km(a[0],a[1],b[0],b[1])/20.0*3600.0 for b in coords] for a in coords]
        def ok(m):  # must be an n x n matrix
            return isinstance(m,list) and len(m)==n and all(isinstance(r,list) and len(r)==n for r in m)
        ck="dm_"+"_".join(f"{a:.4f},{b:.4f}" for a,b in coords)
        cf=os.path.join(self.cache, ck+".json")
        if os.path.exists(cf):
            m=json.load(open(cf)); return m if ok(m) else hav()
        if _fail or self.clock()<self.open_until:
            return hav()
        try:
            import httpx
            cstr=";".join(f"{b},{a}" for a,b in coords)
            r=httpx.get(f"https://apis.mappls.com/advancedmaps/v1/{self.key}/distance_matrix/driving/{cstr}",
                        timeout=8); r.raise_for_status()
            m=r.json()["results"]["durations"]; self.fails=0
            if not ok(m): return hav()
            json.dump(m, open(cf,"w")); return m
        except Exception:
            self.fails+=1
            if self.fails>=self.bf: self.open_until=self.clock()+self.cd
            return hav()

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
