#!/usr/bin/env python3
"""Audit local Task 2 datasets for chemical-expression OCR and normalization.

The script only reads files. It does not delete or rewrite raw data. It checks
whether PEaCE and auxiliary OCSR datasets are present, counts common image and
annotation files, and writes a Markdown report with usability decisions for
mhchem/JSON normalization work.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp", ".webp"}
ANNOTATION_EXTS = {".json", ".jsonl", ".xml", ".txt", ".csv", ".sdf", ".mol"}
MAX_SCAN_FILES = 250_000


@dataclass
class DatasetAudit:
    name: str
    root: Path
    role: str
    exists: bool
    image_count: int = 0
    annotation_count: int = 0
    expected_status: dict[str, bool] = field(default_factory=dict)
    split_counts: dict[str, int] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    decision: str = ""


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def count_lines(path: Path) -> int:
    if not path.exists() or not path.is_file():
        return 0
    with path.open("r", encoding="utf-8", errors="replace") as f:
        return sum(1 for line in f if line.strip())


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


def inspect_peace(audit: DatasetAudit, rules: dict[str, Any]) -> None:
    expected = rules.get("expected_paths", [])
    audit.expected_status = {item: (audit.root / item).exists() for item in expected}
    for split_name, filename in [("train", "train.txt"), ("dev", "dev.txt"), ("test", "test.txt")]:
        audit.split_counts[split_name] = count_lines(audit.root / filename)

    missing = [item for item, exists in audit.expected_status.items() if not exists]
    if missing:
        audit.warnings.append("PEaCE 目录不完整，缺少：" + ", ".join(missing))
    if audit.image_count == 0:
        audit.warnings.append("未发现渲染图片，OCR 训练暂不可用。")
    if not (audit.root / "labels.jsonl").exists():
        audit.warnings.append("未发现 labels.jsonl，无法建立图像到 LaTeX ground truth 的清洗清单。")


def decide_generic(audit: DatasetAudit) -> None:
    if not audit.exists:
        audit.warnings.append("本地未发现数据目录，当前只能做方案级可用性判断。")
        return
    if audit.image_count == 0:
        audit.warnings.append("未发现常见图片文件；请确认数据是否已解压到约定目录。")
    if audit.annotation_count == 0:
        audit.warnings.append("未发现常见标注文件；只能作为待推理图片，不能直接训练或评估。")


def audit_dataset(repo_root: Path, name: str, rules: dict[str, Any]) -> DatasetAudit:
    root = repo_root / rules["root"]
    audit = DatasetAudit(
        name=name,
        root=root,
        role=rules.get("role", ""),
        exists=root.exists(),
        decision=rules.get("first_pass_decision", ""),
    )
    if not audit.exists:
        decide_generic(audit)
        return audit

    image_count, annotation_count, truncated = count_files(root)
    audit.image_count = image_count
    audit.annotation_count = annotation_count
    if truncated:
        audit.warnings.append(f"目录文件超过 {MAX_SCAN_FILES} 个，统计已截断。")

    if name == "PEaCE":
        inspect_peace(audit, rules)
    else:
        decide_generic(audit)

    if not audit.warnings:
        audit.warnings.append("未发现明显结构问题，可进入下一步清洗。")
    return audit


def row(values: list[str | int]) -> str:
    return "| " + " | ".join(str(value) for value in values) + " |"


def render_markdown(audits: list[DatasetAudit], config: dict[str, Any]) -> str:
    lines: list[str] = [
        "# 任务 2 本地数据可用性审计",
        "",
        "目标：化学表达式 OCR，并将识别结果规范化为 mhchem 或结构化 JSON。",
        "",
        "此报告由 `scripts/audit_task2_datasets.py` 生成。脚本只读取文件，不会删除或改写原始数据。",
        "",
        "## 总览",
        "",
        "| 数据集 | 角色 | 本地状态 | 图片数 | 标注文件数 | 建议 |",
        "|---|---|---:|---:|---:|---|",
    ]
    for audit in audits:
        lines.append(
            row(
                [
                    audit.name,
                    audit.role,
                    "存在" if audit.exists else "缺失",
                    audit.image_count,
                    audit.annotation_count,
                    audit.decision,
                ]
            )
        )
    lines.append("")

    for audit in audits:
        lines.extend(
            [
                f"## {audit.name}",
                "",
                f"- 目录：`{audit.root}`",
                f"- 角色：`{audit.role}`",
                f"- 本地状态：{'存在' if audit.exists else '缺失'}",
                f"- 图片数量：{audit.image_count}",
                f"- 标注文件数量：{audit.annotation_count}",
            ]
        )
        if audit.expected_status:
            status = ", ".join(
                f"{name}={'OK' if exists else '缺失'}"
                for name, exists in audit.expected_status.items()
            )
            lines.append("- PEaCE 必需文件：" + status)
        if audit.split_counts:
            split_status = ", ".join(f"{name}={count}" for name, count in audit.split_counts.items())
            lines.append("- split 行数：" + split_status)
        lines.append("- 注意事项：")
        for warning in audit.warnings:
            lines.append(f"  - {warning}")
        lines.append("")

    lines.extend(
        [
            "## 清洗结论",
            "",
            "- PEaCE 是任务 2 的核心数据源；只有当 `final_renders/`、`labels.jsonl` 和 split 文件齐全时，才可进入 OCR 训练/评估。",
            "- DECIMER-Segmentation、MolScribe、PatCID 属于结构图 OCSR 辅助数据，适合输出 SMILES、molfile 或结构 JSON，不应直接当作 mhchem 方程式 OCR 标注。",
            "- 当前公开数据链条缺少大规模 native mhchem ground truth；建议从 PEaCE 的 LaTeX 标签生成候选 mhchem，再做规则校验和人工抽样。",
            "",
            "## 目标输出",
            "",
        ]
    )
    for output in config.get("target_outputs", []):
        lines.append(f"- `{output}`")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("config/task2_chemical_expression_rules.json"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/reports/task2_local_audit.md"),
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
