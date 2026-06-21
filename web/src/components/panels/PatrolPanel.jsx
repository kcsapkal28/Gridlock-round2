import React, { useState } from "react";
import { patrolPlan } from "../../api.js";

export default function PatrolPanel({ onPlan, plan, onFocus }) {
  const [units, setUnits] = useState(3);
  const [topk, setTopk] = useState(15);
  const [busy, setBusy] = useState(false);
  async function gen() {
    setBusy(true);
    try { onPlan(await patrolPlan(units, topk)); } catch { onPlan(null); } finally { setBusy(false); }
  }
  const estimated = plan?.units?.some((u) => u.routing === "estimated");
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
      <div className="section-title">Coverage depth (top zones)</div>
      <div>{[10, 15, 20].map((k) => (
        <button key={k} className={"pill" + (k === topk ? " on" : "")} style={{ cursor: "pointer" }}
          onClick={() => setTopk(k)}>top {k}</button>))}</div>
      <button className="btn" style={{ marginTop: 14 }} disabled={busy} onClick={gen}>
        {busy ? "Optimizing…" : "Generate patrol plan"}</button>

      {plan?.units?.length ? (
        <>
          <div className="muted" style={{ margin: "12px 0 4px" }}>Tap a unit to fly to its zones.</div>
          {plan.units.map((u) => (
            <div key={u.unit_id} className="card" onClick={() => u.stops?.[0] && onFocus?.(u.stops[0].lat, u.stops[0].lon)}>
              <div className="row">
                <span className="name" style={{ color: u.color }}>● Unit {u.unit_id}</span>
                <span className="score">{u.drive_time_min}<span style={{ fontSize: 11, color: "var(--muted)", fontWeight: 400 }}> min drive</span></span>
              </div>
              <div className="meta">{u.n_zones} zones · total impact {u.total_impact}
                {u.routing === "estimated" && <span className="tag" style={{ marginLeft: 6 }}>est.</span>}</div>
            </div>))}
          {estimated && <div className="muted" style={{ marginTop: 8, fontSize: 11 }}>
            “est.” = drive time estimated (no live routing). Add a MapMyIndia key for road-accurate times.</div>}
        </>
      ) : plan ? <div className="muted" style={{ marginTop: 10 }}>No plan returned.</div> : null}
    </div>
  );
}
