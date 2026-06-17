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

<!-- Add the next decision below this line. -->
