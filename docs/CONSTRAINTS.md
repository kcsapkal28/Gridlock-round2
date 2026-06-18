# CONSTRAINTS.md — Hackathon Rules & Disqualification Triggers

> Read before proposing any data source, feature, or integration. When in doubt,
> the conservative reading wins — a disqualification ends the project.

## Event
- **Hackathon:** Flipkart GridLock 2.0 — Round 2, Prototype Phase (virtual submission).
- **Host & partners:** Flipkart + Bengaluru Traffic Police (BTP).
- **Goal:** Innovative, scalable, practical, robust AI prototype for Bengaluru
  traffic. Deliverable = working software OR highly detailed technical framework.
- **Stakes:** Must finish **Top 10** to qualify for the onsite finale at Flipkart HQ.

## Problem statement — Parking-Induced Congestion
On-street illegal / spillover parking near commercial areas, metro stations, and
events chokes carriageways and intersections across Bengaluru.

Current pain points:
1. Enforcement is entirely **patrol-based and reactive**.
2. **No historical or real-time map/heatmap** correlates parking violations to
   actual traffic flow or congestion impact.
3. Authorities **cannot systematically prioritize** high-impact enforcement zones.

**Core direction:** *How can AI-driven parking intelligence detect illegal-parking
hotspots and quantify their impact on traffic flow to enable targeted enforcement?*

## HARD RULES (disqualification)

### 🔴 NO EXTERNAL DATASETS
Use **ONLY** organizer-provided data. Explicitly forbidden, results in **immediate
disqualification**:
- External speed / traffic-flow datasets
- Historical weather data
- Web-scraped event tables
- Alternative / third-party traffic logs
- Any model trained or merged on outside data

This is also an **anti-hallucination boundary**: if you find yourself wanting to
pull in a "helpful" external table, stop — it is forbidden, not a gap to fill.

### 🟢 ALLOWED EXTENSIONS
- **Feature engineering & mathematical logic derived natively** from the given
  schema features.
- **MapMyIndia API integration** — **mapping-infrastructure APIs ONLY**:
  **Snap-to-Road, Distance Matrix, Routing, Geocoding** (incl. reverse-geocoding) permitted.
  - **NOT permitted:** knowledge-enrichment APIs that inject external data —
    **Places/Nearby, Live Traffic, Weather, Demographics** (external knowledge → same
    disqualification spirit as the no-external-datasets rule).
  - Verify each endpoint/field exists before relying on it (anti-hallucination).

## Practical implications for our build
- "Impact on traffic flow" has **no direct column** → must be a defensible
  **engineered/derived metric** (geometry, road-class via MapMyIndia, violation
  severity, spatio-temporal density), not an imported traffic feed.
- Any congestion proxy must be **explainable** to BTP — we have to justify the
  formula, not just the output.
- Keep a clear line in code/docs between "organizer data", "MapMyIndia
  enrichment", and "engineered features" so compliance is auditable.
