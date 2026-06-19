import pandas as pd
from api.logistics import impedance, _sla
class FakeMappls:
    def route(self, coords):
        return {"geometry":[[c[1],c[0]] for c in coords],"duration_s":120,"distance_m":600,"source":"live"}
def _df():
    return pd.DataFrame({"gh7":["a","b"],"lat":[12.970,12.980],"lon":[77.590,77.600],
        "impact":[99.0,95.0],"rank":[1,2],"n":[80,70],"tier3_share":[0.8,0.2],
        "heavy_share":[0.3,0.0],"ranked":[True,True]})
def test_impedance_basic():
    r=impedance([{"lat":12.970,"lng":77.590},{"lat":12.980,"lng":77.600}], _df(), {"a":7.0}, FakeMappls())
    assert r["n_affected"]>=1 and r["impedance_delay_mins"]>0
    assert r["sla_risk"] in ("Low","Medium","Critical")
    assert r["detour_route"] is not None and len(r["detour_route"]["geometry"])>=2
def test_impedance_no_hotspots_far_away():
    r=impedance([{"lat":13.30,"lng":77.80},{"lat":13.31,"lng":77.81}], _df(), {}, FakeMappls())
    assert r["n_affected"]==0 and r["impedance_delay_mins"]==0 and r["sla_risk"]=="Low"
def test_sla_bands():
    assert _sla(2)=="Low" and _sla(8)=="Medium" and _sla(20)=="Critical"
