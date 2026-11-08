# Replay viewer

Open `index.html` in any browser. It is one file, works offline from disk, and fetches nothing.

It plays back one game event by event: the two agents, every record with its tag, the secured store and who holds its key, and the review log a monitor reads after the game. At the end it shows what happened (decided by plain code from the end state) beside what each monitor said. Restricted records carry a hatch pattern and a red outline, so nothing depends on colour alone; the page follows the system's light or dark setting and honours reduced motion.

**Examples.** The picker holds six games, each packed from a saved run file and, for replayed monitors, the matching rows of `replays/scores.jsonl` (same run ID and run file SHA-256):

- four attack-library games on layout 205 (tag laundering with a cover message, a store opening followed by laundering, a naive attack, an honest game);
- the repository's known-answer game for tag laundering, with the frozen monitor's verdict stored at game time;
- a development game in which the saboteur refused its instruction and told its teammate.

**Your own game.** Use "Open a file" or drop a run JSON (`runs/**/*.json`) or a bundle on the page.

**Stills.** "Save still (SVG)" and "Save still (PNG)" export the current frame with the verdicts; the report's Figure 1 is this export (`tools/make_figure1.py`).

**Keys.** Space plays or pauses, Left and Right step, Home and End jump to the first or last event.

**Adding an example.**

```bash
python viewer/tools/make_bundle.py runs/attacks/attack-relabel_cover-seed205.json --out viewer/examples/attack-relabel_cover-seed205.json
python viewer/tools/embed_examples.py
```

The page's address records the game, the event and the theme (for example `index.html#example=attack-plain_first-seed205&event=last&panel=verdicts`), so a link opens the same frame.
