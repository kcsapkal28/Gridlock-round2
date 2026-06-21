# GridLock — Parking-Induced Congestion Intelligence for Bengaluru

> **Flipkart GridLock 2.0 · Round 2 prototype.** Detect illegal-parking hotspots from
> Bengaluru Traffic Police (BTP) citation data and **quantify their impact on traffic flow**,
> so enforcement can be targeted by *congestion impact* instead of raw ticket volume.

GridLock turns a single anonymised BTP citation log (~293k clean records) into a
**Congestion-Impact Score (0–100) for every ~150 m zone** in the city, and exposes it
through a dual-persona operations console. Everything is engineered **natively** from the
provided schema — no external datasets — with MapMyIndia used only as an optional
mapping-infrastructure enrichment seam.

---

## The core idea: volume ≠ impact

A count-based heatmap just re-finds the busiest streets. The interesting signal — and the
one that helps BTP prioritise — is **where a few violations choke a carriageway**:
heavy/commercial vehicles, main-road/junction blocking, freight choke points. GridLock is
built around separating *impact* from *volume*.

`Reported in fe/findings/ (spatial GroupKFold validation):` for **detecting** impact
hotspots, ticket **volume alone scores ROC-AUC ≈ 0.59 (a coin flip)**, while a model using
zone *character* (severity mix, heavy-vehicle share, road context) reaches **≈ 0.85**. That
gap is the product thesis.

---

## Features

### 1. Congestion-Impact Score (the analytical core)
- **Unit:** geohash-7 cells (~153 m). Built on `is_valid` citations only (excludes
  rejected/duplicate). ~243k rows → **5,492 scored zones**, **792 ranked** (n ≥ 50),
  **313 statistically significant** (Getis-Ord Gi\*, p < 0.05).
- **Per-ticket impact intensity** = carriageway-severity tier weight `{0:0, 1:0.5, 2:1, 3:6}`
  × vehicle multiplier `{heavy 2.0, commercial 1.3, else 1.0}` — so lane-blocking and heavy
  vehicles dominate, correcting the "every ticket is ≥ Tier-2" floor that makes plain counts
  ≈ volume.
- **Ensemble engine** = `blend(0.75 · Gi*-significance, 0.25 · impact-character)`, with PCA
  and a hand composite kept as concordance cross-checks. Rate features are
  empirical-Bayes-smoothed so small cells aren't over-trusted.
- **Validated** by temporal stability (Spearman ≈ 0.78 across the enforcement window) and
  face validity (top-50 zones over-concentrate Tier-3 blocking ~3.1×). Full numbers:
  [`fe/findings/FE_REPORT.md`](fe/findings/FE_REPORT.md).

### 2. BTP Command Console (enforcement persona)
Prioritise patrols by impact, not volume. Deck.gl impact choropleth + ranked zone list,
with four operational modes:
- **Hotspots** — impact-ranked zones with decomposition (Tier-3 %, heavy %, dominant vehicle / infraction).
- **Patrol** — multi-unit patrol-plan optimiser (k-means cluster → nearest-neighbour order → MapMyIndia routes).
- **What-If** — explore the impact surface and thresholds.
- **Blind-spot** — zones high on impact-character but low on coverage (enforcement gaps patrol misses).

The map has an **impact-threshold filter** (show all zones, or only those with impact ≥ a
chosen 0–100 cut-off) and an optional **police-station overlay** for geographic reference.

### 3. Flipkart Logistics Resiliency (delivery persona)
Detect parking friction on a delivery route, quantify SLA delay, and reroute around choke
points using the impedance loop (MapMyIndia Routing detour cost). Route metrics + choke-point list.

### 4. Supervised models (optional live scoring)
LightGBM **impact regressor** and **hotspot detector**, validated with spatial GroupKFold
(grouped by gh5 so nearby cells don't leak across folds). Serve fresh `lat/lon` points via
the API. Model details: [`fe/findings/MODEL_CARD.md`](fe/findings/MODEL_CARD.md).

### 5. AI Copilot (Claude, tightly integrated)
Claude is woven into the console as a reasoning layer — not a chat bubble:
- **Command bar (⌘K):** natural-language operator that *drives the app* via tool-use —
  "plan 3 patrols around HSR", "show only zones above 90", "analyze the Whitefield run".
  The model calls our own endpoints and the map/sidebar react.
- **AI enforcement brief:** auto-generated, grounded priority/deploy/watch brief.
- **Explain & recommend:** an inline "AI read" on any selected zone or analyzed route.
- **Insights:** proactive, data-derived flags (e.g. under-counted high-impact zones).

It is **grounded** (answers only from our tool results — no external data, competition-safe),
runs the agentic loop **server-side** with large artifacts kept out of model context, and
**degrades to "offline"** if the LLM backend isn't running. Runs through a local Claude proxy
(see setup); the API path is `/api/v1/ai/*`.

---

## Architecture

```
BTP citation CSV (298,450 rows)
  │  EDA: clean (dedup + is_valid + parse JSON arrays) ............ eda/cells, gridlock_eda.ipynb
  ▼
cleaned.parquet (293,070 rows) → severity (max_sev, sev_sum)
  │  FE: geohash-7 aggregate + EB smoothing + spatial-lag + KDE ... fe/cells, gridlock_fe.ipynb
  ▼  Getis-Ord Gi* + PCA + ensemble blend
cell_scores.parquet (5,492 cells; 792 ranked)
  ├─► priority_table.csv, cells.geojson, rollups, impact_map.html
  ├─► model_impact.txt / model_detect.txt (LightGBM boosters)
  └─► MapMyIndia enrich (top-50, cached) → top_enriched.{csv,geojson}
        │
        ▼
   FastAPI backend (api/) ──serves──► React + Deck.gl frontend (web/)
   static bundle + live scoring + patrol-plan + impedance loop
```

Full data inventory: [`fe/findings/DATAFLOW_AND_FRONTEND.md`](fe/findings/DATAFLOW_AND_FRONTEND.md).

### Repository layout
| Path | What it is |
|------|-----------|
| `eda/` | Verification-first EDA — cells, findings, data dictionary, severity taxonomy |
| `fe/` | Feature-engineering + scoring pipeline (`cells/`), `scorelib.py`, committed artifacts, model cards |
| `api/` | FastAPI backend — scoring, patrol optimiser, logistics impedance, MapMyIndia client, tests |
| `web/` | Vite + React + Deck.gl + MapLibre frontend (dual-persona console) |
| `eda/findings/`, `fe/findings/` | Methodology, data dictionary, severity taxonomy, model cards |
| `gridlock_eda.ipynb`, `gridlock_fe.ipynb` | Canonical reproducible notebooks (run on Kaggle) |
| `run_local.py` | Run the EDA/FE cells locally instead of on Kaggle |
| `mapmyindia_enrich.py`, `rcp.py` | MapMyIndia capacity enrichment & routing-cost-penalty delay loop |

---

## Tech stack
- **Backend:** FastAPI · Uvicorn · Pydantic · httpx (see [`requirements-api.txt`](requirements-api.txt))
- **Frontend:** Vite · React · Deck.gl · MapLibre GL · react-map-gl (Carto dark base)
- **Pipeline (notebooks):** Python 3.12 · pandas · numpy · scikit-learn · LightGBM · folium · geohash
- **Mapping APIs:** MapMyIndia (MapmyIndia/Mappls) — Routing, Distance Matrix, (reverse-)Geocoding only

---

## Setup & run

### 0. Prerequisites
- Python 3.12+, Node 18+.
- The organiser dataset `jan to may police violation_anonymized791b166.csv` placed at the repo
  root. **It is gitignored and not in this repo** (organiser data — not redistributed).

### 1. Runtime artifacts (model + scored cells)
**Already in the repo — nothing to do.** The scored cells, LightGBM model, geojson layers
(`fe_work/cell_scores.parquet`, `fe_work/fe_out/*`) and the prebuilt frontend bundle
(`web/public/data/*`) are committed, so a fresh clone runs with zero extra steps.

<details><summary>Optional: regenerate the artifacts from the dataset</summary>

Needs the organiser CSV at the repo root:
```bash
python run_local.py fe/cells/*.py    # → fe_work/cell_scores.parquet + fe_work/fe_out/*
python mapmyindia_enrich.py 50       # optional MapMyIndia capacity layer (cached)
```
…or run `gridlock_eda.ipynb` → `gridlock_fe.ipynb` on Kaggle. Output inventory:
[`fe/findings/DATAFLOW_AND_FRONTEND.md`](fe/findings/DATAFLOW_AND_FRONTEND.md).
A `fetch_assets.py` Drive-download fallback also exists (see `.assets_url.example`).
</details>

### 2. Backend (FastAPI)
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-api.txt
uvicorn api.main:app --port 8011        # 8011 = the port the frontend dev-proxy expects
```
Health check: `curl localhost:8011/api/v1/health`. The backend reads `SCORES_PARQUET`
(default `fe_work/cell_scores.parquet`) and the impact model from step 1; configurable via
env vars in [`api/config.py`](api/config.py). MapMyIndia key (optional) goes in `.mappls_secrets`.

### 3. Frontend (Vite + React)
```bash
cd web
npm install
npm run dev                              # http://localhost:5173  (proxies /api → :8011)
```

### 4. AI Copilot (optional)
The copilot calls Claude through a local OpenAI/Anthropic proxy. Without it the app runs
normally and the AI surfaces show "offline".
```bash
# in the claude-openai proxy repo (Claude CLI must be logged in):
bash start.sh -p 4000                    # exposes :4001 Anthropic-native passthrough
```
Backend config (env, defaults in `api/config.py`): `AI_BASE_URL=http://localhost:4001`,
`AI_MODEL=claude-sonnet-4-6`, `AI_ENABLED=1`. The grounded agentic loop runs server-side.

### 5. Tests
```bash
pytest api/tests -q                      # 38 tests: scoring, patrol, logistics, mappls, AI tools + loop
```

---

## API endpoints (`api/main.py`, `api/ai/`)
| Method | Path | Purpose |
|--------|------|---------|
| GET  | `/api/v1/health` | Service + model + MapMyIndia status |
| POST | `/api/v1/score` | Impact score for a `{lat, lon}` |
| GET  | `/api/v1/zones/{gh7}` | One zone's full record |
| GET  | `/api/v1/triage/hotspots` | Impact-ranked hotspots as GeoJSON (`min_impact`, `limit`) |
| GET  | `/api/v1/triage/patrol-plan` | Optimised multi-unit patrol plan (`units`, `topk`) |
| POST | `/api/v1/logistics/impedance-loop` | Route choke-point detection + SLA-delay + reroute |
| GET  | `/api/v1/mappls/revgeocode` | Reverse geocode (MapMyIndia passthrough, cached) |
| GET  | `/api/v1/ai/health` | Copilot availability |
| POST | `/api/v1/ai/command` | NL operator — agentic, returns `{reply, ui_actions}` |
| GET  | `/api/v1/ai/brief` | Auto enforcement brief |
| POST | `/api/v1/ai/explain` | "AI read" for a zone (`{gh7}`) or route (`{route_summary}`) |
| GET  | `/api/v1/ai/insights` | Proactive data-derived insights |

---

## Competition compliance
- **No external datasets.** Every feature is engineered natively from the provided BTP schema.
- **MapMyIndia = mapping-infrastructure APIs only** (Routing, Distance Matrix, Geocoding /
  reverse-geocoding). Knowledge-enrichment APIs (Places/Nearby, Live Traffic, Weather,
  Demographics) are **not** used.
- The impact score is **explainable end to end** — the formula is documented and defensible,
  not a black box.

## Honest limitations
- There is **no ground-truth traffic-flow label** in the data, so the Congestion-Impact Score
  is a **defensible proxy**, not a measured congestion outcome.
- The score reflects *enforcement-observed* illegal parking; **citation timestamps measure
  when BTP enforces, not when congestion happens** (3–9 PM is a systemic data gap), so
  hour-of-day is deliberately excluded as a congestion-timing signal.
- Enforcement is concentrated (device Gini ≈ 0.79); headline hotspots are device-breadth-robust,
  but the long tail carries patrol bias. Full caveats: [`eda/findings/EDA_REPORT.md`](eda/findings/EDA_REPORT.md).

## Documentation map
- **Product:** [`PRODUCT.md`](PRODUCT.md) · **Design:** [`DESIGN.md`](DESIGN.md) · **User guide:** [`USER_GUIDE.md`](USER_GUIDE.md)
- **Data facts & dictionary:** [`eda/findings/DATA_DICTIONARY.md`](eda/findings/DATA_DICTIONARY.md)
- **EDA:** [`eda/findings/EDA_REPORT.md`](eda/findings/EDA_REPORT.md) · evidence log [`eda/findings/FINDINGS.md`](eda/findings/FINDINGS.md)
- **Scoring method & validation:** [`fe/findings/FE_REPORT.md`](fe/findings/FE_REPORT.md), [`fe/findings/MODEL_CARD.md`](fe/findings/MODEL_CARD.md)
- **Dataflow:** [`fe/findings/DATAFLOW_AND_FRONTEND.md`](fe/findings/DATAFLOW_AND_FRONTEND.md)
