from api.mappls import MapplsClient
def client(tmp_path, fetch): return MapplsClient(cache_dir=str(tmp_path), key="K", fetcher=fetch, breaker_fails=2, cooldown=999)
def test_live_then_cache(tmp_path):
    calls={"n":0}
    def f(lat,lng): calls["n"]+=1; return {"street":"Grant Road","locality":"GN"}
    c=client(tmp_path,f)
    a=c.revgeocode(12.97,77.59); assert a["source"]=="live" and a["street"]=="Grant Road"
    b=c.revgeocode(12.97,77.59); assert b["source"]=="cache" and calls["n"]==1
def test_failure_falls_back(tmp_path):
    def f(lat,lng): raise TimeoutError("down")
    c=client(tmp_path,f); r=c.revgeocode(12.97,77.59)
    assert r["source"]=="fallback" and "error" not in r
def test_circuit_opens(tmp_path):
    n={"n":0}
    def f(lat,lng): n["n"]+=1; raise TimeoutError("down")
    c=client(tmp_path,f)
    for i in range(5): c.revgeocode(12.97+i*0.001,77.59)
    assert n["n"]<=2
    assert c.status()=="down"
