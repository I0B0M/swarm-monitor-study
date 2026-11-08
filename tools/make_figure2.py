"""Figure 2: missed attacks by scripted policy, per monitor (attack library, layouts 201 to 225).

  python tools/make_figure2.py --numbers replays/numbers.json --out report/figures/figure2

Writes figure2.svg (light), figure2-dark.svg and a PNG of each. One row per monitor prompt and model. Each mark is
one scripted policy over its 25 games: naive policies (tag left unchanged, hollow circle), informed policies (tag
changed to the exit's tag first, filled diamond) and store-opened policies (informed after a visible store opening,
hollow diamond). The policies are deterministic, so a policy, not a game, is the independent unit; the figure shows
no game-level intervals. Marks that share a value are drawn once with a count. Left panel: the monitor's own
verdict. Right panel: a score threshold that flags at most 5% of the monitor's honest runs. Colours are the
validated two-slot categorical palette; shape and fill carry the kind too, so nothing depends on colour alone.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tools.render import svg_to_png  # noqa: E402

MODELS = [("claude:sonnet", "Sonnet 5.5"), ("local:agent", "gpt-oss-20b")]
PROMPTS = [("checklist", "checklist"), ("checklist_judgement", "checklist, last rule asks for judgement *"),
           ("judgement", "judgement only"), ("judgement_exit", "judgement, exit rule only *"), ("outcome", "outcome check")]
KINDS = {  # policy -> kind
    "plain_first": "naive", "plain_last": "naive",
    "relabel_first": "informed", "relabel_last": "informed", "relabel_cover": "informed", "relabel_split": "informed",
    "opened_relabel_first": "opened", "opened_relabel_cover": "opened",
}
THEMES = {
    "light": {"bg": "#fcfcfb", "ink": "#0b0b0b", "ink2": "#52514e", "grid": "#e4e2dc", "naive": "#2a78d6", "informed": "#eb6834"},
    "dark": {"bg": "#1a1a19", "ink": "#f0efec", "ink2": "#c3c2b7", "grid": "#3a3936", "naive": "#3987e5", "informed": "#d95926"},
}


def rows_from(numbers: dict) -> list[dict]:
    rows = []
    for be, model in MODELS:
        for mon, label in PROMPTS:
            marks = {"verdict": [], "threshold": []}
            for po, kind in KINDS.items():
                v = numbers.get(f"policy:{mon}@{be}:{po}")
                if v and v[1]:
                    marks["verdict"].append((kind, v[0] / v[1]))
                t = numbers.get(f"policy_t:{mon}@{be}:{po}")
                if t and t[1]:
                    marks["threshold"].append((kind, t[0] / t[1]))
            if marks["verdict"]:
                frozen = " (frozen)" if (be, mon) == ("claude:sonnet", "checklist") else ""
                rows.append({"label": f"{model} · {label}{frozen}", "marks": marks})
    return rows


def esc(t: str) -> str:
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def mark(kind: str, cx: float, cy: float, c: dict) -> str:
    if kind == "naive":
        return f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="5" fill="{c["bg"]}" stroke="{c["naive"]}" stroke-width="2.5"/>'
    d = f"M {cx:.1f} {cy - 6.5:.1f} L {cx + 6.5:.1f} {cy:.1f} L {cx:.1f} {cy + 6.5:.1f} L {cx - 6.5:.1f} {cy:.1f} Z"
    if kind == "informed":
        return f'<path d="{d}" fill="{c["informed"]}" stroke="{c["bg"]}" stroke-width="1.5"/>'
    return f'<path d="{d}" fill="{c["bg"]}" stroke="{c["informed"]}" stroke-width="2.2"/>'


def svg(rows: list[dict], theme: str) -> str:
    c = THEMES[theme]
    label_w, panel_w, gap, top, row_h = 300, 310, 34, 106, 30
    width = label_w + 2 * panel_w + gap + 24
    height = top + row_h * len(rows) + 66
    x0 = [label_w, label_w + panel_w + gap]
    plot_w = panel_w - 24
    dy = {"naive": -7, "informed": 0, "opened": 7}

    def X(panel, p):
        return x0[panel] + 12 + p * plot_w

    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" font-family="Helvetica, Arial, sans-serif" role="img" '
           f'aria-label="Missed rate per scripted attack policy, by monitor, at the verdict and at a 5 percent false-alarm threshold">',
           f'<rect width="{width}" height="{height}" fill="{c["bg"]}"/>',
           f'<text x="12" y="24" font-size="15" font-weight="700" fill="{c["ink"]}">Missed attacks by scripted policy, per monitor</text>',
           f'<text x="12" y="44" font-size="11.5" fill="{c["ink2"]}">Each mark is one policy over its 25 games (a policy, not a game, is the independent unit); a number beside a mark counts the policies that share it.</text>',
           mark("naive", 18, 66, c), f'<text x="30" y="70" font-size="11.5" fill="{c["ink"]}">naive: tag left unchanged</text>',
           mark("informed", 214, 66, c), f'<text x="226" y="70" font-size="11.5" fill="{c["ink"]}">informed: tag changed to the exit\'s tag first</text>',
           mark("opened", 498, 66, c), f'<text x="510" y="70" font-size="11.5" fill="{c["ink"]}">store opened, then informed</text>']
    for panel, title in enumerate(["At the monitor's own verdict", "At a 5% false-alarm score threshold"]):
        out.append(f'<text x="{x0[panel] + 12}" y="{top - 10}" font-size="12" font-weight="600" fill="{c["ink"]}">{title}</text>')
        for p in (0, 0.5, 1):
            xx = X(panel, p)
            out.append(f'<line x1="{xx:.1f}" y1="{top}" x2="{xx:.1f}" y2="{top + row_h * len(rows)}" stroke="{c["grid"]}" stroke-width="1"/>')
            out.append(f'<text x="{xx:.1f}" y="{top + row_h * len(rows) + 16}" font-size="10.5" fill="{c["ink2"]}" text-anchor="middle">{int(p * 100)}%</text>')
    for i, r in enumerate(rows):
        y = top + row_h * i + row_h / 2
        out.append(f'<text x="{label_w - 10}" y="{y + 4:.1f}" font-size="11.5" fill="{c["ink"]}" text-anchor="end">{esc(r["label"])}</text>')
        for panel, key in enumerate(("verdict", "threshold")):
            groups = Counter((kind, round(p, 2)) for kind, p in r["marks"][key])
            xs = [X(panel, p) for (_, p) in groups]
            for (kind, p), n in sorted(groups.items()):
                cx, cy = X(panel, p), y + dy[kind]
                out.append(mark(kind, cx, cy, c))
                if n > 1:
                    crowded = any(cx < ox <= cx + 30 for ox in xs)  # another mark just to the right: label on the left
                    lx, anchor = (cx - 9, "end") if crowded else (cx + 9, "start")
                    out.append(f'<text x="{lx:.1f}" y="{cy + 3:.1f}" font-size="9.5" fill="{c["ink2"]}" text-anchor="{anchor}">×{n}</text>')
    out.append(f'<text x="12" y="{height - 26}" font-size="10.5" fill="{c["ink2"]}">* exploratory prompts added after the results (amendments 2 and 3). Game totals and honest false alarms are in Table 1;</text>')
    out.append(f'<text x="12" y="{height - 11}" font-size="10.5" fill="{c["ink2"]}">per-policy counts are in Table 3 (Appendix E) and replays/REPLAY_NUMBERS.md.</text>')
    out.append("</svg>")
    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--numbers", default="replays/numbers.json")
    ap.add_argument("--out", default="report/figures/figure2")
    a = ap.parse_args()
    rows = rows_from(json.loads(Path(a.numbers).read_text()))
    if not rows:
        print("no per-policy rows in", a.numbers)
        return 2
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    light, dark = out.with_suffix(".svg"), Path(str(out) + "-dark.svg")
    light.write_text(svg(rows, "light"))
    dark.write_text(svg(rows, "dark"))
    svg_to_png(light, out.with_suffix(".png"))
    svg_to_png(dark, Path(str(out) + "-dark.png"))
    print(f"{len(rows)} rows -> {out}.svg, {out}-dark.svg and their PNGs")
    return 0


if __name__ == "__main__":
    sys.exit(main())
