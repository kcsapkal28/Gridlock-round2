# DATASET.md — Verified Data Dictionary (Single Source of Truth)

> **Rule:** Every data fact stated anywhere must trace back to this file. If a
> fact you need is missing, MEASURE it with code, then add it here with the
> command used. Do not recall data facts from memory of similar datasets.
>
> **Provenance:** All numbers below were measured directly from the file on
> **2026-06-17** with pure-Python `csv` profiling (pandas not installed at the
> time). Re-verify with `docs/../` scripts if the file changes.

---

## File

| Item | Value |
|---|---|
| Path | `jan to may police violation_anonymized791b166.csv` |
| Size | ~110 MB (109,589,874 bytes) |
| Rows | **298,449 data rows** (298,450 lines incl. header) |
| Columns | **24** |
| Encoding/format | UTF-8 CSV, comma-delimited, header row present |
| Anonymization | IDs masked: `FKID…` (id), `FKN…` (vehicle no.), `FKDEV…` (device), `FKUSR…` (user) |

⚠️ **Filename is misleading.** Despite "jan to may", the actual `created_datetime`
range is **2023-11-09 → 2024-04-08** (~5 months, Nov→Apr). Do not assume Jan–May.

⚠️ **Geographic bounding box** (Bengaluru): latitude **12.8027 – 13.2937**,
longitude **77.4426 – 77.7717**.

---

## Columns — verified null rate, cardinality, notes

| # | Column | Null % | Approx. unique | Notes |
|---|---|---|---|---|
| 1 | `id` | 0% | all unique | Masked primary key (`FKID000000…`) |
| 2 | `latitude` | 0% | high | Float, WGS84 |
| 3 | `longitude` | 0% | high | Float, WGS84 |
| 4 | `location` | 1.0% | ~10,942 | Free-text address string |
| 5 | `vehicle_number` | 0% | high | Masked |
| 6 | `vehicle_type` | 0% | **22** | Categorical (see below) |
| 7 | `description` | **100%** | 0 | **DEAD — drop** |
| 8 | `violation_type` | 0% | 991 combos | **JSON array of strings**, multi-label |
| 9 | `offence_code` | 0% | 991 combos | **JSON array of ints**, parallel to col 8 |
| 10 | `created_datetime` | 0% | high | Citation time. **UTC (`+00`).** Primary temporal axis |
| 11 | `closed_datetime` | **100%** | 0 | **DEAD — drop** |
| 12 | `modified_datetime` | 0% | high | Record-modification time. **Leakage suspect** |
| 13 | `device_id` | 0% | 3,070 | Enforcement device (masked) |
| 14 | `created_by_id` | ~0% (5 null) | 2,666 | Officer/user (masked) |
| 15 | `center_code` | 3.8% | 52 | Operational center |
| 16 | `police_station` | ~0% (5 null) | **54** | Enforcement unit |
| 17 | `data_sent_to_scita` | 0% | 2 | Boolean: TRUE 255,893 / FALSE 42,557 |
| 18 | `junction_name` | ~0% (5 null) | 169 | **~50% are "No Junction"** (147,885 no / 150,565 named) |
| 19 | `action_taken_timestamp` | **100%** | 0 | **DEAD — drop** |
| 20 | `data_sent_to_scita_timestamp` | 85.9% | 42,161 | Mostly null |
| 21 | `updated_vehicle_number` | 42.0% | high | Human-review correction trail |
| 22 | `updated_vehicle_type` | 42.0% | 22 | Human-review correction trail |
| 23 | `validation_status` | 42.0% | 5 | See below. **Leakage suspect** (post-hoc) |
| 24 | `validation_timestamp` | 42.0% | high | **Leakage suspect** (post-hoc) |

**Dead columns (100% null — drop on load):** `description`, `closed_datetime`,
`action_taken_timestamp`.

---

## Value distributions (verified)

### `violation_type` (flattened across the JSON arrays — multi-label)
| Violation | Count |
|---|---|
| WRONG PARKING | 164,977 |
| NO PARKING | 139,050 |
| PARKING IN A MAIN ROAD | 23,943 |
| DEFECTIVE NUMBER PLATE | 7,848 |
| PARKING ON FOOTPATH | 3,757 |
| PARKING NEAR BUSTOP/SCHOOL/HOSPITAL ETC | 2,403 |
| DOUBLE PARKING | 2,037 |
| PARKING NEAR ROAD CROSSING | 1,687 |
| REFUSE TO GO FOR HIRE | 887 |
| PARKING NEAR TRAFFIC LIGHT OR ZEBRA CROSS | 525 |
| PARKING OPPOSITE TO ANOTHER PARKED VEHICLE | 486 |
| (then a long tail: black-film, demanding excess fare, footpath/bus-stop variants, etc.) | <250 each |

Top 2 (Wrong + No Parking) ≈ **85%** of all violation tags. ~27 distinct violation strings total.

### `offence_code` (parallel to violation_type)
112 = Wrong Parking (164,977) · 113 = No Parking (139,050) · 107 = Main Road (23,943) ·
116 = Defective Plate (7,848) · 105 = Footpath (3,757) · 111 = Bus-stop/School/Hospital ·
109 = Double Parking · 104 = Near Road Crossing · 124 = Refuse to Hire · 106 = Traffic light/zebra.

### `vehicle_type` (22 categories, top 12)
SCOOTER 94,856 · CAR 88,870 · MOTOR CYCLE 40,811 · PASSENGER AUTO 37,813 ·
MAXI-CAB 11,372 · LGV 8,255 · GOODS AUTO 2,934 · MOPED 2,199 · PRIVATE BUS 1,633 ·
VAN 1,466 · TEMPO 1,368 · BUS (BMTC/KSRTC) 1,281 · (tail: HGV, LORRY, JEEP, TANKER, OTHERS…).
Two-wheelers + cars dominate; commercial vehicles are a meaningful minority.

### `validation_status` (5 values + null)
null 125,254 (42%) · approved 115,400 · rejected 49,754 · created1 7,044 ·
processing 678 · duplicate 320.

### `police_station` (54 stations, top 5 — central commercial core)
Upparpet 34,468 · Shivajinagar 28,044 · Malleshwaram 22,200 · HAL Old Airport 20,819 ·
City Market 17,646. (Vijayanagara, Rajajinagar, Kodigehalli, Magadi Road follow.)

### Temporal (IST = UTC+5:30)
- **By month:** 2023-11: 43,506 · 2023-12: 63,918 · 2024-01: 65,479 · 2024-02: 54,660 ·
  2024-03: 55,455 · 2024-04: 15,432 (partial month).
- **By day-of-week:** fairly even; weekends slightly higher (Sun 50,162 highest, Mon 34,680 lowest).
- **By hour (IST):** ⚠️ **Heavily skewed to mornings** (8 AM–12 noon peak, also 2–6 AM)
  with a **near-empty evening window (3 PM–9 PM)**. This almost certainly reflects
  **enforcement-drive scheduling or timestamp anonymization, NOT true congestion
  timing.** Do not treat `created_datetime` hour as ground-truth violation time.

---

## Known data-quality caveats (read before modeling)
1. No traffic-flow / speed / congestion field exists. "Impact on traffic flow"
   must be **engineered** from geometry + violation severity + context (per rules).
2. `created_datetime` hour distribution is not trustworthy as event timing (see above).
3. `violation_type` / `offence_code` are JSON arrays — parse, then explode or one-hot.
   They are paired by index; treat them as one fact, not two.
4. Leakage suspects (computed after the event): `validation_*`, `modified_datetime`,
   `updated_vehicle_*`. Exclude from features unless justified in DECISIONS.md.
5. ~50% of rows have no junction → `junction_name` is sparse signal for half the data.

---

## How to re-measure (template)
When the file changes or you need a new fact, run a small profiler and paste the
command + output here. Example skeleton:

```python
import csv; csv.field_size_limit(10**7)
from collections import Counter
with open('jan to may police violation_anonymized791b166.csv') as f:
    r = csv.DictReader(f)
    # ... measure, then record the number AND this command in DATASET.md
```
