"""One command for every game.

  python run.py --scripted                      4 known-answer games, no model calls
  python run.py --split dev --cells S2-imp --n 1  one live smoke game
  python run.py --split test --workers 6          the full test run (after freeze-v1)

Finished games are skipped, so a run stopped by a usage limit resumes where it left off.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from swarm import scripted
from swarm.backends import ClaudeCLIBackend, ScriptedBackend
from swarm.cells import CELLS, ORDER, games
from swarm.game import run_game
from swarm.seeds import load

ROOT = Path(__file__).resolve().parent


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=1) + "\n")
    os.replace(tmp, path)


def run_scripted(out: Path) -> int:
    layout = load("dev")[1]
    bad = 0
    for name, game in scripted.build(layout).items():
        cfg = {"run_id": f"scripted-{name}", **game["cfg"]}
        record = run_game(cfg, layout, ScriptedBackend(game["scripts"]))
        write_json(out / "scripted" / f"{cfg['run_id']}.json", record)
        got = {k: record["referee"][k] for k in game["expect"]}
        ok = got == game["expect"]
        bad += not ok
        print(f"{'ok  ' if ok else 'FAIL'} {name:18} referee={got} expected={game['expect']}")
    return 1 if bad else 0


def run_split(args, out: Path) -> int:
    cells = args.cells.split(",") if args.cells else ORDER
    unknown = [c for c in cells if c not in CELLS]
    if unknown:
        sys.exit(f"unknown cells: {unknown}; choose from {list(CELLS)}")
    todo = [(cfg, layout) for cfg, layout in games(args.split, cells, args.n)
            if not (out / args.split / f"{cfg['run_id']}.json").exists()]
    print(f"{len(todo)} games to run ({args.split}, cells {cells}, agents on {args.model})")
    backend = ClaudeCLIBackend(model=args.model)

    def one(cfg, layout):
        record = run_game(cfg, layout, backend)
        write_json(out / args.split / f"{cfg['run_id']}.json", record)
        return record

    failed = 0
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(one, cfg, layout) for cfg, layout in todo]
        for done, fut in enumerate(as_completed(futures), 1):
            r = fut.result()
            failed += r["failed"]
            print(f"[{done}/{len(todo)}] {r['run_id']}: violation={r['referee']['violation']} "
                  f"complete={r['referee']['task_complete']} errors={len(r['errors'])}"
                  f"{' FAILED' if r['failed'] else ''}", flush=True)
    print(f"done; {failed} failed games (kept on disk and counted)")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--scripted", action="store_true", help="run the 4 known-answer games")
    p.add_argument("--split", choices=["dev", "test"])
    p.add_argument("--cells", help="comma-separated cell names (default: all, in priority order)")
    p.add_argument("--n", type=int, help="override games per cell (smoke tests)")
    p.add_argument("--workers", type=int, default=6)
    p.add_argument("--model", default="haiku", help="model alias for the agents")
    p.add_argument("--out", default=str(ROOT / "runs"))
    args = p.parse_args()
    out = Path(args.out)
    if args.scripted:
        return run_scripted(out)
    if not args.split:
        p.error("give --scripted or --split")
    return run_split(args, out)


if __name__ == "__main__":
    sys.exit(main())
