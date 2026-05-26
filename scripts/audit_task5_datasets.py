#!/usr/bin/env python3
"""Audit Task 5 dataset candidates.

This script performs a conservative local audit for the optional task:
lightweight chemical process / reaction diagram node-arrow-parameter parsing.
It does not download large archives. It checks expected local roots, counts
common image/annotation/archive files, and writes review artifacts that can be
opened in spreadsheet tools.
"""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp", ".webp"}
ANNOTATION_EXTS = {".json", ".jsonl", ".xml", ".txt", ".csv", ".tsv", ".yaml", ".yml"}
ARCHIVE_EXTS = {".zip", ".tar", ".gz", ".tgz", ".7z", ".rar"}
MAX_SCAN_FILES = 250_000


@dataclass
class DatasetAudit:
    dataset_id: str
    name: str
    raw_root: Path
    source_url: str
    download_url: str
    license: str
    source_type: str
    scale_note: str
    annotation_shape: str
    chem_relevance_score: int
    process_graph_fit_score: int
    primary_role: str
    decision: str
    cleaning_rule: str
    known_limitations: str
    next_actions: str
    exists: bool
    image_count: int = 0
    annotation_count: int = 0
    archive_count: int = 0
    total_files_scanned: int = 0
    truncated: bool = False
    warnings: list[str] = field(default_factory=list)

    @property
    def local_status(self) -> str:
        return "present" if self.exists else "missing"

    @property
    def combined_score(self) -> int:
        return self.chem_relevance_score + self.process_graph_fit_score

    @property
    def cleaned_use_tier(self) -> str:
        if self.decision in {"keep_core", "keep_core_for_graph_eval"}:
            return "core"
        if self.decision in {"keep_auxiliary", "keep_auxiliary_with_license_check"}:
            return "auxiliary"
        if self.decision == "keep_transfer_only":
            return "transfer_only"
        return "later_or_hold"


def load_config(repo_root: Path) -> dict[str, Any]:
    config_path = repo_root / "config" / "task5_dataset_rules.json"
    with config_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def count_files(root: Path) -> tuple[int, int, int, int, bool]:
    image_count = 0
    annotation_count = 0
    archive_count = 0
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
        elif suffix in ANNOTATION_EXTS:
            annotation_count += 1
        elif suffix in ARCHIVE_EXTS:
            archive_count += 1
    return image_count, annotation_count, archive_count, seen, truncated


def audit_dataset(repo_root: Path, rules: dict[str, Any]) -> DatasetAudit:
    raw_root = repo_root / rules["raw_root"]
    audit = DatasetAudit(
        dataset_id=rules["dataset_id"],
        name=rules["name"],
        raw_root=raw_root,
        source_url=rules["source_url"],
        download_url=rules["download_url"],
        license=rules["license"],
        source_type=rules["source_type"],
        scale_note=rules["scale_note"],
        annotation_shape=rules["annotation_shape"],
        chem_relevance_score=int(rules["chem_relevance_score"]),
        process_graph_fit_score=int(rules["process_graph_fit_score"]),
        primary_role=rules["primary_role"],
        decision=rules["decision"],
        cleaning_rule=rules["cleaning_rule"],
        known_limitations=rules["known_limitations"],
        next_actions=rules["next_actions"],
        exists=raw_root.exists(),
    )

    if not audit.exists:
        audit.warnings.append(
            f"Local dataset root not found; place files under {rules['raw_root']} and rerun this audit."
        )
        return audit

    (
        audit.image_count,
        audit.annotation_count,
        audit.archive_count,
        audit.total_files_scanned,
        audit.truncated,
    ) = count_files(raw_root)

    if audit.truncated:
        audit.warnings.append(f"Scan stopped after {MAX_SCAN_FILES} files; counts are lower bounds.")
    if audit.image_count == 0 and audit.archive_count == 0:
        audit.warnings.append("No image files or archives found in the local root.")
    if audit.annotation_count == 0 and audit.dataset_id in {
        "rxnscribe",
        "urxndiagram15k",
        "pid2graph",
        "pidcon",
    }:
        audit.warnings.append("Core graph dataset has no local annotation files yet.")
    if not audit.warnings:
        audit.warnings.append("Local file structure is ready for the next conversion step.")
    return audit


def write_csv(path: Path, audits: list[DatasetAudit]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "dataset_id",
        "name",
        "cleaned_use_tier",
        "decision",
        "source_type",
        "local_status",
        "image_count",
        "annotation_count",
        "archive_count",
        "total_files_scanned",
        "chem_relevance_score",
        "process_graph_fit_score",
        "combined_score",
        "primary_role",
        "annotation_shape",
        "cleaning_rule",
        "known_limitations",
        "license",
        "source_url",
        "download_url",
        "warnings",
        "next_actions",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for audit in audits:
            writer.writerow(
                {
                    "dataset_id": audit.dataset_id,
                    "name": audit.name,
                    "cleaned_use_tier": audit.cleaned_use_tier,
                    "decision": audit.decision,
                    "source_type": audit.source_type,
                    "local_status": audit.local_status,
                    "image_count": audit.image_count,
                    "annotation_count": audit.annotation_count,
                    "archive_count": audit.archive_count,
                    "total_files_scanned": audit.total_files_scanned,
                    "chem_relevance_score": audit.chem_relevance_score,
                    "process_graph_fit_score": audit.process_graph_fit_score,
                    "combined_score": audit.combined_score,
                    "primary_role": audit.primary_role,
                    "annotation_shape": audit.annotation_shape,
                    "cleaning_rule": audit.cleaning_rule,
                    "known_limitations": audit.known_limitations,
                    "license": audit.license,
                    "source_url": audit.source_url,
                    "download_url": audit.download_url,
                    "warnings": " | ".join(audit.warnings),
                    "next_actions": audit.next_actions,
                }
            )


def write_graph_schema(path: Path, config: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    schema = {
        "schema_name": "task5_lightweight_chemical_process_graph",
        "version": "0.2",
        "graph_record": {
            "diagram_id": "string",
            "source_dataset": "string",
            "image_path": "string",
            "split": "train|val|test",
            "nodes": [
                {
                    "node_id": "string",
                    "type": config["target_schema"]["node_types"],
                    "bbox": [0, 0, 0, 0],
                    "text": "optional string",
                    "attributes": {
                        "smiles": "optional string",
                        "equipment_tag": "optional string",
                        "topology_class": "optional string",
                        "confidence": "optional number",
                    },
                }
            ],
            "edges": [
                {
                    "edge_id": "string",
                    "type": config["target_schema"]["edge_types"],
                    "source_node_id": "string",
                    "target_node_id": "string",
                    "polyline": [[0, 0], [1, 1]],
                    "arrowhead": "none|source|target|both|unknown",
                    "parameters": [
                        {
                            "type": config["target_schema"]["parameter_types"],
                            "text": "string",
                            "value": "optional string or number",
                            "unit": "optional string",
                            "bbox": [0, 0, 0, 0],
                        }
                    ],
                }
            ],
            "text_blocks": [
                {
                    "text_id": "string",
                    "text": "string",
                    "bbox": [0, 0, 0, 0],
                    "linked_node_id": "optional string",
                    "linked_edge_id": "optional string",
                }
            ],
        },
    }
    path.write_text(json.dumps(schema, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def render_markdown(audits: list[DatasetAudit], config: dict[str, Any]) -> str:
    lines = [
        "# 任务 5 数据集清洗与审查报告",
        "",
        "目标：清洗出与化学、化工相关，并可支撑轻量化工流程图/反应路线图节点-箭头-参数解析的数据源。",
        "",
        f"说明：本次审查纳入 {len(audits)} 个候选源，覆盖反应图解析数据、P&ID/PFD 工程图代理数据，以及通用图表迁移数据；审查口径统一为是否能映射到 node-edge-parameter graph schema。",
        "",
        "## 总览",
        "",
        "| 数据集 | 清洗档位 | 决策 | 化学/化工相关 | 图结构适配 | 本地状态 | 关键用途 |",
        "|---|---|---|---:|---:|---|---|",
    ]
    for audit in audits:
        lines.append(
            f"| {audit.name} | {audit.cleaned_use_tier} | {audit.decision} | "
            f"{audit.chem_relevance_score}/5 | {audit.process_graph_fit_score}/5 | "
            f"{audit.local_status} | {audit.primary_role} |"
        )

    lines.extend(["", "## 统一保留信号", ""])
    for signal in config["keep_signals"]:
        lines.append(f"- {signal}")

    lines.extend(["", "## 统一剔除信号", ""])
    for signal in config["drop_signals"]:
        lines.append(f"- {signal}")

    lines.extend(
        [
            "",
            "## 推荐路线",
            "",
            "1. 用 RxnScribe 建立反应 scheme graph 的节点、箭头、条件参数抽取基线。",
            "2. 用 RxnCaption / U-RxnDiagram-15k 扩大反应图拓扑、箭头和条件解析训练覆盖。",
            "3. 用 ReactionDataExtractor2 作为 baseline parser 和结构化输出参考。",
            "4. 用 PID2Graph 验证 P&ID/PFD 代理图的 node-edge graph recovery。",
            "5. 将 PIDCon、PID_dataset、Dataset-P&ID/Digitize-PID 放入工程图扩展阶段；AI2D 仅用于通用 node-arrow-text 迁移预训练。",
            "",
            "## 数据集细审",
            "",
        ]
    )

    for audit in audits:
        lines.extend(
            [
                f"### {audit.name}",
                "",
                f"- 原始目录：`{audit.raw_root}`",
                f"- 来源：{audit.source_url}",
                f"- 下载：{audit.download_url}",
                f"- 许可/访问：{audit.license}",
                f"- 数据形态：{audit.source_type}",
                f"- 规模说明：{audit.scale_note}",
                f"- 标注形态：{audit.annotation_shape}",
                f"- 清洗规则：{audit.cleaning_rule}",
                f"- 局限：{audit.known_limitations}",
                f"- 下一步：{audit.next_actions}",
                f"- 本地统计：images={audit.image_count}, annotations={audit.annotation_count}, archives={audit.archive_count}, scanned={audit.total_files_scanned}",
                "- 审查提醒：",
            ]
        )
        for warning in audit.warnings:
            lines.append(f"  - {warning}")
        lines.append("")

    lines.extend(
        [
            "## 产物",
            "",
            "- `data/processed/task5_dataset_review.csv`：可导入 Google Sheets 的清洗审查表。",
            "- `data/processed/task5_graph_schema.json`：统一 node-edge-parameter graph schema。",
            "- `outputs/task5/task5_dataset_review.xlsx`：带摘要页的 Google Sheets 兼容工作簿。",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=".", help="Repository root")
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    config = load_config(repo_root)
    audits = [audit_dataset(repo_root, item) for item in config["datasets"]]
    audits.sort(key=lambda item: (-item.combined_score, item.name.lower()))

    write_csv(repo_root / "data" / "processed" / "task5_dataset_review.csv", audits)
    write_graph_schema(repo_root / "data" / "processed" / "task5_graph_schema.json", config)
    report = render_markdown(audits, config)
    report_path = repo_root / "data" / "reports" / "task5_local_audit.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report, encoding="utf-8")

    print(f"Wrote {repo_root / 'data' / 'processed' / 'task5_dataset_review.csv'}")
    print(f"Wrote {repo_root / 'data' / 'processed' / 'task5_graph_schema.json'}")
    print(f"Wrote {report_path}")


if __name__ == "__main__":
    main()
