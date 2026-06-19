# JOURNAL.md — Chronological Work Log & Experiment Ledger (append-only)

> The project's "black box recorder." **Append-only, newest at the bottom,
> every entry timestamped.** Drop a breadcrumb after every meaningful step —
> especially mid-task — so a fresh session (or one resuming after summarization)
> can reconstruct exactly where we were and why.
>
> **This is also the anti-hallucination ledger:** every metric we report must
> have a row here with the command that produced it. A number with no journal
> row does not exist.
>
> **Division of labor:**
> - This file = *what happened, in order* (raw, including dead-ends).
> - [PROGRESS.md](PROGRESS.md) = *current snapshot*, refreshed FROM this log.
> - [DECISIONS.md](DECISIONS.md) = *why*, promoted here once a choice is settled.
> - [DATASET.md](DATASET.md) = *verified data facts*.

---

## How to write an entry

Use one of the two templates below. Keep entries terse but self-contained.

### Work / checkpoint entry
```
### YYYY-MM-DD HH:MM — <short title>
- Did: <what was done>
- Result: <FACT: measured outcome | observation>  (cite command/file)
- State: <where we are now — safe to resume from here>
- Next: <the immediate next step>
```

### Experiment run entry (use the EXP ledger table too)
```
### YYYY-MM-DD HH:MM — EXP-NNN <model/idea>
- Hypothesis: <what we expected and why>
- Setup: seed=<n>, split=<time/grouped/...>, features=<...>, lib versions=<...>
- Command: `<exact command run>`
- Result: <FACT: metric = value>  (paste the key output line)
- Verdict: keep / discard / iterate — <one line why>
- Artifact: <path to saved model/config, or "none">
```

---

## Experiment ledger (quick index — one row per run)

| EXP | Date | Model / idea | Metric (val) | Split | Seed | Verdict | Journal entry |
|-----|------|--------------|--------------|-------|------|---------|---------------|
| _none yet_ | | | | | | | |

> Add a row here for every EXP-NNN entry below so runs are scannable at a glance.
> "Metric (val)" must be a number you actually produced — never a guess.

---

## Log

### 2026-06-17 — Project bootstrap
- Did: Profiled the dataset (pure-Python csv) and created the steering files
  (CLAUDE.md, DATASET.md, CONSTRAINTS.md, DECISIONS.md, PROGRESS.md, settings.json).
- Result: FACT — 298,449 rows × 24 cols, dates 2023-11-09→2024-04-08. Full verified
  facts in [DATASET.md](DATASET.md).
- State: Setup complete; no modeling started; no env yet.
- Next: Confirm Round 2 evaluation metric; decide solution framing; set up venv.

### 2026-06-17 — Added this journal
- Did: Created JOURNAL.md to capture chronological progress / mid-task checkpoints
  and experiment runs (gap left by snapshot-style PROGRESS.md). Logged as DECISIONS ADR-001.
- State: Context system now: PROGRESS (snapshot) + JOURNAL (history) + DECISIONS (why)
  + DATASET (facts).
- Next: (unchanged) metric → framing → env.

### 2026-06-17 — EDA Phases 0–7 complete (verification-first)
- Did: Ran the full EDA (cells in `eda/cells/`, notebook `gridlock_eda.ipynb`).
  Cleaning, JSON-array parse, validation lifecycle, enforcement-bias baseline,
  univariate/co-occurrence, severity taxonomy, timestamp-trust gate, grid+DBSCAN
  hotspots, bias-normalised map, vehicle/station severity, space×time, hidden-pattern hunt.
- Result (FACT — all measured; evidence `eda/findings/FINDINGS.md`):
  - Clean rows **293,070** (raw 298,450, −1.8% dedup). Window 2023-11-10→2024-04-08 IST.
  - 27-code 1:1 offence map; 13.4% multi-violation. `is_valid` 83.0% (rejected+dup 16.8%, systemic).
  - Enforcement bias: device Gini **0.788**, officer **0.775** — but top hotspots
    span 23–62 devices (corr 0.61) → headline hotspots robust, bias in long tail.
  - Timestamp = enforcement timing, NOT congestion (3–9 PM dead window 0.86%, uniform).
  - Severity: every ticket ≥ Tier-2, **8.76% Tier-3**; use `sev_sum`.
  - Spatial: **200/7,814 cells (2.56%) = 50% of tickets**; DBSCAN 267 clusters, 2.6% noise.
  - **Volume≠impact:** BMTC/KSRTC bus 46.3% Tier-3 vs scooter 4.4%; cell corr(count,Σsev)=0.969
    but a near-100%-Tier-3 micro-hotspot tail ranks ~900th by volume (count-blind).
  - `junction_name` = workflow attribute (bimodal); `center_code` ~1:1 with `police_station`;
    `location` free-text = top native FE source.
- State: EDA done and reproduced clean. Steering docs updated — DATASET.md rewritten
  as EDA-authoritative; DECISIONS.md ADR-002 (gate outcomes); PROGRESS.md refreshed.
- Next: confirm Round 2 metric; brainstorm + design the congestion-impact score; FE pipeline.

<!-- Append the next entry below this line. -->

### 2026-06-17 — FE score built (Gi*+PCA ensemble); validation caught volume-domination
- Did: Built FE pipeline on remote kernel — fe_base (243,272 valid rows, 5,492 gh7 cells),
  per-cell features + spatial-lag/KDE/interactions, Getis-Ord Gi* (294 sig cells, p<0.05),
  PCA composite (PC1=volume 26.6%, severity orthogonal on PC2; blended to 39.0%),
  ensemble impact + hand cross-check, full validation suite. Cells in `fe/cells/`.
- Result (FACT — measured this session, cell `fe/cells/30_validate.py`):
  - Temporal stability Spearman(half1,half2) = **0.768** (1,003 common cells) — marginal (<0.80).
  - alpha grid: best **alpha=0.25** (stability-proxy 0.821).
  - Approved-only sensitivity Spearman = **0.807** (PASS ≥0.75).
  - Top-50 median distinct_devices = **48** (multi-device, robust).
  - Concordance tau Gi*-PCA = 0.604, PCA-hand = 0.451, Gi*-hand = 0.265.
  - **FACE VALIDITY FAILS: top-50 tier3_share lift = 0.56x, heavy_share lift = 0.19x.**
    Top "impact" cells are BELOW average on carriageway-blocking → currently a VOLUME score.
- Diagnosis (FACT): every ticket has Tier-2 floor → sev_sum≈2×count≈volume; Gi*(sev_sum) and
  PCA-PC1 both volume-driven; severity/heavy signal washed out (loads on PC2).
- Next: amend engine — steep severity weights {0:0,1:.5,2:1,3:6} → impact_intensity; Gi* on
  impact_intensity; add explicit impact-character axis to ensemble; re-validate (face lift must flip >1x).
- State: pipeline committed through 22_ensemble + 30_validate; fix pending user confirm.

<!-- Append the next entry below this line. -->

### 2026-06-17 — FE engine amended (impact-intensity) — face validity now PASSES
- Did: Diagnosed volume-domination; amended engine. Per-ticket impact_intensity =
  tier_weight{0:0,1:.5,2:1,3:6} x vehicle_mult{heavy 2.0, commercial 1.3, else 1.0}.
  Gi* now on impact_intensity_total (not sev_sum). Ensemble = beta*pct(Gi*) +
  (1-beta)*impact_character, where impact_character = mean percentile of
  [tier3_share, heavy_share, road(main_road|junction|circle)] (volume-INDEPENDENT).
  PCA + hand kept as concordance cross-checks only.
- Result (FACT — cell fe/cells/30_validate.py, beta grid):
  - beta selected = **0.60** (rule: max temporal stability s.t. tier3_lift>=2 & heavy>=1;
    naive max-stability picked 0.75 which FAILED impact, heavy_lift 0.91x — rejected).
  - Temporal stability Spearman = **0.774** (aspirational 0.80; capped by Feb enforcement-volume
    regime drop — honest limitation, not a methodology fault).
  - Approved-only sensitivity = **0.747** (~threshold 0.75).
  - Top-50 median distinct_devices = **26** (robust, multi-device).
  - **FACE VALIDITY PASSES: top-50 tier3 lift 2.16x, heavy lift 1.03x** (was 0.56x/0.19x).
  - Gi*-character concordance tau = 0.120 (low BY DESIGN — significance vs character are orthogonal).
- State: engine fixed + re-validated; cells 10/11/20/21/22/30 + scorelib updated. Next: outputs (geojson,
  priority table, KDE, MapMyIndia seam, map), FE_REPORT.
<!-- Append the next entry below this line. -->

### 2026-06-17 — IT1: score optimization (EB smoothing + evidence threshold)
- Did: Empirical-Bayes shrinkage of rate features (tier3_share, heavy_share) toward global mean,
  K=40 pseudo-tickets; raised `ranked` evidence threshold to n>=50; validation now reports
  temporal stability on RANKED (well-supported) cells; beta re-selected by ranked-stability s.t.
  impact delivered (tier3>=2.5, heavy>=1.2).
- Result (FACT — fe/cells/30_validate.py): selected **beta=0.75**.
  - Face validity: **tier3 lift 3.15x, heavy 1.37x** (v1 was 2.16x / 1.03x — big gain).
  - Ranked-cell temporal stability Spearman = **0.782** (792 ranked cells).
  - Approved-only sensitivity = **0.715** (up from 0.665).
  - Top-50 median distinct_devices = **21**; concordance Gi*-char tau = 0.037 (orthogonal by design).
- Decision: EB smoothing + n>=50 ranking adopted (v2). Small-cell noise no longer dominates the headline.
- State: cells 10/22/30 + scorelib updated; outputs+map regenerated. Next: IT2 supervised impact model.
<!-- Append the next entry below this line. -->

### 2026-06-18 — Remote kernel expired -> pivoted to LOCAL; IT2 supervised impact model
- Context: Kaggle proxy token dead (HTTP 000) after the gap; remote /kaggle/working likely wiped.
  Decision: rebuilt the whole pipeline LOCALLY (venv + local CSV) via `run_local.py` (rewrites
  /kaggle paths). Local reproduces remote: cleaned 293,068 (vs 293,070; 2-row pandas-version dedup
  tie, negligible), 5,492 cells, 313 sig, identical top zones. Gi* z magnitudes differ by libpysal
  version but ranks/percentiles identical (score uses percentiles).
- Did (IT2): LightGBM regressor predicting impact, spatial GroupKFold by gh5 (47 groups, 1,417 eval
  cells n>=20), leakage-controlled (excluded impact/gi_z/gi_p/pca/impact_char/lat/lon).
- Result (FACT — fe/cells/50_model_impact.py):
  - Volume-only spatial-CV R2=**0.148** (Spearman 0.390) — volume poorly predicts impact (re-confirms volume!=impact).
  - Cell-intrinsic (transferable, no spatial) R2=**0.337**, Spearman 0.633 — moderate held-out-region generalization.
  - Full (with spatial lag/kde) R2=**0.980**, Spearman 0.989 — faithfully reproduces the score -> deployable scorer.
  - Top drivers (gain): lag_sev_sum, lag_n, impact_intensity_total, kde_sev, heavy_share, mean_sev.
  - Saved: fe_out/model_impact.txt (booster), importance.csv, oof.csv. Tracked copies in fe/artifacts/.
- State: local pipeline fully working; model deliverable done. Next: IT3 hotspot-detection classifier.
<!-- Append the next entry below this line. -->

### 2026-06-18 — IT3 hotspot-detection classifier
- Did: LightGBM binary classifier, label = top-quartile impact among busy cells (n>=20; 355/1417
  positives, 25.1%), spatial GroupKFold by gh5, leakage-controlled features. (fe/cells/51_model_detect.py)
- Result (FACT):
  - Volume-only ROC-AUC=**0.588** (PR 0.338) — volume ~cannot detect impact-hotspots (coin-flip-ish).
  - Cell-intrinsic character ROC-AUC=**0.847** (PR 0.724) — strong held-out-region detection from
    severity/vehicle/road character alone.
  - Full ROC-AUC=**0.988** (PR 0.968) — deployable detector.
  - Top features: lag_sev_sum, kde_sev, heavy_share, lag_n, heavy_share_eb, commercial_share.
  - Saved model_detect.txt + importance/oof; tracked in fe/artifacts/.
- Thesis quantified: impact-hotspots are NOT findable by counting (0.59) but ARE by character (0.85).
- Next: IT4 finalize — regen outputs locally, MODEL_CARD, canonical FE notebook, refresh steering docs.
<!-- Append the next entry below this line. -->

### 2026-06-18 — IT4 finalize (model card, notebook, docs)
- Did: MODEL_CARD.md (3 models + metrics + limits); canonical gridlock_fe.ipynb (24 cells, Kaggle-native,
  prereq=EDA notebook); FE_REPORT.md updated to v2; PROGRESS refreshed; ADR-005 recorded.
- Verification: full FE pipeline re-run end-to-end LOCALLY (00->51) clean — fe_base 243,270; 5,492 cells;
  313 sig; face validity 3.15x; impact R2 0.15/0.34/0.98; detection AUC 0.59/0.85/0.99. All reproduced.
- State: MODEL DELIVERABLE COMPLETE (score v2 + impact regression + hotspot detector, evaluated &
  documented). Pending external: fresh Kaggle URL to re-sync; MapMyIndia key; frontend (later).
<!-- Append the next entry below this line. -->

### 2026-06-18 — MapMyIndia keys verified + top-50 enrichment
- Keys (FACT, 2 test calls): OAuth client_credentials -> 200 (access_token, ~24h); REST key rev_geocode
  -> 200 (returns street/subLocality/locality, NOT lanes). Chose REST-key-in-path (no token lifecycle).
- Built mapmyindia_enrich.py: disk-cached (.mappls_cache/, re-runs=0 calls), top-50 ranked cells,
  rev_geocode -> authoritative street; road-exposure heuristic {arterial/highway 1.5, main road 1.35,
  cross/junction 1.2, local 1.0}; impact_capacity = impact x exposure (optional layer; native impact primary).
- Result (FACT, 50 calls, cached): capacity-adjusted top-12 are ALL **Outer Ring Road** cells
  (Marathahalli/Kadubisanahalli/Devara Beesana Halli/Mahadevapura) — the ORR IT corridor. Mappls street
  names surfaced arterial classification beyond native location text. Outputs: fe_out/top_enriched.csv,
  top_enriched.geojson; tracked copy fe/artifacts/top_enriched.csv.
- Caveat: free tier rev_geocode gives street/locality only -> capacity is a road-type HEURISTIC, not lane data.
- Secrets in .mappls_secrets (gitignored); cache .mappls_cache/ (gitignored).
<!-- Append the next entry below this line. -->

### 2026-06-18 — Severity-weight sensitivity study (Tier-1 optimization)
- Did: perturbed scoring weights across 13 configs (Tier-3 wt 3->10, heavy mult off->3x, Tier-2 floor
  0.5/1.5, Tier-1 0/1, + extreme & flat combos); reused one KNN weights object across all (efficiency).
  Recomputed impact_intensity -> Gi* -> ensemble per config; compared ranking to shipped baseline.
  (fe/cells/52_sensitivity.py; fe/artifacts/sensitivity.csv)
- Result (FACT): ranking highly robust to weights — **Spearman vs baseline min 0.985 / mean 0.995**;
  **top-50 overlap min 42/50 (84%) / mean 46.1**; top-20 min 17/20. Holds even at extreme (w3=10,hm=3)
  and near-flat (w3=3, heavy off) settings.
- Conclusion: hotspot ranking is NOT an artifact of hand-chosen severity weights (Gi* spatial-
  concentration leg dominates; impact-character leg is weight-invariant). Ambiguity #6 (TECHNICAL_REVIEW)
  RESOLVED. Credibility win.
<!-- Append the next entry below this line. -->

### 2026-06-18 — MapMyIndia Snap-to-Road probe (for road-class upgrade)
- Did: tested Snap-to-Road on the REST key (2 calls, ORR corridor path), documented params + geometries.
- Result (FACT): both returned HTTP **412 {"msg":"Parameter missing","error":"Invalid parameter"}** — not
  auth (401/403), not param (tried 2 formats). Conclusion: snapToRoad is **not available on this free-tier
  REST key** (tier-restricted or OAuth/atlas-base only). Reverse-geocode (Geocoding) remains the verified path.
- Decision: road-class enrichment designed as a FALLBACK CHAIN — Snap-to-Road/Routing when available
  (flag-gated, probe-activated), else verified Geocoding street-name heuristic. No model impact; compliant.
<!-- Append the next entry below this line. -->

### 2026-06-18 — Frontend communication layer (FastAPI + fallbacks) BUILT
- Did: implemented the API per spec/plan — api/ package: config, geo, scoring (grid->nearest fallback),
  mappls (cache + circuit breaker + fallback), roadclass (snap->geocode chain, gated), artifacts (static
  bundle + manifest), schemas (Pydantic), main (FastAPI: health/score/zone/revgeocode, request-id, error
  envelope, CORS). TDD throughout.
- Result (FACT): **19/19 tests pass**. Static bundle built (zones 5492, ranked 792). Live smoke test:
  /health {model_loaded:true, mappls:live}; /score (12.997,77.669)->gh7 tdr1zqh impact 99.14 rank 48
  source grid; /openapi.json 200.
- Compliance: only Geocoding (rev_geocode) used; snap-to-road gated off (412 free tier). ADR-007 honored.
- Deferred (Phase-8, documented in plan self-review): /mappls/token + Carto fallback, /mappls/* rate-limit,
  off-grid LightGBM inference in /score.
- State: API layer complete & verified. Next: frontend UI, or Phase-8 follow-ups.
<!-- Append the next entry below this line. -->

### 2026-06-18 — Proto-validation audit (external checklist)
- Verified (FACT): pipeline reads ONLY the organizer CSV + mappls rev_geocode (no shp/scrape/traffic) →
  data + enrichment compliant. Dedup is on vehicle+coord+minute (NOT id; id is unique) with NO pre-sort →
  source of the 2-row drift. cells.geojson props = [gh7,impact,rank,n,tier3_share,heavy_share,gi_z,ranked]
  (missing vehicle/infraction context). impact_capacity range 98.29–149.67 (UNBOUNDED >100). closed_datetime
  & action_taken_timestamp 100% null → clearance-latency NOT computable.
- **MapMyIndia Distance Matrix API VERIFIED (FACT, 1 call): HTTP 200**, results.distances [[0,1807.9]] m,
  durations [[0,238.5]] s. → Routing-Cost-Penalty flow-delay quantification is FEASIBLE (allowed mapping-infra).
- Snap-to-Road still 412 (blocked, free tier).
<!-- Append the next entry below this line. -->

### 2026-06-18 — Audit remediation (items 1-4 of proto-validation checklist)
- §1.3 drift: version-stable dedup key (fixed-width f"{x:.5f}" + strftime) + pre-sort on unique id ->
  deterministic 293,068 across environments (sorting alone only fixes which row survives, not the count).
- §2.2: impact_capacity max-normalized to 0-100 (was 98-150).
- §3.1 leakage: SHIPPED models switched to INTRINSIC (R2 0.337 / AUC 0.847); full kept as labeled baseline.
  (Bug found+fixed: string cols loaded as pandas 'string' dtype slipped past !=object filter -> use is_numeric_dtype.)
- §5.1: geojson +dominant_vehicle_class +primary_infraction_type. clearance_latency NOT derivable (closure cols 100% null).
- Verified: full pipeline re-run clean; 19/19 API tests pass; enrich 0 new calls (cached).
- DECLINED w/ reason: §2.1 PCA-as-weights (PC1=volume -> would re-break score; sensitivity study defends better),
  §5.2 parallel batch (free-tier safety), §1.4 downcast (no memory pressure). §4.1 snap-to-road BLOCKED (412).
- Next: §4.2 Routing-Cost-Penalty delay loop (Distance Matrix VERIFIED 200) as its own focused piece.
<!-- Append the next entry below this line. -->

### 2026-06-18 — Routing Cost Penalty (RCP) flow-impact loop (checklist §4.2)
- Did: rcp.py — per top corridor, MapMyIndia Distance Matrix (mapping-infra) gives free-flow T_base;
  capacity_reduction=min(0.6, 0.10+0.35*tier3_share+0.20*heavy_share); delay_min=T_base*cap/(1-cap).
  Disk-cached (dm_{gh7}.json); pure math unit-tested.
- Result (FACT, 12 corridors, 12 new DM calls then cached): delay range 1.35–11.02 min. Top: tdr3858
  (95% Tier-3) = **11.0 min**, tdr1zmv (heavy 31%) = 7.7 min. Outputs rcp.csv/rcp.geojson; in static bundle.
- Significance: first MEASURED "impact on traffic flow" (minutes), not a proxy — directly answers the PS.
- Compliance: Distance Matrix = mapping infra (routing baseline, NOT live traffic). 21/21 API tests pass.
- Caveat: capacity-reduction is a documented heuristic; O/D geometry approximates the corridor (snap-to-road 412).
<!-- Append the next entry below this line. -->

### 2026-06-18 — Dual-persona frontend BUILT + verified (Vite+React+Deck.gl)
- Built web/ : App shell + persona toggle; MapView (Deck.gl GeoJsonLayer cells colored by impact, Carto-dark
  base, top-hotspot markers, baseline/detour PathLayers, tooltips); BTPSidebar (stats, ROI horizon, ranked
  zones w/ RCP delay); LogisticsSidebar (route presets, delay/SLA/recoverable metrics, choke list).
- Backend endpoints wired: /triage/hotspots, /logistics/impedance-loop (live route_adv detour, cached).
- Verified (FACT, screenshots + logs via preview tool): npm build clean (921 modules); BTP console renders
  5,492 cells + markers + stats; Logistics route analysis returns delay 21.09 min (ORR) / 6.08 min (City
  Market→Hebbal), Critical/Medium SLA, red-blocked + green-detour rendered; 0 console errors; API 200s.
- Next: refine with taste/frontend-design + impeccable skills.
<!-- Append the next entry below this line. -->

### 2026-06-18 — Frontend refinement (frontend-design taste + impeccable polish)
- Taste pass: civic-tech instrument-panel aesthetic — Bricolage Grotesque + Familjen Grotesk + IBM Plex
  Mono, traffic-amber signal accent, grain atmosphere, staggered card motion, live-pulse status.
- Impeccable polish: caught + fixed an Absolute Ban (side-stripe borders on banner/stat/selected-card) →
  full borders + tint + inset ring; bumped muted-text contrast. Added PRODUCT.md + DESIGN.md.
- Verified via preview screenshots (BTP + logistics) + console logs: 0 errors, build clean.
- System status: COMPLETE working dual-persona prototype (BTP console + logistics impedance/detour),
  model + RCP + API + frontend, screenshot/log-verified.
<!-- Append the next entry below this line. -->
