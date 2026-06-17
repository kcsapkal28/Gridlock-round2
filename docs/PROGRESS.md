# PROGRESS.md — Live Project Status

> **Read this first** at the start of every session, then JOURNAL.md (tail), then
> DECISIONS.md, then DATASET.md. **Update this last** before ending a session or
> after any milestone. Keep it short and current — this is a snapshot, not a
> history (history goes in JOURNAL.md, rationale in DECISIONS.md).

_Last updated: 2026-06-17 (post-EDA)_

## Current phase
**EDA complete.** Next: solution framing + feature engineering for the
congestion-impact score.

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

## Next up ⏭️
- [ ] **Brainstorm + spec the congestion-impact score.** Ground it in road-network
      context: ImpactScore = density × severity × vehicle_size × road_capacity ×
      junction_proximity. We have 3 of 5 levers; road-capacity is the gap.
- [ ] Confirm **MapMyIndia access** (road class / lanes / geofencing) — now a real
      dependency for the "flow" leg.
- [ ] Native road-class FE from `location` keywords (works even without MapMyIndia).
- [ ] Severity-weighting **sensitivity analysis** (do rankings survive re-weighting?).
- [ ] Feature/scoring pipeline from EDA-blessed signals; then the map + ranked zones.

## Open questions / blockers ❓
- Is MapMyIndia API access/key actually available to us? (now gating the flow leg)

## Known risks ⚠️
- `created_datetime` hour ≠ congestion timing (DATASET.md caveat 2).
- No traffic-flow column → congestion impact must be engineered & defensible to BTP.
- Enforcement bias in the long tail; external-dataset rule = disqualification.
