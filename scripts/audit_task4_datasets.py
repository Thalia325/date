#!/usr/bin/env python3
"""Audit local Task 4 datasets for chemistry education parsing."""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp", ".webp"}
DOCUMENT_EXTS = {".pdf", ".docx", ".doc", ".pptx", ".ppt"}
ANNOTATION_EXTS = {".json", ".jsonl", ".xml", ".txt", ".csv", ".tsv", ".yaml", ".yml", ".md"}
MAX_SCAN_FILES = 250_000


@dataclass
class DatasetAudit:
    name: str
    root: Path
    role: str
    source_type: str
    decision: str
    exists: bool
    local_status: str
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
    image_count = document_count = annotation_count = seen = 0
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


def dataset_actions(name: str, root_text: str) -> list[str]:
    common = [f"数据更新后重跑：python scripts\\audit_task4_datasets.py 和 python scripts\\build_task4_manifests.py。"]
    actions = {
        "M6Doc": [
            "完整训练/验证集需要按官方 README 提交申请并获得下载链接与解压密码。",
            "取得数据后放入 data/raw/M6Doc/annotations、train2017、val2017、test2017。",
            "优先筛出 Chemistry + textbook/test paper 页面，并映射原生 layout label 到任务 4 标签。",
        ],
        "ScienceQA": [
            "保留 chemistry 题目，规范化 question、choices、answer、lecture、solution、caption、image_path。",
            "图文题可使用本地图片；若未下载图片，至少保留 captions.json 作为图像文本上下文。",
        ],
        "SceMQA": [
            "保留 Chemistry 多选题，解析题干中 A/B/C/D 选项、答案、解释和图片引用。",
            "自由回答题暂不进入 choice-answer schema，可后续扩展到开放题 schema。",
        ],
        "ChineseChemExam": [
            "完成来源授权、脱敏、PDF/图片入库和去重后，再进入人工版面标注。",
            "建议首批标注 500-2000 页，覆盖题干、选项、图表、公式、答案区、解析区。",
        ],
        "ChineseChemLabHandout": [
            "完成来源授权、模板去重和页面化后，再标注实验目的、原理、药品、仪器、步骤、现象、结论、安全说明。",
            "建议首批标注 300-500 页，后续扩展到 1000-2000 页。",
        ],
    }
    return ([f"把数据放到 {root_text}。"] if name not in actions else []) + actions.get(name, []) + common


def audit_dataset(repo_root: Path, name: str, rules: dict[str, Any]) -> DatasetAudit:
    root_text = rules["root"]
    root = repo_root / root_text
    audit = DatasetAudit(
        name=name,
        root=root,
        role=rules.get("role", ""),
        source_type=rules.get("source_type", ""),
        decision=rules.get("first_pass_decision", ""),
        exists=root.exists(),
        local_status="missing",
        next_actions=dataset_actions(name, root_text),
    )
    if not root.exists():
        audit.warnings.append("本地未发现数据目录，当前只能完成方案级审查。")
        return audit

    (
        audit.image_count,
        audit.document_count,
        audit.annotation_count,
        audit.total_files_scanned,
        audit.truncated,
    ) = count_files(root)

    if name == "M6Doc" and not (root / "annotations").exists():
        audit.local_status = "access_required_or_incomplete"
        audit.warnings.append("已发现 M6Doc 目录，但未发现官方 annotations 目录；完整数据仍需申请或解压落盘。")
    elif audit.total_files_scanned == 0:
        audit.local_status = "empty"
        audit.warnings.append("目录存在但为空。")
    elif audit.image_count == 0 and audit.document_count == 0 and audit.annotation_count == 0:
        audit.local_status = "unrecognized"
        audit.warnings.append("未发现常见图片、文档或标注文件，请确认是否解压到约定目录。")
    else:
        audit.local_status = "present"

    if audit.truncated:
        audit.warnings.append(f"目录文件超过 {MAX_SCAN_FILES} 个，统计已截断。")
    if name in {"ScienceQA", "SceMQA"} and audit.annotation_count == 0:
        audit.warnings.append("未发现题目 JSON/JSONL，无法生成题目理解 manifest。")
    if name == "ScienceQA" and audit.image_count == 0:
        audit.warnings.append("ScienceQA 图片尚未下载；脚本会使用 captions.json 保留图像文本上下文。")
    if name.startswith("Chinese") and audit.annotation_count == 0:
        audit.warnings.append("自采数据尚无人工标注，当前只能生成待标注清单。")
    if not audit.warnings:
        audit.warnings.append("本地文件结构未发现明显问题，可进入任务 4 清洗转换。")
    return audit


def md_row(values: list[str | int]) -> str:
    return "| " + " | ".join(str(value) for value in values) + " |"


def render_markdown(audits: list[DatasetAudit], config: dict[str, Any]) -> str:
    lines = [
        "# 任务 4 本地数据清洗与审查报告",
        "",
        "目标：清洗出与化学/化工教育相关的数据，支撑教育文档页面结构化和科学教育内容理解。",
        "",
        "本报告由 `scripts/audit_task4_datasets.py` 生成；脚本只读文件，不删除或改写原始数据。",
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
                    audit.local_status,
                    audit.image_count,
                    audit.document_count,
                    audit.annotation_count,
                    audit.decision,
                ]
            )
        )

    lines.extend(["", "## 统一保留口径", ""])
    lines.extend(f"- {signal}" for signal in config.get("chemistry_keep_signals", []))
    lines.extend(["", "## 统一剔除口径", ""])
    lines.extend(f"- {criterion}" for criterion in config.get("drop_criteria", []))

    for audit in audits:
        lines.extend(
            [
                "",
                f"## {audit.name}",
                "",
                f"- 目录：`{audit.root}`",
                f"- 角色：`{audit.role}`",
                f"- 类型：`{audit.source_type}`",
                f"- 本地状态：{audit.local_status}",
                f"- 文件统计：图片 {audit.image_count}，文档 {audit.document_count}，标注/文本 {audit.annotation_count}",
                "- 审查结论：",
            ]
        )
        lines.extend(f"  - {warning}" for warning in audit.warnings)
        lines.append("- 下一步清洗动作：")
        lines.extend(f"  - {action}" for action in audit.next_actions)

    lines.extend(
        [
            "",
            "## 当前判断",
            "",
            "- ScienceQA 和 SceMQA 可自动补入公开题目数据，并生成题目理解 JSONL。",
            "- M6Doc 完整训练/验证集受官方申请与密码限制；未获批前只能保留公开说明、申请表或测试集。",
            "- 中文化学试卷与实验讲义仍应作为自采核心数据，公开数据不能直接替代细粒度中文教育版面标注。",
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
                    "local_status": audit.local_status,
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
    parser.add_argument("--config", type=Path, default=Path("config/task4_education_parsing_rules.json"))
    parser.add_argument("--output-md", type=Path, default=Path("data/reports/task4_local_audit.md"))
    parser.add_argument("--output-csv", type=Path, default=Path("data/processed/task4_dataset_review.csv"))
    args = parser.parse_args()

    repo_root = args.repo_root.resolve()
    config_path = args.config if args.config.is_absolute() else repo_root / args.config
    output_md = args.output_md if args.output_md.is_absolute() else repo_root / args.output_md
    output_csv = args.output_csv if args.output_csv.is_absolute() else repo_root / args.output_csv
    config = load_json(config_path)
    audits = [audit_dataset(repo_root, name, rules) for name, rules in config.get("datasets", {}).items()]

    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_md.write_text(render_markdown(audits, config), encoding="utf-8")
    write_csv(audits, output_csv)
    print(f"Wrote audit report: {output_md}")
    print(f"Wrote dataset review CSV: {output_csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
