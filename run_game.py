"""Run one experiment on every bot. One bot = one fresh, independent API call
(no shared chat history), with the persona as the system prompt and the
experiment's original instructions as the only user message.

Nothing about game theory, strategy, or how to reason is added anywhere.

  python run_game.py --game games/p_beauty.txt --condition full --dry-run
  ANTHROPIC_API_KEY=... python run_game.py --game games/p_beauty.txt --condition full

--condition  full | demo | none   (none = no persona at all: the raw-LLM baseline)
--repeats    independent draws per bot (LLM answers are random; 5+ recommended)
--limit      only the first N bots (smoke test; written to a separate __smokeN file)
Answers land in results/<game>__<condition>__<model>.csv. Re-running resumes:
(bot, repeat) pairs already in that file are skipped. Every call, including
failures, is appended to results/usage_log.csv with its token counts.
"""
import argparse, csv, json, os, re, glob, random, sys, time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).with_name(".env"))   # key stays in .env, never exported globally

SYSTEM = """You are the person described below. This is a record of what you told an interviewer about yourself and your life.

{persona}

For everything that follows, respond as this person would: with their circumstances, their schooling, their habits of thought and their way of seeing other people. You are not an assistant and you are not an expert; you are this one person, making a decision that affects you."""

ANSWER_FORMAT = """

First say, in a few sentences and in your own words, what you are thinking. Then give your final choice on the last line in exactly this form:
ANSWER: <your choice>"""


PRICES = {"claude-sonnet-5-5": (2.00, 10.00)}   # USD per 1M input / output tokens
USAGE_LOG = Path("results") / "usage_log.csv"
USAGE_COLS = ["time_utc", "game", "condition", "model", "bot_id", "repeat", "attempts",
              "input_tokens", "output_tokens", "stop_reason", "cost_usd", "error"]
_client = None


def call_anthropic(model, system, user, temperature):
    global _client
    import anthropic
    # Current Claude models / SDK 1.x reject `temperature`; sampling runs at the default (1.0).
    if temperature != 1.0:
        raise SystemExit(f"--temperature {temperature} is not supported for {model}; only the default 1.0 is")
    if _client is None:
        _client = anthropic.Anthropic(max_retries=0)    # retries are done (and counted) in with_backoff
    kw = dict(model=model, max_tokens=600,
              messages=[{"role": "user", "content": user}])
    if system:
        kw["system"] = system
    msg = _client.messages.create(**kw)
    text = "".join(b.text for b in msg.content if b.type == "text")   # skip thinking blocks
    u = msg.usage
    return text, dict(input_tokens=u.input_tokens, output_tokens=u.output_tokens, stop_reason=msg.stop_reason)


def call_openai_compatible(model, system, user, temperature):
    from openai import OpenAI        # also works for local/open models via OPENAI_BASE_URL
    msgs = ([{"role": "system", "content": system}] if system else []) + [{"role": "user", "content": user}]
    r = OpenAI().chat.completions.create(model=model, messages=msgs, temperature=temperature, max_tokens=600)
    return r.choices[0].message.content, dict(input_tokens=r.usage.prompt_tokens, output_tokens=r.usage.completion_tokens,
                                              stop_reason=r.choices[0].finish_reason)


def retryable(e):
    """Rate limits (429), overload (529), server errors (5xx) and dropped connections."""
    status = getattr(e, "status_code", None)
    if status is not None:
        return status == 429 or status >= 500
    return type(e).__name__ in ("APIConnectionError", "APITimeoutError", "RateLimitError")


def with_backoff(fn, tries=8, base=2.0, cap=90.0):
    for attempt in range(1, tries + 1):
        try:
            return fn() + (attempt,)
        except Exception as e:
            if not retryable(e) or attempt == tries:
                raise RuntimeError(f"{type(e).__name__} after {attempt} attempt(s): {e}") from e
            retry_after = getattr(getattr(e, "response", None), "headers", {}).get("retry-after")
            delay = float(retry_after) if retry_after else min(cap, base * 2 ** (attempt - 1))
            time.sleep(delay + random.uniform(0, 1))


def cost(model, usage):
    pin, pout = PRICES.get(model, (0.0, 0.0))
    return (usage.get("input_tokens", 0) * pin + usage.get("output_tokens", 0) * pout) / 1e6


def logged_spend():
    if not USAGE_LOG.exists():
        return 0.0
    return sum(float(r["cost_usd"] or 0) for r in csv.DictReader(open(USAGE_LOG)))


def parse(text):
    m = re.findall(r"ANSWER:\s*(.+)", text)
    return m[-1].strip() if m else ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--game", required=True)
    ap.add_argument("--personas", default="personas")
    ap.add_argument("--condition", choices=["full", "demo", "none"], default="full")
    ap.add_argument("--provider", choices=["anthropic", "openai"], default="anthropic")
    ap.add_argument("--model", default=os.environ.get("MODEL", "claude-sonnet-5-5"))
    ap.add_argument("--repeats", type=int, default=1)
    ap.add_argument("--temperature", type=float, default=1.0)
    ap.add_argument("--vars", nargs="*", default=["n_others=99", "prize=Rs. 500"])
    ap.add_argument("--limit", type=int, default=None, help="only the first N bots (smoke tests)")
    ap.add_argument("--workers", type=int, default=1, help="parallel API calls")
    ap.add_argument("--max-cost", type=float, default=None,
                    help="stop (exit 3) once total spend in results/usage_log.csv passes this many USD")
    ap.add_argument("--max-fail-rate", type=float, default=0.05,
                    help="stop (exit 4) if more than this share of this run's calls fail (checked after 40 calls)")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    user = Path(a.game).read_text().strip().format(**dict(v.split("=", 1) for v in a.vars)) + ANSWER_FORMAT
    call = call_anthropic if a.provider == "anthropic" else call_openai_compatible
    bots = [json.loads(Path(f).read_text()) for f in sorted(glob.glob(f"{a.personas}/bot_*.json"))]
    if a.limit:
        bots = bots[:a.limit]

    if a.dry_run:
        b = bots[0]
        print("=== SYSTEM ===\n" + (SYSTEM.format(persona=b["persona_" + a.condition]) if a.condition != "none" else "(none)"))
        print("\n=== USER ===\n" + user + f"\n\n[{len(bots)} bots x {a.repeats} repeats would be sent]")
        return

    Path("results").mkdir(exist_ok=True)
    smoke = f"__smoke{a.limit}" if a.limit else ""    # keep smoke tests out of the real result files
    out = Path("results") / f"{Path(a.game).stem}__{a.condition}__{a.model.replace('/', '_')}{smoke}.csv"
    cols = ["bot_id", "respondent_id", "repeat", "answer", "reasoning", "input_tokens", "output_tokens", "stop_reason"]

    if a.limit and out.exists():
        out.unlink()                                    # smoke tests always start fresh
    done = set()
    if out.exists():                                    # resume: skip (bot, repeat) pairs already written,
        done = {(r["bot_id"], int(r["repeat"])) for r in csv.DictReader(open(out))}   # failures included
    todo = [(b, r) for b in bots for r in range(a.repeats) if (b["bot_id"], r) not in done]
    print(f"{out}: {len(done)} already done, {len(todo)} to run", flush=True)

    spent = logged_spend()
    if a.max_cost is not None and spent > a.max_cost:
        print(f"STOP: logged spend ${spent:.2f} already exceeds --max-cost ${a.max_cost:.2f}"); sys.exit(3)

    def job(b, r):
        system = SYSTEM.format(persona=b["persona_" + a.condition]) if a.condition != "none" else None
        try:
            text, usage, attempts = with_backoff(lambda: call(a.model, system, user, a.temperature))
            return b, r, text, usage, attempts, ""
        except Exception as e:                          # keep failures visible, never silently drop a bot
            return b, r, f"ERROR: {e}", {}, "", str(e)

    new_file = not out.exists()
    log_new = not USAGE_LOG.exists()
    n = fails = 0
    stop_code = 0
    with open(out, "a", newline="") as f, open(USAGE_LOG, "a", newline="") as lf, \
            ThreadPoolExecutor(max_workers=a.workers) as pool:
        w = csv.writer(f); lw = csv.writer(lf)
        if new_file:
            w.writerow(cols)
        if log_new:
            lw.writerow(USAGE_COLS)
        futures = [pool.submit(job, b, r) for b, r in todo]
        for fut in as_completed(futures):
            if fut.cancelled():
                continue                                # never started, not billed
            b, r, text, usage, attempts, err = fut.result()
            c = cost(a.model, usage)
            w.writerow([b["bot_id"], b["respondent_id"], r, parse(text), text] +
                       [usage.get(k, "") for k in ("input_tokens", "output_tokens", "stop_reason")]); f.flush()
            lw.writerow([datetime.now(timezone.utc).isoformat(timespec="seconds"), Path(a.game).stem, a.condition,
                         a.model, b["bot_id"], r, attempts, usage.get("input_tokens", ""),
                         usage.get("output_tokens", ""), usage.get("stop_reason", ""), f"{c:.6f}", err]); lf.flush()
            n += 1; fails += bool(err); spent += c
            if n % 50 == 0:
                print(f"  {n}/{len(todo)} calls, {fails} failed, total spend ${spent:.2f}", flush=True)
            if stop_code:
                continue                                # draining calls already in flight; still logged
            if a.max_cost is not None and spent > a.max_cost:
                print(f"STOP: total spend ${spent:.2f} passed --max-cost ${a.max_cost:.2f}"); stop_code = 3
            elif n >= 40 and fails / n > a.max_fail_rate:
                print(f"STOP: {fails}/{n} calls failed (> {a.max_fail_rate:.0%})"); stop_code = 4
            if stop_code:
                for other in futures:
                    other.cancel()
    print(f"wrote {out}: {n} new calls, {fails} failed, total logged spend ${spent:.2f}")
    if stop_code:
        sys.exit(stop_code)

if __name__ == "__main__":
    main()
