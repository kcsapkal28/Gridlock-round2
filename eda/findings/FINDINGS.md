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

---

## Phase 3 — Temporal & Timestamp Trust (2026-06-17)

**Timestamp anomaly (3.1) — THE pivotal gate:**
- Dead window 15:00–21:00 IST holds only **0.86%** of tickets.
- It is **near-uniform across all stations (std 0.011) and devices (std 0.008)** → systemic, not behavioural.
- Overall hour profile is bimodal (2–5 AM hump + 8 AM–noon peak), collapses after 14:00. No evening enforcement.
- Per-station *active-window shape* DOES differ (HAL ~5 AM, Shivajinagar ~10 AM, City Market midnight bump) → weak station-level timing signal.
- create→modify lag median 15 min → `created_datetime` is genuine real-time capture (officer logging), i.e. it measures **enforcement activity**, not violation occurrence.
- **VERDICT:** `created_datetime` = *when BTP enforces*, NOT *when congestion happens*. Real evening parking-congestion is exactly when the data goes dark.
- **→ DECISION GATE 3 (user decision): "Keep as weak signal."** Hour-of-day usable only as a heavily-caveated, per-station enforcement-activity feature; NEVER as a literal congestion-timing proxy. Activates per-zone hour profiling in Task 5.2.
- **Time convention fixed: IST (Asia/Kolkata).**

**Calendar (3.2):**
- Range 2023-11-10 → 2024-04-08 (Nov & Apr partial — do not read as trend).
- Monthly: Nov 43k(partial), Dec 63k, Jan 65k, **Feb 52k, Mar 54k** — clear step-down in enforcement volume after January (policy/staffing shift, not necessarily fewer violations).
- Day-of-week: **Sunday highest (49.4k), Monday lowest (34k)** — weekend-skewed enforcement.

---

## Phase 4 — Spatial Hotspots (2026-06-17)

**Grid density (4.1):** 110 m cells. 293,070 tickets → 7,814 cells. **200 cells (2.56%) hold 50% of all tickets** — extreme concentration. Top cell (12.981, 77.610) = 4,298 tickets. `derived/grid_counts.parquet`.

**DBSCAN (4.2):** eps=150 m haversine, min_samples=30 → **267 clusters, 2.6% noise** (excellent). **→ DECISION GATE 4 = proceed.**
- Caveat: dense core chains into mega-clusters (cluster 2 = 80.9k tickets, Upparpet/central) — grid view stays more actionable for fine targeting.
- **Tier-3 share varies enormously by location:** Mahadevapura cl.19 = **50%** Tier-3, HAL Old Airport cl.9 = 31%, K.R. Pura 24% — vs <4% in high-volume central clusters. Early signal of high-impact≠high-volume divergence (→ 6.4). `derived/hotspots.parquet`.

**Junction linkage (4.3):** 50.7% of tickets at named BTP junctions overall — **but bimodal by station**: Upparpet 99.5% / Vijayanagara 95.2% / Shivajinagar 81.2% vs HAL Old Airport / K.R. Pura / Kodigehalli / Chikkajala = **0.0%**.
- **→ `junction_name` is an enforcement-workflow attribute, not true geography.** "No Junction" ≠ "not near a junction"; it means that unit doesn't tag junctions. Use with caution as a feature. Top junctions: Safina Plaza (15.2k), KR Market (11.4k), Elite (10.6k), Sagar Theatre (10.3k). Interactive map: `eda_out/42_hotspots.html`.

**Bias-normalised hotspots (4.4, activated by Gate 1B):**
- Top raw-count cells are each observed by **23–62 distinct devices** → genuine multi-officer hotspots, NOT single-device artifacts.
- Single-device "patrol artifact" cells are all small (n=108–588) and never reach top ranks.
- corr(raw count, distinct devices) = **0.608**.
- **VERDICT:** despite device Gini 0.79, the headline hotspots are robust; enforcement bias lives in the long tail, not the core. `derived/grid_bias.parquet`.
