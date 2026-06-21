import React, { useState } from "react";

export default function BlindSpotsPanel({ blind, onSelect }) {
  const fs = blind?.features || [];
  const [limit, setLimit] = useState(5);
  const shown = fs.slice(0, limit);
  return (
    <div>
      <div className="banner">
        <b>Under-enforced blind spots.</b><br />
        <span className="muted">Zones flagged by their <b>character</b> — high carriageway-blocking severity,
        heavy-vehicle share and risky road context — but with <b>low current enforcement</b>. These are
        high-impact spots that a ticket-volume view never surfaces.</span>
      </div>
      <div className="section-title">{fs.length} candidate zones · showing {Math.min(limit, fs.length)}</div>
      {shown.map((f) => {
        const p = f.properties;
        return (
          <div key={p.gh7} className="card"
            onClick={() => onSelect({ gh7: p.gh7, lat: f.geometry.coordinates[1], lon: f.geometry.coordinates[0] })}>
            <div className="row">
              <span className="name mono">{p.gh7}</span>
              <span className="score" style={{ color: "#e85bd0" }}>{p.predicted_impact}<span style={{ fontSize: 10, color: "var(--muted)", fontWeight: 400 }}>/100</span></span>
            </div>
            <div className="kv">Predicted impact</div>
            <div className="meta">{(+p.n).toLocaleString()} citations · {p.distinct_devices} devices · coverage gap {p.blind_gap}
              {p.primary_infraction_type ? <> · {p.primary_infraction_type}</> : null}</div>
          </div>
        );
      })}
      {!fs.length && <div className="muted">No blind-spot data loaded.</div>}
      {fs.length > 5 && (
        <button className="btn more" style={{ marginTop: 4 }}
          onClick={() => setLimit((l) => (l >= fs.length ? 5 : l + 10))}>
          {limit >= fs.length ? "Show top 5 only" : `Show more (${fs.length - limit} left)`}
        </button>
      )}
    </div>
  );
}
