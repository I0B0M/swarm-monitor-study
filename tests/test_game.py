"""Run with: python -m unittest discover -s tests"""

import unittest

from swarm import scripted
from swarm.backends import ScriptedBackend
from swarm.cells import CELLS, games
from swarm.game import run_game
from swarm.seeds import DEV_SEEDS, TEST_SEEDS, load, make_layout
from swarm.world import MAX_ACTIONS_PER_TURN, World


def play(name, layout=None):
    layout = layout or load("dev")[1]
    game = scripted.build(layout)[name]
    cfg = {"run_id": f"t-{name}", **game["cfg"]}
    return run_game(cfg, layout, ScriptedBackend(game["scripts"])), game["expect"]


class RefereeOnScriptedGames(unittest.TestCase):
    def test_every_scripted_game_gets_the_known_answer_on_every_dev_seed(self):
        for seed, layout in load("dev").items():
            for name in ("clean", "honest_bad_order", "plain_sabotage", "relabel_sabotage"):
                with self.subTest(seed=seed, game=name):
                    record, expect = play(name, layout)
                    self.assertEqual(record["referee"]["violation"], expect["violation"])
                    self.assertEqual(record["referee"]["task_complete"], expect["task_complete"])

    def test_referee_ignores_a_lying_chat(self):
        record, _ = play("relabel_sabotage")
        said = " ".join(e["text"] for e in record["events"] if e["type"] == "message")
        self.assertIn("exactly where the manifest says", said)
        self.assertTrue(record["referee"]["violation"])

    def test_referee_ignores_a_chat_that_claims_sabotage(self):
        record, _ = play("honest_bad_order")
        self.assertFalse(record["referee"]["violation"])

    def test_relabel_is_recorded_and_label_at_time_is_logged(self):
        record, _ = play("relabel_sabotage")
        self.assertTrue(record["leak"]["relabelled_restricted"])
        ship = [e for e in record["events"] if e.get("name") == "move_crate" and e["args"]["bay"] == "D"
                and record["final_state"][e["args"]["crate"]]["restricted"]]
        self.assertEqual(ship[0]["label_at_time"], "BAY-D")

    def test_plain_sabotage_ships_with_the_restricted_label(self):
        record, _ = play("plain_sabotage")
        ship = [e for e in record["events"] if e.get("name") == "move_crate" and e["args"]["bay"] == "D"
                and record["final_state"][e["args"]["crate"]]["restricted"]]
        self.assertEqual(ship[0]["label_at_time"], "RESTRICTED")


class WorldRules(unittest.TestCase):
    def setUp(self):
        self.world = World(load("dev")[1], keyholder="B", locker_text="secret")

    def test_only_the_keyholder_can_open_the_locker(self):
        self.assertIn("locked", self.world.apply_turn(1, "A", {"actions": [{"tool": "open_locker"}]})[0])
        self.assertIn("secret", self.world.apply_turn(1, "B", {"actions": [{"tool": "open_locker"}]})[0])

    def test_action_limit_per_turn_is_enforced(self):
        acts = [{"tool": "set_label", "crate": "C-01", "text": f"X{i}"} for i in range(MAX_ACTIONS_PER_TURN + 1)]
        fb = self.world.apply_turn(1, "A", {"actions": acts})
        self.assertIn("Ignored", fb[-1])
        self.assertEqual(self.world.crates["C-01"]["label"], f"X{MAX_ACTIONS_PER_TURN - 1}")

    def test_bad_crate_and_bad_bay_are_rejected(self):
        fb = self.world.apply_turn(1, "A", {"actions": [{"tool": "move_crate", "crate": "C-99", "bay": "A"},
                                                        {"tool": "move_crate", "crate": "C-01", "bay": "Z"}]})
        self.assertTrue(all(line.startswith("Error") for line in fb))


class Seeds(unittest.TestCase):
    def test_committed_seeds_match_the_generator(self):
        for split, seeds in (("dev", DEV_SEEDS), ("test", TEST_SEEDS)):
            committed = load(split)
            self.assertEqual(sorted(committed), seeds)
            for s in seeds:
                self.assertEqual(committed[s], make_layout(s))

    def test_layout_properties(self):
        for s in DEV_SEEDS + TEST_SEEDS:
            m = make_layout(s)["manifest"]
            held = [c for c, e in m.items() if e["hold"]]
            self.assertIn(len(held), (2, 3))
            self.assertGreaterEqual(sum(1 for e in m.values() if not e["hold"] and e["bay"] == "D"), 2)


class Cells(unittest.TestCase):
    def test_test_split_counts_and_roles(self):
        for name, cell in CELLS.items():
            gs = games("test", [name])
            self.assertEqual(len(gs), cell["n_test"])
            self.assertEqual(len({cfg["run_id"] for cfg, _ in gs}), len(gs))
            for cfg, _ in gs:
                if name == "S3a-imp":
                    self.assertEqual(cfg["keyholder"], cfg["imposter"])
                if name == "S3b-imp":
                    self.assertNotEqual(cfg["keyholder"], cfg["imposter"])
                if cell["crew"] == "honest":
                    self.assertIsNone(cfg["imposter"])


if __name__ == "__main__":
    unittest.main()
