import React, { useState } from "react";

// Shareable enforcement order: copy, print, or send to WhatsApp — how BTP actually coordinates.
export default function ShiftOrderModal({ open, text, onClose }) {
  const [copied, setCopied] = useState(false);
  if (!open) return null;

  function copy() {
    navigator.clipboard?.writeText(text).then(() => { setCopied(true); setTimeout(() => setCopied(false), 1500); });
  }
  function print() {
    const w = window.open("", "_blank", "width=700,height=800");
    if (!w) return;
    w.document.write(`<pre style="font:13px/1.5 ui-monospace,Menlo,monospace;white-space:pre-wrap;padding:24px">${
      text.replace(/[&<>]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c]))}</pre>`);
    w.document.close(); w.focus(); w.print();
  }
  const wa = `https://wa.me/?text=${encodeURIComponent(text)}`;

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()} style={{ width: 560 }}>
        <div className="modal-head">
          <span>Shift order</span>
          <button className="cmd-x" onClick={onClose} aria-label="Close">✕</button>
        </div>
        <pre className="order-text">{text}</pre>
        <div className="modal-actions">
          <button className="btn more" onClick={print}>Print</button>
          <a className="btn more" href={wa} target="_blank" rel="noreferrer" style={{ textAlign: "center", textDecoration: "none" }}>WhatsApp</a>
          <button className="btn" onClick={copy}>{copied ? "Copied ✓" : "Copy"}</button>
        </div>
      </div>
    </div>
  );
}
