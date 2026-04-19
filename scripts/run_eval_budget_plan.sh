#!/usr/bin/env bash
# run_eval_budget_plan.sh — Bio Over-Refusal Dataset evaluation execution plan
#
# Recommended run order: cheapest models first so you can inspect results
# before committing to more expensive runs.
#
# API keys are auto-loaded from ~/.api_keys by the Python scripts.
# You do NOT need to source ~/.api_keys manually.
#
# Estimated total: ~$5.10 (worst case; actual cost ~40-60% lower)
#
# Usage: bash scripts/run_eval_budget_plan.sh
#   Or run individual steps by copying the commands below.
#
# Prerequisites:
#   pip install anthropic openai   (already installed)
#   ~/.api_keys must contain ANTHROPIC_API_KEY, OPENAI_API_KEY,
#     DEEPSEEK_API_KEY, GEMINI_API_KEY, GROQ_API_KEY

set -euo pipefail
cd "$(dirname "$0")/.."   # run from project root

echo "=== Bio Over-Refusal Evaluation ==="
echo "Dataset: $(wc -l < data/queries.jsonl) queries"
echo ""

# ------------------------------------------------------------------
# Preview available models and estimated costs
# ------------------------------------------------------------------
echo "--- Available models ---"
python scripts/run_multi_eval.py --list-models
echo ""

# ------------------------------------------------------------------
# STEP 1: Cheap baselines (~$0.46 total)
# These run fast. Inspect results before running expensive models.
# ------------------------------------------------------------------
echo "=== Step 1: Cheap baselines ==="

echo "DeepSeek-chat ($0.06)..."
python scripts/run_multi_eval.py --model deepseek-chat

echo "Gemini 2.0 Flash ($0.09)..."
python scripts/run_multi_eval.py --model gemini-2.0-flash

echo "GPT-4o-mini ($0.13)..."
python scripts/run_multi_eval.py --model gpt-4o-mini

echo "Groq Llama-3.3-70B ($0.18)..."
python scripts/run_multi_eval.py --model llama-3.3-70b-versatile

# ------------------------------------------------------------------
# STEP 2: Claude baseline (~$0.84)
# ------------------------------------------------------------------
echo ""
echo "=== Step 2: Claude baseline ==="

echo "Claude Haiku 4.5 ($0.84)..."
python scripts/run_multi_eval.py --model claude-haiku-4-5-20251001

# ------------------------------------------------------------------
# STEP 3: Primary targets (~$3.80)
# GPT-4o: T4+T5 only to save ~$1.50 vs full run
# ------------------------------------------------------------------
echo ""
echo "=== Step 3: Primary targets ==="

echo "Claude Sonnet 4.6 ($3.17, all 201 queries)..."
python scripts/run_multi_eval.py --model claude-sonnet-4-6

echo "GPT-4o ($0.63, Tier 4+5 only)..."
python scripts/run_multi_eval.py --model gpt-4o --tier 4 5

# ------------------------------------------------------------------
# STEP 4: LLM-as-judge reclassification (~$0.02)
# Reclassify key model results with a more accurate judge
# ------------------------------------------------------------------
echo ""
echo "=== Step 4: LLM-as-judge reclassification ==="

echo "Reclassifying Claude Sonnet results..."
python scripts/classify_with_llm.py results/raw_claude-sonnet-4-6.jsonl

echo "Reclassifying GPT-4o results..."
python scripts/classify_with_llm.py results/raw_gpt-4o.jsonl

# ------------------------------------------------------------------
# STEP 5: Multi-model comparison report
# ------------------------------------------------------------------
echo ""
echo "=== Step 5: Generating FPR comparison report ==="

python scripts/analyze_results.py results/raw_*.jsonl

echo ""
echo "=== Done ==="
echo "Reports:"
echo "  results/fpr_report.md     — human-readable FPR analysis"
echo "  results/fpr_table.csv     — machine-readable tier × subdomain table"
echo "  results/llm_classified_*  — LLM-judge reclassified results"
echo ""
echo "To also analyze judge-reclassified results:"
echo "  python scripts/analyze_results.py results/llm_classified_*.jsonl"
