# Changelog

## v0.1.0 — April 2026

### Dataset
- Phase 1 seed set: 100 queries across 5 tiers and 10 subdomains (completed 2026-04-17)
- Phase 2 expansion to 201 queries following Phase 1 self-audit (completed 2026-04-17)
- Pre-registered tier definitions, annotation schema, and methodology protocol
- 5-tier sensitivity taxonomy (T1 basic biology → T5 expert-disagreement edge cases)
- 10 biology subdomains: virology, toxicology, synthetic_biology, genomics, pathogen_biology,
  immunology, biochemistry, cell_biology, microbiology, structural_biology

### Evaluation
- 9-model evaluation (April 2026): deepseek-chat, gemini-2.5-flash, gpt-4o-mini,
  llama-3.3-70b-versatile, claude-haiku-4-5-20251001, claude-sonnet-4-5-20250929,
  claude-sonnet-4-6, claude-opus-4-7, gpt-4o (T4+T5 only)
- Key finding: FPR scales with model size within Anthropic family —
  Haiku 4.5 (0%) < Sonnet 4.5/4.6 (33.7%) < Opus 4.7 (43.6%)
- All non-Anthropic models: 0.0–0.5% FPR
- All Anthropic refusals are hard API-level stops (stop_reason="refusal", empty response)
- T2 boundary re-tiering: 9 queries adjusted based on IAA disagreement analysis
  (2 upgraded T2→T3, 7 downgraded T2→T1); new distribution: T1=57, T2=41, T3=43, T4=40, T5=20
- IAA: Tier quadratic-weighted κ = 0.885 [0.841, 0.921]; Legitimacy AC1 = 0.890 [0.833, 0.937]
  (LLM judge: gemini-2.5-flash; human Annotator 2 recruitment ongoing)
- Statistical analysis: Wilson CIs, exact binomial vs Anthropic baseline (p < 0.0001),
  McNemar pairwise tests with BH FDR correction

### Scripts
- `scripts/run_claude_eval.py`: Anthropic-SDK evaluator
- `scripts/run_multi_eval.py`: Multi-provider evaluator (Anthropic + OpenAI-compat)
- `scripts/classify_with_llm.py`: LLM-as-judge reclassifier
- `scripts/analyze_results.py`: FPR report generator
- `scripts/compute_stats.py`: Pre-registered statistical analysis
- `scripts/analyze_refusals.py`: Qualitative refusal analysis
- `scripts/compute_iaa.py`: LLM-as-Annotator-2 IAA computation

### Pending (v0.2.0)
- Phase 3 inter-annotator agreement with human Annotator 2 (LLM validation complete; human IAA pending for v0.2.0)
- arXiv preprint submission
- HuggingFace public release
