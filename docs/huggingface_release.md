# Hugging Face Release Guide

This project keeps the Hugging Face dataset repository reproducible from the
GitHub source tree. The HF repo should contain the dataset card as `README.md`,
the JSONL data file, schema documentation, controlled vocabularies, license,
citation metadata, and safe summary reports.

## Prepare the Bundle

Use Python 3.10, 3.11, or 3.12.

```bash
python -m pip install -e ".[release]"
python scripts/prepare_hf_release.py --force --repo-id <hf-user-or-org>/bio-overrefusal
```

The script writes a local bundle to `build/huggingface_dataset/` and prints the
matching `huggingface-cli upload` command when `--repo-id` is supplied. It does
not upload anything by itself.

## Review Before Upload

Check these files in the generated bundle:

- `README.md` renders the YAML dataset card front matter.
- `README.md` contains a `configs` block that points the viewer only to
  `data/queries.jsonl`.
- `data/queries.jsonl` contains exactly 201 rows.
- `schema/jsonl_schema.md`, `schema/features.py`, and `schema/vocab.yaml` match the GitHub release.
- `MANIFEST.md` lists file sizes and SHA-256 hashes.
- No `results/raw_*.jsonl`, `results/llm_classified_*.jsonl`, or
  `results/summary_*.json` files are present.
- No machine-readable result tables such as `results/stats_table.json` or
  `results/fpr_table.csv` are present in the HF bundle; keep those on GitHub so
  the HF dataset builder does not treat them as data rows.

## Publish

After review:

```bash
huggingface-cli upload <hf-user-or-org>/bio-overrefusal build/huggingface_dataset . --repo-type dataset
```

Then open the dataset page and verify:

- The viewer shows the `train` split with 201 rows.
- `https://datasets-server.huggingface.co/is-valid?dataset=<repo-id>` reports
  `preview: true`; full `viewer/search/filter/statistics` may take additional
  worker time after upload.
- The license displays as `cc-by-nc-sa-4.0`.
- The first screen clearly frames the dataset as false-positive refusal
  evaluation, not harmful-content elicitation.
- The loading snippet works from a clean environment.

## Version Updates

For every public release, update `CHANGELOG.md`, `CITATION.cff`,
`dataset_card.md`, and the GitHub release tag together. The HF dataset repo
should be updated only after GitHub CI passes on the corresponding commit.
