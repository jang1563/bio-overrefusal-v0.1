"""Smoke test — load the 5-row fixture with an explicit HuggingFace Features schema.

Invocation:
    python -m tests.test_loader                # from project root
    pytest tests/test_loader.py                 # if pytest is preferred

Purpose:
    (1) Freeze the Features declaration that every `data/queries.jsonl` must load against.
    (2) Catch schema drift before it reaches the evaluation pipeline.
    (3) Validate enum membership against schema/vocab.yaml.

Per Research/02 §1.1, explicit features= bypasses HF's type inference, which drifts on
nullable fields and heterogeneous list-of-dict structures in streaming mode.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

FIXTURE_PATH = Path(__file__).parent / "fixture_5rows.jsonl"
VOCAB_PATH = Path(__file__).parent.parent / "schema" / "vocab.yaml"
EXPECTED_SCHEMA_VERSION = "0.1.0"


def make_features():
    """Canonical Features declaration for queries.jsonl schema v0.1.0.

    Uses the list-of-dict idiom [{...}] for list-of-structs, not Sequence(dict)
    which HF interprets as parallel arrays (dict-of-lists).
    """
    from datasets import Features, Value

    context = {
        "role": Value("string"),
        "setting": Value("string"),
        "description": Value("string"),
        "durc_category": Value("string"),
    }
    citation = {
        "source_type": Value("string"),
        "identifier": Value("string"),
        "url": Value("string"),
    }
    return Features({
        "query_id": Value("string"),
        "query": Value("string"),
        "tier": Value("int32"),
        "subdomain_primary": Value("string"),
        "subdomain_secondary": [Value("string")],
        "legitimacy": Value("string"),
        "biological_reasoning": Value("string"),
        "legitimate_contexts": [context],
        "danger_shift_contexts": [context],
        "style_tags": [Value("string")],
        "citations": [citation],
        "annotator_1_tier": Value("int32"),
        "annotator_1_legitimacy": Value("string"),
        "annotator_2_tier": Value("int32"),
        "annotator_2_legitimacy": Value("string"),
        "adjudicated_tier": Value("int32"),
        "adjudicated_legitimacy": Value("string"),
        "reviewer_comments": Value("string"),
        "schema_version": Value("string"),
    })


def load_vocab() -> dict:
    import yaml

    return yaml.safe_load(VOCAB_PATH.read_text())


def load_rows() -> list[dict]:
    rows = []
    for line in FIXTURE_PATH.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


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
    for r in rows:
        qid = r["query_id"]
        for f in REQUIRED_FIELDS:
            assert r.get(f) is not None, f"{qid}: required field {f!r} is null or missing"
        assert r["schema_version"] == EXPECTED_SCHEMA_VERSION, f"{qid}: schema drift"
        assert 1 <= r["tier"] <= 5, f"{qid}: tier {r['tier']} out of range"
        assert 1 <= r["annotator_1_tier"] <= 5, f"{qid}: annotator_1_tier out of range"
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

    test_load_via_load_dataset(features)


def test_load_via_load_dataset(features) -> None:
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


if __name__ == "__main__":
    test_load()
