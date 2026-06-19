import React from "react";
import DeckGL from "@deck.gl/react";
import { Map } from "react-map-gl/maplibre";
import { GeoJsonLayer, ScatterplotLayer, PathLayer } from "@deck.gl/layers";
import { impactColor } from "../lib/color.js";

const CARTO_DARK = "https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json";

export default function MapView({ persona, cells, tops, rcp, selected, route, viewState, onViewState, onSelect }) {
  const layers = [];

  if (cells) {
    layers.push(new GeoJsonLayer({
      id: "cells",
      data: cells,
      pickable: true,
      stroked: true,
      filled: true,
      getFillColor: (f) => impactColor(f.properties.impact, persona === "logistics" ? 90 : 170),
      getLineColor: (f) => (f.properties.gh7 === selected ? [78, 161, 255, 255] : [20, 28, 44, 120]),
      getLineWidth: (f) => (f.properties.gh7 === selected ? 4 : 1),
      lineWidthUnits: "pixels",
      updateTriggers: { getLineColor: selected, getLineWidth: selected },
    }));
  }

  // BTP: top hotspot markers (sized by impact)
  if (persona === "btp" && tops?.length) {
    layers.push(new ScatterplotLayer({
      id: "tops",
      data: tops,
      pickable: true,
      getPosition: (d) => [d.lon, d.lat],
      getRadius: (d) => 30 + (d.impact || 0),
      radiusUnits: "meters",
      radiusMinPixels: 4,
      getFillColor: (d) => impactColor(d.impact, 230),
      getLineColor: [255, 255, 255, 200],
      lineWidthMinPixels: 1,
      stroked: true,
      onClick: (info) => info.object && onSelect(info.object),
    }));
  }

  // Logistics: baseline (red) + detour (green) + affected cells
  if (persona === "logistics" && route) {
    if (route.baseline_route?.geometry?.length)
      layers.push(new PathLayer({
        id: "baseline", data: [route.baseline_route.geometry],
        getPath: (d) => d, getColor: [220, 40, 50, 220], getWidth: 6, widthUnits: "pixels",
      }));
    if (route.detour_route?.geometry?.length)
      layers.push(new PathLayer({
        id: "detour", data: [route.detour_route.geometry],
        getPath: (d) => d, getColor: [61, 220, 151, 230], getWidth: 6, widthUnits: "pixels",
      }));
    if (route.affected_cells?.length)
      layers.push(new ScatterplotLayer({
        id: "affected", data: route.affected_cells, pickable: true,
        getPosition: (d) => [d.lon, d.lat], getRadius: 70, radiusMinPixels: 6,
        getFillColor: [240, 120, 40, 240], getLineColor: [255, 255, 255, 220], stroked: true, lineWidthMinPixels: 1,
      }));
  }

  const getTooltip = ({ object }) => {
    if (!object) return null;
    const p = object.properties || object;
    const rows = [];
    if (p.impact != null) rows.push(`<div class="t">Impact ${(+p.impact).toFixed(0)}/100</div>`);
    if (p.delay_min != null) rows.push(`⏱ ${(+p.delay_min).toFixed(1)} min delay`);
    if (p.dominant_vehicle_class) rows.push(`🚗 ${p.dominant_vehicle_class}`);
    if (p.primary_infraction_type) rows.push(`⚠ ${p.primary_infraction_type}`);
    if (p.n != null) rows.push(`${p.n} citations`);
    if (p.tier3_share != null) rows.push(`${Math.round(p.tier3_share * 100)}% carriageway-blocking`);
    return { html: `<div>${rows.join("<br>")}</div>`,
      style: { background: "rgba(10,14,22,.95)", border: "1px solid #243049", borderRadius: "8px", fontSize: "12px", padding: "8px 10px" } };
  };

  return (
    <DeckGL
      viewState={viewState}
      onViewStateChange={(e) => onViewState(e.viewState)}
      controller={true}
      layers={layers}
      getTooltip={getTooltip}
    >
      <Map reuseMaps mapStyle={CARTO_DARK} />
      <Legend />
    </DeckGL>
  );
}

function Legend() {
  return (
    <div className="legend">
      <div>Congestion-Impact Score</div>
      <div className="bar" />
      <div className="ends"><span>0</span><span>100</span></div>
    </div>
  );
}
