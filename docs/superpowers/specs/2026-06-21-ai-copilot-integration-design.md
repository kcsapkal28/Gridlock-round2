# GridLock AI Copilot — Integration Design

**Date:** 2026-06-21 · **Status:** approved scope, pending spec review
**Goal:** Tightly integrate Claude as the reasoning layer of GridLock so the product reads as
a *robust AI-native enforcement console*, not an app with a bolted-on chatbot. Every AI
surface is grounded strictly on our own scored data (competition-compliant) and degrades
gracefully when the LLM backend is offline.

---

## 1. Why / fit to the problem statement
The problem is *targeted enforcement of parking-induced congestion*. Raw scores already exist;
the gap is turning them into **decisions** a duty officer or dispatcher acts on. Claude closes
that gap three ways: a command surface that drives the system, proactive operational briefs,
and contextual "why + what to do" reasoning. This is decision-support, not Q&A.

## 2. Compliance (hard rules)
- The copilot is a **reasoning/interface layer over our own computed results**. It ingests **no
  external data**. System prompt enforces: *answer only from tool results; never invent zones,
  numbers, or facts; if a tool returns nothing, say so.*
- MapMyIndia remains **mapping-infrastructure only** (geocoding/routing). No Places/Live-Traffic.
- Place-name resolution uses a **native gazetteer** built from our own data (police-station
  centroids in `web/public/data/stations.json` + station/area names), with MapMyIndia forward
  geocoding as an optional fallback — never an external knowledge source.

## 3. Four capabilities (v1, all approved)
1. **Command bar (NL operator).** Top-bar ⌘K input that drives the app via tool-use:
   "plan 3 patrols around HSR tonight", "show only zones above 80", "analyze City Market → Hebbal".
2. **Auto enforcement brief.** Grounded operational brief at the top of the BTP sidebar:
   priority zones + reasons, suggested unit allocation, blind-spot alerts. Loads on open + refresh.
3. **Explain & recommend on select.** Inline "AI read" when a zone is selected or a route analyzed:
   plain-English why-it's-high-impact + recommended enforcement/dispatch action.
4. **Proactive insight flags.** 1–3 unprompted, data-derived insights (e.g. impact-rank ≫
   volume-rank → under-counted; rising per-station severity; freight choke clusters). Candidates
   are computed natively; Claude phrases/prioritizes them.

## 4. Architecture — server-side agentic loop
```
Browser (command bar / brief card / AI-read block / insights strip)
  │  POST /api/v1/ai/command  { message, history }
  │  GET  /api/v1/ai/brief
  │  POST /api/v1/ai/explain  { gh7 | route_summary }
  │  GET  /api/v1/ai/insights
  ▼
FastAPI  api/ai/  ──► Claude via proxy :4001 (Anthropic Messages API, tool-use)
  │   ONLY /ai/command runs an agentic loop. Each tool returns TWO payloads:
  │     • model_summary  → tiny grounded JSON the model sees (no geometry, no big arrays)
  │     • ui_artifact    → full object (plan w/ route_geometry, route w/ paths) → ui_actions,
  │                        sent straight to the browser, NEVER into model context
  ▼
Response: { reply, ui_actions[] }   ← text + actions the UI applies to existing App state
```
- **Only the command bar loops.** `brief`, `explain`, `insights` are **single model calls**:
  the backend deterministically pre-fetches a *compact* grounded context (already computed
  numbers) and makes ONE call to phrase it. No tool round-trips → fast and bounded.
- **LLM transport:** `anthropic` Python SDK pointed at the local proxy
  (`base_url=AI_BASE_URL`, default `http://localhost:4001`), authenticated by the proxy's
  own Claude CLI session (no separate key needed; `AI_API_KEY` default `sk-dummy`).
- **Primary path:** native tool-use through the 4001 passthrough. **Risk + fallback:** if
  4001 tool-use proves unreliable, fall back to a manual "emit-JSON-action" loop over the
  same SDK with a strict JSON schema. (Implementation task 0 verifies tool-use first.)

## 5. Backend (`api/ai/`)
New module, isolated from existing endpoints:
- `client.py` — thin Claude wrapper (build messages, run tool loop, model selection, timeout,
  health check). Single model for all surfaces: `AI_MODEL` (default `claude-sonnet-4-6`),
  used by the command loop and by brief/explain/insights alike.
- `tools.py` — tool definitions + executors. Each returns `(model_summary, ui_artifact)`;
  `model_summary` is hard-capped (see §5.5). Columns: what the model sees vs what the UI gets.
  | Tool | model_summary (compact) | ui_artifact |
  |---|---|---|
  | `query_hotspots(min_impact?, limit≤10, near?)` | top rows `{gh7, impact, tier3%, heavy%, n}` | — (optional focus) |
  | `get_zone(gh7? \| lat,lon?)` | one zone's scalar fields | `focusZone` |
  | `make_patrol_plan(units, topk, near?)` | `{units, n_zones, drive_mins[], total_impact[]}` | full plan **incl. route_geometry** → `showPatrolPlan` |
  | `analyze_route(origin, dest)` | `{total_delay, sla, recoverable, n_chokes, worst_gh7}` | full route **incl. baseline/detour paths** → `showRoute` |
  | `set_map_view(min_impact? \| show_all? \| focus_gh7? \| persona? \| mode?)` | `{ok:true}` | the corresponding view `ui_action` |
  | `find_blindspots(limit≤10)` | top rows `{gh7, predicted_impact, gap}` | — |
  | `geocode(place)` | `{lat, lon, matched_name}` | — |
  `build_plan` gains an optional `near{lat,lon,radius_km}` filter so "patrols around HSR" plans
  over that area's zones. The full plan/route (geometry) reaches the browser via `ui_artifact`
  only — it is never serialized into the model conversation.
- `routes.py` — the four endpoints; assembles grounded context, runs the loop, returns
  `{reply, ui_actions}` (command) or grounded text (brief/explain/insights).
- `prompts.py` — system prompt + per-endpoint task prompts (operational, concise, grounded).
- `insights.py` — native candidate computation for pillar 4 (divergence, per-station severity).
- Config additions in `api/config.py`: `AI_BASE_URL`, `AI_API_KEY`, `AI_MODEL`
  (default `claude-sonnet-4-6`), `AI_ENABLED`, `AI_TIMEOUT`, `AI_MAX_TOOL_ITERS` (default 5),
  `AI_MODEL_SUMMARY_MAX_CHARS` (≈1500), `AI_HISTORY_EXCHANGES` (default 2). See §5.5.
- `GET /api/v1/ai/health` (or extend `/health`): reports copilot availability.
- `anthropic` added to `requirements-api.txt`.

### ui_actions schema (backend → frontend)
A list of `{ "type": ..., ...payload }`. Types: `focusZone{gh7|lat,lon,zoom}`,
`setFilter{show_all?|min_impact?}`, `setPersona{btp|logistics}`, `setMode{hotspots|patrol|whatif|blind}`,
`showPatrolPlan{plan}`, `showRoute{route}`, `toggleStations{on}`. The frontend applies each to
existing App state — so when the copilot "makes a patrol plan," the map actually renders it.

## 5.5 Performance & context management (fast, seamless, bounded)
The whole point of the split payload is that **large data never enters the model loop**. Rules:

**Bound the context, every request:**
- **System prompt + tool schemas are static and small** (~1–1.5k tokens total): tight tool
  descriptions, the metric primer kept to ~120 words. Sent identically each call so the proxy
  can prompt-cache them if supported (set `cache_control` on system+tools; harmless if ignored).
- **`model_summary` size cap:** each tool result is truncated server-side before it reaches the
  model — lists ≤ 10 rows, only scalar fields, **no geometry, no per-citation data, no GeoJSON.**
  A hard `MODEL_SUMMARY_MAX_CHARS` (≈ 1500) guards every tool result.
- **History is text-only and short.** After a command turn completes, the loop's `tool_use` /
  `tool_result` blocks are **discarded**; only `{user, assistant_text}` is kept, and only the
  **last 2 exchanges** are replayed. Tool plumbing is per-turn and never accumulates.
- **Loop cap:** `AI_MAX_TOOL_ITERS = 5`, but typical commands resolve in 1–2 iterations. Encourage
  **parallel tool calls** (Claude can emit several in one turn) so independent lookups don't serialize.

**Keep it fast:**
- 3 of 4 surfaces (`brief`/`explain`/`insights`) are **one model call** over pre-computed compact
  data — no tool round-trips.
- **Pre-warm:** fetch `/ai/brief` in the background on app load; **cache** the brief for the session
  (refresh button regenerates). **LRU-cache `explain` by gh7** so re-selecting a zone is instant.
- **Abort in-flight:** a new command cancels the previous request (AbortController + server-side
  cancellation) so the UI never queues stale work.
- **Optimistic UI:** `ui_actions` apply the moment they arrive (map moves/plan renders) while the
  reply text settles — the system feels responsive even if the final sentence lands a beat later.

**Budget targets (Sonnet via proxy):** brief/explain/insights ≈ 1 call (~1–3 s); command ≈ 1–2
calls typical, ≤ 5 worst case. Per-request model context stays well under ~4k input tokens because
geometry/large arrays are structurally excluded. Streaming is a fast-follow, not required for v1.

## 6. Frontend (embedded, not a chat panel)
- **Command bar** (`web/src/components/ai/CommandBar.jsx`): input in the top bar + ⌘K to focus.
  On submit → `POST /ai/command` → apply `ui_actions` via a dispatcher → show the reply as a slim
  result line (last exchange only; not a scrolling chat). Loading + "AI offline" states.
- **Brief card** (`ai/BriefCard.jsx`): top of BTP sidebar; loads `/ai/brief` on mount; refresh button.
- **AI read** (`ai/AiRead.jsx`): rendered in the zone-selection detail and after route analysis;
  calls `/ai/explain`; shows narrative + recommended action.
- **Insights strip** (`ai/Insights.jsx`): 1–3 compact cards under the brief from `/ai/insights`.
- **Action dispatcher** (`web/src/lib/aiActions.js`): pure function mapping a `ui_action` to the
  App state setters already present (`setViewState`, `setPlan`, `setRoute`, `setShowAll`,
  `setImpactMin`, `setPersona`, `setBtpMode`, `setShowStations`).
- **API client** additions in `web/src/api.js`: `aiCommand`, `aiBrief`, `aiExplain`, `aiInsights`,
  `aiHealth`.
- Styling consistent with the existing dark instrument-panel theme (amber signal accent).

## 7. Data flow (command example)
"plan 3 patrols around HSR tonight" → `/ai/command` → Claude calls `geocode("HSR")` →
`make_patrol_plan(units=3, topk=15)` (biased to that area) → returns `{reply:"Deployed 3
units covering the 15 highest-impact HSR-area zones; Unit 1 …", ui_actions:[{setPersona:btp},
{setMode:patrol},{showPatrolPlan:{…}},{focusZone:…}]}` → UI switches to patrol mode and renders.

## 8. Error handling & degradation
- Proxy unreachable / timeout → endpoints return `{available:false}`; UI hides/greys AI surfaces
  and shows "AI offline". Core app fully functional (same pattern as the MapMyIndia fallback).
- Tool execution error → captured, returned to Claude as a tool_result error so it can recover or
  explain; never 500s the whole request.
- Tool-loop capped at `AI_MAX_TOOL_ITERS` to bound latency/cost.
- All AI text is advisory; the underlying numbers always come from the deterministic API.

## 9. Testing
- Backend unit tests (`api/tests/test_ai_*.py`) with the Claude client **mocked**: tool dispatch,
  the agent loop (tool_use → execute → result → final), ui_action assembly, grounding-guard
  (model output referencing a number not in tool results is flagged in tests via fixture),
  degradation when client disabled. No real LLM calls in tests.
- **Context-bound tests (explicit):** every tool's `model_summary` stays within
  `AI_MODEL_SUMMARY_MAX_CHARS` and contains **no geometry/GeoJSON** (assert on a full
  patrol-plan and route result); history replay never exceeds `AI_HISTORY_EXCHANGES` and carries
  no `tool_use`/`tool_result` blocks. These lock in the "context can't blow up" guarantee.
- Frontend: manual in-browser verification of each surface (command drives map, brief renders,
  AI-read on select, insights), plus offline-state check.

## 10. Out of scope (v1 / YAGNI)
- Token streaming (non-streaming v1; clean loading states). Streaming is a fast-follow.
- Multi-turn long chat history / memory (command keeps only the last exchange).
- Voice input. User accounts. Persisting conversations.

## 11. File list
New: `api/ai/{__init__,client,tools,routes,prompts,insights}.py`,
`api/tests/test_ai_tools.py`, `api/tests/test_ai_loop.py`,
`web/src/components/ai/{CommandBar,BriefCard,AiRead,Insights}.jsx`,
`web/src/lib/aiActions.js`.
Modified: `api/main.py` (mount ai routes), `api/config.py`, `requirements-api.txt`,
`web/src/App.jsx` (mount surfaces + dispatcher), `web/src/api.js`, `web/src/theme.css`,
`README.md`, `USER_GUIDE.md`.
Branch: `feat/llm-copilot`.
