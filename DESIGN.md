# DESIGN.md — GridLock visual system

**Direction:** civic-tech instrument panel. Dark, precise, operational. Traffic-amber as the single
signal accent (thematic for enforcement), data-forward layout.

**Type (3 families, contrast axis):**
- Display — *Bricolage Grotesque* (700–800): brand, metric numbers (tabular-nums), card scores.
- Body — *Familjen Grotesk*: prose, controls.
- Mono — *IBM Plex Mono*: labels, geohash codes, status, section eyebrows.

**Color (dark, OKLCH-spirit tokens in `web/src/theme.css`):**
- bg `#080b11` (+ faint amber/teal radial glows + grain overlay), panels `#0e1420`/`#131c2c`,
  lines `#1f2c43`/`#2b3b58`, ink `#e9eff8`, muted `#8a9bb5`.
- Accent: amber `#ffb23e` (UI signal); teal `#36d6c3` (secondary). Status: good/warn/hot.
- Impact ramp (map): blue → teal → amber → orange → red (0–100).

**Motion:** staggered card rise on load (ease-out), pulsing live-status dot, smooth Deck.gl view
transitions on zone/route focus. (Add `prefers-reduced-motion` fallback in a future hardening pass.)

**Rules honored:** no side-stripe borders (full borders + tint), no gradient text, glass used only on the
map legend overlay, metric tiles are functional (product register, not a marketing hero). Body contrast
≥4.5:1.

**Components:** topbar + persona toggle; sidebar (banner, stat grid, ROI pills, ranked/choke cards);
MapView (Deck.gl GeoJsonLayer cells, ScatterplotLayer markers, PathLayer routes, styled tooltip, legend).
