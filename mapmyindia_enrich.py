# mapmyindia_enrich.py
"""Optional MapMyIndia (Mappls) enrichment. Runs only if MAPPLS_TOKEN is set.
Given cells.geojson, adds road_name per cell centroid via reverse-geocode.
The whole scoring pipeline works fully WITHOUT this module (native-core design)."""
import os, json, sys, time
import requests


def enrich(geojson_path="eda/eda_out/cells.geojson",
           out_path="eda/eda_out/cells_enriched.geojson", limit=None):
    token = os.environ.get("MAPPLS_TOKEN")
    if not token:
        print("MAPPLS_TOKEN not set -> skipping enrichment (pipeline unaffected).")
        return None
    gj = json.load(open(geojson_path))
    feats = gj["features"][:limit] if limit else gj["features"]
    for ft in feats:
        ring = ft["geometry"]["coordinates"][0][:4]
        cx = sum(p[0] for p in ring) / 4
        cy = sum(p[1] for p in ring) / 4
        try:
            r = requests.get(
                f"https://apis.mappls.com/advancedmaps/v1/{token}/rev_geocode",
                params={"lat": cy, "lng": cx}, timeout=10)
            j = r.json().get("results", [{}])[0]
            ft["properties"]["road_name"] = j.get("street") or j.get("formatted_address")
        except Exception:
            ft["properties"]["road_name"] = None
        time.sleep(0.05)
    json.dump(gj, open(out_path, "w"))
    print(f"enriched {len(feats)} features -> {out_path}")
    return out_path


if __name__ == "__main__":
    enrich(limit=int(sys.argv[1]) if len(sys.argv) > 1 else None)
