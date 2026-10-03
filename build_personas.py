"""Build N persona bots as 1-to-1 copies of real WVS-6 India respondents.

Each bot = one real respondent row, never mixed with another row, so every
correlation between the answers is whatever it was in that person.
Outputs, per bot:  personas/bot_XXX.json  with
  respondent_id   WVS interview number (V3) - traceable back to the source row
  raw             the full, untouched WVS row (all columns)
  persona_full    first-person profile text rendered from the codebook
  persona_demo    demographics-only profile (baseline condition)
  heldout         answers withheld from persona_full, for validation
Usage: python build_personas.py --csv WV6_Data_sav_v20201117.csv --n 100
"""
import argparse, json, math
from pathlib import Path
import numpy as np, pandas as pd
from codebook import CODEBOOK, STATES_IN_CODE_ORDER, STATE_COUNTS

INDIA = 356
DEMO_VARS = ["V240", "V242", "V256", "V253", "V144", "V57", "V58", "V248", "V255", "V229", "V238", "V239"]
# Withheld from the persona and asked back to the bot as a validation test.
DEFAULT_HELDOUT = ["V24", "V56", "V105", "V76", "V100", "V202"]


def load_india(csv):
    df = pd.read_csv(csv, low_memory=False)
    return df[df["V2"] == INDIA].reset_index(drop=True)


def state_map(df):
    codes = sorted(df["V256"].dropna().unique())
    counts = [int((df["V256"] == c).sum()) for c in codes]
    assert counts == STATE_COUNTS, "state codes do not line up with the published table"
    return dict(zip(codes, STATES_IN_CODE_ORDER))


def pick_rows(df, n):
    """Systematic sample from a sorted frame (implicit stratification by state,
    religion, settlement size, gender, age). Real rows, without replacement."""
    order = df.sort_values(["V256", "V144", "V253", "V240", "V242"], kind="stable").index.to_numpy()
    step = len(order) / n
    return [int(order[int(math.floor(step * (i + 0.5)))]) for i in range(n)]


def render(row, smap, skip=()):
    out, section = [], None
    for sec, var, tmpl, labels in CODEBOOK:
        if var in skip or var not in row.index:
            continue
        val = row[var]
        if pd.isna(val) or val < 0:
            continue                       # unanswered: say nothing, invent nothing
        val = int(val)
        if labels == "STATE":
            text = smap.get(val)
        elif labels is None:
            text = str(val)
        else:
            text = labels.get(val)
        if text is None:
            continue                       # code not in codebook: omit
        if var == "V58":
            line = "I have no children." if val == 0 else ("I have 1 child." if val == 1 else f"I have {val} children.")
        else:
            line = " ".join(tmpl.format(v=text).split())
        if sec != section:
            out.append(f"\n[{sec}]")
            section = sec
        out.append("- " + line)
    return "\n".join(out).strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", required=True)
    ap.add_argument("--n", type=int, default=100)
    ap.add_argument("--out", default="personas")
    ap.add_argument("--heldout", nargs="*", default=DEFAULT_HELDOUT)
    a = ap.parse_args()

    df = load_india(a.csv)
    smap = state_map(df)
    rows = pick_rows(df, a.n)
    assert len(set(rows)) == a.n
    out = Path(a.out); out.mkdir(exist_ok=True)
    non_demo = [v for _, v, _, _ in CODEBOOK if v not in DEMO_VARS]

    for k, idx in enumerate(rows, 1):
        r = df.loc[idx]
        raw = {c: (None if pd.isna(v) else (v.item() if hasattr(v, "item") else v)) for c, v in r.items()}
        bot = {
            "bot_id": f"bot_{k:03d}",
            "respondent_id": raw.get("V3"),
            "source_row_in_india_subset": idx,
            "persona_full": render(r, smap, skip=a.heldout),
            "persona_demo": render(r, smap, skip=non_demo),
            "heldout": {v: raw.get(v) for v in a.heldout},
            "raw": raw,
        }
        (out / f"{bot['bot_id']}.json").write_text(json.dumps(bot, indent=1, ensure_ascii=False))

    # representativeness check: the N bots vs all 4,078
    sub = df.loc[rows]
    rep = []
    for name, f in [("women %", lambda d: (d.V240 == 2).mean() * 100),
                    ("mean age", lambda d: d.V242[d.V242 > 0].mean()),
                    ("no formal education %", lambda d: (d.V248 == 1).mean() * 100),
                    ("university degree %", lambda d: (d.V248 == 9).mean() * 100),
                    ("place under 5,000 people %", lambda d: d.V253.isin([1, 2]).mean() * 100),
                    ("Hindu %", lambda d: (d.V144 == 60000000).mean() * 100),
                    ("Muslim %", lambda d: (d.V144 == 50000000).mean() * 100),
                    ("trusting (V24=1), % of valid", lambda d: (d.V24[d.V24 > 0] == 1).mean() * 100),
                    ("mean income step", lambda d: d.V239[d.V239 > 0].mean()),
                    ("states covered", lambda d: d.V256.nunique())]:
        rep.append((name, round(float(f(df)), 1), round(float(f(sub)), 1)))
    t = pd.DataFrame(rep, columns=["measure", "all_4078", f"bots_{a.n}"])
    t.to_csv(out / "_representativeness.csv", index=False)
    print(t.to_string(index=False))
    print(f"\nwrote {a.n} bots to {out}/")

if __name__ == "__main__":
    main()
