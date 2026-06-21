// Apply copilot ui_actions to the existing App state. Pure dispatch — the heavy artifacts
// (patrol plan w/ geometry, route w/ paths) arrive here and never touched the model context.
export function applyAiActions(actions, h) {
  for (const a of actions || []) {
    switch (a.type) {
      case "setPersona":
        if (a.persona) h.setPersona(a.persona);
        break;
      case "setMode":
        if (a.mode) h.setBtpMode(a.mode);
        break;
      case "setFilter":
        if (a.show_all != null) h.setShowAll(!!a.show_all);
        if (a.min_impact != null) { h.setShowAll(false); h.setImpactMin(a.min_impact); }
        break;
      case "toggleStations":
        h.setShowStations(!!a.on);
        break;
      case "focusZone":
        if (a.gh7) h.setSelected(a.gh7);
        if (a.lat != null && a.lon != null) h.focusPoint(a.lat, a.lon);
        break;
      case "showPatrolPlan":
        if (a.plan) { h.setPlan(a.plan); const s = a.plan.units?.[0]?.stops?.[0]; if (s) h.focusPoint(s.lat, s.lon); }
        break;
      case "showRoute":
        if (a.route) {
          h.setRoute(a.route);
          const o = a.route.origin, d = a.route.dest;
          if (o && d) h.focusPoint((o.lat + d.lat) / 2, ((o.lng ?? o.lon) + (d.lng ?? d.lon)) / 2, 11.5);
        }
        break;
      default:
        break;
    }
  }
}
