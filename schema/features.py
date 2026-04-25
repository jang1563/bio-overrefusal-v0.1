"""Canonical Hugging Face Features declaration for schema v0.1.0."""

from __future__ import annotations


def make_features():
    """Return the explicit Features schema for `data/queries.jsonl`.

    The list-of-dict idiom (`[{...}]`) is intentional for list-of-struct fields.
    Hugging Face `Sequence(dict)` represents dict-of-lists and does not match
    this JSONL layout.
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
