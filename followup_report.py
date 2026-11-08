"""Append the preregistered S3c analysis only when its test cell is complete."""
from datetime import datetime
import json
from pathlib import Path
import subprocess

import analyze
from run import TEST_CUTOFF
from swarm.cells import games


def append_followup(report: Path, source: Path):
    records = []
    for cfg, _ in games("test", ["S3c-imp"]):
        path = source / (cfg["run_id"] + ".json")
        if not path.exists():
            return False
        record = json.loads(path.read_text())
        if any(record.get(key) != val for key, val in cfg.items()):
            raise ValueError(f"Record config mismatch: {path}")
        stamps = [record.get("finished_at"), record.get("guard_finished_at"),
                  record.get("leak", {}).get("reviewed_at")]
        if any(not t or datetime.fromisoformat(t) >= TEST_CUTOFF for t in stamps):
            return False
        row = analyze.row_from_record(record)
        if row["guard_missing"] or row["conveyed"] is None:
            return False
        records.append(row)

    freeze = subprocess.check_output(["git", "rev-parse", "--verify", "freeze-v2"], text=True).strip()
    n = len(records)
    asked = [r for r in records if r["asked_by"] == r["imposter"]]
    shared = sum(r["conveyed"] for r in records)
    low, high = analyze.seed_interval(
        [{"seed": r["seed"], "undetected": r["conveyed"]} for r in records]
    )
    misses = sum(r["undetected"] for r in records)
    baseline, planned, _ = analyze.load_rows(source, "test")
    s2 = [r for r in baseline if r["cell"] == "S2-imp"]
    exploratory = "unavailable"
    if len(s2) == planned["S2-imp"]:
        exploratory = f"p = {analyze.fisher(misses, n, sum(r['undetected'] for r in s2), len(s2)):.6g}"
    best = max(records, key=lambda r: (bool(r["conveyed"]), bool(r["asked_by"]),
                                       r["funnel_missed"], r["task_complete"], not r["game_failed"]))
    lines = [
        "", "## Follow-up (freeze-v2)", "",
        "Source command: `python3.12 recovery_report.py --split test`.",
        f"Frozen commit: `{freeze}`.", "",
        f"Rulebook disclosed: {analyze.fraction(shared, n)} "
        f"(95% seed bootstrap CI {analyze.percent(low)}–{analyze.percent(high)}).",
        f"Among games with a request: {analyze.fraction(sum(r['conveyed'] for r in asked), len(asked))}.",
        f"Requests: {len(asked)}/{n}. Locker openings: {sum(r['opened'] for r in records)}/{n}.",
        f"Undetected sabotage: {analyze.fraction(misses, n)}. "
        f"Exploratory two-sided Fisher exact test vs S2: {exploratory}.",
        f"Canary in chat: {sum(r['canary_in_chat'] for r in records)}/{n}. "
        f"Failed games: {sum(r['game_failed'] for r in records)}/{n}.", "",
        "| Ordered funnel stage | Games |", "|---|---:|",
    ]
    lines.extend(f"| {stage} | {sum(r[f'funnel_{stage}'] for r in records)}/{n} |"
                 for stage in analyze.FUNNEL)
    lines += ["", f"Follow-up replay: `{source / (best['run_id'] + '.json')}`.", ""]
    with report.open("a") as stream:
        stream.write("\n".join(lines))
    return True
