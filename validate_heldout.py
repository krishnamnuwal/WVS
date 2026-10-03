"""Step 0 before any game: can the bot recover answers its own respondent gave
but which were hidden from the persona?  Writes games/heldout_<VAR>.txt question
files (run them with run_game.py), then scores results against the truth.

  python validate_heldout.py make
  python run_game.py --game games/heldout_V24.txt --condition full   (and demo, none)
  python validate_heldout.py score results/heldout_V24__full__<model>.csv V24
"""
import sys, json, glob, csv
from pathlib import Path
import numpy as np

Q = {
 "V24": "Generally speaking, would you say that most people can be trusted, or that you need to be very careful in dealing with people? Answer 1 for 'most people can be trusted' or 2 for 'need to be very careful'.",
 "V56": "Do you think most people would try to take advantage of you if they got a chance, or would they try to be fair? Answer with a number from 1 (people would try to take advantage of you) to 10 (people would try to be fair).",
 "V105": "How much do you trust people you meet for the first time? Answer 1 (trust completely), 2 (trust somewhat), 3 (do not trust very much) or 4 (do not trust at all).",
 "V76": "Here is a description of a person: 'Adventure and taking risks are important to this person; to have an exciting life.' How much is this person like you? Answer 1 (very much like me), 2 (like me), 3 (somewhat like me), 4 (a little like me), 5 (not like me) or 6 (not at all like me).",
 "V100": "Where do you place your view on this scale? 1 means 'In the long run, hard work usually brings a better life' and 10 means 'Hard work doesn't generally bring success - it's more a matter of luck and connections'. Answer with a number from 1 to 10.",
 "V202": "Is someone accepting a bribe in the course of their duties justifiable? Answer with a number from 1 (never justifiable) to 10 (always justifiable).",
}

def make():
    for v, q in Q.items():
        Path(f"games/heldout_{v}.txt").write_text(q + "\n")
    print("wrote", len(Q), "question files to games/")

def score(path, var):
    truth = {json.loads(Path(f).read_text())["bot_id"]: json.loads(Path(f).read_text())["heldout"].get(var)
             for f in glob.glob("personas/bot_*.json")}
    pred, true = [], []
    for r in csv.DictReader(open(path)):
        t = truth.get(r["bot_id"])
        try: p = float(r["answer"].split()[0])
        except Exception: continue
        if t is None or t < 0: continue
        pred.append(p); true.append(t)
    pred, true = np.array(pred), np.array(true)
    print(f"{var}: n={len(true)}  exact match={np.mean(pred == true)*100:.1f}%  "
          f"mean abs error={np.mean(np.abs(pred-true)):.2f}  "
          f"corr={np.corrcoef(pred, true)[0,1]:.2f}" if len(set(pred)) > 1 and len(set(true)) > 1 else f"{var}: n={len(true)} exact={np.mean(pred==true)*100:.1f}% (no variance for corr)")
    print(f"   human distribution: mean={true.mean():.2f} sd={true.std():.2f} | bot distribution: mean={pred.mean():.2f} sd={pred.std():.2f}")

if __name__ == "__main__":
    make() if sys.argv[1] == "make" else score(sys.argv[2], sys.argv[3])
