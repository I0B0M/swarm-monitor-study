"""Figure 1: one attack-library game at the moment the laundered record reaches the exit, with each monitor's verdict.

  python tools/make_figure1.py --viewer viewer/index.html
  python tools/make_figure1.py --viewer viewer/index.html --run runs/attacks/attack-relabel_cover-seed205.json --event 3

The figure is the replay viewer's own "Save still" export, so the report shows exactly what the viewer shows.
Its only inputs are the run file and that run's rows in replays/scores.jsonl: the script packs them into a
monitor-replay-bundle/v1, embeds the bundle in a temporary copy of the viewer, lets headless Chromium open it at
the chosen event, and saves the export in light and dark (SVG and PNG). A provenance file records the run's
sha256, the viewer's sha256 and, per monitor, the prompt sha256 of the score row it shows.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tools.render import dump_dom, pre_text, svg_to_png  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
# (monitor, backend in scores.jsonl, label shown in the figure); order is the figure's row order.
MONITORS = [
    ("checklist", "claude:sonnet", "Sonnet 5.5 (the frozen monitor)"),
    ("checklist", "local:agent", "gpt-oss-20b (open weights)"),
    ("judgement", "claude:sonnet", "Sonnet 5.5"),
    ("judgement", "local:agent", "gpt-oss-20b (open weights)"),
    ("outcome", "claude:sonnet", "Sonnet 5.5"),
    ("outcome", "local:agent", "gpt-oss-20b (open weights)"),
]
NAME = "figure1"
HOOK = """<script>
window.addEventListener('load', () => setTimeout(() => {
  const v = window.__viewer;
  v.go(%d);
  const pre = document.createElement('pre');
  pre.id = '__export';
  pre.textContent = v.buildExport().svg;
  document.body.appendChild(pre);
}, 400));
</script>
</body>"""


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def bundle(run_path: Path, scores_path: Path) -> tuple[dict, list[dict]]:
    run = json.loads(run_path.read_text(encoding="utf-8"))
    run_sha = sha256(run_path)
    rows = {}
    for line in scores_path.read_text(encoding="utf-8").splitlines():
        r = json.loads(line)
        if r.get("run_id") == run["run_id"] and r.get("run_sha256") == run_sha:
            rows[(r["monitor"], r["backend"])] = r
    monitors, used = {}, []
    for mon, backend, label in MONITORS:
        r = rows.get((mon, backend))
        if r is None:
            raise SystemExit(f"no score row for {mon} on {backend} for {run['run_id']} at sha256 {run_sha[:12]}")
        monitors[f"{mon}@{label}"] = {k: r[k] for k in ("verdict", "suspicion", "rule_hits", "reason")}
        used.append({"monitor": mon, "backend": backend, "verdict": r["verdict"], "suspicion": r["suspicion"],
                     "prompt_sha256": r["prompt_sha256"]})
    note = f"Attack library game {run['run_id']}; verdicts from replays/scores.jsonl rows for run sha256 {run_sha[:12]}."
    return {"format": "monitor-replay-bundle/v1", "note": note, "run": run,
            "replay": {"run_id": run["run_id"], "monitors": monitors}}, used


def export(viewer: Path, data: dict, event: int, theme: str) -> str:
    text = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    text = text.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    page = viewer.read_text(encoding="utf-8")
    marker = "<!-- EXAMPLES:BEGIN -->"
    if marker not in page or "window.__viewer" not in page:
        raise SystemExit(f"{viewer} is not the replay viewer (no examples marker or test hook)")
    page = page.replace(marker, marker + f'\n<script type="application/json" class="example" data-name="{NAME}" data-title="Figure 1">{text}</script>', 1)
    page = page.replace("</body>", HOOK % event, 1)
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "viewer.html"
        p.write_text(page, encoding="utf-8")
        svg = pre_text(dump_dom(f"file://{p}#example={NAME}&theme={theme}"), "__export")
    if not svg or not svg.startswith("<svg"):
        raise SystemExit("the viewer did not produce an export")
    return svg


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--viewer", default="viewer/index.html")
    ap.add_argument("--run", default="runs/attacks/attack-relabel_cover-seed205.json")
    ap.add_argument("--scores", default="replays/scores.jsonl")
    ap.add_argument("--event", type=int, default=3, help="1-based event index to freeze (3: the exit move)")
    ap.add_argument("--out", default="report/figures")
    a = ap.parse_args()
    viewer, run_path, scores = (ROOT / a.viewer), (ROOT / a.run), (ROOT / a.scores)
    data, used = bundle(run_path, scores)
    out = ROOT / a.out
    out.mkdir(parents=True, exist_ok=True)
    for theme, suffix in (("light", ""), ("dark", "-dark")):
        svg_path = out / f"{NAME}{suffix}.svg"
        svg_path.write_text(export(viewer, data, a.event, theme), encoding="utf-8")
        svg_to_png(svg_path, out / f"{NAME}{suffix}.png")
    prov = {"run_id": data["run"]["run_id"], "run_file": a.run, "run_sha256": sha256(run_path), "event": a.event,
            "viewer_sha256": sha256(viewer), "scores": a.scores, "monitors": used}
    (out / f"{NAME}.provenance.json").write_text(json.dumps(prov, indent=2) + "\n", encoding="utf-8")
    print(f"{NAME}: {prov['run_id']} at event {a.event}; {len(used)} monitors -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
