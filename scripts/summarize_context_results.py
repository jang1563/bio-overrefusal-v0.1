#!/usr/bin/env python3
"""
summarize_context_results.py

Reads completed context condition experiment results and generates:
1. A comparison table (markdown + LaTeX)
2. The text paragraph to insert into evidence.tex §Context-Sensitivity
3. McNemar exact test comparing C0 vs each other condition

Usage:
    python scripts/summarize_context_results.py --model claude-sonnet-4-6
"""
import argparse
import json
import math
from pathlib import Path

RESULTS_DIR = Path(__file__).parent.parent / "results" / "context_condition"

CONDITION_LABELS = {
    "C0": "Neutral (baseline)",
    "C1": "Institutional context",
    "C2": "Authorized researcher",
    "C3": "Biosafety programme",
    "C4": "Minimal",
}


def wilson_ci(k, n, z=1.96):
    if n == 0:
        return (0, 0)
    p = k / n
    denom = 1 + z**2 / n
    centre = (p + z**2 / (2 * n)) / denom
    margin = z * math.sqrt(p * (1 - p) / n + z**2 / (4 * n**2)) / denom
    return (max(0, centre - margin), min(1, centre + margin))


def mcnemar_exact(b, c):
    """McNemar exact p-value (two-sided) for discordant pairs b, c."""
    from scipy.stats import binom
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    p = 2 * binom.cdf(k, n, 0.5)
    return min(p, 1.0)


def load_condition(model_id, condition_key):
    safe_model = model_id.replace("/", "_").replace(":", "_")
    raw_path = RESULTS_DIR / f"raw_{safe_model}_{condition_key}.jsonl"
    if not raw_path.exists():
        return None
    records = []
    with open(raw_path) as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))
    return records


def compute_fpr(records, strict=True):
    legit = [r for r in records if r.get("legitimacy") == "legitimate"
             and r.get("classification") != "error"]
    if not legit:
        return None, 0, 0
    if strict:
        refused = sum(1 for r in legit if r["classification"] == "refuse")
    else:
        refused = sum(1 for r in legit if r["classification"] in ("refuse", "partial", "redirect"))
    return refused / len(legit), refused, len(legit)


def compute_tier_fprs(records, strict=True):
    result = {}
    for t in [1, 2, 3, 4]:
        tier_records = [r for r in records if r.get("tier") == t
                        and r.get("legitimacy") == "legitimate"
                        and r.get("classification") != "error"]
        if not tier_records:
            result[f"T{t}"] = None
            continue
        if strict:
            refused = sum(1 for r in tier_records if r["classification"] == "refuse")
        else:
            refused = sum(1 for r in tier_records
                          if r["classification"] in ("refuse", "partial", "redirect"))
        result[f"T{t}"] = (refused / len(tier_records), refused, len(tier_records))
    return result


def get_refuse_ids(records, strict=True):
    legit = [r for r in records if r.get("legitimacy") == "legitimate"
             and r.get("classification") != "error"]
    if strict:
        return set(r["query_id"] for r in legit if r["classification"] == "refuse")
    return set(r["query_id"] for r in legit
               if r["classification"] in ("refuse", "partial", "redirect"))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="claude-sonnet-4-6")
    args = parser.parse_args()

    model_id = args.model
    print(f"\n{'='*70}")
    print(f"Context Condition Summary: {model_id}")
    print(f"{'='*70}\n")

    # Load all conditions
    condition_data = {}
    for ckey in ["C0", "C1", "C2", "C3", "C4"]:
        records = load_condition(model_id, ckey)
        if records:
            condition_data[ckey] = records
            print(f"Loaded {ckey}: {len(records)} records")

    if not condition_data:
        print("No results found. Run run_context_condition.py first.")
        return

    # FPR summary table
    print(f"\n{'Condition':<6} {'Label':<28} {'FPR':<8} {'CI':<18} {'T3 FPR':<8} {'T4 FPR':<8} {'N'}")
    print("-" * 90)
    summary = {}
    for ckey in ["C0", "C1", "C2", "C3", "C4"]:
        if ckey not in condition_data:
            continue
        records = condition_data[ckey]
        fpr, refused, n = compute_fpr(records, strict=True)
        ci_lo, ci_hi = wilson_ci(refused, n)
        tier_fprs = compute_tier_fprs(records, strict=True)
        t3 = tier_fprs.get("T3")
        t4 = tier_fprs.get("T4")
        t3_str = f"{t3[0]:.1%}" if t3 else "—"
        t4_str = f"{t4[0]:.1%}" if t4 else "—"
        label = CONDITION_LABELS.get(ckey, ckey)[:26]
        print(f"{ckey:<6} {label:<28} {fpr:.1%}   [{ci_lo:.1%}, {ci_hi:.1%}]  {t3_str:<8} {t4_str:<8} {n}")
        summary[ckey] = {
            "fpr": fpr, "refused": refused, "n": n,
            "ci": (ci_lo, ci_hi),
            "tier_fprs": tier_fprs,
        }

    # McNemar tests vs C0
    if "C0" in condition_data:
        c0_ids = get_refuse_ids(condition_data["C0"])
        print("\nMcNemar exact tests vs C0 (baseline):")
        print(f"{'Comparison':<12} {'b (C0 refuse, Cx help)':<26} {'c (C0 help, Cx refuse)':<26} {'p-value'}")
        print("-" * 80)
        for ckey in ["C1", "C2", "C3", "C4"]:
            if ckey not in condition_data:
                continue
            cx_ids = get_refuse_ids(condition_data[ckey])
            b = len(c0_ids - cx_ids)   # C0 refuses, Cx helps
            c = len(cx_ids - c0_ids)   # C0 helps, Cx refuses
            p = mcnemar_exact(b, c)
            print(f"C0 vs {ckey}      b={b:<22} c={c:<22} p={p:.4f}")

    # LaTeX paragraph
    if "C0" in summary:
        c0 = summary["C0"]
        lines = ["\n% === PASTE THIS INTO evidence.tex §Context-Sensitivity ==="]
        lines.append(f"% C0 baseline: FPR={c0['fpr']:.1%} [{c0['ci'][0]:.1%}, {c0['ci'][1]:.1%}], N={c0['n']}")
        for ckey in ["C1", "C2", "C3"]:
            if ckey in summary:
                s = summary[ckey]
                lines.append(f"% {ckey}: FPR={s['fpr']:.1%} [{s['ci'][0]:.1%}, {s['ci'][1]:.1%}]")
        print("\n".join(lines))

        # Auto-generate evidence text
        results_by_cond = []
        for ckey in ["C0", "C1", "C2", "C3"]:
            if ckey not in summary:
                continue
            s = summary[ckey]
            t3 = s["tier_fprs"].get("T3")
            t3_str = f"{t3[0]:.0%}" if t3 else "—"
            results_by_cond.append(f"{CONDITION_LABELS[ckey]}: {s['fpr']:.1%} [{s['ci'][0]:.1%}, {s['ci'][1]:.1%}] overall, T3={t3_str}")

        print("\n% Suggested evidence paragraph:")
        print("% " + "; ".join(results_by_cond))
        c0_fpr = c0["fpr"]
        c1_fpr = summary.get("C1", {}).get("fpr")
        c2_fpr = summary.get("C2", {}).get("fpr")
        if c1_fpr is not None and c2_fpr is not None:
            reduction = (c0_fpr - min(c1_fpr, c2_fpr)) / c0_fpr * 100 if c0_fpr > 0 else 0
            if reduction < 10:
                interp = "minimal context-sensitivity"
                impl = "API-level filters are the dominant mechanism"
            elif reduction < 30:
                interp = "moderate context-sensitivity"
                impl = "partial mitigation via institutional framing is feasible"
            else:
                interp = "strong context-sensitivity"
                impl = "institutional context substantially mitigates over-refusal"
            print(f"% Interpretation: {interp} ({reduction:.0f}% FPR reduction from C0→best). {impl}.")

    # Save comparison JSON
    safe_model = model_id.replace("/", "_").replace(":", "_")
    out_path = RESULTS_DIR / f"comparison_{safe_model}.json"
    out = {"model": model_id, "conditions": {}}
    for ckey, s in summary.items():
        out["conditions"][ckey] = {
            "label": CONDITION_LABELS.get(ckey, ckey),
            "fpr": s["fpr"],
            "refused": s["refused"],
            "n": s["n"],
            "ci_lo": s["ci"][0],
            "ci_hi": s["ci"][1],
            "tier_fprs": {
                tk: {"fpr": v[0], "refused": v[1], "n": v[2]}
                for tk, v in s["tier_fprs"].items() if v is not None
            },
        }
    with open(out_path, "w") as f:
        json.dump(out, f, indent=2)
    print(f"\nComparison saved: {out_path}")


if __name__ == "__main__":
    main()
