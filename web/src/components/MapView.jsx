import React from "react";
import DeckGL from "@deck.gl/react";
import { Map } from "react-map-gl/maplibre";
import { GeoJsonLayer, ScatterplotLayer, PathLayer } from "@deck.gl/layers";
import { impactColor } from "../lib/color.js";

const CARTO_DARK = "https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json";
const hexRgb = (h) => [1, 3, 5].map((i) => parseInt(h.slice(i, i + 2), 16));

export default function MapView(props) {
  const { persona, btpMode, cells, tops, rcp, blind, selected, route, plan, multi,
    viewState, onViewState, onSelect, onToggleCell } = props;
  const layers = [];
  const isBTP = persona === "btp";
  const whatif = isBTP && btpMode === "whatif";
  const multiSet = new Set(multi || []);

  if (cells) {
    layers.push(new GeoJsonLayer({
      id: "cells", data: cells, pickable: true, stroked: true, filled: true,
      getFillColor: (f) => {
        if (whatif && multiSet.has(f.properties.gh7)) return [255, 178, 62, 230];
        return impactColor(f.properties.impact, persona === "logistics" ? 90 : 160);
      },
      getLineColor: (f) => (f.properties.gh7 === selected ? [255, 178, 62, 255] : [20, 28, 44, 110]),
      getLineWidth: (f) => (f.properties.gh7 === selected ? 4 : 1),
      lineWidthUnits: "pixels",
      onClick: (info) => { if (whatif && info.object) onToggleCell(info.object.properties.gh7); },
      updateTriggers: {
        getFillColor: [whatif, multi], getLineColor: selected, getLineWidth: selected,
      },
    }));
  }

  // BTP · Hotspots — top markers
  if (isBTP && btpMode === "hotspots" && tops?.length) {
    layers.push(new ScatterplotLayer({
      id: "tops", data: tops, pickable: true,
      getPosition: (d) => [d.lon, d.lat], getRadius: (d) => 30 + (d.impact || 0),
      radiusUnits: "meters", radiusMinPixels: 4, getFillColor: (d) => impactColor(d.impact, 230),
      getLineColor: [255, 255, 255, 200], lineWidthMinPixels: 1, stroked: true,
      onClick: (info) => info.object && onSelect(info.object),
    }));
  }

  // BTP · Patrol Plan — one route + numbered stops per unit
  if (isBTP && btpMode === "patrol" && plan?.units?.length) {
    layers.push(new PathLayer({
      id: "patrol-routes", data: plan.units, getPath: (u) => u.route_geometry,
      getColor: (u) => [...hexRgb(u.color), 230], getWidth: 5, widthUnits: "pixels", capRounded: true,
    }));
    const stops = plan.units.flatMap((u) => u.stops.map((s, i) => ({ ...s, color: u.color, seq: i + 1 })));
    layers.push(new ScatterplotLayer({
      id: "patrol-stops", data: stops, pickable: true, getPosition: (d) => [d.lon, d.lat],
      getRadius: 90, radiusMinPixels: 7, getFillColor: (d) => hexRgb(d.color),
      getLineColor: [10, 14, 22, 230], lineWidthMinPixels: 2, stroked: true,
    }));
  }

  // BTP · Blind Spots — hollow magenta markers
  if (isBTP && btpMode === "blind" && blind?.features?.length) {
    layers.push(new ScatterplotLayer({
      id: "blind", data: blind.features, pickable: true,
      getPosition: (f) => f.geometry.coordinates, getRadius: 120, radiusMinPixels: 7,
      stroked: true, filled: false, getLineColor: [232, 91, 208, 240], lineWidthMinPixels: 2,
    }));
  }

  // Logistics — baseline + detour + affected
  if (persona === "logistics" && route) {
    if (route.baseline_route?.geometry?.length)
      layers.push(new PathLayer({ id: "baseline", data: [route.baseline_route.geometry],
        getPath: (d) => d, getColor: [220, 40, 50, 220], getWidth: 6, widthUnits: "pixels" }));
    if (route.detour_route?.geometry?.length)
      layers.push(new PathLayer({ id: "detour", data: [route.detour_route.geometry],
        getPath: (d) => d, getColor: [61, 220, 151, 230], getWidth: 6, widthUnits: "pixels" }));
    if (route.affected_cells?.length)
      layers.push(new ScatterplotLayer({ id: "affected", data: route.affected_cells, pickable: true,
        getPosition: (d) => [d.lon, d.lat], getRadius: 70, radiusMinPixels: 6,
        getFillColor: [240, 120, 40, 240], getLineColor: [255, 255, 255, 220], stroked: true, lineWidthMinPixels: 1 }));
  }

  const getTooltip = ({ object }) => {
    if (!object) return null;
    const p = object.properties || object;
    const rows = [];
    if (p.seq != null) rows.push(`<div class="t">Unit stop ${p.seq}</div>`);
    if (p.predicted_impact != null) rows.push(`<div class="t">Predicted impact ${p.predicted_impact}</div>`);
    if (p.impact != null) rows.push(`<div class="t">Impact ${(+p.impact).toFixed(0)}/100</div>`);
    if (p.delay_min != null) rows.push(`⏱ ${(+p.delay_min).toFixed(1)} min delay`);
    if (p.dominant_vehicle_class) rows.push(`🚗 ${p.dominant_vehicle_class}`);
    if (p.primary_infraction_type) rows.push(`⚠ ${p.primary_infraction_type}`);
    if (p.n != null) rows.push(`${p.n} citations`);
    if (p.tier3_share != null) rows.push(`${Math.round(p.tier3_share * 100)}% carriageway-blocking`);
    if (!rows.length) return null;
    return { html: `<div>${rows.join("<br>")}</div>`,
      style: { background: "rgba(10,14,22,.95)", border: "1px solid #243049", borderRadius: "8px", fontSize: "12px", padding: "8px 10px" } };
  };

  return (
    <DeckGL viewState={viewState} onViewStateChange={(e) => onViewState(e.viewState)}
      controller={true} layers={layers} getTooltip={getTooltip}>
      <Map reuseMaps mapStyle={CARTO_DARK} />
      <Legend mode={isBTP ? btpMode : "logistics"} />
    </DeckGL>
  );
}

function Legend({ mode }) {
  if (mode === "blind")
    return <div className="legend"><div>● Blind spot (under-enforced)</div></div>;
  if (mode === "patrol")
    return <div className="legend"><div>Patrol routes by unit</div></div>;
  return (
    <div className="legend">
      <div>Congestion-Impact Score</div>
      <div className="bar" />
      <div className="ends"><span>0</span><span>100</span></div>
    </div>
  );
}
