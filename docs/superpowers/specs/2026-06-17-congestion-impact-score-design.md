# Congestion-Impact Score & Feature Engineering — Design Spec

**Date:** 2026-06-17
**Depends on:** EDA findings (`eda/findings/EDA_REPORT.md`, `FINDINGS.md`, `SEVERITY_TAXONOMY.md`, `DATA_DICTIONARY.md`)
**Builds on artifacts:** `/kaggle/working/cleaned.parquet`, `derived/severity.parquet`

---

## 1. Goal & Output

Produce an **unsupervised, spatially-rigorous Congestion-Impact Score** per geohash-7 cell that ranks
illegal-parking zones by their estimated impact on traffic flow, optimized for **result fidelity** (not
hand-explainability). No ground-truth congestion label exists, so the score is composed from objective
spatial statistics + data-driven weighting, and selected/validated by temporal stability.

**Primary deliverables:**
- `cell_scores.parquet` / `.csv` — per geohash-7 cell: centroid, all features, component sub-scores, Gi* z, PCA composite, final ensemble Impact (0–100), rank, confidence flag, rollup keys (gh6/gh5).
- `cells.geojson` (+ gh6/gh5 rollups) — scored polygons for Mappls choropleth.
- `priority_table.csv` — ranked top zones with component decomposition.
- KDE severity raster/contours (`kde.*`) for map rendering.
- `mapmyindia_enrich.py` — isolated optional enrichment seam (road class/width, junction geofences, map layer); pipeline runs fully without it.

---

## 2. Unit & Data Preparation

- **Unit:** geohash-7 (~153×153 m). Encode each violation's (lat,lon) → gh7; store gh6, gh5 for rollups.
  Geohash via `pygeohash` (pip-installed library; not external data).
- **Population filter:** `is_valid` (exclude `validation_status ∈ {rejected, duplicate}`, keep approved +
  unreviewed) → ~83% of rows. NOT approved-only (would bias hotspots toward audited areas — see EDA 6b.3).
- **Vehicle field:** `vehicle_type_final = coalesce(updated_vehicle_type, vehicle_type)`.
- **Severity:** join `derived/severity.parquet` (`max_sev`, `sev_sum`) from the validated taxonomy.
- **Confidence flag:** cells with `n_valid ≥ 25` are `ranked=True`; sparser cells retained but
  `ranked=False` (kept out of headline ranking to stop single-ticket cells topping a percentile scale).

---

## 3. Feature Catalog (per cell, all native)

| Group | Features |
|-------|----------|
| **Volume** | `n`, `n_valid`, `distinct_days`, `distinct_weeks` |
| **Severity** | `sev_sum_total`, `tier3_share`, `mean_sev`, `tier3_count` |
| **Vehicle impact** | `heavy_share` (BUS/PRIVATE BUS/TEMPO/HGV/LORRY/TANKER/FACTORY BUS), `commercial_share` (+autos/LGV/goods), `twowheeler_share` |
| **Road context** (location text, regex on lowercased `location`) | `f_main_road`, `f_circle`, `f_cross`, `f_junction`, `f_busstop_school_hosp`, `f_metro`, `f_market`, `f_mall` (share of cell's tickets whose location string contains the term) |
| **Spatial-lag** | neighbor-cell aggregates over gh7 king-contiguity: `lag_n`, `lag_sev_sum`, `lag_tier3_share` (corridor/spillover signal) |
| **KDE intensity** | `kde_sev` = severity-weighted Gaussian KDE evaluated at cell centroid (smooth surface, bandwidth ≈ 250 m) |
| **Interactions** | `heavy_x_mainroad = heavy_share × f_main_road`, `tier3_x_junction = tier3_share × f_junction` |
| **Persistence / breadth** | `distinct_devices`, `distinct_officers`, `recurrence_weeks` (# distinct ISO weeks with ≥1 ticket). NO hour-of-day (Gate 3). |

All continuous features percentile-normalized to 0–1 for the composite (robust to right-skew).

---

## 4. Scoring Engine (ensemble; data-driven)

**4.1 Getis-Ord Gi\* (spatial significance).**
- Spatial weights: `libpysal` distance-band or KNN (k≈8) on cell centroids.
- Statistic: `esda.getisord.G_Local` on the severity-weighted intensity (`sev_sum_total`).
- Output: `gi_z` (z-score), `gi_p`. High positive z = statistically significant impact hotspot.

**4.2 PCA / factor composite (objective weights).**
- Standardize the percentile features; `sklearn.decomposition.PCA`.
- Composite = projection on PC1 (sign-aligned so higher = more impact), validated that PC1 loadings are
  non-degenerate and align with severity/volume/heavy direction. Store loadings as the objective
  "what-drives-impact" readout. (If PC1 explains <~40% variance, blend PC1+PC2 by explained-variance.)

**4.3 Ensemble.**
- `Impact_raw = α·percentile(gi_z) + (1−α)·percentile(pca_composite)`, a tunable blend.
- `α` is selected in §5 to maximize temporal-stability Spearman (grid-search α ∈ {0,0.25,0.5,0.75,1};
  default 0.5 if stability is flat across α).
- `Impact = 100 × percentile(Impact_raw)`. Final rank + gh6/gh5 rollup sums.

**4.4 Interpretability cross-check (not shipped as the score).**
- Hand-weighted composite (Severity .30, Volume .25, VehicleImpact .20, RoadContext .15, Persistence .10).
- Report Kendall's W agreement between {Gi*, PCA, hand}; large disagreement triggers investigation.

---

## 5. Validation = Model Selection / QA

| Check | Method | Pass threshold |
|-------|--------|----------------|
| **Temporal stability (primary selector)** | Recompute full score on Nov–Jan vs Feb–Apr halves; Spearman of cell ranks | Spearman ≥ 0.80 |
| **Spatial cross-validation** | Fit composite on random 50% of cells, predict held-out cells' `sev_sum`; report Spearman | report (target ≥ 0.6) |
| **Method concordance** | Kendall's W across {Gi*, PCA, hand} top-N rankings | W ≥ 0.6 |
| **Bias robustness** | Top-50 cells: distinct-device count distribution; + recompute on approved-only subset, Spearman vs full | multi-device confirmed; Spearman ≥ 0.75 |
| **Face validity** | Top-50 vs baseline: Tier-3 share, heavy-vehicle share, named-junction share lift | clear positive lift |

The ensemble blend (Gi*/PCA weighting in 4.3) is chosen to maximize the temporal-stability Spearman.

---

## 6. Architecture / File Structure

All cells run on the remote Kaggle kernel via `kaggle_exec.py`; charts pulled via `kaggle_pull.py`.
Reuses EDA plumbing. New analysis cells under `fe/cells/`, outputs to `/kaggle/working/fe_out/`.

- `fe/cells/00_prepare.py` — load cleaned+severity, filter is_valid, coalesce vehicle, geohash encode → `fe_base.parquet`.
- `fe/cells/10_features.py` — build all Section-3 features per gh7 → `cell_features.parquet`.
- `fe/cells/11_spatial_lag_kde.py` — spatial-lag + KDE + interactions (needs centroids/weights).
- `fe/cells/20_gistar.py` — Getis-Ord Gi* → `gi.parquet`.
- `fe/cells/21_pca.py` — PCA composite + loadings → `pca.parquet`.
- `fe/cells/22_ensemble.py` — rank-aggregate → `cell_scores.parquet`; hand cross-check.
- `fe/cells/30_validate.py` — all Section-5 checks → `validation_report.md` + charts.
- `fe/cells/40_outputs.py` — `cells.geojson`, rollups, `priority_table.csv`, KDE raster.
- `mapmyindia_enrich.py` — optional, key-gated enrichment + Mappls layer (local module).
- `fe/findings/FE_REPORT.md` — executive summary of the score + validation results.

**Verification-first discipline** (as in EDA): every aggregation guarded by an assertion
(rows conserved on geohash join, percentile in [0,1], no cell lost in spatial-lag merge, Gi* output
length == cell count). Commit per cell.

---

## 7. Constraints & Decisions Carried From EDA

- Native-core; MapMyIndia is enrichment only (no key yet → pipeline must run without it).
- Time-of-day excluded from the score (Gate 3: enforcement timing ≠ congestion timing).
- `junction_name` is a workflow attribute, not geography → use `location`-text `f_junction` instead, and
  reserve true junction geofences for the MapMyIndia seam.
- `center_code` dropped (≈1:1 with `police_station`).
- No external datasets; `pip install` of libraries (pygeohash, esda/libpysal already present) is permitted.

---

## 8. Out of Scope (YAGNI)

- Supervised model on a constructed pseudo-label (rejected earlier; ensemble of Gi*+PCA is the chosen engine).
- Repeat-offender modeling (3.1% of tickets, mobile — negligible).
- Real-time/streaming scoring (batch only).
- The live Mappls front-end app (only the GeoJSON/enrichment seam is in scope).
