#!/usr/bin/env python3
"""Build a RegionOCR crop-classification manifest from Chemical Images data.

The script reads class folders such as one_molecule/several_molecules/reactions/
other and writes a CSV manifest. It does not alter source images.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
import zipfile
from pathlib import Path
from typing import Any


IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp", ".webp"}


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def stable_split(path: Path, seed: int, train: float, val: float) -> str:
    digest = hashlib.sha1(f"{seed}:{path.as_posix()}".encode("utf-8")).hexdigest()
    bucket = int(digest[:8], 16) / 0xFFFFFFFF
    if bucket < train:
        return "train"
    if bucket < train + val:
        return "val"
    return "test"


def find_class_dir(root: Path, class_name: str) -> Path | None:
    candidates = [
        root / class_name,
        root / "classified" / class_name,
        root / "for_model" / class_name,
    ]
    for candidate in candidates:
        if candidate.exists() and candidate.is_dir():
            return candidate
    return None


def collect_images(class_dir: Path) -> list[Path]:
    return sorted(
        path
        for path in class_dir.rglob("*")
        if path.is_file() and path.suffix.lower() in IMAGE_EXTS
    )


def collect_zip_images(root: Path, class_names: list[str], aliases: dict[str, list[str]]) -> list[tuple[Path, str, str]]:
    rows: list[tuple[Path, str, str]] = []
    alias_lookup = {
        alias: class_name
        for class_name in class_names
        for alias in aliases.get(class_name, [class_name])
    }
    for archive in sorted(root.rglob("*.zip")):
        try:
            with zipfile.ZipFile(archive) as zf:
                for member in sorted(zf.namelist()):
                    if member.endswith("/") or member.startswith("__MACOSX/"):
                        continue
                    if Path(member).suffix.lower() not in IMAGE_EXTS:
                        continue
                    parts = [part for part in member.split("/") if part]
                    for index, part in enumerate(parts):
                        if part != "classified" or index + 1 >= len(parts):
                            continue
                        source_label = alias_lookup.get(parts[index + 1])
                        if source_label:
                            rows.append((archive.resolve(), member, source_label))
                        break
        except zipfile.BadZipFile:
            continue
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("data/raw/ChemicalImagesClassifier"))
    parser.add_argument("--config", type=Path, default=Path("config/regionocr_dataset_rules.json"))
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/processed/chemical_classifier_manifest.csv"),
    )
    parser.add_argument("--seed", type=int, default=20260525)
    parser.add_argument("--train", type=float, default=0.8)
    parser.add_argument("--val", type=float, default=0.1)
    args = parser.parse_args()

    if args.train <= 0 or args.val < 0 or args.train + args.val >= 1:
        raise ValueError("Expected 0 < train and 0 <= val and train + val < 1.")

    config = load_json(args.config)
    dataset_rules = config["datasets"]["Chemical Images Classifier Dataset"]
    label_mapping = dataset_rules["label_mapping"]
    required_class_dirs = dataset_rules["required_class_dirs"]
    class_aliases = dataset_rules.get("class_aliases", {})

    rows: list[dict[str, str]] = []
    missing: list[str] = []
    found: set[str] = set()
    for source_label in required_class_dirs:
        class_dir = find_class_dir(args.root, source_label)
        if class_dir is None:
            missing.append(source_label)
            continue
        found.add(source_label)
        target_label = label_mapping[source_label]
        for image_path in collect_images(class_dir):
            rows.append(
                {
                    "image_path": str(image_path.resolve()),
                    "source_dataset": "Chemical Images Classifier Dataset",
                    "source_label": source_label,
                    "target_label": target_label,
                    "split": stable_split(image_path.resolve(), args.seed, args.train, args.val),
                }
            )

    for archive_path, member_path, source_label in collect_zip_images(
        args.root,
        required_class_dirs,
        class_aliases,
    ):
        found.add(source_label)
        target_label = label_mapping[source_label]
        image_ref = f"{archive_path}!{member_path}"
        rows.append(
            {
                "image_path": image_ref,
                "source_dataset": "Chemical Images Classifier Dataset",
                "source_label": source_label,
                "target_label": target_label,
                "split": stable_split(Path(member_path), args.seed, args.train, args.val),
            }
        )

    missing = [source_label for source_label in required_class_dirs if source_label not in found]

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "image_path",
                "source_dataset",
                "source_label",
                "target_label",
                "split",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)

    split_counts = {}
    for row in rows:
        split_counts[row["split"]] = split_counts.get(row["split"], 0) + 1
    print(f"Wrote manifest: {args.output.resolve()}")
    print(f"Rows: {len(rows)}")
    print(f"Splits: {split_counts}")
    if missing:
        print("Missing class folders: " + ", ".join(missing))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
