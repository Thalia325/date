#!/usr/bin/env python3
"""Audit local Task 4 datasets for chemistry education parsing.

The script is intentionally conservative: it only reads local files, counts
common assets, checks whether expected dataset roots exist, and writes a
Markdown audit plus a CSV review table. Missing datasets are reported as
planning-level candidates rather than silently ignored.
"""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp", ".webp"}
DOCUMENT_EXTS = {".pdf", ".docx", ".doc", ".pptx", ".ppt"}
ANNOTATION_EXTS = {".json", ".jsonl", ".xml", ".txt", ".csv", ".tsv", ".yaml", ".yml"}
MAX_SCAN_FILES = 250_000


@dataclass
class DatasetAudit:
    name: str
    root: Path
    role: str
    source_type: str
    decision: str
    exists: bool
    image_count: int = 0
    document_count: int = 0
    annotation_count: int = 0
    total_files_scanned: int = 0
    truncated: bool = False
    warnings: list[str] = field(default_factory=list)
    next_actions: list[str] = field(default_factory=list)


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def count_files(root: Path) -> tuple[int, int, int, int, bool]:
    image_count = 0
    document_count = 0
    annotation_count = 0
    seen = 0
    truncated = False
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
        elif suffix in DOCUMENT_EXTS:
            document_count += 1
        elif suffix in ANNOTATION_EXTS:
            annotation_count += 1
    return image_count, document_count, annotation_count, seen, truncated


def add_dataset_actions(audit: DatasetAudit, name: str) -> None:
    if name == "M6Doc":
        audit.next_actions.extend(
            [
                "筛出 Chemistry + textbook/test paper 页面。",
                "把原生版面类映射到 question_block、figure、table、formula、paragraph 等目标类。",
                "抽样检查题干、选项、答案、实验步骤是否需要二次细标。",
            ]
        )
    elif name == "ScienceQA":
        audit.next_actions.extend(
            [
                "按 metadata 优先、关键词兜底筛选 Chemistry 题目。",
                "输出 question -> choices -> answer -> explanation 的 JSONL。",
                "图文题保留 image_path 与 text context，不能当作文档版面检测数据。",
            ]
        )
    elif name == "TQA":
        audit.next_actions.extend(
            [
                "筛选化学课程、章节、题目和关联图片。",
                "建立 question、supporting_text、supporting_figure 的链接清单。",
                "剔除上下文缺失或答案缺失的孤立样本。",
            ]
        )
    elif name == "ChineseChemExam":
        audit.next_actions.extend(
            [
                "按来源、年级、年份、题型建清单并脱敏。",
                "对 500-2000 页高价值样本标注题号、题干、选项、图表、公式、答案区。",
                "按来源隔离 train/val/test，避免同卷泄漏。",
            ]
        )
    elif name == "ChineseChemLabHandout":
        audit.next_actions.extend(
            [
                "按实验名称、课程阶段和来源建清单并去重。",
                "标注实验目的、原理、药品、仪器、步骤、现象、结论、注意事项、报告填写区。",
                "把装置图、表格和安全说明与对应实验步骤建立关系。",
            ]
        )


def audit_dataset(repo_root: Path, name: str, rules: dict[str, Any]) -> DatasetAudit:
    root = repo_root / rules["root"]
    audit = DatasetAudit(
        name=name,
        root=root,
        role=rules.get("role", ""),
        source_type=rules.get("source_type", ""),
        decision=rules.get("first_pass_decision", ""),
        exists=root.exists(),
    )
    add_dataset_actions(audit, name)

    if not audit.exists:
        audit.warnings.append("本地未发现数据目录，当前只能完成方案级审查。")
        audit.next_actions.insert(0, f"把数据放到 {rules['root']} 后重跑本脚本。")
        if name.startswith("Chinese"):
            audit.next_actions.insert(1, "先完成来源授权、PDF/图片入库、去重，再进入人工标注。")
        return audit

    (
        audit.image_count,
        audit.document_count,
        audit.annotation_count,
        audit.total_files_scanned,
        audit.truncated,
    ) = count_files(root)

    if audit.truncated:
        audit.warnings.append(f"目录文件超过 {MAX_SCAN_FILES} 个，统计已截断。")
    if audit.image_count == 0 and audit.document_count == 0:
        audit.warnings.append("未发现常见图片或文档文件，请确认数据是否已解压到约定目录。")
    if audit.annotation_count == 0:
        audit.warnings.append("未发现常见标注文件；如果是自采数据，需要补充版面和内容标注。")

    if not audit.warnings:
        audit.warnings.append("本地文件结构未发现明显问题，可进入任务 4 清洗转换。")
    return audit


def md_row(values: list[str | int]) -> str:
    return "| " + " | ".join(str(value) for value in values) + " |"


def render_markdown(audits: list[DatasetAudit], config: dict[str, Any]) -> str:
    lines = [
        "# 任务 4 本地数据清洗与审查报告",
        "",
        "目标：清洗出与化学/化工教育相关的数据，支撑教育文档页面结构化和科学教育内容理解两类任务。",
        "",
        "本报告由 `scripts/audit_task4_datasets.py` 生成。脚本只读取文件，不删除或改写原始数据。",
        "",
        "## 总览",
        "",
        "| 数据集 | 角色 | 本地状态 | 图片 | 文档 | 标注/文本 | 初步结论 |",
        "|---|---|---:|---:|---:|---:|---|",
    ]
    for audit in audits:
        lines.append(
            md_row(
                [
                    audit.name,
                    audit.role,
                    "存在" if audit.exists else "缺失",
                    audit.image_count,
                    audit.document_count,
                    audit.annotation_count,
                    audit.decision,
                ]
            )
        )

    lines.extend(
        [
            "",
            "## 统一保留口径",
            "",
        ]
    )
    for signal in config.get("chemistry_keep_signals", []):
        lines.append(f"- {signal}")

    lines.extend(["", "## 统一剔除口径", ""])
    for criterion in config.get("drop_criteria", []):
        lines.append(f"- {criterion}")

    for audit in audits:
        lines.extend(
            [
                "",
                f"## {audit.name}",
                "",
                f"- 目录：`{audit.root}`",
                f"- 角色：`{audit.role}`",
                f"- 类型：`{audit.source_type}`",
                f"- 本地状态：{'存在' if audit.exists else '缺失'}",
                f"- 文件统计：图片 {audit.image_count}，文档 {audit.document_count}，标注/文本 {audit.annotation_count}",
                "- 审查结论：",
            ]
        )
        for warning in audit.warnings:
            lines.append(f"  - {warning}")
        lines.append("- 下一步清洗动作：")
        for action in audit.next_actions:
            lines.append(f"  - {action}")

    lines.extend(
        [
            "",
            "## 目标输出",
            "",
        ]
    )
    for output in config.get("target_outputs", []):
        lines.append(f"- `{output}`")

    lines.extend(
        [
            "",
            "## 当前判断",
            "",
            "- M6Doc 是页面结构识别主数据；ScienceQA 和 TQA 是题目理解、图文上下文理解数据。",
            "- 公开数据缺少可直接训练的中文化学实验讲义细粒度解析标注。",
            "- 中文化学试卷与中文实验讲义/报告模板应作为任务 4 的核心自建数据，建议先标注 500-2000 页。",
            "",
        ]
    )
    return "\n".join(lines)


def write_csv(audits: list[DatasetAudit], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "dataset",
                "role",
                "source_type",
                "local_status",
                "image_count",
                "document_count",
                "annotation_count",
                "decision",
                "warnings",
                "next_actions",
            ],
        )
        writer.writeheader()
        for audit in audits:
            writer.writerow(
                {
                    "dataset": audit.name,
                    "role": audit.role,
                    "source_type": audit.source_type,
                    "local_status": "exists" if audit.exists else "missing",
                    "image_count": audit.image_count,
                    "document_count": audit.document_count,
                    "annotation_count": audit.annotation_count,
                    "decision": audit.decision,
                    "warnings": " | ".join(audit.warnings),
                    "next_actions": " | ".join(audit.next_actions),
                }
            )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("config/task4_education_parsing_rules.json"),
    )
    parser.add_argument(
        "--output-md",
        type=Path,
        default=Path("data/reports/task4_local_audit.md"),
    )
    parser.add_argument(
        "--output-csv",
        type=Path,
        default=Path("data/processed/task4_dataset_review.csv"),
    )
    args = parser.parse_args()

    repo_root = args.repo_root.resolve()
    config_path = args.config if args.config.is_absolute() else repo_root / args.config
    output_md = args.output_md if args.output_md.is_absolute() else repo_root / args.output_md
    output_csv = args.output_csv if args.output_csv.is_absolute() else repo_root / args.output_csv
    config = load_json(config_path)

    audits = [
        audit_dataset(repo_root, name, rules)
        for name, rules in config.get("datasets", {}).items()
    ]

    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_md.write_text(render_markdown(audits, config), encoding="utf-8")
    write_csv(audits, output_csv)
    print(f"Wrote audit report: {output_md}")
    print(f"Wrote dataset review CSV: {output_csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
