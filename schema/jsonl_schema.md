# JSONL Schema — Bio Over-Refusal Dataset v0.1.0

Canonical record shape for `data/queries.jsonl`. Loaded into HuggingFace Datasets via the explicit `Features` declaration in [`tests/test_loader.py`](../tests/test_loader.py). Controlled vocabularies live in [`vocab.yaml`](vocab.yaml) — enum membership is enforced at load time by the loader smoke test.

---

## Top-level fields

| Field | Type | Required | Description |
|---|---|---|---|
| `query_id` | string | yes | Stable identifier. Convention: `t{tier}_{subdomain}_{NNNN}` where `subdomain` is the full `subdomain_primary` value (e.g. `t1_virology_0042`, `t3_cell_biology_0007`). |
| `query` | string | yes | The natural-language query a researcher would send to Claude. Single sentence or short paragraph. |
| `tier` | int32 (1–5) | yes | Final (adjudicated) tier. Starts equal to `annotator_1_tier`; overwritten by Phase 3 adjudication. |
| `subdomain_primary` | string enum | yes | Dominant subdomain (`vocab.yaml::subdomains`). Used for stratified analysis. |
| `subdomain_secondary` | list[string enum] | yes (may be empty list) | Additional subdomains the query touches. Descriptive, not stratified. |
| `legitimacy` | string enum | yes | Final legitimacy label (`vocab.yaml::legitimacy`). Records with `likely_misuse` must be removed before Phase 6 release. |
| `biological_reasoning` | string | yes | 2–4 sentences explaining why the query falls at this tier. Free text. |
| `legitimate_contexts` | list[context] | yes (≥2 items) | Realistic researcher personas that make this query benign. See `context` schema below. |
| `danger_shift_contexts` | list[context] | yes (≥2 items for tiers 3–5; may be empty for tiers 1–2) | Scenarios where the same query pattern would raise concern. See `context` schema below. |
| `style_tags` | list[string enum] | yes (≥1 item) | Phrasing styles (`vocab.yaml::style_tags`). |
| `citations` | list[citation] | yes (≥1 item) | Public sources where this question is already addressed. See `citation` schema below. |
| `annotator_1_tier` | int32 (1–5) | yes | Tier assigned by annotator 1 at authoring time. Immutable after Phase 1 freeze. |
| `annotator_1_legitimacy` | string enum | yes | Legitimacy assigned by annotator 1. Immutable after Phase 1 freeze. |
| `annotator_2_tier` | int32 (1–5) or null | no | Blinded second-annotator tier (Phase 3). Nullable. |
| `annotator_2_legitimacy` | string enum or null | no | Blinded second-annotator legitimacy. Nullable. |
| `adjudicated_tier` | int32 (1–5) or null | no | Post-disagreement adjudicated tier if annotators differ. Nullable. |
| `adjudicated_legitimacy` | string enum or null | no | Post-disagreement adjudicated legitimacy. Nullable. |
| `reviewer_comments` | string or null | no | Free-text reviewer notes (aggregated from Phase 2/3). Nullable. |
| `schema_version` | string | yes | Semver, starts at `"0.1.0"`. Bumped per the versioning rules below. |

## `context` object schema

Used for both `legitimate_contexts` and `danger_shift_contexts` list items.

| Field | Type | Required | Description |
|---|---|---|---|
| `role` | string enum | yes | Researcher role archetype (`vocab.yaml::researcher_roles`). |
| `setting` | string | yes | Short free-text institutional / project setting (e.g., "R1 university virology lab studying influenza HA receptor binding for the candidate's 2nd-year qualifying exam"). |
| `description` | string | yes | 1–2 sentences fleshing out the scenario. |
| `durc_category` | string enum or null | no | For `danger_shift_contexts` only: which NSABB DURC category the shifted scenario would fall under (`vocab.yaml::nsabb_durc_categories`). Null when no DURC category applies and for all `legitimate_contexts` entries. |

## `citation` object schema

| Field | Type | Required | Description |
|---|---|---|---|
| `source_type` | string enum | yes | `vocab.yaml::citation_source_types`. |
| `identifier` | string | yes | Short human-readable reference (e.g., "Janeway's Immunobiology 10e, ch. 4" or "Nat Rev Micro 2024;22:543"). |
| `url` | string or null | no | DOI, arXiv URL, or publisher URL where available. Null for textbook-only references. |

---

## Versioning rules

Every record carries `schema_version`. Bumping rules follow semver:

- **Major bump (`X` → `X+1`).** Any field rename, type change, or enum-value removal. Requires re-emitting every record at the new schema version and archiving the prior `queries.jsonl` under `data/archive/v{prev}.jsonl`.
- **Minor bump (`Y` → `Y+1`).** Additive change: new optional field, new enum value. Existing records remain valid; new records carry the higher version.
- **Patch bump (`Z` → `Z+1`).** Typo correction in an enum value or description — but only when meaning is unchanged. If meaning changes, it is a major bump.

After a major or minor bump:
1. Update `schema/vocab.yaml` and `schema/jsonl_schema.md`.
2. Emit a new `data/queries.jsonl` where every record's `schema_version` reflects the new version.
3. Archive the prior file under `data/archive/v{prev_version}.jsonl`.
4. Record the diff in the project's top-level `CHANGELOG.md`.

---

## HuggingFace loading

The canonical loader pattern is:

```python
from datasets import load_dataset
from tests.test_loader import make_features

ds = load_dataset(
    "json",
    data_files={"train": "data/queries.jsonl"},
    features=make_features(),
)
```

Explicit `features=` bypasses HF's type inference, which otherwise drifts on nullable fields and heterogeneous list-of-dict structures (see Research/02 §1.1). The smoke test in [`tests/test_loader.py`](../tests/test_loader.py) asserts the fixture loads against `make_features()`.

---

## Fields reserved for Phase 4/5 outputs

These live in `data/claude_responses.jsonl`, **not** in `queries.jsonl`. Keyed back to `query_id`.

| Field | Type | Description |
|---|---|---|
| `query_id` | string | Foreign key into `queries.jsonl`. |
| `provider` / `model` / `model_version_exact` | string | Claude model identifiers. |
| `batch_id` / `request_id` / `custom_id` | string | API provenance. |
| `system_prompt_sha256` | string | Hash ref into `provenance/run_<UTC>.json`. |
| `temperature` / `max_tokens` | float / int | Sampling parameters. |
| `response_text` | string | Claude's answer. |
| `stop_reason` / `usage` | string / object | API metadata. |
| `api_timestamp` / `script_sha` / `env_lockfile_sha256` | string | Reproducibility ties. |
| `classification` | string enum | `vocab.yaml::response_classes`. Filled by the judge pass. |
| `judge_model` / `judge_rubric_hash` | string | Judge provenance. |

See `Research/03 §5.1` for the full response-row spec and provenance tie-ins.
