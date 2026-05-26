#!/usr/bin/env python3
"""Audit local RegionOCR candidate datasets without modifying source files.

The script checks whether each dataset folder exists, counts likely images and
annotation files, inspects COCO-like category names when available, and writes a
Markdown report with a first-pass usability decision.
"""

from __future__ import annotations

import argparse
import json
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any


IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp", ".webp"}
ANNOTATION_EXTS = {".json", ".xml", ".txt", ".csv"}
MAX_SCAN_FILES = 250_000


@dataclass
class DatasetAudit:
    name: str
    root: Path
    exists: bool
    role: str
    image_count: int = 0
    annotation_count: int = 0
    class_dir_counts: dict[str, int] | None = None
    archive_image_count: int = 0
    archive_annotation_count: int = 0
    archive_class_counts: dict[str, int] | None = None
    archive_names: list[str] | None = None
    coco_categories: list[str] | None = None
    warnings: list[str] | None = None
    decision: str = ""


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def iter_files_limited(root: Path):
    seen = 0
    for path in root.rglob("*"):
        if path.is_file():
            seen += 1
            if seen > MAX_SCAN_FILES:
                break
            yield path


def count_files(root: Path) -> tuple[int, int, bool]:
    image_count = 0
    annotation_count = 0
    truncated = False
    seen = 0
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        seen += 1
        if seen > MAX_SCAN_FILES:
            truncated = True
            break
        suffix = path.suffix.lower()
        if suffix in IMAGE_EXTS:
            image_count += 1
        elif suffix in ANNOTATION_EXTS:
            annotation_count += 1
    return image_count, annotation_count, truncated


def image_count_under(path: Path) -> int:
    if not path.exists() or not path.is_dir():
        return 0
    count = 0
    for child in path.rglob("*"):
        if child.is_file() and child.suffix.lower() in IMAGE_EXTS:
            count += 1
    return count


def iter_zip_members(root: Path):
    for archive in sorted(root.rglob("*.zip")):
        try:
            with zipfile.ZipFile(archive) as zf:
                for name in zf.namelist():
                    if name.endswith("/") or name.startswith("__MACOSX/"):
                        continue
                    yield archive, name
        except zipfile.BadZipFile:
            continue


def count_archive_members(root: Path) -> tuple[int, int, list[str]]:
    image_count = 0
    annotation_count = 0
    archive_names: set[str] = set()
    for archive, member in iter_zip_members(root):
        archive_names.add(archive.name)
        suffix = Path(member).suffix.lower()
        if suffix in IMAGE_EXTS:
            image_count += 1
        elif suffix in ANNOTATION_EXTS:
            annotation_count += 1
    return image_count, annotation_count, sorted(archive_names)


def zip_class_counts(root: Path, class_names: list[str], aliases: dict[str, list[str]]) -> dict[str, int]:
    counts = {class_name: 0 for class_name in class_names}
    alias_lookup = {
        alias: class_name
        for class_name in class_names
        for alias in aliases.get(class_name, [class_name])
    }
    for _archive, member in iter_zip_members(root):
        if Path(member).suffix.lower() not in IMAGE_EXTS:
            continue
        parts = [part for part in member.split("/") if part]
        for index, part in enumerate(parts):
            if part != "classified" or index + 1 >= len(parts):
                continue
            class_key = alias_lookup.get(parts[index + 1])
            if class_key:
                counts[class_key] += 1
            break
    return counts


def find_coco_categories(root: Path) -> list[str]:
    names: list[str] = []
    for path in iter_files_limited(root):
        if path.suffix.lower() != ".json":
            continue
        try:
            payload = load_json(path)
        except Exception:
            continue
        categories = payload.get("categories")
        if not isinstance(categories, list):
            continue
        for item in categories:
            if isinstance(item, dict) and isinstance(item.get("name"), str):
                names.append(item["name"])
        if names:
            break
    return sorted(set(names))


def audit_class_dirs(root: Path, class_names: list[str]) -> dict[str, int]:
    counts = {}
    for class_name in class_names:
        candidates = [
            root / class_name,
            root / "classified" / class_name,
            root / "for_model" / class_name,
        ]
        counts[class_name] = max(image_count_under(candidate) for candidate in candidates)
    return counts


def decide_usability(name: str, audit: DatasetAudit, rules: dict[str, Any]) -> list[str]:
    warnings: list[str] = []
    if not audit.exists:
        warnings.append("本地未发现数据目录，暂时只能做方案级判断。")
        return warnings

    if audit.image_count == 0:
        if audit.archive_image_count == 0:
            warnings.append("未发现常见图片文件，请检查数据是否缺失、仍未解压，或目录层级不符合预期。")
        else:
            warnings.append("图片目前位于压缩包内；如果训练框架不支持 zip 成员路径，需要先解压或实现 zip-aware dataloader。")

    if name == "M6Doc":
        if audit.annotation_count == 0 and audit.archive_annotation_count == 0:
            warnings.append("未发现标注文件；M6Doc 必须有区域标注才适合训练或验证版面检测器。")
        if not audit.coco_categories:
            warnings.append("未读取到 COCO categories；标注落地后需要确认源标签到 RegionOCR 标签的映射。")

    if name == "DECIMER-Segmentation":
        if audit.annotation_count == 0 and audit.archive_annotation_count == 0:
            warnings.append("未发现 mask/json/xml 等标注文件；只能作为待推理图片，不能作为训练数据。")

    if name == "Chemical Images Classifier Dataset":
        required = rules.get("required_class_dirs", [])
        missing = [
            class_name
            for class_name in required
            if (
                (not audit.class_dir_counts or audit.class_dir_counts.get(class_name, 0) == 0)
                and (not audit.archive_class_counts or audit.archive_class_counts.get(class_name, 0) == 0)
            )
        ]
        if missing:
            warnings.append("缺少或未识别这些分类目录：" + ", ".join(missing))

    if name == "PatCID" and audit.image_count > 100_000:
        warnings.append("图片数量很大，建议先用 benchmark 子集，不要直接混入第一阶段主训练集。")

    return warnings


def audit_dataset(repo_root: Path, name: str, rules: dict[str, Any]) -> DatasetAudit:
    root = repo_root / rules["root"]
    exists = root.exists()
    audit = DatasetAudit(
        name=name,
        root=root,
        exists=exists,
        role=rules.get("role", ""),
        warnings=[],
        decision=rules.get("first_pass_decision", ""),
    )
    if not exists:
        audit.warnings = decide_usability(name, audit, rules)
        return audit

    image_count, annotation_count, truncated = count_files(root)
    audit.image_count = image_count
    audit.annotation_count = annotation_count
    if truncated:
        audit.warnings.append(f"目录文件超过 {MAX_SCAN_FILES} 个，统计已截断。")

    archive_images, archive_annotations, archive_names = count_archive_members(root)
    audit.archive_image_count = archive_images
    audit.archive_annotation_count = archive_annotations
    audit.archive_names = archive_names

    required_class_dirs = rules.get("required_class_dirs")
    if required_class_dirs:
        audit.class_dir_counts = audit_class_dirs(root, required_class_dirs)
        audit.archive_class_counts = zip_class_counts(
            root,
            required_class_dirs,
            rules.get("class_aliases", {}),
        )
        # For crop-classification datasets, the useful archive image count is
        # the subset that appears under recognized class directories.
        audit.archive_image_count = sum(audit.archive_class_counts.values())

    audit.coco_categories = find_coco_categories(root)
    audit.warnings.extend(decide_usability(name, audit, rules))
    return audit


def markdown_table_row(values: list[str | int]) -> str:
    return "| " + " | ".join(str(value) for value in values) + " |"


def render_markdown(audits: list[DatasetAudit], config: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("# RegionOCR 本地数据可用性审计")
    lines.append("")
    lines.append("本报告由 `scripts/audit_regionocr_datasets.py` 生成。脚本只读取文件，不删除或改写原始数据。")
    lines.append("")
    lines.append("## 总览")
    lines.append("")
    lines.append("| 数据集 | 本地目录 | 图片数 | 标注文件数 | 压缩包图片数 | 压缩包标注数 | 一阶段建议 |")
    lines.append("|---|---:|---:|---:|---:|---:|---|")
    for audit in audits:
        root_status = "存在" if audit.exists else "缺失"
        lines.append(
            markdown_table_row(
                [
                    audit.name,
                    root_status,
                    audit.image_count,
                    audit.annotation_count,
                    audit.archive_image_count,
                    audit.archive_annotation_count,
                    audit.decision,
                ]
            )
        )
    lines.append("")

    for audit in audits:
        lines.append(f"## {audit.name}")
        lines.append("")
        lines.append(f"- 目录：`{audit.root}`")
        lines.append(f"- 角色：`{audit.role}`")
        lines.append(f"- 本地状态：{'存在' if audit.exists else '缺失'}")
        lines.append(f"- 图片数量：{audit.image_count}")
        lines.append(f"- 标注文件数量：{audit.annotation_count}")
        if audit.archive_image_count:
            lines.append(f"- 压缩包内可识别图片数量：{audit.archive_image_count}")
        if audit.archive_annotation_count:
            lines.append(f"- 压缩包内可识别标注文件数量：{audit.archive_annotation_count}")
        if audit.archive_names:
            lines.append("- 识别到的压缩包：" + ", ".join(audit.archive_names))
        if audit.coco_categories:
            lines.append("- 读取到的 COCO 类别：" + ", ".join(audit.coco_categories[:80]))
        if audit.class_dir_counts:
            class_counts = ", ".join(
                f"{name}={count}" for name, count in audit.class_dir_counts.items()
            )
            lines.append("- 分类目录图片数：" + class_counts)
        if audit.archive_class_counts:
            archive_class_counts = ", ".join(
                f"{name}={count}" for name, count in audit.archive_class_counts.items()
            )
            lines.append("- 压缩包分类图片数：" + archive_class_counts)
        if audit.warnings:
            lines.append("- 注意事项：")
            for warning in audit.warnings:
                lines.append(f"  - {warning}")
        else:
            lines.append("- 注意事项：未发现明显结构问题。")
        lines.append("")

    lines.append("## 目标标签")
    lines.append("")
    for label in config.get("target_labels", []):
        lines.append(f"- `{label}`")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("config/regionocr_dataset_rules.json"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/reports/regionocr_local_audit.md"),
    )
    args = parser.parse_args()

    repo_root = args.repo_root.resolve()
    config_path = args.config if args.config.is_absolute() else repo_root / args.config
    output_path = args.output if args.output.is_absolute() else repo_root / args.output

    config = load_json(config_path)
    audits = [
        audit_dataset(repo_root, name, rules)
        for name, rules in config.get("datasets", {}).items()
    ]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_markdown(audits, config), encoding="utf-8")
    print(f"Wrote audit report: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
