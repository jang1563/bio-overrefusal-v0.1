#!/usr/bin/env python3
"""
build_control_from_published.py — Assemble the should-refuse calibration control
by REUSING published, peer-reviewed harmful-bio safety benchmarks.

This tool deliberately does NOT author harmful prompts. It samples the
*should-refuse* (harmful) split from existing public benchmarks whose primary
stated purpose is exactly LLM-safety / red-team / oversight research, maps each
item to this project's subdomain + uplift-category schema, and writes a GATED
control file. Reusing public items adds no new attention hazard.

Sources (bio splits only):
  - SOSBench           SOSBench/SOSBench            field `goal`, filter subject==biology   (arXiv:2505.21605)
  - SciSafeEval        Tianhao0x01/SciSafeEval      config `biology`, field `instruction`    (arXiv:2410.03769, CC BY-NC 4.0)
  - SORRY-Bench (opt)  sorry-bench/sorry-bench-202406  GATED — needs your HF access; bio/chem-weapon classes (arXiv:2406.14598)

Disclosure (see docs/should_refuse_control_spec.md):
  - Prompt BODIES are written ONLY to data/control/should_refuse.jsonl (gitignored).
  - This tool PRINTS aggregate provenance only (counts) — never prompt text.
  - Published outputs are IDs/labels + aggregate TPR; never the prompt bodies.

Usage:
    python scripts/build_control_from_published.py            # dry-run: print distribution only, write nothing
    python scripts/build_control_from_published.py --write    # materialize the GATED file (run under biosafety oversight)
    python scripts/build_control_from_published.py --n 30 --min-per-subdomain 2 --include-sorrybench

Run --write only with institutional/biosafety sign-off on the sourcing.
"""

import argparse
import hashlib
import json
import random
import re
from collections import Counter, defaultdict
from pathlib import Path

OUT = Path(__file__).parent.parent / "data" / "control" / "should_refuse.jsonl"

SUBDOMAINS = [
    "virology", "toxicology", "synthetic_biology", "genomics", "pathogen_biology",
    "immunology", "biochemistry", "cell_biology", "microbiology", "structural_biology",
]

# Keyword -> subdomain (first match wins; order = specificity). Operates on prompt
# text in memory only; never displayed. Tunable; review the dry-run distribution.
SUBDOMAIN_PATTERNS = [
    ("virology", r"\b(virus|viral|influenza|coronavirus|sars|h5n1|ebola|poxvirus|virion|capsid)\b"),
    ("toxicology", r"\b(toxin|ricin|botulinum|nerve agent|organophosphate|venom|lethal dose|ld50|saxitoxin)\b"),
    ("pathogen_biology", r"\b(anthrax|plague|yersinia|francisella|bacillus|select agent|tularemia|burkholderia|pathogen)\b"),
    ("synthetic_biology", r"\b(de novo|synthesi[sz]e|gene synthesis|plasmid|assembl|crispr|chassis|biocontainment)\b"),
    ("genomics", r"\b(genome|genomic|sequenc|nucleotide|oligonucleotide|gene editing)\b"),
    ("immunology", r"\b(immun|cytokine|antibody|antigen|vaccine|interferon|complement)\b"),
    ("structural_biology", r"\b(crystal structure|cryo-?em|protein structure|fold|x-ray|active site)\b"),
    ("biochemistry", r"\b(enzyme|catalyti|metaboli|biochem|substrate|inhibitor|pathway)\b"),
    ("microbiology", r"\b(bacteri|antibiotic|resistance|culture|fermentation|spore|microb)\b"),
    ("cell_biology", r"\b(cell|membrane|organelle|apoptosi|receptor|endosom|trafficking)\b"),
]

UPLIFT_PATTERNS = [
    ("synthesis", r"\b(synthesi[sz]e|produc|manufactur|make|prepare|cultivat|grow)\b"),
    ("enhancement", r"\b(enhanc|increase|gain[- ]of[- ]function|more (transmissible|virulent|lethal)|optimi[sz]e potency)\b"),
    ("weaponization", r"\b(weapon|aerosol|disperse|disseminat|deliver|payload|munition)\b"),
    ("evasion", r"\b(evade|bypass|undetect|avoid detection|defeat|circumvent screening)\b"),
    ("acquisition", r"\b(acquire|obtain|purchase|procure|source|where to (get|buy))\b"),
]


def _match(text: str, patterns, default: str) -> str:
    t = text.lower()
    for label, pat in patterns:
        if re.search(pat, t):
            return label
    return default


def map_subdomain(prompt: str) -> str:
    return _match(prompt, SUBDOMAIN_PATTERNS, default="pathogen_biology")


def map_uplift(prompt: str) -> str:
    return _match(prompt, UPLIFT_PATTERNS, default="other")


def _norm_key(prompt: str) -> str:
    return hashlib.sha1(re.sub(r"\s+", " ", prompt.strip().lower()).encode()).hexdigest()


# --- source loaders: each yields dicts {source_benchmark, source_id, source_license, query} ---

def load_sosbench():
    from datasets import load_dataset
    ds = load_dataset("SOSBench/SOSBench", split="train")
    for i, row in enumerate(ds):
        if (row.get("subject") or "").strip().lower() == "biology":
            g = (row.get("goal") or "").strip()
            if g:
                yield {"source_benchmark": "SOSBench", "source_id": f"sosbench:{i}",
                       "source_license": "other (academic safety research)", "query": g}


def load_scisafeeval():
    from datasets import load_dataset
    dd = load_dataset("Tianhao0x01/SciSafeEval", "biology")
    for split in dd:  # gene_*/protein_* splits
        for row in dd[split]:
            instr = (row.get("instruction") or "").strip()
            if instr:
                yield {"source_benchmark": "SciSafeEval", "source_id": f"scisafeeval:{split}:{row.get('idx')}",
                       "source_license": "cc-by-nc-4.0", "query": instr}


def load_sorrybench():
    from datasets import load_dataset
    ds = load_dataset("sorry-bench/sorry-bench-202406", split="train")  # GATED: requires HF access
    bio = re.compile(r"\b(biolog|pathogen|toxin|virus|bioweapon|chemical weapon)\b", re.I)
    for i, row in enumerate(ds):
        cat = " ".join(str(row.get(k, "")) for k in ("category", "subcategory", "turns"))
        prompt = row.get("turns")
        prompt = prompt[0] if isinstance(prompt, list) and prompt else (row.get("prompt") or "")
        if prompt and bio.search(cat + " " + str(prompt)):
            yield {"source_benchmark": "SORRY-Bench", "source_id": f"sorrybench:{i}",
                   "source_license": "other (gated)", "query": str(prompt).strip()}


def select(items, n: int, min_per_subdomain: int, seed: int = 0):
    """Deterministic balanced sample: ~min per subdomain, then round-robin fill to n."""
    rng = random.Random(seed)
    by_sd = defaultdict(list)
    for it in items:
        by_sd[it["subdomain_primary"]].append(it)
    for sd in by_sd:
        rng.shuffle(by_sd[sd])
    chosen, used = [], set()
    # pass 1: guarantee floor per subdomain
    for sd in SUBDOMAINS:
        for it in by_sd.get(sd, [])[:min_per_subdomain]:
            chosen.append(it)
            used.add(id(it))
    # pass 2: round-robin fill
    pools = {sd: [it for it in by_sd.get(sd, []) if id(it) not in used] for sd in SUBDOMAINS}
    while len(chosen) < n and any(pools.values()):
        for sd in SUBDOMAINS:
            if len(chosen) >= n:
                break
            if pools[sd]:
                chosen.append(pools[sd].pop())
    return chosen[:n]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=25, help="target control-set size")
    ap.add_argument("--min-per-subdomain", type=int, default=2)
    ap.add_argument("--write", action="store_true", help="materialize the GATED file (biosafety sign-off required)")
    ap.add_argument("--include-sorrybench", action="store_true", help="add gated SORRY-Bench (needs HF access)")
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()

    loaders = [load_sosbench, load_scisafeeval]
    if args.include_sorrybench:
        loaders.append(load_sorrybench)

    seen, items = set(), []
    for loader in loaders:
        try:
            for rec in loader():
                key = _norm_key(rec["query"])
                if key in seen:
                    continue
                seen.add(key)
                rec["subdomain_primary"] = map_subdomain(rec["query"])
                rec["uplift_category"] = map_uplift(rec["query"])
                items.append(rec)
        except Exception as e:
            print(f"[warn] {loader.__name__} failed: {e}")

    if not items:
        print("No items loaded. Check network / dataset access (SORRY-Bench is gated).")
        return

    chosen = select(items, args.n, args.min_per_subdomain, args.seed)
    # assign control_ids
    counters = Counter()
    for it in chosen:
        sd = it["subdomain_primary"]
        counters[sd] += 1
        it["control_id"] = f"sr_{sd}_{counters[sd]:04d}"

    # ---- aggregate provenance ONLY (no prompt text) ----
    print(f"Loaded {len(items)} unique candidate items; selected {len(chosen)} (target {args.n}).")
    print("By source:    ", dict(Counter(it["source_benchmark"] for it in chosen)))
    print("By subdomain: ", dict(Counter(it["subdomain_primary"] for it in chosen)))
    print("By uplift:    ", dict(Counter(it["uplift_category"] for it in chosen)))

    if not args.write:
        print("\n[dry-run] wrote nothing. Re-run with --write (and biosafety sign-off) to materialize the gated file.")
        return

    OUT.parent.mkdir(parents=True, exist_ok=True)
    fields = ["control_id", "subdomain_primary", "uplift_category", "source_benchmark", "source_id", "source_license", "query"]
    with OUT.open("w") as f:
        for it in chosen:
            f.write(json.dumps({k: it[k] for k in fields}, ensure_ascii=False) + "\n")
    print(f"\nWrote {len(chosen)} gated control items -> {OUT} (gitignored). Do not commit or republish prompt bodies.")


if __name__ == "__main__":
    main()
