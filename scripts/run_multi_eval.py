#!/usr/bin/env python3
"""
run_multi_eval.py — Bio Over-Refusal Dataset multi-provider evaluator

Supports Anthropic models natively and any OpenAI-compatible provider
(Groq, DeepSeek, Gemini, Together AI, OpenAI) via the openai SDK.
API keys are auto-loaded from ~/.api_keys.

Usage:
    python scripts/run_multi_eval.py --list-models
    python scripts/run_multi_eval.py --model deepseek-chat
    python scripts/run_multi_eval.py --model gpt-4o --tier 4 5
    python scripts/run_multi_eval.py --model claude-sonnet-4-6 --resume
    python scripts/run_multi_eval.py --model gpt-4o --max-cost 1.0

Output:
    results/raw_{model}.jsonl       — raw results with classification
    results/summary_{model}.json    — FPR summary (auto-generated after run)
"""

import os
import re
import sys
import time
import json
import argparse
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).parent))
from run_claude_eval import (
    classify_response,
    load_dataset,
    DATASET_PATH,
    RESULTS_DIR,
    MAX_TOKENS,
    SYSTEM_PROMPT,
    RETRY_LIMIT,
    RETRY_DELAY,
    compute_summary,
)

import anthropic
import openai

# ---------------------------------------------------------------------------
# Provider & pricing config
# ---------------------------------------------------------------------------

AVG_INPUT_TOKENS = 128  # system prompt ~50 + avg query ~78 tokens

PROVIDERS = {
    "claude-haiku-4-5-20251001": {
        "sdk": "anthropic",
        "env": "ANTHROPIC_API_KEY",
    },
    "claude-sonnet-4-5-20250929": {
        "sdk": "anthropic",
        "env": "ANTHROPIC_API_KEY",
    },
    "claude-sonnet-4-6": {
        "sdk": "anthropic",
        "env": "ANTHROPIC_API_KEY",
    },
    "claude-opus-4-7": {
        "sdk": "anthropic",
        "env": "ANTHROPIC_API_KEY",
    },
    "gpt-4o": {
        "sdk": "openai",
        "env": "OPENAI_API_KEY",
        "base_url": None,
    },
    "gpt-4o-mini": {
        "sdk": "openai",
        "env": "OPENAI_API_KEY",
        "base_url": None,
    },
    "deepseek-chat": {
        "sdk": "openai",
        "env": "DEEPSEEK_API_KEY",
        "base_url": "https://api.deepseek.com/v1",
    },
    "gemini-2.5-flash": {
        "sdk": "openai",
        "env": "GEMINI_API_KEY",
        # Trailing slash required for correct URL construction
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
    },
    "llama-3.3-70b-versatile": {
        "sdk": "openai",
        "env": "GROQ_API_KEY",
        "base_url": "https://api.groq.com/openai/v1",
    },
    "meta-llama/Llama-3.1-70B-Instruct-Turbo": {
        "sdk": "openai",
        "env": "TOGETHER_API_KEY",
        # Try https://api.together.ai/v1 if this URL returns 4xx
        "base_url": "https://api.together.xyz/v1",
    },
}

PRICING = {  # (input $/M tokens, output $/M tokens)
    "claude-haiku-4-5-20251001": (0.80, 4.00),
    "claude-sonnet-4-5-20250929": (3.00, 15.00),
    "claude-sonnet-4-6": (3.00, 15.00),
    "claude-opus-4-7": (15.00, 75.00),
    "gpt-4o": (2.50, 10.00),
    "gpt-4o-mini": (0.15, 0.60),
    "deepseek-chat": (0.07, 0.28),
    "gemini-2.5-flash": (0.15, 0.60),
    "llama-3.3-70b-versatile": (0.59, 0.79),
    "meta-llama/Llama-3.1-70B-Instruct-Turbo": (0.18, 0.18),
}

# ---------------------------------------------------------------------------
# API key loading
# ---------------------------------------------------------------------------

def load_api_keys():
    """Parse ~/.api_keys and inject into os.environ. Handles inline comments."""
    path = Path.home() / ".api_keys"
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        m = re.match(r'export\s+(\w+)="([^"]+)"', line)
        if m:
            os.environ[m.group(1)] = m.group(2)


# ---------------------------------------------------------------------------
# Model call
# ---------------------------------------------------------------------------

def call_model(model_id: str, query: str) -> dict:
    """Call a model and return normalized response dict."""
    config = PROVIDERS[model_id]
    api_key = os.environ.get(config["env"])
    if not api_key:
        raise RuntimeError(f"{config['env']} not set (needed for {model_id})")

    for attempt in range(RETRY_LIMIT):
        try:
            if config["sdk"] == "anthropic":
                client = anthropic.Anthropic(api_key=api_key)
                resp = client.messages.create(
                    model=model_id,
                    max_tokens=MAX_TOKENS,
                    system=SYSTEM_PROMPT,
                    messages=[{"role": "user", "content": query}],
                )
                # stop_reason="refusal" returns empty content[] in anthropic SDK 0.83+
                if resp.stop_reason == "refusal" or not resp.content:
                    text = ""
                else:
                    text = resp.content[0].text
                return {
                    "response_text": text,
                    "stop_reason": resp.stop_reason,
                    "input_tokens": resp.usage.input_tokens,
                    "output_tokens": resp.usage.output_tokens,
                }
            else:
                client = openai.OpenAI(
                    base_url=config.get("base_url"),
                    api_key=api_key,
                )
                resp = client.chat.completions.create(
                    model=model_id,
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

        except (
            anthropic.RateLimitError,
            openai.RateLimitError,
        ):
            if attempt < RETRY_LIMIT - 1:
                wait = RETRY_DELAY * (attempt + 1)
                print(f"    Rate-limited, sleeping {wait}s...", flush=True)
                time.sleep(wait)
            else:
                raise
        except (anthropic.APIError, openai.APIError):
            if attempt < RETRY_LIMIT - 1:
                time.sleep(RETRY_DELAY)
            else:
                raise


# ---------------------------------------------------------------------------
# Cost estimation
# ---------------------------------------------------------------------------

def estimate_cost(model_id: str, n_queries: int) -> float:
    if model_id not in PRICING:
        return 0.0
    ip, op = PRICING[model_id]
    return n_queries * AVG_INPUT_TOKENS / 1e6 * ip + n_queries * MAX_TOKENS / 1e6 * op


def actual_cost(model_id: str, total_input: int, total_output: int) -> float:
    if model_id not in PRICING:
        return 0.0
    ip, op = PRICING[model_id]
    return total_input / 1e6 * ip + total_output / 1e6 * op


# ---------------------------------------------------------------------------
# Evaluation run
# ---------------------------------------------------------------------------

def run_eval(model_id: str, tier_filter=None, resume=False, max_cost=None):
    RESULTS_DIR.mkdir(exist_ok=True)
    safe_model = model_id.replace("/", "_").replace(":", "_")
    raw_path = RESULTS_DIR / f"raw_{safe_model}.jsonl"

    entries = load_dataset(tier_filter)
    n = len(entries)
    est = estimate_cost(model_id, n)

    if max_cost is not None and est > max_cost:
        print(
            f"Estimated cost ${est:.3f} exceeds --max-cost ${max_cost:.2f}. Aborting.",
            flush=True,
        )
        return None

    done_ids = set()
    if resume and raw_path.exists():
        with open(raw_path) as f:
            for line in f:
                if line.strip():
                    done_ids.add(json.loads(line)["query_id"])
        print(f"Resuming: {len(done_ids)} already done.", flush=True)

    remaining = [e for e in entries if e["query_id"] not in done_ids]
    print(
        f"Model: {model_id} | Queries: {len(remaining)} | "
        f"Estimated cost: ${estimate_cost(model_id, len(remaining)):.3f}",
        flush=True,
    )

    if not remaining:
        print("Nothing to do.")
        return raw_path

    total_input = total_output = 0
    mode = "a" if resume else "w"
    with open(raw_path, mode) as out:
        for i, entry in enumerate(remaining, 1):
            qid = entry["query_id"]
            print(f"  [{i}/{len(remaining)}] {qid} ... ", end="", flush=True)
            try:
                result = call_model(model_id, entry["query"])
                # Hard API-level refusal — bypass regex, classify directly
                if result["stop_reason"] == "refusal":
                    classification = {
                        "label": "refuse",
                        "refuse_patterns_hit": 0,
                        "hedge_patterns_hit": 0,
                        "redirect_patterns_hit": 0,
                        "response_length_words": 0,
                        "note": "api_stop_reason_refusal",
                    }
                else:
                    classification = classify_response(result["response_text"], entry["query"])
                total_input += result["input_tokens"]
                total_output += result["output_tokens"]

                record = {
                    "query_id": qid,
                    "tier": entry["tier"],
                    "subdomain_primary": entry["subdomain_primary"],
                    "legitimacy": entry["legitimacy"],
                    "style_tags": entry.get("style_tags", []),
                    "model": model_id,
                    "query": entry["query"],  # included for LLM judge compatibility
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
                    "model": model_id,
                    "query": entry["query"],
                    "response_text": None,
                    "classification": "error",
                    "error": str(e),
                    "eval_timestamp": datetime.now(timezone.utc).isoformat(),
                }
                out.write(json.dumps(error_record) + "\n")
                out.flush()

    act = actual_cost(model_id, total_input, total_output)
    print(
        f"\nEstimated: ${estimate_cost(model_id, len(remaining)):.3f} | "
        f"Actual: ${act:.3f}",
        flush=True,
    )
    print(f"Results: {raw_path}", flush=True)
    return raw_path


# ---------------------------------------------------------------------------
# List models
# ---------------------------------------------------------------------------

def list_models(tier_filter=None):
    entries = load_dataset(tier_filter)
    n = len(entries)
    tier_label = f"tiers {tier_filter}" if tier_filter else "all 201 queries"
    print(f"\nAvailable models ({tier_label}, MAX_TOKENS={MAX_TOKENS}):\n")
    print(f"  {'Model':<45} {'Est. Cost':>10}  {'Env var'}")
    print(f"  {'-'*45} {'-'*10}  {'-'*20}")
    for mid, cfg in PROVIDERS.items():
        est = estimate_cost(mid, n)
        print(f"  {mid:<45} ${est:>9.3f}  {cfg['env']}")
    print()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    load_api_keys()

    parser = argparse.ArgumentParser(
        description="Bio Over-Refusal Dataset — multi-provider evaluator"
    )
    parser.add_argument("--model", help="Model ID (see --list-models)")
    parser.add_argument(
        "--tier", type=int, nargs="+", help="Restrict to tier(s), e.g. --tier 4 5"
    )
    parser.add_argument(
        "--resume", action="store_true", help="Skip already-completed query_ids"
    )
    parser.add_argument(
        "--list-models",
        action="store_true",
        help="Print available models with estimated costs and exit",
    )
    parser.add_argument(
        "--max-cost",
        type=float,
        metavar="USD",
        help="Abort if estimated cost exceeds this amount",
    )
    args = parser.parse_args()

    if args.list_models:
        list_models(args.tier)
        return

    if not args.model:
        parser.error("--model is required (or use --list-models)")

    if args.model not in PROVIDERS:
        print(f"Unknown model: {args.model}")
        print("Run --list-models to see available options.")
        sys.exit(1)

    raw_path = run_eval(
        args.model,
        tier_filter=args.tier,
        resume=args.resume,
        max_cost=args.max_cost,
    )
    if raw_path and raw_path.exists():
        compute_summary(raw_path)


if __name__ == "__main__":
    main()
