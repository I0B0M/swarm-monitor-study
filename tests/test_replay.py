"""Replay layer checks. Run: python -m unittest discover -s tests"""

import json
import tempfile
import unittest
from pathlib import Path

import attack_library
from replay import monitors
from replay.runs import derive_cell, load_runs
from swarm.guard import GUARD_SYSTEM, render_log
from swarm.seeds import make_layout


class FrozenMonitorIsUntouched(unittest.TestCase):
    def test_checklist_is_the_frozen_guard_prompt(self):
        system, render = monitors.MONITORS["checklist"]
        self.assertIs(system, GUARD_SYSTEM)
        self.assertIs(render, render_log)

    def test_outcome_extends_the_checklist_without_changing_it(self):
        system, _ = monitors.MONITORS["outcome"]
        self.assertTrue(system.startswith(GUARD_SYSTEM))

    def test_judgement_has_no_checklist(self):
        system, _ = monitors.MONITORS["judgement"]
        self.assertNotIn("Kestrel", system)
        self.assertNotIn("moment it is moved", system)

    def test_local_schema_only_bounds_the_array(self):
        a, b = dict(monitors.SCHEMA["properties"]), dict(monitors.LOCAL_SCHEMA["properties"])
        self.assertEqual(set(a), set(b))
        self.assertEqual(b["rule_hits"]["maxItems"], 2)


class AttackLibrary(unittest.TestCase):
    def test_refuses_dev_and_test_seeds(self):
        with tempfile.TemporaryDirectory() as d:
            for seed in (1, 5, 101, 125):
                with self.assertRaises(SystemExit):
                    attack_library.run([seed], d)

    def test_every_policy_has_the_expected_ground_truth(self):
        with tempfile.TemporaryDirectory() as d:
            n = attack_library.run([201, 202], d)
            self.assertEqual(n, 16)
            for path, rec in load_runs([d]):
                informed = rec["attack_kind"] == "informed"
                self.assertEqual(rec["referee"]["violation"], rec["attack_kind"] != "honest", path)
                self.assertEqual(bool(rec["referee"]["relabelled_restricted"]), informed, path)
                self.assertTrue(rec["referee"]["task_complete"], path)

    def test_outcome_view_includes_the_end_state(self):
        with tempfile.TemporaryDirectory() as d:
            attack_library.run([203], d)
            rec = json.loads(next(Path(d).glob("attack-relabel_first-*.json")).read_text())
            text = monitors.render_outcome(rec)
            self.assertIn("Final crate state:", text)
            self.assertIn("HOLD in bay", text)

    def test_cell_is_derived_for_old_files(self):
        self.assertEqual(derive_cell({"setup": "S2", "crew": "imposter"}), "S2-imp")
        self.assertEqual(derive_cell({"cell": "S3b-imp"}), "S3b-imp")
        self.assertEqual(derive_cell({"attack_policy": "plain_first"}), "attack-plain_first")


class Layouts(unittest.TestCase):
    def test_fresh_layouts_are_deterministic(self):
        self.assertEqual(make_layout(201), make_layout(201))


if __name__ == "__main__":
    unittest.main()
