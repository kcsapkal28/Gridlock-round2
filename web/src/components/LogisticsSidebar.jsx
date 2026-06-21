import React from "react";
import { slaColor } from "../lib/color.js";

// Sample delivery routes across Bengaluru that cross known hotspot corridors.
const PRESETS = [
  { name: "Koramangala → Whitefield (ORR)", wp: [{ lat: 12.935, lng: 77.622 }, { lat: 12.997, lng: 77.669 }] },
  { name: "City Market → Hebbal", wp: [{ lat: 12.964, lng: 77.578 }, { lat: 13.035, lng: 77.589 }] },
  { name: "Electronic City → KR Puram", wp: [{ lat: 12.842, lng: 77.660 }, { lat: 13.008, lng: 77.696 }] },
];

export default function LogisticsSidebar({ route, busy, onAnalyze, onFocus }) {
  return (
    <div className="sidebar">
      <div className="banner">
        <b>Protect delivery SLAs.</b><br />
        <span className="muted">Detect parking-induced friction on a fleet route and reroute around it.</span>
      </div>

      <div className="section-title">Simulate a delivery route</div>
      {PRESETS.map((p) => (
        <button key={p.name} className="btn alt" style={{ marginBottom: 6, textAlign: "left" }}
          disabled={busy} onClick={() => onAnalyze(p.wp)}>{p.name}</button>
      ))}
      {busy && <div className="muted" style={{ marginTop: 8 }}>Analyzing route impedance…</div>}

      {route && (
        <>
          <div className="stats" style={{ marginTop: 14 }}>
            <div className="stat">
              <div className="metric-big" style={{ color: "var(--hot)" }}>{route.impedance_delay_mins}<span style={{ fontSize: 14 }}> min</span></div>
              <div className="k">Total delay added by parking on this route</div>
            </div>
            <div className="stat">
              <div className="metric-big risk" style={{ color: slaColor[route.sla_risk] }}>{route.sla_risk}</div>
              <div className="k">SLA breach risk</div>
            </div>
          </div>
          <div className="stat" style={{ marginBottom: 12 }}>
            <div className="v" style={{ color: "var(--good)" }}>{route.minutes_saved_by_detour}<span style={{ fontSize: 13 }}> min</span></div>
            <div className="k">Avoidable by rerouting around the worst choke ({route.n_affected} choke cells on route)</div>
          </div>

          {route.routing_live === false && (
            <div className="muted" style={{ fontSize: 11, marginBottom: 8 }}>
              Straight-line preview through the choke zones — add a MapMyIndia key for road-accurate routing.
            </div>
          )}
          <div className="muted" style={{ marginBottom: 8 }}>
            <span style={{ color: "var(--hot)" }}>━</span> blocked route ·
            <span style={{ color: "var(--good)" }}> ━</span> optimized detour ·
            <span style={{ color: "#5dcaa5" }}> ●</span> pickup ·
            <span style={{ color: "#78a2ff" }}> ●</span> drop
          </div>

          <div className="section-title">Choke points on this route</div>
          {(route.affected_cells || []).length > 0 && <div className="muted" style={{ marginBottom: 6, fontSize: 11 }}>Tap a choke point to locate it on the map.</div>}
          {(route.affected_cells || []).slice(0, 12).map((c) => (
            <div key={c.gh7} className="card" onClick={() => onFocus?.(c.lat, c.lon)}>
              <div className="row">
                <span className="name mono">{c.gh7}</span>
                <span className="score" style={{ color: "var(--hot)" }}>+{c.delay_min.toFixed(1)}<span style={{ fontSize: 10, color: "var(--muted)", fontWeight: 400 }}> min</span></span>
              </div>
              <div className="meta">{c.primary_infraction_type || "parking"} · {c.dominant_vehicle_class || "mixed"} · impact {c.impact}/100</div>
            </div>
          ))}
          {route.n_affected === 0 && <div className="muted">No active hotspots on this route — clear run. ✅</div>}
        </>
      )}
    </div>
  );
}
