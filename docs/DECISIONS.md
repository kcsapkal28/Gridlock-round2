# DECISIONS.md — Technical Decision Log (append-only)

> Append-only record of meaningful technical decisions and the reasoning behind
> them. **Before re-opening a settled question, read this file.** Add an entry
> whenever you make a choice future-you (or a fresh session) would otherwise
> re-litigate. Newest at the bottom. Never silently reverse a decision — add a
> new entry that supersedes the old one and say which `#` it replaces.

### Format
```
## ADR-NNN — <short title>
- Date: YYYY-MM-DD
- Status: accepted | superseded by ADR-XXX | proposed
- Context: what forced the decision
- Decision: what we chose
- Reasoning: why (tie to metric / rules / data fact in DATASET.md)
- Consequences: trade-offs, what this rules out
```

---

## ADR-000 — Establish project steering files
- Date: 2026-06-17
- Status: accepted
- Context: Need to prevent Claude from hallucinating dataset/metric facts and to
  preserve context across long sessions and summarization.
- Decision: Created `CLAUDE.md` (operating manual + anti-hallucination + context
  protocols), `docs/DATASET.md` (verified single source of truth for data facts),
  `docs/CONSTRAINTS.md` (rules), `docs/DECISIONS.md` (this log), `docs/PROGRESS.md`
  (live status), and `.claude/settings.json` (env defaults).
- Reasoning: Durable files are more reliable than model recollection; a single
  source of truth removes the temptation to "remember" data facts.
- Consequences: All future data claims must cite DATASET.md or a fresh measurement;
  all decisions must be logged here.

## ADR-001 — Add JOURNAL.md for chronological progress & experiment tracking
- Date: 2026-06-17
- Status: accepted
- Context: PROGRESS.md is a snapshot that gets overwritten (no history) and
  DECISIONS.md only records settled choices. Neither captures a mid-task
  checkpoint trail or per-run experiment results — a real gap for an ML
  competition with many runs and for resuming after session summarization.
- Decision: Added `docs/JOURNAL.md` as an append-only, timestamped log + an
  experiment ledger table. Updated CLAUDE.md §4 so the context protocol reads
  PROGRESS → JOURNAL → DECISIONS → DATASET, and every reported metric must trace
  to a JOURNAL run entry.
- Reasoning: Separates "what happened" (journal, durable history) from "where we
  are" (progress, snapshot) and "why" (decisions). Doubles as the anti-hallucination
  ledger — no metric without a dated row + command.
- Consequences: One more file to keep current; append a breadcrumb after each
  meaningful step. PROGRESS.md is now derived from the journal, not the primary record.

## ADR-002 — EDA decision gates (Phases 0–7)
- Date: 2026-06-17
- Status: accepted
- Context: Completed a verification-first EDA over the BTP citation log. Each phase
  ended in a decision gate. Full evidence: `eda/findings/FINDINGS.md` +
  `eda/findings/EDA_REPORT.md`. These are now settled and feed the modeling plan.
- Decisions (gate outcomes):
  1. **Cleaning:** drop 3 dead cols; dedup on `vehicle_number`+5dp-coord+minute
     (−1.8%) → **293,070 clean rows**. (Gate 0/1)
  2. **`is_valid` flag** (False iff rejected/duplicate, 83.0% True); carry BOTH
     "all" and "valid-only" through spatial analysis. rejected+duplicate is
     systemic (uniform across stations), not a few bad stations. (Gate 1A)
  3. **Enforcement bias is HIGH** (device Gini 0.79). Activated bias-normalised
     hotspot map; verdict — headline hotspots are device-breadth-robust, bias
     lives in the long tail. (Gate 1B / 4.4)
  4. **Severity taxonomy** adopted as the native impact-weighting backbone; every
     ticket ≥ Tier-2 so use `sev_sum`, not `max_sev`. (Gate 2)
  5. **`created_datetime` = enforcement timing, NOT congestion timing** (3–9 PM
     dead window is a systemic artifact). Hour-of-day kept only as a weak,
     per-zone enforcement-activity feature — never a congestion-timing proxy.
     (Gate 3, user-confirmed)
  6. **`junction_name` = workflow attribute, not geography** (bimodal by station);
     use with caution, "No Junction" ≠ "not near a junction". (4.3)
  7. **Drop/deprioritise:** `center_code` (~1:1 with `police_station`),
     `data_sent_to_scita` as quality (it's pipeline-maturity), `updated_*` /
     `validation_timestamp`, repeat-offender identity. (Gate 6)
  8. **`location` free-text = top native FE source** (road-class + POI keywords,
     zero external data). (Gate 6)
- Reasoning: tie every choice to measured evidence in FINDINGS.md and to the
  competition framing (impact, not just volume; native features only).
- Consequences: The congestion-impact score must up-weight Tier-3 / heavy-vehicle
  share and surface the high-severity micro-hotspot tail that volume-ranking misses.
  Validation must remain spatio-temporal (no random K-fold). Metric still TBD.

## ADR-003 — Round 2 is a panel-judged prototype; solution = enforcement-prioritisation system (not a leaderboard model)
- Date: 2026-06-17
- Status: accepted
- Context: Asked whether our direction matches the problem statement ("detect
  illegal-parking hotspots and quantify their impact on traffic flow to enable
  targeted enforcement"). Confirmed with user that Round 2 is **judged by a panel
  on the prototype/framework**, NOT a numeric leaderboard metric.
- Decision:
  1. Build a **demoable enforcement-prioritisation system**: hotspot detection +
     a defensible congestion-impact score + a prioritised, actionable enforcement
     map/ranking. Win condition = innovative, practical, robust, explainable.
  2. **Do NOT manufacture a supervised target / chase an invented R².** There is
     no traffic-flow target in the data; regressing on a self-invented proxy is
     explicitly disallowed by CLAUDE.md §5. "AI" here = the impact-scoring engine,
     spatial clustering, and geospatial intelligence (optional: lightweight
     per-zone hotspot-intensity forecasting to make enforcement proactive).
  3. **Correction to the impact score — ground it in road-network context, not
     violation severity alone.** "Impact on *flow*" is a property of the road.
     ImpactScore = density × severity_tier × vehicle_size_weight ×
     road_capacity_context × junction_proximity. We have the first three; the
     road-capacity/class lever is the gap. Fill it with native `location`
     road-class keywords + MapMyIndia road class / lanes / geofencing (the only
     sanctioned enrichment, explicitly encouraged for this).
- Reasoning: Aligns the build with how it will actually be evaluated and with the
  literal problem statement; avoids the two drift risks (leaderboard-style
  modeling, and a severity-only "impact" that a BTP panel would rightly question).
- Consequences: Deliverable is a prototype (scoring engine + map + ranked zones +
  methodology narrative), not a submission.csv. MapMyIndia access becomes a real
  dependency to confirm. Severity taxonomy still needs a sensitivity analysis
  (see review, ADR-002 consequences).

<!-- Add the next decision below this line. -->
