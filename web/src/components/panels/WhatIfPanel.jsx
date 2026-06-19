import React, { useMemo } from "react";

export default function WhatIfPanel({ tops, rcp, multi, onPreset }) {
  const rcpBy = useMemo(() => {
    const m = {}; (rcp?.features || []).forEach((f) => { m[f.properties.gh7] = f.properties.delay_min; });
    return m;
  }, [rcp]);
  const totT3 = useMemo(() => (tops || []).reduce((s, z) => s + z.tier3_share * z.n, 0) || 1, [tops]);
  const sel = (tops || []).filter((z) => multi.includes(z.gh7));
  const delay = Math.round(sel.reduce((s, z) =>
    s + (rcpBy[z.gh7] ?? Math.min(0.6, 0.10 + 0.35 * z.tier3_share + 0.20 * z.heavy_share) * 6), 0));
  const t3 = Math.round(sel.reduce((s, z) => s + z.tier3_share * z.n, 0) / totT3 * 100);
  const cites = sel.reduce((s, z) => s + z.n, 0);
  return (
    <div>
      <div className="banner">
        <b>What-if: clear these zones.</b><br />
        <span className="muted">See the enforcement payoff before you deploy.</span>
      </div>
      <div className="muted" style={{ marginBottom: 8 }}>
        Quick-select:{" "}
        {[5, 10, 15].map((n) => (
          <button key={n} className="pill" style={{ cursor: "pointer" }} onClick={() => onPreset(n)}>top {n}</button>))}
      </div>
      <div className="stats">
        <div className="stat"><div className="v" style={{ color: "var(--hot)" }}>{delay}<span style={{ fontSize: 13 }}> min</span></div><div className="k">Delay relieved</div></div>
        <div className="stat"><div className="v" style={{ color: "var(--amber)" }}>{t3}%</div><div className="k">Carriageway-blocking removed</div></div>
        <div className="stat"><div className="v">{sel.length}</div><div className="k">Zones selected</div></div>
        <div className="stat"><div className="v">{cites.toLocaleString()}</div><div className="k">Citations covered</div></div>
      </div>
      <div className="muted" style={{ marginTop: 10 }}>Click zones on the map to add or remove them.</div>
    </div>
  );
}
