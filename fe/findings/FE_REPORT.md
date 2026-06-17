# Congestion-Impact Score — FE Report

**Date:** 2026-06-17 · **Spec:** `docs/superpowers/specs/2026-06-17-congestion-impact-score-design.md`
All numbers below were measured this session (cells in `fe/cells/`; ledger in `docs/JOURNAL.md`).

## What this produces
An unsupervised, spatially-rigorous **Congestion-Impact Score (0–100) per geohash-7 cell** (~153 m),
ranking illegal-parking zones by estimated traffic-flow impact — built natively (MapMyIndia is an
optional enrichment seam), validated by temporal stability and face validity.

## Method (data-driven ensemble)
- **Unit/data:** geohash-7 cells; `is_valid` rows only (83.0%, excludes rejected/duplicate);
  `vehicle_type_final = coalesce(updated, raw)`. 243,272 rows → **5,492 cells (1,229 ranked, n≥25)**.
- **Per-ticket impact intensity:** tier weight `{0:0, 1:0.5, 2:1, 3:6}` × vehicle multiplier
  `{heavy 2.0, commercial 1.3, else 1.0}` — so carriageway-blocking + heavy vehicles dominate
  (corrects the Tier-2 floor that made plain counts ≈ volume).
- **Engine = blend(β·Gi*-significance, (1−β)·impact-character)**, β=0.60:
  - **Getis-Ord Gi\*** on `impact_intensity_total` → statistically significant impact hotspots
    (313 cells at p<0.05).
  - **Impact-character** = volume-independent mean percentile of `tier3_share`, `heavy_share`,
    road-context (`main_road|junction|circle`).
  - **PCA** (PC1=volume 26.6%, severity orthogonal on PC2) and a hand composite are kept as
    **concordance cross-checks**, not the shipped score.
- **β selection:** max temporal stability subject to the score actually delivering impact
  (Tier-3 lift ≥2, heavy ≥1). Naïve max-stability picked β=0.75 but that failed impact
  (heavy lift 0.91×) and was rejected.

## Validation (measured)
| Check | Result | Note |
|------|--------|------|
| **Face validity** | **Tier-3 lift 2.16×**, heavy 1.03× | top-50 over-concentrate carriageway-blocking (was 0.56×/0.19× pre-fix) |
| Temporal stability | Spearman **0.774** | aspirational 0.80; capped by the real Feb enforcement-volume regime drop |
| Approved-only sensitivity | Spearman **0.747** | ≈ threshold 0.75 — ranking survives the strict 38.7% subset |
| Bias robustness | top-50 median **26** distinct devices | not patrol artifacts |
| Method concordance | Gi*–character τ **0.12** | low *by design* — significance vs character are orthogonal; blending is the point |

## Top priority zones (ranked, n≥25)
| # | geohash | lat, lon | impact | n | Tier-3 | heavy |
|---|---------|----------|--------|---|--------|-------|
| 1 | tdr1zqj | 12.997, 77.670 | 100.0 | 94 | 68% | 43% |
| 2 | tdr1zmv | 12.997, 77.669 | 100.0 | 87 | 79% | 31% |
| 3 | tdr6000 | 13.008, 77.696 | 100.0 | 1501 | 34% | 1% |
| 4 | tdr3858 | 12.940, 77.696 | 99.9 | 1192 | 95% | 7% |
| 5 | tdr1trf | 12.964, 77.578 | 99.9 | 546 | 14% | 1% |

The blend surfaces **both** small high-character freight/commercial choke points (#1–2: ~70–80%
Tier-3, ~30–43% heavy) **and** high-volume statistically-significant cells (#3,#5). Full list:
`fe_out/priority_table.csv`.

## Outputs (`/kaggle/working/fe_out/`, pulled to `eda/eda_out/`)
- `cells.geojson` (5,492 scored polygons) — Mappls choropleth-ready.
- `impact_map.html` — folium choropleth of 1,229 ranked cells + top-15 markers.
- `priority_table.csv` (top-100), `rollup_gh6.csv` / `rollup_gh5.csv` (zoom levels), `kde_points.csv`.
- `mapmyindia_enrich.py` — optional road-name/geofence enrichment (no-op without `MAPPLS_TOKEN`).

## Honest limitations
- Temporal stability ~0.77 (not 0.80): the Feb enforcement-volume drop genuinely reshuffles
  mid-tier cells; the top tier is stable.
- Score reflects *enforcement-observed* illegal parking; true congestion has no ground-truth label
  here, so the score is a defensible proxy, not a measured outcome.
- Hour-of-day excluded (enforcement-timing, not congestion — EDA Gate 3).
