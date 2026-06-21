// Data access: static bundle (served from /data) + live API.
// In dev, API is "" → Vite proxies /api → localhost:8011. In prod, set VITE_API_BASE to the backend URL.
const API = import.meta.env.VITE_API_BASE || "";

export async function loadStatic(name) {
  const r = await fetch(`/data/${name}`);
  if (!r.ok) throw new Error(`static ${name} ${r.status}`);
  return r.json();
}
export async function getHealth() {
  try { const r = await fetch(`${API}/api/v1/health`); return r.ok ? r.json() : null; }
  catch { return null; }
}
export async function patrolPlan(units, topk, priority = "impact", startFromStation = true) {
  const r = await fetch(`${API}/api/v1/triage/patrol-plan?units=${units}&topk=${topk}`
    + `&priority=${priority}&start_from_station=${startFromStation}`);
  if (!r.ok) throw new Error(`patrol ${r.status}`);
  return r.json();
}
// Forgiving area-name geocoder (typos / abbreviations OK). Returns {name,lat,lon,...} or {error}.
export async function geocodePlace(q) {
  const r = await fetch(`${API}/api/v1/geocode?q=${encodeURIComponent(q)}`);
  if (!r.ok) throw new Error(`geocode ${r.status}`);
  return r.json();
}
// Analyse a delivery route from two free-typed names — no AI proxy required.
export async function routeByName(origin, dest, minImpact = 80) {
  const r = await fetch(`${API}/api/v1/logistics/route-by-name?origin=${encodeURIComponent(origin)}`
    + `&dest=${encodeURIComponent(dest)}&min_impact=${minImpact}`);
  const j = await r.json().catch(() => null);
  if (!r.ok) throw new Error((j && j.error && j.error.message) || `route ${r.status}`);
  return j;
}
export async function impedanceLoop(waypoints, min_impact = 80) {
  const r = await fetch(`${API}/api/v1/logistics/impedance-loop`, {
    method: "POST", headers: { "content-type": "application/json" },
    body: JSON.stringify({ waypoints, min_impact }),
  });
  if (!r.ok) throw new Error(`impedance ${r.status}`);
  return r.json();
}

// ---- AI copilot ----
export async function aiHealth() {
  try { const r = await fetch(`${API}/api/v1/ai/health`); return r.ok ? r.json() : { available: false }; }
  catch { return { available: false }; }
}
export async function aiCommand(message, history = [], signal) {
  const r = await fetch(`${API}/api/v1/ai/command`, {
    method: "POST", headers: { "content-type": "application/json" },
    body: JSON.stringify({ message, history }), signal,
  });
  if (!r.ok) throw new Error(`ai command ${r.status}`);
  return r.json();
}
export async function aiBrief() {
  const r = await fetch(`${API}/api/v1/ai/brief`);
  if (!r.ok) throw new Error(`ai brief ${r.status}`);
  return r.json();
}
export async function aiExplain(body) {
  const r = await fetch(`${API}/api/v1/ai/explain`, {
    method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error(`ai explain ${r.status}`);
  return r.json();
}
export async function aiInsights() {
  const r = await fetch(`${API}/api/v1/ai/insights`);
  if (!r.ok) throw new Error(`ai insights ${r.status}`);
  return r.json();
}
