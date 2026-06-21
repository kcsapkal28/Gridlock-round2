import React, { useEffect, useState } from "react";
import { aiExplain } from "../../api.js";

// Contextual "AI read": why-this-matters + recommended action for a selected zone or analyzed route.
export default function AiRead({ available, gh7, routeSummary }) {
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!available || (!gh7 && !routeSummary)) { setText(""); return; }
    let live = true;
    setBusy(true); setText("");
    const body = gh7 ? { gh7 } : { route_summary: routeSummary };
    aiExplain(body)
      .then((d) => { if (live) setText(d.text || ""); })
      .catch(() => { if (live) setText(""); })
      .finally(() => { if (live) setBusy(false); });
    return () => { live = false; };
  }, [available, gh7, JSON.stringify(routeSummary || null)]);

  if (!available) return null;
  if (!busy && !text) return null;
  return (
    <div className="ai-read">
      <div className="ai-read-tag"><i className="ti ti-sparkles" aria-hidden="true" /> AI read</div>
      {busy ? <div className="ai-skeleton"><span /><span /></div> : <p>{text}</p>}
    </div>
  );
}
