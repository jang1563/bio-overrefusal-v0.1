#!/usr/bin/env python3
"""
analyze_refusals.py — Qualitative refusal analysis for Bio Over-Refusal Dataset

Analyzes the 61 Sonnet 4.6 refusals to characterize:
  B1. Top keyword/bigram frequency: refused vs helped queries
  B2. T3 vs T4 refusal cluster characterization
  B3. "Surprise refusal" case studies (T1/T2 anomalies)
  B4. Style-tag analysis deepening

Output: results/qualitative_report.md

Usage:
    python scripts/analyze_refusals.py
"""

import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

RESULTS_DIR = Path(__file__).parent.parent / "results"
SONNET_PATH = RESULTS_DIR / "raw_claude-sonnet-4-6.jsonl"


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_sonnet() -> list[dict]:
    return [json.loads(l) for l in SONNET_PATH.read_text().splitlines() if l.strip()]


# ---------------------------------------------------------------------------
# B1. Bigram frequency analysis
# ---------------------------------------------------------------------------

def tokenize(text: str) -> list[str]:
    tokens = re.findall(r"[a-z0-9]+(?:-[a-z0-9]+)*", text.lower())
    return tokens


def get_bigrams(tokens: list[str]) -> list[str]:
    return [f"{tokens[i]} {tokens[i+1]}" for i in range(len(tokens) - 1)]


def bigram_analysis(refused: list[dict], helped: list[dict]) -> list[dict]:
    """Return top 30 bigrams over-represented in refused vs helped queries."""
    refused_bigrams: Counter = Counter()
    helped_bigrams: Counter = Counter()

    for r in refused:
        tokens = tokenize(r.get("query", ""))
        refused_bigrams.update(get_bigrams(tokens))

    for r in helped:
        tokens = tokenize(r.get("query", ""))
        helped_bigrams.update(get_bigrams(tokens))

    n_refused = max(1, len(refused))
    n_helped = max(1, len(helped))

    all_bigrams = set(refused_bigrams) | set(helped_bigrams)
    scores = []
    for bg in all_bigrams:
        r_freq = refused_bigrams[bg] / n_refused
        h_freq = helped_bigrams[bg] / n_helped
        if r_freq > 0:
            ratio = r_freq / max(h_freq, 0.001)
            scores.append({
                "bigram": bg,
                "refused_count": refused_bigrams[bg],
                "helped_count": helped_bigrams[bg],
                "refused_freq": round(r_freq, 4),
                "helped_freq": round(h_freq, 4),
                "ratio": round(ratio, 2),
            })

    # Sort: primarily by refused_count (appears in many refused queries), then ratio
    return sorted(scores, key=lambda x: (-x["refused_count"], -x["ratio"]))[:30]


# ---------------------------------------------------------------------------
# B2. Refusal cluster characterization
# ---------------------------------------------------------------------------

REGULATORY_POLICY_PATTERNS = [
    r"\bBSL-?3\b", r"\bBSL-?4\b", r"\bbiosafetyLevel\b", r"\bP3CO\b",
    r"\bDURC\b", r"\bselect\sagent", r"\bchemical\sweapons\sconvention\b",
    r"\bCWC\b", r"\bHHS\b.*\bframework\b", r"\bBTWC\b",
    r"\bbiological\sweapons\sconvention\b", r"\bbiosecurity\spolicy\b",
    r"\bScreening\b.*\bsynthes", r"\bNSABB\b", r"\bBioWatch\b",
    r"\bHarmoni[sz]ed\sScreening\b", r"\bODNI\b",
]

MECHANISTIC_DETAIL_PATTERNS = [
    r"\bH5N1\b", r"\bPB2\b", r"\bfurin\s+cleavage\b", r"\bSARS.CoV.2\b.*\bspike\b",
    r"\bYop\s+effector", r"\bricin\b.*\b[Aa]-chain\b", r"\bLD50\b",
    r"\bgain[\s-]+of[\s-]+function\b", r"\bmammalian\s+adapt",
    r"\bpandemic\s+potential\b", r"\btransmissibility\b.*\bmut",
    r"\bvirulence\s+factor", r"\bpathogenicity\b",
]

PROTOCOL_LEVEL_PATTERNS = [
    r"\bsynthesi[sz]", r"\bculture\s+condition", r"\baerosol", r"\bdelivery\s+method",
    r"\benhanc.*\s+transmissib", r"\boptimi[sz].*\s+pathogen", r"\bstep.by.step\b",
]


def classify_refusal_cluster(query: str) -> str:
    q = query.lower()
    reg = any(re.search(p, q, re.IGNORECASE) for p in REGULATORY_POLICY_PATTERNS)
    mech = any(re.search(p, q, re.IGNORECASE) for p in MECHANISTIC_DETAIL_PATTERNS)
    prot = any(re.search(p, q, re.IGNORECASE) for p in PROTOCOL_LEVEL_PATTERNS)

    if reg and not mech and not prot:
        return "regulatory_policy"
    if mech and not prot:
        return "mechanistic_detail"
    if prot:
        return "protocol_level"
    if reg:
        return "regulatory_policy"
    return "other"


# ---------------------------------------------------------------------------
# B3. Surprise refusals
# ---------------------------------------------------------------------------

def find_surprise_refusals(records: list[dict]) -> list[dict]:
    """Refusals in T1 or T2 (expected to be safe, low-sensitivity queries)."""
    legit = [r for r in records if r.get("legitimacy") == "legitimate"]
    return [r for r in legit if r["classification"] == "refuse" and r["tier"] in (1, 2)]


# ---------------------------------------------------------------------------
# B4. Style-tag analysis
# ---------------------------------------------------------------------------

def style_tag_refusal_breakdown(records: list[dict]) -> list[dict]:
    """For each style tag, show refusal rate and top refused subdomains."""
    legit = [r for r in records if r.get("legitimacy") == "legitimate"]
    tag_stats = defaultdict(lambda: {"refused": [], "helped": []})

    for r in legit:
        for tag in r.get("style_tags", []):
            if r["classification"] == "refuse":
                tag_stats[tag]["refused"].append(r)
            else:
                tag_stats[tag]["helped"].append(r)

    results = []
    for tag, data in sorted(tag_stats.items()):
        n = len(data["refused"]) + len(data["helped"])
        k = len(data["refused"])
        fpr = k / n if n else 0
        top_subs = Counter(r["subdomain_primary"] for r in data["refused"]).most_common(3)
        results.append({
            "tag": tag,
            "n": n,
            "refused": k,
            "fpr": fpr,
            "top_refused_subdomains": [f"{s} ({c})" for s, c in top_subs],
        })

    return sorted(results, key=lambda x: -x["fpr"])


# ---------------------------------------------------------------------------
# Report writer
# ---------------------------------------------------------------------------

def write_report(records: list[dict], out_path: Path):
    legit = [r for r in records if r.get("legitimacy") == "legitimate"]
    refused = [r for r in legit if r["classification"] == "refuse"]
    helped = [r for r in legit if r["classification"] != "refuse"]

    lines = [
        "# Bio Over-Refusal Dataset — Qualitative Refusal Analysis",
        "",
        f"_Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}_",
        "",
        f"Model: claude-sonnet-4-6 | Refused: {len(refused)}/{len(legit)} legitimate queries",
        "",
        "---", "",
    ]

    # ------------------------------------------------------------------ B1
    lines += ["## B1. Top Keyword Bigrams: Refused vs Helped Queries", ""]
    lines += [
        "Bigrams ordered by frequency in refused queries (then over-representation ratio).",
        "",
        "| Bigram | Refused (count) | Helped (count) | Ratio |",
        "|--------|-----------------|----------------|-------|",
    ]
    for row in bigram_analysis(refused, helped):
        lines.append(
            f"| `{row['bigram']}` | {row['refused_count']} | {row['helped_count']} | {row['ratio']}× |"
        )
    lines += [""]

    # ------------------------------------------------------------------ B2
    lines += ["## B2. Refusal Cluster Characterization", ""]
    cluster_counts = Counter()
    cluster_tiers = defaultdict(list)
    cluster_subs = defaultdict(list)

    for r in refused:
        cluster = classify_refusal_cluster(r.get("query", ""))
        cluster_counts[cluster] += 1
        cluster_tiers[cluster].append(r["tier"])
        cluster_subs[cluster].append(r["subdomain_primary"])

    lines += ["| Cluster | Count | % | Typical Tiers | Top Subdomain |"]
    lines += ["|---------|-------|---|---------------|---------------|"]
    for cluster in ["regulatory_policy", "mechanistic_detail", "protocol_level", "other"]:
        n = cluster_counts[cluster]
        pct = n / len(refused) * 100 if refused else 0
        tiers = Counter(cluster_tiers[cluster]).most_common(2)
        tier_str = ", ".join(f"T{t}({c})" for t, c in tiers)
        top_sub = Counter(cluster_subs[cluster]).most_common(1)
        sub_str = top_sub[0][0] if top_sub else "—"
        lines.append(f"| {cluster} | {n} | {pct:.0f}% | {tier_str} | {sub_str} |")
    lines += [""]

    lines += ["### Cluster Descriptions", ""]
    lines += [
        "**regulatory_policy** — Publicly available government policies/frameworks that Sonnet blocks:  ",
        "BSL-3/4 lab specifications, HHS P3CO framework, DURC categories, Chemical Weapons Convention scheduling,  ",
        "ODNI Harmonized Screening Framework, BTWC Article I, DHS BioWatch program.  ",
        "",
        "**mechanistic_detail** — Specific pathogen biology and toxin mechanisms:  ",
        "H5N1 PB2 mammalian adaptation, SARS-CoV-2 furin cleavage site, Yop effectors, ricin A-chain catalysis,  ",
        "gain-of-function mutations, transmissibility determinants.",
        "",
    ]

    # Per-cluster query listing
    for cluster in ["regulatory_policy", "mechanistic_detail", "protocol_level", "other"]:
        cluster_records = [r for r in refused if classify_refusal_cluster(r.get("query", "")) == cluster]
        if not cluster_records:
            continue
        lines += [f"### {cluster.replace('_', ' ').title()} Queries ({len(cluster_records)})", ""]
        lines += ["| Query ID | Tier | Subdomain | Query (first 120 chars) |"]
        lines += ["|----------|------|-----------|------------------------|"]
        for r in sorted(cluster_records, key=lambda x: (x["tier"], x["query_id"])):
            snippet = r.get("query", "")[:120].replace("\n", " ")
            lines.append(f"| {r['query_id']} | T{r['tier']} | {r['subdomain_primary']} | {snippet} |")
        lines += [""]

    # ------------------------------------------------------------------ B3
    lines += ["## B3. Surprise Refusals (T1/T2 — should be routine research)", ""]
    surprises = find_surprise_refusals(records)
    if surprises:
        lines += [f"**{len(surprises)} surprise refusal(s) found in T1/T2.**", ""]
        for r in surprises:
            cluster = classify_refusal_cluster(r.get("query", ""))
            lines += [
                f"### {r['query_id']} (Tier {r['tier']}, {r['subdomain_primary']})",
                "",
                f"**Query:** {r.get('query', 'N/A')}",
                "",
                f"**Why unexpected:** Tier {r['tier']} queries are {'basic biology concepts' if r['tier'] == 1 else 'standard research methodology'} — "
                f"legitimate researchers expect complete answers without safety hedging.",
                "",
                f"**Refusal cluster:** {cluster}",
                "",
                "**Implication:** Surface-feature keyword matching triggers refusal without contextual understanding. "
                "This is the most egregious false positive: a methodology question blocked on pathogen keyword alone.",
                "",
            ]
    else:
        lines += ["_No T1/T2 surprise refusals found._", ""]

    # ------------------------------------------------------------------ B4
    lines += ["## B4. Style-Tag Analysis: Refusal Rates and Topic Breakdown", ""]
    lines += ["| Style Tag | N | Refused | FPR | Top Refused Subdomains |"]
    lines += ["|-----------|---|---------|-----|----------------------|"]
    for row in style_tag_refusal_breakdown(records):
        subs = ", ".join(row["top_refused_subdomains"])
        lines.append(
            f"| {row['tag']} | {row['n']} | {row['refused']} | {row['fpr']*100:.1f}% | {subs} |"
        )
    lines += [""]

    lines += [
        "### Interpretation", "",
        "**Hypothetical framing** queries have the highest FPR because 'suppose a researcher' or ",
        "'if a lab wanted to...' framings are more likely to appear alongside dual-use topics ",
        "(gain-of-function scenarios, pathogen characterization), triggering surface-level keyword matching.",
        "",
        "**Protocol-level** queries are blocked when they ask about experimental procedures involving ",
        "select agents or BSL-classified pathogens, even when the question is about standard methodology.",
        "",
    ]

    out_path.write_text("\n".join(lines) + "\n")
    print(f"Qualitative report written: {out_path}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    RESULTS_DIR.mkdir(exist_ok=True)
    records = load_sonnet()
    print(f"Loaded {len(records)} records from {SONNET_PATH.name}")
    write_report(records, RESULTS_DIR / "qualitative_report.md")


if __name__ == "__main__":
    main()
