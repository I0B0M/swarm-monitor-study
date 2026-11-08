"""Table 2 of the report, as Markdown, straight from replays/numbers.json (so no number is retyped by hand).

  python tools/make_table2.py [--numbers replays/numbers.json]
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ROWS = [  # (monitor, backend, monitor label, model label)
    ("checklist", "claude:sonnet", "checklist (frozen)", "Sonnet 5.5"),
    ("judgement", "claude:sonnet", "judgement only", "Sonnet 5.5"),
    ("judgement_exit", "claude:sonnet", "judgement, exit rule only *", "Sonnet 5.5"),
    ("outcome", "claude:sonnet", "outcome check", "Sonnet 5.5"),
    ("checklist", "local:agent", "checklist", "gpt-oss-20b"),
    ("judgement", "local:agent", "judgement only", "gpt-oss-20b"),
    ("judgement_exit", "local:agent", "judgement, exit rule only *", "gpt-oss-20b"),
    ("outcome", "local:agent", "outcome check", "gpt-oss-20b"),
    ("checklist", "local:coder", "checklist", "Qwen3.8-27B"),
    ("judgement", "local:coder", "judgement only", "Qwen3.8-27B"),
    ("outcome", "local:coder", "outcome check", "Qwen3.8-27B"),
    ("checklist", "local:chores", "checklist", "Qwen3.5-9B"),
    ("judgement", "local:chores", "judgement only", "Qwen3.5-9B"),
    ("outcome", "local:chores", "outcome check", "Qwen3.5-9B"),
]


def pct(x: float) -> str:
    return f"{100 * x:.1f}%"


def kn(v) -> str:
    return "not run" if not v or not v[1] else f"{v[0]}/{v[1]}"


def table(numbers: dict) -> str:
    out = ["| Monitor | Model | Honest false alarms | Naive undetected | Informed undetected | Added evasion (informed minus naive; Newcombe 95%) | After a store opening |",
           "|---|---|---|---|---|---|---|"]
    for mon, be, ml, model in ROWS:
        d = numbers.get(f"attack:{mon}@{be}")
        if not d or not d["informed_undetected"][1]:
            continue
        lo, hi = d["gap_newcombe"]
        out.append(f"| {ml} | {model} | {kn(d['honest_false_alarms'])} | {kn(d['naive_undetected'])} | {kn(d['informed_undetected'])} | "
                   f"{pct(d['gap'])} ({pct(lo)} to {pct(hi)}) | {kn(d['informed_opened_undetected'])} |")
    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--numbers", default="replays/numbers.json")
    a = ap.parse_args()
    print(table(json.loads(Path(a.numbers).read_text())))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
