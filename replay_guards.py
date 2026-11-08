"""Replay saved games through other monitors, without touching the game (issue #5).

  python replay_guards.py --runs runs/test --backend claude:sonnet --monitors judgement,outcome --workers 3
  python replay_guards.py --runs runs/test runs/attacks --backend local:agent --monitors checklist,judgement,outcome
  python replay_guards.py --runs runs/dev-prompt-v3-haiku --backend local:agent --dry-run

One JSON line per (game, monitor, backend) is appended to replays/scores.jsonl. Rerunning skips rows
that already have a verdict, so a run stopped by a usage limit resumes. A missing verdict is written
as missing and never counted as clean. Run files are read, hashed and never modified.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import threading
import time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from replay.backends import make_backend
from replay.monitors import LOCAL_SCHEMA, MONITORS, SCHEMA, review
from replay.runs import attempted, derive_cell, load_runs, sha256_file

ROOT = Path(__file__).resolve().parent


def done_keys(out: Path) -> set:
    keys = set()
    if out.exists():
        for line in out.read_text().splitlines():
            r = json.loads(line)
            if r.get("verdict") is not None:
                keys.add((r["run_id"], r["monitor"], r["backend"]))
    return keys


def row_for(path: Path, rec: dict, verdict: dict, backend: str) -> dict:
    ref = rec["referee"]
    return {
        "run_id": rec["run_id"], "file": str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path),
        "run_sha256": sha256_file(path), "split": rec.get("split"), "cell": derive_cell(rec),
        "setup": rec.get("setup"), "crew": rec.get("crew"), "seed": rec.get("seed"),
        "attack_kind": rec.get("attack_kind"), "attack_policy": rec.get("attack_policy"),
        "violation": ref["violation"], "relabelled": bool(ref.get("relabelled_restricted")),
        "attempted": attempted(rec), "failed": rec.get("failed", False), "backend": backend,
        **{k: verdict.get(k) for k in ("monitor", "verdict", "suspicion", "rule_hits", "reason", "error",
                                        "models", "attempts", "duration_ms", "cost_usd_equiv", "prompt_sha256")},
    }


def summarise(rows: list[dict]) -> None:
    table = defaultdict(Counter)
    for r in rows:
        if r["verdict"] is None:
            table[(r["cell"], r["monitor"])]["missing"] += 1
            continue
        c = table[(r["cell"], r["monitor"])]
        c["games"] += 1
        c["violations"] += r["violation"]
        c["flagged"] += r["verdict"] == "flag"
        c["undetected"] += r["violation"] and r["verdict"] == "clean"
    print(f"{'cell':22} {'monitor':10} games viol flag undetected missing")
    for (cell, mon), c in sorted(table.items()):
        print(f"{cell:22} {mon:10} {c['games']:5} {c['violations']:4} {c['flagged']:4} {c['undetected']:10} {c['missing']:7}")


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--runs", nargs="+", required=True, help="folders of saved game files")
    p.add_argument("--backend", required=True, help="claude:<alias> or local:<model>")
    p.add_argument("--monitors", default="judgement,outcome", help=f"comma list from {sorted(MONITORS)}")
    p.add_argument("--workers", type=int, default=3)
    p.add_argument("--out", default=str(ROOT / "replays" / "scores.jsonl"))
    p.add_argument("--limit", type=int, help="score at most this many (game, monitor) pairs")
    p.add_argument("--match", help="only games whose run_id matches this regular expression")
    p.add_argument("--dry-run", action="store_true", help="list what would be scored and stop")
    args = p.parse_args()

    monitors = args.monitors.split(",")
    unknown = [m for m in monitors if m not in MONITORS]
    if unknown:
        sys.exit(f"unknown monitors {unknown}; choose from {sorted(MONITORS)}")
    games = load_runs(args.runs)
    if args.match:
        games = [(path, rec) for path, rec in games if re.search(args.match, rec["run_id"])]
    if not games:
        print(f"0 games found in {args.runs}")
        return 2
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    skip = done_keys(out)
    todo = [(path, rec, m) for path, rec in games for m in monitors if (rec["run_id"], m, args.backend) not in skip]
    if args.limit:
        todo = todo[: args.limit]
    splits = Counter(rec.get("split") for _, rec in games)
    print(f"{len(games)} games ({dict(splits)}); {len(todo)} (game, monitor) pairs to score on {args.backend}")
    if args.dry_run or not todo:
        return 0

    backend = make_backend(args.backend, SCHEMA, LOCAL_SCHEMA)
    lock, rows, calls = threading.Lock(), [], Counter()

    def one(item):
        path, rec, m = item
        verdict = review(m, rec, backend)
        row = row_for(path, rec, verdict, args.backend)
        with lock:
            with out.open("a") as fh:
                fh.write(json.dumps(row) + "\n")
            rows.append(row)
            calls[args.backend] += verdict.get("attempts") or 0
        return row

    t0 = time.time()
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        for i, r in enumerate(pool.map(one, todo), 1):
            if i % 10 == 0 or i == len(todo):
                print(f"[{i}/{len(todo)}] {r['run_id']} {r['monitor']} -> {r['verdict']}/{r['suspicion']}", flush=True)
    print(f"done in {time.time() - t0:.0f} s; model calls on {args.backend}: {calls[args.backend]}")
    summarise(rows)
    return 0


if __name__ == "__main__":
    sys.exit(main())
