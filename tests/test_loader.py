"""Smoke test — load the 5-row fixture with an explicit HuggingFace Features schema.

Invocation:
    python -m tests.test_loader                # from project root
    pytest tests/test_loader.py                 # if pytest is preferred

Purpose:
    (1) Freeze the Features declaration that every `data/queries.jsonl` must load against.
    (2) Catch schema drift before it reaches the evaluation pipeline.
    (3) Validate enum membership against schema/vocab.yaml.

Explicit features= bypasses HF's type inference, which drifts on
nullable fields and heterogeneous list-of-dict structures in streaming mode.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from schema.features import make_features

FIXTURE_PATH = Path(__file__).parent / "fixture_5rows.jsonl"
DATASET_PATH = Path(__file__).parent.parent / "data" / "queries.jsonl"
DATASET_CARD_PATH = Path(__file__).parent.parent / "dataset_card.md"
VOCAB_PATH = Path(__file__).parent.parent / "schema" / "vocab.yaml"
EXPECTED_SCHEMA_VERSION = "0.1.0"
EXPECTED_TIER_COUNTS = {1: 57, 2: 41, 3: 43, 4: 40, 5: 20}
FEATURE_FIELD_NAMES = (
    "query_id",
    "query",
    "tier",
    "subdomain_primary",
    "subdomain_secondary",
    "legitimacy",
    "biological_reasoning",
    "legitimate_contexts",
    "danger_shift_contexts",
    "style_tags",
    "citations",
    "annotator_1_tier",
    "annotator_1_legitimacy",
    "annotator_2_tier",
    "annotator_2_legitimacy",
    "adjudicated_tier",
    "adjudicated_legitimacy",
    "reviewer_comments",
    "schema_version",
)

def load_vocab() -> dict:
    import yaml

    return yaml.safe_load(VOCAB_PATH.read_text())


def load_dataset_card_metadata() -> dict:
    import yaml

    text = DATASET_CARD_PATH.read_text()
    if not text.startswith("---\n"):
        raise AssertionError("dataset_card.md must start with YAML front matter")
    _, yaml_block, _ = text.split("---", 2)
    return yaml.safe_load(yaml_block)


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


def load_rows() -> list[dict]:
    return load_jsonl(FIXTURE_PATH)


def assert_enums(rows: list[dict], vocab: dict) -> None:
    allowed_subdomains = set(vocab["subdomains"])
    allowed_legitimacy = set(vocab["legitimacy"])
    allowed_style_tags = set(vocab["style_tags"])
    allowed_citation_types = set(vocab["citation_source_types"])
    allowed_roles = set(vocab["researcher_roles"])
    allowed_durc = set(vocab["nsabb_durc_categories"])
    allowed_tiers = set(int(k) for k in vocab["tiers"].keys())

    for r in rows:
        qid = r["query_id"]
        assert r["tier"] in allowed_tiers, f"{qid}: tier {r['tier']} not in vocab"
        assert r["subdomain_primary"] in allowed_subdomains, f"{qid}: bad subdomain_primary"
        for s in r["subdomain_secondary"]:
            assert s in allowed_subdomains, f"{qid}: bad subdomain_secondary {s}"
        assert r["legitimacy"] in allowed_legitimacy, f"{qid}: bad legitimacy"
        for tag in r["style_tags"]:
            assert tag in allowed_style_tags, f"{qid}: bad style_tag {tag}"
        for cit in r["citations"]:
            assert cit["source_type"] in allowed_citation_types, f"{qid}: bad citation source_type {cit['source_type']}"
        for ctx in r["legitimate_contexts"] + r["danger_shift_contexts"]:
            assert ctx["role"] in allowed_roles, f"{qid}: bad role {ctx['role']}"
            if ctx.get("durc_category") is not None:
                assert ctx["durc_category"] in allowed_durc, f"{qid}: bad durc_category {ctx['durc_category']}"


REQUIRED_FIELDS = (
    "query_id",
    "query",
    "tier",
    "subdomain_primary",
    "subdomain_secondary",
    "legitimacy",
    "biological_reasoning",
    "legitimate_contexts",
    "danger_shift_contexts",
    "style_tags",
    "citations",
    "annotator_1_tier",
    "annotator_1_legitimacy",
    "schema_version",
)


def assert_row_invariants(rows: list[dict]) -> None:
    seen_query_ids = set()
    for r in rows:
        qid = r["query_id"]
        assert qid not in seen_query_ids, f"{qid}: duplicate query_id"
        seen_query_ids.add(qid)
        for f in REQUIRED_FIELDS:
            assert r.get(f) is not None, f"{qid}: required field {f!r} is null or missing"
        assert r["schema_version"] == EXPECTED_SCHEMA_VERSION, f"{qid}: schema drift"
        assert 1 <= r["tier"] <= 5, f"{qid}: tier {r['tier']} out of range"
        assert 1 <= r["annotator_1_tier"] <= 5, f"{qid}: annotator_1_tier out of range"
        assert r["legitimacy"] == r["annotator_1_legitimacy"], (
            f"{qid}: final and annotator_1 legitimacy differ before adjudication"
        )
        qid_match = re.fullmatch(r"t([1-5])_([a-z_]+)_(\d{4})", qid)
        assert qid_match, f"{qid}: query_id must match tN_subdomain_NNNN"
        assert qid_match.group(2) == r["subdomain_primary"], (
            f"{qid}: query_id subdomain must match subdomain_primary"
        )
        assert len(r["legitimate_contexts"]) >= 2, f"{qid}: need >=2 legitimate_contexts"
        assert len(r["style_tags"]) >= 1, f"{qid}: need >=1 style_tag"
        assert len(r["citations"]) >= 1, f"{qid}: need >=1 citation"
        # Tier-conditional: tiers 3-5 must have >=2 danger_shift_contexts.
        if r["tier"] >= 3:
            assert len(r["danger_shift_contexts"]) >= 2, (
                f"{qid}: tier {r['tier']} needs >=2 danger_shift_contexts"
            )
        # Null-discipline: durc_category on legitimate_contexts must be null.
        for ctx in r["legitimate_contexts"]:
            assert ctx.get("durc_category") is None, (
                f"{qid}: legitimate_contexts[].durc_category must be null"
            )


def assert_release_dataset_shape(rows: list[dict]) -> None:
    from collections import Counter

    tier_counts = Counter(r["tier"] for r in rows)
    legitimacy_counts = Counter(r["legitimacy"] for r in rows)
    subdomain_counts = Counter(r["subdomain_primary"] for r in rows)

    assert len(rows) == 201, f"Expected 201 dataset rows, got {len(rows)}"
    assert dict(tier_counts) == EXPECTED_TIER_COUNTS
    assert legitimacy_counts == {"legitimate": 181, "ambiguous": 20}
    assert "likely_misuse" not in legitimacy_counts
    assert all(count >= 15 for count in subdomain_counts.values()), (
        f"Subdomain coverage below 15: {dict(subdomain_counts)}"
    )
    for r in rows:
        expected_legitimacy = "ambiguous" if r["tier"] == 5 else "legitimate"
        assert r["legitimacy"] == expected_legitimacy, (
            f"{r['query_id']}: tier {r['tier']} should be {expected_legitimacy}"
        )


def test_load() -> None:
    rows = load_rows()
    assert len(rows) == 5, f"Expected 5 fixture rows, got {len(rows)}"

    assert_row_invariants(rows)
    for r in rows:
        assert r["tier"] == 1, f"{r['query_id']}: fixture rows are all Tier 1 by design"

    try:
        vocab = load_vocab()
    except ModuleNotFoundError:
        print("WARN: PyYAML not installed; skipping vocab enum checks.", file=sys.stderr)
    else:
        assert_enums(rows, vocab)

    try:
        from datasets import Dataset
    except ModuleNotFoundError:
        print("WARN: `datasets` not installed; skipping HF Features load.", file=sys.stderr)
        return

    features = make_features()
    ds = Dataset.from_list(rows, features=features)
    assert len(ds) == 5
    assert set(ds.column_names) == set(features.keys())
    print(f"OK [from_list]: loaded {len(ds)} rows with schema v{ds[0]['schema_version']}")

    assert_load_via_load_dataset(features)


def assert_load_via_load_dataset(features) -> None:
    """Exercise the documented `load_dataset("json", ...)` path from jsonl_schema.md.

    This catches issues (esp. with nullable int fields) that `Dataset.from_list`
    hides because it bypasses the JSON streaming loader's type inference.
    """
    try:
        from datasets import load_dataset
    except ModuleNotFoundError:
        print("WARN: `datasets` not installed; skipping load_dataset path.", file=sys.stderr)
        return

    ds = load_dataset(
        "json",
        data_files={"train": str(FIXTURE_PATH)},
        features=features,
    )["train"]
    assert len(ds) == 5
    assert set(ds.column_names) == set(features.keys())
    print(f"OK [load_dataset]: loaded {len(ds)} rows from {FIXTURE_PATH.name}")


def test_full_dataset_release_invariants() -> None:
    rows = load_jsonl(DATASET_PATH)
    assert_release_dataset_shape(rows)
    assert_row_invariants(rows)

    try:
        vocab = load_vocab()
    except ModuleNotFoundError:
        print("WARN: PyYAML not installed; skipping vocab enum checks.", file=sys.stderr)
    else:
        assert_enums(rows, vocab)


def test_dataset_card_metadata_matches_loader_schema() -> None:
    from datasets import DatasetInfo

    metadata = load_dataset_card_metadata()
    features = metadata["dataset_info"]["features"]
    feature_names = {
        feature["name"]
        for feature in features
    }
    assert metadata["license"] == "cc-by-nc-sa-4.0"
    assert metadata["dataset_info"]["splits"][0]["num_examples"] == 201
    assert feature_names == set(FEATURE_FIELD_NAMES)

    parsed_info = DatasetInfo._from_yaml_dict(metadata["dataset_info"])
    assert parsed_info.features == make_features()

    nested = {feature["name"]: feature for feature in features}
    context_names = {"role", "setting", "description", "durc_category"}
    for field in ("legitimate_contexts", "danger_shift_contexts"):
        assert {item["name"] for item in nested[field]["list"]} == context_names
    assert {item["name"] for item in nested["citations"]["list"]} == {
        "source_type",
        "identifier",
        "url",
    }


if __name__ == "__main__":
    test_load()
    test_full_dataset_release_invariants()
    test_dataset_card_metadata_matches_loader_schema()
