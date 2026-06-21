import React, { useEffect, useRef, useState } from "react";
import { aiCommand } from "../../api.js";

// Natural-language operator bar. Drives the app via tool-use; not a chat log — shows the last reply.
export default function CommandBar({ available, onActions }) {
  const [value, setValue] = useState("");
  const [busy, setBusy] = useState(false);
  const [reply, setReply] = useState(null);
  const [err, setErr] = useState(false);
  const inputRef = useRef(null);
  const histRef = useRef([]);          // [{role, content}], trimmed to last 2 exchanges
  const abortRef = useRef(null);

  useEffect(() => {
    const onKey = (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") { e.preventDefault(); inputRef.current?.focus(); }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  async function submit(e) {
    e?.preventDefault();
    const msg = value.trim();
    if (!msg || busy || !available) return;
    abortRef.current?.abort();
    const ctrl = new AbortController(); abortRef.current = ctrl;
    setBusy(true); setErr(false); setReply(null);
    try {
      const d = await aiCommand(msg, histRef.current, ctrl.signal);
      onActions?.(d.ui_actions);                       // optimistic: map reacts immediately
      setReply(d.reply);
      histRef.current = [...histRef.current, { role: "user", content: msg }, { role: "assistant", content: d.reply }].slice(-4);
      setValue("");
    } catch (e2) {
      if (e2.name !== "AbortError") { setErr(true); setReply("Copilot request failed — is the proxy running?"); }
    } finally { setBusy(false); }
  }

  const placeholder = available
    ? "Ask the copilot…  e.g. “plan 3 patrols around HSR”   (⌘K)"
    : "Copilot offline — start the Claude proxy to enable";

  return (
    <div className="cmdbar">
      <form className={"cmd-input" + (busy ? " busy" : "")} onSubmit={submit}>
        <i className={"ti " + (busy ? "ti-loader-2 spin" : "ti-sparkles")} aria-hidden="true" />
        <input ref={inputRef} value={value} disabled={!available || busy}
          onChange={(e) => setValue(e.target.value)} placeholder={placeholder} aria-label="AI command" />
        {value && <button type="submit" className="cmd-go" disabled={busy}>Run</button>}
      </form>
      {reply && (
        <div className={"cmd-reply" + (err ? " err" : "")}>
          <i className="ti ti-robot" aria-hidden="true" />
          <span>{reply}</span>
          <button className="cmd-x" aria-label="dismiss" onClick={() => setReply(null)}><i className="ti ti-x" /></button>
        </div>
      )}
    </div>
  );
}
