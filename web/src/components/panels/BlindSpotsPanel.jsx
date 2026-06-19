import React from "react";

export default function BlindSpotsPanel({ blind, onSelect }) {
  const fs = blind?.features || [];
  return (
    <div>
      <div className="banner">
        <b>Under-enforced blind spots.</b><br />
        <span className="muted">High impact-character, low current enforcement — what patrols miss.</span>
      </div>
      <div className="section-title">{fs.length} candidate zones</div>
      {fs.slice(0, 40).map((f) => {
        const p = f.properties;
        return (
          <div key={p.gh7} className="card"
            onClick={() => onSelect({ gh7: p.gh7, lat: f.geometry.coordinates[1], lon: f.geometry.coordinates[0] })}>
            <div className="row">
              <span className="name mono">{p.gh7}</span>
              <span className="score" style={{ color: "#e85bd0" }}>{p.predicted_impact}</span>
            </div>
            <div className="meta">
              {p.n} citations · {p.distinct_devices} devices · gap {p.blind_gap}
              {p.primary_infraction_type ? <> · {p.primary_infraction_type}</> : null}
            </div>
          </div>
        );
      })}
      {!fs.length && <div className="muted">No blind-spot data loaded.</div>}
    </div>
  );
}
