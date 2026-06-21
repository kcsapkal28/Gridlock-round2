# PRODUCT.md — GridLock

**What it is:** A dual-persona operations console for parking-induced congestion in Bengaluru, built on
293k BTP citations. It scores every ~150 m zone for traffic-flow impact and exposes two views.

**Register:** product (design serves the data/tooling, not a marketing surface).

**Personas / surfaces:**
- **BTP Command Console** — prioritise enforcement by congestion-impact, not ticket volume. Impact
  heatmap (Deck.gl) + ranked zone list + enforcement-ROI horizon.
- **Flipkart Logistics Resiliency** — detect parking friction on a delivery route, quantify SLA delay,
  reroute around choke points (live MapMyIndia Routing). Route metrics + choke-point list.

**Users:** traffic-police command staff (deploy patrols); logistics dispatchers (protect delivery SLAs).
Desktop, indoor control-room / office lighting, focused operational use → dark instrument-panel theme.

**Tone:** precise, technical, civic-tech command center. Traffic-amber signal accent. No marketing gloss.

**Tech:** Vite + React + Deck.gl + MapLibre (Carto dark base); FastAPI backend (static bundle + live
scoring + impedance-loop). Data + APIs are mapping-infrastructure only (no external knowledge sources).
