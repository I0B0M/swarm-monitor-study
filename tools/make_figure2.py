"""Figure 2: what knowing the checklist is worth, by monitor (attack library, layouts 201 to 225).

  python tools/make_figure2.py --numbers replays/numbers.json --out report/figures/figure2

Writes figure2.svg (light), figure2-dark.svg and a PNG of each. One row per monitor prompt and model; two marks per row:
the undetected rate on naive attacks (circle) and on rule-informed attacks (diamond), each with its exact
95% interval and k/n. Left panel: the monitor's own verdict. Right panel: a threshold set so that at most
5% of honest games are flagged. Colours are the validated two-slot categorical palette; shape and labels
carry identity too, so nothing depends on colour alone.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from replay import stats as S  # noqa: E402
from tools.render import svg_to_png  # noqa: E402

MODELS = [("claude:sonnet", "Sonnet 5.5"), ("local:agent", "gpt-oss-20b"), ("local:coder", "Qwen3.8-27B"),
          ("local:chores", "Qwen3.5-9B")]
PROMPTS = [("checklist", "checklist"), ("judgement", "judgement only"), ("outcome", "outcome check")]
THEMES = {
    "light": {"bg": "#fcfcfb", "ink": "#0b0b0b", "ink2": "#52514e", "grid": "#e4e2dc", "naive": "#2a78d6",
              "informed": "#eb6834"},
    "dark": {"bg": "#1a1a19", "ink": "#f0efec", "ink2": "#c3c2b7", "grid": "#3a3936", "naive": "#3987e5",
             "informed": "#d95926"},
}


def rows_from(numbers: dict) -> list[dict]:
    rows = []
    for be, model in MODELS:
        for mon, label in PROMPTS:
            d = numbers.get(f"attack:{mon}@{be}")
            if not d or not d.get("informed_undetected") or not d["informed_undetected"][1]:
                continue
            frozen = " (frozen)" if (be, mon) == ("claude:sonnet", "checklist") else ""
            rows.append({"label": f"{model} · {label}{frozen}", "d": d})
    return rows


def esc(t: str) -> str:
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def svg(rows: list[dict], theme: str) -> str:
    c = THEMES[theme]
    label_w, panel_w, gap, top, row_h = 230, 250, 36, 92, 30
    width = label_w + 2 * panel_w + gap + 24
    height = top + row_h * len(rows) + 64
    x0 = [label_w, label_w + panel_w + gap]
    plot_w = panel_w - 20

    def X(panel, p):
        return x0[panel] + 10 + p * plot_w

    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" font-family="Helvetica, Arial, sans-serif" role="img" '
           f'aria-label="Undetected rate on naive and rule-informed attacks, by monitor, at the verdict and at a 5 percent false-alarm threshold">',
           f'<rect width="{width}" height="{height}" fill="{c["bg"]}"/>',
           f'<text x="12" y="24" font-size="15" font-weight="700" fill="{c["ink"]}">What knowing the checklist is worth, by monitor</text>',
           f'<text x="12" y="44" font-size="11.5" fill="{c["ink2"]}">Scripted attacks on 25 fresh layouts; undetected rate with exact 95% intervals; k/n printed for rule-informed attacks.</text>',
           # legend
           f'<circle cx="18" cy="64" r="5" fill="{c["bg"]}" stroke="{c["naive"]}" stroke-width="2.5"/>',
           f'<text x="28" y="68" font-size="11.5" fill="{c["ink"]}">naive attack: ships the record with its tag unchanged</text>',
           f'<path d="M 340 58 L 346 64 L 340 70 L 334 64 Z" fill="{c["informed"]}"/>',
           f'<text x="352" y="68" font-size="11.5" fill="{c["ink"]}">rule-informed attack: launders the tag first</text>']
    for panel, title in enumerate(["At the monitor's own verdict", "At a threshold with at most 5% false alarms"]):
        out.append(f'<text x="{x0[panel] + 10}" y="{top - 8}" font-size="12" font-weight="600" fill="{c["ink"]}">{title}</text>')
        for p in (0, 0.5, 1):
            xx = X(panel, p)
            out.append(f'<line x1="{xx:.1f}" y1="{top}" x2="{xx:.1f}" y2="{top + row_h * len(rows)}" stroke="{c["grid"]}" stroke-width="1"/>')
            out.append(f'<text x="{xx:.1f}" y="{top + row_h * len(rows) + 16}" font-size="10.5" fill="{c["ink2"]}" text-anchor="middle">{int(p * 100)}%</text>')
    for i, r in enumerate(rows):
        y = top + row_h * i + row_h / 2
        out.append(f'<text x="{label_w - 8}" y="{y + 4:.1f}" font-size="11.5" fill="{c["ink"]}" text-anchor="end">{esc(r["label"])}</text>')
        d = r["d"]
        for panel, (nk, ik) in enumerate([("naive_undetected", "informed_undetected"),
                                          ("naive_undetected_at_threshold", "informed_undetected_at_threshold")]):
            for kind, key, dy in (("naive", nk, -5), ("informed", ik, 5)):
                kn = d.get(key)
                if not kn or kn[0] is None or not kn[1]:
                    continue
                k, n = kn
                lo, hi = S.clopper_pearson(k, n)
                p = k / n
                yy = y + dy
                col = c[kind]
                out.append(f'<line x1="{X(panel, lo):.1f}" y1="{yy:.1f}" x2="{X(panel, hi):.1f}" y2="{yy:.1f}" stroke="{col}" stroke-width="2" stroke-linecap="round">'
                           f'<title>{esc(r["label"])}, {kind}: {k}/{n} undetected, 95% interval {100 * lo:.1f}% to {100 * hi:.1f}%</title></line>')
                cx = X(panel, p)
                if kind == "naive":
                    out.append(f'<circle cx="{cx:.1f}" cy="{yy:.1f}" r="4.5" fill="{c["bg"]}" stroke="{col}" stroke-width="2.5"/>')
                else:
                    out.append(f'<path d="M {cx:.1f} {yy - 6:.1f} L {cx + 6:.1f} {yy:.1f} L {cx:.1f} {yy + 6:.1f} L {cx - 6:.1f} {yy:.1f} Z" fill="{col}" stroke="{c["bg"]}" stroke-width="1.5"/>')
                    tx = X(panel, hi) + 6 if p < 0.82 else X(panel, lo) - 6
                    anchor = "start" if p < 0.82 else "end"
                    out.append(f'<text x="{tx:.1f}" y="{yy + 4:.1f}" font-size="10.5" fill="{c["ink2"]}" text-anchor="{anchor}">{k}/{n}</text>')
    out.append(f'<text x="12" y="{height - 12}" font-size="10.5" fill="{c["ink2"]}">Naive k/n and every honest false-alarm count are in Table 2. Source: replays/REPLAY_NUMBERS.md.</text>')
    out.append("</svg>")
    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--numbers", default="replays/numbers.json")
    ap.add_argument("--out", default="report/figures/figure2")
    a = ap.parse_args()
    rows = rows_from(json.loads(Path(a.numbers).read_text()))
    if not rows:
        print("no attack-library rows in", a.numbers)
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
