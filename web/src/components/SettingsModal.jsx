import React, { useState } from "react";
import { getKeys, setKeys, clearKeys, getHealth, aiHealth } from "../api.js";

const MODELS = ["claude-sonnet-4-6", "claude-opus-4-8", "claude-haiku-4-5-20251001"];

export default function SettingsModal({ open, onClose, onSaved }) {
  const init = getKeys();
  const [mappls, setMappls] = useState(init.mappls || "");
  const [anthropic, setAnthropic] = useState(init.anthropic || "");
  const [model, setModel] = useState(init.model || "claude-sonnet-4-6");
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState(null); // {mappls, ai}

  if (!open) return null;

  async function saveAndTest() {
    setBusy(true); setStatus(null);
    setKeys({ mappls: mappls.trim(), anthropic: anthropic.trim(), model: model.trim() });
    try {
      const [h, ai] = await Promise.all([getHealth(), aiHealth()]);
      setStatus({
        mappls: h ? String(h.mappls) : "down",
        ai: ai?.available ? `online · ${ai.model || model}` : "offline",
        aiOk: !!ai?.available,
        mapplsOk: h && h.mappls === "live",
      });
    } catch {
      setStatus({ mappls: "error", ai: "error" });
    } finally { setBusy(false); onSaved?.(); }
  }
  function reset() {
    clearKeys(); setMappls(""); setAnthropic(""); setModel("claude-sonnet-4-6");
    setStatus(null); onSaved?.();
  }

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-head">
          <span>API Keys (optional)</span>
          <button className="cmd-x" onClick={onClose} aria-label="Close">✕</button>
        </div>
        <p className="muted" style={{ margin: "0 0 14px", lineHeight: 1.5 }}>
          Use your own keys to power live road-routing and the AI copilot. Keys are stored
          <b> only in this browser</b> and sent per-request — never saved on the server.
        </p>

        <label className="field">
          <span className="field-lab">MapMyIndia (Mappls) REST key</span>
          <input value={mappls} onChange={(e) => setMappls(e.target.value)} type="password"
            placeholder="enables road-accurate routing & distance matrix" autoComplete="off" />
          <span className="field-hint">Used for patrol routes, detours and the delivery-route simulator.</span>
        </label>

        <label className="field">
          <span className="field-lab">Anthropic API key</span>
          <input value={anthropic} onChange={(e) => setAnthropic(e.target.value)} type="password"
            placeholder="sk-ant-…  enables the AI copilot" autoComplete="off" />
          <span className="field-hint">Calls Anthropic directly (no proxy). Powers the brief, insights, explain &amp; command bar.</span>
        </label>

        <label className="field">
          <span className="field-lab">Claude model</span>
          <select value={model} onChange={(e) => setModel(e.target.value)}>
            {MODELS.map((m) => <option key={m} value={m}>{m}</option>)}
          </select>
        </label>

        {status && (
          <div className="key-status">
            <div><b>Mappls:</b> <span className={status.mapplsOk ? "ok" : "bad"}>{status.mappls}</span></div>
            <div><b>AI copilot:</b> <span className={status.aiOk ? "ok" : "bad"}>{status.ai}</span></div>
          </div>
        )}

        <div className="modal-actions">
          <button className="btn more" onClick={reset} disabled={busy}>Clear keys</button>
          <button className="btn" onClick={saveAndTest} disabled={busy}>
            {busy ? "Testing…" : "Save & test"}</button>
        </div>
      </div>
    </div>
  );
}
