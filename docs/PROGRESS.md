# PROGRESS.md — Live Project Status

> **Read this first** at the start of every session, then DECISIONS.md, then
> DATASET.md. **Update this last** before ending a session or after any milestone.
> Keep it short and current — this is a status board, not a history (history goes
> in DECISIONS.md).

_Last updated: 2026-06-17_

## Current phase
Project setup / data understanding.

## Done ✅
- Located and profiled the dataset (298,449 rows, 24 cols). Verified facts
  recorded in [DATASET.md](DATASET.md).
- Created steering files: CLAUDE.md, DATASET.md, CONSTRAINTS.md, DECISIONS.md,
  PROGRESS.md, .claude/settings.json (see [DECISIONS.md](DECISIONS.md) ADR-000).

## In progress 🔧
- (none yet)

## Next up ⏭️
- [ ] Confirm the **official evaluation metric** for Round 2 → record in DECISIONS.md.
- [ ] Decide solution framing: hotspot detection + congestion-impact score
      (spatial clustering / heatmap) vs. a predictive model. Brainstorm first.
- [ ] Set up reproducible Python env (venv + pinned requirements).
- [ ] Build the cleaning + feature-engineering pipeline (drop dead cols, parse
      JSON violation arrays, derive time/space features natively).

## Open questions / blockers ❓
- What exactly does Round 2 score on? (deliverable quality vs. a leaderboard metric)
- Is MapMyIndia API access/key actually available to us?

## Known risks ⚠️
- `created_datetime` hour is not trustworthy as event timing (see DATASET.md caveats).
- No traffic-flow column exists → congestion impact must be engineered & defensible.
- External-dataset rule = disqualification risk (see CONSTRAINTS.md).
