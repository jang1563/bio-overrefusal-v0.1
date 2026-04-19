# Bio Over-Refusal Dataset v0.1.0

An expert-annotated benchmark of **201 legitimate biology research queries** stratified by sensitivity tier, designed to measure **false-positive refusal rates (FPR)** of large language models.

## Headline Finding

| Model | FPR (strict) | Wilson 95% CI |
|-------|-------------|---------------|
| deepseek-chat | 0.0% | [0.0%, 2.1%] |
| gemini-2.5-flash | 0.0% | [0.0%, 2.1%] |
| gpt-4o-mini | 0.0% | [0.0%, 2.1%] |
| llama-3.3-70b-versatile | 0.0% | [0.0%, 2.1%] |
| claude-haiku-4-5-20251001 | 0.0% | [0.0%, 2.1%] |
| **claude-sonnet-4-6** | **33.7%** | **[27.2%, 40.9%]** |
| gpt-4o (T4+T5 only) | 0.0% | [0.0%, 8.8%] |

**61 out of 181 legitimate queries refused** by Claude Sonnet 4.6 — all as hard API-level stops (`stop_reason="refusal"`, empty response). Claude Haiku 4.5 (same provider): 0.0% FPR.

Exact binomial test vs Anthropic's published 0.05% baseline: **p < 0.0001**.  
McNemar (Haiku vs Sonnet, 181 paired queries): **p < 0.0001** (BH q < 0.0001).

## Dataset Structure

### Tier System

| Tier | Name | N | FPR Target |
|------|------|---|-----------|
| 1 | Basic Biology | 50 | 0% |
| 2 | Advanced Biology | 50 | <1% |
| 3 | Educational Dual-Use-Adjacent | 41 | Policy/governance framing |
| 4 | Legitimate Research That Sounds Dangerous | 40 | **Primary measurement tier** |
| 5 | True Edge Cases | 20 | Not measured (expert disagreement) |

### Sonnet 4.6 Tier Breakdown

| Tier | Refused | Total | FPR | Wilson 95% CI |
|------|---------|-------|-----|---------------|
| T1 | 0 | 50 | 0.0% | [0.0%, 7.1%] |
| T2 | 1 | 50 | 2.0% | [0.4%, 10.5%] |
| T3 | 34 | 41 | 82.9% | [68.7%, 91.5%] |
| T4 | 26 | 40 | 65.0% | [49.5%, 77.9%] |

### Subdomains (10)

`virology` · `toxicology` · `synthetic_biology` · `genomics` · `pathogen_biology` ·
`immunology` · `biochemistry` · `cell_biology` · `microbiology` · `structural_biology`

## Quick Start

```bash
git clone <repo-url> && cd OverRefusal

# Install dependencies
pip install anthropic openai statsmodels scipy numpy pandas scikit-learn irrCAC

# Load API keys (expected format: export KEY="value")
source ~/.api_keys

# Evaluate a model
python scripts/run_multi_eval.py --model claude-sonnet-4-6
python scripts/run_multi_eval.py --model deepseek-chat
python scripts/run_multi_eval.py --list-models   # see all supported models + cost estimates

# Generate FPR report
python scripts/analyze_results.py results/raw_*.jsonl

# Statistical analysis (Wilson CIs, McNemar, BH FDR)
python scripts/compute_stats.py

# Qualitative refusal analysis
python scripts/analyze_refusals.py

# LLM-as-judge reclassification
python scripts/classify_with_llm.py results/raw_claude-sonnet-4-6.jsonl

# IAA analysis (requires OPENAI_API_KEY)
python scripts/compute_iaa.py
```

## Repository Structure

```
data/
  queries.jsonl          — 201 annotated queries (the dataset)
schema/                  — JSON schema for queries.jsonl
scripts/
  run_claude_eval.py     — Anthropic-SDK evaluator
  run_multi_eval.py      — Multi-provider evaluator
  classify_with_llm.py   — LLM-as-judge reclassifier
  analyze_results.py     — FPR report generator
  compute_stats.py       — Pre-registered statistical analysis
  analyze_refusals.py    — Qualitative refusal analysis
  compute_iaa.py         — IAA computation (LLM-as-Annotator-2)
results/                 — Generated outputs (raw_*.jsonl excluded from git)
  fpr_report.md          — Multi-model FPR comparison
  stats_report.md        — Wilson CIs, McNemar, BH FDR
  qualitative_report.md  — Keyword analysis, refusal clusters
  iaa_report.md          — Inter-annotator agreement
tier_definitions.md      — Pre-registered tier criteria
dataset_card.md          — HuggingFace dataset card
```

## Key Findings

1. **Sonnet 4.6 FPR = 33.7%** vs 0.0% for all 5 other full-run models including Claude Haiku 4.5
2. **All 61 refusals are API-level**: `stop_reason="refusal"` with empty `content[]` — not safety hedging
3. **T3 most affected (82.9%)**: Regulatory/policy topics (BSL-3 specs, DURC framework, CWC scheduling) blocked despite being publicly available government policy
4. **T4 also severely affected (65.0%)**: Primary mechanistic research questions refused
5. **Intra-family gap**: Haiku 4.5 (0%) vs Sonnet 4.6 (33.7%) — same provider, same queries
6. **T2 anomaly**: One methodology question about bat coronavirus assays refused by keyword matching
7. **Hypothetical framing = highest FPR** (59.1%): "suppose a researcher..." triggers more refusals

## Refusal Clusters (Sonnet 4.6)

| Cluster | Count | Key Topics |
|---------|-------|-----------|
| regulatory_policy | 18 (30%) | BSL-3/4 specs, HHS P3CO, DURC policy, CWC scheduling |
| mechanistic_detail | 9 (15%) | H5N1 PB2 adaptation, furin cleavage, ricin A-chain |
| protocol_level | 5 (8%) | Select-agent protocols, aerosol methods |
| other | 29 (48%) | Mixed toxicology/pathogen biology |

## Evaluation Cost Estimates

| Model | Cost (201 queries) | Provider |
|-------|-------------------|---------|
| deepseek-chat | ~$0.06 | DeepSeek |
| gemini-2.5-flash | ~$0.09 | Google |
| gpt-4o-mini | ~$0.13 | OpenAI |
| llama-3.3-70b-versatile | ~$0.18 | Groq |
| claude-haiku-4-5-20251001 | ~$0.84 | Anthropic |
| claude-sonnet-4-6 | ~$3.17 | Anthropic |

## Related Work

- **XSTest** (250 queries, 2023): Foundational over-refusal benchmark, general domain
- **OR-Bench** (80K, 2024): Large-scale, generic topics
- **FalseReject** (16K, 44 categories): General safety topics
- **Health-ORSC-Bench** (31K, 2024): Health-general, not biology-research-specific

This dataset fills the gap: biology-research-specific, expert-annotated, sensitivity-stratified, with hard API-level refusal detection.

## Citation

```bibtex
@dataset{bio_overrefusal_2026,
  title     = {Bio Over-Refusal Dataset v0.1.0},
  author    = {primary annotator},
  year      = {2026},
  note      = {Pre-release v0.1.0, April 2026. Phase 3 human IAA pending.},
  license   = {CC BY-NC-SA 4.0}
}
```

## License

[CC BY-NC-SA 4.0](LICENSE) — Attribution-NonCommercial-ShareAlike 4.0 International
