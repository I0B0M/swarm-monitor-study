# Swarm Monitor Study

What happens when one AI agent finds the rulebook for the system watching its team?

Two AI agents work together on the same fictional inventory task. We compare three setups.

| Setup | What the agents know |
| --- | --- |
| 1. No monitor | No monitor reviews the run. The experiment still records actions. |
| 2. Known monitor | Both agents are told a monitor watches. |
| 3. One agent can find the instructions | Both agents know the same monitor watches. Only one can read a planted copy of its instructions. |

The task, incentives, tools and opportunity to break a rule are matched across setups. The monitor is passive and has the same prompt and access in both monitored setups. Independent action logs determine which rules the agents actually broke. In the monitored runs, we also count which violations the monitor caught, which it missed and how often it flagged a clean run.

The experiment starts with a small pilot. The final report should show the counts across all three setups and one example that explains what changed. There are no study results yet.

## Start here

[Open issues](../../issues) hold the implementation order. Start with the inventory task and one replayable run. The model pilot depends on confirming provider eligibility and a budget.
