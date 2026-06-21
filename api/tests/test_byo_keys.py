"""Bring-your-own-key plumbing: per-request Mappls header + direct-Anthropic selection."""
from fastapi.testclient import TestClient
from api.main import create_app
from api.ai.client import AIClient
from api.config import settings


def test_ai_for_request_selects_byo_key():
    default = AIClient(settings)               # proxy/env default
    # no header → returns the default instance
    assert AIClient.for_request(settings, {}, default) is default
    # header present → a distinct, direct-Anthropic client with the requested model
    c = AIClient.for_request(settings, {"x-anthropic-key": "sk-ant-xyz", "x-ai-model": "claude-opus-4-8"}, default)
    assert c is not default
    assert c.model == "claude-opus-4-8"
    assert c.api_key == "sk-ant-xyz"
    assert c.base_url is None               # direct Anthropic, not the proxy
    # same key+model is cached (no rebuild)
    c2 = AIClient.for_request(settings, {"x-anthropic-key": "sk-ant-xyz", "x-ai-model": "claude-opus-4-8"}, default)
    assert c2 is c


def test_endpoints_accept_key_headers(mini_scores):
    c = TestClient(create_app(scores_parquet=mini_scores))
    # headers must be accepted without error on the mappls-using endpoints
    h = {"X-Mappls-Key": "DUMMYKEY"}
    assert c.get("/api/v1/health", headers=h).status_code == 200
    assert c.get("/api/v1/triage/patrol-plan?units=1&topk=4", headers=h).status_code == 200
    r = c.get("/api/v1/ai/health", headers={"X-Anthropic-Key": "sk-ant-bad"})
    assert r.status_code == 200 and r.json()["available"] in (True, False)
