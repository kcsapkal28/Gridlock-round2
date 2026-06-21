import React, { useState } from "react";
import { patrolPlan } from "../../api.js";

const PRIORITIES = [
  ["impact", "Impact"],
  ["carriageway", "Lane-blocking"],
  ["heavy", "Heavy vehicles"],
];

export default function PatrolPanel({ onPlan, plan, onFocus }) {
  const [units, setUnits] = useState(3);
  const [topk, setTopk] = useState(15);
  const [priority, setPriority] = useState("impact");
  const [fromStation, setFromStation] = useState(true);
  const [showOpts, setShowOpts] = useState(false);
  const [busy, setBusy] = useState(false);

  async function gen() {
    setBusy(true);
    try { onPlan(await patrolPlan(units, topk, priority, fromStation)); }
    catch { onPlan(null); }
    finally { setBusy(false); }
  }
  const estimated = plan?.units?.some((u) => u.routing === "estimated");

  return (
    <div>
      <div className="banner">
        <b>Optimized patrol deployment.</b><br />
        <span className="muted">A practical, step-by-step plan: each unit rolls out from its nearest
        police station, clears the highest-impact zones in route order, then returns.</span>
      </div>

      <div className="section-title">Patrol units</div>
      <div>{[1, 2, 3, 4].map((n) => (
        <button key={n} className={"pill" + (n === units ? " on" : "")} style={{ cursor: "pointer" }}
          onClick={() => setUnits(n)}>{n}</button>))}</div>

      <div className="section-title">Prioritise by</div>
      <div>{PRIORITIES.map(([k, l]) => (
        <button key={k} className={"pill" + (k === priority ? " on" : "")} style={{ cursor: "pointer" }}
          onClick={() => setPriority(k)}>{l}</button>))}</div>

      <button className="muted" style={{ background: "none", border: 0, cursor: "pointer", padding: "12px 0 4px", color: "var(--muted)" }}
        onClick={() => setShowOpts((v) => !v)}>{showOpts ? "▾" : "▸"} Advanced options</button>
      {showOpts && (
        <div style={{ paddingLeft: 4 }}>
          <div className="section-title">Coverage depth (top zones)</div>
          <div>{[10, 15, 20].map((k) => (
            <button key={k} className={"pill" + (k === topk ? " on" : "")} style={{ cursor: "pointer" }}
              onClick={() => setTopk(k)}>top {k}</button>))}</div>
          <label className="mc-check" style={{ marginTop: 12 }}>
            <input type="checkbox" checked={fromStation} onChange={(e) => setFromStation(e.target.checked)} />
            <span>Start &amp; end each route at a police station</span>
          </label>
        </div>
      )}

      <button className="btn" style={{ marginTop: 14 }} disabled={busy} onClick={gen}>
        {busy ? "Optimizing…" : "Generate patrol plan"}</button>

      {plan?.units?.length ? (
        <>
          <div className="muted" style={{ margin: "14px 0 8px" }}>
            {plan.units.length} unit{plan.units.length > 1 ? "s" : ""} · prioritised by{" "}
            {PRIORITIES.find(([k]) => k === (plan.priority || "impact"))?.[1]?.toLowerCase()}. Tap a stop to locate it.
          </div>
          {plan.units.map((u) => (
            <div key={u.unit_id} className="plan-unit">
              <div className="uhead">
                <span className="uname" style={{ color: u.color }}>● Unit {u.unit_id}</span>
                <span className="muted" style={{ fontSize: 12 }}>{u.n_zones} zones · impact {u.total_impact}
                  {u.routing === "estimated" && <span className="tag" style={{ marginLeft: 6 }}>est.</span>}</span>
              </div>
              {u.station && <div className="udepot">Depot: <b>{u.station.name}</b> police station</div>}
              <div className="plan-times">
                <span><b>{u.shift_time_min}</b> min shift</span>
                <span>{u.drive_time_min} min drive</span>
                <span>{u.dwell_time_min} min on-site</span>
              </div>
              <ol className="plan-steps">
                {u.station && (
                  <li className="step depart edge">
                    <span className="dot">▲</span>
                    <div className="s-area">Depart — {u.station.name} PS</div>
                  </li>
                )}
                {u.stops.map((s) => (
                  <li key={s.gh7 + s.seq} className="step stop plan-clickable" style={{ color: u.color }}
                    onClick={() => onFocus?.(s.lat, s.lon)}>
                    <span className="dot">{s.seq}</span>
                    <div className="s-area" style={{ color: "var(--text)" }}>{s.area}
                      <span className="mono">{s.gh7}</span></div>
                    <div className="s-act">{s.action}</div>
                    <div className="s-meta">impact {s.impact}/100 · {Math.round(s.tier3_share * 100)}% lane-block
                      · {Math.round(s.heavy_share * 100)}% heavy · ~{Math.round(s.dwell_min)} min</div>
                  </li>
                ))}
                {u.station && (
                  <li className="step return edge">
                    <span className="dot">●</span>
                    <div className="s-area">Return — {u.station.name} PS</div>
                  </li>
                )}
              </ol>
            </div>
          ))}
          {estimated && <div className="muted" style={{ marginTop: 8, fontSize: 11 }}>
            “est.” = drive time estimated (no live routing). Add a MapMyIndia key for road-accurate times.</div>}
        </>
      ) : plan ? <div className="muted" style={{ marginTop: 10 }}>No plan returned.</div> : null}
    </div>
  );
}
