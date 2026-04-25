#!/usr/bin/env python3
"""Prepare a reproducible Hugging Face dataset-repository bundle.

This script performs local file assembly only. It never uploads data or reads
API tokens. Use the printed `huggingface-cli upload` command after reviewing the
output directory.
"""

from __future__ import annotations

import argparse
import hashlib
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT_DIR = PROJECT_ROOT / "build" / "huggingface_dataset"


@dataclass(frozen=True)
class ReleaseFile:
    source: Path
    destination: Path
    required: bool = True


HF_RELEASE_FILES = (
    ReleaseFile(Path("dataset_card.md"), Path("README.md")),
    ReleaseFile(Path("data/queries.jsonl"), Path("data/queries.jsonl")),
    ReleaseFile(Path("schema/jsonl_schema.md"), Path("schema/jsonl_schema.md")),
    ReleaseFile(Path("schema/features.py"), Path("schema/features.py")),
    ReleaseFile(Path("schema/vocab.yaml"), Path("schema/vocab.yaml")),
    ReleaseFile(Path("tier_definitions.md"), Path("tier_definitions.md")),
    ReleaseFile(Path("LICENSE"), Path("LICENSE")),
    ReleaseFile(Path("CITATION.cff"), Path("CITATION.cff")),
    ReleaseFile(
        Path("results/fpr_report.md"),
        Path("results/fpr_report.md"),
        required=False,
    ),
    ReleaseFile(
        Path("results/stats_report.md"),
        Path("results/stats_report.md"),
        required=False,
    ),
    ReleaseFile(
        Path("results/stats_table.json"),
        Path("results/stats_table.json"),
        required=False,
    ),
    ReleaseFile(
        Path("results/fpr_table.csv"),
        Path("results/fpr_table.csv"),
        required=False,
    ),
    ReleaseFile(
        Path("results/qualitative_report.md"),
        Path("results/qualitative_report.md"),
        required=False,
    ),
    ReleaseFile(
        Path("results/iaa_report.md"),
        Path("results/iaa_report.md"),
        required=False,
    ),
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def copy_release_file(spec: ReleaseFile, out_dir: Path) -> Path | None:
    source = PROJECT_ROOT / spec.source
    if not source.exists():
        if spec.required:
            raise FileNotFoundError(f"Required release file is missing: {source}")
        return None

    destination = out_dir / spec.destination
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    return destination


def write_manifest(out_dir: Path, copied_files: list[Path]) -> None:
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    lines = [
        "# Hugging Face Release Manifest",
        "",
        f"Generated from `{PROJECT_ROOT.name}` at `{timestamp}`.",
        "",
        "| Path | Size | SHA-256 |",
        "|---|---:|---|",
    ]

    for path in sorted(copied_files, key=lambda p: p.relative_to(out_dir).as_posix()):
        rel = path.relative_to(out_dir).as_posix()
        lines.append(f"| `{rel}` | {path.stat().st_size} | `{sha256_file(path)}` |")

    lines.extend([
        "",
        "Raw provider outputs are intentionally excluded from this bundle.",
        "Review the README card and dataset viewer before making the HF repo public.",
        "",
    ])
    (out_dir / "MANIFEST.md").write_text("\n".join(lines), encoding="utf-8")


def build_hf_release(out_dir: Path = DEFAULT_OUT_DIR, force: bool = False) -> list[Path]:
    if out_dir.exists():
        if not force:
            raise FileExistsError(f"{out_dir} already exists; pass --force to replace it")
        shutil.rmtree(out_dir)

    out_dir.mkdir(parents=True)
    copied = []
    for spec in HF_RELEASE_FILES:
        destination = copy_release_file(spec, out_dir)
        if destination is not None:
            copied.append(destination)

    write_manifest(out_dir, copied)
    copied.append(out_dir / "MANIFEST.md")
    return copied


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=DEFAULT_OUT_DIR,
        help=f"Output directory (default: {DEFAULT_OUT_DIR})",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Replace an existing output directory.",
    )
    parser.add_argument(
        "--repo-id",
        help=(
            "Optional HF repo id used only to print the upload command, "
            "e.g. username/bio-overrefusal."
        ),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    copied = build_hf_release(args.out_dir, force=args.force)
    print(f"Prepared {len(copied)} files in {args.out_dir}")
    if args.repo_id:
        print()
        print("After reviewing the bundle, publish with:")
        print(f"huggingface-cli upload {args.repo_id} {args.out_dir} . --repo-type dataset")


if __name__ == "__main__":
    main()
