# Public Release Checklist

Use this checklist before making the GitHub repository public or publishing the
Hugging Face dataset repository.

## GitHub

1. Use Python 3.10, 3.11, or 3.12 and run `python -m pytest -q` plus `python -m ruff check .`.
2. Confirm `git status --short` only shows intended changes.
3. Confirm files matched by `.gitignore` are not tracked
   (`git ls-files | git check-ignore --stdin --no-index` should be empty):
   - `results/raw_*.jsonl`, `results/llm_classified_*.jsonl`, `results/summary_*.json`
   - any working notes or internal review artifacts
4. Review `README.md`, `dataset_card.md`, `tier_definitions.md`, and
   `results/stats_report.md` for public-facing claims and limitations.
5. Set the repository description to:
   `Domain-expert-authored benchmark for LLM over-refusal on legitimate biology research queries.`
6. Add repository topics:
   `ai-safety`, `biosecurity`, `biology`, `llm-evaluation`, `benchmark`,
   `over-refusal`, `huggingface-datasets`.
7. Create an annotated release tag, for example:
   `git tag -a v0.1.0 -m "Bio Over-Refusal Dataset v0.1.0"`.

## Hugging Face Dataset Repo

The Hugging Face dataset repository should contain the files needed for the
dataset viewer and for reproducible evaluation:

- `README.md` copied from this repository's `dataset_card.md`
- `data/queries.jsonl`
- `schema/jsonl_schema.md`
- `schema/features.py`
- `schema/vocab.yaml`
- `tier_definitions.md`
- `LICENSE`
- Optional generated summaries from `results/`, excluding raw model responses
  and excluding machine-readable `.json`/`.csv` result tables that the HF dataset
  builder may try to ingest as rows

Build the upload bundle from GitHub with:

```bash
python scripts/prepare_hf_release.py --force --repo-id <hf-user-or-org>/bio-overrefusal
```

Before publishing, open the dataset page and check:

1. The dataset card renders with the YAML front matter intact.
2. The YAML `configs` block points only to `data/queries.jsonl`.
3. The preview/viewer shows exactly 201 rows in the `train` split.
4. The field types match `schema/jsonl_schema.md`.
5. The license displays as `cc-by-nc-sa-4.0`.
6. The first-screen summary clearly says the dataset is for false-positive
   refusal evaluation, not harmful-content elicitation.

## Versioning

- Patch release: documentation fixes or non-semantic citation typo fixes.
- Minor release: additive optional fields, new rows, or new model-result tables.
- Major release: schema-breaking field rename, type change, or enum removal.

Every release should update `CHANGELOG.md`, `dataset_card.md`, and the citation
metadata if the version or release date changes.
