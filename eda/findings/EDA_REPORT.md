# GridLock 2.0 — Parking-Induced Congestion: EDA Report

**Problem:** Detect illegal-parking hotspots and quantify their impact on traffic flow, to enable
targeted BTP enforcement. **Data:** one anonymized BTP citation log (no external data permitted).

---

## 1. Dataset at a glance
- **293,070 clean citations** (from 298,450 raw; −1.8% exact-ish duplicates), 24 columns.
- **Window:** 2023-11-10 → 2024-04-08 IST (Nov & Apr partial). Geography: all 100% inside Bengaluru.
- This is a **police enforcement log, not a sensor feed** — it records where/when officers *ticketed*,
  which is the central interpretive caveat throughout.

## 2. Data-quality verdict
- `id` unique; coordinates 100% valid. 3 columns 100%-null and dropped (`description`,
  `closed_datetime`, `action_taken_timestamp`).
- `violation_type`/`offence_code` are perfectly parallel JSON arrays → clean **27-code dictionary**;
  13.4% of tickets are multi-violation.
- Validation block (4 cols) is perfectly co-null → `validation_status=NULL` means *unreviewed* (42%).
  **16.8% of reviewed tickets are rejected/duplicate** (uniform across stations) → `is_valid` flag built;
  spatial analysis carried both all and valid-only (83% valid).

## 3. The three caveats that constrain any model
1. **Enforcement bias (device Gini 0.79, officer 0.78).** Tickets are highly concentrated in a minority
   of devices/officers. *Mitigation:* the top hotspots are each seen by 23–62 distinct devices
   (corr count↔breadth 0.61) → **headline hotspots are robust; bias lives in the long tail.**
2. **Timestamps measure enforcement, not congestion.** The 3–9 PM dead window (0.86% of tickets) is
   uniform across all stations (std 0.011) → systemic scheduling artifact. `created_datetime` is genuine
   capture time of *patrol activity*. **Decision: hour-of-day kept only as a weak, per-zone
   enforcement-activity feature — never as a congestion-timing proxy.**
3. **`junction_name` is a workflow attribute, not geography.** 50.7% "at a junction" overall, but bimodal
   by station (Upparpet 99.5% vs HAL Old Airport 0.0%). "No Junction" ≠ "not near a junction."

## 4. Severity taxonomy (native impact weighting)
Every offence label mapped to a carriageway-impact tier from label semantics alone (Tier 3 blocks a moving
lane … Tier 0 no flow impact). Result: **every ticket is ≥ Tier-2** (Wrong/No Parking on nearly all);
**8.76% reach Tier-3.** `max_sev` is near-binary → use `sev_sum` for gradation.

## 5. Where the hotspots are
- **Extreme concentration: 200 of 7,814 110 m-cells (2.56%) hold 50% of all tickets.**
- DBSCAN (150 m): 267 clusters, 2.6% noise. Dense core chains into mega-clusters (grid view is finer).
- Top volume hotspots: Upparpet/central, Vijayanagara, Shivajinagar, HAL Old Airport.
- Top junctions: Safina Plaza (15.2k), KR Market (11.4k), Elite (10.6k), Sagar Theatre (10.3k).
- Interactive map: `eda/eda_out/42_hotspots.html`.

## 6. Where the IMPACT is (the flagship insight)
**Volume ≠ congestion impact.**
- **By vehicle:** BMTC/KSRTC buses are **46% Tier-3**, private buses 31%, tempos/HGVs/lorries ~25% —
  vs scooters 4.4% (the volume leader). Heavy/commercial vehicles drive carriageway-blocking.
- **By place:** peripheral IT-corridor stations lead per-ticket severity (Whitefield 3.74, Mahadevapura
  3.60, HAL 3.15) over the high-volume central core.
- **Micro-hotspots:** a high-severity tail of small cells is **near-100% Tier-3** yet ranks ~900th by
  volume (e.g. a K.R. Pura cell: 55 tickets, all 55 Tier-3). **Invisible to count-based enforcement** —
  this tail is precisely where an impact score earns its value (cell-level corr count↔impact = 0.969 in bulk).

## 7. Signals VALIDATED for a future congestion-impact score
- Spatial density (grid/DBSCAN), **device-breadth-validated** to separate demand from patrol.
- Severity weighting from the native taxonomy (esp. Tier-3 share, heavy-vehicle share).
- `location` free-text **road-class/POI keywords** (main road 22%, circle 20%, cross 12%, junction 10%,
  market/mall/hospital) — rich, fully native, zero external data.
- Per-zone enforcement rhythm (weak, zone-level only).

## 8. Signals NOT to trust / drop
- Hour-of-day as congestion timing (enforcement-scheduled). • `data_sent_to_scita` as quality
  (pipeline-maturity, time-dependent). • `junction_name` as true proximity (workflow artifact).
- Drop: `description`, `closed_datetime`, `action_taken_timestamp` (dead); `center_code` (~1:1 with
  `police_station`); `updated_*`/`validation_timestamp` low-value beyond the `is_valid` flag;
  repeat-offender identity (3.1% of tickets, mobile).

---
*Reproducible notebook: `gridlock_eda.ipynb` (also uploaded to Kaggle `/kaggle/working`). Full evidence
log: `eda/findings/FINDINGS.md`. Column decisions: `eda/findings/DATA_DICTIONARY.md`. Severity tiers:
`eda/findings/SEVERITY_TAXONOMY.md`.*
