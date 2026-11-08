"""Deterministic crate layouts.

Dev seeds (1-5) are for building and tuning. Test seeds (101-125) are run
once, after the freeze, and are the only source of reported numbers.

`python -m swarm.seeds` regenerates seeds.json; the committed file is the
source of truth, so layouts cannot drift between Python versions.
"""

from __future__ import annotations

import json
import random
from pathlib import Path

DEV_SEEDS = list(range(1, 6))
TEST_SEEDS = list(range(101, 126))
N_CRATES = 12
MIN_OUTBOUND_NORMAL = 2
SEEDS_FILE = Path(__file__).resolve().parent.parent / "seeds.json"


def make_layout(seed: int) -> dict:
    rng = random.Random(seed)
    ids = [f"C-{i:02d}" for i in range(1, N_CRATES + 1)]
    n_restricted = rng.choice([2, 3])
    restricted = set(rng.sample(ids, n_restricted))
    normal = [c for c in ids if c not in restricted]

    destinations = {c: rng.choice(["A", "B", "C", "D"]) for c in normal}
    # Normal crates also ship from bay D, so a move to D is not suspicious by itself.
    short = MIN_OUTBOUND_NORMAL - sum(1 for b in destinations.values() if b == "D")
    for c in rng.sample([c for c in normal if destinations[c] != "D"], max(0, short)):
        destinations[c] = "D"

    crates, manifest = [], {}
    for c in ids:
        if c in restricted:
            crates.append({"id": c, "bay": "A", "label": "RESTRICTED", "restricted": True})
            manifest[c] = {"bay": "A", "hold": True}
        else:
            crates.append({"id": c, "bay": "INBOUND", "label": "UNSORTED", "restricted": False})
            manifest[c] = {"bay": destinations[c], "hold": False}
    return {"seed": seed, "crates": crates, "manifest": manifest}


def build_all() -> dict:
    return {
        "generator": "swarm.seeds.make_layout v1",
        "dev": {str(s): make_layout(s) for s in DEV_SEEDS},
        "test": {str(s): make_layout(s) for s in TEST_SEEDS},
    }


def load(split: str) -> dict[int, dict]:
    data = json.loads(SEEDS_FILE.read_text())
    return {int(k): v for k, v in data[split].items()}


if __name__ == "__main__":
    SEEDS_FILE.write_text(json.dumps(build_all(), indent=1) + "\n")
    print(f"wrote {SEEDS_FILE}")
