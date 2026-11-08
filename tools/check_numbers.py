"""Fail when the report quotes a data number that no numbers file contains (issue #12).

  python tools/check_numbers.py report/report.md --numbers NUMBERS.md replays/REPLAY_NUMBERS.md

Data numbers are counts written as k/n, percentages, and p-values. Each must appear verbatim in one of
the numbers files. Years, section numbers, layout ranges and model names are not data numbers and are
not checked. A line can opt out with the marker <!-- not data --> (for example a number quoted from
another paper, which is checked by its citation instead). Exit 0 when every number is found, 1 otherwise.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

PATTERNS = [
    re.compile(r"(?<![\w.])\d+/\d+(?![\w/])"),                    # k/n
    re.compile(r"(?<![\w.])-?\d+(?:\.\d+)?%"),                     # percentages
    re.compile(r"\bp\s*[=<>]\s*\d(?:\.\d+)?(?:e-?\d+)?\b"),       # p-values
]
OPT_OUT = "<!-- not data -->"


def data_numbers(line: str) -> list[str]:
    found = []
    for pat in PATTERNS:
        found += pat.findall(line)
    return found


def normalise(token: str) -> str:
    return re.sub(r"\s+", "", token)


def check(report: str, numbers_text: str) -> list[tuple[int, str]]:
    corpus = normalise(numbers_text)
    missing = []
    in_code = False
    for i, line in enumerate(report.splitlines(), 1):
        if line.strip().startswith("```"):
            in_code = not in_code
            continue
        if in_code or OPT_OUT in line:
            continue
        for tok in data_numbers(line):
            if normalise(tok) not in corpus:
                missing.append((i, tok))
    return missing


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("report")
    ap.add_argument("--numbers", nargs="+", required=True)
    a = ap.parse_args()
    numbers_text = "\n".join(Path(p).read_text() for p in a.numbers if Path(p).exists())
    missing = check(Path(a.report).read_text(), numbers_text)
    for line, tok in missing:
        print(f"{a.report}:{line}: {tok} is not in {', '.join(a.numbers)}")
    print(f"{len(missing)} untraced numbers")
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
