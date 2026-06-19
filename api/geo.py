import math, pygeohash as pgh
def encode_gh7(lat, lon): return pgh.encode(lat, lon, precision=7)
def haversine_km(lat1, lon1, lat2, lon2):
    R=6371.0; p=math.pi/180
    a=(math.sin((lat2-lat1)*p/2)**2 + math.cos(lat1*p)*math.cos(lat2*p)*math.sin((lon2-lon1)*p/2)**2)
    return 2*R*math.asin(math.sqrt(a))
def nearest_idx(lat, lon, lats, lons):
    best,bi=float("inf"),-1
    for i,(la,lo) in enumerate(zip(lats,lons)):
        d=haversine_km(lat,lon,la,lo)
        if d<best: best,bi=d,i
    return bi

def decode_polyline(s, precision=6):
    """Decode a Google/Mappls encoded polyline -> list of [lng,lat]. Mappls uses precision 6."""
    if not isinstance(s, str): return []
    coords=[]; idx=lat=lng=0; factor=10**precision
    while idx < len(s):
        for _unit in range(2):
            shift=result=0
            while True:
                b=ord(s[idx])-63; idx+=1
                result|=(b & 0x1f)<<shift; shift+=5
                if b < 0x20: break
            d=~(result>>1) if (result & 1) else (result>>1)
            if _unit==0: lat+=d
            else: lng+=d
        coords.append([lng/factor, lat/factor])
    return coords

def cells_near_path(waypoints, df, radius_km=0.20, limit=40):
    """Indices of df rows within radius_km of any waypoint (lat/lon cols)."""
    hit=set()
    lats=df["lat"].tolist(); lons=df["lon"].tolist()
    for w in waypoints:
        for i,(la,lo) in enumerate(zip(lats,lons)):
            if haversine_km(w["lat"], w["lng"], la, lo) <= radius_km:
                hit.add(i)
    return list(hit)[:limit] if limit else list(hit)
