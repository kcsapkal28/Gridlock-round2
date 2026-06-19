# Targeted-Enforcement Features (A+B+C) — Design Spec

**Date:** 2026-06-18 · **Builds on:** existing BTP console, `cell_scores.parquet`, `rcp.csv`,
intrinsic model `fe_out/model_impact.txt`, FastAPI (`api/`), static bundle, `MapplsClient`.
**Compliance (ADR-007):** native data + mapping-infrastructure APIs only (Distance Matrix, Routing,
Geocoding). No Places/Nearby/Live-Traffic/Weather/Demographics.

## Goal
Complete the problem statement's "reactive patrol → targeted, systematic, proactive enforcement" arc with
three additions to the BTP Command console: **A) Patrol Route Optimizer**, **B) Enforcement What-If
Simulator**, **C) Under-Enforced Blind-Spot Finder**.

## Console integration
A mode switcher in the BTP sidebar: **Hotspots** (existing) · **Patrol Plan** · **What-If** · **Blind
Spots**. One shared `MapView`; each mode swaps the active Deck.gl layers + the sidebar panel. The
Flipkart-Logistics persona is unchanged.

---

## A. Patrol Route Optimizer

**Backend** — `GET /api/v1/triage/patrol-plan?units=N&topk=K` (N∈1..4 default 3, K default 15):
1. Take the top-K ranked cells by `impact` from `cell_scores`.
2. **Cluster** the K cells into N groups (k-means on lat/lon; deterministic seed). Each group = one unit.
3. For each group, fetch a drive-time matrix via `MapplsClient.distance_matrix_many(coords)` (one Mappls
   **Distance Matrix** call per group, cached by rounded-coord key), then order the stops by
   nearest-neighbour from the group centroid (greedy TSP).
4. For each ordered group, call `MapplsClient.route(coords)` (**Routing**, cached) for the path geometry.
5. **Response:** `{units:[{unit_id, color, stops:[{gh7,lat,lon,impact,rank}], route_geometry:[[lng,lat]],
   drive_time_min, total_impact, n_zones}], topk, generated_for:{units,topk}}`.
- **Fallbacks:** if Distance Matrix unavailable → order stops by haversine nearest-neighbour; if Routing
  unavailable → straight-line geometry between stops. Never 5xx; `degraded:true` flag when fallback used.
- **New `MapplsClient` method** `distance_matrix_many(coords)`: cached call to
  `/advancedmaps/v1/{key}/distance_matrix/driving/{lng,lat;...}`; returns the durations matrix; fallback
  returns haversine-based matrix.

**Frontend** — Patrol Plan panel: `units` slider (1–4), `topk` selector (10/15/20), "Generate plan"
button → calls the endpoint; renders N `PathLayer`s (distinct colors) + numbered `ScatterplotLayer` stops;
per-unit cards (zones, total impact, drive time). Map fits to the plan bounds.

---

## B. Enforcement What-If Simulator (client-only)

**Data:** the static `priority_table.json` + `rcp.geojson` (delay per gh7) already served. No new API.

**Panel:** zone multi-select (click cells on map OR "top-N" preset buttons 5/10/15). Live readout:
- `delay_relieved_min` = Σ RCP delay over selected zones (zones without an RCP value contribute a
  capacity-estimate fallback = `min(0.6, 0.10+0.35·tier3+0.20·heavy)·6`).
- `tier3_removed_pct` = Σ tier3_count(selected) / Σ tier3_count(all ranked).
- `heavy_addressed`, `citations_covered`.
- **Marginal-value curve:** a small inline SVG sparkline of cumulative delay-relieved vs zones-cleared
  (top-ranked first) showing diminishing returns.

**Map:** selected zones highlighted (amber ring); others dimmed. Selection state lives in the React app.

---

## C. Under-Enforced Blind-Spot Finder

**Offline compute** — `fe/cells/53_blindspots.py` (runs in pipeline / local):
1. Load `cell_features_full` + intrinsic feature list (same as shipped model).
2. `predicted_impact = model_impact.txt.predict(intrinsic_features)` for **all** cells (not just ranked).
3. `coverage = percentile(n)` (citation volume) and `device_breadth = percentile(distinct_devices)`.
4. `blind_spot = predicted_impact_pctile ≥ 0.80 AND coverage_pctile ≤ 0.35` (high predicted impact,
   low observed enforcement). `blind_gap = predicted_impact_pctile − coverage_pctile`.
5. Write `fe_out/blindspots.geojson` (top ~80 by `blind_gap`): props `gh7, lat, lon, predicted_impact,
   n, distinct_devices, blind_gap, dominant_vehicle_class, primary_infraction_type`.

**Static bundle:** `api/artifacts.py` copies `blindspots.geojson` into the web bundle.

**Frontend** — Blind Spots panel: ranked list by `blind_gap` + a distinct map layer (hollow magenta
markers to read as "unverified/expected" vs solid hotspot markers). Copy frames them as *expected* impact
the current patrol pattern under-observes.

---

## Files
- Modify: `api/mappls.py` (+`distance_matrix_many`), `api/main.py` (+`/triage/patrol-plan`),
  `api/schemas.py` (+PatrolPlan models), `api/artifacts.py` (+blindspots copy).
- Create: `api/patrol.py` (cluster + order + assemble plan), `api/tests/test_patrol.py`,
  `fe/cells/53_blindspots.py`.
- Frontend: `web/src/components/BTPSidebar.jsx` (mode switcher + 4 panels, split into
  `panels/HotspotsPanel.jsx`, `PatrolPanel.jsx`, `WhatIfPanel.jsx`, `BlindSpotsPanel.jsx`),
  `web/src/components/MapView.jsx` (mode-driven layers), `web/src/api.js` (+patrolPlan, +loadStatic blindspots).

## Testing
- `test_patrol.py`: cluster returns N groups; plan has N units; fallback path (no Distance Matrix) still
  returns ordered stops + straight-line geometry; never raises. Mock Mappls (no live calls).
- `53_blindspots.py`: guard predicted_impact finite, blind_spot count > 0 and < all cells, geojson feature
  count matches.
- Frontend: build clean; screenshot each mode; B math verified against a hand sum.

## Non-goals
- No supervised re-training (reuse shipped intrinsic booster). No new spatial unit. No Snap-to-Road
  (blocked on free tier). Logistics persona unchanged.

## Open assumptions
- `ASSUMPTION:` k-means(N) on lat/lon is adequate clustering for ≤4 units over ≤20 zones (small, fast).
- `ASSUMPTION:` blind-spot thresholds (0.80 / 0.35) are demo-tuned; exposed as constants for adjustment.
