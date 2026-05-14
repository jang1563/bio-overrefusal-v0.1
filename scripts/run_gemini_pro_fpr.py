"""
run_gemini_pro_fpr.py — FPR evaluation for Gemini 2.5 Pro on 201 biology queries.

Uses httpx directly (not OpenAI-compatible SDK) to set thinkingBudget=0,
avoiding the issue where Pro's thinking tokens consume all maxOutputTokens.
Same SYSTEM_PROMPT and classify_response as run_claude_eval.py.
"""

import asyncio
import json
import os
import sys
import pathlib
from datetime import datetime, timezone

import httpx

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from run_claude_eval import classify_response, SYSTEM_PROMPT, RESULTS_DIR

DATASET_PATH = pathlib.Path(__file__).parent.parent / "data" / "queries.jsonl"
OUT_FILE = RESULTS_DIR / "raw_gemini-2.5-pro.jsonl"
MODEL = "gemini-2.5-pro"
MAX_OUTPUT_TOKENS = 2048
MAX_CONCURRENT = 4


async def query_gemini_pro(api_key: str, query_text: str,
                           semaphore: asyncio.Semaphore) -> tuple[str, str, int, int]:
    url = (f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}"
           f":generateContent?key={api_key}")
    payload = {
        "system_instruction": {"parts": [{"text": SYSTEM_PROMPT}]},
        "contents": [{"parts": [{"text": query_text}]}],
        "generationConfig": {
            "maxOutputTokens": MAX_OUTPUT_TOKENS,
            "temperature": 0.0,
        },
        "thinkingConfig": {"thinkingBudget": 0},
    }
    async with semaphore:
        try:
            async with httpx.AsyncClient(timeout=120) as client:
                r = await client.post(url, json=payload)
                data = r.json()
            if "candidates" not in data or not data["candidates"]:
                return "", "refusal", 0, 0
            candidate = data["candidates"][0]
            finish = candidate.get("finishReason", "STOP")
            if finish in ("SAFETY", "RECITATION", "PROHIBITED_CONTENT", "SPII"):
                return "", "refusal", 0, 0
            parts = candidate.get("content", {}).get("parts", [])
            text = "".join(p.get("text", "") for p in parts if not p.get("thought"))
            usage = data.get("usageMetadata", {})
            in_tok = usage.get("promptTokenCount", 0)
            out_tok = usage.get("candidatesTokenCount", 0)
            return text or "", finish, in_tok, out_tok
        except Exception as e:
            print(f"  Error: {e}", file=sys.stderr)
            return "", "error", 0, 0


async def main() -> None:
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        print("ERROR: GEMINI_API_KEY not set", file=sys.stderr)
        sys.exit(1)

    queries = [json.loads(line) for line in DATASET_PATH.read_text().splitlines() if line.strip()]

    # Resume support
    done_ids = set()
    if OUT_FILE.exists():
        for line in OUT_FILE.read_text().splitlines():
            if line.strip():
                done_ids.add(json.loads(line)["query_id"])

    pending = [q for q in queries if q["query_id"] not in done_ids]
    print(f"Model: {MODEL} | Total: {len(queries)} | Done: {len(done_ids)} | Remaining: {len(pending)}")

    semaphore = asyncio.Semaphore(MAX_CONCURRENT)

    async def run_one(q: dict, idx: int) -> dict:
        text, stop, in_tok, out_tok = await query_gemini_pro(api_key, q["query"], semaphore)
        cls_result = classify_response(text or "", q["query"])
        label = cls_result["label"]
        print(f"  [{idx:3d}/201] {q['query_id']:<35} {label}", flush=True)
        return {
            "query_id": q["query_id"],
            "tier": q["tier"],
            "subdomain_primary": q.get("subdomain_primary", ""),
            "legitimacy": q.get("adjudicated_legitimacy", q.get("legitimacy", "")),
            "style_tags": q.get("style_tags", []),
            "model": MODEL,
            "query": q["query"],
            "response_text": text[:500] if text else "",
            "stop_reason": stop,
            "input_tokens": in_tok,
            "output_tokens": out_tok,
            "classification": label,
            "classification_detail": json.dumps({k: v for k, v in cls_result.items() if k != "label"}),
            "eval_timestamp": datetime.now(timezone.utc).isoformat(),
        }

    tasks = [run_one(q, i + len(done_ids) + 1) for i, q in enumerate(pending)]

    with OUT_FILE.open("a") as f:
        # Run in batches to stream results
        batch_size = 20
        for i in range(0, len(tasks), batch_size):
            batch = tasks[i:i + batch_size]
            results = await asyncio.gather(*batch)
            for r in results:
                f.write(json.dumps(r) + "\n")
            f.flush()

    # Final summary
    all_results = [json.loads(line) for line in OUT_FILE.read_text().splitlines() if line.strip()]
    t1_t4 = [r for r in all_results if r["tier"] in (1, 2, 3, 4)]
    n_refused = sum(1 for r in t1_t4 if r["classification"] in ("refuse", "partial"))
    fpr = n_refused / len(t1_t4) * 100 if t1_t4 else 0
    print(f"\nFPR (T1-T4, N={len(t1_t4)}): {n_refused}/{len(t1_t4)} = {fpr:.1f}%")
    print(f"Total completed: {len(all_results)}/201")
    print(f"Saved → {OUT_FILE}")


if __name__ == "__main__":
    asyncio.run(main())
