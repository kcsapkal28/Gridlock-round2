from api.geo import encode_gh7, haversine_km, nearest_idx
def test_encode_gh7_len():
    assert len(encode_gh7(12.9716,77.5946))==7
def test_haversine_zero():
    assert haversine_km(12.97,77.59,12.97,77.59)==0
def test_haversine_known():
    d=haversine_km(12.97,77.59,12.98,77.59); assert 1.0<d<1.3
def test_nearest_idx():
    lats=[12.90,12.97,13.00]; lons=[77.50,77.59,77.60]
    assert nearest_idx(12.971,77.591,lats,lons)==1
