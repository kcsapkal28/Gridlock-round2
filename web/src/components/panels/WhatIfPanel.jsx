import React, { useEffect, useMemo, useState } from "react";
import AiRead from "../ai/AiRead.jsx";

// Enforcement modes → (effectiveness, dwell multiplier). Heavy sweep only clears the
// heavy-vehicle share of a zone's problem, so it strongly prefers high-heavy zones.
const MODES = {
  tow:   { label: "Tow-away blitz",     eff: 0.95, dwell: 1.4 },
  ticket:{ label: "Active ticketing",   eff: 0.75, dwell: 1.0 },
  heavy: { label: "Heavy-vehicle sweep", eff: 0.90, dwell: 0.8, heavyOnly: true },
};

// Sustained on-site enforcement time at a hotspot (minutes) — a real tow/ticket operation, not a
// drive-by. Travel between stops is added separately so a unit realistically does a handful/shift.
const TRAVEL_MIN = 20;
const dwellBase = (z) => 25 + 25 * z.tier3_share + 15 * z.heavy_share + Math.min(15, (z.n || 0) / 50);

export default function WhatIfPanel({ tops, rcp, multi, onSetMulti, onSelect, aiAvail }) {
  const [units, setUnits] = useState(3);
  const [mode, setMode] = useState("ticket");
  const [showAssume, setShowAssume] = useState(false);
  // editable planning ASSUMPTIONS (no traffic-count data exists — these are tunable, labeled)
  const [shiftHrs, setShiftHrs] = useState(8);
  const [flow, setFlow] = useState(350);    // vehicles/hr through a cleared cell (travel already in stop cost)
  const [vot, setVot] = useState(400);      // ₹ value of time per vehicle-hour
  const [officer, setOfficer] = useState(350); // ₹ cost per officer-hour

  const m = MODES[mode];
  const rcpBy = useMemo(() => {
    const x = {}; (rcp?.features || []).forEach((f) => { x[f.properties.gh7] = f.properties.delay_min; });
    return x;
  }, [rcp]);

  // per-zone economics under the current mode
  const calc = useMemo(() => {
    const fn = (z) => {
      const delay = rcpBy[z.gh7] ?? Math.min(0.6, 0.1 + 0.35 * z.tier3_share + 0.2 * z.heavy_share) * 6;
      const eff = m.heavyOnly ? m.eff * z.heavy_share : m.eff;
      const relief = delay * eff;
      const dwell = dwellBase(z) * m.dwell + TRAVEL_MIN;   // on-site + travel = one stop's cost
      return { z, relief, dwell, roi: dwell > 0 ? relief / dwell : 0 };
    };
    return fn;
  }, [rcpBy, m]);

  const budgetMin = units * shiftHrs * 60;                // deployed officer-minutes per shift
  const totImpact = useMemo(() => (tops || []).reduce((s, z) => s + z.impact, 0) || 1, [tops]);

  // ranked by ROI, then greedily fill the on-site budget → recommended set + cumulative frontier
  const ranked = useMemo(() => (tops || []).map(calc).filter((r) => r.relief > 0)
    .sort((a, b) => b.roi - a.roi), [tops, calc]);
  const frontier = useMemo(() => {
    let cumD = 0, cumR = 0; const pts = []; const pick = [];
    for (const r of ranked) {
      if (cumD + r.dwell > budgetMin) continue;
      cumD += r.dwell; cumR += r.relief; pts.push({ hrs: cumD / 60, relief: cumR }); pick.push(r);
    }
    return { pts, pick };
  }, [ranked, budgetMin]);

  // auto-optimize: set the map selection to the recommended set when the optimizer inputs change.
  useEffect(() => {
    if (frontier.pick.length) onSetMulti?.(frontier.pick.map((r) => r.z.gh7));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [units, mode, shiftHrs, tops]);

  // outcomes computed from the ACTUAL selection (so manual map edits are reflected)
  const sel = useMemo(() => (tops || []).filter((z) => (multi || []).includes(z.gh7)).map(calc), [tops, multi, calc]);
  const reliefTot = sel.reduce((s, r) => s + r.relief, 0);
  const dwellTot = sel.reduce((s, r) => s + r.dwell, 0);
  const pctNetwork = Math.round(sel.reduce((s, r) => s + r.z.impact, 0) / totImpact * 100);
  const officerHrsUsed = dwellTot / 60;
  const officerHrsAvail = budgetMin / 60;
  const vehHours = sel.reduce((s, r) => s + (r.relief / 60) * (flow * shiftHrs), 0);
  const benefit = vehHours * vot;
  const cost = units * shiftHrs * officer;                // full-shift officer cost
  const bcr = cost > 0 ? benefit / cost : 0;

  // diminishing-returns knee over the recommended frontier (80% of relief)
  const kneeIdx = useMemo(() => {
    const tot = frontier.pts.length ? frontier.pts[frontier.pts.length - 1].relief : 0;
    return frontier.pts.findIndex((p) => p.relief >= 0.8 * tot);
  }, [frontier]);

  const inr = (v) => "₹" + (v >= 1e5 ? (v / 1e5).toFixed(1) + "L" : Math.round(v).toLocaleString("en-IN"));

  // deterministic readout — the fallback that works with AI OFF
  const readout = sel.length
    ? `${units} unit${units > 1 ? "s" : ""} (${m.label.toLowerCase()}) clear ${sel.length} zones `
      + `(~${(sel.length / units).toFixed(1)}/unit), relieving ~${Math.round(reliefTot)} delay-min `
      + `(${pctNetwork}% of tracked congestion) for ${officerHrsUsed.toFixed(0)} of ${officerHrsAvail.toFixed(0)} `
      + `deployed officer-hours. Est. ${inr(benefit)}/day of travel time saved vs ~${inr(cost)} officer cost. `
      + (kneeIdx >= 0 && kneeIdx < frontier.pick.length - 1
          ? `Returns taper after zone ${kneeIdx + 1} — the rest add little.`
          : `This budget is well-matched to the zones.`)
    : "Set units and mode to auto-plan, or click zones on the map.";

  const scenario = {
    units, mode: m.label, zones: sel.length, relief_min: Math.round(reliefTot),
    pct_network: pctNetwork, officer_hours_used: +officerHrsUsed.toFixed(1),
    officer_hours_available: +officerHrsAvail.toFixed(1), veh_hours_per_day: Math.round(vehHours),
    benefit_cost_ratio: +bcr.toFixed(1), knee_zone: kneeIdx >= 0 ? kneeIdx + 1 : null,
    note: "veh-hours & ₹ use tunable flow/value-of-time assumptions, not measured counts",
  };

  return (
    <div>
      <div className="banner">
        <b>Enforcement planner.</b><br />
        <span className="muted">Pick your units and style — it auto-selects the best-ROI zones that
        budget can clear, then shows the payoff and where returns taper off.</span>
      </div>

      <div className="section-title">Patrol units</div>
      <div>{[1, 2, 3, 4, 5, 6].map((n) => (
        <button key={n} className={"pill" + (n === units ? " on" : "")} style={{ cursor: "pointer" }}
          onClick={() => setUnits(n)}>{n}</button>))}</div>

      <div className="section-title">Enforcement mode</div>
      <div className="wi-modes">{Object.entries(MODES).map(([k, v]) => (
        <button key={k} className={"pill" + (k === mode ? " on" : "")} style={{ cursor: "pointer" }}
          onClick={() => setMode(k)}>{v.label}</button>))}</div>

      <button className="assume-toggle" onClick={() => setShowAssume((v) => !v)}>
        {showAssume ? "▾" : "▸"} Assumptions (editable)</button>
      {showAssume && (
        <div className="assume-grid">
          <Assume lab="Shift hrs / unit" val={shiftHrs} set={setShiftHrs} min={4} max={12} step={1} />
          <Assume lab="Flow (veh/hr)" val={flow} set={setFlow} min={100} max={2000} step={50} />
          <Assume lab="Value of time (₹/veh-hr)" val={vot} set={setVot} min={100} max={1000} step={50} />
          <Assume lab="Officer cost (₹/hr)" val={officer} set={setOfficer} min={100} max={1000} step={50} />
          <div className="assume-note">No traffic-count data exists (external data is barred), so
            vehicle-hours and ₹ are planning estimates from these tunable inputs.</div>
        </div>
      )}

      <div className="stats" style={{ marginTop: 14 }}>
        <div className="stat"><div className="v" style={{ color: "var(--hot)" }}>{Math.round(reliefTot)}<span style={{ fontSize: 13 }}> min</span></div><div className="k">Network delay relieved</div></div>
        <div className="stat"><div className="v" style={{ color: "var(--teal)" }}>{pctNetwork}%</div><div className="k">Top-100 congestion addressed</div></div>
        <div className="stat"><div className="v">{Math.round(vehHours).toLocaleString()}<span style={{ fontSize: 12 }}> v-hr</span></div><div className="k" title="Assumption-based estimate">Vehicle-hours saved / day*</div></div>
        <div className="stat"><div className="v" style={{ color: "var(--good)" }}>{inr(benefit)}</div><div className="k" title="Assumption-based estimate">Travel time saved / day*</div></div>
        <div className="stat"><div className="v">{officerHrsUsed.toFixed(0)}<span style={{ fontSize: 12, color: "var(--muted)" }}>/{officerHrsAvail.toFixed(0)}</span></div><div className="k">Officer-hours (deployed)</div></div>
        <div className="stat"><div className="v">{sel.length}</div><div className="k">Zones cleared</div></div>
      </div>

      {frontier.pts.length > 1 && <ReturnsCurve pts={frontier.pts} kneeIdx={kneeIdx} selN={sel.length} />}

      <div className="wi-readout">{readout}</div>
      <AiRead available={aiAvail} scenario={scenario} />

      {sel.length > 0 && <>
        <div className="section-title">Contribution (best ROI first)</div>
        {[...sel].sort((a, b) => b.roi - a.roi).slice(0, 8).map((r, i) => {
          const maxRoi = sel[0] ? Math.max(...sel.map((x) => x.roi)) : 1;
          return (
            <div key={r.z.gh7} className="contrib" onClick={() => onSelect?.({ gh7: r.z.gh7, lat: r.z.lat, lon: r.z.lon })}>
              <div className="row">
                <span className="name mono">#{i + 1} · {r.z.gh7}</span>
                <span className="score" style={{ color: "var(--hot)" }}>{r.relief.toFixed(1)}<span style={{ fontSize: 10, color: "var(--muted)", fontWeight: 400 }}> min</span></span>
              </div>
              <div className="roi-bar"><span style={{ width: `${Math.max(6, (r.roi / maxRoi) * 100)}%` }} /></div>
              <div className="meta">impact {Math.round(r.z.impact)} · {Math.round(r.z.tier3_share * 100)}% lane-block · {Math.round(r.z.heavy_share * 100)}% heavy · ~{Math.round(r.dwell)} min on-site</div>
            </div>
          );
        })}
      </>}
      <div className="muted" style={{ marginTop: 10, fontSize: 11 }}>
        Auto-optimized for your budget. Click zones on the map to override. * = planning estimate (see assumptions).
      </div>
    </div>
  );
}

function Assume({ lab, val, set, min, max, step }) {
  return (
    <label className="assume">
      <span>{lab}</span>
      <input type="number" value={val} min={min} max={max} step={step}
        onChange={(e) => set(Math.max(min, Math.min(max, +e.target.value || min)))} />
    </label>
  );
}

// compact cumulative-relief vs officer-hours curve with the 80% knee marked
function ReturnsCurve({ pts, kneeIdx, selN }) {
  const W = 320, H = 80, P = 6;
  const maxH = pts[pts.length - 1].hrs || 1, maxR = pts[pts.length - 1].relief || 1;
  const x = (h) => P + (h / maxH) * (W - 2 * P);
  const y = (r) => H - P - (r / maxR) * (H - 2 * P);
  const line = pts.map((p, i) => `${i ? "L" : "M"}${x(p.hrs).toFixed(1)},${y(p.relief).toFixed(1)}`).join(" ");
  const area = `${line} L${x(pts[pts.length - 1].hrs).toFixed(1)},${H - P} L${x(0).toFixed(1)},${H - P} Z`;
  const knee = kneeIdx >= 0 ? pts[kneeIdx] : null;
  const cur = pts[Math.min(selN, pts.length) - 1];
  return (
    <div className="returns-wrap">
      <div className="returns-head">Diminishing returns <span className="muted">· relief vs officer-hours</span></div>
      <svg viewBox={`0 0 ${W} ${H}`} className="returns-svg" preserveAspectRatio="none">
        <path d={area} fill="rgba(255,178,62,.10)" />
        <path d={line} fill="none" stroke="var(--amber)" strokeWidth="2" />
        {knee && <>
          <line x1={x(knee.hrs)} y1={P} x2={x(knee.hrs)} y2={H - P} stroke="var(--teal)" strokeWidth="1" strokeDasharray="3 3" />
        </>}
        {cur && <circle cx={x(cur.hrs)} cy={y(cur.relief)} r="3" fill="var(--hot)" />}
      </svg>
      {knee && <div className="returns-cap muted">~80% of relief by ~{knee.hrs.toFixed(0)} officer-hrs (zone {kneeIdx + 1}). Beyond that, each unit-hour buys less.</div>}
    </div>
  );
}
