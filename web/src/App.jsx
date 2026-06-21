import React, { useEffect, useMemo, useState } from "react";
import { loadStatic, getHealth, impedanceLoop, routeByName, aiHealth } from "./api.js";
import MapView from "./components/MapView.jsx";
import BTPSidebar from "./components/BTPSidebar.jsx";
import LogisticsSidebar from "./components/LogisticsSidebar.jsx";
import CommandBar from "./components/ai/CommandBar.jsx";
import { applyAiActions } from "./lib/aiActions.js";

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
  const [sidebarOpen, setSidebarOpen] = useState(true);
  // map controls
  const [showAll, setShowAll] = useState(true);
  const [impactMin, setImpactMin] = useState(50);
  const [showStations, setShowStations] = useState(false);
  const [aiAvail, setAiAvail] = useState(false);

  useEffect(() => {
    loadStatic("cells.geojson").then(setCells).catch(() => {});
    loadStatic("priority_table.json").then(setTops).catch(() => {});
    loadStatic("rcp.geojson").then(setRcp).catch(() => {});
    loadStatic("blindspots.geojson").then(setBlind).catch(() => {});
    loadStatic("stations.json").then(setStations).catch(() => {});
    getHealth().then(setHealth);
    aiHealth().then((d) => setAiAvail(!!d.available));
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

  function focusPoint(lat, lon, zoom = 14.5) {
    setViewState((v) => ({ ...v, longitude: lon, latitude: lat, zoom, transitionDuration: 600 }));
  }
  const aiApply = (actions) => applyAiActions(actions, {
    setPersona, setBtpMode, setShowAll, setImpactMin, setShowStations, setSelected, setPlan, setRoute, focusPoint,
  });
  function focusZone(z) {
    setSelected(z.gh7);
    setViewState((v) => ({ ...v, longitude: z.lon, latitude: z.lat, zoom: 15, transitionDuration: 600 }));
  }
  function presetSelect(n) { setMulti((tops || []).slice(0, n).map((z) => z.gh7)); }
  function toggleCell(gh7) {
    setMulti((m) => (m.includes(gh7) ? m.filter((x) => x !== gh7) : [...m, gh7]));
  }

  function recenterRoute(r) {
    if (r?.origin && r?.dest)
      setViewState((v) => ({ ...v, longitude: (r.origin.lng + r.dest.lng) / 2,
        latitude: (r.origin.lat + r.dest.lat) / 2, zoom: 11.5, transitionDuration: 700 }));
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
  // Name-based route analysis (fuzzy geocoder) — works without the AI proxy. Throws on
  // unresolved names so the sidebar can surface the message.
  async function analyzeByName(origin, dest) {
    setBusy(true);
    try { const r = await routeByName(origin, dest, 80); setRoute(r); recenterRoute(r); return r; }
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
        <CommandBar available={aiAvail} onActions={aiApply} />
        <div className="health">
          {health ? <span className="live-dot" /> : null}
          API {health ? "ONLINE" : <span style={{ color: "var(--warn)" }}>STATIC-ONLY</span>}
          {health && <> · MODEL {health.model_loaded ? "✓" : "—"} · MAPPLS {String(health.mappls).toUpperCase()}</>}
        </div>
      </div>

      <div className={"body" + (sidebarOpen ? "" : " collapsed")}>
        {persona === "btp"
          ? <BTPSidebar btpMode={btpMode} setBtpMode={setBtpMode} stats={stats} tops={tops} rcp={rcp}
              blind={blind} selected={selected} onSelect={focusZone} onFocus={focusPoint}
              plan={plan} onPlan={setPlan} multi={multi} onPreset={presetSelect} aiAvail={aiAvail} />
          : <LogisticsSidebar route={route} busy={busy} onAnalyze={analyzeRoute} onAnalyzeByName={analyzeByName}
              onFocus={focusPoint} aiAvail={aiAvail} onAiActions={aiApply} />}
        <button className="sidebar-toggle" onClick={() => setSidebarOpen((v) => !v)}
          title={sidebarOpen ? "Hide panel" : "Show panel"} aria-label="Toggle sidebar">
          {sidebarOpen ? "‹" : "›"}
        </button>
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
