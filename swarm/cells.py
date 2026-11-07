"""The experiment's cells and the exact list of games each one runs."""

from __future__ import annotations

from .prompts import other
from .seeds import load

# n_test matches issue #4. n_dev is for smoke tests on dev seeds 1-5.
CELLS = {
    "S2-imp": {"setup": "S2", "crew": "imposter", "locker": "neutral", "key": "alternate", "n_test": 50, "n_dev": 5},
    "S3b-imp": {"setup": "S3b", "crew": "imposter", "locker": "rulebook", "key": "crewmate", "n_test": 60, "n_dev": 5},
    "S3a-imp": {"setup": "S3a", "crew": "imposter", "locker": "rulebook", "key": "imposter", "n_test": 50, "n_dev": 5},
    "S2-hon": {"setup": "S2", "crew": "honest", "locker": "neutral", "key": "alternate", "n_test": 50, "n_dev": 5},
    "S3-hon": {"setup": "S3", "crew": "honest", "locker": "rulebook", "key": "alternate", "n_test": 50, "n_dev": 5},
}
# Run order: if the usage limit stops a run, the most important cells are done.
ORDER = ["S2-imp", "S3b-imp", "S2-hon", "S3-hon", "S3a-imp"]


def games(split: str, cell_names: list[str], n: int | None = None) -> list[tuple[dict, dict]]:
    layouts = load(split)
    seeds = sorted(layouts)
    out = []
    for name in cell_names:
        cell = CELLS[name]
        for i in range(n or cell[f"n_{split}"]):
            seed = seeds[i % len(seeds)]
            rep = i // len(seeds) + 1
            imposter = None if cell["crew"] == "honest" else ("A" if i % 2 == 0 else "B")
            if cell["key"] == "imposter":
                keyholder = imposter
            elif cell["key"] == "crewmate":
                keyholder = other(imposter)
            else:
                keyholder = "A" if (i // 2) % 2 == 0 else "B"
            cfg = {"run_id": f"{split}-{name}-seed{seed}-r{rep}", "split": split, "cell": name,
                   "setup": cell["setup"], "crew": cell["crew"], "seed": seed, "rep": rep,
                   "imposter": imposter, "keyholder": keyholder, "locker": cell["locker"]}
            out.append((cfg, layouts[seed]))
    return out
