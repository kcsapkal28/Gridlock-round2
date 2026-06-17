# Congestion-Severity Taxonomy

Each offence label is assigned a **carriageway-impact tier**, derived purely from the
label semantics (native to the schema — no external data). This is the weighting
backbone of any later congestion-impact score. Tiers reflect *how much a stationary
vehicle obstructs moving traffic*, NOT legal severity or fine amount.

| Tier | Meaning | Labels (offence codes) |
|------|---------|------------------------|
| **3** | High — blocks a moving lane / intersection | PARKING IN A MAIN ROAD (107), DOUBLE PARKING (109), PARKING NEAR ROAD CROSSING (104), PARKING NEAR TRAFFIC LIGHT OR ZEBRA CROSS (106), H T V PROHIBITED (147), AGAINST ONE WAY/NO ENTRY (135), STOPING ON WHITE/STOP LINE (146), U TURN PROHIBITED (134) |
| **2** | Medium — narrows carriageway / edge obstruction | WRONG PARKING (112), NO PARKING (113), PARKING OPPOSITE TO ANOTHER PARKED VEHICLE (108), PARKING OTHER THAN BUS STOP (139), PARKING NEAR BUSTOP/SCHOOL/HOSPITAL ETC (111) |
| **1** | Low — footpath / pedestrian, minimal flow impact | PARKING ON FOOTPATH (105) |
| **0** | None — document/behaviour, no flow impact | DEFECTIVE NUMBER PLATE (116), USING BLACK FILM (133), WITHOUT SIDE MIRROR (144), REFUSE TO GO FOR HIRE (124), DEMANDING EXCESS FARE (125), FAIL TO USE SAFETY BELTS (110), RIDER NOT WEARING HELMET (140), 2W/3W USING MOBILE PHONE (237), OTHER USING MOBILE PHONE (437), JUMPING TRAFFIC SIGNAL (115), VIOLATING LANE DISCIPLINE (130), OBSTRUCTING DRIVER (136), CARRYING LENGHTY MATERIAL (123) |

Notes:
- `JUMPING TRAFFIC SIGNAL`, `VIOLATING LANE DISCIPLINE`, `OBSTRUCTING DRIVER` are *moving* violations, not parking — Tier 0 for parking-congestion purposes (they're not stationary obstructions). Counted but not weighted as parking impact.
- Per-ticket we compute `max_sev` (worst tier on the ticket) and `sev_sum` (sum of tiers).
