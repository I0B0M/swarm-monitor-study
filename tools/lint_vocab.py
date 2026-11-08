"""Keep game words, the word "swarm" and dashes out of judge-facing text (issue #12).

  python tools/lint_vocab.py report/report.md README.md JUDGE_FAQ.md

Issue #6 asks for no game words in the PDF (agent, saboteur, monitor and violation instead); the team never
says "swarm" except in the repository's and the event's names; Bryan's rule bans em and en dashes. Text
inside backticks and fenced code blocks is skipped, because commands and file paths keep the code's names.
Exit 0 when clean, 1 otherwise.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

GAME_WORDS = ["crate", "crates", "crewmate", "crewmates", "imposter", "imposters", "guard", "guards",
              "locker", "lockers", "cargo", "bay d", "robot", "robots"]
ALLOWED_SWARM = ["swarm alignment hackathon", "swarm-monitor-study"]
DASHES = {"\u2014": "em dash", "\u2013": "en dash"}


def strip_code(line: str) -> str:
    return re.sub(r"`[^`]*`", "", line)


def lint(text: str) -> list[tuple[int, str]]:
    problems = []
    in_code = False
    for i, raw in enumerate(text.splitlines(), 1):
        if raw.strip().startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            continue
        line = strip_code(raw)
        low = line.lower()
        full = raw.lower()
        for ch, name in DASHES.items():
            if ch in line:
                problems.append((i, name))
        for w in GAME_WORDS:
            if re.search(rf"(?<![\w-]){re.escape(w)}(?![\w-])", low):
                problems.append((i, f"game word '{w}'"))
        masked = full  # "swarm" is visible in code spans too, so it is checked on the whole line
        for ok in ALLOWED_SWARM:
            masked = masked.replace(ok, "")
        masked = re.sub(r"https?://\S+", "", masked)
        if "swarm" in masked:
            problems.append((i, "the word 'swarm' outside the repository or event name"))
    return problems


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", nargs="+")
    a = ap.parse_args()
    total = 0
    for f in a.files:
        for line, msg in lint(Path(f).read_text()):
            print(f"{f}:{line}: {msg}")
            total += 1
    print(f"{total} problems")
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main())
