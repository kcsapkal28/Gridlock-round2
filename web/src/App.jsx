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
  const [stations, setStations] = useState(null);
  const [health, setHealth] = useState(null);
  const [selected, setSelected] = useState(null);
  const [route, setRoute] = useState(null);
  const [plan, setPlan] = useState(null);
  const [multi, setMulti] = useState([]); // gh7[] for What-If
  const [busy, setBusy] = useState(false);
  const [viewState, setViewState] = useState(INITIAL);
  // map controls
  const [showAll, setShowAll] = useState(true);
  const [impactMin, setImpactMin] = useState(50);
  const [showStations, setShowStations] = useState(false);

  useEffect(() => {
    loadStatic("cells.geojson").then(setCells).catch(() => {});
    loadStatic("priority_table.json").then(setTops).catch(() => {});
    loadStatic("rcp.geojson").then(setRcp).catch(() => {});
    loadStatic("blindspots.geojson").then(setBlind).catch(() => {});
    loadStatic("stations.json").then(setStations).catch(() => {});
    getHealth().then(setHealth);
  }, []);

  const stats = useMemo(() => {
    const zones = cells?.features?.length || 0;
    const ranked = cells?.features?.filter((f) => f.properties.ranked).length || 0;
    const netDelay = (rcp?.features || []).reduce((s, f) => s + (f.properties.delay_min || 0), 0);
    return { zones, ranked, netDelay: Math.round(netDelay) };
  }, [cells, rcp]);

  const shown = useMemo(() => {
    if (showAll || !cells?.features) return cells?.features?.length || 0;
    return cells.features.filter((f) => (f.properties.impact || 0) >= impactMin).length;
  }, [cells, showAll, impactMin]);

  function focusPoint(lat, lon) {
    setViewState((v) => ({ ...v, longitude: lon, latitude: lat, zoom: 14.5, transitionDuration: 600 }));
  }
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
          {health && <> · MODEL {health.model_loaded ? "✓" : "—"} · MAPPLS {String(health.mappls).toUpperCase()}</>}
        </div>
      </div>

      <div className="body">
        {persona === "btp"
          ? <BTPSidebar btpMode={btpMode} setBtpMode={setBtpMode} stats={stats} tops={tops} rcp={rcp}
              blind={blind} selected={selected} onSelect={focusZone} onFocus={focusPoint}
              plan={plan} onPlan={setPlan} multi={multi} onPreset={presetSelect} />
          : <LogisticsSidebar route={route} busy={busy} onAnalyze={analyzeRoute} onFocus={focusPoint} />}
        <div className="map-wrap">
          <div className="map-ctrl">
            <div className="mc-title">Impact filter</div>
            <label className="mc-check">
              <input type="checkbox" checked={showAll} onChange={(e) => setShowAll(e.target.checked)} />
              <span>Show all zones</span>
            </label>
            <div className="mc-slider" style={{ opacity: showAll ? 0.4 : 1 }}>
              <span className="mc-lab">Impact ≥ <b>{impactMin}</b></span>
              <input type="range" min="0" max="100" step="1" value={impactMin} disabled={showAll}
                onChange={(e) => setImpactMin(+e.target.value)} />
            </div>
            <div className="mc-count">{showAll ? `${shown.toLocaleString()} zones (all)` : `${shown.toLocaleString()} of ${(stats.zones).toLocaleString()} shown`}</div>
            <label className="mc-check" style={{ marginTop: 8, borderTop: "1px solid var(--line)", paddingTop: 8 }}>
              <input type="checkbox" checked={showStations} onChange={(e) => setShowStations(e.target.checked)} />
              <span>Police stations</span>
            </label>
          </div>
          <MapView
            persona={persona} btpMode={btpMode} cells={cells} tops={tops} rcp={rcp} blind={blind}
            selected={selected} route={route} plan={plan} multi={multi}
            viewState={viewState} onViewState={setViewState}
            onSelect={focusZone} onToggleCell={toggleCell}
            showAll={showAll} impactMin={impactMin} stations={stations} showStations={showStations}
          />
        </div>
      </div>
    </div>
  );
}
