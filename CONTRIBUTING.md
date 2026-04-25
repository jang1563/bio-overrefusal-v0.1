# Contributing

Thanks for helping improve Bio Over-Refusal. This repository is a benchmark for
legitimate biology research queries, so contributions need to preserve both
scientific usefulness and dual-use caution.

## Good Contributions

- Schema fixes, loader improvements, documentation, and reproducibility work.
- Additional citations that clarify why an existing query is legitimate.
- New benign biology queries that fit the tier definitions in
  [`tier_definitions.md`](tier_definitions.md).
- Independent evaluation results that include model version, provider, date,
  prompt, and classification method.

## Out of Scope

- Queries that request synthesis, production, weaponization, evasion, dosing,
  optimization, or deployment of harmful biological agents or toxins.
- Prompt-injection or jailbreak examples.
- Raw API responses that contain secrets, account metadata, or private reviewer
  notes.

## Pull Request Checklist

Before opening a PR:

1. Use Python 3.10, 3.11, or 3.12.
2. Run `python -m pytest -q` and `python -m ruff check .`.
3. Keep `data/queries.jsonl` valid against `schema/jsonl_schema.md`.
4. Include at least one public citation for every new query.
5. Do not commit ignored evaluation artifacts such as `results/raw_*.jsonl`.
6. Update `CHANGELOG.md` for dataset, schema, or result changes.
7. Check [`SAFETY.md`](SAFETY.md) before changing row content or adding evaluation artifacts.

For new dataset rows, prefer small, reviewable batches and explain the tiering
rationale in the PR description.
