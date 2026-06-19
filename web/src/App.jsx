import React, { useEffect, useMemo, useState } from "react";
import { loadStatic, getHealth, impedanceLoop } from "./api.js";
import MapView from "./components/MapView.jsx";
import BTPSidebar from "./components/BTPSidebar.jsx";
import LogisticsSidebar from "./components/LogisticsSidebar.jsx";

const INITIAL = { longitude: 77.59, latitude: 12.97, zoom: 11, pitch: 0, bearing: 0 };

export default function App() {
  const [persona, setPersona] = useState("btp");
  const [btpMode, setBtpMode] = useState("hotspots");
  const [cells, setCells] = useState(null);
  const [tops, setTops] = useState([]);
  const [rcp, setRcp] = useState(null);
  const [blind, setBlind] = useState(null);
  const [health, setHealth] = useState(null);
  const [selected, setSelected] = useState(null);
  const [route, setRoute] = useState(null);
  const [plan, setPlan] = useState(null);
  const [multi, setMulti] = useState([]); // gh7[] for What-If
  const [busy, setBusy] = useState(false);
  const [viewState, setViewState] = useState(INITIAL);

  useEffect(() => {
    loadStatic("cells.geojson").then(setCells).catch(() => {});
    loadStatic("priority_table.json").then(setTops).catch(() => {});
    loadStatic("rcp.geojson").then(setRcp).catch(() => {});
    loadStatic("blindspots.geojson").then(setBlind).catch(() => {});
    getHealth().then(setHealth);
  }, []);

  const stats = useMemo(() => {
    const zones = cells?.features?.length || 0;
    const ranked = cells?.features?.filter((f) => f.properties.ranked).length || 0;
    const netDelay = (rcp?.features || []).reduce((s, f) => s + (f.properties.delay_min || 0), 0);
    return { zones, ranked, netDelay: Math.round(netDelay) };
  }, [cells, rcp]);

  function focusZone(z) {
    setSelected(z.gh7);
    setViewState((v) => ({ ...v, longitude: z.lon, latitude: z.lat, zoom: 15, transitionDuration: 600 }));
  }
  function presetSelect(n) { setMulti((tops || []).slice(0, n).map((z) => z.gh7)); }
  function toggleCell(gh7) {
    setMulti((m) => (m.includes(gh7) ? m.filter((x) => x !== gh7) : [...m, gh7]));
  }

  async function analyzeRoute(waypoints) {
    setBusy(true);
    const a = waypoints[0], b = waypoints[waypoints.length - 1];
    setViewState((v) => ({ ...v, longitude: (a.lng + b.lng) / 2, latitude: (a.lat + b.lat) / 2,
      zoom: 11.5, transitionDuration: 700 }));
    try { setRoute(await impedanceLoop(waypoints, 80)); }
    catch { setRoute(null); }
    finally { setBusy(false); }
  }

  return (
    <div className="app">
      <div className="topbar">
        <div className="brand">Grid<span className="dot">●</span>Lock <span className="muted">| Parking-Congestion Intelligence</span></div>
        <div className="toggle">
          <button className={persona === "btp" ? "on" : ""} onClick={() => setPersona("btp")}>BTP Command</button>
          <button className={persona === "logistics" ? "on" : ""} onClick={() => setPersona("logistics")}>Flipkart Logistics</button>
        </div>
        <div className="spacer" />
        <div className="health">
          {health ? <span className="live-dot" /> : null}
          API {health ? "ONLINE" : <span style={{ color: "var(--warn)" }}>STATIC-ONLY</span>}
          {health && <> · MODEL {health.model_loaded ? "✓" : "—"} · MAPPLS {health.mappls.toUpperCase()}</>}
        </div>
      </div>

      <div className="body">
        {persona === "btp"
          ? <BTPSidebar btpMode={btpMode} setBtpMode={setBtpMode} stats={stats} tops={tops} rcp={rcp}
              blind={blind} selected={selected} onSelect={focusZone}
              plan={plan} onPlan={setPlan} multi={multi} onPreset={presetSelect} />
          : <LogisticsSidebar route={route} busy={busy} onAnalyze={analyzeRoute} />}
        <div className="map-wrap">
          <MapView
            persona={persona} btpMode={btpMode} cells={cells} tops={tops} rcp={rcp} blind={blind}
            selected={selected} route={route} plan={plan} multi={multi}
            viewState={viewState} onViewState={setViewState}
            onSelect={focusZone} onToggleCell={toggleCell}
          />
        </div>
      </div>
    </div>
  );
}
