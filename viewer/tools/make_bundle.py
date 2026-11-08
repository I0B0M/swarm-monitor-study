"""Pack one saved game and its replayed monitor verdicts into a viewer example (monitor-replay-bundle/v1).

  python viewer/tools/make_bundle.py runs/attacks/attack-relabel_cover-seed205.json --out viewer/examples/attack-relabel_cover-seed205.json

The bundle holds the run file unchanged plus, for each monitor prompt and backend, the verdict, suspicion,
rule hits and reason of the row in replays/scores.jsonl whose run_id and run_sha256 match this run file.
Nothing else goes in: a verdict stored in the run file itself (the frozen monitor at game time) is shown by the
viewer from the run file, and a monitor with no matching row is simply absent. Then re-embed the examples:

  python viewer/tools/embed_examples.py
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

LABELS = {"claude:sonnet": "Sonnet 5.5", "local:agent": "gpt-oss-20b (open weights)",
          "local:coder": "Qwen3.8-27B (open weights)", "local:chores": "Qwen3.5-9B (open weights)"}
MONITORS = ["checklist", "judgement", "outcome"]


def build(run_path: Path, scores_path: Path, note: str = "") -> dict:
    raw = run_path.read_bytes()
    run, sha = json.loads(raw), hashlib.sha256(raw).hexdigest()
    rows = {}
    if scores_path.exists():
        for line in scores_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            r = json.loads(line)
            if r.get("run_id") == run["run_id"] and r.get("run_sha256") == sha and r.get("verdict") is not None:
                rows[(r["monitor"], r["backend"])] = r
    monitors = {}
    for mon in MONITORS:
        for backend, label in LABELS.items():
            r = rows.get((mon, backend))
            if r:
                monitors[f"{mon}@{label}"] = {k: r[k] for k in ("verdict", "suspicion", "rule_hits", "reason")}
    src = f"Verdicts: rows of replays/scores.jsonl for run sha256 {sha[:12]}." if monitors else "No replayed verdicts for this run."
    return {"format": "monitor-replay-bundle/v1", "note": " ".join(x for x in (note, src) if x), "run": run,
            "replay": {"run_id": run["run_id"], "monitors": monitors}}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("run")
    ap.add_argument("--scores", default="replays/scores.jsonl")
    ap.add_argument("--note", default="", help="one sentence shown under the game's title")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    b = build(Path(a.run), Path(a.scores), a.note)
    Path(a.out).write_text(json.dumps(b, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{a.out}: {b['run']['run_id']}, {len(b['replay']['monitors'])} replayed verdicts")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
