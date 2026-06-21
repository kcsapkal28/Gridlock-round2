import React, { useMemo } from "react";
import DeckGL from "@deck.gl/react";
import { Map } from "react-map-gl/maplibre";
import { GeoJsonLayer, ScatterplotLayer, PathLayer, TextLayer } from "@deck.gl/layers";
import { impactColor } from "../lib/color.js";

const CARTO_DARK = "https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json";
const hexRgb = (h) => [1, 3, 5].map((i) => parseInt(h.slice(i, i + 2), 16));

export default function MapView(props) {
  const { persona, btpMode, cells, tops, rcp, blind, selected, route, plan, multi,
    viewState, onViewState, onSelect, onToggleCell,
    showAll, impactMin, stations, showStations, commandCards } = props;
  const layers = [];
  const isBTP = persona === "btp";
  const whatif = isBTP && btpMode === "whatif";
  const multiSet = new Set(multi || []);

  // Congestion-impact threshold filter: show all, or only zones with impact >= impactMin.
  const cellData = useMemo(() => {
    if (!cells) return null;
    if (showAll) return cells;
    return { type: "FeatureCollection",
      features: (cells.features || []).filter((f) => (f.properties.impact || 0) >= impactMin) };
  }, [cells, showAll, impactMin]);

  if (cellData) {
    layers.push(new GeoJsonLayer({
      id: "cells", data: cellData, pickable: true, stroked: true, filled: true,
      getFillColor: (f) => {
        if (whatif && multiSet.has(f.properties.gh7)) return [255, 178, 62, 235];
        return impactColor(f.properties.impact, persona === "logistics" ? 90 : 170);
      },
      getLineColor: (f) => (f.properties.gh7 === selected ? [255, 178, 62, 255] : [18, 26, 42, 120]),
      getLineWidth: (f) => (f.properties.gh7 === selected ? 4 : 1),
      lineWidthUnits: "pixels",
      onClick: (info) => { if (info.object) (whatif ? onToggleCell(info.object.properties.gh7) : onSelect(info.object.properties)); },
      updateTriggers: { getFillColor: [whatif, multi], getLineColor: selected, getLineWidth: selected },
    }));
  }

  // Police-station enforcement centroids — geographic reference, any mode.
  if (showStations && stations?.length) {
    const sts = stations.filter((s) => !/^no /i.test(s.name));
    layers.push(new ScatterplotLayer({
      id: "stations", data: sts, pickable: true, getPosition: (d) => [d.lon, d.lat],
      getRadius: 140, radiusMinPixels: 5, radiusMaxPixels: 9,
      getFillColor: [120, 162, 255, 235], getLineColor: [12, 16, 26, 230], lineWidthMinPixels: 1, stroked: true,
    }));
    layers.push(new TextLayer({
      id: "station-labels", data: sts, getPosition: (d) => [d.lon, d.lat], getText: (d) => d.name,
      getSize: 10, getColor: [173, 196, 255, 235], getPixelOffset: [0, -12],
      getTextAnchor: "middle", fontWeight: 500, outlineWidth: 2, outlineColor: [8, 11, 18, 255],
      fontSettings: { sdf: true },
    }));
  }

  // BTP · Hotspots — top markers sized by impact
  if (isBTP && btpMode === "hotspots" && tops?.length) {
    layers.push(new ScatterplotLayer({
      id: "tops", data: tops, pickable: true,
      getPosition: (d) => [d.lon, d.lat], getRadius: (d) => 30 + (d.impact || 0),
      radiusUnits: "meters", radiusMinPixels: 4, getFillColor: (d) => impactColor(d.impact, 235),
      getLineColor: [255, 255, 255, 200], lineWidthMinPixels: 1, stroked: true,
      onClick: (info) => info.object && onSelect(info.object),
    }));
  }

  // BTP · Simple/decision mode — numbered priority-deployment markers
  if (commandCards && commandCards.length) {
    const data = commandCards.map((c, i) => ({ ...c, seq: i + 1 }));
    layers.push(new ScatterplotLayer({
      id: "command-cards", data, pickable: true, getPosition: (d) => [d.lon, d.lat],
      getRadius: 40 + 60, radiusUnits: "meters", radiusMinPixels: 13, radiusMaxPixels: 22,
      getFillColor: [255, 178, 62, 240], getLineColor: [10, 14, 22, 255], lineWidthMinPixels: 2, stroked: true,
      onClick: (info) => info.object && onSelect({ gh7: info.object.gh7, lat: info.object.lat, lon: info.object.lon }),
    }));
    layers.push(new TextLayer({
      id: "command-seq", data, getPosition: (d) => [d.lon, d.lat], getText: (d) => String(d.seq),
      getSize: 14, getColor: [10, 14, 22, 255], getTextAnchor: "middle", getAlignmentBaseline: "center",
      fontWeight: 700, fontSettings: { sdf: true },
    }));
    layers.push(new TextLayer({
      id: "command-area", data, getPosition: (d) => [d.lon, d.lat], getText: (d) => d.area,
      getSize: 11, getColor: [255, 220, 150, 255], getPixelOffset: [0, -20], getTextAnchor: "middle",
      fontWeight: 600, outlineWidth: 2, outlineColor: [8, 11, 18, 255], fontSettings: { sdf: true },
    }));
  }

  // BTP · Patrol Plan — one route + numbered stops per unit
  if (isBTP && btpMode === "patrol" && plan?.units?.length) {
    layers.push(new PathLayer({
      id: "patrol-routes", data: plan.units, getPath: (u) => u.route_geometry,
      getColor: (u) => [...hexRgb(u.color), 235], getWidth: 5, widthUnits: "pixels", capRounded: true, jointRounded: true,
    }));
    // Depots (police stations each unit rolls out from)
    const depots = plan.units.map((u) => u.station && { ...u.station, color: u.color }).filter(Boolean);
    if (depots.length) {
      layers.push(new ScatterplotLayer({
        id: "patrol-depots", data: depots, pickable: true, getPosition: (d) => [d.lon, d.lat],
        getRadius: 150, radiusMinPixels: 8, getFillColor: [10, 14, 22, 235],
        getLineColor: (d) => hexRgb(d.color), lineWidthMinPixels: 3, stroked: true,
      }));
      layers.push(new TextLayer({
        id: "patrol-depot-labels", data: depots, getPosition: (d) => [d.lon, d.lat],
        getText: (d) => `▲ ${d.name}`, getSize: 10, getColor: [173, 196, 255, 235],
        getPixelOffset: [0, -15], getTextAnchor: "middle", fontWeight: 600,
        outlineWidth: 2, outlineColor: [8, 11, 18, 255], fontSettings: { sdf: true },
      }));
    }
    const stops = plan.units.flatMap((u) => u.stops.map((s, i) => ({ ...s, color: u.color, seq: s.seq ?? i + 1 })));
    layers.push(new ScatterplotLayer({
      id: "patrol-stops", data: stops, pickable: true, getPosition: (d) => [d.lon, d.lat],
      getRadius: 130, radiusMinPixels: 9, getFillColor: (d) => hexRgb(d.color),
      getLineColor: [10, 14, 22, 235], lineWidthMinPixels: 2, stroked: true,
      onClick: (info) => info.object && onSelect(info.object),
    }));
    layers.push(new TextLayer({
      id: "patrol-seq", data: stops, getPosition: (d) => [d.lon, d.lat], getText: (d) => String(d.seq),
      getSize: 12, getColor: [10, 14, 22, 255], getTextAnchor: "middle", getAlignmentBaseline: "center",
      fontWeight: 700, fontSettings: { sdf: true },
    }));
  }

  // BTP · Blind Spots — hollow magenta markers
  if (isBTP && btpMode === "blind" && blind?.features?.length) {
    layers.push(new ScatterplotLayer({
      id: "blind", data: blind.features, pickable: true,
      getPosition: (f) => f.geometry.coordinates, getRadius: 130, radiusMinPixels: 7,
      stroked: true, filled: false, getLineColor: [232, 91, 208, 245], lineWidthMinPixels: 2,
      onClick: (info) => info.object && onSelect({ gh7: info.object.properties.gh7,
        lat: info.object.geometry.coordinates[1], lon: info.object.geometry.coordinates[0] }),
    }));
  }

  // Logistics — blocked route + detour + choke cells + origin/dest pins
  if (persona === "logistics" && route) {
    if (route.baseline_route?.geometry?.length)
      layers.push(new PathLayer({ id: "baseline", data: [route.baseline_route.geometry],
        getPath: (d) => d, getColor: [226, 75, 74, 230], getWidth: 6, widthUnits: "pixels", capRounded: true, jointRounded: true }));
    if (route.detour_route?.geometry?.length)
      layers.push(new PathLayer({ id: "detour", data: [route.detour_route.geometry],
        getPath: (d) => d, getColor: [99, 153, 34, 235], getWidth: 6, widthUnits: "pixels", capRounded: true, jointRounded: true }));
    if (route.affected_cells?.length)
      layers.push(new ScatterplotLayer({ id: "affected", data: route.affected_cells, pickable: true,
        getPosition: (d) => [d.lon, d.lat], getRadius: 90, radiusMinPixels: 6,
        getFillColor: [239, 159, 39, 240], getLineColor: [255, 255, 255, 220], stroked: true, lineWidthMinPixels: 1,
        onClick: (info) => info.object && onSelect(info.object) }));
    const od = [route.origin && { ...route.origin, kind: "Pickup", c: [93, 202, 165] },
                route.dest && { ...route.dest, kind: "Drop", c: [120, 162, 255] }].filter(Boolean);
    layers.push(new ScatterplotLayer({ id: "od", data: od, getPosition: (d) => [d.lng, d.lat],
      getRadius: 170, radiusMinPixels: 8, getFillColor: (d) => d.c, getLineColor: [255, 255, 255, 240], stroked: true, lineWidthMinPixels: 2 }));
    layers.push(new TextLayer({ id: "od-labels", data: od, getPosition: (d) => [d.lng, d.lat], getText: (d) => d.kind,
      getSize: 11, getColor: [255, 255, 255, 240], getPixelOffset: [0, -16], getTextAnchor: "middle",
      fontWeight: 700, outlineWidth: 2, outlineColor: [8, 11, 18, 255], fontSettings: { sdf: true } }));
  }

  const getTooltip = ({ object }) => {
    if (!object) return null;
    const p = object.properties || object;
    const rows = [];
    if (p.name && p.n != null && p.lat != null && p.gh7 == null) rows.push(`<div class="t">${p.name} police station</div>`);
    if (p.seq != null) rows.push(`<div class="t">Patrol stop ${p.seq} · rank #${p.rank ?? ""}</div>`);
    if (p.predicted_impact != null) rows.push(`<div class="t">Predicted impact ${p.predicted_impact}/100</div>`);
    if (p.impact != null && p.seq == null) rows.push(`<div class="t">Impact ${(+p.impact).toFixed(0)}/100</div>`);
    if (p.delay_min != null) rows.push(`+${(+p.delay_min).toFixed(1)} min delay`);
    if (p.dominant_vehicle_class) rows.push(`${p.dominant_vehicle_class}`);
    if (p.primary_infraction_type) rows.push(`${p.primary_infraction_type}`);
    if (p.n != null && p.gh7 != null) rows.push(`${(+p.n).toLocaleString()} citations`);
    if (p.tier3_share != null) rows.push(`${Math.round(p.tier3_share * 100)}% carriageway-blocking`);
    if (!rows.length) return null;
    return { html: `<div>${rows.join("<br>")}</div>`,
      style: { background: "rgba(10,14,22,.95)", border: "1px solid #243049", borderRadius: "8px", fontSize: "12px", padding: "8px 10px", color: "#dfe7f2" } };
  };

  return (
    <DeckGL viewState={viewState} onViewStateChange={(e) => onViewState(e.viewState)}
      controller={true} layers={layers} getTooltip={getTooltip}>
      <Map reuseMaps mapStyle={CARTO_DARK} />
      <Legend mode={isBTP ? btpMode : "logistics"} showStations={showStations} />
    </DeckGL>
  );
}

function Dot({ c }) { return <span style={{ display: "inline-block", width: 9, height: 9, borderRadius: 9, background: c, marginRight: 7, verticalAlign: "middle" }} />; }
function Line({ c }) { return <span style={{ display: "inline-block", width: 14, height: 3, borderRadius: 2, background: c, marginRight: 7, verticalAlign: "middle" }} />; }

function Legend({ mode, showStations }) {
  const station = showStations ? <div><Dot c="#78a2ff" />Police station</div> : null;
  if (mode === "blind")
    return <div className="legend"><div><span style={{ color: "#e85bd0" }}>◯</span> Blind spot (under-enforced)</div>{station}</div>;
  if (mode === "patrol")
    return <div className="legend"><div><Line c="#ffb23e" />Patrol route (by unit)</div><div><Dot c="#36d6c3" />Numbered stop</div><div><span style={{ color: "#78a2ff" }}>▲</span> Depot (police station)</div>{station}</div>;
  if (mode === "logistics")
    return <div className="legend">
      <div><Line c="#e24b4a" />Blocked route</div>
      <div><Line c="#639922" />Optimized detour</div>
      <div><Dot c="#ef9f27" />Choke point</div>
      <div><Dot c="#5dcaa5" />Pickup</div><div><Dot c="#78a2ff" />Drop</div>{station}
    </div>;
  return (
    <div className="legend">
      <div>Congestion-Impact Score</div>
      <div className="bar" />
      <div className="ends"><span>0 (low)</span><span>100 (critical)</span></div>
      {station}
    </div>
  );
}
