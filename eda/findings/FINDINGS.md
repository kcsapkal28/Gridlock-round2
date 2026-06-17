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

---

## Phase 1 — Data Quality (2026-06-17)

**Nulls (1.1):** 3 dead cols (100%). `data_sent_to_scita_timestamp` 86% null. The 4 validation cols all at exactly **41.97%**.

**JSON arrays (1.2):** `violation_type`/`offence_code` parse 100%, are perfectly parallel (0 length mismatches), and yield a clean **1:1 code↔label map of 27 codes** (no ambiguity). **13.4% of tickets are multi-violation** (max 12). Full map stored in DATA_DICTIONARY.

**Validation lifecycle (1.3):**
- The 4 validation columns are **perfectly co-null (corr = 1.000)** → `validation_status = NULL` means *never reviewed*, not a state.
- Status mix: NULL 41.97% (unreviewed), approved 38.67%, **rejected 16.67%**, created1 2.36%, processing 0.23%, duplicate 0.11%.
- Every *reviewed* ticket → `data_sent_to_scita = TRUE` (100%); unreviewed NULL block only 66% sent. So SCITA-send ≈ "entered the review pipeline."
- rejected+duplicate (16.8%) is **uniformly spread** (~20–23% across most stations), NOT concentrated → systemic review rate, not a few bad stations.
- **→ DECISION GATE 1A:** 16.8% is material (>10%) → built `is_valid` flag (excludes rejected/duplicate; keeps approved/created1/processing/NULL). Carry **both "all" and "valid-only"** through spatial analysis.

**Cleaning (1.4):** 298,450 → −5,380 exact-ish duplicates (1.8%, key = vehicle+5dp-coord+minute) → −0 out-of-bbox → **293,070 clean rows**. `is_valid` = 83.0%. Written to `cleaned.parquet`.

**Enforcement bias (1.5) — the headline caveat:**
- **device_id Gini = 0.788** (3,070 devices; top 10% = 66.7% of tickets; just 517 devices = 80%).
- **created_by_id Gini = 0.775** (2,666 officers; 485 = 80%).
- police_station Gini = 0.548. One device alone issues ~4,200 tickets.
- **→ DECISION GATE 1B = HIGH bias (≥0.5):** Task 4.4 (bias-normalised hotspot map) is ACTIVATED. Raw ticket density ≠ true violation density; hotspots must be cross-checked against patrol concentration.

**Plot-state note:** the persistent remote kernel retains matplotlib figure state across cells → all plotting cells now begin with `plt.close("all")`.
