#!/usr/bin/env python3
"""Build first-pass Task 4 manifests for chemistry education parsing.

Outputs are intentionally schema-first and conservative. When raw datasets are
missing, the script still creates empty output files with the right headers so
the downstream workflow is stable.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from pathlib import Path
from typing import Any, Iterable


IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp", ".webp"}
DOCUMENT_EXTS = {".pdf", ".docx", ".doc", ".pptx", ".ppt"}
ANNOTATION_EXTS = {".json", ".jsonl"}
MAX_JSON_FILES = 5000

CHEMISTRY_KEYWORDS = [
    "chemistry",
    "chemical",
    "molecule",
    "atom",
    "element",
    "compound",
    "ion",
    "acid",
    "base",
    "salt",
    "oxidation",
    "reduction",
    "solution",
    "reaction",
    "precipitate",
    "gas",
    "化学",
    "化工",
    "元素",
    "分子",
    "原子",
    "化合物",
    "离子",
    "酸",
    "碱",
    "盐",
    "氧化",
    "还原",
    "溶液",
    "反应",
    "沉淀",
    "气体",
    "实验",
    "试剂",
    "仪器",
    "装置",
]

FORMULA_RE = re.compile(
    r"\b(?:H2O|CO2|O2|H2|NaCl|HCl|NaOH|CaCO3|KMnO4|H2SO4)\b|"
    r"\b[A-Z][a-z]?\d*(?:[A-Z][a-z]?\d*)+\b|"
    r"(?:->|<=>|\\rightarrow|\\ce\{)"
)

SCIENCEQA_CHOICE_KEYS = ("choices", "choice", "options", "answer_choices")
QUESTION_KEYS = ("question", "question_stem", "stem", "prompt")
EXPLANATION_KEYS = ("solution", "explanation", "rationale", "lecture")
CONTEXT_KEYS = ("hint", "lecture", "context", "text", "paragraph", "passage")
IMAGE_KEYS = ("image", "image_path", "img", "figure", "diagram")


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8", errors="replace") as f:
        return json.load(f)


def load_jsonl(path: Path) -> list[Any]:
    rows: list[Any] = []
    with path.open("r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows


def iter_json_records(root: Path) -> Iterable[tuple[str, dict[str, Any]]]:
    if not root.exists():
        return
    seen = 0
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in ANNOTATION_EXTS:
            continue
        seen += 1
        if seen > MAX_JSON_FILES:
            break
        try:
            payload = load_json(path) if path.suffix.lower() == ".json" else load_jsonl(path)
        except (OSError, json.JSONDecodeError):
            continue
        yield from flatten_records(payload, path.stem)


def flatten_records(payload: Any, source_id: str) -> Iterable[tuple[str, dict[str, Any]]]:
    if isinstance(payload, dict):
        if looks_like_record(payload):
            yield source_id, payload
            return
        for key, value in payload.items():
            if isinstance(value, dict):
                if looks_like_record(value):
                    yield str(key), value
                else:
                    yield from flatten_records(value, str(key))
            elif isinstance(value, list):
                for idx, item in enumerate(value):
                    if isinstance(item, dict):
                        yield from flatten_records(item, f"{key}_{idx}")
    elif isinstance(payload, list):
        for idx, item in enumerate(payload):
            if isinstance(item, dict):
                yield from flatten_records(item, f"{source_id}_{idx}")


def looks_like_record(item: dict[str, Any]) -> bool:
    keys = set(item)
    return bool(keys.intersection(QUESTION_KEYS)) or {"images", "annotations"}.issubset(keys)


def text_from(item: dict[str, Any], keys: Iterable[str]) -> str:
    parts: list[str] = []
    for key in keys:
        value = item.get(key)
        if isinstance(value, str) and value.strip():
            parts.append(value.strip())
        elif isinstance(value, list):
            parts.extend(str(v).strip() for v in value if str(v).strip())
    return "\n".join(parts)


def first_value(item: dict[str, Any], keys: Iterable[str]) -> Any:
    for key in keys:
        value = item.get(key)
        if value not in (None, "", []):
            return value
    return None


def is_chemistry_record(item: dict[str, Any]) -> bool:
    metadata_text = " ".join(
        str(item.get(key, ""))
        for key in (
            "subject",
            "topic",
            "category",
            "skill",
            "task",
            "grade",
            "lessonName",
            "lesson",
            "chapter",
        )
    )
    full_text = " ".join(
        [
            metadata_text,
            text_from(item, QUESTION_KEYS),
            text_from(item, CONTEXT_KEYS),
            text_from(item, EXPLANATION_KEYS),
        ]
    ).lower()
    return any(keyword.lower() in full_text for keyword in CHEMISTRY_KEYWORDS) or bool(FORMULA_RE.search(full_text))


def stable_split(identifier: str, seed: int, train: float, val: float) -> str:
    digest = hashlib.sha1(f"{seed}:{identifier}".encode("utf-8")).hexdigest()
    bucket = int(digest[:8], 16) / 0xFFFFFFFF
    if bucket < train:
        return "train"
    if bucket < train + val:
        return "val"
    return "test"


def resolve_split(record_id: str, split_map: dict[str, str], seed: int) -> str:
    if record_id in split_map:
        return split_map[record_id]
    return stable_split(record_id, seed, 0.8, 0.1)


def load_scienceqa_splits(root: Path) -> dict[str, str]:
    split_file = root / "pid_splits.json"
    if not split_file.exists():
        return {}
    try:
        payload = load_json(split_file)
    except json.JSONDecodeError:
        return {}
    split_map: dict[str, str] = {}
    if isinstance(payload, dict):
        for split, ids in payload.items():
            if isinstance(ids, list):
                for record_id in ids:
                    split_map[str(record_id)] = "val" if split == "dev" else str(split)
    return split_map


def normalize_choices(value: Any) -> list[dict[str, str]]:
    if not isinstance(value, list):
        return []
    labels = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    choices: list[dict[str, str]] = []
    for idx, choice in enumerate(value):
        if isinstance(choice, dict):
            label = str(choice.get("label") or choice.get("key") or labels[idx])
            text = str(choice.get("text") or choice.get("value") or choice.get("choice") or "").strip()
        else:
            label = labels[idx] if idx < len(labels) else str(idx + 1)
            text = str(choice).strip()
        if text:
            choices.append({"label": label, "text": text})
    return choices


def normalize_answer(answer: Any, choices: list[dict[str, str]]) -> dict[str, str]:
    if isinstance(answer, int) and 0 <= answer < len(choices):
        return choices[answer]
    answer_text = str(answer).strip() if answer is not None else ""
    if answer_text.isdigit():
        idx = int(answer_text)
        if 0 <= idx < len(choices):
            return choices[idx]
    for choice in choices:
        if answer_text and answer_text in {choice["label"], choice["text"]}:
            return choice
    return {"label": answer_text, "text": ""}


def image_paths(root: Path, item: dict[str, Any]) -> list[str]:
    raw = first_value(item, IMAGE_KEYS)
    if raw is None:
        return []
    values = raw if isinstance(raw, list) else [raw]
    paths: list[str] = []
    for value in values:
        path_text = str(value).strip()
        if not path_text:
            continue
        path = Path(path_text)
        candidate = path if path.is_absolute() else root / path
        paths.append(str(candidate.resolve()))
    return paths


def question_payload(
    *,
    source_dataset: str,
    record_id: str,
    record: dict[str, Any],
    root: Path,
    split: str,
) -> dict[str, Any] | None:
    question = text_from(record, QUESTION_KEYS)
    choices = normalize_choices(first_value(record, SCIENCEQA_CHOICE_KEYS))
    if not question or not choices:
        return None
    answer = normalize_answer(record.get("answer", record.get("correct_answer")), choices)
    context_text = text_from(record, CONTEXT_KEYS)
    explanation = text_from(record, EXPLANATION_KEYS)
    topic_tags = [
        str(record.get(key))
        for key in ("subject", "topic", "category", "skill")
        if record.get(key)
    ]
    return {
        "question_id": record_id,
        "source_dataset": source_dataset,
        "language": "zh" if re.search(r"[\u4e00-\u9fff]", question) else "en",
        "subject": "chemistry",
        "topic_tags": topic_tags,
        "question_stem": question,
        "choices": choices,
        "answer": answer,
        "explanation": explanation,
        "context": {
            "text": context_text,
            "image_paths": image_paths(root, record),
        },
        "page_regions": [],
        "split": split,
    }


def build_scienceqa(root: Path, seed: int) -> list[dict[str, Any]]:
    split_map = load_scienceqa_splits(root)
    rows: list[dict[str, Any]] = []
    for record_id, record in iter_json_records(root):
        if not is_chemistry_record(record):
            continue
        payload = question_payload(
            source_dataset="ScienceQA",
            record_id=record_id,
            record=record,
            root=root,
            split=resolve_split(record_id, split_map, seed),
        )
        if payload:
            rows.append(payload)
    return dedupe_questions(rows)


def build_tqa(root: Path, seed: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for record_id, record in iter_json_records(root):
        if not is_chemistry_record(record):
            continue
        payload = question_payload(
            source_dataset="TQA",
            record_id=record_id,
            record=record,
            root=root,
            split=stable_split(record_id, seed, 0.8, 0.1),
        )
        if payload:
            rows.append(payload)
    return dedupe_questions(rows)


def dedupe_questions(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    deduped: list[dict[str, Any]] = []
    for row in rows:
        key = normalize_text(row["question_stem"] + " " + " ".join(c["text"] for c in row["choices"]))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(row)
    return deduped


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


def bbox_from(annotation: dict[str, Any]) -> list[float]:
    bbox = annotation.get("bbox") or annotation.get("box") or annotation.get("rect")
    if isinstance(bbox, list) and len(bbox) >= 4:
        return [float(v) for v in bbox[:4]]
    polygon = annotation.get("polygon") or annotation.get("segmentation")
    if isinstance(polygon, list) and polygon and isinstance(polygon[0], (int, float)):
        xs = [float(v) for idx, v in enumerate(polygon) if idx % 2 == 0]
        ys = [float(v) for idx, v in enumerate(polygon) if idx % 2 == 1]
        if xs and ys:
            return [min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys)]
    return []


def category_lookup(categories: Any) -> dict[Any, str]:
    lookup: dict[Any, str] = {}
    if isinstance(categories, list):
        for category in categories:
            if isinstance(category, dict):
                cat_id = category.get("id", category.get("category_id"))
                name = category.get("name", category.get("label"))
                if cat_id is not None and name:
                    lookup[cat_id] = str(name)
    elif isinstance(categories, dict):
        lookup.update(categories)
    return lookup


def map_region_label(raw_label: str, config: dict[str, Any]) -> str:
    raw = raw_label.strip().lower()
    mapping = {
        "title": "page_title",
        "section": "section_title",
        "section_title": "section_title",
        "paragraph": "paragraph",
        "text": "paragraph",
        "question": "question_block",
        "answer": "answer_area",
        "figure": "figure",
        "image": "figure",
        "table": "table",
        "formula": "formula",
        "equation": "chemical_equation",
        "caption": "figure_caption",
        "figure_caption": "figure_caption",
        "table_caption": "table_caption",
    }
    target = mapping.get(raw, raw_label)
    if target in config.get("target_region_labels", []):
        return target
    return "paragraph" if raw in {"plain text", "body"} else target


def build_m6doc(root: Path, config: dict[str, Any], seed: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not root.exists():
        return rows
    for path in sorted(root.rglob("*.json")):
        try:
            payload = load_json(path)
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(payload, dict):
            continue
        if "images" in payload and "annotations" in payload:
            rows.extend(parse_coco_layout(payload, root, path, config, seed))
        elif "pages" in payload:
            rows.extend(parse_page_layout(payload.get("pages"), root, path, config, seed))
    return rows


def parse_coco_layout(
    payload: dict[str, Any],
    root: Path,
    annotation_path: Path,
    config: dict[str, Any],
    seed: int,
) -> list[dict[str, Any]]:
    categories = category_lookup(payload.get("categories"))
    images = {
        image.get("id"): image
        for image in payload.get("images", [])
        if isinstance(image, dict) and image.get("id") is not None
    }
    by_image: dict[Any, list[dict[str, Any]]] = {}
    for annotation in payload.get("annotations", []):
        if isinstance(annotation, dict):
            by_image.setdefault(annotation.get("image_id"), []).append(annotation)

    rows: list[dict[str, Any]] = []
    for image_id, annotations in by_image.items():
        image = images.get(image_id, {})
        metadata = " ".join(str(image.get(k, "")) for k in ("subject", "document_type", "type", "doc_type"))
        if metadata and not is_chemistry_layout_metadata(metadata):
            continue
        file_name = str(image.get("file_name") or image.get("path") or "")
        image_path = resolve_existing_path(root, file_name)
        regions = []
        for annotation in annotations:
            raw_label = str(annotation.get("label") or categories.get(annotation.get("category_id"), ""))
            bbox = bbox_from(annotation)
            if raw_label and bbox:
                regions.append(
                    {
                        "region_id": str(annotation.get("id", "")),
                        "label": map_region_label(raw_label, config),
                        "source_label": raw_label,
                        "bbox": bbox,
                        "text": str(annotation.get("text", "")),
                    }
                )
        if regions:
            record_id = str(image_id)
            rows.append(
                {
                    "page_id": record_id,
                    "document_id": str(image.get("document_id") or annotation_path.stem),
                    "source_dataset": "M6Doc",
                    "image_path": image_path,
                    "language": str(image.get("language") or ""),
                    "subject": str(image.get("subject") or "Chemistry"),
                    "document_type": str(image.get("document_type") or image.get("type") or ""),
                    "regions": regions,
                    "split": stable_split(record_id, seed, 0.8, 0.1),
                }
            )
    return rows


def parse_page_layout(
    pages: Any,
    root: Path,
    annotation_path: Path,
    config: dict[str, Any],
    seed: int,
) -> list[dict[str, Any]]:
    if not isinstance(pages, list):
        return []
    rows: list[dict[str, Any]] = []
    for idx, page in enumerate(pages):
        if not isinstance(page, dict):
            continue
        metadata = " ".join(str(page.get(k, "")) for k in ("subject", "document_type", "type", "doc_type"))
        if metadata and not is_chemistry_layout_metadata(metadata):
            continue
        regions = []
        for region in page.get("regions", page.get("annotations", [])):
            if not isinstance(region, dict):
                continue
            raw_label = str(region.get("label") or region.get("category") or region.get("type") or "")
            bbox = bbox_from(region)
            if raw_label and bbox:
                regions.append(
                    {
                        "region_id": str(region.get("id", "")),
                        "label": map_region_label(raw_label, config),
                        "source_label": raw_label,
                        "bbox": bbox,
                        "text": str(region.get("text", "")),
                    }
                )
        if regions:
            page_id = str(page.get("id") or page.get("page_id") or f"{annotation_path.stem}_{idx}")
            rows.append(
                {
                    "page_id": page_id,
                    "document_id": str(page.get("document_id") or annotation_path.stem),
                    "source_dataset": "M6Doc",
                    "image_path": resolve_existing_path(root, str(page.get("image") or page.get("image_path") or "")),
                    "language": str(page.get("language") or ""),
                    "subject": str(page.get("subject") or "Chemistry"),
                    "document_type": str(page.get("document_type") or page.get("type") or ""),
                    "regions": regions,
                    "split": stable_split(page_id, seed, 0.8, 0.1),
                }
            )
    return rows


def is_chemistry_layout_metadata(metadata: str) -> bool:
    lower = metadata.lower()
    has_chemistry = "chemistry" in lower or "化学" in metadata
    if not has_chemistry:
        return False
    if any(doc_type in lower for doc_type in ("textbook", "test paper", "exam", "handout")):
        return True
    if any(doc_type in metadata for doc_type in ("教材", "试卷", "讲义", "实验")):
        return True
    return True


def resolve_existing_path(root: Path, text: str) -> str:
    if not text:
        return ""
    path = Path(text)
    candidate = path if path.is_absolute() else root / path
    return str(candidate.resolve())


def build_self_collected_manifest(root: Path, source_dataset: str, seed: int) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    if not root.exists():
        return rows
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in IMAGE_EXTS | DOCUMENT_EXTS:
            continue
        record_id = hashlib.sha1(str(path.resolve()).encode("utf-8")).hexdigest()[:16]
        rows.append(
            {
                "record_id": record_id,
                "source_dataset": source_dataset,
                "source_path": str(path.resolve()),
                "file_type": "image" if path.suffix.lower() in IMAGE_EXTS else "document",
                "language": "zh",
                "annotation_status": "needs_layout_and_content_annotation",
                "recommended_split": stable_split(record_id, seed, 0.8, 0.1),
                "notes": "",
            }
        )
    return rows


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def write_csv(path: Path, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("config/task4_education_parsing_rules.json"),
    )
    parser.add_argument(
        "--page-layout-output",
        type=Path,
        default=Path("data/processed/task4_page_layout_regions.jsonl"),
    )
    parser.add_argument(
        "--qa-output",
        type=Path,
        default=Path("data/processed/task4_question_choice_answer_explanation.jsonl"),
    )
    parser.add_argument(
        "--self-collected-output",
        type=Path,
        default=Path("data/processed/task4_self_collected_annotation_manifest.csv"),
    )
    parser.add_argument("--seed", type=int, default=20260525)
    args = parser.parse_args()

    repo_root = args.repo_root.resolve()
    config_path = args.config if args.config.is_absolute() else repo_root / args.config
    config = load_json(config_path)
    datasets = config.get("datasets", {})

    m6doc_root = repo_root / datasets.get("M6Doc", {}).get("root", "data/raw/M6Doc")
    scienceqa_root = repo_root / datasets.get("ScienceQA", {}).get("root", "data/raw/ScienceQA")
    tqa_root = repo_root / datasets.get("TQA", {}).get("root", "data/raw/TQA")
    exam_root = repo_root / datasets.get("ChineseChemExam", {}).get("root", "data/raw/ChineseChemExam")
    handout_root = repo_root / datasets.get("ChineseChemLabHandout", {}).get("root", "data/raw/ChineseChemLabHandout")

    page_rows = build_m6doc(m6doc_root, config, args.seed)
    qa_rows = build_scienceqa(scienceqa_root, args.seed) + build_tqa(tqa_root, args.seed)
    self_rows = build_self_collected_manifest(exam_root, "ChineseChemExam", args.seed)
    self_rows.extend(build_self_collected_manifest(handout_root, "ChineseChemLabHandout", args.seed))

    page_output = args.page_layout_output if args.page_layout_output.is_absolute() else repo_root / args.page_layout_output
    qa_output = args.qa_output if args.qa_output.is_absolute() else repo_root / args.qa_output
    self_output = args.self_collected_output if args.self_collected_output.is_absolute() else repo_root / args.self_collected_output

    write_jsonl(page_output, page_rows)
    write_jsonl(qa_output, qa_rows)
    write_csv(
        self_output,
        self_rows,
        [
            "record_id",
            "source_dataset",
            "source_path",
            "file_type",
            "language",
            "annotation_status",
            "recommended_split",
            "notes",
        ],
    )

    print(f"Wrote page layout JSONL: {page_output}")
    print(f"Page layout rows: {len(page_rows)}")
    print(f"Wrote QA JSONL: {qa_output}")
    print(f"QA rows: {len(qa_rows)}")
    print(f"Wrote self-collected annotation manifest: {self_output}")
    print(f"Self-collected rows: {len(self_rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
