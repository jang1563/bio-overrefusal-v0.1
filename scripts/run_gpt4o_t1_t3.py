#!/usr/bin/env python3
"""
run_gpt4o_t1_t3.py — Run GPT-4o on T1-T3 queries to complete full N=201 coverage.

Saves to results/raw_gpt-4o_t1_t3.jsonl (does not overwrite existing T4+T5 results).
After completion, merges with raw_gpt-4o.jsonl -> raw_gpt-4o_full.jsonl.

Usage:
    python scripts/run_gpt4o_t1_t3.py
    python scripts/run_gpt4o_t1_t3.py --resume   # skip already-done query_ids
    python scripts/run_gpt4o_t1_t3.py --dry-run  # count queries + estimate cost only
"""

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import openai
from statsmodels.stats.proportion import proportion_confint

sys.path.insert(0, str(Path(__file__).parent))
from run_claude_eval import classify_response, SYSTEM_PROMPT, MAX_TOKENS, RETRY_LIMIT, RETRY_DELAY

DATASET_PATH = Path(__file__).parent.parent / "data" / "queries.jsonl"
RESULTS_DIR = Path(__file__).parent.parent / "results"
OUT_T1_T3 = RESULTS_DIR / "raw_gpt-4o_t1_t3.jsonl"
OUT_T4_T5 = RESULTS_DIR / "raw_gpt-4o.jsonl"
OUT_FULL = RESULTS_DIR / "raw_gpt-4o_full.jsonl"

MODEL = "gpt-4o"
# GPT-4o pricing ($/M tokens)
PRICE_INPUT = 2.50
PRICE_OUTPUT = 10.00


def load_api_key():
    path = Path.home() / ".api_keys"
    if path.exists():
        for line in path.read_text().splitlines():
            m = re.match(r'export\s+(\w+)="([^"]+)"', line)
            if m:
                os.environ[m.group(1)] = m.group(2)
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        raise RuntimeError("OPENAI_API_KEY not found in ~/.api_keys or environment")
    return key


def load_t1_t3():
    rows = []
    with open(DATASET_PATH) as f:
        for line in f:
            if line.strip():
                r = json.loads(line)
                if r["tier"] in (1, 2, 3):
                    rows.append(r)
    assert len(rows) == 141, f"Expected 141 T1-T3 queries, got {len(rows)}"
    return rows


def call_gpt4o(client, query: str) -> dict:
    for attempt in range(RETRY_LIMIT):
        try:
            resp = client.chat.completions.create(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": query},
                ],
            )
            return {
                "response_text": resp.choices[0].message.content,
                "stop_reason": resp.choices[0].finish_reason,
                "input_tokens": resp.usage.prompt_tokens,
                "output_tokens": resp.usage.completion_tokens,
            }
        except openai.RateLimitError:
            if attempt < RETRY_LIMIT - 1:
                wait = RETRY_DELAY * (attempt + 1)
                print(f"    Rate-limited, sleeping {wait}s...", flush=True)
                time.sleep(wait)
            else:
                raise
        except openai.APIError:
            if attempt < RETRY_LIMIT - 1:
                time.sleep(RETRY_DELAY)
            else:
                raise


def merge_and_stats():
    with open(OUT_T4_T5) as f:
        existing = [json.loads(l) for l in f if l.strip()]
    with open(OUT_T1_T3) as f:
        new = [json.loads(l) for l in f if l.strip()]

    combined = existing + new
    assert len(combined) == 201, f"Expected 201, got {len(combined)}"

    with open(OUT_FULL, "w") as f:
        for r in combined:
            f.write(json.dumps(r) + "\n")
    print(f"\nMerged {len(combined)} records -> {OUT_FULL}")

    legit = [r for r in combined if r["tier"] in (1, 2, 3, 4)]
    refused = [r for r in legit if r["classification"] == "refuse"]
    n, k = len(legit), len(refused)
    lo, hi = proportion_confint(k, n, alpha=0.05, method="wilson")
    print(f"\nGPT-4o Full FPR: {k}/{n} = {k/n*100:.1f}% [{lo*100:.1f}%, {hi*100:.1f}%]")

    for tier in [1, 2, 3, 4]:
        tier_rows = [r for r in legit if r["tier"] == tier]
        tier_ref = [r for r in tier_rows if r["classification"] == "refuse"]
        print(f"  T{tier}: {len(tier_ref)}/{len(tier_rows)} refused")

    return k, n, lo, hi


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--resume", action="store_true", help="Skip already-done query_ids")
    parser.add_argument("--dry-run", action="store_true", help="Estimate cost only, do not call API")
    args = parser.parse_args()

    entries = load_t1_t3()
    print(f"T1-T3 queries loaded: {len(entries)}")

    done_ids = set()
    if args.resume and OUT_T1_T3.exists():
        with open(OUT_T1_T3) as f:
            for line in f:
                if line.strip():
                    done_ids.add(json.loads(line)["query_id"])
        print(f"Resuming: {len(done_ids)} already done")

    remaining = [e for e in entries if e["query_id"] not in done_ids]
    est_cost = (len(remaining) * 128 / 1e6 * PRICE_INPUT +
                len(remaining) * MAX_TOKENS / 1e6 * PRICE_OUTPUT)
    print(f"Remaining: {len(remaining)} | Estimated cost: ${est_cost:.3f}")

    if args.dry_run:
        print("Dry run complete — no API calls made.")
        return

    api_key = load_api_key()
    client = openai.OpenAI(api_key=api_key)

    RESULTS_DIR.mkdir(exist_ok=True)
    mode = "a" if (args.resume and OUT_T1_T3.exists()) else "w"
    total_input = total_output = 0

    with open(OUT_T1_T3, mode) as out:
        for i, entry in enumerate(remaining, 1):
            qid = entry["query_id"]
            print(f"  [{i}/{len(remaining)}] {qid} ... ", end="", flush=True)
            try:
                result = call_gpt4o(client, entry["query"])
                classification = classify_response(result["response_text"], entry["query"])
                total_input += result["input_tokens"]
                total_output += result["output_tokens"]

                record = {
                    "query_id": qid,
                    "tier": entry["tier"],
                    "subdomain_primary": entry["subdomain_primary"],
                    "legitimacy": entry["legitimacy"],
                    "style_tags": entry.get("style_tags", []),
                    "model": MODEL,
                    "query": entry["query"],
                    "response_text": result["response_text"],
                    "stop_reason": result["stop_reason"],
                    "input_tokens": result["input_tokens"],
                    "output_tokens": result["output_tokens"],
                    "classification": classification["label"],
                    "classification_detail": classification,
                    "eval_timestamp": datetime.now(timezone.utc).isoformat(),
                }
                out.write(json.dumps(record) + "\n")
                out.flush()
                print(classification["label"], flush=True)

            except Exception as e:
                print(f"ERROR: {e}", flush=True)
                error_record = {
                    "query_id": qid,
                    "tier": entry["tier"],
                    "subdomain_primary": entry["subdomain_primary"],
                    "legitimacy": entry["legitimacy"],
                    "model": MODEL,
                    "query": entry["query"],
                    "response_text": None,
                    "classification": "error",
                    "error": str(e),
                    "eval_timestamp": datetime.now(timezone.utc).isoformat(),
                }
                out.write(json.dumps(error_record) + "\n")
                out.flush()

    act_cost = (total_input / 1e6 * PRICE_INPUT + total_output / 1e6 * PRICE_OUTPUT)
    print(f"\nEstimated: ${est_cost:.3f} | Actual: ${act_cost:.3f}")
    print(f"Saved: {OUT_T1_T3}")

    print("\nMerging with T4+T5 and computing full stats...")
    merge_and_stats()


if __name__ == "__main__":
    main()
