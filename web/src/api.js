// Data access: static bundle (served from /data) + live API.
// In dev, API is "" → Vite proxies /api → localhost:8011. In prod, set VITE_API_BASE to the backend URL.
const API = import.meta.env.VITE_API_BASE || "";

// ---- judge-supplied API keys (stored in this browser only, sent as per-request headers) ----
const KEY_STORE = "gridlock.keys";
export function getKeys() {
  try { return JSON.parse(localStorage.getItem(KEY_STORE)) || {}; }
  catch { return {}; }
}
export function setKeys(k) {
  const cur = getKeys();
  localStorage.setItem(KEY_STORE, JSON.stringify({ ...cur, ...k }));
}
export function clearKeys() { localStorage.removeItem(KEY_STORE); }

// Headers carrying the keys (omitted when blank). These reach the backend, which uses them
// per-request only and never stores them server-side.
function keyHeaders() {
  const k = getKeys(), h = {};
  if (k.mappls) h["X-Mappls-Key"] = k.mappls.trim();
  if (k.anthropic) h["X-Anthropic-Key"] = k.anthropic.trim();
  if (k.model) h["X-AI-Model"] = k.model.trim();
  return h;
}
// fetch against the API with key headers always attached.
function apiFetch(path, opts = {}) {
  return fetch(`${API}${path}`, { ...opts, headers: { ...keyHeaders(), ...(opts.headers || {}) } });
}

export async function loadStatic(name) {
  const r = await fetch(`/data/${name}`);
  if (!r.ok) throw new Error(`static ${name} ${r.status}`);
  return r.json();
}
export async function getHealth() {
  try { const r = await apiFetch(`/api/v1/health`); return r.ok ? r.json() : null; }
  catch { return null; }
}
export async function patrolPlan(units, topk, priority = "impact", startFromStation = true) {
  const r = await apiFetch(`/api/v1/triage/patrol-plan?units=${units}&topk=${topk}`
    + `&priority=${priority}&start_from_station=${startFromStation}`);
  if (!r.ok) throw new Error(`patrol ${r.status}`);
  return r.json();
}
// Forgiving area-name geocoder (typos / abbreviations OK). Returns {name,lat,lon,...} or {error}.
export async function geocodePlace(q) {
  const r = await apiFetch(`/api/v1/geocode?q=${encodeURIComponent(q)}`);
  if (!r.ok) throw new Error(`geocode ${r.status}`);
  return r.json();
}
// Analyse a delivery route from two free-typed names — no AI proxy required.
export async function routeByName(origin, dest, minImpact = 80) {
  const r = await apiFetch(`/api/v1/logistics/route-by-name?origin=${encodeURIComponent(origin)}`
    + `&dest=${encodeURIComponent(dest)}&min_impact=${minImpact}`);
  const j = await r.json().catch(() => null);
  if (!r.ok) throw new Error((j && j.error && j.error.message) || `route ${r.status}`);
  return j;
}
export async function impedanceLoop(waypoints, min_impact = 80) {
  const r = await apiFetch(`/api/v1/logistics/impedance-loop`, {
    method: "POST", headers: { "content-type": "application/json" },
    body: JSON.stringify({ waypoints, min_impact }),
  });
  if (!r.ok) throw new Error(`impedance ${r.status}`);
  return r.json();
}

// ---- AI copilot ----
export async function aiHealth() {
  try { const r = await apiFetch(`/api/v1/ai/health`); return r.ok ? r.json() : { available: false }; }
  catch { return { available: false }; }
}
export async function aiCommand(message, history = [], signal) {
  const r = await apiFetch(`/api/v1/ai/command`, {
    method: "POST", headers: { "content-type": "application/json" },
    body: JSON.stringify({ message, history }), signal,
  });
  if (!r.ok) throw new Error(`ai command ${r.status}`);
  return r.json();
}
export async function aiBrief() {
  const r = await apiFetch(`/api/v1/ai/brief`);
  if (!r.ok) throw new Error(`ai brief ${r.status}`);
  return r.json();
}
export async function aiExplain(body) {
  const r = await apiFetch(`/api/v1/ai/explain`, {
    method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error(`ai explain ${r.status}`);
  return r.json();
}
export async function aiInsights() {
  const r = await apiFetch(`/api/v1/ai/insights`);
  if (!r.ok) throw new Error(`ai insights ${r.status}`);
  return r.json();
}
