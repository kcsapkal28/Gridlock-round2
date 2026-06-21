"""Agentic loop tests with a fully mocked Claude client — no real LLM calls."""
import json
import types
from api.ai.client import AIClient
from api.config import settings


def _blk(**kw):
    b = types.SimpleNamespace(**kw)
    b.model_dump = lambda: {k: v for k, v in kw.items() if k != "model_dump"}
    return b


class FakeMessages:
    """Scripted: first create() asks for a tool, second returns final text. Records msgs sent."""
    def __init__(self):
        self.calls = []
    def create(self, **kw):
        self.calls.append(kw)
        if len(self.calls) == 1:
            return types.SimpleNamespace(stop_reason="tool_use", content=[
                _blk(type="tool_use", id="t1", name="query_hotspots", input={"limit": 3})])
        return types.SimpleNamespace(stop_reason="end_turn", content=[_blk(type="text", text="Top zone is z0.")])


def _client():
    c = AIClient(settings)
    c._client = types.SimpleNamespace(messages=FakeMessages())
    return c


def test_loop_runs_tool_then_answers():
    c = _client()
    seen = {}
    def executor(name, inp):
        seen["name"] = name
        return {"top": [{"gh7": "z0", "impact": 99}]}, [{"type": "focusZone", "gh7": "z0"}]
    reply, actions = c.run("sys", [{"role": "user", "content": "top zone?"}], tools=[], executor=executor)
    assert seen["name"] == "query_hotspots"
    assert reply == "Top zone is z0."
    assert actions == [{"type": "focusZone", "gh7": "z0"}]


def test_tool_result_is_capped_and_clean():
    c = _client()
    huge = "x" * 9000
    def executor(name, inp):
        return {"blob": huge, "geometry": [[1, 2]] * 500}, []
    c.run("sys", [{"role": "user", "content": "go"}], tools=[], executor=executor)
    # the 2nd create() call carries the tool_result; it must be capped
    second = c._client.messages.calls[1]
    tool_result = second["messages"][-1]["content"][0]["content"]
    assert len(tool_result) <= settings.AI_MODEL_SUMMARY_MAX_CHARS + 40


def test_tool_error_does_not_crash():
    c = _client()
    def executor(name, inp):
        raise RuntimeError("boom")
    reply, actions = c.run("sys", [{"role": "user", "content": "go"}], tools=[], executor=executor)
    assert reply == "Top zone is z0." and actions == []   # error captured, loop still completes


def test_available_false_when_disabled():
    import copy
    s = copy.copy(settings)
    s.AI_ENABLED = False
    assert AIClient(s).available() is False


def test_available_false_when_probe_fails():
    # client present but count_tokens raises (dead proxy / missing key) -> offline, no crash
    c = _client()                      # FakeMessages has no count_tokens
    assert c.available() is False
