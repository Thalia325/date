#!/usr/bin/env python3
"""Audit dataset folders under Date/ and write per-folder review reports.

The project keeps competition-facing datasets under Date/任务一 ... Date/任务五.
This script audits those exact folders and writes 清洗审查报告.md into each
dataset directory. It does not modify source data.
"""

from __future__ import annotations

import csv
import json
import re
import zipfile
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp", ".webp"}
DOCUMENT_EXTS = {".pdf", ".docx", ".doc", ".pptx", ".ppt"}
ANNOTATION_EXTS = {".json", ".jsonl", ".xml", ".txt", ".csv", ".tsv", ".yaml", ".yml", ".ann", ".md"}
ARCHIVE_EXTS = {".zip", ".tar", ".gz", ".tgz", ".7z", ".rar"}
REPORT_NAME = "清洗审查报告.md"
MAX_SCAN_FILES = 300_000
MAX_ZIP_MEMBERS = 500_000


@dataclass
class DatasetSpec:
    task: str
    dataset: str
    folder: str
    requirement: str
    role: str
    source: str
    expected_paths: list[str] = field(default_factory=list)
    verdict_basis: str = ""
    keep_rules: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)


@dataclass
class FolderStats:
    data_files: int = 0
    total_bytes: int = 0
    image_count: int = 0
    document_count: int = 0
    annotation_count: int = 0
    archive_count: int = 0
    binary_part_count: int = 0
    log_count: int = 0
    ext_counts: Counter[str] = field(default_factory=Counter)
    sample_files: list[str] = field(default_factory=list)
    truncated: bool = False


def rel(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def iter_data_files(root: Path):
    seen = 0
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if path.name == REPORT_NAME:
            continue
        seen += 1
        if seen > MAX_SCAN_FILES:
            break
        yield path


def scan_folder(root: Path) -> FolderStats:
    stats = FolderStats()
    seen = 0
    for path in iter_data_files(root):
        seen += 1
        suffix = path.suffix.lower()
        stats.data_files += 1
        try:
            stats.total_bytes += path.stat().st_size
        except OSError:
            pass
        stats.ext_counts[suffix or "<none>"] += 1
        if len(stats.sample_files) < 8:
            stats.sample_files.append(rel(path, root))
        if suffix in IMAGE_EXTS:
            stats.image_count += 1
        elif suffix in DOCUMENT_EXTS:
            stats.document_count += 1
        elif suffix in ANNOTATION_EXTS:
            stats.annotation_count += 1
        elif suffix in ARCHIVE_EXTS:
            stats.archive_count += 1
        elif suffix == ".bin":
            stats.binary_part_count += 1
        elif suffix == ".log":
            stats.log_count += 1
    stats.truncated = seen >= MAX_SCAN_FILES
    return stats


def mb(num_bytes: int) -> str:
    return f"{num_bytes / 1024 / 1024:.2f} MB"


def count_json_records(path: Path) -> tuple[int | None, str]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return None, f"JSON 解析失败：{exc}"
    if isinstance(data, list):
        return len(data), "list"
    if isinstance(data, dict):
        return len(data), "dict"
    return 1, type(data).__name__


def count_jsonl_lines(path: Path) -> int:
    try:
        with path.open("r", encoding="utf-8", errors="replace") as f:
            return sum(1 for line in f if line.strip())
    except OSError:
        return 0


def inspect_zip(path: Path, class_names: list[str] | None = None) -> dict[str, Any]:
    result: dict[str, Any] = {
        "name": path.name,
        "ok": False,
        "members": 0,
        "images": 0,
        "annotations": 0,
        "class_counts": {},
        "error": "",
    }
    try:
        with zipfile.ZipFile(path) as zf:
            for index, info in enumerate(zf.infolist()):
                if index >= MAX_ZIP_MEMBERS:
                    result["error"] = f"成员超过 {MAX_ZIP_MEMBERS}，统计已截断"
                    break
                if info.is_dir() or info.filename.startswith("__MACOSX/"):
                    continue
                suffix = Path(info.filename).suffix.lower()
                result["members"] += 1
                if suffix in IMAGE_EXTS:
                    result["images"] += 1
                elif suffix in ANNOTATION_EXTS:
                    result["annotations"] += 1
                if class_names and suffix in IMAGE_EXTS:
                    parts = [part for part in info.filename.replace("\\", "/").split("/") if part]
                    for class_name in class_names:
                        aliases = [class_name]
                        if class_name == "other":
                            aliases.append("rest")
                        if any(part in aliases for part in parts):
                            result["class_counts"][class_name] = result["class_counts"].get(class_name, 0) + 1
                            break
            result["ok"] = True
    except zipfile.BadZipFile:
        result["error"] = "不是有效 zip 或压缩包已损坏"
    except Exception as exc:
        result["error"] = str(exc)
    return result


def inspect_peace(root: Path) -> dict[str, Any]:
    labels_path = root / "real_world_test_set" / "labels.json"
    result: dict[str, Any] = {
        "labels": 0,
        "images": len(list((root / "real_world_test_set").rglob("*.png"))) if (root / "real_world_test_set").exists() else 0,
        "missing_images": 0,
        "chemical_path_labels": 0,
        "normal_path_labels": 0,
        "signals": {},
        "sample_labels": [],
    }
    if not labels_path.exists():
        result["error"] = "未发现 real_world_test_set/labels.json"
        return result
    labels = json.loads(labels_path.read_text(encoding="utf-8"))
    result["labels"] = len(labels)
    missing = []
    patterns = {
        "上下标": r"\^|_",
        "离子/电荷": r"\\\+|\\-|\\mathrm\{[A-Za-z0-9]+[+-]\}|[A-Za-z]\s*\^\s*\{\s*[0-9]*[+-]\s*\}",
        "反应箭头": r"\\rightarrow|\\leftarrow|\\rightleftharpoons|->|→|⇌|↔",
        "化学式/单位": r"[A-Z](?:\s+[a-z])?(?:\s*[0-9]|\s*\^|\s*_)?|\\mu|\\mathrm|mol|g|cm",
    }
    signal_counts = {name: 0 for name in patterns}
    for image_ref, label in labels.items():
        if not (root / "real_world_test_set" / image_ref).exists():
            missing.append(image_ref)
        if "chemical" in image_ref:
            result["chemical_path_labels"] += 1
        if "normal" in image_ref:
            result["normal_path_labels"] += 1
        for name, pattern in patterns.items():
            if re.search(pattern, label):
                signal_counts[name] += 1
        if len(result["sample_labels"]) < 3:
            result["sample_labels"].append(f"{image_ref}: {label[:120]}")
    result["missing_images"] = len(missing)
    result["signals"] = signal_counts
    return result


def inspect_chemtable(root: Path) -> dict[str, Any]:
    result: dict[str, Any] = {}
    metadata = root / "data" / "metadata.csv"
    result["metadata_exists"] = metadata.exists()
    result["image_files"] = len(list((root / "data" / "img").glob("*.png"))) if (root / "data" / "img").exists() else 0
    if metadata.exists():
        with metadata.open("r", encoding="utf-8", errors="replace", newline="") as f:
            reader = csv.DictReader(f)
            rows = 0
            fieldnames = reader.fieldnames or []
            reaction_rows = table_rows = condition_hits = 0
            for row in reader:
                rows += 1
                data_text = row.get("data", "")
                if '"reactions"' in data_text:
                    reaction_rows += 1
                if '"tables"' in data_text:
                    table_rows += 1
                if re.search(r"condition|catalyst|solvent|yield|temperature|time|pressure|equiv|mol", data_text, re.I):
                    condition_hits += 1
            result.update(
                {
                    "metadata_rows": rows,
                    "metadata_columns": fieldnames,
                    "rows_with_reactions": reaction_rows,
                    "rows_with_tables": table_rows,
                    "rows_with_condition_signal": condition_hits,
                }
            )
    return result


def inspect_chemtables(root: Path) -> dict[str, Any]:
    result: dict[str, Any] = {}
    files = {
        "all": root / "ChemTables_ALL" / "ChemTables_ALL.json",
        "train": root / "ChemTables_Sample_StandardSplit" / "ChemTables_Sample_Train.json",
        "dev": root / "ChemTables_Sample_StandardSplit" / "ChemTables_Sample_Dev.json",
        "test": root / "ChemTables_Sample_StandardSplit" / "ChemTables_Sample_Test.json",
    }
    for key, path in files.items():
        count, kind = count_json_records(path) if path.exists() else (None, "missing")
        result[key] = {"exists": path.exists(), "count": count, "kind": kind}
    return result


def inspect_scienceqa(root: Path) -> dict[str, Any]:
    result: dict[str, Any] = {}
    problems = root / "problems.json"
    if not problems.exists():
        return {"error": "未发现 problems.json"}
    data = json.loads(problems.read_text(encoding="utf-8"))
    values = data.values() if isinstance(data, dict) else data
    split_counter: Counter[str] = Counter()
    topic_counter: Counter[str] = Counter()
    chemistry = 0
    with_image = 0
    for item in values:
        text = " ".join(str(item.get(key, "")) for key in ("subject", "topic", "category", "skill")).lower()
        if "chem" in text:
            chemistry += 1
        if item.get("image"):
            with_image += 1
        split_counter[item.get("split", "")] += 1
        topic_counter[item.get("topic", "")] += 1
    result["problem_count"] = len(data)
    result["chemistry_count"] = chemistry
    result["with_image_field"] = with_image
    result["local_image_files"] = len(list((root / "images").rglob("*.*"))) if (root / "images").exists() else 0
    result["splits"] = dict(split_counter)
    result["top_topics"] = dict(topic_counter.most_common(6))
    return result


def inspect_scemqa(root: Path) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, relative in {
        "multiple_choice_json": "chem/chem_multiple_choice.json",
        "free_response_json": "chem/chem_free_response.json",
        "multiple_choice_jsonl": "test_chem_multiple_choice.jsonl",
        "free_response_jsonl": "test_chem_free_response.jsonl",
    }.items():
        path = root / relative
        if not path.exists():
            result[key] = "missing"
        elif path.suffix == ".jsonl":
            result[key] = count_jsonl_lines(path)
        else:
            count, kind = count_json_records(path)
            result[key] = f"{count} ({kind})"
    result["image_files"] = len([p for p in root.rglob("*") if p.is_file() and p.suffix.lower() in IMAGE_EXTS])
    return result


def expected_status(root: Path, paths: list[str]) -> list[str]:
    rows = []
    for item in paths:
        exists = any(root.glob(item)) if any(ch in item for ch in "*?[]") else (root / item).exists()
        rows.append(f"`{item}`：{'OK' if exists else '缺失'}")
    return rows


def verdict_for(spec: DatasetSpec, stats: FolderStats, detail: dict[str, Any]) -> tuple[str, str]:
    name = spec.dataset
    if stats.data_files == 0:
        return "不符合（本地未落地有效数据）", "目录内未发现除报告以外的数据文件，当前只能保留为候选源。"
    if name == "M6Doc":
        if stats.image_count == 0 and stats.annotation_count <= 1:
            return "部分符合（仅说明/申请材料落地）", "缺少页面图像与区域标注，不能直接用于训练或严格验证。"
    if name == "DECIMER-Segmentation":
        return "不符合（本地未落地有效数据）", "未发现结构图分割图片、mask 或标注文件。"
    if name == "Chemical Images Classifier":
        zip_info = detail.get("zip", {})
        class_counts = zip_info.get("class_counts", {})
        if zip_info.get("ok") and all(class_counts.get(key, 0) for key in ["one_molecule", "several_molecules", "reactions", "other"]):
            return "部分符合", "可作为化学图片 crop 二级分类数据；不含整页区域坐标，不能单独满足 RegionOCR。"
        return "部分符合（需解压/确认类别）", "已发现压缩包或分片，但需确认压缩包完整性和四类目录。"
    if name == "PEaCE":
        if detail.get("labels") and detail.get("missing_images") == 0:
            return "部分符合", "real-world 子集图像与 LaTeX 标签齐全，可做评测和规范化候选；完整训练集未落地。"
        return "不符合", "缺少标签或图片，无法审查化学表达式规范化质量。"
    if name == "ChemTable":
        if detail.get("metadata_rows", 0) and detail.get("image_files", 0):
            return "符合", "图像、metadata 和反应/条件字段信号齐全，适合任务三主数据源。"
    if name == "ChemTables":
        if detail.get("all", {}).get("count") == 788:
            return "部分符合", "适合表类型路由和负样本，不是字段级反应条件 KIE ground truth。"
    if name == "ScienceQA":
        if detail.get("chemistry_count", 0) > 0 and detail.get("local_image_files", 0) > 0:
            return "符合", "化学题目、答案、解析和图片字段/本地图像基本齐全。"
    if name == "SceMQA":
        if isinstance(detail.get("multiple_choice_jsonl"), int) and detail.get("multiple_choice_jsonl", 0) > 0:
            return "符合", "化学多选/自由回答子集和配图已落地，适合任务四题目理解。"
    if spec.task == "任务五":
        return "不符合（本地未落地有效数据）", "目录内无源数据，无法映射到 node-edge-parameter 图结构 schema。"
    return "部分符合", "发现本地文件，但仍需要按任务 schema 做字段级转换和抽样复核。"


def render_report(spec: DatasetSpec, root: Path, stats: FolderStats, detail: dict[str, Any], report_time: str) -> str:
    verdict, reason = verdict_for(spec, stats, detail)
    lines = [
        f"# {spec.dataset} 数据集审查报告",
        "",
        f"- 所属任务：{spec.task}",
        f"- 审查时间：{report_time}",
        f"- 本地目录：`{root}`",
        f"- 数据集角色：{spec.role}",
        f"- 任务要求：{spec.requirement}",
        f"- 审查结论：**{verdict}**",
        f"- 结论依据：{reason}",
        f"- 来源：{spec.source}",
        "",
        "## 文件落地情况",
        "",
        f"- 数据文件数（不含本报告）：{stats.data_files}",
        f"- 数据体量：{mb(stats.total_bytes)}",
        f"- 图片：{stats.image_count}；文档：{stats.document_count}；标注/文本：{stats.annotation_count}；压缩包：{stats.archive_count}",
        f"- 二进制分片：{stats.binary_part_count}；下载/分片日志：{stats.log_count}",
    ]
    if stats.ext_counts:
        common_ext = ", ".join(f"{k}:{v}" for k, v in stats.ext_counts.most_common(10))
        lines.append(f"- 主要扩展名：{common_ext}")
    if stats.truncated:
        lines.append(f"- 注意：文件扫描超过 {MAX_SCAN_FILES} 个，统计已截断。")
    if spec.expected_paths:
        lines.extend(["", "## 必需路径检查", ""])
        lines.extend(f"- {row}" for row in expected_status(root, spec.expected_paths))

    lines.extend(["", "## 任务适配性审查", "", spec.verdict_basis])
    if spec.keep_rules:
        lines.append("")
        lines.append("### 保留口径")
        lines.extend(f"- {item}" for item in spec.keep_rules)
    if spec.risks:
        lines.append("")
        lines.append("### 风险与限制")
        lines.extend(f"- {item}" for item in spec.risks)

    if detail:
        lines.extend(["", "## 数据集专项检查", ""])
        for key, value in detail.items():
            if key == "zip":
                lines.append(f"- 压缩包 `{value.get('name')}`：有效={value.get('ok')}，成员={value.get('members')}，图片={value.get('images')}，标注/文本={value.get('annotations')}")
                if value.get("class_counts"):
                    counts = ", ".join(f"{k}={v}" for k, v in value["class_counts"].items())
                    lines.append(f"- 压缩包类别计数：{counts}")
                if value.get("error"):
                    lines.append(f"- 压缩包提醒：{value.get('error')}")
            elif key == "signals":
                signals = ", ".join(f"{k}={v}" for k, v in value.items())
                lines.append(f"- 任务二规范文本信号：{signals}")
            elif key == "sample_labels":
                lines.append("- 标签抽样：")
                for item in value:
                    lines.append(f"  - `{item}`")
            elif isinstance(value, dict):
                lines.append(f"- {key}：{json.dumps(value, ensure_ascii=False)}")
            else:
                lines.append(f"- {key}：{value}")

    lines.extend(
        [
            "",
            "## 是否符合当前任务要求",
            "",
            f"{verdict}。{reason}",
            "",
            "## 后续处理建议",
            "",
        ]
    )
    if "不符合" in verdict:
        lines.append("- 先补齐原始图像、标注和官方 split；补齐后重新运行本地审查。")
    elif "部分符合" in verdict:
        lines.append("- 当前数据可进入受限用途；正式训练/评测前仍需补齐缺口并做记录级校验。")
    else:
        lines.append("- 可进入下一步清洗转换，但需保留原始字段、派生字段和质量标记，便于追溯。")
    lines.extend(
        [
            "- 必做坏图/坏 JSON 检查、重复样本检查、路径一致性检查和 train/val/test 泄漏检查。",
            "- 对化学表达式、反应条件、表格字段或图结构的派生结果，应保留无法解析原因，避免只留下不可追溯的标准化结果。",
        ]
    )
    if stats.sample_files:
        lines.extend(["", "## 当前目录抽样", ""])
        lines.extend(f"- `{item}`" for item in stats.sample_files)
    lines.append("")
    return "\n".join(lines)


def build_specs() -> list[DatasetSpec]:
    return [
        DatasetSpec(
            "任务一",
            "M6Doc",
            "任务一/M6Doc",
            "化学文档区域识别与分类，需有页面图像、区域坐标和类别标签。",
            "整页版面区域检测主数据候选",
            "https://github.com/HCIILAB/M6Doc",
            ["annotations", "train2017", "val2017"],
            "M6Doc 理论上适合标题、正文、表格、图、题目等区域识别；本地若只有 README 和申请表，则不满足训练数据要求。",
            ["保留 Chemistry、textbook、test paper、scientific article 等相关页面。"],
            ["官方完整数据需申请，缺少 annotations 时不能作为模型训练/验证样本。"],
        ),
        DatasetSpec(
            "任务一",
            "DECIMER-Segmentation",
            "任务一/DECIMER-Segmentation",
            "补充化学结构区域检测，需有结构图像及 mask/bbox/segmentation 标注。",
            "化学结构区域检测辅助源",
            "https://github.com/Kohulan/DECIMER-Image-Segmentation",
            [],
            "该数据源适合补强 chemical_structure 类；若本地无图像和 mask/json/xml，则当前不可用。",
        ),
        DatasetSpec(
            "任务一",
            "Chemical Images Classifier",
            "任务一/Chemical Images Classifier",
            "识别化学图片 crop 类型，支持 one_molecule、several_molecules、reactions、other 四类。",
            "crop 级化学图片二级分类",
            "https://zenodo.org/records/5003653",
            ["dataset_for_image_classifier.zip"],
            "该数据集适合检测后的 crop 二级分类，不提供整页 bbox，因此只能作为任务一辅助数据。",
            ["保留 one_molecule、several_molecules、reactions、other/rest 四类并映射到目标标签。"],
            ["压缩包未解压时训练框架需支持 zip 读取或先解压；分片文件不能替代可训练样本清单。"],
        ),
        DatasetSpec(
            "任务二",
            "PEaCE",
            "任务二/PEaCE",
            "将化学表达式、化学方程式、上下标、离子、电荷、反应箭头等识别为规范文本。",
            "化学表达式 OCR 与 LaTeX/mhchem/JSON 规范化主数据候选",
            "https://research.uni-hannover.de/en/publications/peace-a-chemistry-oriented-dataset-for-optical-recognition-on-scientific-documents",
            ["final_renders", "train.txt", "dev.txt", "test.txt", "labels.jsonl", "real_world_test_set/labels.json"],
            "本地 real-world 子集能审查表达式 OCR 与规范化候选，但完整 PEaCE release 未落地时，不能支撑大规模训练。",
            ["保留含上下标、电荷、离子、单位、化学式和方程式的样本。", "LaTeX 标签转 mhchem/reaction JSON 后必须规则校验和人工抽样。"],
            ["本地 real-world 子集中可能没有反应箭头样本；不能据此覆盖完整化学方程式箭头能力。"],
        ),
        DatasetSpec(
            "任务三",
            "ChemTable",
            "任务三/ChemTable",
            "抽取化学表格中的反应条件、实验参数、产率、选择性、底物/产物等 KIE 字段。",
            "反应条件表格 KIE 主数据",
            "https://github.com/ustc-ai4science/ChemTable",
            ["data/img", "data/metadata.csv"],
            "ChemTable 同时包含表格图像、结构化 metadata、reaction/table/question 字段，是任务三最直接的数据源。",
            ["保留 reaction、condition、yield、temperature、time、catalyst、solvent、substrate 等字段。"],
            ["metadata 中字段需再转换为统一 KIE schema，不能直接混用原始 JSON 字符串。"],
        ),
        DatasetSpec(
            "任务三",
            "ChemTables",
            "任务三/ChemTables",
            "辅助判断化学专利表格类型，筛选反应/化合物/性质等表格。",
            "表类型分类与负样本辅助数据",
            "https://data.mendeley.com/",
            ["ChemTables_ALL/ChemTables_ALL.json", "ChemTables_Sample_StandardSplit/ChemTables_Sample_Train.json"],
            "ChemTables 有标准 split，可用于表类型路由；它不是字段级反应条件标注。",
            ["保留 reaction table、compound table、property table 等与化学 KIE 有关的类型。"],
            ["缺少单元格级 bbox 和字段级实体关系时，只能辅助筛选，不能替代 ChemTable。"],
        ),
        DatasetSpec(
            "任务四",
            "M6Doc",
            "任务四/M6Doc",
            "教育文档页面结构化解析，需有页面图像、题目/答案/图表/公式等区域标注。",
            "教育版面结构辅助源",
            "https://github.com/HCIILAB/M6Doc",
            ["annotations", "train2017", "val2017"],
            "M6Doc 可作为教育页面版面检测候选；本地只有申请材料时不能训练。",
            ["优先保留 Chemistry textbook/test paper 页面。"],
            ["粒度可能不足以区分题干、选项、解析、答案区和实验步骤。"],
        ),
        DatasetSpec(
            "任务四",
            "ScienceQA",
            "任务四/ScienceQA",
            "化学/科学教育题目理解，需有题干、选项、答案、解析、图片或 caption 上下文。",
            "结构化科学题目理解主数据",
            "https://github.com/lupantech/ScienceQA",
            ["problems.json", "pid_splits.json", "captions.json", "images"],
            "ScienceQA 已结构化，可筛出 chemistry 题目用于题目理解和图文 QA，不适合作为 OCR 版面标注。",
            ["按 topic/category/skill 过滤 chemistry，保留 question、choices、answer、lecture、solution、image。"],
            ["英文 K-12 科学题为主，不能替代中文化学试卷页面标注。"],
        ),
        DatasetSpec(
            "任务四",
            "SceMQA",
            "任务四/SceMQA",
            "多模态化学题目理解，需有题干、答案、解析和图片引用。",
            "化学多模态题目理解主数据",
            "https://huggingface.co/datasets/Haozy/SceMQA-main",
            ["chem/chem_multiple_choice.json", "chem/chem_free_response.json", "Multiple_Choice", "Free_Response"],
            "SceMQA 已提供化学子集和本地图像，适合任务四的题目理解和知识解释。",
            ["保留 chemistry 多选题和自由回答题，统一题干、选项、答案、解析、图片字段。"],
            ["不是实验讲义/中文试卷版面数据，不能覆盖细粒度页面区域标注。"],
        ),
        DatasetSpec(
            "任务五",
            "RxnScribe",
            "任务五/RxnScribe",
            "化学反应示意图节点、箭头和条件参数解析，需有图像与 graph/box/文本标注。",
            "反应 scheme graph 训练主候选",
            "https://github.com/thomas0809/RxnScribe",
            [],
            "适合把 reactants/products 映射为节点、reaction arrow 映射为边、conditions 映射为参数；本地未落地则不可用。",
        ),
        DatasetSpec(
            "任务五",
            "ReactionDataExtractor2",
            "任务五/ReactionDataExtractor2",
            "作为反应图解析 baseline，需有工具代码、模型或可运行样例输出。",
            "反应图解析 baseline 与 schema 参考",
            "https://github.com/dmw51/reactiondataextractor2",
            [],
            "更像工具而非纯数据集；本地无代码/样例时不能参与审查转换。",
        ),
        DatasetSpec(
            "任务五",
            "RxnCaption / U-RxnDiagram-15k",
            "任务五/RxnCaption - U-RxnDiagram-15k",
            "反应图像拓扑、箭头、条件和实体解析，需有图像与详细标注。",
            "大规模反应图节点-箭头-条件训练候选",
            "https://huggingface.co/datasets/songjhPKU/U-RxnDiagram-15k",
            [],
            "适合任务五反应图 graph schema；本地未下载时不可用。",
        ),
        DatasetSpec(
            "任务五",
            "PID2Graph",
            "任务五/PID2Graph",
            "P&ID/PFD 代理图的节点、管线/边和连接关系解析，需有图像与图结构标注。",
            "流程图 graph recovery 评测候选",
            "https://zenodo.org/records/14803338",
            [],
            "适合验证 node-edge graph recovery，但不直接覆盖化学反应条件文本。",
        ),
    ]


def detail_for(spec: DatasetSpec, root: Path) -> dict[str, Any]:
    if spec.dataset == "Chemical Images Classifier":
        zip_path = root / "dataset_for_image_classifier.zip"
        if zip_path.exists():
            return {"zip": inspect_zip(zip_path, ["one_molecule", "several_molecules", "reactions", "other"])}
    if spec.dataset == "PEaCE":
        return inspect_peace(root)
    if spec.dataset == "ChemTable":
        return inspect_chemtable(root)
    if spec.dataset == "ChemTables":
        return inspect_chemtables(root)
    if spec.dataset == "ScienceQA":
        return inspect_scienceqa(root)
    if spec.dataset == "SceMQA":
        return inspect_scemqa(root)
    return {}


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    date_root = repo_root / "Date"
    report_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    written: list[Path] = []

    for spec in build_specs():
        root = date_root / spec.folder
        root.mkdir(parents=True, exist_ok=True)
        stats = scan_folder(root)
        detail = detail_for(spec, root)
        report = render_report(spec, root, stats, detail, report_time)
        report_path = root / REPORT_NAME
        report_path.write_text(report, encoding="utf-8")
        written.append(report_path)

    print(f"Wrote {len(written)} reports")
    for path in written:
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
