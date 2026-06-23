import React, { useState } from "react";
import { aiCommand } from "../api.js";

// Simple mode: an Inspector asks a question or reads "today's deployment" in plain language,
// then prints/shares a shift order. AI is optional — the deployment list works without it.
export default function CommandView({ today, loading, area, onArea, onFocus, onOpenOrder, aiAvail, onAiActions }) {
  const [q, setQ] = useState("");
  const [areaInput, setAreaInput] = useState(area || "");
  const [aiBusy, setAiBusy] = useState(false);
  const [aiReply, setAiReply] = useState("");

  async function ask(e) {
    e.preventDefault();
    const text = q.trim();
    if (!text || aiBusy) return;
    setAiBusy(true); setAiReply("");
    try {
      const d = await aiCommand(text);
      onAiActions?.(d.ui_actions);
      setAiReply(d.reply || "");
    } catch {
      setAiReply("Copilot is offline — add an Anthropic key in ⚙ Settings, or use today's deployment below.");
    } finally { setAiBusy(false); }
  }
  function applyArea(e) { e.preventDefault(); onArea?.(areaInput.trim()); }

  const cards = today?.cards || [];
  const tierColor = { Persistent: "var(--hot)", Recurring: "var(--amber)", Intermittent: "var(--muted)" };

  return (
    <div className="sidebar">
      <div className="cmd-hero">
        <div className="hero-title">What do you need to decide?</div>
        <form className="ai-routebox" onSubmit={ask}>
          <i className={"ti " + (aiBusy ? "ti-loader-2 spin" : "ti-sparkles")} aria-hidden="true" />
          <input value={q} onChange={(e) => setQ(e.target.value)} disabled={aiBusy}
            placeholder='e.g. "Where do I deploy in Indiranagar this morning?"' aria-label="Ask GridLock" />
          <button type="submit" className="cmd-go" disabled={aiBusy || !q.trim()}>Ask</button>
        </form>
        {aiReply && <div className="hero-reply">{aiReply}</div>}
        {!aiAvail && !aiReply && <div className="hero-hint">Tip: the AI assistant turns on with an Anthropic key (⚙). The plan below works without it.</div>}
      </div>

      <div className="section-title">Today's priority deployment</div>
      <form className="area-row" onSubmit={applyArea}>
        <input value={areaInput} onChange={(e) => setAreaInput(e.target.value)}
          placeholder="Focus an area (optional) — e.g. Koramangala" aria-label="Focus area" />
        <button type="submit" className="cmd-go">Go</button>
        {area && <button type="button" className="cmd-x" title="Clear" onClick={() => { setAreaInput(""); onArea?.(""); }}>✕</button>}
      </form>

      {loading && <div className="muted">Loading deployment…</div>}
      {!loading && today?.summary && <div className="muted" style={{ margin: "2px 0 10px" }}>{today.summary}</div>}

      {cards.map((c, i) => (
        <div key={c.gh7} className="deploy-card" onClick={() => onFocus?.(c)}>
          <div className="dc-rank">{i + 1}</div>
          <div className="dc-body">
            <div className="dc-area">{c.area}
              {c.spots > 1 && <span className="dc-spots">{c.spots} spots</span>}</div>
            <div className="dc-station">📍 {c.station} police station</div>
            <div className="dc-action">{c.action}</div>
            <div className="dc-meta">
              <span className="dc-impact">impact {Math.round(c.impact)}/100</span>
              <span>· {c.tier3_pct}% lane-blocking</span>
              <span>· {c.heavy_pct}% heavy</span>
              {c.delay_min != null && <span>· ~{c.delay_min} min delay</span>}
            </div>
            <div className="dc-conf" style={{ color: tierColor[c.confidence?.tier] || "var(--muted)" }}>
              {c.confidence?.phrase}
            </div>
          </div>
        </div>
      ))}

      {cards.length > 0 && (
        <button className="btn" style={{ marginTop: 6 }} onClick={() => onOpenOrder?.(today.shift_order)}>
          📋 Generate shift order
        </button>
      )}
      {!loading && cards.length === 0 && <div className="muted">No deployment data.</div>}

      <div className="muted" style={{ marginTop: 12, fontSize: 11 }}>
        Ranked by traffic-flow impact, not ticket volume. Tap a location to see it on the map.
        Switch to <b>Pro</b> (top bar) for the full analyst console.
      </div>
    </div>
  );
}
