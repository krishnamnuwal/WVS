"""Score the full run and draw the report charts. Reads results/*.csv and
personas/, writes report/*.png and report/stats.json (numbers for report.md).
Nothing is dropped silently: every failed or unparseable reply is counted.

  python analyze.py
"""
import csv, glob, json, re
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

MODEL = "claude-sonnet-5-5"
CONDS = ["full", "demo", "none"]
HELDOUT = {"V24": (1, 2), "V56": (1, 10), "V105": (1, 4), "V76": (1, 6), "V100": (1, 10), "V202": (1, 10)}
EDU = {1: "No formal education", 2: "Incomplete primary", 3: "Complete primary",
       4: "Incomplete secondary (tech.)", 5: "Complete secondary (tech.)",
       6: "Incomplete secondary (univ.-prep.)", 7: "Complete secondary (univ.-prep.)",
       8: "Some university", 9: "University degree"}
# Reference palette slots 1-3 (validated all-pairs), light mode; text in ink tokens.
COLOR = {"full": "#2a78d6", "demo": "#eb6834", "none": "#1baf7a"}
INK, INK2, GRID, SURFACE = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"
OUT = Path("report"); OUT.mkdir(exist_ok=True)
plt.rcParams.update({"figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
                     "text.color": INK, "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
                     "axes.edgecolor": GRID, "axes.spines.top": False, "axes.spines.right": False,
                     "font.size": 10})

bots = {b["bot_id"]: b for b in (json.loads(Path(f).read_text()) for f in sorted(glob.glob("personas/bot_*.json")))}
NUM = re.compile(r"-?\d+(?:\.\d+)?")


def load(stem, cond):
    d = pd.read_csv(f"results/{stem}__{cond}__{MODEL}.csv", dtype={"answer": str}, keep_default_na=False)
    d["condition"] = cond
    return d


def classify(d, lo, hi):
    """status: ok | api_error | no_answer_line | not_a_number | out_of_range ; value: parsed number."""
    status, value = [], []
    for ans, txt in zip(d["answer"], d["reasoning"]):
        if str(txt).startswith("ERROR:"):
            status.append("api_error"); value.append(np.nan); continue
        if not ans.strip():
            status.append("no_answer_line"); value.append(np.nan); continue
        m = NUM.search(ans)
        if not m:
            status.append("not_a_number"); value.append(np.nan); continue
        v = float(m.group())
        if not lo <= v <= hi:
            status.append("out_of_range"); value.append(v); continue
        status.append("ok"); value.append(v)
    d["status"], d["value"] = status, value
    d["truncated"] = d["stop_reason"].astype(str).eq("max_tokens")
    return d


stats = {"runs": []}

# ---------------------------------------------------------------- held-out
rows = []
for var, (lo, hi) in HELDOUT.items():
    for cond in CONDS:
        d = classify(load(f"heldout_{var}", cond), lo, hi)
        d["truth"] = [bots[b]["heldout"].get(var) for b in d["bot_id"]]
        stats["runs"].append(dict(run=f"heldout_{var}", condition=cond, calls=len(d),
                                  **d["status"].value_counts().reindex(
                                      ["ok", "api_error", "no_answer_line", "not_a_number", "out_of_range"],
                                      fill_value=0).astype(int).to_dict(),
                                  truncated=int(d["truncated"].sum())))
        m = d[(d["status"] == "ok") & d["truth"].notna()]
        p, t = m["value"].to_numpy(), m["truth"].to_numpy(dtype=float)
        corr = float(np.corrcoef(p, t)[0, 1]) if len(set(p)) > 1 and len(set(t)) > 1 else None
        rows.append(dict(var=var, condition=cond, n_scored=len(m),
                         n_unscorable=int((d["status"] != "ok").sum()),
                         n_no_truth=int(d["truth"].isna().sum()),
                         exact=float(np.mean(p == t)), mae=float(np.mean(np.abs(p - t))), corr=corr,
                         human_mean=float(t.mean()), human_sd=float(t.std()),
                         bot_mean=float(p.mean()), bot_sd=float(p.std()),
                         bot_distinct=int(len(set(p)))))
        if cond == "full":   # constant baseline: always answer the humans' most common value (in-sample)
            mode = pd.Series(t).mode().iloc[0]
            rows[-1]["baseline_mode"] = float(mode)
            rows[-1]["baseline_exact"] = float(np.mean(t == mode))
            rows[-1]["baseline_median"] = float(np.median(t))       # the constant that minimises MAE
            rows[-1]["baseline_mae"] = float(np.mean(np.abs(t - np.median(t))))
ho = pd.DataFrame(rows)
stats["heldout"] = ho.to_dict("records")

fig, axes = plt.subplots(1, 6, figsize=(13, 3.6), sharey=False)
for ax, var in zip(axes, HELDOUT):
    sub = ho[ho["var"] == var]
    x = np.arange(len(CONDS))
    ax.bar(x, sub["mae"], width=0.6, color=[COLOR[c] for c in CONDS], edgecolor=SURFACE, linewidth=2)
    base = ho[(ho["var"] == var) & (ho["condition"] == "full")]["baseline_mae"].iloc[0]
    ax.axhline(base, color=INK, linewidth=1, linestyle="--")
    ax.set_xticks(x, CONDS); ax.set_title(var, color=INK, fontsize=11)
    ax.grid(axis="y", color=GRID, linewidth=0.8); ax.set_axisbelow(True)
    for xi, v in zip(x, sub["mae"]):
        ax.text(xi, v, f"{v:.2f}", ha="center", va="bottom", fontsize=8, color=INK2)
axes[0].set_ylabel("Mean absolute error")
fig.suptitle("Held-out questions: mean absolute error by condition (dashed line = always answer the humans' median)",
             fontsize=10, color=INK)
fig.tight_layout(); fig.savefig(OUT / "heldout_mae.png", dpi=150); plt.close(fig)

fig, axes = plt.subplots(1, 6, figsize=(13, 3.6))
for ax, var in zip(axes, HELDOUT):
    sub = ho[ho["var"] == var]
    labels = ["human"] + CONDS
    means = [sub["human_mean"].iloc[0]] + list(sub["bot_mean"])
    sds = [sub["human_sd"].iloc[0]] + list(sub["bot_sd"])
    cols = ["#8a8985"] + [COLOR[c] for c in CONDS]
    x = np.arange(4)
    ax.errorbar(x, means, yerr=sds, fmt="none", ecolor=cols, elinewidth=2, capsize=0)
    ax.scatter(x, means, s=60, c=cols, edgecolors=SURFACE, linewidths=2, zorder=3)
    lo, hi = HELDOUT[var]; ax.set_ylim(lo - 0.5, hi + 0.5)
    ax.set_xticks(x, labels, rotation=30); ax.set_title(var, color=INK, fontsize=11)
    ax.grid(axis="y", color=GRID, linewidth=0.8); ax.set_axisbelow(True)
axes[0].set_ylabel("Answer (mean ± 1 SD)")
fig.suptitle("Held-out questions: human vs bot answer distributions", fontsize=10, color=INK)
fig.tight_layout(); fig.savefig(OUT / "heldout_means.png", dpi=150); plt.close(fig)

# ---------------------------------------------------------------- p-beauty
pb = []
for cond in CONDS:
    d = classify(load("p_beauty", cond), 0, 100)
    stats["runs"].append(dict(run="p_beauty", condition=cond, calls=len(d),
                              **d["status"].value_counts().reindex(
                                  ["ok", "api_error", "no_answer_line", "not_a_number", "out_of_range"],
                                  fill_value=0).astype(int).to_dict(),
                              truncated=int(d["truncated"].sum())))
    pb.append(d)
pb = pd.concat(pb, ignore_index=True)
pb["V248"] = [bots[b]["raw"].get("V248") for b in pb["bot_id"]]
pb["V24"] = [bots[b]["raw"].get("V24") for b in pb["bot_id"]]
txt = pb["reasoning"].astype(str)
pb["r_50_33"] = txt.str.contains(r"\b50\b") & txt.str.contains(r"\b33(?:\.\d+)?\b")      # strict: both numerals
# broad: strict, or "50" (also Hindi पचास / "fifty") together with "two-thirds" in English, Hindi or romanized Hindi
pb["r_50_33_any"] = pb["r_50_33"] | (txt.str.contains(r"\b50\b|पचास|fifty", case=False)
                                     & txt.str.contains(r"two[- ]thirds|2/3|दो[- ]तिहाई|do[- ]tihai", case=False))
pb["r_hindi_script"] = txt.str.contains(r"[\u0900-\u097F]")
pb["r_ai_players"] = txt.str.contains(r"\bAI\b|language model|\bLLM", regex=True)
pb["r_jargon"] = txt.str.contains(r"(?i)nash|equilibri|game theor|keynes|beauty contest|level[- ]?\d|k-level|iterat")
pb["r_experiments"] = txt.str.contains(r"(?i)experiment|studies|research|typically|usually (?:land|find|end)")
ok = pb[pb["status"] == "ok"]

summ = {}
for cond in CONDS:
    g = ok[ok["condition"] == cond]["value"]
    summ[cond] = dict(n=int(len(g)), mean=float(g.mean()), median=float(g.median()), sd=float(g.std(ddof=1)),
                      share_20_26=float(g.between(20, 26).mean()), share_0=float((g == 0).mean()),
                      share_ge50=float((g >= 50).mean()), min=float(g.min()), max=float(g.max()),
                      share_50_33=float(pb[pb["condition"] == cond]["r_50_33"].mean()),
                      share_jargon=float(pb[pb["condition"] == cond]["r_jargon"].mean()),
                      share_experiments=float(pb[pb["condition"] == cond]["r_experiments"].mean()),
                      n_50_33=int(pb[pb["condition"] == cond]["r_50_33"].sum()),
                      n_50_33_any=int(pb[pb["condition"] == cond]["r_50_33_any"].sum()),
                      n_hindi_script=int(pb[pb["condition"] == cond]["r_hindi_script"].sum()),
                      n_ai_players=int(pb[pb["condition"] == cond]["r_ai_players"].sum()),
                      calls=int((pb["condition"] == cond).sum()))
    if cond != "none":    # how much of the spread is between bots (persona) vs within a bot (resampling)
        bm = ok[ok["condition"] == cond].groupby("bot_id")["value"]
        within = float(bm.var(ddof=1).mean()); between = float(bm.mean().var(ddof=1))
        summ[cond]["var_between_bots"] = between; summ[cond]["var_within_bot"] = within
        summ[cond]["share_between"] = between / (between + within)
stats["p_beauty"] = summ

rng = np.random.default_rng(0)
def boot_diff(cond, B=5000):
    """Mean(cond) - mean(none), 95% CI; resample bots (clusters of 5) for persona, draws for none."""
    a = ok[ok["condition"] == cond].groupby("bot_id")["value"].apply(np.array).to_list()
    b = ok[ok["condition"] == "none"]["value"].to_numpy()
    est = np.mean(np.concatenate(a)) - b.mean()
    ds = []
    for _ in range(B):
        aa = np.concatenate([a[i] for i in rng.integers(0, len(a), len(a))])
        ds.append(aa.mean() - rng.choice(b, len(b)).mean())
    return dict(diff=float(est), lo=float(np.percentile(ds, 2.5)), hi=float(np.percentile(ds, 97.5)))
stats["p_beauty_vs_none"] = {c: boot_diff(c) for c in ["full", "demo"]}

# histograms: one shared axis, step outlines, bins of width 2
fig, ax = plt.subplots(figsize=(9, 4.2))
bins = np.arange(0, 102, 2)
for cond in CONDS:
    g = ok[ok["condition"] == cond]["value"]
    ax.hist(g, bins=bins, histtype="step", linewidth=2, color=COLOR[cond],
            weights=np.full(len(g), 100 / len(g)),
            label=f"{cond}  (n={len(g)}, mean {g.mean():.1f}, median {g.median():.0f})")
ax.axvspan(20, 26, color=GRID, alpha=0.6, zorder=0, linewidth=0)
ax.text(23, ax.get_ylim()[1] * 0.97, "20–26", ha="center", va="top", fontsize=8, color=INK2)
ax.set_xlim(0, 100); ax.set_xlabel("Guess (0–100)"); ax.set_ylabel("% of guesses in condition")
ax.grid(axis="y", color=GRID, linewidth=0.8); ax.set_axisbelow(True)
ax.legend(frameon=False, fontsize=9, labelcolor=INK)
ax.set_title("p-beauty contest (p = 2/3): distribution of guesses by condition", color=INK, fontsize=11)
fig.tight_layout(); fig.savefig(OUT / "pbeauty_hist.png", dpi=150); plt.close(fig)

# guesses by education and trust (bot-level means from raw V248 / V24)
by_edu, by_trust = {}, {}
for cond in ["full", "demo"]:
    bm = ok[ok["condition"] == cond].groupby("bot_id").agg(guess=("value", "mean"), V248=("V248", "first"),
                                                             V24=("V24", "first"))
    e = bm.dropna(subset=["V248"])
    by_edu[cond] = {int(k): dict(n_bots=int(len(v)), mean=float(v["guess"].mean()), sd=float(v["guess"].std(ddof=1)) if len(v) > 1 else None)
                    for k, v in e.groupby("V248")}
    by_edu[cond + "_spearman"] = float(e["guess"].rank().corr(e["V248"].rank()))
    t = bm.dropna(subset=["V24"])
    by_trust[cond] = {int(k): dict(n_bots=int(len(v)), mean=float(v["guess"].mean()), sd=float(v["guess"].std(ddof=1)))
                      for k, v in t.groupby("V24")}
stats["by_education"], stats["by_trust"] = by_edu, by_trust

r5033 = {}
for cond in CONDS:
    s = pb[pb["condition"] == cond]
    r5033[cond] = {int(k): dict(replies=int(len(v)), n_50_33=int(v["r_50_33"].sum()), share=float(v["r_50_33"].mean()),
                                n_50_33_any=int(v["r_50_33_any"].sum()), n_hindi_script=int(v["r_hindi_script"].sum()))
                   for k, v in s.dropna(subset=["V248"]).groupby("V248")}
stats["r_50_33_by_edu"] = r5033

fig, axes = plt.subplots(1, 2, figsize=(12, 4.2), sharey=True)
for ax, cond in zip(axes, ["full", "demo"]):
    bm = ok[ok["condition"] == cond].groupby("bot_id").agg(guess=("value", "mean"), V248=("V248", "first")).dropna()
    jit = rng.uniform(-0.18, 0.18, len(bm))
    ax.scatter(bm["V248"] + jit, bm["guess"], s=22, color=COLOR[cond], alpha=0.55, edgecolors="none")
    mm = bm.groupby("V248")["guess"].mean()
    ax.plot(mm.index, mm.values, color=INK, linewidth=2, marker="o", markersize=8,
            markeredgecolor=SURFACE, markeredgewidth=2, label="mean per level")
    ax.set_xticks(range(1, 10), [str(i) for i in range(1, 10)])
    ax.set_xlabel("Education, V248 (1 = no formal education … 9 = university degree)")
    ax.set_title(f"{cond} persona: each dot = one bot's mean of 5 guesses", color=INK, fontsize=10)
    ax.grid(axis="y", color=GRID, linewidth=0.8); ax.set_axisbelow(True)
    nm = ok[ok["condition"] == "none"]["value"].mean()
    ax.axhline(nm, color=COLOR["none"], linestyle="--", linewidth=1.5, label=f"no-persona mean ({nm:.1f})")
    ax.legend(frameon=False, fontsize=8, labelcolor=INK)
axes[0].set_ylabel("Guess")
fig.tight_layout(); fig.savefig(OUT / "pbeauty_by_education.png", dpi=150); plt.close(fig)

fig, ax = plt.subplots(figsize=(6.5, 3.8))
labels = {1: "Most people can\nbe trusted (V24=1)", 2: "Need to be very\ncareful (V24=2)"}
for i, cond in enumerate(["full", "demo"]):
    bm = ok[ok["condition"] == cond].groupby("bot_id").agg(guess=("value", "mean"), V24=("V24", "first")).dropna()
    for k in (1, 2):
        g = bm[bm["V24"] == k]["guess"]
        x = k + (i - 0.5) * 0.3
        ax.scatter(x + rng.uniform(-0.05, 0.05, len(g)), g, s=18, color=COLOR[cond], alpha=0.5, edgecolors="none")
        ax.plot([x - 0.1, x + 0.1], [g.mean()] * 2, color=INK, linewidth=2.5)
    ax.scatter([], [], color=COLOR[cond], label=cond)
ax.set_xticks([1, 2], [labels[1], labels[2]]); ax.set_ylabel("Bot mean guess")
ax.set_title("p-beauty guesses by generalized trust (black bar = mean)", color=INK, fontsize=10)
ax.grid(axis="y", color=GRID, linewidth=0.8); ax.set_axisbelow(True); ax.legend(frameon=False, fontsize=8)
fig.tight_layout(); fig.savefig(OUT / "pbeauty_by_trust.png", dpi=150); plt.close(fig)

# five verbatim examples: full condition, repeat 0, first bot (by id) at education levels 1, 3, 5, 7, 9
ex = []
f0 = pb[(pb["condition"] == "full") & (pb["repeat"] == 0)].sort_values("bot_id")
for lvl in (1, 3, 5, 7, 9):
    r = f0[f0["V248"] == lvl].iloc[0]
    ex.append(dict(bot_id=r["bot_id"], V248=lvl, edu=EDU[lvl], answer=r["answer"], text=r["reasoning"]))
stats["examples"] = ex

# ---------------------------------------------------------------- spend
log = pd.read_csv("results/usage_log.csv", keep_default_na=False)
for c in ["input_tokens", "output_tokens"]:
    log[c] = pd.to_numeric(log[c], errors="coerce").fillna(0).astype(int)
log["cost_usd"] = pd.to_numeric(log["cost_usd"], errors="coerce").fillna(0)
log["attempts"] = pd.to_numeric(log["attempts"], errors="coerce")
stats["usage"] = dict(logged_calls=int(len(log)), errors=int((log["error"] != "").sum()),
                      retried_calls=int((log["attempts"] > 1).sum()),
                      input_tokens=int(log["input_tokens"].sum()), output_tokens=int(log["output_tokens"].sum()),
                      cost_usd=float(log["cost_usd"].sum()),
                      first_call=log["time_utc"].min(), last_call=log["time_utc"].max())
Path(OUT / "stats.json").write_text(json.dumps(stats, indent=1, default=str))
print(json.dumps({k: stats[k] for k in ["p_beauty", "p_beauty_vs_none", "usage"]}, indent=1))
print(ho.round(3).to_string())
print(pd.DataFrame(stats["runs"]).to_string())
