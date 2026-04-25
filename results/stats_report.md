# Bio Over-Refusal Dataset — Statistical Analysis Report

_Generated: 2026-04-19 (updated with all Anthropic model tier breakdowns)_

Pre-registered methods: see `tier_definitions.md` and the analysis plan in `scripts/compute_stats.py`.

**Key:** FPR = fraction of **legitimate** queries refused.  
Wilson 95% CI (primary), Jeffreys (cells n<10), Clopper-Pearson (sensitivity check).  
Anthropic baseline p₀ = 0.05% (Next-gen CC blog).

---

## A1. Per-Model FPR with Confidence Intervals

| Model | N Legit | Refused | FPR | 95% CI (Wilson) | Method |
|-------|---------|---------|-----|-----------------|--------|
| claude-haiku-4-5-20251001 | 181 | 0 | 0.0% | [0.0%, 2.1%] | Wilson |
| claude-opus-4-7 | 181 | 79 | 43.6% | [36.6%, 50.9%] | Wilson |
| claude-sonnet-4-5-20250929 | 181 | 61 | 33.7% | [27.2%, 40.9%] | Wilson |
| claude-sonnet-4-6 | 181 | 61 | 33.7% | [27.2%, 40.9%] | Wilson |
| deepseek-chat | 181 | 0 | 0.0% | [0.0%, 2.1%] | Wilson |
| gemini-2.5-flash | 181 | 0 | 0.0% | [0.0%, 2.1%] | Wilson |
| gpt-4o | 40 | 0 | 0.0% | [0.0%, 8.8%] | Wilson |
| gpt-4o-mini | 181 | 0 | 0.0% | [0.0%, 2.1%] | Wilson |
| llama-3.3-70b-versatile | 181 | 0 | 0.0% | [0.0%, 2.1%] | Wilson |

### Sonnet 4.6 Headline Estimate (sensitivity check)

- **Wilson 95% CI**: 33.7% [27.2%, 40.9%]
- **Clopper-Pearson 95% CI** (conservative): 33.7% [26.9%, 41.1%]

### Anthropic Models — FPR by Tier (Wilson CIs)

#### Claude Opus 4.7

| Tier | N Legit | Refused | FPR | 95% CI |
|------|---------|---------|-----|--------|
| T1 | 57 | 3 | 5.3% | [1.8%, 14.4%] |
| T2 | 41 | 6 | 14.6% | [6.9%, 28.4%] |
| T3 | 43 | 39 | 90.7% | [78.4%, 96.3%] |
| T4 | 40 | 31 | 77.5% | [62.5%, 87.7%] |

#### Claude Sonnet 4.5

| Tier | N Legit | Refused | FPR | 95% CI |
|------|---------|---------|-----|--------|
| T1 | 57 | 0 | 0.0% | [0.0%, 6.3%] |
| T2 | 41 | 1 | 2.4% | [0.4%, 12.6%] |
| T3 | 43 | 35 | 81.4% | [67.4%, 90.3%] |
| T4 | 40 | 25 | 62.5% | [47.0%, 75.8%] |

#### Claude Sonnet 4.6

| Tier | N Legit | Refused | FPR | 95% CI |
|------|---------|---------|-----|--------|
| T1 | 57 | 0 | 0.0% | [0.0%, 6.3%] |
| T2 | 41 | 1 | 2.4% | [0.4%, 12.6%] |
| T3 | 43 | 34 | 79.1% | [64.8%, 88.6%] |
| T4 | 40 | 26 | 65.0% | [49.5%, 77.9%] |

#### Claude Haiku 4.5

| Tier | N Legit | Refused | FPR | 95% CI |
|------|---------|---------|-----|--------|
| T1 | 57 | 0 | 0.0% | [0.0%, 6.3%] |
| T2 | 41 | 0 | 0.0% | [0.0%, 8.6%] |
| T3 | 43 | 0 | 0.0% | [0.0%, 8.2%] |
| T4 | 40 | 0 | 0.0% | [0.0%, 8.8%] |

## A2. Exact Binomial Test: Sonnet vs Anthropic Baseline

**H₀**: Sonnet FPR ≤ 0.05%  
**H₁**: Sonnet FPR > 0.05% (one-tailed, greater)  
Observed: k = 61 refusals out of n = 181 legitimate queries  
**p-value: < 0.0001**

_All other models have 0–1 refusals (trivially below baseline; no test needed)._

## A3. Pairwise McNemar Tests (full-run models, BH FDR q=0.10)

_GPT-4o excluded: only T4+T5 data (60 queries), cannot be paired with 201-query models._

| Model 1 | Model 2 | Discordant (b,c) | p (exact) | q (BH) | Sig |
|---------|---------|-----------------|-----------|--------|-----|
| claude-haiku-4-5-20251001 | claude-sonnet-4-6 | (0, 61) | < 0.0001 | < 0.0001 | ✓ |
| claude-sonnet-4-6 | deepseek-chat | (61, 0) | < 0.0001 | < 0.0001 | ✓ |
| claude-sonnet-4-6 | gemini-2.5-flash | (61, 0) | < 0.0001 | < 0.0001 | ✓ |
| claude-sonnet-4-6 | gpt-4o-mini | (61, 0) | < 0.0001 | < 0.0001 | ✓ |
| claude-sonnet-4-6 | llama-3.3-70b-versatile | (61, 0) | < 0.0001 | < 0.0001 | ✓ |
| claude-haiku-4-5-20251001 | deepseek-chat | (0, 0) | 1.0000 | 1.0000 |  _no_discordance_ |
| claude-haiku-4-5-20251001 | gemini-2.5-flash | (0, 0) | 1.0000 | 1.0000 |  _no_discordance_ |
| claude-haiku-4-5-20251001 | gpt-4o-mini | (0, 0) | 1.0000 | 1.0000 |  _no_discordance_ |
| claude-haiku-4-5-20251001 | llama-3.3-70b-versatile | (0, 0) | 1.0000 | 1.0000 |  _no_discordance_ |
| deepseek-chat | gemini-2.5-flash | (0, 0) | 1.0000 | 1.0000 |  _no_discordance_ |
| deepseek-chat | gpt-4o-mini | (0, 0) | 1.0000 | 1.0000 |  _no_discordance_ |
| deepseek-chat | llama-3.3-70b-versatile | (0, 0) | 1.0000 | 1.0000 |  _no_discordance_ |
| gemini-2.5-flash | gpt-4o-mini | (0, 0) | 1.0000 | 1.0000 |  _no_discordance_ |
| gemini-2.5-flash | llama-3.3-70b-versatile | (0, 0) | 1.0000 | 1.0000 |  _no_discordance_ |
| gpt-4o-mini | llama-3.3-70b-versatile | (0, 0) | 1.0000 | 1.0000 |  _no_discordance_ |

## A4. Tier × Subdomain Refusal Heatmap (Sonnet 4.6)

_Counts = refused / total legitimate in cell. — = cell empty._

| Subdomain | T1 | T2 | T3 | T4 |
|-----------|----|----|----|----|
| biochemistry | 0/6 | 0/4 | 4/4 | 2/3 |
| cell_biology | 0/6 | 0/4 | 2/3 | 2/3 |
| genomics | 0/5 | 0/5 | 2/4 | 0/4 |
| immunology | 0/5 | 0/5 | 3/4 | 1/4 |
| microbiology | 0/7 | 0/3 | 4/4 | 2/4 |
| pathogen_biology | 0/6 | 0/4 | 4/7 | 5/5 |
| structural_biology | 0/4 | 0/4 | 4/4 | 2/2 |
| synthetic_biology | 0/7 | 0/3 | 2/4 | 2/5 |
| toxicology | 0/4 | 0/4 | 4/4 | 5/5 |
| virology | 0/7 | 1/5 | 5/5 | 5/5 |

## A5. Bootstrap 95% CIs on Key Proportions (n_resamples=10,000)

| Proportion | Estimate | Bootstrap 95% CI |
|-----------|---------|-----------------|
| Sonnet overall FPR (n=181) | 33.7% | [26.5%, 40.3%] |
| Sonnet T3 FPR (n=43) | 79.1% | [65.1%, 90.7%] |
| Sonnet T4 FPR (n=40) | 65.0% | [50.0%, 80.0%] |
| Haiku vs Sonnet discordance (n=181) | 33.7% | [27.1%, 40.9%] |

## A6. BH-Corrected Per-Cell Binomial Tests (Sonnet, n≥10 cells, q=0.10)

H₀: cell FPR ≤ 0.05% (one-tailed, greater).  

_No testable cells (n≥10) found._

