# Active Experiments

This repository's public v0.1.0 release is anchored on the dataset, schema,
baseline multi-model runs, statistical report, and responsible-use scope.

The local worktree also contains follow-up experiments that should be treated as
post-v0.1.0 until they are reviewed and versioned:

| Experiment | Local files | Release guidance |
|---|---|---|
| Context-condition sensitivity | `scripts/run_context_condition.py`, `scripts/summarize_context_results.py`, `results/context_condition/` | Keep out of v0.1.0 headline claims until the design, prompt conditions, and raw-output handling are reviewed. |
| Gemini 2.5 Pro follow-up | `scripts/run_gemini_pro_fpr.py`, `scripts/run_multi_eval.py` provider entry | Candidate for v0.1.1 after results are summarized in `results/fpr_report.md` and reflected in the dataset card. |

Raw model outputs should not be committed unless they have been reviewed for
secrets, account metadata, and safe public release. Prefer tracked aggregate
tables and short reports for public documentation.

