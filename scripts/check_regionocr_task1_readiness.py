#!/usr/bin/env python3
"""Create a task-level readiness report for RegionOCR dataset preparation."""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path


IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp", ".webp"}
ANNOTATION_EXTS = {".json", ".xml", ".txt", ".csv"}
MODEL_EXTS = {".h5", ".pt", ".pth", ".onnx", ".ckpt"}


@dataclass
class ReadinessItem:
    capability: str
    status: str
    evidence: str
    next_action: str


def count_files(root: Path, exts: set[str]) -> int:
    if not root.exists():
        return 0
    return sum(1 for path in root.rglob("*") if path.is_file() and path.suffix.lower() in exts)


def count_csv_rows(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        return sum(1 for _row in reader)


def status_icon(status: str) -> str:
    return {
        "ready": "可用",
        "partial": "部分可用",
        "missing": "缺失",
    }[status]


def build_items(repo_root: Path) -> list[ReadinessItem]:
    raw = repo_root / "data" / "raw"
    processed = repo_root / "data" / "processed"

    m6doc_root = raw / "M6Doc"
    m6doc_images = count_files(m6doc_root, IMAGE_EXTS)
    m6doc_annotations = count_files(m6doc_root, ANNOTATION_EXTS)
    if m6doc_images and m6doc_annotations:
        m6doc_status = "ready"
        m6doc_action = "运行 COCO 转换脚本生成页面级 RegionOCR JSONL。"
    else:
        m6doc_status = "missing"
        m6doc_action = "申请并落地 M6Doc train/val，至少包含 annotations 和 train2017/val2017。"

    decimer_root = raw / "DECIMER-Segmentation"
    decimer_images = count_files(decimer_root, IMAGE_EXTS)
    decimer_annotations = count_files(decimer_root, ANNOTATION_EXTS)
    decimer_models = count_files(decimer_root, MODEL_EXTS)
    if decimer_annotations:
        decimer_status = "ready"
        decimer_action = "将化学结构区域标注转换为 RegionOCR JSONL。"
    elif decimer_models:
        decimer_status = "partial"
        decimer_action = "模型可用于推理生成候选框；如要训练仍需人工/公开标注。"
    else:
        decimer_status = "missing"
        decimer_action = "落地 DECIMER-Segmentation 模型或可转换标注，用于补强 chemical_structure 区域。"

    chemic_manifest = processed / "chemical_classifier_manifest.csv"
    chemic_rows = count_csv_rows(chemic_manifest)
    if chemic_rows:
        chemic_status = "ready"
        chemic_action = "作为检测后 crop 的二级分类数据，不作为整页 bbox 数据。"
    else:
        chemic_status = "missing"
        chemic_action = "运行 build_chemical_classifier_manifest.py 生成分类 manifest。"

    regions_jsonl = [
        processed / "m6doc_regionocr_regions.jsonl",
        processed / "decimer_regionocr_regions.jsonl",
        processed / "patcid_regionocr_regions.jsonl",
    ]
    regions_rows = 0
    for path in regions_jsonl:
        if path.exists():
            with path.open("r", encoding="utf-8") as f:
                regions_rows += sum(1 for line in f if line.strip())
    if regions_rows:
        regions_status = "partial" if not (m6doc_images and m6doc_annotations) else "ready"
        regions_action = "抽样核验 bbox、type、text_ref、image_ref 后进入训练/评测。"
    else:
        regions_status = "missing"
        regions_action = "M6Doc/DECIMER 标注到位后运行 build_regionocr_regions_from_coco.py。"

    return [
        ReadinessItem(
            "整页版面检测",
            m6doc_status,
            f"M6Doc images={m6doc_images}, annotations={m6doc_annotations}",
            m6doc_action,
        ),
        ReadinessItem(
            "化学结构区域检测",
            decimer_status,
            f"DECIMER images={decimer_images}, annotations={decimer_annotations}, models={decimer_models}",
            decimer_action,
        ),
        ReadinessItem(
            "化学图片 crop 二级分类",
            chemic_status,
            f"chemical_classifier_manifest rows={chemic_rows}",
            chemic_action,
        ),
        ReadinessItem(
            "RegionOCR regions JSONL",
            regions_status,
            f"region records={regions_rows}",
            regions_action,
        ),
    ]


def render_markdown(items: list[ReadinessItem]) -> str:
    ready_count = sum(1 for item in items if item.status == "ready")
    missing = [item.capability for item in items if item.status == "missing"]
    lines = [
        "# 任务一 RegionOCR 准备度报告",
        "",
        f"总体状态：{ready_count}/{len(items)} 项可用。",
        "",
    ]
    if missing:
        lines.append("当前还不能宣称任务一完整清洗完成；缺口集中在：" + "、".join(missing) + "。")
    else:
        lines.append("核心数据链路已具备，可进入抽样质检和训练/评测准备。")
    lines.extend(
        [
            "",
            "| 能力 | 状态 | 本地证据 | 下一步 |",
            "|---|---|---|---|",
        ]
    )
    for item in items:
        lines.append(
            f"| {item.capability} | {status_icon(item.status)} | {item.evidence} | {item.next_action} |"
        )
    lines.extend(
        [
            "",
            "## 推荐复跑命令",
            "",
            "```powershell",
            "python scripts\\audit_regionocr_datasets.py",
            "python scripts\\build_chemical_classifier_manifest.py",
            "python scripts\\check_regionocr_task1_readiness.py",
            "```",
            "",
            "M6Doc 或 DECIMER 标注转成 COCO 后，继续运行：",
            "",
            "```powershell",
            "python scripts\\build_regionocr_regions_from_coco.py `",
            "  --input-json data\\raw\\M6Doc\\annotations\\instances_train2017.json `",
            "  --dataset-name M6Doc `",
            "  --image-root data\\raw\\M6Doc\\train2017 `",
            "  --output-jsonl data\\processed\\m6doc_regionocr_regions.jsonl",
            "```",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/reports/regionocr_task1_readiness.md"),
    )
    args = parser.parse_args()

    repo_root = args.repo_root.resolve()
    output_path = args.output if args.output.is_absolute() else repo_root / args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_markdown(build_items(repo_root)), encoding="utf-8")
    print(f"Wrote readiness report: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
