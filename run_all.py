"""Run the full plan: 6 held-out questions (1 repeat) and p_beauty (5 repeats),
each under full, demo and none. Resumable: re-running skips finished calls.
Stops if total logged spend passes MAX_COST or more than MAX_FAIL of calls fail.

  python run_all.py
"""
import csv, subprocess, sys
from pathlib import Path

MODEL, WORKERS, MAX_COST, MAX_FAIL = "claude-sonnet-5-5", 8, 25.0, 0.05
HELDOUT = ["V24", "V56", "V105", "V76", "V100", "V202"]
RUNS = [(f"games/heldout_{v}.txt", 1) for v in HELDOUT] + [("games/p_beauty.txt", 5)]


def overall_fail_rate():
    log = Path("results/usage_log.csv")
    rows = list(csv.DictReader(open(log))) if log.exists() else []
    return (sum(bool(r["error"]) for r in rows) / len(rows)) if rows else 0.0, len(rows)


for game, repeats in RUNS:
    for cond in ["full", "demo", "none"]:
        cmd = [sys.executable, "run_game.py", "--game", game, "--condition", cond, "--model", MODEL,
               "--repeats", str(repeats), "--workers", str(WORKERS), "--max-cost", str(MAX_COST),
               "--max-fail-rate", str(MAX_FAIL)]
        print(">>", " ".join(cmd[1:]), flush=True)
        rc = subprocess.call(cmd)
        if rc:
            sys.exit(f"STOPPED after {game} {cond} (exit {rc})")
        rate, n = overall_fail_rate()
        if rate > MAX_FAIL:
            sys.exit(f"STOPPED: {rate:.1%} of {n} logged calls failed")
print("ALL RUNS DONE")
