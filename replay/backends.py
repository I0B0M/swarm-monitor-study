"""Model backends for replayed monitors and for exploratory games.

- claude: the repo's own ClaudeCLIBackend (`claude -p` on the subscription, no API key).
- local: any OpenAI-compatible chat server with JSON-schema output, such as a llama.cpp router on
  127.0.0.1:8080. Open-weight models make the extra monitors free to run and rerun offline.
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request

LOCAL_URL = os.environ.get("REPLAY_LOCAL_URL", "http://127.0.0.1:8080/v1/chat/completions")


class LocalOpenAIBackend:
    """Same call()/act() shape as swarm.backends.ClaudeCLIBackend."""

    def __init__(self, model: str, schema: dict, temperature: float = 0.0, seed: int | None = 7,
                 retries: int = 2, timeout_s: int = 600, max_tokens: int = 2048, url: str = LOCAL_URL):
        self.model, self.schema, self.temperature, self.seed = model, schema, temperature, seed
        self.retries, self.timeout_s, self.max_tokens, self.url = retries, timeout_s, max_tokens, url

    def _post(self, body: dict) -> dict:
        req = urllib.request.Request(self.url, data=json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=self.timeout_s) as resp:
            return json.loads(resp.read())

    def call(self, system: str, prompt: str):
        meta: dict = {"backend": "local-openai", "model_alias": self.model, "attempts": 0}
        body = {
            "model": self.model,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "response_format": {"type": "json_schema",
                                "json_schema": {"name": "reply", "schema": self.schema, "strict": True}},
        }
        if self.seed is not None:
            body["seed"] = self.seed
        for attempt in range(1, self.retries + 2):
            meta["attempts"] = attempt
            t0 = time.time()
            try:
                data = self._post(body)
            except (urllib.error.URLError, TimeoutError, ConnectionError) as exc:
                meta["error"] = f"http: {exc}"[:300]
                time.sleep(3 * attempt)
                continue
            meta["duration_ms"] = int((time.time() - t0) * 1000)
            choice = (data.get("choices") or [{}])[0]
            text = (choice.get("message") or {}).get("content") or ""
            usage = data.get("usage") or {}
            meta.update({"models": [data.get("model") or self.model], "finish_reason": choice.get("finish_reason"),
                         "prompt_tokens": usage.get("prompt_tokens"),
                         "completion_tokens": usage.get("completion_tokens"), "cost_usd_equiv": 0.0})
            try:
                out = json.loads(text)
            except json.JSONDecodeError:
                meta["error"] = f"unparseable ({choice.get('finish_reason')}): {text[:160]}"
                continue
            if not isinstance(out, dict):
                meta["error"] = "reply is not an object"
                continue
            meta.pop("error", None)
            return out, meta
        return None, meta

    def act(self, agent: str, system: str, observation: str):
        return self.call(system, observation)


def make_backend(spec: str, schema: dict, local_schema: dict, temperature: float = 0.0):
    """spec is 'claude:<alias>' or 'local:<model>'."""
    kind, _, model = spec.partition(":")
    if kind == "claude":
        from swarm.backends import ClaudeCLIBackend
        return ClaudeCLIBackend(model=model or "sonnet", schema=schema)
    if kind == "local":
        return LocalOpenAIBackend(model=model or "agent", schema=local_schema, temperature=temperature)
    raise ValueError(f"unknown backend {spec!r}: use claude:<alias> or local:<model>")
