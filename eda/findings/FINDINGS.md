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

---

## Phase 2 — Univariate & Severity (2026-06-17)

**Univariate (2.1):**
- Vehicles: SCOOTER 92.9k, CAR 87.4k, MOTOR CYCLE 39.9k, PASSENGER AUTO 37.3k dominate. Two-wheelers ≈ 47% of all tickets.
- Violations: WRONG PARKING 161.9k + NO PARKING 136.6k ≈ 90% of tags; PARKING IN A MAIN ROAD 23.4k is the leading Tier-3.
- `center_code` top-15 distribution mirrors `police_station` almost exactly → likely a near-1:1 mapping (candidate redundant feature).

**Co-occurrence (2.2):** Dominant bundles are the carriageway-blockers riding on generic tags:
WRONG PARKING + PARKING IN A MAIN ROAD (15.3k), NO PARKING + PARKING IN A MAIN ROAD (11.0k).
DEFECTIVE NUMBER PLATE never appears alone (always with wrong/no parking).

**Severity taxonomy (2.3):** Tiers assigned from label semantics (see SEVERITY_TAXONOMY.md).
- **max_sev takes only {2,3}** — every ticket has ≥1 Tier-2 violation; **8.76% reach Tier-3**. So `max_sev` is near-binary; use `sev_sum` for gradation.
- **→ DECISION GATE 2 = proceed.** Guard confirmed only the 13 known document/behaviour/moving labels default to Tier 0; no Tier-2/3 label under-scored.
- Stored `derived/severity.parquet` (id, is_valid, max_sev, sev_sum).
