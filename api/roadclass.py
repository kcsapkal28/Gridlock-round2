def road_exposure(street):
    s=(street or "").lower()
    if any(k in s for k in ["ring road","highway","nh-","national highway","flyover","trunk","outer ring"]):
        return 1.50,"arterial/highway"
    if "main road" in s: return 1.35,"main road"
    if any(k in s for k in ["cross","circle","junction"]): return 1.20,"cross/junction"
    return 1.00,"local"
class RoadClassifier:
    """Fallback chain: Snap-to-Road (if snap_on) -> geocode street-name heuristic -> local."""
    def __init__(self, snap_on=False, snapper=None, revgeocoder=None):
        self.snap_on=snap_on; self.snapper=snapper; self.revgeocoder=revgeocoder
    def classify(self, lat, lon):
        if self.snap_on and self.snapper:
            try:
                st=self.snapper(lat,lon)
                exp,rc=road_exposure(st); return {"road_class":rc,"exposure":exp,"source":"snap"}
            except Exception: pass
        st=""
        if self.revgeocoder:
            try: st=(self.revgeocoder(lat,lon) or {}).get("street","")
            except Exception: st=""
        exp,rc=road_exposure(st); return {"road_class":rc,"exposure":exp,"source":"geocode"}
