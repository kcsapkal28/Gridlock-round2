from api.roadclass import road_exposure, RoadClassifier
def test_exposure_keywords():
    assert road_exposure("Outer Ring Road")[0]==1.5
    assert road_exposure("80 Feet Main Road")[0]==1.35
    assert road_exposure("5th Cross")[0]==1.2
    assert road_exposure("Some Lane")[0]==1.0
def test_classifier_uses_geocode_when_snap_off():
    rc=RoadClassifier(snap_on=False, revgeocoder=lambda la,lo:{"street":"Outer Ring Road"})
    r=rc.classify(12.99,77.67)
    assert r["road_class"]=="arterial/highway" and r["exposure"]==1.5 and r["source"]=="geocode"
def test_classifier_unknown_on_empty():
    rc=RoadClassifier(snap_on=False, revgeocoder=lambda la,lo:{"street":""})
    r=rc.classify(0,0); assert r["exposure"]==1.0 and r["road_class"]=="local"
