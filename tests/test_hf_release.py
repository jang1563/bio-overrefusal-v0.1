from pathlib import Path

from scripts.prepare_hf_release import PROJECT_ROOT, build_hf_release


def test_hf_release_bundle_contains_public_files_only(tmp_path: Path) -> None:
    out_dir = tmp_path / "hf_dataset"

    copied = build_hf_release(out_dir, force=True)
    copied_relpaths = {path.relative_to(out_dir).as_posix() for path in copied}

    assert "README.md" in copied_relpaths
    assert "data/queries.jsonl" in copied_relpaths
    assert "schema/jsonl_schema.md" in copied_relpaths
    assert "schema/features.py" in copied_relpaths
    assert "schema/vocab.yaml" in copied_relpaths
    assert "tier_definitions.md" in copied_relpaths
    assert "LICENSE" in copied_relpaths
    assert "CITATION.cff" in copied_relpaths
    assert "MANIFEST.md" in copied_relpaths

    assert (out_dir / "README.md").read_text() == (
        PROJECT_ROOT / "dataset_card.md"
    ).read_text()
    assert not list(out_dir.glob("results/raw_*.jsonl"))
    assert not list(out_dir.glob("results/llm_classified_*.jsonl"))
    assert not list(out_dir.glob("results/summary_*.json"))

    manifest = (out_dir / "MANIFEST.md").read_text()
    assert "Raw provider outputs are intentionally excluded" in manifest
