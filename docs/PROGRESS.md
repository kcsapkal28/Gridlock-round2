# PROGRESS.md — Live Project Status

> **Read this first** at the start of every session, then JOURNAL.md (tail), then
> DECISIONS.md, then DATASET.md. **Update this last** before ending a session or
> after any milestone. Keep it short and current — this is a snapshot, not a
> history (history goes in JOURNAL.md, rationale in DECISIONS.md).

_Last updated: 2026-06-17 (post-FE score v1)_

## Current phase
**Congestion-impact score v1 built, validated, and rendered.** Next: MapMyIndia
enrichment (needs key) + demo packaging / canonical FE notebook.

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

## Done (FE) ✅
- Spec + plan (`docs/superpowers/`); ADR-004. Pipeline `fe/cells/` on Kaggle kernel.
- Score: geohash-7, is_valid, impact_intensity (steep tiers × vehicle mult), Gi* + impact-
  character ensemble (β=0.60). 5,492 cells / 1,229 ranked.
- Validated: **face validity Tier-3 lift 2.16×**, stability 0.774, approved-only 0.747,
  top-50 median 26 devices. Report `fe/findings/FE_REPORT.md`.
- Outputs: `cells.geojson`, `impact_map.html`, `priority_table.csv`, rollups, KDE;
  `mapmyindia_enrich.py` (key-gated no-op).

## Next up ⏭️
- [ ] **MapMyIndia access/key** — wire `mapmyindia_enrich.py` for road class/geofences + Mappls layer.
- [ ] Canonical FE notebook (assemble `fe/cells/` like `gridlock_eda.ipynb`) + demo packaging.
- [ ] Optional: road-segment unit as higher-fidelity enrichment once MapMyIndia is in.

## Open questions / blockers ❓
- Is MapMyIndia API access/key actually available to us? (now gating the flow leg)

## Known risks ⚠️
- `created_datetime` hour ≠ congestion timing (DATASET.md caveat 2).
- No traffic-flow column → congestion impact must be engineered & defensible to BTP.
- Enforcement bias in the long tail; external-dataset rule = disqualification.
