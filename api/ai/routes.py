"""AI copilot endpoints. `build_ai_router(svc, mappls)` returns a FastAPI router wired to the
already-constructed scoring service + MapMyIndia client, so it shares their loaded artifacts."""
import json
import os
from fastapi import APIRouter
from pydantic import BaseModel

from api.config import settings
from api.logistics import load_rcp
from api.ai.client import AIClient
from api.ai.tools import ToolExecutor, TOOLS
from api.ai import prompts, insights as insights_mod


def _load_json(path, default):
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return default


class CommandReq(BaseModel):
    message: str
    history: list = []          # [{role:"user"|"assistant", content:"..."}], text-only


class ExplainReq(BaseModel):
    gh7: str | None = None
    route_summary: dict | None = None


def build_ai_router(svc, mappls):
    ai = AIClient(settings)
    rcp = load_rcp()
    blind = _load_json(os.path.join(settings.STATIC_OUT, "blindspots.geojson"), {}).get("features", [])
    stations = _load_json(os.path.join(settings.STATIC_OUT, "stations.json"), [])
    ex = ToolExecutor(svc, mappls, rcp, blind, stations)
    r = APIRouter(prefix="/api/v1/ai")

    @r.get("/health")
    def health():
        return {"available": ai.available(), "model": settings.AI_MODEL if settings.AI_ENABLED else None}

    @r.post("/command")
    def command(req: CommandReq):
        if not ai.available():
            return {"available": False, "reply": "Copilot is offline.", "ui_actions": []}
        hist = [m for m in (req.history or []) if m.get("role") in ("user", "assistant") and m.get("content")]
        hist = hist[-(settings.AI_HISTORY_EXCHANGES * 2):]
        msgs = [{"role": m["role"], "content": str(m["content"])[:1000]} for m in hist]
        msgs.append({"role": "user", "content": req.message})
        reply, actions = ai.run(prompts.COMMAND_SYSTEM, msgs, TOOLS, ex.dispatch)
        return {"available": True, "reply": reply, "ui_actions": actions}

    @r.get("/brief")
    def brief():
        if not ai.available():
            return {"available": False, "brief": ""}
        top, _ = ex.query_hotspots({"limit": 5})
        bs, _ = ex.find_blindspots({"limit": 3})
        data = {"top_zones": top["top"], "total_zones": int(len(svc.df)),
                "rankable": int(svc.df["ranked"].sum()), "blind_spots": bs["top"]}
        text = ai.complete(prompts.BRIEF_SYSTEM, prompts.BRIEF_TASK.format(data=json.dumps(data, default=str)))
        return {"available": True, "brief": text}

    @r.post("/explain")
    def explain(req: ExplainReq):
        if not ai.available():
            return {"available": False, "text": ""}
        if req.gh7:
            data, _ = ex.get_zone({"gh7": req.gh7})
            task = prompts.EXPLAIN_ZONE_TASK
        elif req.route_summary:
            data = req.route_summary
            task = prompts.EXPLAIN_ROUTE_TASK
        else:
            return {"available": True, "text": ""}
        text = ai.complete(prompts.EXPLAIN_SYSTEM, task.format(data=json.dumps(data, default=str)), max_tokens=220)
        return {"available": True, "text": text}

    @r.get("/insights")
    def insights():
        if not ai.available():
            return {"available": False, "insights": []}
        cand = insights_mod.candidates(svc)
        if not cand["findings"]:
            return {"available": True, "insights": []}
        text = ai.complete(prompts.INSIGHTS_SYSTEM, prompts.INSIGHTS_TASK.format(data=json.dumps(cand)))
        lines = [ln.strip(" -•").strip() for ln in text.splitlines() if ln.strip()]
        return {"available": True, "insights": lines[:3]}

    return r
