import React, { useEffect, useState } from "react";
import { aiBrief } from "../../api.js";

let briefCache = null;   // session cache — the brief is over static data, so generate once

// Proactive enforcement brief — auto-loads, grounded in current data.
export default function BriefCard({ available }) {
  const [text, setText] = useState(briefCache);
  const [busy, setBusy] = useState(false);

  async function load(force) {
    if (!available) return;
    if (briefCache != null && !force) { setText(briefCache); return; }
    setBusy(true);
    try { const d = await aiBrief(); briefCache = d.brief || ""; setText(briefCache); }
    catch { setText(""); }
    finally { setBusy(false); }
  }
  useEffect(() => { load(false); /* eslint-disable-next-line */ }, [available]);

  if (!available) return null;
  return (
    <div className="ai-brief">
      <div className="ai-brief-head">
        <span><i className="ti ti-sparkles" aria-hidden="true" /> AI enforcement brief</span>
        <button className="ai-refresh" onClick={() => load(true)} disabled={busy} aria-label="refresh brief">
          <i className={"ti " + (busy ? "ti-loader-2 spin" : "ti-refresh")} />
        </button>
      </div>
      {busy && !text ? (
        <div className="ai-skeleton"><span /><span /><span /></div>
      ) : (
        <div className="ai-brief-body">
          {(text || "").split("\n").filter(Boolean).map((para, i) => <p key={i}>{para}</p>)}
        </div>
      )}
    </div>
  );
}
