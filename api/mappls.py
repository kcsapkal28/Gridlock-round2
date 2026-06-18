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
