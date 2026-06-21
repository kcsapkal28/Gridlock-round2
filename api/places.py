"""Native Bengaluru gazetteer + a forgiving place-name resolver.

This is *mapping-infrastructure* (geocoding-style), not external knowledge enrichment:
it maps a free-typed area name to an approximate centroid so the UI can build a route or
focus the map. Matching is intentionally tolerant — exact, substring, token-overlap and
fuzzy (edit-distance) — so minor spelling mistakes and abbreviations still resolve.

Coordinates are approximate locality centroids (general geographic knowledge), used only to
seed routing/geocoding; the impact model never depends on them.
"""
import re
from difflib import SequenceMatcher

# Well-known Bengaluru localities (approx. centroids). Keys are canonical lowercase names.
AREAS = {
    "koramangala": (12.935, 77.622), "hsr layout": (12.911, 77.647),
    "whitefield": (12.970, 77.750), "indiranagar": (12.971, 77.641),
    "marathahalli": (12.956, 77.701), "electronic city": (12.842, 77.660),
    "hebbal": (13.035, 77.597), "city market": (12.964, 77.578),
    "majestic": (12.977, 77.572), "jayanagar": (12.930, 77.583),
    "mg road": (12.975, 77.606), "kr puram": (13.008, 77.696),
    "bellandur": (12.926, 77.676), "banashankari": (12.925, 77.546),
    "yeshwanthpur": (13.028, 77.550), "malleshwaram": (13.003, 77.569),
    "btm layout": (12.916, 77.610), "sarjapur": (12.905, 77.700),
    "silk board": (12.917, 77.622), "jp nagar": (12.910, 77.585),
    "rajajinagar": (12.991, 77.555), "vijayanagar": (12.972, 77.538),
    "basavanagudi": (12.941, 77.575), "shivajinagar": (12.985, 77.605),
    "ulsoor": (12.981, 77.622), "domlur": (12.961, 77.638),
    "ejipura": (12.940, 77.628), "wilson garden": (12.949, 77.598),
    "frazer town": (12.998, 77.614), "cox town": (13.000, 77.622),
    "banaswadi": (13.014, 77.651), "ramamurthy nagar": (13.018, 77.677),
    "kalyan nagar": (13.024, 77.640), "hennur": (13.040, 77.640),
    "kammanahalli": (13.018, 77.638), "horamavu": (13.030, 77.660),
    "cv raman nagar": (12.985, 77.663), "kr pura": (13.008, 77.696),
    "krishnarajapuram": (13.008, 77.696), "tin factory": (13.000, 77.668),
    "mahadevapura": (12.991, 77.689), "kadugodi": (12.992, 77.760),
    "varthur": (12.940, 77.745), "panathur": (12.935, 77.696),
    "kr market": (12.964, 77.578), "chickpet": (12.968, 77.580),
    "yelahanka": (13.100, 77.596), "rt nagar": (13.022, 77.595),
    "sanjaynagar": (13.035, 77.575), "sahakarnagar": (13.060, 77.580),
    "jalahalli": (13.045, 77.545), "peenya": (13.030, 77.520),
    "nagarbhavi": (12.960, 77.510), "kengeri": (12.910, 77.485),
    "rr nagar": (12.927, 77.520), "rajarajeshwari nagar": (12.927, 77.520),
    "uttarahalli": (12.905, 77.545), "kanakapura road": (12.890, 77.560),
    "bannerghatta road": (12.890, 77.600), "btm": (12.916, 77.610),
    "hsr": (12.911, 77.647), "ecity": (12.842, 77.660),
    "electronics city": (12.842, 77.660), "kundalahalli": (12.965, 77.715),
    "brookefield": (12.965, 77.717), "itpl": (12.985, 77.736),
    "hoodi": (12.992, 77.715), "graphite india": (12.998, 77.685),
    "old airport road": (12.960, 77.660), "airport road": (12.960, 77.660),
    "outer ring road": (12.935, 77.690), "orr": (12.935, 77.690),
    "hosur road": (12.890, 77.640), "tumkur road": (13.030, 77.520),
    "old madras road": (13.000, 77.660), "sarjapur road": (12.920, 77.690),
    "richmond town": (12.962, 77.600), "shanthi nagar": (12.957, 77.595),
    "lalbagh": (12.950, 77.585), "cubbon park": (12.976, 77.592),
    "vidhana soudha": (12.979, 77.591), "race course road": (12.985, 77.585),
    "seshadripuram": (12.994, 77.575), "okalipuram": (12.985, 77.560),
    "magadi road": (12.978, 77.545), "kammagondanahalli": (13.020, 77.510),
    "nagawara": (13.045, 77.620), "thanisandra": (13.060, 77.630),
    "manyata tech park": (13.045, 77.620), "hennur road": (13.035, 77.645),
    "kaggadasapura": (12.985, 77.680), "vimanapura": (12.965, 77.665),
    "jeevan bima nagar": (12.961, 77.659), "new tippasandra": (12.975, 77.660),
    "halasuru": (12.981, 77.622), "lingarajapuram": (13.010, 77.625),
    "baiyappanahalli": (12.991, 77.650), "byappanahalli": (12.991, 77.650),
    "vasanth nagar": (12.990, 77.592), "infantry road": (12.983, 77.600),
    "commercial street": (12.983, 77.609), "brigade road": (12.971, 77.607),
    "church street": (12.975, 77.606), "double road": (12.960, 77.596),
    "wind tunnel road": (12.960, 77.665),
}

# Common abbreviations / aliases → canonical key (helps short or noisy input).
ALIASES = {
    "blr": "majestic", "bangalore": "majestic", "bengaluru": "majestic",
    "kr puram": "krishnarajapuram", "krpuram": "krishnarajapuram",
    "ec": "electronic city", "e city": "electronic city",
    "jpnagar": "jp nagar", "rtnagar": "rt nagar",
    "mgroad": "mg road", "kadubeesanahalli": "bellandur",
    "outer ring road orr": "orr", "marthahalli": "marathahalli",
    "indra nagar": "indiranagar", "koramangla": "koramangala",
    "jaynagar": "jayanagar", "jaya nagar": "jayanagar", "whitfield": "whitefield",
    "bellandhur": "bellandur", "majestik": "majestic", "hsr layout": "hsr layout",
}

_WORD = re.compile(r"[a-z0-9]+")


def _norm(s):
    return " ".join(_WORD.findall((s or "").lower()))


def _tokens(s):
    return set(_WORD.findall((s or "").lower()))


def _ratio(a, b):
    return SequenceMatcher(None, a, b).ratio()


def build_gazetteer(stations=None):
    """Canonical name -> (lat, lon). Areas + aliases + any police-station names."""
    g = dict(AREAS)
    for alias, canon in ALIASES.items():
        if canon in g:
            g.setdefault(alias, g[canon])
    for s in (stations or []):
        if isinstance(s, dict) and s.get("name") and not str(s["name"]).lower().startswith("no "):
            g.setdefault(s["name"].lower(), (s["lat"], s.get("lon", s.get("lng"))))
    return g


def _hav(lat1, lon1, lat2, lon2):
    from math import radians, sin, cos, asin, sqrt
    p = radians
    a = sin((p(lat2) - p(lat1)) / 2) ** 2 + cos(p(lat1)) * cos(p(lat2)) * sin((p(lon2) - p(lon1)) / 2) ** 2
    return 2 * 6371.0 * asin(sqrt(a))


def nearest_area(lat, lon, gazetteer, stations=None):
    """Reverse: coordinate -> the nearest named locality, title-cased. Always returns a string."""
    best_name, best_d = None, 1e9
    for name, (la, lo) in gazetteer.items():
        if lo is None:
            continue
        d = _hav(lat, lon, la, lo)
        if d < best_d:
            best_name, best_d = name, d
    return (best_name or "area").title()


def nearest_station(lat, lon, stations):
    """Nearest usable police station to a point. Returns {name,lat,lon,dist_km} or None."""
    best, bd = None, 1e9
    for s in (stations or []):
        if not isinstance(s, dict) or not s.get("name") or str(s["name"]).lower().startswith("no "):
            continue
        lo = s.get("lon", s.get("lng"))
        d = _hav(lat, lon, s["lat"], lo)
        if d < bd:
            bd, best = d, {"name": s["name"], "lat": float(s["lat"]), "lon": float(lo), "dist_km": round(d, 2)}
    return best


def resolve(query, gazetteer, cutoff=0.55):
    """Forgiving resolver. Returns {name, lat, lon, score, method, candidates} or
    {error, candidates}. Order: exact → alias → substring → token-overlap → fuzzy."""
    q = _norm(query)
    if not q:
        return {"error": "empty query", "candidates": []}
    g = gazetteer

    def _canon(k):
        return ALIASES.get(k, k)

    def _result(k, score, method, cands):
        la, lo = g[k]
        return {"name": _canon(k), "lat": la, "lon": lo, "score": score, "method": method,
                "candidates": [_canon(c) for c in cands][:5]}

    # 1. exact
    if q in g:
        return _result(q, 1.0, "exact", [])

    # 2. substring — a real key contained in the query (len>=4, avoids short aliases like "ec"
    #    matching inside unrelated words) or the query contained in a key. Pick best by similarity.
    subs = [k for k in g if (len(k) >= 4 and k in q) or (len(q) >= 3 and q in k)]
    if subs:
        best = max(subs, key=lambda k: _ratio(q, k))
        return _result(best, 0.9, "substring", sorted(subs, key=lambda k: _ratio(q, k), reverse=True))

    # 3. token coverage — find a known place mentioned inside a noisy query ("around hsr tonight").
    #    Score = fraction of the KEY's tokens present in the query; ignore matches that rely only on
    #    generic tokens (road/nagar/...) so "park street" doesn't latch onto "church street".
    STOP = {"road", "nagar", "layout", "town", "street", "city", "market", "cross", "circle",
            "main", "new", "old", "park", "tech", "garden"}
    qt = _tokens(q)
    scored = []
    for k in g:
        kt = _tokens(k)
        if not kt:
            continue
        inter = qt & kt
        if inter and (inter - STOP):                    # at least one meaningful shared token
            scored.append((len(inter) / len(kt), len(k), k))
    if scored:
        scored.sort(reverse=True)                        # by coverage, then key length
        if scored[0][0] >= 0.5:
            return _result(scored[0][2], round(scored[0][0], 2), "tokens", [k for *_, k in scored[:5]])

    # 4. fuzzy edit-distance over keys (typos)
    fuzzy = sorted(((_ratio(q, k), k) for k in g), reverse=True)
    if fuzzy and fuzzy[0][0] >= cutoff:
        return _result(fuzzy[0][1], round(fuzzy[0][0], 2), "fuzzy", [k for _, k in fuzzy[:5]])

    return {"error": f"could not resolve '{query}'",
            "candidates": [_canon(k) for _, k in fuzzy[:5]]}
