"""Run the approved recovery sequence after the Claude quota resets."""
from datetime import datetime, timedelta
import json
from pathlib import Path
import shutil
import subprocess
import sys

from run import ROOT, TEST_CUTOFF, now
from swarm.backends import usage_limit

RESET = TEST_CUTOFF - timedelta(hours=6)
RUNS = ROOT / "runs/test"
ARCHIVE = ROOT / "runs/archive/test-infra-failures"


def command(*args):
    return subprocess.run(args, cwd=ROOT).returncode


def checkpoint(message, *paths):
    subprocess.run(["git", "add", "--", *paths], cwd=ROOT, check=True)
    if command("git", "diff", "--cached", "--quiet") == 1:
        subprocess.run(["git", "commit", "-m", message], cwd=ROOT, check=True)


def run(*args):
    return command(sys.executable, "-u", "run.py", *args, "--workers", "6")


def s3a_complete():
    rows = [json.loads(path.read_text()) for path in RUNS.glob("*S3a-imp*.json")]
    return len(rows) == 50 and all(
        datetime.fromisoformat(row["finished_at"]) < TEST_CUTOFF
        and not any(usage_limit(e["error"]) for e in row["errors"])
        for row in rows
    )


def restore_s3b():
    restored = []
    for original in sorted(ARCHIVE.glob("*S3b-imp*.json")):
        active = RUNS / original.name
        if active.exists():
            row = json.loads(active.read_text())
            if (datetime.fromisoformat(row["finished_at"]) < TEST_CUTOFF
                    and not row["errors"]
                    and row.get("guards", {}).get("checklist", {}).get("verdict") is not None
                    and row.get("leak", {}).get("conveyed") is not None
                    and datetime.fromisoformat(row["guard_finished_at"]) < TEST_CUTOFF
                    and datetime.fromisoformat(row["leak"]["reviewed_at"]) < TEST_CUTOFF):
                continue
            # A previous recovery may already have restored this same original.
            if active.read_bytes() == original.read_bytes():
                continue
            retained = ARCHIVE / "replacement-attempts" / active.name
            retained.parent.mkdir(exist_ok=True)
            if retained.exists():
                raise RuntimeError(f"refusing to overwrite preserved attempt: {retained}")
            active.rename(retained)
        shutil.copyfile(original, active)
        restored.append(original.stem)
    if restored:
        with (ROOT / "DEVLOG.md").open("a") as out:
            out.write("\nS3b recovery fallback: restored the original failed records for "
                      "replacements that could not be completed and reviewed. "
                      + ", ".join(restored) + ".\n")


def main():
    if now() < RESET:
        sys.exit("Claude reset is still pending. No model calls were started.")
    branch = subprocess.check_output(["git", "branch", "--show-current"], cwd=ROOT, text=True).strip()
    if branch != "test" or command("git", "diff", "--cached", "--quiet"):
        sys.exit("Recovery requires branch test and a clear Git index.")
    stages = [
        ("A", "Checkpoint S3a recovery", ("--split", "test", "--cells", "S3a-imp")),
        ("B", "Checkpoint outstanding checklist reviews", ("--review", "test")),
        ("C", "Checkpoint S3b leak reviews", ("--review-leak", "test")),
        ("D", "Checkpoint S3b replacement games", ("--split", "test", "--cells", "S3b-imp")),
        ("D guard", "Checkpoint S3b replacement checklist reviews", ("--review", "test")),
        ("D leak", "Checkpoint S3b replacement leak reviews", ("--review-leak", "test")),
    ]
    failed = None
    for label, message, args in stages:
        if now() >= TEST_CUTOFF:
            failed = f"{label}: cutoff"
            break
        print(f"Recovery step {label}", flush=True)
        status = run(*args)
        checkpoint(message, "runs/test")
        if status or (label == "A" and not s3a_complete()):
            failed = f"{label}: runner exit {status} or incomplete recovery"
            break
    if failed:
        restore_s3b()
    subprocess.run([sys.executable, "recovery_report.py", "--split", "test"], cwd=ROOT, check=True)
    checkpoint("Regenerate study results after recovery", "DEVLOG.md", "runs/test",
               "runs/archive/test-infra-failures", "NUMBERS.md", "results.csv",
               "undetected-sabotage.svg", "s3b-leak-funnel.svg")
    if failed:
        sys.exit(f"Recovery stopped at step {failed}. Checkpoint and report saved.")


if __name__ == "__main__":
    main()
