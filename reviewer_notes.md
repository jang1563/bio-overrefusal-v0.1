# Reviewer Notes — Bio Over-Refusal Dataset v0.1.0

Log of expert reviewer feedback, self-audit findings, and adjudicated decisions.
Maintained per Methodology (Research/02_Methodology_Protocol.md §Phase 3).

---

## Phase 1 — Seed Set (100 queries, Tiers 1–5)

### Review status

**Expert reviewer circulation: SKIPPED**
Decision date: 2026-04-17
Reason: Project timeline. Expert reviewer recruitment (Section 11, Open Decisions)
deferred to post-expansion Phase 3. Inter-annotator agreement (Cohen's kappa) will
be assessed on the full 200+ query set rather than the 100-query seed set.

### Self-audit findings (2026-04-17)

Conducted by: primary annotator (dataset author)
Scope: All 100 seed queries in data/queries.jsonl

**Finding 1 — Style tag distribution gap**
- hypothetical: 2% (5 queries) vs. 15% target
- protocol_level: 9% (18 queries) vs. 20% target
- Action: Phase 2 expansion (Task 10) must include ≥15 hypothetical-tagged queries
  and ≥20 protocol_level-tagged queries to reach target distribution.

**Finding 2 — Structural_biology T4 gap**
- Tier 4 seeds contain 0 structural_biology queries; quota requires 2.
- Action: Phase 2 expansion must include ≥2 T4 structural_biology queries.
  Candidates: pore-forming toxin structural comparison; pathogen surface protein
  structure-function for antibody development; cryo-EM reconstruction of
  select-agent virion components.

**Finding 3 — DURC category coverage confirmed adequate**
- All 7 NSABB DURC categories appear ≥3 times across Tiers 3–5 ✓
- enhance_harmful_consequences dominated (55 instances) — expected given Tier 4/5
  scope; other categories have adequate representation.

**Finding 4 — Legitimacy distribution appropriate**
- Tiers 1–4: 100% legitimate; Tier 5: 100% ambiguous ✓
- No likely-misuse queries identified in self-audit.

**Finding 5 — Tier 3 citation quality note**
- Several Tier 3 entries cite hypothetical regulatory framework documents (e.g.,
  "RCSB PDB, Data Usage Policy"). These should be verified as active URLs before
  Phase 6 release. Flag for pre-release red-team checklist §A.

**Finding 6 — Biological reasoning length**
- Tier 5 entries have shorter biological_reasoning fields (due to annotation
  generation constraints). Expansion annotations should target 3–4 full sentences.
  Existing Tier 5 entries will be reviewed in Phase 3 and expanded if needed.

### Tier definition stability assessment

Tier definitions reviewed against all 100 seed queries. No seed query required
reclassification. Operational criteria in tier_definitions.md are confirmed stable
for Phase 2 expansion.

Tier boundary cases identified during seeding:
- t5_toxicology_0002 (BoNT clinical question): internal note that this is arguably
  Tier 2, included in Tier 5 specifically to document classifier over-triggering.
  If kappa analysis shows annotator disagreement about tier placement, reclassify
  to Tier 2 with a note in disagreements.md.
- t5_immunology_0002 (HIV Fas/FasL): same — arguably Tier 2 or 3; included in
  Tier 5 as documentation of over-refusal pattern.

---

## Phase 2 — Expansion to 200 queries (planned)

Target start: 2026-04-17 (immediate, following Phase 1 self-audit)
Expert reviewer recruitment: deferred to Phase 3

Expansion targets:
- Tier 1: +30 queries (20 seeds → 50 final)
- Tier 2: +30 queries (20 seeds → 50 final)
- Tier 3: +20 queries (20 seeds → 40 final)
- Tier 4: +20 queries (20 seeds → 40 final)
- Tier 5: 0 (already at quota)

Expansion constraints from self-audit:
1. ≥15 hypothetical-style queries across T1–T4
2. ≥20 protocol_level-style queries across T1–T4
3. ≥2 T4 structural_biology queries
4. Ensure subdomain floor (≥15 per subdomain across 200 queries) is met at close

---

## Phase 3 — Inter-annotator agreement (planned)

Second annotator: TBD (recruitment deferred; candidates include former SOMA
collaborators or biodefense-adjacent academics)
Target: Cohen's kappa > 0.7 on legitimacy labels
Focus: Tier 4 and Tier 5 queries (highest disagreement expected)
Disagreement documentation: data/disagreements.md
