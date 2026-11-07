"""Where an agent's decision comes from.

ScriptedBackend: pre-written moves, no model calls. Used for tests.
ClaudeCLIBackend: one `claude -p` call per turn, on the logged-in Claude
subscription. No API key is needed. The default Claude Code system prompt is
replaced, all tools and settings are switched off, and the reply must match
TURN_SCHEMA.
"""

from __future__ import annotations

import json
import subprocess
import tempfile
import time

from .prompts import TURN_SCHEMA

FINISH = {"actions": [{"tool": "finish"}]}


class ScriptedBackend:
    def __init__(self, scripts: dict[str, list[dict]]):
        self.scripts = {agent: list(turns) for agent, turns in scripts.items()}

    def act(self, agent: str, system: str, observation: str):
        turns = self.scripts.get(agent) or []
        decision = turns.pop(0) if turns else FINISH
        return decision, {"backend": "scripted"}


class ClaudeCLIBackend:
    def __init__(self, model: str = "haiku", retries: int = 2, timeout_s: int = 180,
                 schema: dict | None = None):
        self.model = model
        self.retries = retries
        self.timeout_s = timeout_s
        self.schema = json.dumps(schema or TURN_SCHEMA)
        # Run from an empty folder so no project files or settings are picked up.
        self.workdir = tempfile.mkdtemp(prefix="swarm-cli-")

    def _command(self, system: str, prompt: str) -> list[str]:
        return [
            "claude", "-p", prompt,
            "--model", self.model,
            "--system-prompt", system,
            "--tools", "",
            "--setting-sources", "",
            "--strict-mcp-config",
            "--no-session-persistence",
            "--json-schema", self.schema,
            "--output-format", "json",
        ]

    def call(self, system: str, prompt: str):
        """One structured call. Returns (structured_output or None, meta)."""
        meta: dict = {"backend": "claude-cli", "model_alias": self.model, "attempts": 0}
        for attempt in range(1, self.retries + 2):
            meta["attempts"] = attempt
            try:
                proc = subprocess.run(self._command(system, prompt), cwd=self.workdir,
                                      capture_output=True, text=True, timeout=self.timeout_s)
                data = json.loads(proc.stdout)
            except subprocess.TimeoutExpired:
                meta["error"] = "timeout"
                continue
            except json.JSONDecodeError:
                meta["error"] = f"unparseable output (exit {proc.returncode}): {proc.stderr[-300:]}"
                time.sleep(2 * attempt)
                continue
            meta.update({
                "models": sorted((data.get("modelUsage") or {}).keys()),
                "duration_ms": data.get("duration_ms"),
                "cost_usd_equiv": data.get("total_cost_usd"),
                "stop_reason": data.get("stop_reason"),
            })
            out = data.get("structured_output")
            if data.get("is_error") or not isinstance(out, dict):
                meta["error"] = str(data.get("result") or "no structured output")[:300]
                time.sleep(2 * attempt)
                continue
            meta.pop("error", None)
            return out, meta
        return None, meta

    def act(self, agent: str, system: str, observation: str):
        return self.call(system, observation)
