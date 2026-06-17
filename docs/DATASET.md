# DATASET.md — Verified Data Dictionary (Single Source of Truth)

> **Rule:** Every data fact stated anywhere must trace back to this file. If a
> fact you need is missing, MEASURE it with code, then add it here with the
> command used. Do not recall data facts from memory of similar datasets.
>
> **Provenance:** Initial profiling 2026-06-17 (pure-Python csv). **Superseded
> and extended by the full EDA (Phases 0–7), completed 2026-06-17.** The EDA is
> authoritative. Full evidence: [`eda/findings/EDA_REPORT.md`](../eda/findings/EDA_REPORT.md)
> (exec summary), [`eda/findings/FINDINGS.md`](../eda/findings/FINDINGS.md) (per-phase
> evidence log), [`eda/findings/DATA_DICTIONARY.md`](../eda/findings/DATA_DICTIONARY.md)
> (column decisions + 27-code map), [`eda/findings/SEVERITY_TAXONOMY.md`](../eda/findings/SEVERITY_TAXONOMY.md)
> (tier map). Reproducible notebook: `gridlock_eda.ipynb`. Plots/derived: `eda/eda_out/`.

---

## ⭐ The one framing that governs everything
This is a **police enforcement log, not a sensor feed.** It records where/when
officers *ticketed*, not where/when congestion *occurred*. Every downstream
interpretation must respect this. (EDA §1, FINDINGS Phase 3.)

---

## File

| Item | Value |
|---|---|
| Path | `jan to may police violation_anonymized791b166.csv` |
| Size | ~110 MB (109,589,874 bytes) |
| Rows (raw) | **298,450** |
| Rows (clean) | **293,070** — after −5,380 (1.8%) exact-ish duplicates (dedup key = `vehicle_number` + 5dp-rounded coord + minute); 0 out-of-bbox dropped |
| Columns | **24** (3 dead → effectively 21) |
| Encoding/format | UTF-8 CSV, comma-delimited, header row; all columns read as strings (cast downstream) |
| Anonymization | IDs masked: `FKID…` (id), `FKN…` (vehicle no.), `FKDEV…` (device), `FKUSR…` (user) |

⚠️ **Filename is misleading.** Window is **2023-11-10 → 2024-04-08 IST** (Nov &
Apr are partial months — do not read month totals as a trend). Not Jan–May.

⚠️ **Geographic extent (actual data):** latitude **12.8027 – 13.2937**, longitude
**77.4426 – 77.7717**. 100% of rows fall inside the Bengaluru validation bbox
(lat 12.7–13.35, lon 77.3–77.9). **Time convention: IST (Asia/Kolkata).**

---

## Columns — verified

| # | Column | Null % (raw) | Decision | Notes |
|---|---|---|---|---|
| 1 | `id` | 0% | **KEY** | Unique, verified primary key |
| 2 | `latitude` | 0% | KEEP (spatial) | 100% valid, in-bbox |
| 3 | `longitude` | 0% | KEEP (spatial) | 100% valid |
| 4 | `location` | ~1% | KEEP (aux) | Free-text address — **rich native FE goldmine** (see below) |
| 5 | `vehicle_number` | 0% | KEEP | Masked; reliable (only 1.0% corrected on review) |
| 6 | `vehicle_type` | 0% | KEEP | 22 categories |
| 7 | `description` | **100%** | **DROP** | Dead |
| 8 | `violation_type` | 0% | KEEP (parse) | JSON array of labels, multi-label |
| 9 | `offence_code` | 0% | KEEP (parse) | JSON array of ints, **perfectly parallel** to col 8 |
| 10 | `created_datetime` | 0% | KEEP (trust-gated) | UTC `+00`. **= enforcement time, NOT congestion time** |
| 11 | `closed_datetime` | **100%** | **DROP** | Dead |
| 12 | `modified_datetime` | 0% | KEEP (aux) | create→modify median lag 15 min → real-time capture. No extra signal; leakage suspect |
| 13 | `device_id` | 0% | KEEP (bias) | 3,070 devices. **Gini 0.788** |
| 14 | `created_by_id` | ~0% | KEEP (bias) | 2,666 officers. **Gini 0.775** |
| 15 | `center_code` | 3.8% | DROP candidate | 52 codes, **~1:1 with `police_station`** → redundant |
| 16 | `police_station` | ~0% | KEEP | 54 stations. Gini 0.548 |
| 17 | `data_sent_to_scita` | 0% | CAUTION | TRUE 87%. **Pipeline-maturity flag (time-dependent), NOT quality** |
| 18 | `junction_name` | ~0% | KEEP (caution) | 169 named junctions or "No Junction". **Workflow attribute, not geography** |
| 19 | `action_taken_timestamp` | **100%** | **DROP** | Dead |
| 20 | `data_sent_to_scita_timestamp` | ~86% | low value | No extra signal beyond col 17 |
| 21 | `updated_vehicle_number` | ~42% | low value | Review-correction trail |
| 22 | `updated_vehicle_type` | ~42% | low value | Review-correction trail |
| 23 | `validation_status` | ~42% | KEEP (→`is_valid`) | See lifecycle below. Leakage suspect (post-hoc) |
| 24 | `validation_timestamp` | ~42% | low value | Leakage suspect (post-hoc) |

**Dead columns (drop on load):** `description`, `closed_datetime`, `action_taken_timestamp`.

### Derived columns (added in cleaning)
- `created_dt` — tz-aware datetime parsed from `created_datetime`.
- `validation_status_clean` — `validation_status` with nulls coalesced to `"NULL"`.
- `is_valid` — bool, **False iff status ∈ {rejected, duplicate}**; **83.0% True**.
- `max_sev`, `sev_sum` — per-ticket severity (see taxonomy). Stored `derived/severity.parquet`.

---

## violation_type / offence_code — 27 codes, verified 1:1
- Arrays parse 100%, **perfectly parallel** (0 length mismatches). Clean **1:1 map
  of 27 offence codes ↔ labels** (no ambiguity). **13.4% of tickets are multi-violation** (max 12).
- Full code↔label table: [`eda/findings/DATA_DICTIONARY.md`](../eda/findings/DATA_DICTIONARY.md).
- Top labels (clean): WRONG PARKING 161.9k + NO PARKING 136.6k ≈ **90% of tags**;
  PARKING IN A MAIN ROAD 23.4k (leading Tier-3). DEFECTIVE NUMBER PLATE never appears alone.

## Severity taxonomy (native congestion-impact weighting)
Each label → carriageway-impact tier from semantics alone (zero external data).
Full map: [`eda/findings/SEVERITY_TAXONOMY.md`](../eda/findings/SEVERITY_TAXONOMY.md).
- **Tier 3** (blocks moving lane/intersection): Main Road, Double, Near Crossing,
  Near Traffic Light/Zebra, HTV Prohibited, Against One-Way, Stop-Line, U-Turn.
- **Tier 2** (narrows carriageway): Wrong Parking, No Parking, Opposite Parked, Other-than-Bus-Stop, Near Bus-stop/School/Hospital.
- **Tier 1**: Footpath. **Tier 0**: document/behaviour/moving violations (no parking-flow impact).
- **Every ticket is ≥ Tier-2** (Wrong/No Parking floor) → `max_sev` ∈ {2,3}, near-binary.
  **8.76% reach Tier-3.** **Use `sev_sum` for gradation, not `max_sev`.**

## validation_status — lifecycle
- The 4 validation columns are **perfectly co-null (corr 1.000)** → `NULL` = *never
  reviewed*, not a state.
- Mix: **NULL 41.97%** (unreviewed) · approved 38.67% · **rejected 16.67%** ·
  created1 2.36% · processing 0.23% · duplicate 0.11%.
- rejected+duplicate (16.8%) is **uniform across stations** (~20–23%) → systemic
  review rate, not a few bad stations → justified the `is_valid` flag (carry both
  "all" and "valid-only" through spatial work).

## vehicle_type (22 categories, clean counts)
SCOOTER 92.9k · CAR 87.4k · MOTOR CYCLE 39.9k · PASSENGER AUTO 37.3k (two-wheelers
≈ 47% of tickets). Commercial/heavy (buses, tempo, HGV, lorry) are a minority **but
dominate Tier-3** (see impact facts).

---

## Spatial structure (verified)
- **Extreme concentration: 200 of 7,814 110 m-cells (2.56%) hold 50% of all tickets.**
  Top cell (12.981, 77.610) = 4,298 tickets. (`derived/grid_counts.parquet`.)
- DBSCAN (eps 150 m haversine, min_samples 30): **267 clusters, 2.6% noise.** Dense
  core chains into mega-clusters (grid view is finer for targeting). (`derived/hotspots.parquet`.)
- Top volume hotspots: Upparpet/central, Vijayanagara, Shivajinagar, HAL Old Airport.
  Top junctions: Safina Plaza 15.2k, KR Market 11.4k, Elite 10.6k, Sagar Theatre 10.3k.
- Interactive map: `eda/eda_out/42_hotspots.html`.

## Volume ≠ congestion impact (flagship insight)
- **By vehicle (Tier-3 rate):** BMTC/KSRTC bus **46.3%**, private bus 30.7%, tempo
  26.7%, HGV 25.3%, lorry 25.0% — vs scooter 4.4%, motorcycle 5.4%, car 11.3%.
- **By place (mean severity):** peripheral IT-corridor stations lead — Whitefield
  3.74, Mahadevapura 3.60, HAL 3.15 — over the high-volume central core.
- **Micro-hotspots:** cell-level corr(count, Σsev) = **0.969** (volume ≈ impact in
  bulk), BUT a high-severity tail is **near-100% Tier-3 yet ranks ~900th by volume**
  (e.g. a K.R. Pura cell: 55 tickets, all 55 Tier-3). **Invisible to count-based
  enforcement — this tail is where an impact score earns its value.** (`derived/divergence.parquet`.)

---

## ⚠️ The three caveats that constrain any model (read before modeling)
1. **Enforcement bias** (device Gini 0.79, officer 0.78): tickets concentrate in a
   minority of devices/officers. *Mitigation verified:* top hotspots are each seen
   by 23–62 distinct devices (corr count↔breadth 0.61) → **headline hotspots are
   robust; bias lives in the long tail.** (`derived/grid_bias.parquet`.)
2. **Timestamps measure enforcement, not congestion.** 3–9 PM dead window (0.86% of
   tickets) is uniform across stations (std 0.011) → systemic scheduling artifact.
   **Decision: hour-of-day kept ONLY as a weak, per-zone enforcement-activity
   feature — never as a congestion-timing proxy.**
3. **`junction_name` is a workflow attribute, not geography.** 50.7% "at a junction"
   overall but bimodal by station (Upparpet 99.5% vs HAL 0.0%). "No Junction" ≠ "not
   near a junction." Use with caution.

## location free-text — top native FE goldmine
99.1% present, 10,935 unique. Keyword coverage: "road" 92.7%, "main road" 22.0%,
"circle" 19.7%, "nagar" 46.6%, "cross" 12.3%, "junction" 9.6%, "metro" 0.4%; POIs:
mall 5.7%, market 3.3%, hospital 1.6%. **Road-class + POI context with zero external
data** — top feature-engineering candidate.

## Signals to DROP / not trust
Hour-of-day as congestion timing · `data_sent_to_scita` as quality · `junction_name`
as true proximity · `description`/`closed_datetime`/`action_taken_timestamp` (dead) ·
`center_code` (~1:1 with `police_station`) · `updated_*`/`validation_timestamp`
(low value beyond `is_valid`) · repeat-offender identity (3.1% of tickets, mobile —
not a hotspot driver).

---

## How to re-measure (template)
When the file changes or you need a new fact, prefer re-running the notebook or a
cell from `eda/cells/`. For a quick one-off:
```python
import csv; csv.field_size_limit(10**7)
from collections import Counter
with open('jan to may police violation_anonymized791b166.csv') as f:
    r = csv.DictReader(f)
    # ... measure, then record the number AND the command here (and in JOURNAL.md if a run)
```
