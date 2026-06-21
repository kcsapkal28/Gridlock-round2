#!/usr/bin/env python3
"""Fetch GridLock runtime artifacts (scored cells, model, geojson layers) from a Google
Drive folder and place them where the API + frontend expect them, then build the web bundle.

These artifacts are too large / not appropriate for git, so they live on Drive. This script
makes a fresh clone runnable with one command.

URL resolution (first match wins):
  1. CLI arg:        python fetch_assets.py "<drive folder url>"
  2. env var:        GRIDLOCK_ASSETS_URL="<url>"  python fetch_assets.py
  3. file:           ./.assets_url   (one line; gitignored)

Usage:
  python fetch_assets.py                 # uses env var or .assets_url
  python fetch_assets.py "<folder url>"  # explicit
It is idempotent: already-present required files are not re-downloaded.
"""
import os
import sys
import glob
import shutil

CACHE = ".assets_cache"
FE_WORK = "fe_work"
FE_OUT = os.path.join(FE_WORK, "fe_out")
WEB_DATA = os.path.join("web", "public", "data")

# Drive filename -> destination path in the repo. The Drive folder may be flat or nested;
# files are matched by basename, so upload order/structure does not matter.
PLACEMENT = {
    "cell_scores.parquet":   os.path.join(FE_WORK, "cell_scores.parquet"),   # REQUIRED (backend scoring)
    "model_impact.txt":      os.path.join(FE_OUT, "model_impact.txt"),       # live ML /score (LightGBM)
    "model_detect.txt":      os.path.join(FE_OUT, "model_detect.txt"),       # optional detection model
    "cells.geojson":         os.path.join(FE_OUT, "cells.geojson"),          # REQUIRED (frontend heatmap)
    "rcp.geojson":           os.path.join(FE_OUT, "rcp.geojson"),            # REQUIRED (flow-impact layer)
    "blindspots.geojson":    os.path.join(FE_OUT, "blindspots.geojson"),     # REQUIRED (blind-spot layer)
    "top_enriched.geojson":  os.path.join(FE_OUT, "top_enriched.geojson"),   # enriched markers
    "rcp.csv":               os.path.join(FE_OUT, "rcp.csv"),                # measured logistics delays
    "kde_points.csv":        os.path.join(FE_OUT, "kde_points.csv"),         # severity surface
    "rollup_gh6.csv":        os.path.join(FE_OUT, "rollup_gh6.csv"),         # zoom aggregation
    "rollup_gh5.csv":        os.path.join(FE_OUT, "rollup_gh5.csv"),         # zoom aggregation
    "priority_table.csv":    os.path.join(FE_OUT, "priority_table.csv"),     # optional (top-100 table)
}
# Minimum set for the app to actually run (backend boot + core frontend layers).
REQUIRED = ["cell_scores.parquet", "cells.geojson", "rcp.geojson", "blindspots.geojson"]


def resolve_url():
    if len(sys.argv) > 1 and sys.argv[1].strip():
        return sys.argv[1].strip()
    if os.environ.get("GRIDLOCK_ASSETS_URL", "").strip():
        return os.environ["GRIDLOCK_ASSETS_URL"].strip()
    if os.path.exists(".assets_url"):
        for line in open(".assets_url"):
            line = line.strip()
            if line and not line.startswith("#"):
                return line
    return ""


def _have_required():
    return all(os.path.exists(PLACEMENT[n]) for n in REQUIRED)


def download(url):
    try:
        import gdown
    except ImportError:
        sys.exit("gdown is not installed. Run:  pip install -r requirements.txt")
    os.makedirs(CACHE, exist_ok=True)
    is_folder = ("/folders/" in url) or ("/drive/folders" in url)
    if is_folder:
        gdown.download_folder(url, output=CACHE, quiet=False, use_cookies=False)
    else:
        # single shared file/zip link
        gdown.download(url, output=os.path.join(CACHE, ""), quiet=False, fuzzy=True)


def place():
    """Copy every recognised file from the cache into its expected path."""
    found = {
        os.path.basename(p): p
        for p in glob.glob(os.path.join(CACHE, "**", "*"), recursive=True)
        if os.path.isfile(p)
    }
    placed = []
    for name, dest in PLACEMENT.items():
        if name in found:
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            shutil.copy(found[name], dest)
            placed.append(name)
    missing = [n for n in REQUIRED if not os.path.exists(PLACEMENT[n])]
    return placed, missing


def build_bundle():
    """Regenerate the frontend static bundle (web/public/data) from the fetched artifacts."""
    try:
        from api.artifacts import build_static
        from api.config import settings
        build_static(PLACEMENT["cell_scores.parquet"], FE_OUT, WEB_DATA, settings.VERSION)
        print(f"[fetch_assets] built frontend bundle -> {WEB_DATA}/")
        return True
    except Exception as e:  # noqa: BLE001 - non-fatal; backend can still serve API
        print(f"[fetch_assets] WARN: could not build web bundle ({e})")
        return False


def ensure_assets():
    """Make sure runtime artifacts exist; download from Drive if not. Returns True on success."""
    if _have_required():
        if not os.path.exists(os.path.join(WEB_DATA, "cells.geojson")):
            build_bundle()
        return True

    url = resolve_url()
    if not url:
        print("[fetch_assets] No Drive URL configured. Set GRIDLOCK_ASSETS_URL, pass it as an "
              "argument, or put the folder link in a one-line .assets_url file. "
              "See README 'Runtime artifacts'.")
        return False

    print(f"[fetch_assets] downloading artifacts from: {url}")
    download(url)
    placed, missing = place()
    print(f"[fetch_assets] placed {len(placed)} file(s): {', '.join(placed) or 'none'}")
    if missing:
        print(f"[fetch_assets] ERROR: missing REQUIRED file(s): {', '.join(missing)}. "
              "Check the Drive folder contents/sharing.")
        return False
    build_bundle()
    print("[fetch_assets] done.")
    return True


if __name__ == "__main__":
    sys.exit(0 if ensure_assets() else 1)
