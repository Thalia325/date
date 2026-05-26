#!/usr/bin/env python3
"""Build a PEaCE chemical-expression manifest for Task 2.

The manifest keeps likely chemical-equation/expression records and preserves the
original LaTeX label for later LaTeX -> mhchem -> JSON normalization.

It supports both PEaCE layouts:
- full release: final_renders/, labels.jsonl, train.txt/dev.txt/test.txt
- GitHub real-world set: real_world_test_set/labels.json and image folders
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path
from typing import Any


IMAGE_EXTS = [".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp"]
FILENAME_KEYS = ("filename", "file", "image", "image_path", "name", "id", "record_id")
LABEL_KEYS = ("label", "latex", "ground_truth", "gt", "text", "target", "formula")


CHEM_PATTERNS = [
    re.compile(r"\\(?:rightarrow|leftarrow|rightleftharpoons|leftrightarrow|ce)\b"),
    re.compile(r"(?:->|<-|<=>|=>|=)"),
    re.compile(r"\b[A-Z][a-z]?\s*(?:_\{?\d+\}?|\d)\b"),
    re.compile(r"\b(?:aq|s|l|g)\b"),
    re.compile(r"\^[{]?[+\-0-9]+[}]?"),
    re.compile(r"\+"),
]


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(item, dict):
                rows.append(item)
    return rows


def load_real_world_labels(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8", errors="replace") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        return {}
    return {str(key): str(value) for key, value in data.items() if str(value).strip()}


def first_string(item: dict[str, Any], keys: tuple[str, ...]) -> str:
    for key in keys:
        value = item.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def make_label_lookup(labels: list[dict[str, Any]]) -> dict[str, str]:
    lookup: dict[str, str] = {}
    for idx, item in enumerate(labels):
        label = first_string(item, LABEL_KEYS)
        if not label:
            continue
        filename = first_string(item, FILENAME_KEYS)
        keys = {str(idx), str(idx + 1)}
        if filename:
            path = Path(filename)
            keys.update({filename, path.name, path.stem})
        for key in keys:
            lookup[key] = label
    return lookup


def resolve_image(root: Path, filename: str) -> Path | None:
    direct = root / "final_renders" / filename
    if direct.exists():
        return direct
    path = Path(filename)
    candidates = [
        root / "final_renders" / path.name,
        root / "final_renders" / path.stem,
    ]
    for ext in IMAGE_EXTS:
        candidates.append(root / "final_renders" / f"{path.stem}{ext}")
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def is_likely_chemical_expression(label: str) -> bool:
    compact = re.sub(r"(?<=\w)\s+(?=\w)", "", label)
    hits = sum(1 for pattern in CHEM_PATTERNS if pattern.search(label) or pattern.search(compact))
    has_element_pair = bool(
        re.search(r"\b[A-Z][a-z]?\b.*\b[A-Z][a-z]?\b", label)
        or re.search(r"\b[A-Z][a-z]?\b.*\b[A-Z][a-z]?\b", compact)
    )
    return hits >= 2 or (hits >= 1 and has_element_pair)


def read_split(root: Path, split: str) -> list[str]:
    path = root / f"{split}.txt"
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", errors="replace") as f:
        return [line.strip() for line in f if line.strip()]


def build_full_release_rows(root: Path, include_all: bool) -> tuple[list[dict[str, str]], int, int]:
    labels = load_jsonl(root / "labels.jsonl")
    lookup = make_label_lookup(labels)
    rows: list[dict[str, str]] = []
    missing_label = 0
    missing_image = 0

    for split in ("train", "dev", "test"):
        for filename in read_split(root, split):
            key_candidates = [filename, Path(filename).name, Path(filename).stem]
            label = next((lookup[key] for key in key_candidates if key in lookup), "")
            if not label:
                missing_label += 1
                continue
            image_path = resolve_image(root, filename)
            if image_path is None:
                missing_image += 1
                continue
            if not include_all and not is_likely_chemical_expression(label):
                continue
            rows.append(
                {
                    "image_path": str(image_path.resolve()),
                    "source_dataset": "PEaCE",
                    "split": split,
                    "latex": label,
                    "normalization_target": "mhchem_or_reaction_json",
                }
            )
    return rows, missing_label, missing_image


def build_real_world_rows(root: Path, include_all: bool) -> tuple[list[dict[str, str]], int, int]:
    real_root = root / "real_world_test_set"
    labels = load_real_world_labels(real_root / "labels.json")
    rows: list[dict[str, str]] = []
    missing_image = 0

    for image_name, label in labels.items():
        image_path = real_root / image_name
        if not image_path.exists():
            missing_image += 1
            continue
        if not include_all and not is_likely_chemical_expression(label):
            continue
        rows.append(
            {
                "image_path": str(image_path.resolve()),
                "source_dataset": "PEaCE_real_world_test_set",
                "split": "real_world_test",
                "latex": label,
                "normalization_target": "mhchem_or_reaction_json",
            }
        )
    return rows, 0, missing_image


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("data/raw/PEaCE"))
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/processed/peace_expression_manifest.csv"),
    )
    parser.add_argument(
        "--include-all",
        action="store_true",
        help="Keep all PEaCE records instead of filtering likely chemical expressions.",
    )
    args = parser.parse_args()

    rows: list[dict[str, str]] = []
    missing_label = 0
    missing_image = 0

    if (args.root / "labels.jsonl").exists():
        full_rows, full_missing_label, full_missing_image = build_full_release_rows(
            args.root, args.include_all
        )
        rows.extend(full_rows)
        missing_label += full_missing_label
        missing_image += full_missing_image

    if (args.root / "real_world_test_set" / "labels.json").exists():
        real_rows, real_missing_label, real_missing_image = build_real_world_rows(
            args.root, args.include_all
        )
        rows.extend(real_rows)
        missing_label += real_missing_label
        missing_image += real_missing_image

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "image_path",
                "source_dataset",
                "split",
                "latex",
                "normalization_target",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)

    split_counts: dict[str, int] = {}
    for row in rows:
        split_counts[row["split"]] = split_counts.get(row["split"], 0) + 1

    print(f"Wrote PEaCE manifest: {args.output.resolve()}")
    print(f"Rows: {len(rows)}")
    print(f"Splits: {split_counts}")
    print(f"Missing labels: {missing_label}")
    print(f"Missing images: {missing_image}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
