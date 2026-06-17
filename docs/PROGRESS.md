# PROGRESS.md — Live Project Status

> **Read this first** at the start of every session, then JOURNAL.md (tail), then
> DECISIONS.md, then DATASET.md. **Update this last** before ending a session or
> after any milestone. Keep it short and current — this is a snapshot, not a
> history (history goes in JOURNAL.md, rationale in DECISIONS.md).

_Last updated: 2026-06-18 (post-models v2)_

## Current phase
**Model complete: impact score v2 + supervised impact & detection models, evaluated.**
Running LOCALLY (Kaggle token expired — `run_local.py` rebuilds from CSV; local==remote).
Next: MapMyIndia enrichment (needs key) + frontend/system (later, per user).

## Done ✅
- Profiled the dataset; verified facts in [DATASET.md](DATASET.md).
- Steering files: CLAUDE.md, DATASET.md, CONSTRAINTS.md, DECISIONS.md, PROGRESS.md,
  .claude/settings.json (ADR-000); [JOURNAL.md](JOURNAL.md) (ADR-001).
- **Full EDA Phases 0–7** (verification-first). Cleaned to **293,070 rows**;
  built `is_valid`, severity taxonomy (`sev_sum`), grid/DBSCAN hotspots,
  bias-normalised map. Gate outcomes logged in [DECISIONS.md](DECISIONS.md) ADR-002.
  Report: `eda/findings/EDA_REPORT.md`. Notebook: `gridlock_eda.ipynb`.

## Key EDA takeaways feeding the build
- **Volume ≠ impact** — heavy/commercial vehicles & peripheral IT-corridor zones
  carry the Tier-3 (carriageway-blocking) load; a count-only heatmap misses the
  high-severity micro-hotspot tail. The impact score's value lives in that tail.
- 3 hard caveats baked into DATASET.md: enforcement bias, timestamp = enforcement
  (not congestion), `junction_name` = workflow attribute.
- Top native FE source: `location` free-text (road-class + POI keywords).

## Direction (confirmed — ADR-003)
Round 2 is a **panel-judged prototype**, not a metric leaderboard. Build a
demoable **enforcement-prioritisation system**: hotspot detection + a road-grounded
congestion-impact score + a prioritised enforcement map. No invented R² target.

## Done (FE + models) ✅
- Spec + plan (`docs/superpowers/`); ADR-004/005. Pipeline `fe/cells/` (runs on Kaggle OR local).
- **Score v2:** geohash-7, is_valid, impact_intensity (steep tiers × vehicle mult), EB-smoothed
  rates (K=40), Gi* + impact-character ensemble **β=0.75**. 5,492 cells / **792 ranked (n≥50)**.
  Face validity **Tier-3 3.15×**, stability 0.782, approved-only 0.715, top-50 median 21 devices.
- **Supervised models** (spatial gh5-CV): impact regression R² 0.15/0.34/0.98 (vol/intrinsic/full);
  hotspot-detection ROC-AUC 0.59/**0.85**/0.99. Thesis quantified: volume can't find impact-hotspots,
  character can. `fe/findings/MODEL_CARD.md`.
- Outputs: `cells.geojson`, `impact_map.html`, `priority_table.csv`, rollups, KDE, model boosters;
  notebooks `gridlock_eda.ipynb` + `gridlock_fe.ipynb`; `mapmyindia_enrich.py` (key-gated).

## Next up ⏭️
- [ ] **MapMyIndia access/key** — wire `mapmyindia_enrich.py` for road class/geofences + Mappls layer.
- [ ] Frontend / full working system (per user — later).
- [ ] Optional: road-segment unit as higher-fidelity enrichment once MapMyIndia is in.
- [ ] Re-sync artifacts to Kaggle when a fresh proxy URL is available (paste new `.kaggle_url`).

## Open questions / blockers ❓
- Is MapMyIndia API access/key actually available to us? (now gating the flow leg)

## Known risks ⚠️
- `created_datetime` hour ≠ congestion timing (DATASET.md caveat 2).
- No traffic-flow column → congestion impact must be engineered & defensible to BTP.
- Enforcement bias in the long tail; external-dataset rule = disqualification.
