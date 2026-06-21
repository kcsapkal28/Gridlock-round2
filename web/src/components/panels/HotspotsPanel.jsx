import React, { useMemo, useState } from "react";

export default function HotspotsPanel({ stats, tops, rcp, selected, onSelect }) {
  const [topN, setTopN] = useState(10);
  const [showAllZones, setShowAllZones] = useState(false);
  const rcpByGh = useMemo(() => {
    const m = {};
    (rcp?.features || []).forEach((f) => { m[f.properties.gh7] = f.properties.delay_min; });
    return m;
  }, [rcp]);
  const roi = useMemo(() => {
    const vals = (rcp?.features || []).map((f) => f.properties.delay_min).sort((a, b) => b - a);
    return Math.round(vals.slice(0, topN).reduce((s, v) => s + v, 0));
  }, [rcp, topN]);

  return (
    <div>
      <div className="banner">
        <b>Enforce by impact, not volume.</b><br />
        <span className="muted">293k citations → ranked congestion-impact hotspots.</span>
      </div>
      <div className="stats">
        <div className="stat"><div className="v">{stats.zones.toLocaleString()}</div><div className="k">Zones scored</div></div>
        <div className="stat"><div className="v">{stats.ranked.toLocaleString()}</div><div className="k" title="Zones with at least 50 citations — enough data to rank with confidence">Rankable zones (≥50 tickets)</div></div>
        <div className="stat"><div className="v">{stats.netDelay}<span style={{ fontSize: 13 }}> min</span></div><div className="k">Measured delay (top corridors)</div></div>
        <div className="stat"><div className="v">{roi}<span style={{ fontSize: 13 }}> min</span></div><div className="k">Relieved if top-{topN} cleared</div></div>
      </div>
      <div className="muted" style={{ marginBottom: 8 }}>
        Enforcement ROI horizon:{" "}
        {[5, 10, 12].map((n) => (
          <button key={n} className={"pill" + (n === topN ? " on" : "")} style={{ cursor: "pointer" }}
            onClick={() => setTopN(n)}>top {n}</button>
        ))}
      </div>
      <div className="section-title">Priority enforcement zones</div>
      {(showAllZones ? (tops || []) : (tops || []).slice(0, 3)).map((z) => (
        <div key={z.gh7} className={"card" + (z.gh7 === selected ? " sel" : "")} onClick={() => onSelect(z)}>
          <div className="row">
            <span className="name">#{z.rank} · <span className="mono">{z.gh7}</span></span>
            <span className="score" style={{ color: "var(--warn)" }}>{(+z.impact).toFixed(0)}<span style={{ fontSize: 10, color: "var(--muted)", fontWeight: 400 }}>/100</span></span>
          </div>
          <div className="kv">Rank · impact score</div>
          <div className="meta">
            {Math.round(z.tier3_share * 100)}% carriageway-blocking · {Math.round(z.heavy_share * 100)}% heavy · {z.n} citations
            {rcpByGh[z.gh7] != null && <> · <b style={{ color: "var(--hot)" }}>{rcpByGh[z.gh7].toFixed(1)} min delay</b></>}
          </div>
        </div>
      ))}
      {(tops || []).length > 3 && (
        <button className="btn more" style={{ marginTop: 4 }} onClick={() => setShowAllZones((v) => !v)}>
          {showAllZones ? "Show top 3 only" : `Show all ${tops.length} ranked zones`}
        </button>
      )}
    </div>
  );
}
