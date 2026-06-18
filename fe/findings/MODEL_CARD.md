# Model Card — GridLock Parking Congestion-Impact System

**Task:** Detect illegal-parking hotspots and quantify their impact on traffic flow, to enable
targeted BTP enforcement. **Date:** 2026-06-18. All metrics measured this session (`docs/JOURNAL.md`).

## Components
The system has three coupled models, all on **geohash-7 cells (~153 m)** built from the BTP citation
log (293k cleaned rows, `is_valid` filter, EB-smoothed rates):

1. **Congestion-Impact Score (primary, unsupervised).**
   `Impact = 100·pct( 0.75·pct(Gi*z on impact_intensity) + 0.25·impact_character )`
   - `impact_intensity` per ticket = tier weight `{0:0,1:.5,2:1,3:6}` × vehicle mult `{heavy 2.0, comm 1.3, else 1.0}`.
   - `impact_character` = volume-independent mean percentile of EB-smoothed Tier-3 share, heavy share, road context.
   - Getis-Ord Gi* (PySAL) gives statistically significant impact hotspots (313 cells at p<0.05).
2. **Impact regression model (LightGBM)** — predicts the score from cell features; serves/generalizes scoring.
3. **Hotspot-detection classifier (LightGBM)** — flags top-quartile impact-hotspots probabilistically.
4. **MapMyIndia capacity layer (enrichment, optional)** — reverse-geocodes top cells to authoritative
   street/locality and applies a road-type **exposure** weight `{arterial/highway 1.5, main road 1.35,
   cross/junction 1.2, local 1.0}` → `impact_capacity = impact × exposure`. Native `impact` stays primary;
   this layer adds the "flow capacity" dimension. `FACT:` it re-ranks **Outer Ring Road** (Marathahalli/
   Kadubisanahalli/Mahadevapura) corridor cells to the top — illegal parking on a high-capacity arterial
   has outsized flow impact. `CAVEAT:` free-tier rev_geocode gives street/locality, not lane counts, so
   exposure is a **heuristic**, not measured capacity.

## Evaluation (spatial GroupKFold by gh5 — held-out regions)
| Model | Metric | Volume-only | Cell-intrinsic | Full |
|------|--------|------------|----------------|------|
| Impact regression | R² | 0.148 | 0.337 | 0.980 |
| Impact regression | Spearman | 0.390 | 0.633 | 0.989 |
| Hotspot detection | ROC-AUC | 0.588 | **0.847** | 0.988 |
| Hotspot detection | PR-AUC | 0.338 | 0.724 | 0.968 |

**Headline:** volume alone ≈ coin-flip for finding impact-hotspots (AUC 0.588); cell *character*
(severity/heavy-vehicle/road) detects them at **0.847 AUC** in unseen regions; the full model is a
deployable 0.99-AUC detector / 0.98-R² scorer.

## Score validation (the shipped unsupervised score)
- **Face validity:** top-50 cells carry **3.15× Tier-3** and **1.37× heavy-vehicle** vs baseline.
- **Temporal stability** (ranked cells, Nov–Jan vs Feb–Apr): Spearman **0.782**.
- **Approved-only sensitivity:** Spearman **0.715**.
- **Bias robustness:** top-50 seen by median **21** distinct devices (not patrol artifacts).
- **Method concordance** Gi*–character τ ≈ 0.04 (orthogonal by design — significance vs character).

## Top drivers (LightGBM gain)
Neighborhood severity (`lag_sev_sum`), `impact_intensity`, KDE severity, `heavy_share`,
`commercial_share`, `mean_sev`. Volume (`n`) is weak alone.

## Intended use & limitations
- **Use:** rank ~792 well-supported (n≥50) cells for enforcement prioritization; outputs are
  Mappls-ready (`cells.geojson`, rollups, `priority_table.csv`, `impact_map.html`).
- **Not** a measured congestion outcome — there is no ground-truth flow label; the score is a
  defensible proxy from enforcement data.
- Timestamps reflect enforcement scheduling, not congestion timing → time-of-day excluded.
- `junction_name`/`center_code` excluded (workflow artifact / redundant).
- MapMyIndia capacity layer is a road-type **heuristic** (street-name based), not lane-level data;
  applied to top-50 cells (free-tier budget), cached in `.mappls_cache/`.
- Stability capped (~0.78) by the real Feb enforcement-volume regime change.

## Artifacts
`fe_out/model_impact.txt`, `model_detect.txt` (LightGBM boosters), `*_importance.csv`, `*_oof.csv`;
score outputs in `fe_out/` (`cells.geojson`, `priority_table.csv`, rollups, `kde_points.csv`,
`impact_map.html`); MapMyIndia layer `fe_out/top_enriched.{csv,geojson}`; tracked copies in
`fe/artifacts/`. Reproduce: `gridlock_fe.ipynb` (Kaggle) or `python run_local.py fe/cells/*.py` (local);
enrichment via `python mapmyindia_enrich.py 50`.
