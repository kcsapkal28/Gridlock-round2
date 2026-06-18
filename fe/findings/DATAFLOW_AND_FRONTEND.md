# Dataflow & Frontend Data Inventory

## End-to-end dataflow

```
BTP citation CSV (298,450 rows, /kaggle/input)
  │  EDA clean: dedup + is_valid + parse arrays
  ▼
cleaned.parquet (293,070 rows)  ──► derived/severity.parquet (max_sev, sev_sum)
  │  FE prepare: filter is_valid (243,272) + coalesce vehicle_type + geohash-7
  ▼
fe_base.parquet (243,270 rows, gh7/gh6/gh5)
  │  aggregate per gh7 + empirical-Bayes smoothing
  ▼
cell_features.parquet (5,492 cells)
  │  + spatial-lag + KDE + interactions
  ▼
cell_features_full.parquet
  │  Getis-Ord Gi* (gi_z)  +  PCA composite
  ▼
  │  ensemble: impact = 100·pct(0.75·pct(gi_z) + 0.25·impact_character)
  ▼
cell_scores.parquet (5,492 cells; 792 ranked n≥50)
  ├─► validation_report.md            (metrics)
  ├─► cells.geojson, rollup_gh6/gh5.csv, priority_table.csv, kde_points.csv, impact_map.html
  ├─► model_impact.txt / model_detect.txt  (LightGBM boosters: serve/score new points)
  └─► MapMyIndia enrich (top-50, cached) ─► top_enriched.{csv,geojson}  (street + impact_capacity)
```

Reproduce: `gridlock_eda.ipynb` → `gridlock_fe.ipynb` (Kaggle), or `python run_local.py fe/cells/*.py`
then `python mapmyindia_enrich.py 50` (local).

## What the frontend can show (artifact → UI use)

| Artifact | Rows | Use on frontend |
|----------|------|-----------------|
| `cells.geojson` | 5,492 polygons | **Choropleth heatmap** of impact (props: impact, rank, n, tier3_share, heavy_share, gi_z, ranked) |
| `priority_table.csv` | top 100 | **Ranked enforcement list** with decomposition |
| `top_enriched.geojson` | top 50 | **Markers/popups** with street name, locality, road_class, `impact_capacity`, capacity-rank |
| `rollup_gh6.csv` / `rollup_gh5.csv` | 785 / 59 | **Zoom-level aggregation** (district/area view) |
| `kde_points.csv` | 5,492 | Smooth **severity surface** / contour layer |
| `validation_report.md` + `MODEL_CARD.md` | — | **Methodology / "how it works" panel** |
| `model_*.txt` (boosters) | — | Optional **backend live-scoring** of a new lat/lon |

## Per-zone fields available

**Exported now** (in geojson/priority/enriched): `impact` (0–100), `rank`, `n` (tickets),
`tier3_share` (% carriageway-blocking), `heavy_share`, `gi_z` (significance), `ranked` flag;
enriched: `mappls_street`, `mappls_locality`, `road_class`, `road_exposure`, `impact_capacity`.

**Available but NOT yet exported** (one-line add to `40_outputs.py` for richer popups):
dominant violation types, vehicle-type breakdown, `police_station`, `distinct_devices`/`officers`,
`commercial_share`, `mean_sev`, road-context flags, peak enforcement hour (caveat: enforcement timing,
not congestion timing).

## Headline numbers for the UI
- 293k citations analysed → **5,492 zones**, **792 ranked** (n≥50), **313 statistically significant** (Gi* p<0.05).
- Detection: volume-only AUC 0.59 vs **character 0.85** (the "don't enforce by count" story).
- Top capacity-adjusted corridor: **Outer Ring Road** (Marathahalli / Kadubisanahalli / Mahadevapura).
