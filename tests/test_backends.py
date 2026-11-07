import json
import os
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch

from swarm.backends import CodexCLIBackend


class CodexTurns(unittest.TestCase):
    def test_retries_invalid_turn_and_records_pinned_model(self):
        def reply(turn):
            event = {"type": "item.completed",
                     "item": {"type": "agent_message", "text": json.dumps(turn)}}
            return subprocess.CompletedProcess([], 0, json.dumps(event), "")

        good = {"actions": [{"tool": "move_crate", "crate": "C-02", "bay": "D"}]}
        responses = iter([reply({"actions": [{"tool": "teleport"}]}), reply(good)])

        def fake_run(argv, **kwargs):
            self.assertEqual(list(Path(kwargs["cwd"]).iterdir()), [])
            self.assertNotIn("OPENAI_API_KEY", kwargs["env"])
            self.assertIn("state of play", kwargs["input"])
            self.assertTrue(any("hidden role" in arg for arg in argv))
            return next(responses)

        with patch.dict(os.environ, {"OPENAI_API_KEY": "unused"}), \
             patch("swarm.backends.subprocess.run", side_effect=fake_run) as process, \
             patch("swarm.backends.time.sleep"):
            turn, meta = CodexCLIBackend().act("A", "hidden role", "state of play")

        self.assertEqual(turn, good)
        self.assertEqual(process.call_count, 2)
        self.assertEqual(meta["models"], ["gpt-6.1-sol"])
        self.assertEqual(meta["attempts"], 2)
        self.assertNotIn("error", meta)


class SubscriptionQuota(unittest.TestCase):
    def test_weekly_limit_from_claude(self):
        from swarm.backends import usage_limit

        self.assertTrue(usage_limit("You've hit your weekly limit · resets 6am (America/New_York)"))
