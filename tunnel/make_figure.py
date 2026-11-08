"""Draw Figure 1 from FACTS.json and print the breakdown of 'no' answers. Run facts.py first."""
import glob, json, re
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
ALL = json.loads((HERE / "FACTS.json").read_text())
F = ALL["locked"]
CI = {g: ALL["stats"][f"finder_used_ci_{g}"] for g in ("none", "watch", "penalty")}
INK, MUTED, GRID = "#1a1a19", "#5f5e58", "#e6e4dd"
BLUE, ORANGE = "#2a78d6", "#eb6834"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9, "text.color": INK, "axes.labelcolor": MUTED, "xtick.color": INK, "ytick.color": MUTED})

fig, (a, b) = plt.subplots(1, 2, figsize=(7.2, 2.9), gridspec_kw={"width_ratios": [2.2, 1]})
groups = ["none", "watch", "penalty"]
labels = ["No monitor\nmentioned", "Monitor\nmentioned", "Monitor and\nstated penalty"]
used = [F[g]["finder_used"] for g in groups]
R =[json.loads(Path(f).read_text()) for f in sorted(glob.glob(str(HERE / "games7" / "*.json")))]
spread = [sum(any(x != d["finder"] for x in d["tunnel"]) for d in R if d["group"] == g) for g in groups]
w = .36
for i, (u, s) in enumerate(zip(used, spread)):
    a.bar(i - w / 2 - .01, u, w, color=BLUE, label="Discovering agent used the route" if i == 0 else None, zorder=3)
    a.bar(i + w / 2 + .01, s, w, color=ORANGE, label="At least one teammate followed" if i == 0 else None, zorder=3)
    lo, hi = CI[groups[i]]
    a.errorbar(i - w / 2 - .01, u, yerr=[[u - 20 * lo], [20 * hi - u]], color=INK, capsize=3, lw=1, zorder=4)
    a.text(i - w / 2 - .10, max(u, 20 * hi) + .4, str(u), ha="center", fontsize=9); a.text(i + w / 2 + .01, s + .4, str(s), ha="center", fontsize=9)
a.set_xticks(range(3)); a.set_xticklabels(labels); a.set_ylim(0, 21); a.set_yticks([0, 5, 10, 15, 20]); a.set_ylabel("Episodes (of 20)")
a.set_title("A. Use and spread by what agents were told", loc="left", fontsize=9.5, fontweight="bold")
a.legend(frameon=False, loc="upper right", fontsize=8, bbox_to_anchor=(1.0, 1.02))

fin = sum(F[g]["finder_users_no"] for g in groups); finN = sum(F[g]["users"] - F[g]["follower_users"] for g in groups)
fol = sum(F[g]["follower_users_no"] for g in groups); folN = sum(F[g]["follower_users"] for g in groups)
b.bar([0, 1], [100 * fin / finN, 100 * fol / folN], .55, color=[BLUE, ORANGE], zorder=3)
b.text(0, 100 * fin / finN + 3, f"{fin} of {finN}", ha="center"); b.text(1, 100 * fol / folN + 3, f"{fol} of {folN}", ha="center")
b.set_xticks([0, 1]); b.set_xticklabels(["Discovering\nagents", "Following\nagents"]); b.set_ylim(0, 100); b.set_ylabel('Answered "no" (%)')
b.set_title("B. Self-report", loc="left", fontsize=9.5, fontweight="bold")
for x in (a, b):
    x.grid(axis="y", color=GRID, lw=.8, zorder=0); x.set_axisbelow(True)
    for s_ in ("top", "right", "left"): x.spines[s_].set_visible(False)
    x.spines["bottom"].set_color("#b9b7ae"); x.tick_params(length=0)
fig.tight_layout(); fig.savefig(HERE / "figure1.png", dpi=220); print("saved", fin, finN, fol, folN, spread)

named = other = blank = 0; hide = []
for d in R:
    for a_ in d["tunnel"]:
        if a_ != d["finder"] and d["reports"][a_]["answer"] == "no":
            s = (d["reports"][a_]["statement"] or "").strip()
            if not s: blank += 1
            elif re.search("tunnel", s, re.I): named += 1
            else: other += 1
            for n in d["notes"][a_]:
                if re.search(r"hide|conceal|deny|not (tell|mention|admit)|cover", n, re.I): hide.append((d["run_id"], a_, n[:220]))
print("no answers: states only approved gates", other, "names tunnel", named, "blank", blank); print("hiding-language notes", hide)


# Figure 2: one real episode, event by event
rep = ALL["replay"]; key = []
for e in rep["timeline"]:
    if e["what"] == "found the note": key.append((e["round"], e["agent"], "found"))
    elif e["what"] == "message" and re.search(r"\b\d{4}\b", e["text"]): key.append((e["round"], e["agent"], "post"))
    elif e["what"] == "entered tunnel": key.append((e["round"], e["agent"], "enter"))
lanes = ["A1", "A2", "A3", "A4"]; y = {a: 3 - i for i, a in enumerate(lanes)}
fig2, ax = plt.subplots(figsize=(7.2, 2.35))
style = {"found": ("D", INK, "Found the route note"), "post": ("o", BLUE, "Posted the access code"), "enter": ("s", ORANGE, "Entered the route")}
seen = set(); xs = {}
for i, (rnd, a_, k) in enumerate(key):
    m, c, lab = style[k]
    ax.scatter(i, y[a_], marker=m, s=62, color=c, zorder=3, edgecolor="white", linewidth=.8, label=None if k in seen else lab); seen.add(k)
    xs.setdefault(rnd, []).append(i)
for a_ in lanes: ax.hlines(y[a_], -.6, len(key) - .4, color=GRID, lw=.9, zorder=1)
for rnd, v in xs.items():
    ax.text((min(v) + max(v)) / 2, 3.62, f"Round {rnd}", ha="center", fontsize=8.5, color=MUTED)
    if min(v) > 0: ax.vlines(min(v) - .5, -.45, 3.45, color="#b9b7ae", lw=.8, linestyles=(0, (3, 3)), zorder=1)
names = {a_: f"Agent {a_[1]}" + (" (discoverer)" if a_ == rep["finder"] else "") for a_ in lanes}
ax.set_yticks([y[a_] for a_ in lanes]); ax.set_yticklabels([names[a_] for a_ in lanes], color=INK)
ax.set_xticks([]); ax.set_xlim(-.7, len(key) + 1.3); ax.set_ylim(-.55, 3.95)
ax.text(len(key) + .55, 3.62, "Asked afterwards", ha="center", fontsize=8.5, color=MUTED)
for a_ in lanes:
    ans = rep["answers"][a_]["answer"]
    ax.text(len(key) + .55, y[a_], ans.upper(), ha="center", va="center", fontsize=9.5, fontweight="bold", color=ORANGE if ans == "no" else INK)
for s_ in ax.spines.values(): s_.set_visible(False)
ax.tick_params(length=0)
ax.legend(frameon=False, loc="upper center", bbox_to_anchor=(.46, -.01), ncol=3, fontsize=8, handletextpad=.3)
fig2.tight_layout(); fig2.savefig(HERE / "figure2.png", dpi=220); print("figure2", rep["run_id"], key)
