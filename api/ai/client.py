"""Thin Claude wrapper over the local claude-openai proxy (Anthropic-native, port 4001).

Two entry points:
- `complete(system, user)`  — single model call, returns text (brief / explain / insights).
- `run(system, messages, tools, executor)` — the agentic tool loop (command bar only).

Context discipline (see spec §5.5): tool RESULTS fed back to the model are the compact
`model_summary` strings ONLY — never geometry or large arrays. The full artifacts travel to the
browser via `ui_actions`, which this loop accumulates separately and never sends to the model.
"""
import json
import time


class AIClient:
    def __init__(self, settings):
        self.s = settings
        self._client = None
        self._avail = None          # cached availability
        self._avail_ts = 0.0
        if settings.AI_ENABLED:
            try:
                import anthropic     # optional dependency — absent => AI simply stays offline
                self._client = anthropic.Anthropic(
                    api_key=settings.AI_API_KEY, base_url=settings.AI_BASE_URL,
                    timeout=settings.AI_TIMEOUT, max_retries=1)
            except Exception:
                self._client = None

    # ---- availability: cheap key-validating probe (count_tokens), cached 30s ----
    # Returns True only when AI is enabled AND the proxy is reachable AND the key is valid.
    # Distinguishes all the "no key" cases: missing SDK / disabled / dead proxy / bad key.
    def available(self):
        if not (self.s.AI_ENABLED and self._client):
            return False
        now = time.monotonic()
        if self._avail is not None and (now - self._avail_ts) < 30:
            return self._avail
        try:
            self._client.messages.count_tokens(
                model=self.s.AI_MODEL, messages=[{"role": "user", "content": "ping"}])
            ok = True
        except Exception:
            ok = False
        self._avail, self._avail_ts = ok, now
        return ok

    def _invalidate(self):
        self._avail = None

    def _cap(self, text):
        n = self.s.AI_MODEL_SUMMARY_MAX_CHARS
        return text if len(text) <= n else text[:n] + " …(truncated)"

    def complete(self, system, user, max_tokens=900):
        r = self._client.messages.create(
            model=self.s.AI_MODEL, max_tokens=max_tokens, system=system,
            messages=[{"role": "user", "content": user}])
        return "".join(b.text for b in r.content if b.type == "text").strip()

    def run(self, system, messages, tools, executor, max_tokens=1024):
        """Agentic loop. `executor(name, input) -> (summary_str, ui_actions_list)`.
        Returns (reply_text, ui_actions). Tool plumbing stays inside this call."""
        msgs = list(messages)
        ui_actions = []
        for _ in range(self.s.AI_MAX_TOOL_ITERS):
            r = self._client.messages.create(
                model=self.s.AI_MODEL, max_tokens=max_tokens, system=system,
                tools=tools, messages=msgs)
            if r.stop_reason != "tool_use":
                text = "".join(b.text for b in r.content if b.type == "text").strip()
                return text, ui_actions
            # record the assistant turn (tool_use blocks) then answer each tool
            msgs.append({"role": "assistant", "content": [b.model_dump() for b in r.content]})
            results = []
            for b in r.content:
                if b.type != "tool_use":
                    continue
                try:
                    summary, actions = executor(b.name, b.input or {})
                except Exception as e:  # never 500 the request on a tool error
                    summary, actions = {"error": str(e)[:200]}, []
                ui_actions.extend(actions or [])
                results.append({"type": "tool_result", "tool_use_id": b.id,
                                "content": self._cap(json.dumps(summary, default=str))})
            msgs.append({"role": "user", "content": results})
        # iteration cap hit — make one final no-tools call to summarise
        try:
            r = self._client.messages.create(
                model=self.s.AI_MODEL, max_tokens=max_tokens, system=system, messages=msgs)
            text = "".join(b.text for b in r.content if b.type == "text").strip()
        except Exception:
            text = "I gathered the data but couldn't finish composing a reply — please retry."
        return text, ui_actions
