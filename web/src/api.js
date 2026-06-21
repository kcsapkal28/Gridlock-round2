// Data access: static bundle (served from /data) + live API (proxied at /api).
export async function loadStatic(name) {
  const r = await fetch(`/data/${name}`);
  if (!r.ok) throw new Error(`static ${name} ${r.status}`);
  return r.json();
}
export async function getHealth() {
  try { const r = await fetch("/api/v1/health"); return r.ok ? r.json() : null; }
  catch { return null; }
}
export async function patrolPlan(units, topk) {
  const r = await fetch(`/api/v1/triage/patrol-plan?units=${units}&topk=${topk}`);
  if (!r.ok) throw new Error(`patrol ${r.status}`);
  return r.json();
}
export async function impedanceLoop(waypoints, min_impact = 80) {
  const r = await fetch("/api/v1/logistics/impedance-loop", {
    method: "POST", headers: { "content-type": "application/json" },
    body: JSON.stringify({ waypoints, min_impact }),
  });
  if (!r.ok) throw new Error(`impedance ${r.status}`);
  return r.json();
}

// ---- AI copilot ----
export async function aiHealth() {
  try { const r = await fetch("/api/v1/ai/health"); return r.ok ? r.json() : { available: false }; }
  catch { return { available: false }; }
}
export async function aiCommand(message, history = [], signal) {
  const r = await fetch("/api/v1/ai/command", {
    method: "POST", headers: { "content-type": "application/json" },
    body: JSON.stringify({ message, history }), signal,
  });
  if (!r.ok) throw new Error(`ai command ${r.status}`);
  return r.json();
}
export async function aiBrief() {
  const r = await fetch("/api/v1/ai/brief");
  if (!r.ok) throw new Error(`ai brief ${r.status}`);
  return r.json();
}
export async function aiExplain(body) {
  const r = await fetch("/api/v1/ai/explain", {
    method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error(`ai explain ${r.status}`);
  return r.json();
}
export async function aiInsights() {
  const r = await fetch("/api/v1/ai/insights");
  if (!r.ok) throw new Error(`ai insights ${r.status}`);
  return r.json();
}
