# GridLock — User Guide

**Parking-induced congestion intelligence for Bengaluru.** This guide explains every
feature, what each control does, how to leverage it operationally, and how it is backed
by the data. It is written for two audiences: **BTP command staff** (targeted enforcement)
and **Flipkart logistics dispatchers** (protecting delivery SLAs).

> Numbers in this guide trace to the project's measured artifacts: the EDA/FE findings
> (`eda/findings/`, `fe/findings/`) and the live API. Where a metric comes from the
> validation reports rather than a fresh run, it is attributed inline.

---

## Table of contents
1. [What GridLock is](#1-what-gridlock-is)
2. [The core idea: volume ≠ impact](#2-the-core-idea-volume--impact)
3. [The Congestion-Impact Score](#3-the-congestion-impact-score)
4. [Personas & the interface](#4-personas--the-interface)
5. [BTP Command Console](#5-btp-command-console)
   - [5.1 Hotspots](#51-hotspots)
   - [5.2 Patrol plan](#52-patrol-plan)
   - [5.3 What-if](#53-what-if)
   - [5.4 Blind spots](#54-blind-spots)
6. [Flipkart Logistics: route resilience](#6-flipkart-logistics-route-resilience)
7. [Reading the map](#7-reading-the-map)
8. [Status bar: online vs static-only](#8-status-bar-online-vs-static-only)
9. [API reference](#9-api-reference)
10. [Setup & running](#10-setup--running)
11. [Data, methodology & honest limitations](#11-data-methodology--honest-limitations)
12. [Troubleshooting](#12-troubleshooting)
13. [Glossary](#13-glossary)

---

## 1. What GridLock is

GridLock turns a single anonymised Bengaluru Traffic Police (BTP) citation log
(**293,070 clean records**, Nov 2023 – Apr 2024) into a **Congestion-Impact Score (0–100)
for every ~150 m zone** in the city, then exposes it through a dual-persona operations
console. It is a decision-support prototype: it tells you *where illegal parking most
chokes traffic flow*, so enforcement and routing can be prioritised systematically rather
than reactively.

- **Data:** one organiser-provided citation log. **No external datasets** are used —
  every feature is engineered natively from the schema (a hard competition rule).
- **Mapping:** MapMyIndia is used **only** for mapping-infrastructure (routing, distance
  matrix, geocoding) — never for external knowledge layers.
- **Unit of analysis:** geohash-7 cells (~153 m squares).

---

## 2. The core idea: volume ≠ impact

A naïve heatmap of where the most tickets are issued just re-discovers the busiest
streets. The operationally useful question is different: **where do a few violations
actually block a moving lane?** That is what GridLock scores.

Evidence (from `fe/findings/`, spatial GroupKFold validation):

- For **detecting** impact hotspots, ticket **volume alone scores ROC-AUC ≈ 0.59** — barely
  better than a coin flip. A model using zone *character* (severity mix, heavy-vehicle
  share, road context) reaches **≈ 0.85**.
- Heavy/commercial vehicles dominate carriageway blocking: **BMTC/KSRTC buses are ~46%
  Tier-3** (lane-blocking) vs **scooters ~4%** — even though scooters are the volume leader.
- A tail of small zones is **near-100% Tier-3 yet ranks ~900th by volume** — invisible to
  count-based enforcement. Surfacing that tail is where the impact score earns its value.

This "volume ≠ impact" insight is the backbone of every feature below.

---

## 3. The Congestion-Impact Score

A single, explainable score (0–100) per geohash-7 cell. Method (from
`fe/findings/FE_REPORT.md`):

**Step 1 — per-ticket impact intensity.** Each violation is weighted by how much a
stationary vehicle obstructs moving traffic:

```
impact_intensity = severity_tier_weight × vehicle_multiplier
   severity_tier_weight : {Tier 0: 0, Tier 1: 0.5, Tier 2: 1, Tier 3: 6}
   vehicle_multiplier   : {heavy: 2.0, commercial: 1.3, else: 1.0}
```

Tier 3 = blocks a moving lane/intersection (main road, double parking, near crossing…);
Tier 2 = narrows the carriageway (wrong/no parking); Tier 1 = footpath; Tier 0 = document/
behaviour violations with no flow impact. (Full map: `eda/findings/SEVERITY_TAXONOMY.md`.)

**Step 2 — aggregate per cell**, on valid citations only (`is_valid`, 83% of rows;
excludes rejected/duplicate). Rate features (Tier-3 share, heavy share) are
**empirical-Bayes smoothed** (K=40) so small cells aren't over-trusted.

**Step 3 — ensemble engine:**

```
impact = blend( 0.75 · Getis-Ord Gi* significance , 0.25 · impact-character )
```

- **Gi\*** finds statistically significant clusters of high impact intensity (313 cells at
  p < 0.05).
- **Impact-character** = volume-independent percentile of Tier-3 share, heavy share, and
  road context (main-road / junction / circle keywords from the free-text address).
- PCA and a hand composite are kept as cross-checks, not shipped.

**Coverage:** ~243k valid citations → **5,492 scored zones**, of which **792 are "ranked"**
(n ≥ 50 citations — enough data to trust) and **313 are statistically significant**.

**Validation (reported in `fe/findings/`):** top-50 zones over-concentrate carriageway-
blocking ~3.1×; temporal stability Spearman ≈ 0.78; ranking survives the strict approved-
only subset (≈ 0.72). The supervised "full" detector reaches ROC-AUC ≈ 0.99 / impact R² ≈ 0.98.

**Per-zone fields you'll see in the UI:** `impact` (0–100), `rank`, `n` (citations),
`tier3_share`, `heavy_share`, `gi_z` (significance), plus dominant vehicle class and
primary infraction type.

---

## 4. Personas & the interface

The top bar has a **persona toggle**:

- **BTP Command** — prioritise enforcement by congestion impact. Four modes (Section 5).
- **Flipkart Logistics** — protect delivery SLAs by routing around parking friction (Section 6).

Top-right is a **status bar** (Section 8). The main area is a dark instrument-panel **map**
(Deck.gl + MapLibre, Carto dark base) with a left **sidebar** whose contents change per
persona/mode.

### The AI copilot (Claude, embedded)
Claude is woven into the console — not a separate chatbot:
- **Command bar** (top, press ⌘K): type a plain-English instruction and the copilot *operates
  the app* for you — e.g. "plan 3 patrols around HSR", "show only zones above 90", "analyze the
  Koramangala → Whitefield run". It calls the same endpoints you'd use and the map/sidebar react.
- **AI enforcement brief** (top of the BTP sidebar): an auto-written priority/deploy/watch brief.
- **AI read**: select any zone, or analyze a route, and an inline plain-English "why + what to do".
- **AI insights**: a few proactive, data-derived flags (e.g. high-impact zones a count view misses).

The copilot answers **only from the live data** (grounded — no outside facts), and the AI panels
quietly disappear if the Claude backend isn't running. See the README for enabling it.

---

## 5. BTP Command Console

Switch between four modes with the mode toggle at the top of the sidebar.

### 5.1 Hotspots

**Purpose:** the ranked priority list — enforce by impact, not volume.

**What you see**
- Summary stats: zones scored, ranked (n ≥ 50), measured delay on top corridors, and
  "relieved if top-N cleared".
- **Enforcement ROI horizon** pills: `top 5 / 10 / 12` — recompute the relief estimate for
  that many zones.
- **Priority enforcement zones** — a ranked card list. Each card shows: `#rank`, the
  geohash, **impact score**, **% carriageway-blocking** (Tier-3 share), **% heavy** vehicles,
  **citation count**, and **measured delay (min)** where available.

**Controls**
- Click an ROI pill (`top 5 / 10 / 12`) to change the relief horizon.
- Click any zone card → the map flies to and selects that zone.

**How to leverage**
- Deploy enforcement top-down: the #1 zone is the highest flow-impact location in the city.
- Use the **ROI horizon** ("X minutes relieved if top-N cleared") to justify *how many*
  zones a shift should target, and to brief leadership with a concrete payoff number.
- Watch the **% heavy / % carriageway-blocking** columns — two zones with equal impact but
  different composition call for different enforcement (e.g. a freight choke vs. a market spillover).

### 5.2 Patrol plan

**Purpose:** convert the ranked list into an **optimised multi-unit deployment** that covers
the most impact with the least drive time.

**What you see**
- After "Generate patrol plan", one card per unit: **drive-time (min)**, **number of zones**,
  and **total impact** covered. Routes are drawn on the map.

**Controls**
- **Patrol units**: `1 / 2 / 3 / 4` — how many teams you're deploying.
- **Coverage depth**: `top 10 / 15 / 20` — how deep into the priority list to cover.
- **Generate patrol plan** — runs the optimiser.

**Under the hood:** the top-K impact zones are clustered (k-means) into one cluster per
unit, ordered within each cluster by nearest-neighbour, and turned into drive routes via the
MapMyIndia Routing API (with a haversine fallback if the API is unavailable).

**How to leverage**
- Set **units** to match the shift's available teams; set **coverage depth** to how
  ambitious the sweep is.
- Compare each unit's **drive-time vs total impact** — if one unit has high drive-time for
  modest impact, that cluster is geographically scattered; consider reducing depth or adding
  a unit.

### 5.3 What-if

**Purpose:** preview the enforcement payoff of clearing a chosen set of zones *before* you
commit resources.

**What you see** (live, as you select)
- **Delay relieved (min)**, **% carriageway-blocking removed**, **zones selected**, and
  **citations covered**.

**Controls**
- **Quick-select** pills: `top 5 / 10 / 15` — load a preset set instantly.
- **Click zones on the map** to add or remove them from the set (toggle).

**How to leverage**
- Build the **smallest zone set that hits a target** — e.g. "what's the fewest zones to
  relieve 30 minutes of network delay?" Start with a quick-select, then add/remove on the map.
- Use it in planning meetings to compare two candidate enforcement packages side by side.

### 5.4 Blind spots

**Purpose:** surface **under-enforced** zones — high impact-character but low current
enforcement. These are the zones a count-based, patrol-driven process systematically misses.

**What you see**
- Candidate zones with **predicted impact**, **citation count**, **distinct enforcement
  devices** seen, and the **blind gap** (how under-covered it is).

**Controls**
- Click a candidate → the map focuses it.

**How to leverage**
- Treat blind spots as **expansion targets**: add them to upcoming patrol routes (Section 5.2)
  to extend coverage beyond the already-known hotspots.
- Because they're identified by *character* (severity, heavy-vehicle, road context) rather
  than ticket volume, they're exactly the carriageway-blocking locations that wouldn't
  bubble up on a volume map.

---

## 6. Flipkart Logistics: route resilience

**Purpose:** for a delivery route, detect the parking-induced friction it crosses,
quantify the **SLA delay**, and propose a **reroute** around the worst choke point.

**What you see** (after analysing a route)
- **Total delay added by parking on this route (min)** — summed delay across the hotspots
  the route crosses.
- **SLA breach risk** — `Critical` (≥ 15 min), `Medium` (≥ 5 min), or `Low`.
- **Avoidable by rerouting (min)** — the delay of the *worst* choke the detour routes around
  (this is correctly *less* than the total when a route crosses several chokes).
- On the map: **pickup** and **drop** pins, the **blocked route (red)** vs the **optimised
  detour (green)**, and **choke-point** markers (orange).
- **Choke points on this route** — a clickable list (tap to locate on the map) with per-cell
  delay, primary infraction, dominant vehicle class, and impact.

**Controls**
- Pick one of the **sample delivery routes** (e.g. *Koramangala → Whitefield (ORR)*,
  *City Market → Hebbal*, *Electronic City → KR Puram*). Each crosses known hotspot corridors.
- (Programmatically, any list of waypoints can be analysed via the API — Section 9.)

> **Routing accuracy:** road-accurate blocked/detour geometry and drive times come from the
> MapMyIndia Routing API. Without a `.mappls_secrets` key the app still works — routes are
> drawn as a straight-line preview threaded through the choke zones, and patrol drive times
> are *estimated* (haversine) and tagged `est.` Add a key for road-accurate routing.

**Under the hood:** the route is matched to ranked impact cells within ~200 m of its path;
each contributes a measured delay (from the precomputed routing-cost-penalty table where
available, else a capacity-based estimate). A perpendicular via-point around the worst choke
is sent to the MapMyIndia Routing API to compute the detour.

**How to leverage**
- **Triage deliveries:** flag `Critical`/`Medium` routes for re-timing or pre-emptive reroute.
- **Quantify corridor exposure:** the per-corridor delay numbers turn "this area is bad
  traffic" into an SLA figure you can plan against.
- A "no active hotspots — clear run" result is a green light to dispatch as-is.

---

## 7. Reading the map

- **Choropleth colour = impact** (blue/low → amber → red/critical). See the legend (bottom-left).
- **Click any zone** to focus and select it (the sidebar highlights the matching card).
- **In What-if**, clicking a zone toggles it in/out of your selected set.
- **Patrol plan** overlays each unit's colour-coded route with numbered stops; **Logistics**
  overlays pickup/drop pins, the blocked route (red) and detour (green).

**Impact filter (top-left of the map).** By default every scored zone is shown. To declutter
to only the worst zones, untick *Show all zones* and drag the slider — the map then shows only
zones with **impact ≥ N**, and the readout shows how many qualify (e.g. "825 of 5,492 shown").
Tick *Police stations* to overlay the 54 station locations as labelled markers for geographic
reference.

---

## 8. Status bar: online vs static-only

Top-right indicators tell you what's available:

| Badge | Meaning |
|---|---|
| **API ONLINE** | The FastAPI backend is reachable — Patrol Plan and live route analysis work. |
| **STATIC-ONLY** | No backend; the app runs entirely from the committed data bundle. Hotspots, What-if, and Blind spots still work; Patrol Plan and live routing are unavailable. |
| **MODEL ✓ / —** | Whether the LightGBM live-scoring model is loaded. |
| **MAPPLS …** | MapMyIndia client state (ok / degraded). Routing degrades to a fallback if the key is absent. |

This is by design: the prebuilt bundle (`web/public/data/`) makes the core experience
demoable with zero backend.

---

## 9. API reference

Base URL (local): `http://localhost:8011`. Defined in `api/main.py`.

| Method | Path | Purpose | Params / body |
|---|---|---|---|
| GET | `/api/v1/health` | Service, model, MapMyIndia status | — |
| POST | `/api/v1/score` | Impact score for a point | `{ "lat": float, "lon": float }` |
| GET | `/api/v1/zones/{gh7}` | One zone's full record | path: geohash-7 |
| GET | `/api/v1/triage/hotspots` | Impact-ranked hotspots as GeoJSON | `min_impact` (0), `limit` (500) |
| GET | `/api/v1/triage/patrol-plan` | Optimised multi-unit patrol plan | `units` (3), `topk` (15) |
| POST | `/api/v1/logistics/impedance-loop` | Route choke-points + SLA delay + reroute | `{ "waypoints": [{lat,lng}…], "min_impact": 80 }` |
| GET | `/api/v1/mappls/revgeocode` | Reverse geocode (cached passthrough) | `lat`, `lng` |

Every response carries an `X-Request-ID` header (echoed from the request or generated).
Errors return `{ "error": { "code", "message", "request_id" } }`.

Example:
```bash
curl localhost:8011/api/v1/health
curl "localhost:8011/api/v1/triage/hotspots?min_impact=80&limit=50"
curl -X POST localhost:8011/api/v1/score -H 'content-type: application/json' \
     -d '{"lat":12.997,"lon":77.669}'
```

---

## 10. Setup & running

### Prerequisites
- Python 3.12+, Node 18+.
- The runtime artifacts (`fe_work/cell_scores.parquet`, `fe_work/fe_out/*`, and the
  `web/public/data/*` bundle) are **committed** — a fresh clone runs with no extra steps.

### Backend (FastAPI)
```bash
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements-api.txt
uvicorn api.main:app --port 8011
```
Health: `curl localhost:8011/api/v1/health`.

### Frontend (Vite + React + Deck.gl)
```bash
cd web
npm install
npm run dev            # http://localhost:5173  (proxies /api → :8011)
```

### Tests
```bash
pytest api/tests -q
```

### Configuration (env vars, `api/config.py`)
| Var | Default | Meaning |
|---|---|---|
| `SCORES_PARQUET` | `fe_work/cell_scores.parquet` | Scored zones the API serves |
| `IMPACT_MODEL` | `fe_work/fe_out/model_impact.txt` | LightGBM booster for live `/score` |
| `STATIC_OUT` | `web/public/data` | Frontend bundle location |
| `CORS_ORIGINS` | `localhost:5173,localhost:3000` | Allowed origins |
| `MAPPLS_SECRETS` | `.mappls_secrets` | MapMyIndia key file (optional; app degrades without it) |
| `BREAKER_FAILS` / `BREAKER_COOLDOWN` | `5` / `120` | MapMyIndia circuit-breaker |

> The MapMyIndia key file (`.mappls_secrets`) is a **secret** — keep it local, never commit
> it. Without it, routing/reverse-geocode fall back gracefully.

### Regenerating artifacts (optional)
Only needed if you change the pipeline. Requires the organiser CSV at the repo root and the
pipeline deps (`pip install -r requirements.txt`):
```bash
python run_local.py fe/cells/*.py     # → fe_work/cell_scores.parquet + fe_work/fe_out/*
python mapmyindia_enrich.py 50        # optional MapMyIndia capacity layer (cached)
```
Or run `gridlock_eda.ipynb` → `gridlock_fe.ipynb` on Kaggle.

---

## 11. Data, methodology & honest limitations

**What the data is.** One anonymised BTP citation log — *an enforcement record, not a
sensor feed.* It captures where/when officers ticketed, not where/when congestion occurred.

**Verified data facts** (full set in `eda/findings/DATA_DICTIONARY.md`): 298,450 raw → **293,070 clean**
rows (1.8% exact-ish duplicates removed); window 2023-11-10 → 2024-04-08 IST; 27 offence
codes; every ticket ≥ Tier-2, **8.76% Tier-3**; **200 of ~7,815 110 m-cells hold 50% of all
tickets**.

**Limitations to state honestly (especially to a judging panel):**
1. **No ground-truth traffic-flow label exists** in the data. The Congestion-Impact Score is
   a *defensible, explainable proxy* (severity × vehicle × spatial significance × road
   context), not a measured congestion outcome.
2. **Timestamps measure enforcement, not congestion.** There is a systemic 3–9 PM gap in the
   data (officers don't ticket then), so hour-of-day is deliberately **excluded** as a
   congestion-timing signal.
3. **Enforcement bias.** Tickets concentrate in a minority of devices/officers (device Gini
   ≈ 0.79). Headline hotspots are robust (each seen by many devices), but the long tail
   carries patrol bias — read low-volume zones with that caveat.
4. **`junction_name` is a workflow attribute, not geography** — "No Junction" ≠ "not near a
   junction"; it's used cautiously.

Source documents: `eda/findings/DATA_DICTIONARY.md` (data facts), `eda/findings/EDA_REPORT.md`
(EDA) + `eda/findings/FINDINGS.md` (evidence log), `fe/findings/FE_REPORT.md` +
`fe/findings/MODEL_CARD.md` (scoring & models).

---

## 12. Troubleshooting

| Symptom | Cause & fix |
|---|---|
| `LightGBM … Model format error, expect a tree here` on Windows | Git converted the model `.txt` files' line endings to CRLF. Ensure `.gitattributes` is present, then `git config --global core.autocrlf false` and re-checkout (or re-clone). LightGBM must be 4.x. |
| Status shows **STATIC-ONLY** | Backend isn't running. Start `uvicorn api.main:app --port 8011`. Hotspots/What-if/Blind spots still work from the bundle. |
| **MODEL —** in the status bar | `IMPACT_MODEL` file missing or LightGBM not installed. `/score` falls back to grid lookup; install `requirements-api.txt` and ensure `fe_work/fe_out/model_impact.txt` exists. |
| MapMyIndia features degraded | `.mappls_secrets` absent or rate-limited — routing/geocoding use fallbacks; functionality is preserved, accuracy of detours reduced. |
| Frontend can't reach the API | Confirm the backend is on port **8011** (the Vite dev proxy expects it) and CORS origins include your frontend URL. |

---

## 13. Glossary

- **geohash-7** — a ~153 m square cell; the unit every score is computed on.
- **Tier 0–3** — carriageway-impact tier of a violation (3 = blocks a moving lane).
- **`is_valid`** — citation not rejected/duplicate (83% of rows); spatial work uses these.
- **Gi\*** (Getis-Ord) — spatial statistic flagging statistically significant impact clusters.
- **Impact-character** — volume-independent blend of Tier-3 share, heavy share, road context.
- **Ranked zone** — a cell with ≥ 50 citations, i.e. enough data to trust its score.
- **RCP (routing-cost penalty)** — measured per-cell delay used by the logistics loop.
- **ROI horizon** — the "minutes relieved if top-N zones are cleared" planning figure.

---

*GridLock — Flipkart GridLock 2.0, Round 2. Built natively from organiser data; MapMyIndia
used for mapping infrastructure only. See `README.md` for a quick overview and `PRODUCT.md`
for the product framing.*
