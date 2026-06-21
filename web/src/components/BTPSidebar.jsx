import React from "react";
import HotspotsPanel from "./panels/HotspotsPanel.jsx";
import PatrolPanel from "./panels/PatrolPanel.jsx";
import WhatIfPanel from "./panels/WhatIfPanel.jsx";
import BlindSpotsPanel from "./panels/BlindSpotsPanel.jsx";
import BriefCard from "./ai/BriefCard.jsx";
import Insights from "./ai/Insights.jsx";
import AiRead from "./ai/AiRead.jsx";

const MODES = [["hotspots", "Hotspots"], ["patrol", "Patrol Plan"], ["whatif", "What-If"], ["blind", "Blind Spots"]];

export default function BTPSidebar(p) {
  return (
    <div className="sidebar">
      <BriefCard available={p.aiAvail} />
      {p.selected && <AiRead available={p.aiAvail} gh7={p.selected} />}
      <div className="toggle modes">
        {MODES.map(([k, l]) => (
          <button key={k} className={p.btpMode === k ? "on" : ""} onClick={() => p.setBtpMode(k)}>{l}</button>
        ))}
      </div>
      {p.btpMode === "hotspots" && <HotspotsPanel stats={p.stats} tops={p.tops} rcp={p.rcp} selected={p.selected} onSelect={p.onSelect} />}
      {p.btpMode === "patrol" && <PatrolPanel onPlan={p.onPlan} plan={p.plan} onFocus={p.onFocus} />}
      {p.btpMode === "whatif" && <WhatIfPanel tops={p.tops} rcp={p.rcp} multi={p.multi}
        onSetMulti={p.onSetMulti} onSelect={p.onSelect} aiAvail={p.aiAvail} />}
      {p.btpMode === "blind" && <BlindSpotsPanel blind={p.blind} onSelect={p.onSelect} />}
      {p.btpMode === "hotspots" && <Insights available={p.aiAvail} />}
    </div>
  );
}
