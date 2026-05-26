#!/usr/bin/env python3
"""Audit and prepare Task 3 reaction-condition KIE datasets.

The script is intentionally conservative: it only reads raw files and writes
small derived reports/manifests. Record-level cleaning can run once the five
source datasets are placed under data/raw using the configured directory names.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable


IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp", ".webp"}
TABLE_EXTS = {".csv", ".tsv", ".xlsx", ".xls", ".html"}
ANNOTATION_EXTS = {
    ".json",
    ".jsonl",
    ".ann",
    ".xml",
    ".txt",
    ".csv",
    ".tsv",
    ".proto",
    ".pbtxt",
}
ARCHIVE_EXTS = {".zip", ".tar", ".gz", ".tgz", ".bz2", ".xz", ".7z"}
MAX_SCAN_FILES = 250_000
MAX_TEXT_FILES = 200
MAX_TEXT_BYTES = 16_384
MAX_TABULAR_ROWS = 1_000


@dataclass
class DatasetAudit:
    name: str
    roots: list[Path]
    role: str
    priority: str
    exists: bool
    present_roots: list[Path] = field(default_factory=list)
    file_count: int = 0
    image_count: int = 0
    table_count: int = 0
    annotation_count: int = 0
    archive_count: int = 0
    expected_status: dict[str, bool] = field(default_factory=dict)
    split_counts: dict[str, int] = field(default_factory=dict)
    keyword_hits: dict[str, int] = field(default_factory=dict)
    field_hits: dict[str, int] = field(default_factory=dict)
    candidate_records: int = 0
    scanned_records: int = 0
    warnings: list[str] = field(default_factory=list)
    decision: str = ""
    cleaning_action: str = ""


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def normalize_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list, tuple)):
        try:
            return json.dumps(value, ensure_ascii=False)
        except TypeError:
            return str(value)
    return str(value)


def keyword_counter(text: str, keywords: Iterable[str]) -> dict[str, int]:
    lowered = text.lower()
    hits: dict[str, int] = {}
    for keyword in keywords:
        needle = keyword.lower()
        count = lowered.count(needle)
        if count:
            hits[keyword] = hits.get(keyword, 0) + count
    return hits


def merge_counts(target: dict[str, int], source: dict[str, int]) -> None:
    for key, value in source.items():
        target[key] = target.get(key, 0) + value


def iter_files(root: Path) -> Iterable[Path]:
    seen = 0
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        seen += 1
        if seen > MAX_SCAN_FILES:
            break
        yield path


def first_existing_roots(repo_root: Path, roots: list[str]) -> tuple[list[Path], list[Path]]:
    resolved = [repo_root / root for root in roots]
    present = [root for root in resolved if root.exists()]
    return resolved, present


def path_matches_glob(root: Path, pattern: str) -> bool:
    if any(char in pattern for char in "*?[]"):
        return any(root.glob(pattern))
    return (root / pattern).exists()


def count_nonempty_lines(path: Path) -> int:
    if not path.exists() or not path.is_file():
        return 0
    try:
        with path.open("r", encoding="utf-8", errors="replace") as f:
            return sum(1 for line in f if line.strip())
    except OSError:
        return 0


def sample_text(path: Path) -> str:
    try:
        with path.open("r", encoding="utf-8", errors="replace") as f:
            return f.read(MAX_TEXT_BYTES)
    except (OSError, UnicodeDecodeError):
        return ""


def record_has_kie_signal(record_text: str, keep_keywords: list[str], aliases: dict[str, list[str]]) -> bool:
    keyword_hits = keyword_counter(record_text, keep_keywords)
    field_hit_total = 0
    for values in aliases.values():
        field_hit_total += sum(keyword_counter(record_text, values).values())
    return sum(keyword_hits.values()) >= 2 or field_hit_total >= 2


def scan_csv_or_tsv(path: Path, keep_keywords: list[str], aliases: dict[str, list[str]]) -> tuple[int, int]:
    delimiter = "\t" if path.suffix.lower() == ".tsv" else ","
    scanned = 0
    candidates = 0
    try:
        with path.open("r", encoding="utf-8", errors="replace", newline="") as f:
            reader = csv.DictReader(f, delimiter=delimiter)
            for row in reader:
                scanned += 1
                row_text = normalize_text(row)
                if record_has_kie_signal(row_text, keep_keywords, aliases):
                    candidates += 1
                if scanned >= MAX_TABULAR_ROWS:
                    break
    except (csv.Error, OSError, UnicodeDecodeError):
        return 0, 0
    return scanned, candidates


def scan_jsonl(path: Path, keep_keywords: list[str], aliases: dict[str, list[str]]) -> tuple[int, int]:
    scanned = 0
    candidates = 0
    try:
        with path.open("r", encoding="utf-8", errors="replace") as f:
            for line in f:
                if not line.strip():
                    continue
                scanned += 1
                try:
                    payload = json.loads(line)
                except json.JSONDecodeError:
                    payload = line
                if record_has_kie_signal(normalize_text(payload), keep_keywords, aliases):
                    candidates += 1
                if scanned >= MAX_TABULAR_ROWS:
                    break
    except OSError:
        return 0, 0
    return scanned, candidates


def scan_json(path: Path, keep_keywords: list[str], aliases: dict[str, list[str]]) -> tuple[int, int]:
    try:
        if path.stat().st_size > 200_000_000:
            return 0, 0
        payload = load_json(path)
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return 0, 0

    records: list[Any]
    if isinstance(payload, list):
        records = payload[:MAX_TABULAR_ROWS]
    elif isinstance(payload, dict):
        list_values = [value for value in payload.values() if isinstance(value, list)]
        records = list_values[0][:MAX_TABULAR_ROWS] if list_values else [payload]
    else:
        records = [payload]

    scanned = 0
    candidates = 0
    for record in records:
        scanned += 1
        if record_has_kie_signal(normalize_text(record), keep_keywords, aliases):
            candidates += 1
    return scanned, candidates


def scan_text_record(path: Path, keep_keywords: list[str], aliases: dict[str, list[str]]) -> tuple[int, int]:
    text = sample_text(path)
    if not text.strip():
        return 0, 0
    return 1, int(record_has_kie_signal(text, keep_keywords, aliases))


def inspect_dataset(
    repo_root: Path,
    name: str,
    rules: dict[str, Any],
    config: dict[str, Any],
) -> DatasetAudit:
    roots, present_roots = first_existing_roots(repo_root, rules.get("roots", []))
    audit = DatasetAudit(
        name=name,
        roots=roots,
        role=rules.get("role", ""),
        priority=rules.get("priority", ""),
        exists=bool(present_roots),
        present_roots=present_roots,
        decision=rules.get("first_pass_decision", ""),
    )
    keep_keywords = config.get("keep_keywords", [])
    aliases = config.get("field_aliases", {})

    if not audit.exists:
        audit.warnings.append("Local raw directory is missing; only dataset-level screening is complete.")
        audit.cleaning_action = "download_or_mount_before_record_level_cleaning"
        return audit

    expected = rules.get("expected_paths", [])
    audit.expected_status = {
        item: any(path_matches_glob(root, item) for root in present_roots)
        for item in expected
    }

    text_files_scanned = 0
    truncated = False
    for root in present_roots:
        for path in iter_files(root):
            audit.file_count += 1
            suffix = path.suffix.lower()
            if suffix in IMAGE_EXTS:
                audit.image_count += 1
            if suffix in TABLE_EXTS:
                audit.table_count += 1
            if suffix in ANNOTATION_EXTS:
                audit.annotation_count += 1
            if suffix in ARCHIVE_EXTS:
                audit.archive_count += 1

            lower_name = path.name.lower()
            for split_name in ("train", "dev", "test", "valid", "validation"):
                if re.search(rf"(^|[_\-.]){split_name}([_\-.]|$)", lower_name):
                    audit.split_counts[split_name] = audit.split_counts.get(split_name, 0) + 1

            if suffix in {".txt", ".ann", ".xml", ".html", ".csv", ".tsv", ".json", ".jsonl"}:
                if text_files_scanned < MAX_TEXT_FILES:
                    text = sample_text(path)
                    merge_counts(audit.keyword_hits, keyword_counter(text, keep_keywords))
                    for field_name, field_aliases in aliases.items():
                        field_count = sum(keyword_counter(text, field_aliases).values())
                        if field_count:
                            audit.field_hits[field_name] = audit.field_hits.get(field_name, 0) + field_count
                    text_files_scanned += 1

            if suffix == ".jsonl":
                scanned, candidates = scan_jsonl(path, keep_keywords, aliases)
            elif suffix == ".json":
                scanned, candidates = scan_json(path, keep_keywords, aliases)
            elif suffix in {".csv", ".tsv"}:
                scanned, candidates = scan_csv_or_tsv(path, keep_keywords, aliases)
            elif suffix in {".txt", ".ann", ".xml", ".html"}:
                scanned, candidates = scan_text_record(path, keep_keywords, aliases)
            else:
                scanned, candidates = 0, 0
            audit.scanned_records += scanned
            audit.candidate_records += candidates

            if audit.file_count >= MAX_SCAN_FILES:
                truncated = True
                break

    if truncated:
        audit.warnings.append(f"File scan stopped at {MAX_SCAN_FILES} files.")

    missing_expected = [item for item, ok in audit.expected_status.items() if not ok]
    if missing_expected:
        audit.warnings.append("Missing expected paths: " + ", ".join(missing_expected))

    if audit.image_count == 0 and audit.role == "primary_visual_table_kie":
        audit.warnings.append("No image files found; visual table KIE is not ready.")
    if audit.annotation_count == 0:
        audit.warnings.append("No annotation or metadata files found.")
    if audit.scanned_records and audit.candidate_records == 0:
        audit.warnings.append("Sampled records did not show enough reaction-condition KIE signals.")

    if audit.candidate_records > 0:
        audit.cleaning_action = "keep_candidate_records_for_task3_kie"
    elif audit.annotation_count or audit.image_count or audit.table_count:
        audit.cleaning_action = "keep_dataset_pending_schema_specific_conversion"
    else:
        audit.cleaning_action = "manual_review_required"

    if not audit.warnings:
        audit.warnings.append("No blocking local structure issues detected in the sampled files.")

    return audit


def md_row(values: list[Any]) -> str:
    return "| " + " | ".join(str(value) for value in values) + " |"


def top_items(items: dict[str, int], limit: int = 8) -> str:
    if not items:
        return "-"
    pairs = sorted(items.items(), key=lambda item: (-item[1], item[0]))[:limit]
    return ", ".join(f"{key}:{value}" for key, value in pairs)


def render_markdown(audits: list[DatasetAudit], config: dict[str, Any]) -> str:
    lines: list[str] = [
        "# Task 3 local audit: reaction-condition and experiment-parameter KIE",
        "",
        "Goal: clean and screen the five proposed sources for chemistry/chemical-engineering data that can support reaction-condition table KIE.",
        "",
        "This report is generated by `scripts/audit_task3_datasets.py`. The script reads raw data and writes only derived reports/manifests.",
        "",
        "## Summary",
        "",
        "| Dataset | Role | Priority | Local status | Files | Images | Tables | Annotations | Sampled records | Candidate records | Cleaning action |",
        "|---|---|---:|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for audit in audits:
        lines.append(
            md_row(
                [
                    audit.name,
                    audit.role,
                    audit.priority,
                    "present" if audit.exists else "missing",
                    audit.file_count,
                    audit.image_count,
                    audit.table_count,
                    audit.annotation_count,
                    audit.scanned_records,
                    audit.candidate_records,
                    audit.cleaning_action,
                ]
            )
        )
    lines.extend(
        [
            "",
            "## Unified KIE schema",
            "",
            "The cleaned Task 3 output should map every usable table row, patent snippet, ORD reaction, or recipe entry into `data/processed/task3_kie_schema.json` fields. Core fields are reactants, products, catalysts, reagents, solvents, temperature, time, pH, pressure, yield, selectivity, conversion, molar ratio, operation, balanced equation, and evidence.",
            "",
            "## Dataset decisions",
            "",
        ]
    )

    for audit in audits:
        source_rules = config.get("datasets", {}).get(audit.name, {})
        roots = ", ".join(str(root) for root in audit.roots)
        present = ", ".join(str(root) for root in audit.present_roots) or "-"
        lines.extend(
            [
                f"### {audit.name}",
                "",
                f"- Source: {source_rules.get('source_url', '-')}",
                f"- Role: `{audit.role}`",
                f"- Configured roots: `{roots}`",
                f"- Present roots: `{present}`",
                f"- First-pass decision: `{audit.decision}`",
                f"- Cleaning action: `{audit.cleaning_action}`",
                f"- Keyword hits: {top_items(audit.keyword_hits)}",
                f"- Field hits: {top_items(audit.field_hits)}",
            ]
        )
        if audit.expected_status:
            status = ", ".join(f"{name}={'OK' if ok else 'missing'}" for name, ok in audit.expected_status.items())
            lines.append(f"- Expected paths: {status}")
        if audit.split_counts:
            lines.append("- Split-like files: " + ", ".join(f"{k}={v}" for k, v in sorted(audit.split_counts.items())))
        lines.append("- Screening notes:")
        for warning in audit.warnings:
            lines.append(f"  - {warning}")
        recommended = source_rules.get("recommended_use", [])
        if recommended:
            lines.append("- Recommended use after cleaning:")
            for item in recommended:
                lines.append(f"  - {item}")
        limitations = source_rules.get("limitations", [])
        if limitations:
            lines.append("- Limitations:")
            for item in limitations:
                lines.append(f"  - {item}")
        lines.append("")

    lines.extend(
        [
            "## Cleaning rules",
            "",
            "- Keep ChemTable condition-optimization, substrate-screening, and reaction-feature tables as the primary visual-table KIE source.",
            "- Use ChemTables as a table-type router and negative-sample source; do not treat it as field-level KIE ground truth.",
            "- Keep ChEMU entities and reaction steps for patent text KIE, especially materials, reagents/catalysts, products, solvents, temperature, time, and yields.",
            "- Use ORD/ORDerly as the normalized reaction schema and consistency benchmark rather than OCR/table ground truth.",
            "- Use solid-state synthesis recipes for operation/condition JSON design and materials synthesis examples.",
            "- Drop records dominated by bibliography, funding, generic statistics, or table-of-contents text unless they contain target KIE fields.",
            "",
            "## Current conclusion",
            "",
        ]
    )
    missing = [audit.name for audit in audits if not audit.exists]
    if missing:
        lines.append("Record-level cleaning is blocked for missing local raw datasets: " + ", ".join(missing) + ".")
    else:
        lines.append("All configured raw dataset roots are present; proceed to schema-specific converters.")
    lines.append("")
    return "\n".join(lines)


def write_manifest(path: Path, audits: list[DatasetAudit]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "dataset",
                "role",
                "priority",
                "local_status",
                "configured_roots",
                "present_roots",
                "files",
                "images",
                "tables",
                "annotations",
                "sampled_records",
                "candidate_records",
                "decision",
                "cleaning_action",
                "warnings",
            ],
        )
        writer.writeheader()
        for audit in audits:
            writer.writerow(
                {
                    "dataset": audit.name,
                    "role": audit.role,
                    "priority": audit.priority,
                    "local_status": "present" if audit.exists else "missing",
                    "configured_roots": ";".join(str(root) for root in audit.roots),
                    "present_roots": ";".join(str(root) for root in audit.present_roots),
                    "files": audit.file_count,
                    "images": audit.image_count,
                    "tables": audit.table_count,
                    "annotations": audit.annotation_count,
                    "sampled_records": audit.scanned_records,
                    "candidate_records": audit.candidate_records,
                    "decision": audit.decision,
                    "cleaning_action": audit.cleaning_action,
                    "warnings": " | ".join(audit.warnings),
                }
            )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--config", type=Path, default=Path("config/task3_reaction_condition_kie_rules.json"))
    parser.add_argument("--report", type=Path, default=Path("data/reports/task3_local_audit.md"))
    parser.add_argument("--manifest", type=Path, default=Path("data/processed/task3_dataset_manifest.csv"))
    parser.add_argument("--schema", type=Path, default=Path("data/processed/task3_kie_schema.json"))
    args = parser.parse_args()

    repo_root = args.repo_root.resolve()
    config_path = args.config if args.config.is_absolute() else repo_root / args.config
    report_path = args.report if args.report.is_absolute() else repo_root / args.report
    manifest_path = args.manifest if args.manifest.is_absolute() else repo_root / args.manifest
    schema_path = args.schema if args.schema.is_absolute() else repo_root / args.schema

    config = load_json(config_path)
    audits = [
        inspect_dataset(repo_root, name, rules, config)
        for name, rules in config.get("datasets", {}).items()
    ]

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(render_markdown(audits, config), encoding="utf-8")
    write_manifest(manifest_path, audits)
    write_json(schema_path, config.get("target_schema", {}))

    print(f"Wrote audit report: {report_path}")
    print(f"Wrote dataset manifest: {manifest_path}")
    print(f"Wrote KIE schema: {schema_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
