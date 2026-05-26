#!/usr/bin/env python3
"""Filter and remap COCO-style annotations to RegionOCR target labels.

This is intended for M6Doc, DECIMER-Segmentation, PatCID benchmark, or any
dataset that can be represented as COCO JSON. Source JSON is read-only.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8-sig") as f:
        return json.load(f)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def normalize_label(label: str) -> str:
    return " ".join(label.replace("_", " ").replace("-", " ").lower().split())


def build_mapping(raw_mapping: dict[str, str]) -> dict[str, str]:
    mapping = {}
    for source_label, target_label in raw_mapping.items():
        mapping[source_label] = target_label
        mapping[normalize_label(source_label)] = target_label
    return mapping


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-json", type=Path, required=True)
    parser.add_argument("--dataset-name", required=True)
    parser.add_argument("--config", type=Path, default=Path("config/regionocr_dataset_rules.json"))
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument(
        "--keep-unmapped",
        action="store_true",
        help="Keep annotations with unmapped labels using their original category names.",
    )
    args = parser.parse_args()

    config = load_json(args.config)
    dataset_rules = config["datasets"][args.dataset_name]
    label_mapping = build_mapping(dataset_rules.get("label_mapping", {}))
    coco = load_json(args.input_json)

    source_categories = coco.get("categories", [])
    if not isinstance(source_categories, list):
        raise ValueError("Input JSON does not contain a COCO-style categories list.")

    old_cat_id_to_target: dict[int, str] = {}
    unmapped: list[str] = []
    for category in source_categories:
        if not isinstance(category, dict):
            continue
        cat_id = category.get("id")
        name = category.get("name")
        if not isinstance(cat_id, int) or not isinstance(name, str):
            continue
        target = label_mapping.get(name) or label_mapping.get(normalize_label(name))
        if target is None and args.keep_unmapped:
            target = name
        if target is None:
            unmapped.append(name)
            continue
        old_cat_id_to_target[cat_id] = target

    target_labels = sorted(set(old_cat_id_to_target.values()))
    target_categories = [
        {"id": idx + 1, "name": label}
        for idx, label in enumerate(target_labels)
    ]
    target_to_new_cat_id = {item["name"]: item["id"] for item in target_categories}

    annotations = []
    used_image_ids = set()
    dropped_annotations = 0
    for annotation in coco.get("annotations", []):
        if not isinstance(annotation, dict):
            continue
        old_cat_id = annotation.get("category_id")
        target_label = old_cat_id_to_target.get(old_cat_id)
        if target_label is None:
            dropped_annotations += 1
            continue
        new_annotation = dict(annotation)
        new_annotation["category_id"] = target_to_new_cat_id[target_label]
        annotations.append(new_annotation)
        if "image_id" in new_annotation:
            used_image_ids.add(new_annotation["image_id"])

    images = [
        image
        for image in coco.get("images", [])
        if isinstance(image, dict) and image.get("id") in used_image_ids
    ]

    output = {
        "info": {
            "source_dataset": args.dataset_name,
            "source_annotation": str(args.input_json),
            "unmapped_source_categories": sorted(set(unmapped)),
            "dropped_annotations": dropped_annotations,
        },
        "licenses": coco.get("licenses", []),
        "images": images,
        "annotations": annotations,
        "categories": target_categories,
    }
    write_json(args.output_json, output)
    print(f"Wrote RegionOCR COCO JSON: {args.output_json.resolve()}")
    print(f"Images kept: {len(images)}")
    print(f"Annotations kept: {len(annotations)}")
    print(f"Annotations dropped: {dropped_annotations}")
    if unmapped:
        print("Unmapped categories: " + ", ".join(sorted(set(unmapped))))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
