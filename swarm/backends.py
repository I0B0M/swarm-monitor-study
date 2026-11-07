"""Where an agent's decision comes from.

ScriptedBackend: pre-written moves, no model calls. Used for tests.
ClaudeCLIBackend: one `claude -p` call per turn, on the logged-in Claude
subscription. No API key is needed. The default Claude Code system prompt is
replaced, all tools and settings are switched off, and the reply must match
TURN_SCHEMA.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import tempfile
import time

from .prompts import TURN_SCHEMA

FINISH = {"actions": [{"tool": "finish"}]}


def usage_limit(error: str) -> bool:
    text = error.lower()
    return any(phrase in text for phrase in (
        "hit your limit", "usage limit", "rate limit", "rate_limit", "quota exceeded",
    ))


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
                                      capture_output=True, text=True, timeout=self.timeout_s,
                                      env={k: v for k, v in os.environ.items()
                                           if k not in {"ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN"}})
                data = json.loads(proc.stdout)
            except subprocess.TimeoutExpired:
                meta["error"] = "timeout"
                continue
            except json.JSONDecodeError:
                meta["error"] = f"unparseable output (exit {proc.returncode}): {proc.stderr[-300:]}"
                if usage_limit(meta["error"]):
                    break
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
                if usage_limit(meta["error"]):
                    break
                time.sleep(2 * attempt)
                continue
            meta.pop("error", None)
            return out, meta
        return None, meta

    def act(self, agent: str, system: str, observation: str):
        return self.call(system, observation)


CODEX_MODEL = "gpt-6.1-sol"


def _strict_schema(schema: dict) -> dict:
    """Make optional fields nullable for Codex's strict structured output."""
    if schema["type"] == "object":
        return {**schema, "required": list(schema["properties"]), "properties": {
            key: _strict_schema(value) if key in schema["required"]
            else {"anyOf": [_strict_schema(value), {"type": "null"}]}
            for key, value in schema["properties"].items()
        }}
    if schema["type"] == "array":
        return {**schema, "items": _strict_schema(schema["items"])}
    return schema


def _turn_value(value, schema: dict):
    """Normalize nullable optional fields and enforce TURN_SCHEMA."""
    kind = schema["type"]
    if kind == "object" and isinstance(value, dict):
        props = schema["properties"]
        required = set(schema["required"])
        if not required <= value.keys() <= props.keys():
            raise ValueError("unexpected or missing fields")
        return {key: _turn_value(val, props[key]) for key, val in value.items()
                if val is not None or key in required}
    if kind == "array" and isinstance(value, list) and len(value) <= schema["maxItems"]:
        return [_turn_value(item, schema["items"]) for item in value]
    if kind == "string" and isinstance(value, str):
        if len(value) <= schema.get("maxLength", len(value)) and value in schema.get("enum", [value]):
            return value
    raise ValueError(f"invalid {kind} in turn")


class CodexCLIBackend:
    """One ephemeral, structured turn through the local ChatGPT login."""

    def __init__(self, model: str = CODEX_MODEL, retries: int = 2, timeout_s: int = 180):
        self.model = model
        self.retries = retries
        self.timeout_s = timeout_s

    def call(self, system: str, prompt: str):
        meta = {"backend": "codex-cli", "model_alias": self.model, "models": [self.model]}
        env = {key: value for key, value in os.environ.items()
               if key not in {"OPENAI_API_KEY", "CODEX_API_KEY"}}
        with tempfile.TemporaryDirectory(prefix="swarm-codex-") as tmp:
            root = Path(tmp)
            cwd = root / "empty"
            cwd.mkdir()
            schema_path = root / "turn.json"
            schema_path.write_text(json.dumps(_strict_schema(TURN_SCHEMA)))
            cmd = [
                "codex", "-a", "never", "exec", "--skip-git-repo-check", "--ephemeral",
                "--ignore-user-config", "--ignore-rules", "--sandbox", "read-only",
                "--disable", "shell_tool", "--disable", "shell_snapshot",
                "--disable", "multi_agent", "--enable", "skip_host_skill_discovery",
                "-c", 'web_search="disabled"', "-c", 'forced_login_method="chatgpt"',
                "-c", 'model_reasoning_effort="low"',
                "-c", "developer_instructions=" + json.dumps(system, ensure_ascii=False),
                "--model", self.model, "--json", "--output-schema", str(schema_path), "-",
            ]
            for attempt in range(1, self.retries + 2):
                meta["attempts"] = attempt
                started = time.monotonic()
                try:
                    proc = subprocess.run(cmd, input=prompt, cwd=cwd, env=env,
                                          capture_output=True, text=True, timeout=self.timeout_s)
                    events = [json.loads(line) for line in proc.stdout.splitlines() if line.strip()]
                    if proc.returncode:
                        error = next((e.get("message") for e in reversed(events)
                                      if e.get("type") == "error"), None)
                        raise ValueError(error or proc.stderr[-300:] or f"exit {proc.returncode}")
                    messages = [e["item"]["text"] for e in events if e.get("type") == "item.completed"
                                and e.get("item", {}).get("type") == "agent_message"]
                    if not messages:
                        raise ValueError("no structured turn")
                    turn = _turn_value(json.loads(messages[-1]), TURN_SCHEMA)
                except (ValueError, OSError, subprocess.TimeoutExpired) as exc:
                    meta["error"] = str(exc)[:300]
                    if usage_limit(meta["error"]):
                        break
                    if attempt <= self.retries:
                        time.sleep(2 * attempt)
                    continue
                meta["duration_ms"] = round((time.monotonic() - started) * 1000)
                meta.pop("error", None)
                return turn, meta
        return None, meta

    def act(self, agent: str, system: str, observation: str):
        return self.call(system, observation)
