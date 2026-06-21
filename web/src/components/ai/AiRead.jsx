import React, { useEffect, useState } from "react";
import { aiExplain } from "../../api.js";

const explainCache = new Map();   // key -> text, so re-selecting a zone is instant

// Contextual "AI read": why-this-matters + recommended action for a selected zone or analyzed route.
export default function AiRead({ available, gh7, routeSummary }) {
  const routeKey = JSON.stringify(routeSummary || null);
  const key = gh7 ? `z:${gh7}` : (routeSummary ? `r:${routeKey}` : null);
  const [text, setText] = useState((key && explainCache.get(key)) || "");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!available || !key) { setText(""); return; }
    if (explainCache.has(key)) { setText(explainCache.get(key)); setBusy(false); return; }
    let live = true;
    setBusy(true); setText("");
    aiExplain(gh7 ? { gh7 } : { route_summary: routeSummary })
      .then((d) => { explainCache.set(key, d.text || ""); if (live) setText(d.text || ""); })
      .catch(() => { if (live) setText(""); })
      .finally(() => { if (live) setBusy(false); });
    return () => { live = false; };
  }, [available, key]);

  if (!available) return null;
  if (!busy && !text) return null;
  return (
    <div className="ai-read">
      <div className="ai-read-tag"><i className="ti ti-sparkles" aria-hidden="true" /> AI read</div>
      {busy ? <div className="ai-skeleton"><span /><span /></div> : <p>{text}</p>}
    </div>
  );
}
