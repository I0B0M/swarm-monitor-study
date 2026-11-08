"""Inline the example bundles into index.html between the EXAMPLES markers.

Run from anywhere: python3 tools/embed_examples.py
Re-run it whenever a bundle in examples/ changes. The page never fetches anything,
so the bundles must live inside the HTML file.
"""

from __future__ import annotations

import html
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
PAGE = HERE / "index.html"
EXAMPLES = HERE / "examples"

# Picker order and judge-facing titles; the first one opens by default. Unknown bundles are appended with their file name.
# Build a bundle from a run file and replays/scores.jsonl with make_bundle.py.
TITLES = {
    "attack-relabel_cover-seed205": "Tag laundering with a cover message (attack library, layout 205)",
    "attack-opened_relabel_first-seed205": "Store opened, then tag laundering (attack library, layout 205)",
    "attack-plain_first-seed205": "Naive attack: tag left unchanged (attack library, layout 205)",
    "attack-honest_clean-seed205": "Honest game (attack library, layout 205)",
    "scripted-relabel_sabotage": "Known-answer game: tag laundering (scripted, development layout)",
    "dev-v3-S2-imp-seed1-r1": "The saboteur refuses and tells its teammate (development game)",
}


def main() -> None:
    files = {p.stem: p for p in sorted(EXAMPLES.glob("*.json"))}
    order = [n for n in TITLES if n in files] + [n for n in files if n not in TITLES]
    blocks = []
    for name in order:
        data = json.loads(files[name].read_text(encoding="utf-8"))
        text = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
        # Keep the JSON inert inside a script element.
        text = text.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
        title = html.escape(TITLES.get(name, name), quote=True)
        blocks.append(
            f'<script type="application/json" class="example" data-name="{html.escape(name, quote=True)}" '
            f'data-title="{title}">{text}</script>'
        )
    page = PAGE.read_text(encoding="utf-8")
    new = re.sub(
        r"<!-- EXAMPLES:BEGIN -->.*?<!-- EXAMPLES:END -->",
        lambda _m: "<!-- EXAMPLES:BEGIN -->\n" + "\n".join(blocks) + "\n<!-- EXAMPLES:END -->",
        page,
        flags=re.S,
    )
    PAGE.write_text(new, encoding="utf-8")
    print(f"embedded {len(blocks)} examples into {PAGE.name} ({len(new.encode('utf-8'))} bytes)")


if __name__ == "__main__":
    main()
