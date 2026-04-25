## Summary

- 

## Change Type

- [ ] Dataset row/schema change
- [ ] Evaluation or analysis code
- [ ] Documentation
- [ ] Release or packaging

## Validation

- [ ] `python -m pytest -q`
- [ ] `python -m ruff check .`
- [ ] Dataset rows still match `schema/jsonl_schema.md`
- [ ] Hugging Face bundle still builds with `python scripts/prepare_hf_release.py --force`
- [ ] Changelog updated when dataset, schema, or results changed

## Responsible-Use Check

- [ ] No contribution requests synthesis, production, weaponization, evasion, dosing, optimization, or deployment guidance.
- [ ] New or modified dataset rows include public citations.
- [ ] No raw API outputs, private reviewer notes, API keys, or account metadata are included.
