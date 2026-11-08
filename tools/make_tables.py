"""The report's attack-library tables, as Markdown, straight from replays/numbers.json (no number retyped).

  python tools/make_tables.py matrix      # Table 1: informed attacks missed, prompt by model, with the checklist's scores and reasons
  python tools/make_tables.py policies    # Table E1: by policy, for the checklist prompts
  python tools/make_tables.py library     # Table E2: every monitor, with false alarms, naive and store-opened attacks
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

MODELS = [("claude:sonnet", "Sonnet 5.5"), ("local:agent", "gpt-oss-20b"), ("local:coder", "Qwen3.8-27B"), ("local:chores", "Qwen3.5-9B")]
PROMPTS = [
    ("checklist", "checklist"),
    ("checklist_judgement", "checklist + judgement *"),
    ("judgement", "judgement only"),
    ("judgement_exit", "judgement, exit rule only *"),
    ("outcome", "outcome check"),
]
POLICIES = [
    ("plain_first", "naive: first actions"),
    ("plain_last", "naive: last actions"),
    ("relabel_first", "informed: first actions"),
    ("relabel_last", "informed: last actions"),
    ("relabel_cover", "informed: after a cover message"),
    ("relabel_split", "informed: two steps"),
    ("opened_relabel_first", "store opened, then informed: first actions"),
    ("opened_relabel_cover", "store opened, then informed: cover message"),
]
POLICY_COLUMNS = [
    ("checklist", "local:agent", "gpt-oss-20b checklist"),
    ("checklist", "local:coder", "Qwen3.8-27B checklist"),
    ("checklist", "local:chores", "Qwen3.5-9B checklist"),
    ("checklist", "claude:sonnet", "Sonnet 5.5 checklist"),
    ("checklist_judgement", "local:agent", "gpt-oss-20b checklist + judgement *"),
    ("checklist_judgement", "claude:sonnet", "Sonnet 5.5 checklist + judgement *"),
]


def kn(v) -> str:
    return "not run" if not v or not v[1] else f"{v[0]}/{v[1]}"


def library(numbers: dict) -> str:
    out = ["| Prompt | Model | Honest false alarms | Naive missed | Informed missed | Store-opened missed |",
           "|---|---|---|---|---|---|"]
    for be, model in MODELS:
        for mon, label in PROMPTS:
            d = numbers.get(f"attack:{mon}@{be}")
            if not d or not d["informed_undetected"][1]:
                continue
            out.append(f"| {label} | {model} | {kn(d['honest_false_alarms'])} | {kn(d['naive_undetected'])} | "
                       f"{kn(d['informed_undetected'])} | {kn(d['informed_opened_undetected'])} |")
    return "\n".join(out)


def matrix(numbers: dict) -> str:
    """Informed attacks missed: one row per prompt (plus the checklist's score threshold), one column per model."""
    models = [(be, m) for be, m in MODELS if f"attack:checklist@{be}" in numbers]
    def span(be: str) -> str:
        s = numbers.get(f"scores:checklist@{be}") or {}
        inf, hon = s.get("informed"), s.get("honest")
        return f"{inf[0]} to {inf[1]} ({hon[0]} to {hon[1]})" if inf and hon else "not run"

    # Dashes set relative column widths when pandoc wraps the table: a wide label column, equal model columns.
    out = ["| Prompt | " + " | ".join(m for _, m in models) + " |", "|" + "-" * 38 + "|" + ("-" * 18 + "|") * len(models)]

    def row(label: str, cells: list[str]) -> None:
        out.append(f"| {label} | " + " | ".join(cells) + " |")

    row("checklist, verdict", [kn(numbers[f"attack:checklist@{be}"]["informed_undetected"]) for be, _ in models])
    row("misses whose reason asks for review", [kn((numbers.get(f"review_ask:checklist@{be}") or {}).get("missed")) for be, _ in models])
    row("checklist scores, informed (honest)", [span(be) for be, _ in models])
    row("checklist score at 5% false alarms", [kn(numbers[f"attack:checklist@{be}"]["informed_undetected_at_threshold"]) for be, _ in models])
    for mon, label in PROMPTS:
        if mon != "checklist":
            row(label, [kn((numbers.get(f"attack:{mon}@{be}") or {}).get("informed_undetected")) for be, _ in models])
    return "\n".join(out)


def policies(numbers: dict) -> str:
    cols = [c for c in POLICY_COLUMNS if any(f"policy:{c[0]}@{c[1]}:" in k for k in numbers)]
    out = ["| Attack policy | " + " | ".join(c[2] for c in cols) + " |", "|---|" + "---|" * len(cols)]
    for po, label in POLICIES:
        cells = [kn(numbers.get(f"policy:{mon}@{be}:{po}")) for mon, be, _ in cols]
        out.append(f"| {label} | " + " | ".join(cells) + " |")
    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("table", choices=["matrix", "library", "policies"])
    ap.add_argument("--numbers", default="replays/numbers.json")
    a = ap.parse_args()
    numbers = json.loads(Path(a.numbers).read_text())
    print({"matrix": matrix, "library": library, "policies": policies}[a.table](numbers))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
