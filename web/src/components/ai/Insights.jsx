import React, { useEffect, useState } from "react";
import { aiInsights } from "../../api.js";

// Proactive, data-derived insight flags (Claude phrases natively-computed candidates).
export default function Insights({ available }) {
  const [items, setItems] = useState([]);
  useEffect(() => {
    if (!available) return;
    let live = true;
    aiInsights().then((d) => { if (live) setItems(d.insights || []); }).catch(() => {});
    return () => { live = false; };
  }, [available]);

  if (!available || !items.length) return null;
  return (
    <div className="ai-insights">
      <div className="section-title">AI insights</div>
      {items.map((t, i) => (
        <div key={i} className="ai-insight"><i className="ti ti-bulb" aria-hidden="true" /><span>{t}</span></div>
      ))}
    </div>
  );
}
