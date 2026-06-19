import React, { useState } from "react";
import { patrolPlan } from "../../api.js";

export default function PatrolPanel({ onPlan, plan }) {
  const [units, setUnits] = useState(3);
  const [topk, setTopk] = useState(15);
  const [busy, setBusy] = useState(false);
  async function gen() {
    setBusy(true);
    try { onPlan(await patrolPlan(units, topk)); } catch { onPlan(null); } finally { setBusy(false); }
  }
  return (
    <div>
      <div className="banner">
        <b>Optimized patrol deployment.</b><br />
        <span className="muted">Cover the highest-impact zones with the fewest unit-minutes.</span>
      </div>
      <div className="section-title">Patrol units</div>
      <div>{[1, 2, 3, 4].map((n) => (
        <button key={n} className={"pill" + (n === units ? " on" : "")} style={{ cursor: "pointer" }}
          onClick={() => setUnits(n)}>{n}</button>))}</div>
      <div className="section-title">Coverage depth</div>
      <div>{[10, 15, 20].map((k) => (
        <button key={k} className={"pill" + (k === topk ? " on" : "")} style={{ cursor: "pointer" }}
          onClick={() => setTopk(k)}>top {k}</button>))}</div>
      <button className="btn" style={{ marginTop: 14 }} disabled={busy} onClick={gen}>
        {busy ? "Optimizing…" : "Generate patrol plan"}</button>
      {plan?.units?.map((u) => (
        <div key={u.unit_id} className="card" style={{ marginTop: 9 }}>
          <div className="row">
            <span className="name" style={{ color: u.color }}>● Unit {u.unit_id}</span>
            <span className="score">{u.drive_time_min}<span style={{ fontSize: 11, color: "var(--muted)" }}> min</span></span>
          </div>
          <div className="meta">{u.n_zones} zones · total impact {u.total_impact}</div>
        </div>))}
      {plan && !plan.units?.length && <div className="muted" style={{ marginTop: 10 }}>No plan returned.</div>}
    </div>
  );
}
