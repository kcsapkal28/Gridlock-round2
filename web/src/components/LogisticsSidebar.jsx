import React, { useState } from "react";
import { slaColor } from "../lib/color.js";
import { aiCommand } from "../api.js";
import AiRead from "./ai/AiRead.jsx";

// Sample delivery routes across Bengaluru that cross known hotspot corridors.
const PRESETS = [
  { name: "Koramangala → Whitefield (ORR)", wp: [{ lat: 12.935, lng: 77.622 }, { lat: 12.997, lng: 77.669 }] },
  { name: "City Market → Hebbal", wp: [{ lat: 12.964, lng: 77.578 }, { lat: 13.035, lng: 77.589 }] },
  { name: "Electronic City → KR Puram", wp: [{ lat: 12.842, lng: 77.660 }, { lat: 13.008, lng: 77.696 }] },
  { name: "Indiranagar → Marathahalli", wp: [{ lat: 12.971, lng: 77.641 }, { lat: 12.956, lng: 77.701 }] },
  { name: "HSR Layout → Whitefield", wp: [{ lat: 12.911, lng: 77.647 }, { lat: 12.970, lng: 77.750 }] },
  { name: "Jayanagar → Majestic", wp: [{ lat: 12.930, lng: 77.583 }, { lat: 12.977, lng: 77.572 }] },
  { name: "Bellandur → MG Road", wp: [{ lat: 12.926, lng: 77.676 }, { lat: 12.975, lng: 77.606 }] },
  { name: "Silk Board → Hebbal", wp: [{ lat: 12.917, lng: 77.622 }, { lat: 13.035, lng: 77.597 }] },
];

export default function LogisticsSidebar({ route, busy, onAnalyze, onAnalyzeByName, onFocus, aiAvail, onAiActions }) {
  const [q, setQ] = useState("");
  const [aiBusy, setAiBusy] = useState(false);
  const [aiErr, setAiErr] = useState("");
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const [nameErr, setNameErr] = useState("");

  async function runNamed(e) {
    e.preventDefault();
    if (!from.trim() || !to.trim() || busy) return;
    setNameErr("");
    try {
      const r = await onAnalyzeByName?.(from.trim(), to.trim());
      if (r?.origin_name && r?.dest_name) setNameErr("");
    } catch (err) {
      setNameErr(String(err.message || err).replace(/^Error:\s*/, ""));
    }
  }

  async function runAi(e) {
    e.preventDefault();
    const text = q.trim();
    if (!text || aiBusy) return;
    setAiBusy(true); setAiErr("");
    try {
      const d = await aiCommand(`Analyze the delivery route: ${text}`);
      onAiActions?.(d.ui_actions);
      const hasRoute = (d.ui_actions || []).some((a) => a.type === "showRoute");
      if (!hasRoute) setAiErr(d.reply || "Couldn't resolve that route — try two known areas.");
      else setQ("");
    } catch {
      setAiErr("Copilot request failed — is the proxy running?");
    } finally { setAiBusy(false); }
  }

  return (
    <div className="sidebar">
      <div className="banner">
        <b>Protect delivery SLAs.</b><br />
        <span className="muted">Detect parking-induced friction on a fleet route and reroute around it.</span>
      </div>

      <div className="section-title">Simulate a delivery route</div>

      <form className="route-form" onSubmit={runNamed}>
        <div className="route-field">
          <span className="pin" style={{ color: "#5dcaa5" }}>FROM</span>
          <input value={from} onChange={(e) => setFrom(e.target.value)} disabled={busy}
            placeholder="Pickup area — e.g. “Koramangala”" aria-label="Origin area" />
        </div>
        <div className="route-field">
          <span className="pin" style={{ color: "#78a2ff" }}>TO</span>
          <input value={to} onChange={(e) => setTo(e.target.value)} disabled={busy}
            placeholder="Drop area — e.g. “Whitefield”" aria-label="Destination area" />
        </div>
        <button type="submit" className="btn" disabled={busy || !from.trim() || !to.trim()}>
          {busy ? "Analyzing…" : "Analyze route"}</button>
      </form>
      {route?.origin_name && route?.dest_name && !nameErr && (
        <div className="route-resolved">✓ {route.origin_name} → {route.dest_name}</div>
      )}
      {nameErr && <div className="muted" style={{ color: "var(--hot)", marginBottom: 8, fontSize: 11 }}>{nameErr}</div>}
      <div className="muted" style={{ fontSize: 11, margin: "2px 0 8px" }}>
        Typos &amp; abbreviations are fine (e.g. “ecity”, “marthahalli”).
      </div>

      {aiAvail && (
        <>
          <form className="ai-routebox" onSubmit={runAi}>
            <i className={"ti " + (aiBusy ? "ti-loader-2 spin" : "ti-sparkles")} aria-hidden="true" />
            <input value={q} onChange={(e) => setQ(e.target.value)} disabled={aiBusy}
              placeholder="Describe any route — e.g. “HSR to Electronic City”" aria-label="AI route" />
            <button type="submit" className="cmd-go" disabled={aiBusy || !q.trim()}>Go</button>
          </form>
          {aiErr && <div className="muted" style={{ color: "var(--hot)", marginBottom: 8, fontSize: 11 }}>{aiErr}</div>}
        </>
      )}

      <div className="section-title">Or pick a sample corridor</div>
      {PRESETS.map((p) => (
        <button key={p.name} className="btn alt" style={{ marginBottom: 6, textAlign: "left" }}
          disabled={busy || aiBusy} onClick={() => onAnalyze(p.wp)}>{p.name}</button>
      ))}
      {(busy || aiBusy) && <div className="muted" style={{ marginTop: 8 }}>Analyzing route impedance…</div>}

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

          <AiRead available={aiAvail} routeSummary={{
            total_delay_min: route.impedance_delay_mins, sla_risk: route.sla_risk,
            recoverable_min: route.minutes_saved_by_detour, n_chokes: route.n_affected,
            worst_gh7: route.worst_choke && route.worst_choke.gh7 }} />

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
