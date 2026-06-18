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
