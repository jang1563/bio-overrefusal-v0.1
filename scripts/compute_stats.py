#!/usr/bin/env python3
"""
compute_stats.py — Pre-registered statistical analysis for Bio Over-Refusal Dataset

Implements all methods from Research/02_Methodology_Protocol.md §4:
  A1. Per-model FPR with Wilson / Jeffreys CIs
  A2. Exact binomial test: Sonnet vs Anthropic published baseline (p0=0.0005)
  A3. Pairwise McNemar tests (full-run models only) + BH FDR q=0.10
  A4. Tier × subdomain refusal heatmap (Sonnet)
  A5. Bootstrap CIs on key proportions (n_resamples=10,000)
  A6. BH-corrected per-cell binomial tests (Sonnet, n≥10 cells)

Outputs:
  results/stats_report.md   — human-readable report
  results/stats_table.json  — machine-readable results

Usage:
    python scripts/compute_stats.py
    python scripts/compute_stats.py --check   # print headline Sonnet result only
"""

import argparse
import json
import numpy as np
from collections import defaultdict
from datetime import datetime, timezone
from itertools import combinations
from pathlib import Path

import scipy.stats
from statsmodels.stats.proportion import proportion_confint
from statsmodels.stats.contingency_tables import mcnemar
from statsmodels.stats.multitest import multipletests

RESULTS_DIR = Path(__file__).parent.parent / "results"

# Full-run models (201 queries each) — GPT-4o excluded (only T4+T5)
FULL_RUN_MODELS = [
    "claude-haiku-4-5-20251001",
    "claude-sonnet-4-6",
    "deepseek-chat",
    "gemini-2.5-flash",
    "gpt-4o-mini",
    "llama-3.3-70b-versatile",
]

ANTHROPIC_BASELINE_P0 = 0.0005  # 0.05% from Next-gen CC blog


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_results(path: Path) -> list[dict]:
    return [json.loads(l) for l in path.read_text().splitlines() if l.strip()]


def load_all_results() -> dict[str, list[dict]]:
    all_records = {}
    for path in sorted(RESULTS_DIR.glob("raw_*.jsonl")):
        records = load_results(path)
        if records:
            model = records[0].get("model", path.stem.replace("raw_", ""))
            all_records[model] = records
    return all_records


# ---------------------------------------------------------------------------
# Helper: FPR numerator/denominator for legitimate queries
# ---------------------------------------------------------------------------

def legit_refusals(records: list[dict]) -> tuple[int, int]:
    """Return (k_refused, n_legit) for legitimate queries only."""
    legit = [r for r in records if r.get("legitimacy") == "legitimate"]
    k = sum(1 for r in legit if r["classification"] == "refuse")
    return k, len(legit)


def legit_refusals_subset(records: list[dict], tier=None, subdomain=None) -> tuple[int, int]:
    legit = [r for r in records if r.get("legitimacy") == "legitimate"]
    if tier is not None:
        legit = [r for r in legit if r.get("tier") == tier]
    if subdomain is not None:
        legit = [r for r in legit if r.get("subdomain_primary") == subdomain]
    k = sum(1 for r in legit if r["classification"] == "refuse")
    return k, len(legit)


# ---------------------------------------------------------------------------
# A1. Wilson and Jeffreys CIs
# ---------------------------------------------------------------------------

def wilson_ci(k: int, n: int, alpha: float = 0.05) -> tuple[float, float]:
    if n == 0:
        return (float("nan"), float("nan"))
    lo, hi = proportion_confint(k, n, alpha=alpha, method="wilson")
    return lo, hi


def clopper_pearson_ci(k: int, n: int, alpha: float = 0.05) -> tuple[float, float]:
    if n == 0:
        return (float("nan"), float("nan"))
    lo, hi = proportion_confint(k, n, alpha=alpha, method="beta")
    return lo, hi


def jeffreys_ci(k: int, n: int, alpha: float = 0.05) -> tuple[float, float]:
    if n == 0:
        return (float("nan"), float("nan"))
    lo = scipy.stats.beta.ppf(alpha / 2, 0.5 + k, 0.5 + n - k)
    hi = scipy.stats.beta.ppf(1 - alpha / 2, 0.5 + k, 0.5 + n - k)
    return lo, hi


def ci_for_cell(k: int, n: int) -> dict:
    """Choose Wilson for n≥10, Jeffreys for n<10 or zero events."""
    if n == 0:
        return {"method": "—", "lo": float("nan"), "hi": float("nan"), "fpr": float("nan")}
    fpr = k / n
    if n < 10:
        lo, hi = jeffreys_ci(k, n)
        method = "Jeffreys"
    else:
        lo, hi = wilson_ci(k, n)
        method = "Wilson"
    return {"method": method, "fpr": fpr, "lo": lo, "hi": hi}


# ---------------------------------------------------------------------------
# A2. Exact binomial test vs Anthropic baseline
# ---------------------------------------------------------------------------

def binomial_test_vs_baseline(k: int, n: int, p0: float) -> dict:
    result = scipy.stats.binomtest(k, n, p=p0, alternative="greater")
    return {"p_value": result.pvalue, "p0": p0, "k": k, "n": n}


# ---------------------------------------------------------------------------
# A3. Pairwise McNemar tests
# ---------------------------------------------------------------------------

def build_refusal_vector(records: list[dict], query_ids: list[str]) -> dict[str, bool]:
    """Map query_id → True if refused (legitimate queries only), else False."""
    legit = {r["query_id"]: r for r in records if r.get("legitimacy") == "legitimate"}
    return {qid: (legit[qid]["classification"] == "refuse") if qid in legit else False
            for qid in query_ids}


def mcnemar_pair(vec1: dict, vec2: dict) -> dict:
    """Compute McNemar 2×2 table and test for paired models."""
    qids = sorted(set(vec1) & set(vec2))
    a = sum(1 for q in qids if vec1[q] and vec2[q])      # both refuse
    b = sum(1 for q in qids if vec1[q] and not vec2[q])   # m1 refuse only
    c = sum(1 for q in qids if not vec1[q] and vec2[q])   # m2 refuse only
    d = sum(1 for q in qids if not vec1[q] and not vec2[q])  # both help
    table = np.array([[a, b], [c, d]])
    if b + c == 0:
        return {"a": a, "b": b, "c": c, "d": d, "p_value": 1.0, "note": "no_discordance"}
    result = mcnemar(table, exact=True)
    return {"a": a, "b": b, "c": c, "d": d, "p_value": result.pvalue, "note": ""}


def pairwise_mcnemar(all_records: dict[str, list[dict]]) -> list[dict]:
    """Run all 15 pairs for full-run models, return sorted by p_value."""
    full_models = [m for m in FULL_RUN_MODELS if m in all_records]
    # Shared legitimate query IDs across full-run models
    legit_ids = sorted({
        r["query_id"]
        for m in full_models
        for r in all_records[m]
        if r.get("legitimacy") == "legitimate"
    })

    vecs = {m: build_refusal_vector(all_records[m], legit_ids) for m in full_models}
    results = []
    for m1, m2 in combinations(full_models, 2):
        row = mcnemar_pair(vecs[m1], vecs[m2])
        row["model1"] = m1
        row["model2"] = m2
        results.append(row)

    # BH FDR correction
    pvals = [r["p_value"] for r in results]
    _, pvals_corrected, _, _ = multipletests(pvals, alpha=0.10, method="fdr_bh")
    for r, qval in zip(results, pvals_corrected):
        r["q_value"] = qval
        r["significant_bh"] = bool(qval < 0.10)

    return sorted(results, key=lambda x: x["p_value"])


# ---------------------------------------------------------------------------
# A4. Tier × subdomain heatmap (Sonnet)
# ---------------------------------------------------------------------------

def tier_subdomain_heatmap(records: list[dict]) -> dict:
    legit = [r for r in records if r.get("legitimacy") == "legitimate"]
    tiers = sorted({r["tier"] for r in legit})
    subdomains = sorted({r["subdomain_primary"] for r in legit})

    cells = {}
    for tier in tiers:
        for sub in subdomains:
            subset = [r for r in legit if r["tier"] == tier and r["subdomain_primary"] == sub]
            k = sum(1 for r in subset if r["classification"] == "refuse")
            cells[(tier, sub)] = (k, len(subset))
    return {"tiers": tiers, "subdomains": subdomains, "cells": cells}


# ---------------------------------------------------------------------------
# A5. Bootstrap CIs on key proportions
# ---------------------------------------------------------------------------

def bootstrap_ci(labels: list[int], n_resamples: int = 10_000, seed: int = 42) -> tuple[float, float]:
    """Percentile bootstrap CI for a binary 0/1 array (FPR)."""
    arr = np.array(labels, dtype=float)
    rng = np.random.default_rng(seed)
    samples = [rng.choice(arr, size=len(arr), replace=True).mean() for _ in range(n_resamples)]
    return (float(np.percentile(samples, 2.5)), float(np.percentile(samples, 97.5)))


def build_refusal_labels(records: list[dict], tier=None) -> list[int]:
    legit = [r for r in records if r.get("legitimacy") == "legitimate"]
    if tier is not None:
        legit = [r for r in legit if r.get("tier") == tier]
    return [1 if r["classification"] == "refuse" else 0 for r in legit]


def bootstrap_discordance(rec1: list[dict], rec2: list[dict]) -> tuple[float, float]:
    """Bootstrap CI for the discordance rate between two models (paired)."""
    legit1 = {r["query_id"]: r for r in rec1 if r.get("legitimacy") == "legitimate"}
    legit2 = {r["query_id"]: r for r in rec2 if r.get("legitimacy") == "legitimate"}
    shared = sorted(set(legit1) & set(legit2))
    discordant = [
        1 if (legit1[q]["classification"] == "refuse") != (legit2[q]["classification"] == "refuse")
        else 0
        for q in shared
    ]
    return bootstrap_ci(discordant)


# ---------------------------------------------------------------------------
# A6. BH-corrected per-cell binomial tests (Sonnet)
# ---------------------------------------------------------------------------

def per_cell_binomial(records: list[dict], p0: float = ANTHROPIC_BASELINE_P0) -> list[dict]:
    """One-sample binomial per tier×subdomain cell (n≥10 only), BH-corrected."""
    legit = [r for r in records if r.get("legitimacy") == "legitimate"]
    tiers = sorted({r["tier"] for r in legit})
    subdomains = sorted({r["subdomain_primary"] for r in legit})

    rows = []
    for tier in tiers:
        for sub in subdomains:
            subset = [r for r in legit if r["tier"] == tier and r["subdomain_primary"] == sub]
            n = len(subset)
            if n < 10:
                continue
            k = sum(1 for r in subset if r["classification"] == "refuse")
            result = scipy.stats.binomtest(k, n, p=p0, alternative="greater")
            rows.append({
                "tier": tier,
                "subdomain": sub,
                "k": k,
                "n": n,
                "fpr": k / n,
                "p_value": result.pvalue,
            })

    if rows:
        pvals = [r["p_value"] for r in rows]
        _, pvals_corrected, _, _ = multipletests(pvals, alpha=0.10, method="fdr_bh")
        for r, qval in zip(rows, pvals_corrected):
            r["q_value"] = qval
            r["significant_bh"] = bool(qval < 0.10)

    return rows


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------

def fmt_pct(v: float) -> str:
    if v != v:  # NaN
        return "—"
    return f"{v * 100:.1f}%"


def fmt_ci(lo: float, hi: float) -> str:
    if lo != lo or hi != hi:
        return "—"
    return f"[{lo * 100:.1f}%, {hi * 100:.1f}%]"


def fmt_p(p: float) -> str:
    if p < 0.0001:
        return "< 0.0001"
    return f"{p:.4f}"


# ---------------------------------------------------------------------------
# Report writer
# ---------------------------------------------------------------------------

def write_report(all_records: dict[str, list[dict]], out_path: Path):
    sonnet = all_records.get("claude-sonnet-4-6", [])
    haiku = all_records.get("claude-haiku-4-5-20251001", [])

    lines = [
        "# Bio Over-Refusal Dataset — Statistical Analysis Report",
        "",
        f"_Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}_",
        "",
        "Pre-registered methods: `Research/02_Methodology_Protocol.md §4`",
        "",
        "**Key:** FPR = fraction of **legitimate** queries refused.  ",
        "Wilson 95% CI (primary), Jeffreys (cells n<10), Clopper-Pearson (sensitivity check).  ",
        "Anthropic baseline p₀ = 0.05% (Next-gen CC blog).",
        "",
        "---", "",
    ]

    # ------------------------------------------------------------------ A1
    lines += ["## A1. Per-Model FPR with Confidence Intervals", ""]
    lines += ["| Model | N Legit | Refused | FPR | 95% CI (Wilson) | Method |"]
    lines += ["|-------|---------|---------|-----|-----------------|--------|"]
    for model, records in sorted(all_records.items()):
        k, n = legit_refusals(records)
        ci = ci_for_cell(k, n)
        lines.append(
            f"| {model} | {n} | {k} | {fmt_pct(ci['fpr'])} | "
            f"{fmt_ci(ci['lo'], ci['hi'])} | {ci['method']} |"
        )
    lines += [""]

    # Sonnet headline with Clopper-Pearson sensitivity
    k_s, n_s = legit_refusals(sonnet)
    lo_w, hi_w = wilson_ci(k_s, n_s)
    lo_cp, hi_cp = clopper_pearson_ci(k_s, n_s)
    lines += [
        "### Sonnet 4.6 Headline Estimate (sensitivity check)",
        "",
        f"- **Wilson 95% CI**: {fmt_pct(k_s/n_s)} {fmt_ci(lo_w, hi_w)}",
        f"- **Clopper-Pearson 95% CI** (conservative): {fmt_pct(k_s/n_s)} {fmt_ci(lo_cp, hi_cp)}",
        "",
    ]

    # Per-tier breakdown for Sonnet
    lines += ["### Sonnet 4.6 FPR by Tier (Wilson CIs)", ""]
    lines += ["| Tier | N Legit | Refused | FPR | 95% CI |"]
    lines += ["|------|---------|---------|-----|--------|"]
    for tier in [1, 2, 3, 4]:
        k, n = legit_refusals_subset(sonnet, tier=tier)
        ci = ci_for_cell(k, n)
        lines.append(
            f"| T{tier} | {n} | {k} | {fmt_pct(ci['fpr'])} | {fmt_ci(ci['lo'], ci['hi'])} |"
        )
    lines += [""]

    # ------------------------------------------------------------------ A2
    lines += ["## A2. Exact Binomial Test: Sonnet vs Anthropic Baseline", ""]
    binom = binomial_test_vs_baseline(k_s, n_s, ANTHROPIC_BASELINE_P0)
    lines += [
        f"**H₀**: Sonnet FPR ≤ {ANTHROPIC_BASELINE_P0 * 100:.2f}%  ",
        f"**H₁**: Sonnet FPR > {ANTHROPIC_BASELINE_P0 * 100:.2f}% (one-tailed, greater)  ",
        f"Observed: k = {binom['k']} refusals out of n = {binom['n']} legitimate queries  ",
        f"**p-value: {fmt_p(binom['p_value'])}**",
        "",
        "_All other models have 0–1 refusals (trivially below baseline; no test needed)._",
        "",
    ]

    # ------------------------------------------------------------------ A3
    lines += ["## A3. Pairwise McNemar Tests (full-run models, BH FDR q=0.10)", ""]
    lines += ["_GPT-4o excluded: only T4+T5 data (60 queries), cannot be paired with 201-query models._", ""]
    pairs = pairwise_mcnemar(all_records)
    lines += ["| Model 1 | Model 2 | Discordant (b,c) | p (exact) | q (BH) | Sig |"]
    lines += ["|---------|---------|-----------------|-----------|--------|-----|"]
    for row in pairs:
        sig = "✓" if row["significant_bh"] else ""
        disc = f"({row['b']}, {row['c']})"
        note = f" _{row['note']}_" if row.get("note") else ""
        lines.append(
            f"| {row['model1']} | {row['model2']} | {disc} | "
            f"{fmt_p(row['p_value'])} | {fmt_p(row['q_value'])} | {sig}{note} |"
        )
    lines += [""]

    # ------------------------------------------------------------------ A4
    lines += ["## A4. Tier × Subdomain Refusal Heatmap (Sonnet 4.6)", ""]
    lines += ["_Counts = refused / total legitimate in cell. — = cell empty._", ""]
    hmap = tier_subdomain_heatmap(sonnet)
    header = "| Subdomain | " + " | ".join(f"T{t}" for t in hmap["tiers"]) + " |"
    sep = "|-----------|" + "|".join("----" for _ in hmap["tiers"]) + "|"
    lines += [header, sep]
    for sub in hmap["subdomains"]:
        cells = []
        for tier in hmap["tiers"]:
            k, n = hmap["cells"].get((tier, sub), (0, 0))
            cells.append(f"{k}/{n}" if n > 0 else "—")
        lines.append(f"| {sub} | " + " | ".join(cells) + " |")
    lines += [""]

    # ------------------------------------------------------------------ A5
    lines += ["## A5. Bootstrap 95% CIs on Key Proportions (n_resamples=10,000)", ""]
    lines += ["| Proportion | Estimate | Bootstrap 95% CI |"]
    lines += ["|-----------|---------|-----------------|"]

    def _bootstrap_row(label: str, labels: list[int]) -> str:
        est = sum(labels) / len(labels) if labels else float("nan")
        lo, hi = bootstrap_ci(labels)
        return f"| {label} | {fmt_pct(est)} | {fmt_ci(lo, hi)} |"

    lines.append(_bootstrap_row("Sonnet overall FPR (n=181)", build_refusal_labels(sonnet)))
    lines.append(_bootstrap_row("Sonnet T3 FPR (n=41)", build_refusal_labels(sonnet, tier=3)))
    lines.append(_bootstrap_row("Sonnet T4 FPR (n=40)", build_refusal_labels(sonnet, tier=4)))

    if haiku:
        disc_lo, disc_hi = bootstrap_discordance(haiku, sonnet)
        k_disc = sum(
            1 for qid in {r["query_id"] for r in haiku if r.get("legitimacy") == "legitimate"}
            & {r["query_id"] for r in sonnet if r.get("legitimacy") == "legitimate"}
            if (
                next((r for r in haiku if r["query_id"] == qid), {"classification": ""})["classification"] == "refuse"
            ) != (
                next((r for r in sonnet if r["query_id"] == qid), {"classification": ""})["classification"] == "refuse"
            )
        )
        n_disc = sum(1 for r in sonnet if r.get("legitimacy") == "legitimate")
        est_disc = k_disc / n_disc if n_disc else float("nan")
        lines.append(f"| Haiku vs Sonnet discordance (n={n_disc}) | {fmt_pct(est_disc)} | {fmt_ci(disc_lo, disc_hi)} |")
    lines += [""]

    # ------------------------------------------------------------------ A6
    lines += ["## A6. BH-Corrected Per-Cell Binomial Tests (Sonnet, n≥10 cells, q=0.10)", ""]
    lines += [f"H₀: cell FPR ≤ {ANTHROPIC_BASELINE_P0 * 100:.2f}% (one-tailed, greater).  ", ""]
    cell_tests = per_cell_binomial(sonnet)
    if cell_tests:
        lines += ["| Tier | Subdomain | k | n | FPR | p | q (BH) | Sig |"]
        lines += ["|------|-----------|---|---|-----|---|--------|-----|"]
        for row in sorted(cell_tests, key=lambda x: x["p_value"]):
            sig = "✓" if row["significant_bh"] else ""
            lines.append(
                f"| T{row['tier']} | {row['subdomain']} | {row['k']} | {row['n']} | "
                f"{fmt_pct(row['fpr'])} | {fmt_p(row['p_value'])} | {fmt_p(row['q_value'])} | {sig} |"
            )
    else:
        lines += ["_No testable cells (n≥10) found._"]
    lines += [""]

    out_path.write_text("\n".join(lines) + "\n")
    print(f"Stats report written: {out_path}")


# ---------------------------------------------------------------------------
# JSON output
# ---------------------------------------------------------------------------

def write_json(all_records: dict[str, list[dict]], out_path: Path):
    sonnet = all_records.get("claude-sonnet-4-6", [])
    data = {}

    # Per-model summary
    data["models"] = {}
    for model, records in all_records.items():
        k, n = legit_refusals(records)
        ci = ci_for_cell(k, n)
        data["models"][model] = {
            "n_legit": n, "k_refused": k,
            "fpr": round(k / n, 4) if n else None,
            "wilson_lo": round(ci["lo"], 4) if ci["lo"] == ci["lo"] else None,
            "wilson_hi": round(ci["hi"], 4) if ci["hi"] == ci["hi"] else None,
        }

    # Sonnet binomial test
    k_s, n_s = legit_refusals(sonnet)
    binom = binomial_test_vs_baseline(k_s, n_s, ANTHROPIC_BASELINE_P0)
    data["sonnet_baseline_test"] = binom

    # McNemar pairs
    pairs = pairwise_mcnemar(all_records)
    data["mcnemar_pairs"] = [
        {k: v for k, v in row.items() if k not in ("a", "b", "c", "d")}
        for row in pairs
    ]

    out_path.write_text(json.dumps(data, indent=2) + "\n")
    print(f"Stats JSON written: {out_path}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Bio Over-Refusal — statistical analysis")
    parser.add_argument("--check", action="store_true",
                        help="Print headline Sonnet result only and exit")
    args = parser.parse_args()

    all_records = load_all_results()
    print(f"Loaded {len(all_records)} models: {', '.join(sorted(all_records))}")

    sonnet = all_records.get("claude-sonnet-4-6", [])
    if args.check:
        k, n = legit_refusals(sonnet)
        lo, hi = wilson_ci(k, n)
        binom = binomial_test_vs_baseline(k, n, ANTHROPIC_BASELINE_P0)
        print(f"\nSonnet FPR = {k}/{n} = {k/n*100:.1f}%")
        print(f"Wilson 95% CI: {fmt_ci(lo, hi)}")
        print(f"Binomial test vs p0={ANTHROPIC_BASELINE_P0}: p {fmt_p(binom['p_value'])}")
        return

    RESULTS_DIR.mkdir(exist_ok=True)
    write_report(all_records, RESULTS_DIR / "stats_report.md")
    write_json(all_records, RESULTS_DIR / "stats_table.json")


if __name__ == "__main__":
    main()
