# Bio Over-Refusal Dataset v0.1.0

[![CI](https://github.com/jang1563/bio-overrefusal-v0.1/actions/workflows/ci.yml/badge.svg)](https://github.com/jang1563/bio-overrefusal-v0.1/actions/workflows/ci.yml)
[![Python 3.10–3.12](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue)](pyproject.toml)
[![License: CC BY-NC-SA 4.0](https://img.shields.io/badge/License-CC%20BY--NC--SA%204.0-lightgrey)](LICENSE)
[![Hugging Face Dataset](https://img.shields.io/badge/%F0%9F%A4%97%20Hugging%20Face-Dataset-yellow)](https://huggingface.co/datasets/jang1563/bio-overrefusal-v0.1)

> **TL;DR.** 201 domain-expert-authored and tier-annotated biology research queries, stratified by sensitivity, used to measure **false-positive refusal rates (FPR)** in frontier LLMs. **Anthropic Claude Opus 4.7 refuses 43.6%** of legitimate biology research queries; Sonnet 4.5/4.6 refuse 33.7%; Haiku 4.5 and non-Anthropic full-run models show 0% strict refusals. All Anthropic refusals are hard API-level stops (`stop_reason="refusal"`).

This repository contains the dataset, schema, evaluation scripts, statistical analysis, and release documentation needed to reproduce the v0.1.0 results. It is intended for AI safety evaluation and safety-calibration research, **not** for harmful-content elicitation.

- **Dataset (Hugging Face):** [jang1563/bio-overrefusal-v0.1](https://huggingface.co/datasets/jang1563/bio-overrefusal-v0.1)
- **Dataset card:** [`dataset_card.md`](dataset_card.md)
- **Statistical report:** [`results/stats_report.md`](results/stats_report.md)
- **Responsible-use scope:** [`SAFETY.md`](SAFETY.md)

## Release Status

| Surface | Status |
|---------|--------|
| Dataset | v0.1.0 — 201 annotated queries, schema-validated in CI |
| GitHub | Public, CI green on Python 3.10 / 3.11 / 3.12 |
| Hugging Face | Public dataset repo, CC BY-NC-SA 4.0, viewer configured for `data/queries.jsonl` |
| Human IAA | Pending for v0.2.0 (LLM-based validation reported in `results/iaa_report.md`) |

## Headline Finding

| Model | N Legit | FPR (strict) | Wilson 95% CI | Notes |
|-------|---------|-------------|---------------|-------|
| deepseek-chat | 181 | 0.0% | [0.0%, 2.1%] | |
| gemini-2.5-flash | 181 | 0.0% | [0.0%, 2.1%] | |
| gpt-4o-mini | 181 | 0.0% | [0.0%, 2.1%] | |
| llama-3.3-70b-versatile | 181 | 0.0% | [0.0%, 2.1%] | |
| claude-haiku-4-5-20251001 | 181 | 0.0% | [0.0%, 2.1%] | |
| **claude-sonnet-4-5-20250929** | **181** | **33.7%** | **[27.2%, 40.9%]** | |
| **claude-sonnet-4-6** | **181** | **33.7%** | **[27.2%, 40.9%]** | |
| **claude-opus-4-7** | **181** | **43.6%** | **[36.6%, 50.9%]** | Highest FPR |
| gpt-4o | 40 | 0.0% | [0.0%, 8.8%] | T4+T5 only |

**FPR is higher in the larger tested Anthropic models**: Haiku 4.5 (0%) < Sonnet 4.5/4.6 (33.7%) < Opus 4.7 (43.6%). Non-Anthropic models had 0% strict refusals in the tested runs, with 0.0–0.5% broad FPR. All Anthropic refusals are hard API-level stops (`stop_reason="refusal"`, empty response).

Exact binomial test vs Anthropic's published 0.05% baseline: **p < 0.0001**.  
McNemar (Haiku vs Sonnet 4.6, 181 paired queries): **p < 0.0001** (BH q < 0.0001).

## Dataset Structure

### Tier System

| Tier | Name | N | FPR Target |
|------|------|---|-----------|
| 1 | Basic Biology | 57 | 0% |
| 2 | Advanced Biology | 41 | <1% |
| 3 | Educational Dual-Use-Adjacent | 43 | Policy/governance framing |
| 4 | Legitimate Research That Sounds Dangerous | 40 | **Primary measurement tier** |
| 5 | True Edge Cases | 20 | Not measured (expert disagreement) |

### Sonnet 4.6 Tier Breakdown

| Tier | Refused | Total | FPR | Wilson 95% CI |
|------|---------|-------|-----|---------------|
| T1 | 0 | 57 | 0.0% | [0.0%, 6.3%] |
| T2 | 1 | 41 | 2.4% | [0.4%, 12.6%] |
| T3 | 34 | 43 | 79.1% | [64.8%, 88.6%] |
| T4 | 26 | 40 | 65.0% | [49.5%, 77.9%] |

### Subdomains (10)

`virology` · `toxicology` · `synthetic_biology` · `genomics` · `pathogen_biology` ·
`immunology` · `biochemistry` · `cell_biology` · `microbiology` · `structural_biology`

## Quick Start

Requires Python 3.10, 3.11, or 3.12. The CI matrix validates all three versions.

```bash
git clone https://github.com/jang1563/bio-overrefusal-v0.1.git && cd bio-overrefusal-v0.1

# Install runtime + development dependencies
python -m pip install -e ".[dev]"

# Validate the dataset schema and loader
python -m pytest -q
python -m ruff check .

# Evaluate a model (requires the relevant provider API key)
export ANTHROPIC_API_KEY="..."
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

# Prepare a Hugging Face dataset-repo bundle for review/upload
python scripts/prepare_hf_release.py --force --repo-id <hf-user-or-org>/bio-overrefusal
```

Raw model outputs are intentionally ignored by git (`results/raw_*.jsonl`) because they can be large and provider-specific. The repository tracks reproducible summary tables and reports.

## Repository Structure

```
.github/workflows/ci.yml — CI validation for loader + dataset invariants
data/
  queries.jsonl          — 201 annotated queries (the dataset)
schema/                  — JSON schema for queries.jsonl
  features.py            — Canonical Hugging Face `Features` declaration
scripts/
  run_claude_eval.py     — Anthropic-SDK evaluator
  run_multi_eval.py      — Multi-provider evaluator
  classify_with_llm.py   — LLM-as-judge reclassifier
  analyze_results.py     — FPR report generator
  compute_stats.py       — Pre-registered statistical analysis
  analyze_refusals.py    — Qualitative refusal analysis
  compute_iaa.py         — IAA computation (LLM-as-Annotator-2)
  prepare_hf_release.py  — Local Hugging Face dataset-repo bundle builder
results/                 — Generated outputs (raw_*.jsonl excluded from git)
  fpr_report.md          — Multi-model FPR comparison
  stats_report.md        — Wilson CIs, McNemar, BH FDR
  qualitative_report.md  — Keyword analysis, refusal clusters
  iaa_report.md          — LLM-based label validation (human IAA pending)
docs/
  public_release_checklist.md — GitHub + Hugging Face release checklist
  huggingface_release.md      — HF bundle/upload workflow
tier_definitions.md      — Pre-registered tier criteria
dataset_card.md          — HuggingFace dataset card
CONTRIBUTING.md          — Contribution and dual-use safety guidelines
```

## Key Findings

1. **FPR is higher in the larger tested Anthropic models**: Haiku 4.5 (0%) < Sonnet 4.5/4.6 (33.7%) < Opus 4.7 (43.6%) — non-Anthropic models had 0% strict refusals and ≤0.5% broad FPR
2. **All Anthropic refusals are API-level**: `stop_reason="refusal"` with empty `content[]` — not safety hedging
3. **T3 most affected (79.1%)**: Regulatory/policy topics (BSL-3 specs, DURC framework, CWC scheduling) blocked despite being publicly available government policy
4. **T4 also severely affected (65.0%)**: Primary mechanistic research questions refused
5. **Intra-family gap**: Haiku 4.5 (0%) vs Sonnet 4.6 (33.7%) vs Opus 4.7 (43.6%) — same queries
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
| claude-sonnet-4-5-20250929 | ~$3.17 | Anthropic |
| claude-sonnet-4-6 | ~$3.17 | Anthropic |
| claude-opus-4-7 | ~$15.82 | Anthropic |
| gpt-4o | ~$0.63 (T4+T5 only) | OpenAI |

## Related Work

- **XSTest** (250 queries, 2023): Foundational over-refusal benchmark, general domain
- **OR-Bench** (80K, 2024): Large-scale, generic topics
- **FalseReject** (16K, 44 categories): General safety topics
- **Health-ORSC-Bench** (31K, 2024): Health-general, not biology-research-specific

This dataset fills the gap: biology-research-specific, domain-expert-authored, sensitivity-stratified, with hard API-level refusal detection.

## Responsible Use

This benchmark is scoped to false-positive refusal measurement on legitimate research questions. It should not be used for jailbreaks, prompt injection, or attempts to elicit operational biological harm. New dataset contributions must include public citations and must not request synthesis, production, weaponization, evasion, dosing, optimization, or deployment of harmful biological agents or toxins.

See [`SAFETY.md`](SAFETY.md) for the public responsible-use scope and reporting guidance.

## Reproducibility Notes

- `python -m pytest -q` validates schema fields, controlled vocabularies, row counts, tier counts, query ID conventions, and Hugging Face loader compatibility.
- `python -m ruff check .` validates Python source hygiene for the public release.
- `schema/jsonl_schema.md` is the canonical data contract.
- `dataset_card.md` is the Hugging Face-facing card; `scripts/prepare_hf_release.py` copies it as `README.md` in the HF dataset bundle.
- `docs/public_release_checklist.md` lists the GitHub and Hugging Face publication steps.

## Citation

```bibtex
@dataset{bio_overrefusal_2026,
  title     = {Bio Over-Refusal Dataset v0.1.0},
  author    = {Kim, JangKeun},
  year      = {2026},
  note      = {Initial public release v0.1.0, April 2026. Phase 3 human IAA pending.},
  license   = {CC BY-NC-SA 4.0}
}
```

## License

[CC BY-NC-SA 4.0](LICENSE) — Attribution-NonCommercial-ShareAlike 4.0 International
