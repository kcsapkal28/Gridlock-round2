# Frontend Communication Layer — API & Fallback Design Spec

**Date:** 2026-06-18 · **Depends on:** model artifacts in `fe_work/fe_out/` (`cell_scores.parquet`,
`cells.geojson`, `priority_table.csv`, `top_enriched.{csv,geojson}`, `kde_points.csv`,
`model_impact.txt`, `model_detect.txt`), `fe/scorelib.py`, `mapmyindia_enrich.py`.

## 1. Goal

Define the **communication contract and a robust, fallback-first API** between the model/data layer and the
(future) frontend — *before* any UI work. Priorities, in order: **clear protocol → robustness → live
features**. The frontend's core experience must work even if the backend or MapMyIndia is fully down.

## 2. Architecture (two layers)

1. **Static artifact store** — everything precomputed, served as immutable files (CDN/`/public`),
   cache-forever. The frontend's map/heatmap/priority-list read these directly; **no backend required**.
2. **Thin FastAPI gateway** — stateless, only the genuinely dynamic endpoints (live scoring, MapMyIndia
   proxy, health). Reuses existing Python code (`scorelib`, boosters, `pygeohash`, `cell_scores`).

```
Frontend (static SPA)
  ├─ static: cells.geojson, priority_table.json, rollup_gh6/gh5.json, kde_points.json,
  │          top_enriched.geojson, manifest.json     (works with backend DOWN)
  └─ dynamic (FastAPI /api/v1): /score, /mappls/*, /zones[/{gh7}], /health
```

**Stack:** FastAPI + Uvicorn (Python — matches model code), Pydantic schemas, `httpx` for async outbound.
**Runtime:** local-first (`uvicorn api.main:app`); cloud-portable via env config. **Auth:** none for the
local demo (documented; add API-key middleware later for cloud).

## 3. File structure (`api/` package — each unit independently testable)

- `api/main.py` — FastAPI app, route wiring, CORS, middleware (request-id, error handler), startup load.
- `api/schemas.py` — Pydantic request/response models (the typed contract).
- `api/scoring.py` — `ScoringService`: load `cell_scores` + boosters once; `score(lat,lon)` with fallback chain.
- `api/mappls.py` — `MapplsClient`: cached + rate-limited + circuit-broken proxy; token minting; reuses `.mappls_cache/`.
- `api/roadclass.py` — `road_class(lat,lon)` with a **fallback chain** (Snap-to-Road → Routing → geocoding
  street-name heuristic). Flag-gated + probe-activated (Snap-to-Road returns 412 on the current free-tier
  key, so it is OFF by default; the geocoding heuristic is the active path). Mapping-infra APIs only.
- `api/artifacts.py` — `build_static(out_dir)`: generate the static JSON bundle + `manifest.json` from `fe_work/fe_out/`.
- `api/config.py` — env-driven settings (paths, CORS origins, timeouts, breaker thresholds).
- `api/tests/` — pytest unit + contract tests (incl. forced-failure fallback tests).
- `web/public/` — destination for the static bundle.

## 4. Communication protocol (the contract)

- **REST/JSON**, versioned base **`/api/v1`**; **OpenAPI 3** auto-served at `/docs` and `/openapi.json`.
- **CORS** restricted to configured frontend origin(s).
- **`X-Request-ID`** response header (generated if absent); included in logs and error bodies.
- **`Cache-Control`:** static artifacts `max-age=31536000, immutable`; dynamic GETs `max-age=60`; `/score` `no-store`.
- **Uniform error envelope** for ALL non-2xx:
  `{"error": {"code": "STRING_CODE", "message": "human text", "request_id": "..."}}`
  with correct HTTP status (400 validation, 404 not-found, 429 rate-limited, 503 dependency-down).
- **Every dynamic response includes `source`** (`grid|model|nearest|live|cache|fallback`) and, where
  relevant, `degraded: bool` — the UI always knows data provenance.

### Endpoints

| Method · Path | Request | Response (success) |
|---|---|---|
| `GET /api/v1/health` | — | `{status:"ok", version, artifacts_version, model_loaded:bool, mappls:"live\|cached\|down"}` |
| `GET /api/v1/zones` | `?bbox=minLon,minLat,maxLon,maxLat&min_impact=&limit=` | `{count, zones:[ZoneSummary]}` (optional; static GeoJSON is default source) |
| `GET /api/v1/zones/{gh7}` | path gh7 | `ZoneDetail` or 404 |
| `POST /api/v1/score` | `{lat:float, lon:float}` | `ScoreResult` |
| `GET /api/v1/mappls/revgeocode` | `?lat=&lng=` | `{street, subLocality, locality, district, source}` |
| `GET /api/v1/mappls/token` | — | `{token:str\|null, expires_in:int, fallback_basemap:"carto"}` |

### Core schemas (Pydantic)

- `ScoreRequest{lat: float[-90,90], lon: float[-180,180]}`
- `ScoreResult{gh7, impact: float, rank: int|null, tier3_share, heavy_share, source: Literal["grid","model","nearest"], degraded: bool, nearest: list[ZoneSummary]}`
- `ZoneSummary{gh7, lat, lon, impact, rank, tier3_share, heavy_share}`
- `ZoneDetail = ZoneSummary + {n, sev_sum, commercial_share, gi_z, top_violations, top_vehicles, mappls_street?, road_class?, impact_capacity?}`
- `ErrorEnvelope{error:{code, message, request_id}}`

## 5. Fallback mechanisms (robustness core)

**Principle: every dynamic path has an ordered fallback chain and always returns something usable.**

- **`/score`** (`ScoringService.score`):
  1. geohash the point → **in-memory grid lookup** in `cell_scores` → `source:"grid"`.
  2. off-grid point → **LightGBM model inference** on derived features → `source:"model"`.
  3. model unavailable/error → **nearest ranked zone** by haversine → `source:"nearest", degraded:true`.
  Valid coordinates never produce a 5xx.
- **`/mappls/revgeocode`** (`MapplsClient`):
  1. **disk cache** (`.mappls_cache/{gh7|latlng}.json`) → `source:"cache"`.
  2. **live Mappls**, `timeout=5s`, `retries=1` → `source:"live"` (and cache it).
  3. failure/quota → cached-if-any, else **native locality from our data** → `source:"fallback"`.
- **Circuit breaker (Mappls):** after `BREAKER_FAILS` (default 5) consecutive failures, **open** for
  `BREAKER_COOLDOWN` (default 120s) — skip live calls, serve fallback directly. Half-open probe after
  cooldown. State exposed via `/health.mappls`.
- **`/mappls/token`:** OAuth token **cached server-side** (~24h), refreshed proactively at 90% TTL; if OAuth
  is down → `{token:null, fallback_basemap:"carto"}` so the frontend renders on **OSM/Carto tiles**.
- **Road-class enrichment** (`roadclass.road_class`): **Snap-to-Road** (if `ROADCLASS_SNAP=on` and a startup
  probe returns 200) → **Routing** road-name → **geocoding street-name heuristic** (`road_exposure`) →
  `road_class:"unknown", exposure:1.0`. Verified status: Snap-to-Road = 412 on free tier → chain starts at
  the geocoding heuristic today; no behavior change to the shipped `impact_capacity`.
- **Rate limiting:** token-bucket on `/mappls/*` (default 60/min) to protect the free tier; over-limit → 429
  with the error envelope.
- **Bounded everything:** 5s outbound timeouts, ≤1 retry, no unbounded waits.
- **Static-first guarantee:** the frontend's map/heatmap/priority list use **static artifacts**; backend
  outage degrades only live-scoring and live-Mappls, never the core view.
- **Startup readiness:** load model + `cell_scores` once; if a booster fails to load, `/score` degrades to
  lookup-only and `/health.model_loaded=false` (app still serves).

## 6. Static artifact generation

`api/artifacts.py build_static()` converts `fe_work/fe_out/` into a web bundle in `web/public/data/`:
- `cells.geojson` (copy), `priority_table.json`, `rollup_gh6.json`, `rollup_gh5.json`,
  `kde_points.json`, `top_enriched.geojson` (copy).
- `manifest.json`: `{generated_at, artifacts_version, files:[{name, sha256, bytes}], headline_stats}`.
- Frontend loads `manifest.json` first → knows versions/checksums → safe cache-busting.

## 7. Testing

- **Unit:** `ScoringService` (grid hit, off-grid→model, model-down→nearest); `MapplsClient`
  (cache hit, live success, timeout→fallback, breaker open/half-open); `road_exposure`.
- **Contract:** FastAPI `TestClient` per endpoint — happy path + each fallback (inject failures via
  monkeypatched httpx) + error-envelope shape + `source`/`degraded` flags.
- **Determinism:** fixed seeds; tests use a tiny fixture `cell_scores` slice, not the full parquet.
- **No live API calls in tests** — Mappls fully mocked (protects free tier).

## 7a. MapMyIndia rules compliance

This API uses **mapping-infrastructure APIs only**: `/mappls/revgeocode` = **Geocoding** (allowed);
`/mappls/token` = base-map **tiles/SDK** (mapping rendering, allowed), with Carto fallback. We use **no**
knowledge-enrichment APIs — **Places/Nearby, Live Traffic, Weather, Demographics are prohibited** and must
never be added to `api/mappls.py`. Road-class signals come from our own heuristic on geocoded street names
or Snap-to-Road/Routing (mapping-infra, fallback-chained, currently gated off — 412 on free-tier) — never a
places/attributes knowledge lookup. See ADR-007.

## 8. Non-goals (YAGNI)

- Auth/multi-tenant (local demo). DB/persistence (parquet + static files suffice). Real-time streaming.
- The frontend UI itself (separate spec). Writes/feedback endpoints. Lane-level capacity (free-tier limit).

## 9. Open assumptions (flagged)

- `ASSUMPTION:` single frontend origin for CORS (configurable). `ASSUMPTION:` off-grid live model scoring
  uses the *intrinsic* feature subset (spatial/neighbor features need a built grid; for a lone point we use
  cell-intrinsic features → the 0.85-AUC-class path, with `source:"model"`). `ASSUMPTION:` map SDK is Mappls
  with Carto fallback.
