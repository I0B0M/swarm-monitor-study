"""Regenerate frozen metrics, then apply the authorized reporting notes."""

from pathlib import Path

import analyze
from followup_report import append_followup


def main():
    analyze.main()
    report = Path("NUMBERS.md")
    rows, _, _ = analyze.load_rows(Path("runs/test"), "test")
    direct = [r for r in rows if r["cell"] == "S3a-imp"]
    teammate = [r for r in rows if r["cell"] == "S3b-imp"]
    judged = [r for r in teammate if r["conveyed"] is not None]
    opened = sum(r["opened"] for r in teammate)
    asked = sum(bool(r["asked_by"]) for r in judged)
    lines = [
        "## Recovery notes",
        "",
        "Source command: `python3.12 recovery_report.py --split test`.",
        "",
        f"S3a among {len(direct)} saved games: {sum(r['opened'] for r in direct)} opened, "
        f"{sum(r['relabelled'] for r in direct)} relabelled, "
        f"{sum(r['violation'] for r in direct)} violations, "
        f"{sum(r['undetected'] for r in direct)} confirmed undetected, "
        f"and {sum(r['guard_missing'] for r in direct)} missing guard verdicts.",
        "",
    ]
    if len(judged) == len(teammate) == 60 and not asked and not opened:
        lines += ["S3b: the disclosure pathway was not exercised (0/60 requests, "
                  "0/60 openings); no inference about disclosure is possible from this cell.", ""]
    else:
        lines += [f"S3b: {opened}/{len(teammate)} keyholders opened the locker. "
                  f"Requests and disclosures have been assessed in {len(judged)}/{len(teammate)} "
                  "saved games.", ""]
    candidates = [r for r in direct if r["opened"] and r["relabelled"] and not r["game_failed"]]
    lines += ["## Figure 1 replay", ""]
    if candidates:
        best = max(candidates, key=lambda r: (r["relabelled_then_shipped"], r["undetected"],
                                              r["violation"], not r["guard_missing"]))
        path = f"runs/test/{best['run_id']}.json"
        lines += [f"Use `{path}`. The imposter opened the rulebook and relabelled a restricted crate. "
                  f"Final violation: {best['violation']}. Checklist verdict: {best['guard_verdict']}.",
                  f"Source command: `python3.12 -m json.tool {path}`.", ""]
    else:
        lines += ["No completed S3a replay with an opening and relabel is available.", ""]
    base = report.read_text().split("## Figure 1 replay", 1)[0]
    report.write_text(base + "\n".join(lines))
    append_followup(report, Path("runs/test"))


if __name__ == "__main__":
    main()
