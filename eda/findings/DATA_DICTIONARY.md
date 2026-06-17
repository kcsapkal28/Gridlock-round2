# Data Dictionary — BTP Parking Violations

Source: `/kaggle/input/datasets/kartikeysapkal/gridlock-round2-csv/jan to may police violation_anonymized791b166.csv`
Shape: **298,450 rows × 24 columns**. All columns read as `object` (str); cast deliberately downstream.

| # | Column | Meaning | Example | Null % (raw) | Decision |
|---|--------|---------|---------|--------------|----------|
| 1 | id | Primary key (unique, verified) | FKID000000 | 0 | KEY |
| 2 | latitude | Violation lat (100% in Bengaluru bbox) | 12.9255567 | 0 | KEEP (spatial) |
| 3 | longitude | Violation lon | 77.618665 | 0 | KEEP (spatial) |
| 4 | location | Free-text address | "18th Main Road, Koramangala…" | ~1 | KEEP (aux) |
| 5 | vehicle_number | Anonymised plate | FKN00GL0000 | 0 | KEEP (repeat-offender) |
| 6 | vehicle_type | 22 categories | CAR | 0 | KEEP |
| 7 | description | — | NaN | 100 | **DROP** (dead) |
| 8 | violation_type | JSON array of labels (multi-label) | ["WRONG PARKING",…] | 0 | KEEP (parse) |
| 9 | offence_code | JSON array, parallel to violation_type | [112,104] | 0 | KEEP (parse) |
| 10 | created_datetime | Ticket creation (UTC +00) | 2023-11-20 00:28:46+00 | 0 | KEEP (temporal; trust gated) |
| 11 | closed_datetime | — | NaN | 100 | **DROP** (dead) |
| 12 | modified_datetime | Last modification (UTC) | 2023-11-28 04:48:04+00 | 0 | KEEP (aux) |
| 13 | device_id | Enforcement device (~3070) | FKDEV00000 | 0 | KEEP (bias) |
| 14 | created_by_id | Officer (~2666) | FKUSR00000 | ~0 | KEEP (bias) |
| 15 | center_code | 52 codes | 9 | ~3.8 | KEEP |
| 16 | police_station | 54 stations | Madiwala | ~0 | KEEP (enforcement unit) |
| 17 | data_sent_to_scita | Sent to SCITA integration (TRUE/FALSE) | TRUE | 0 | KEEP (probe meaning) |
| 18 | junction_name | 169 named BTP junctions or "No Junction" | No Junction | ~0 | KEEP (junction linkage) |
| 19 | action_taken_timestamp | — | NaN | 100 | **DROP** (dead) |
| 20 | data_sent_to_scita_timestamp | When sent to SCITA | NaN | ~86 | KEEP (sparse, probe) |
| 21 | updated_vehicle_number | Corrected plate after review | FKN00GL0000 | ~42 | KEEP (validation block) |
| 22 | updated_vehicle_type | Corrected type after review | MAXI-CAB | ~42 | KEEP (validation block) |
| 23 | validation_status | approved/rejected/created1/processing/duplicate | approved | ~42 | KEEP (validity filter) |
| 24 | validation_timestamp | When reviewed | 2023-11-30 03:08:24+00 | ~42 | KEEP (validation block) |

Offence-code ↔ label map: populated in Phase 1 Task 1.2.
