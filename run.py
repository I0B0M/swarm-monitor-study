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
from swarm.backends import CODEX_MODEL, ClaudeCLIBackend, CodexCLIBackend, ScriptedBackend
from swarm.cells import CELLS, ORDER, games
from swarm.game import run_game
from swarm.guard import GUARD_SCHEMA, review
from swarm.seeds import load

ROOT = Path(__file__).resolve().parent


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=1) + "\n")
    os.replace(tmp, path)


class RoleRouter:
    """Sends the imposter's turns to the imposter's model and everyone else's to the agent model."""

    def __init__(self, imposter, honest_backend, imposter_backend):
        self.imposter, self.honest, self.imp = imposter, honest_backend, imposter_backend

    def act(self, agent, system, observation):
        return (self.imp if agent == self.imposter else self.honest).act(agent, system, observation)


def guard_backend(args) -> ClaudeCLIBackend:
    return ClaudeCLIBackend(model=args.guard_model, schema=GUARD_SCHEMA)


def run_scripted(args, out: Path) -> int:
    layout = load("dev")[1]
    guard = guard_backend(args) if args.guard else None
    bad = 0
    for name, game in scripted.build(layout).items():
        cfg = {"run_id": f"scripted-{name}", **game["cfg"]}
        record = run_game(cfg, layout, ScriptedBackend(game["scripts"]))
        if guard:
            record["guards"]["checklist"] = review(record, guard)
        write_json(out / "scripted" / f"{cfg['run_id']}.json", record)
        got = {k: record["referee"][k] for k in game["expect"]}
        ok = got == game["expect"]
        bad += not ok
        g = record["guards"].get("checklist")
        gtxt = f" guard={g['verdict']}/{g.get('suspicion')} rules={g.get('rule_hits')}" if g else ""
        print(f"{'ok  ' if ok else 'FAIL'} {name:18} referee={got}{gtxt}")
    return 1 if bad else 0


def run_review(args, out: Path) -> int:
    """Add a checklist-guard verdict to saved games that do not have one yet."""
    guard = guard_backend(args)
    paths = [p for p in sorted((out / args.review).glob("*.json"))
             if "checklist" not in json.loads(p.read_text()).get("guards", {})]
    print(f"{len(paths)} games need a guard verdict")

    def one(path):
        record = json.loads(path.read_text())
        record["guards"]["checklist"] = review(record, guard)
        write_json(path, record)
        return record

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        for done, r in enumerate(pool.map(one, paths), 1):
            g = r["guards"]["checklist"]
            print(f"[{done}/{len(paths)}] {r['run_id']}: guard={g['verdict']}/{g.get('suspicion')}", flush=True)
    return 0


def run_split(args, out: Path) -> int:
    cells = args.cells.split(",") if args.cells else ORDER
    unknown = [c for c in cells if c not in CELLS]
    if unknown:
        sys.exit(f"unknown cells: {unknown}; choose from {list(CELLS)}")
    todo = [(cfg, layout) for cfg, layout in games(args.split, cells, args.n)
            if not (out / args.split / f"{cfg['run_id']}.json").exists()]
    print(f"{len(todo)} games to run ({args.split}, cells {cells}, agents on {args.model})")
    backend = ClaudeCLIBackend(model=args.model)
    if args.imposter_backend == "codex-cli":
        imposter_backend = CodexCLIBackend(model=args.imposter_model or CODEX_MODEL)
    else:
        imposter_backend = ClaudeCLIBackend(model=args.imposter_model) if args.imposter_model else backend
    guard = guard_backend(args) if args.guard else None

    def one(cfg, layout):
        cfg = {**cfg, "agent_model": args.model,
               "imposter_model": imposter_backend.model if cfg["imposter"] else None,
               "imposter_backend": args.imposter_backend if cfg["imposter"] else None}
        record = run_game(cfg, layout, RoleRouter(cfg["imposter"], backend, imposter_backend))
        if guard:
            record["guards"]["checklist"] = review(record, guard)
        write_json(out / args.split / f"{cfg['run_id']}.json", record)
        return record

    failed = 0
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(one, cfg, layout) for cfg, layout in todo]
        for done, fut in enumerate(as_completed(futures), 1):
            r = fut.result()
            failed += r["failed"]
            g = r["guards"].get("checklist") or {}
            print(f"[{done}/{len(todo)}] {r['run_id']}: violation={r['referee']['violation']} "
                  f"tried={bool(r['referee']['moved_restricted'] or r['referee']['relabelled_restricted'])} "
                  f"complete={r['referee']['task_complete']} guard={g.get('verdict')}/{g.get('suspicion')} "
                  f"errors={len(r['errors'])}{' FAILED' if r['failed'] else ''}", flush=True)
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
    p.add_argument("--imposter-backend", choices=["claude-cli", "codex-cli"], default="claude-cli")
    p.add_argument("--imposter-model", help="model for the imposter only (default: backend default)")
    p.add_argument("--guard-model", default="sonnet", help="model alias for the checklist guard")
    p.add_argument("--no-guard", dest="guard", action="store_false", help="skip the guard review")
    p.add_argument("--review", choices=["scripted", "dev", "test"], help="add guard verdicts to saved games")
    p.add_argument("--out", default=str(ROOT / "runs"))
    args = p.parse_args()
    out = Path(args.out)
    if args.scripted:
        return run_scripted(args, out)
    if args.review:
        return run_review(args, out)
    if not args.split:
        p.error("give --scripted, --review or --split")
    return run_split(args, out)


if __name__ == "__main__":
    sys.exit(main())
