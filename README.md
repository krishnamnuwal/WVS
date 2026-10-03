# Virtual India: persona bots, batch 1 (100 bots)

Each bot is one real WVS-6 India respondent, copied whole. No traits are mixed between people.

0. Setup: `python3 -m venv .venv && .venv/bin/pip install anthropic python-dotenv pandas numpy matplotlib`,
   then put `ANTHROPIC_API_KEY=...` in `.env` (git-ignored; `run_game.py` loads it, nothing else does).
1. `python build_personas.py --csv WV6_Data_sav_v20201117.csv --n 100`  (use `--n 4078` for everyone)
2. `python validate_heldout.py make`, then run each `games/heldout_*.txt` with `run_game.py`
   under `--condition full`, `demo` and `none`, and score with `validate_heldout.py score`.
3. `python run_game.py --game games/<experiment>.txt --condition full --repeats 5`
4. `python run_all.py` does steps 2-3 for all six held-out questions (1 repeat) and `p_beauty` (5 repeats)
   under all three conditions; `python analyze.py` then scores everything and draws `report/*.png`.

- `codebook.py`: variable -> sentence and labels. Check labels against the official WVS-6 codebook before publishing.
- `personas/bot_XXX.json`: full profile, demographics-only profile, held-out answers, and the untouched raw row (442 columns).
- `personas/_representativeness.csv`: the 100 bots against all 4,078.
- `games/`: paste original experiment instructions word for word. Nothing about strategy is added by the runner.
- `run_game.py`: one fresh API call per bot and repeat. Resumable (skips bot/repeat pairs already in the output CSV,
  failures included), retries rate-limit/server errors with backoff, logs every call to `results/usage_log.csv`,
  and stops on `--max-cost` (USD) or `--max-fail-rate`. `--limit N` runs the first N bots into a separate `__smokeN` file.
  `claude-sonnet-5-5` does not accept `temperature`, so it runs at the default (1.0).
- `analyze.py`: counts every failed or unparseable reply instead of skipping it (`validate_heldout.py score` skips them).

Status: batch 1 has been run once on `claude-sonnet-5-5` (2 October 2026; 3,300 calls, 0 failed, 0 unparseable, $12.60).
Results and limitations are in `report.md`. Still to do before publishing: verify `codebook.py` against the official
codebook (V100 and V76 take only some scale values in this sample), and replace `games/p_beauty.txt`, which is
placeholder wording, with the text of a real Indian experiment.
