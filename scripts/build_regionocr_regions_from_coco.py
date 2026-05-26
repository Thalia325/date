#!/usr/bin/env python3
"""Convert COCO-style detection annotations to RegionOCR JSONL records.

Input datasets such as M6Doc, DECIMER-Segmentation, or PatCID benchmark can be
normalized with this script after their source labels are mapped in
config/regionocr_dataset_rules.json.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8-sig") as f:
        return json.load(f)


def normalize_label(label: str) -> str:
    return " ".join(label.replace("_", " ").replace("-", " ").lower().split())


def build_mapping(raw_mapping: dict[str, str]) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for source_label, target_label in raw_mapping.items():
        mapping[source_label] = target_label
        mapping[normalize_label(source_label)] = target_label
    return mapping


def resolve_image_ref(image: dict[str, Any], image_root: Path | None) -> str:
    file_name = image.get("file_name") or image.get("path") or image.get("image_ref")
    if not isinstance(file_name, str):
        file_name = str(image.get("id"))
    if image_root is None:
        return file_name
    return str((image_root / file_name).resolve())


def coerce_bbox(value: Any) -> list[float] | None:
    if not isinstance(value, list) or len(value) != 4:
        return None
    try:
        return [float(item) for item in value]
    except (TypeError, ValueError):
        return None


def region_score(annotation: dict[str, Any], default_score: float) -> float:
    score = annotation.get("score", default_score)
    try:
        return float(score)
    except (TypeError, ValueError):
        return default_score


def text_reference(annotation: dict[str, Any]) -> str | None:
    for key in ("text_ref", "text", "transcription", "ocr_text"):
        value = annotation.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-json", type=Path, required=True)
    parser.add_argument("--dataset-name", required=True)
    parser.add_argument("--config", type=Path, default=Path("config/regionocr_dataset_rules.json"))
    parser.add_argument("--output-jsonl", type=Path, required=True)
    parser.add_argument("--image-root", type=Path)
    parser.add_argument("--default-score", type=float, default=1.0)
    parser.add_argument(
        "--keep-empty-images",
        action="store_true",
        help="Write image records even when all annotations were filtered out.",
    )
    args = parser.parse_args()

    config = load_json(args.config)
    dataset_rules = config["datasets"][args.dataset_name]
    label_mapping = build_mapping(dataset_rules.get("label_mapping", {}))
    coco = load_json(args.input_json)

    category_id_to_type: dict[int, str] = {}
    unmapped_categories: set[str] = set()
    for category in coco.get("categories", []):
        if not isinstance(category, dict):
            continue
        category_id = category.get("id")
        name = category.get("name")
        if not isinstance(category_id, int) or not isinstance(name, str):
            continue
        target_type = label_mapping.get(name) or label_mapping.get(normalize_label(name))
        if target_type is None:
            unmapped_categories.add(name)
            continue
        category_id_to_type[category_id] = target_type

    images_by_id = {
        image.get("id"): image
        for image in coco.get("images", [])
        if isinstance(image, dict) and image.get("id") is not None
    }
    regions_by_image_id: dict[Any, list[dict[str, Any]]] = defaultdict(list)
    dropped_annotations = 0

    for annotation in coco.get("annotations", []):
        if not isinstance(annotation, dict):
            continue
        image_id = annotation.get("image_id")
        target_type = category_id_to_type.get(annotation.get("category_id"))
        bbox = coerce_bbox(annotation.get("bbox"))
        if image_id not in images_by_id or target_type is None or bbox is None:
            dropped_annotations += 1
            continue

        image = images_by_id[image_id]
        image_ref = resolve_image_ref(image, args.image_root)
        region = {
            "bbox": bbox,
            "type": target_type,
            "score": region_score(annotation, args.default_score),
            "text_ref": text_reference(annotation),
            "image_ref": image_ref,
        }
        if annotation.get("id") is not None:
            region["source_annotation_id"] = annotation["id"]
        regions_by_image_id[image_id].append(region)

    args.output_jsonl.parent.mkdir(parents=True, exist_ok=True)
    written_images = 0
    written_regions = 0
    with args.output_jsonl.open("w", encoding="utf-8") as f:
        for image_id, image in images_by_id.items():
            regions = regions_by_image_id.get(image_id, [])
            if not regions and not args.keep_empty_images:
                continue
            record = {
                "source_dataset": args.dataset_name,
                "source_image_id": image_id,
                "image_ref": resolve_image_ref(image, args.image_root),
                "width": image.get("width"),
                "height": image.get("height"),
                "regions": regions,
            }
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
            written_images += 1
            written_regions += len(regions)

    print(f"Wrote RegionOCR JSONL: {args.output_jsonl.resolve()}")
    print(f"Images written: {written_images}")
    print(f"Regions written: {written_regions}")
    print(f"Annotations dropped: {dropped_annotations}")
    if unmapped_categories:
        print("Unmapped categories: " + ", ".join(sorted(unmapped_categories)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
