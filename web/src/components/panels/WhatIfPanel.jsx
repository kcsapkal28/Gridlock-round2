import React, { useMemo, useState } from "react";

// Per-zone on-site enforcement time (mirrors the backend patrol estimate), used to size effort.
const dwellMin = (z) => (8 + Math.min(12, (z.n || 0) / 60)) * (1 + 0.4 * z.tier3_share + 0.3 * z.heavy_share);

export default function WhatIfPanel({ tops, rcp, multi, onPreset }) {
  const [eff, setEff] = useState(80);          // enforcement effectiveness %
  const f = eff / 100;

  const rcpBy = useMemo(() => {
    const m = {}; (rcp?.features || []).forEach((x) => { m[x.properties.gh7] = x.properties.delay_min; });
    return m;
  }, [rcp]);

  const totT3 = useMemo(() => (tops || []).reduce((s, z) => s + z.tier3_share * z.n, 0) || 1, [tops]);
  const totImpact = useMemo(() => (tops || []).reduce((s, z) => s + z.impact, 0) || 1, [tops]);

  const sel = (tops || []).filter((z) => multi.includes(z.gh7));
  const delayRaw = sel.reduce((s, z) =>
    s + (rcpBy[z.gh7] ?? Math.min(0.6, 0.10 + 0.35 * z.tier3_share + 0.20 * z.heavy_share) * 6), 0);
  const delay = Math.round(delayRaw * f);
  const t3 = Math.round((sel.reduce((s, z) => s + z.tier3_share * z.n, 0) / totT3) * 100 * f);
  const heavyCites = Math.round(sel.reduce((s, z) => s + z.heavy_share * z.n, 0) * f);
  const congShare = Math.round((sel.reduce((s, z) => s + z.impact, 0) / totImpact) * 100);
  const officerHrs = Math.round(sel.reduce((s, z) => s + dwellMin(z), 0) / 60 * 10) / 10;
  const cites = Math.round(sel.reduce((s, z) => s + z.n, 0) * f);

  return (
    <div>
      <div className="banner">
        <b>What-if: clear these zones.</b><br />
        <span className="muted">Model the enforcement payoff before you deploy. Set how effectively a
        zone gets cleared, then pick zones (quick-select or tap the map).</span>
      </div>

      <div className="muted" style={{ marginBottom: 4 }}>
        Quick-select:{" "}
        {[3, 5, 10, 15].map((n) => (
          <button key={n} className="pill" style={{ cursor: "pointer" }} onClick={() => onPreset(n)}>top {n}</button>))}
      </div>

      <div className="wi-slider">
        <div className="lab"><span>Enforcement effectiveness</span><b>{eff}%</b></div>
        <input type="range" min="40" max="100" step="5" value={eff} onChange={(e) => setEff(+e.target.value)} />
        <div className="muted" style={{ fontSize: 11 }}>
          {eff >= 95 ? "Full tow-away + intercept" : eff >= 75 ? "Active ticketing + some towing" : "Ticketing only — partial clearance"}
        </div>
      </div>

      <div className="stats" style={{ marginTop: 14 }}>
        <div className="stat"><div className="v" style={{ color: "var(--hot)" }}>{delay}<span style={{ fontSize: 13 }}> min</span></div><div className="k">Network delay relieved</div></div>
        <div className="stat"><div className="v" style={{ color: "var(--amber)" }}>{t3}%</div><div className="k">Carriageway-blocking removed</div></div>
        <div className="stat"><div className="v">{heavyCites.toLocaleString()}</div><div className="k">Heavy-vehicle tickets cleared</div></div>
        <div className="stat"><div className="v" style={{ color: "var(--teal)" }}>{congShare}%</div><div className="k">Citywide top-100 congestion addressed</div></div>
        <div className="stat"><div className="v">{officerHrs}<span style={{ fontSize: 13 }}> hrs</span></div><div className="k">Officer-hours required (on-site)</div></div>
        <div className="stat"><div className="v">{sel.length}</div><div className="k">Zones · {cites.toLocaleString()} citations</div></div>
      </div>

      {sel.length === 0
        ? <div className="muted">Select zones above or click them on the map to simulate.</div>
        : <div className="muted">Showing payoff at <b style={{ color: "var(--amber)" }}>{eff}%</b> effectiveness across {sel.length} zone{sel.length > 1 ? "s" : ""}.</div>}
    </div>
  );
}
