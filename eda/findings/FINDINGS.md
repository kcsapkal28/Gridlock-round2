# EDA Findings Log — GridLock Parking Congestion

Running insight log. Each entry dated. Decision-gate outcomes recorded for auditability.

---

## Phase 0 — Load & Integrity (2026-06-17)

- **Dataset confirmed:** 298,450 rows × 24 cols. `id` unique (valid primary key).
- **Coordinates: 100% parseable, 100% inside Bengaluru bbox** (lat 12.7–13.35, lon 77.3–77.9).
  - **→ DECISION GATE 0 = proceed normally.** No out-of-bbox repair task needed.
- All columns arrive as strings; deliberate casting deferred to cleaning.
- `raw.parquet` checkpoint written to `/kaggle/working` (resumability secured).
- Dead columns confirmed for drop: `description`, `closed_datetime`, `action_taken_timestamp` (100% null).
