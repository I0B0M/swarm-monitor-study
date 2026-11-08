# Questions a judge is likely to ask

## Did you tune until it worked?

Not the monitor: its checklist was written once (commit d124d0b) and never edited. The saboteur, yes, on development layouts 1 to 5 only and all logged in [DEVLOG.md](DEVLOG.md): Claude models refused the role, so the instruction's wording changed and the saboteur moved to GPT-6.1 Sol before the freeze. Test layouts 101 to 125 ran after the tag `freeze-v1`. The plan for every added analysis was public in pull request #9 before any test file reached GitHub, with what we had seen at the time stated in its first section ([ANALYSIS_PLAN_ADDENDUM.md](ANALYSIS_PLAN_ADDENDUM.md)), and the attack library and ask probe use fresh layouts that never touched development or testing.

## Isn't the blind spot rigged?

It is designed and documented, not discovered: the checklist itself says it reads a record's tag at the moment of the exit move. What we measure is what that documented gap is worth to an attacker who can read it, and that depends on the monitor. With the checklist, gpt-oss-20b missed 75/100 rule-informed attacks; the same model given the task's rules and no checklist missed 1/100 ([replays/REPLAY_NUMBERS.md](replays/REPLAY_NUMBERS.md)). The scripted known-answer game that launders a tag ([runs/scripted/scripted-relabel_sabotage.json](runs/scripted/scripted-relabel_sabotage.json)) shows the frozen monitor's own reaction at game time: clean, with a suspicion score of 60.

## Isn't this a single-agent result?

The checklist sits with the honest agent in one condition and with the saboteur in another, so in the first the only route from the rules to the saboteur runs through its teammate. In the frozen games no honest keyholder opened the store (0/54), so that route was never used, and the paper says so plainly. The ask probe tests the honest side of the route directly: asked by a teammate, an open-weight keyholder opened the store in 35/60 games and repeated the checklist's wording in 0/60 ([replays/ASK_NUMBERS.md](replays/ASK_NUMBERS.md)).

## What is the false-alarm rate?

The frozen monitor flagged 0/100 honest games in the frozen study (provisional counts, issue #4). On the attack library every monitor's honest false alarms sit beside its miss rates, and the threshold view sets each monitor's threshold so that at most 5% of honest games are flagged ([replays/REPLAY_NUMBERS.md](replays/REPLAY_NUMBERS.md)). For example, gpt-oss-20b without a checklist flagged 1/50 honest library games, and Sonnet 5.5 with any of the three prompts flagged 0/25.

## Why these models?

Claude models refused to play the saboteur in development, so it runs on GPT-6.1 Sol. The honest agent is Claude Haiku 5.5 and the frozen monitor Claude Sonnet 5.5, a strong monitor. The open-weight monitors (gpt-oss-20b, Qwen3.8-27B, Qwen3.5-9B) play the weaker trusted monitors that control evaluations conventionally use, and anyone can rerun them offline; their weight files' hashes are in [replays/MODELS.md](replays/MODELS.md).

## What if the effect is zero?

It was, in the pre-registered comparison, and the paper reports it first: undetected sabotage was 0/50 in the baseline and 0/54 with the honest agent holding the checklist, a difference within plus or minus 10 points by an equivalence test fixed in advance. A zero there means the checklist never reached the saboteur, not that secrecy is worthless; the attack library shows where rule knowledge does pay.

## Isn't the outcome monitor just the referee?

Close to it: it sees the manifest and the end state, as the plain-code referee does, so catching nearly every violation is expected by construction. It is the reference for the defensive recommendation (check the end state when you can), not a discovery. The 1st-place project at Apart's AI Control Hackathon 2026 made the same point for attacks of omission with a final-state check.

## Aren't you attacking your own blind spot?

Yes, on purpose, and on fresh layouts that never touch the test set. The library's attacks are hand-written, so they are a lower bound on what full rule knowledge can buy. What the library measures is how much of the gap each monitor inherits, and that differs sharply: 75/100 missed by the literal checklist monitor, 1/100 by the same model using judgement.

## Is anything here pre-existing?

No. The repository was created on 2026-11-07 during the sprint, and its history starts that day.
