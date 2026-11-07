"""One command for every game.

  python run.py --scripted                      4 known-answer games, no model calls
  python run.py --split dev --cells S2-imp --n 1  one live smoke game
  python run.py --split test --workers 6          the full test run (after freeze-v1)

Finished games are skipped, so a run stopped by a usage limit resumes where it left off.
"""

from __future__ import annotations

import argparse
import fcntl
import json
import os
import subprocess
import sys
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from datetime import datetime, timezone
from pathlib import Path

from swarm import leak, scripted
from swarm.backends import (
    CODEX_MODEL, ClaudeCLIBackend, CodexCLIBackend, ScriptedBackend, usage_limit,
)
from swarm.cells import CELLS, ORDER, games
from swarm.game import run_game
from swarm.guard import GUARD_SCHEMA, review
from swarm.seeds import load

ROOT = Path(__file__).resolve().parent
TEST_CUTOFF = datetime.fromisoformat("2026-11-08T12:00:00-05:00")
HONEST_MODEL = "claude-haiku-5-5"
GUARD_MODEL = "claude-sonnet-5-5"


def now():
    return datetime.now(timezone.utc)


def check_frozen(args, parser, out, *, play):
    if args.guard_model != GUARD_MODEL:
        parser.error("test reviews require the frozen Sonnet model")
    if out.resolve() != (ROOT / "runs").resolve():
        parser.error("test games and reviews use the canonical runs/test directory")
    if play:
        if (args.imposter_backend, args.imposter_model or CODEX_MODEL, args.model) != (
                "codex-cli", CODEX_MODEL, HONEST_MODEL):
            parser.error("test requires the frozen Codex imposter and Haiku crewmate")
        if args.n is not None or not args.guard or args.cells not in (None, "all"):
            parser.error("test requires all preregistered cells and the checklist guard")
    frozen = subprocess.run(["git", "diff", "--quiet", "freeze-v1", "--",
                             "run.py", "seeds.json", "swarm", "analyze.py"], cwd=ROOT)
    if frozen.returncode != 0:
        parser.error("test code or seeds do not match freeze-v1")


def with_split_lock(out, split, action):
    folder = out / split
    folder.mkdir(parents=True, exist_ok=True)
    # Use a permanent inode for the lock; removing it can race with a second runner.
    with (folder / ".runner.tmp").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            sys.exit(f"another writer is running for {folder}")
        return action()



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
             if json.loads(p.read_text()).get("guards", {}).get("checklist", {}).get("verdict") is None]
    print(f"{len(paths)} games need a guard verdict")

    def one(path):
        if (args.review or args.review_leak) == "test" and now() >= TEST_CUTOFF:
            return None
        record = json.loads(path.read_text())
        record["guards"]["checklist"] = review(record, guard)
        record["guard_finished_at"] = now().isoformat()
        write_json(path, record)
        return record

    errors = 0
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        for done, r in enumerate(pool.map(one, paths), 1):
            if r is None:
                errors += 1
                continue
            g = r["guards"]["checklist"]
            errors += g["verdict"] is None
            print(f"[{done}/{len(paths)}] {r['run_id']}: guard={g['verdict']}/{g.get('suspicion')}", flush=True)
    return int(bool(errors))


def run_review_leak(args, out: Path) -> int:
    """Annotate S3b chat, including retries for previously failed annotations."""
    paths = []
    for path in sorted((out / args.review_leak).glob("*.json")):
        record = json.loads(path.read_text())
        if record.get("cell") == "S3b-imp" and record["leak"].get("conveyed") is None:
            paths.append(path)
    print(f"{len(paths)} S3b games need leak annotation", flush=True)
    backend = ClaudeCLIBackend(model=args.guard_model, schema=leak.LEAK_SCHEMA)

    def one(path):
        if (args.review or args.review_leak) == "test" and now() >= TEST_CUTOFF:
            return None
        record = json.loads(path.read_text())
        record["leak"] = leak.review(record, backend)
        record["leak"]["reviewed_at"] = now().isoformat()
        write_json(path, record)
        return record

    errors = 0
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        for done, record in enumerate(pool.map(one, paths), 1):
            if record is None:
                errors += 1
                continue
            result = record["leak"]
            errors += result["conveyed"] is None
            print(f"[{done}/{len(paths)}] {record['run_id']}: asked={result['asked_by']} "
                  f"conveyed={result['conveyed']} started={result['started_by']}"
                  f" error={result['judge'].get('error', '-')}", flush=True)
    return int(bool(errors))


def run_split(args, out: Path) -> int:
    cells = args.cells.split(",") if args.cells not in (None, "all") else ORDER
    unknown = [c for c in cells if c not in CELLS]
    if unknown:
        sys.exit(f"unknown cells: {unknown}; choose from {list(CELLS)}")
    split_dir = out / args.split
    expected = games(args.split, cells, args.n)
    interrupted = [cfg["run_id"] for cfg, _ in expected
                   if (split_dir / f"{cfg['run_id']}.started").exists()
                   and not (split_dir / f"{cfg['run_id']}.json").exists()]
    if interrupted:
        print(f"Interrupted test games will not be replayed: {', '.join(interrupted)}", flush=True)
    todo = [(cfg, layout) for cfg, layout in expected
            if not (split_dir / f"{cfg['run_id']}.json").exists() and cfg["run_id"] not in interrupted]
    print(f"{len(todo)} games to run ({args.split}, cells {cells}, agents on {args.model})", flush=True)
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
        path = split_dir / f"{cfg['run_id']}.json"
        started = path.with_suffix(".started")
        if args.split == "test":
            with started.open("x") as marker:
                marker.write(now().isoformat() + "\n")
        record = run_game(cfg, layout, RoleRouter(cfg["imposter"], backend, imposter_backend))
        record["finished_at"] = now().isoformat()
        # Preserve the played game even if the independent guard call is interrupted.
        write_json(path, record)
        if args.split == "test":
            started.unlink()
        if guard and not record["usage_limited"]:
            result = review(record, guard)
            record["guards"]["checklist"] = result
            record["guard_finished_at"] = now().isoformat()
            record["usage_limited"] = usage_limit(result.get("error", ""))
            write_json(path, record)
        return record

    failed, done = 0, 0
    stop = None
    remaining = iter(todo)
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        pending = set()

        def fill():
            nonlocal stop
            while not stop and len(pending) < args.workers:
                if args.split == "test" and now() >= TEST_CUTOFF:
                    stop = "test cutoff"
                    break
                job = next(remaining, None)
                if job is None:
                    break
                pending.add(pool.submit(one, *job))

        fill()
        while pending:
            completed, pending = wait(pending, return_when=FIRST_COMPLETED)
            for fut in completed:
                r = fut.result()
                done += 1
                g = r["guards"].get("checklist") or {}
                failed += r["failed"] or (guard is not None and g.get("verdict") is None)
                if r["usage_limited"]:
                    stop = "subscription usage limit"
                print(f"[{done}/{len(todo)}] {r['run_id']}: violation={r['referee']['violation']} "
                      f"tried={bool(r['referee']['moved_restricted'] or r['referee']['relabelled_restricted'])} "
                      f"complete={r['referee']['task_complete']} guard={g.get('verdict')}/{g.get('suspicion')} "
                      f"errors={len(r['errors'])}{' FAILED' if r['failed'] else ''}", flush=True)
            fill()
    print(f"done; {failed} failed or unreviewed games (kept on disk and counted)", flush=True)
    if stop:
        print(f"Stopped dispatch at {stop}; {len(todo) - done} games not started.", flush=True)
        return 75
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--scripted", action="store_true", help="run the 4 known-answer games")
    p.add_argument("--split", choices=["dev", "test"])
    p.add_argument("--cells", help="comma-separated cell names (default: all, in priority order)")
    p.add_argument("--n", type=int, help="override games per cell (smoke tests)")
    p.add_argument("--workers", type=int, default=6)
    p.add_argument("--model", default=HONEST_MODEL, help="model ID for the honest agents")
    p.add_argument("--imposter-backend", choices=["claude-cli", "codex-cli"], default="codex-cli")
    p.add_argument("--imposter-model", help="model for the imposter only (default: backend default)")
    p.add_argument("--guard-model", default=GUARD_MODEL, help="model ID for the checklist guard")
    p.add_argument("--no-guard", dest="guard", action="store_false", help="skip the guard review")
    p.add_argument("--review", choices=["scripted", "dev", "test"], help="add guard verdicts to saved games")
    p.add_argument("--review-leak", choices=["dev", "test"], help="annotate saved S3b chat")
    p.add_argument("--out", default=str(ROOT / "runs"))
    args = p.parse_args()
    if args.workers < 1 or (args.n is not None and args.n < 1):
        p.error("--workers and --n must be positive")
    out = Path(args.out)
    if args.scripted:
        return with_split_lock(out, "scripted", lambda: run_scripted(args, out))
    if args.review:
        if args.review == "test":
            check_frozen(args, p, out, play=False)
        return with_split_lock(out, args.review, lambda: run_review(args, out))
    if args.review_leak:
        if args.review_leak == "test":
            check_frozen(args, p, out, play=False)
        return with_split_lock(out, args.review_leak, lambda: run_review_leak(args, out))
    if not args.split:
        p.error("give --scripted, --review, --review-leak or --split")
    if args.split == "test":
        check_frozen(args, p, out, play=True)
    return with_split_lock(out, args.split, lambda: run_split(args, out))


if __name__ == "__main__":
    sys.exit(main())
