#!/usr/bin/env python3
"""Build mhchem and reaction-JSON candidates from Task 2 OCR manifests.

This script is intentionally conservative: it creates reviewable candidates,
not final labels. PEaCE labels are LaTeX, so the output should be treated as a
normalization worklist for rule checks and human sampling.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path
from typing import Any


ARROW_PATTERNS = [
    (re.compile(r"\\xrightarrow(?:\[[^\]]*\])?\{([^{}]*)\}"), r" ->[\1] "),
    (re.compile(r"\\xleftarrow(?:\[[^\]]*\])?\{([^{}]*)\}"), r" <-[\1] "),
    (re.compile(r"\\rightleftharpoons\b"), " <=> "),
    (re.compile(r"\\leftrightarrow\b"), " <=> "),
    (re.compile(r"\\rightarrow\b|\\to\b|\\longrightarrow\b"), " -> "),
    (re.compile(r"\\leftarrow\b|\\longleftarrow\b"), " <- "),
]

TEXT_COMMANDS = [
    re.compile(r"\\(?:mathrm|mathbf|mathit|text|operatorname)\{([^{}]*)\}"),
    re.compile(r"\\(?:rm|bf|it)\s+([A-Za-z0-9+\-]+)"),
]

LATEX_REPLACEMENTS = {
    r"\cdot": ".",
    r"\bullet": ".",
    r"\Delta": "Delta",
    r"\circ": "deg",
    r"\,": " ",
    r"\;": " ",
    r"\:": " ",
    r"\ ": " ",
    "~": " ",
    "&": "",
}

STATE_RE = re.compile(r"\((aq|s|l|g|cr)\)$")
CHARGE_RE = re.compile(r"(\^(?:[0-9]*[+-]|[+-][0-9]*)|[0-9]+[+-]|[+-])$")
COEFF_RE = re.compile(r"^(\d+(?:/\d+)?|\d*\.\d+)\s*([A-Z(].*)$")


def read_manifest(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def strip_outer_math(text: str) -> str:
    text = text.strip()
    if text.startswith("$") and text.endswith("$"):
        return text.strip("$").strip()
    if text.startswith(r"\(") and text.endswith(r"\)"):
        return text[2:-2].strip()
    if text.startswith(r"\[") and text.endswith(r"\]"):
        return text[2:-2].strip()
    return text


def replace_text_commands(text: str) -> str:
    previous = None
    current = text
    while previous != current:
        previous = current
        for pattern in TEXT_COMMANDS:
            current = pattern.sub(r"\1", current)
    return current


def normalize_latex_expression(latex: str) -> str:
    text = strip_outer_math(latex)

    ce_match = re.search(r"\\ce\{(.+)\}", text)
    if ce_match:
        text = ce_match.group(1)

    text = replace_text_commands(text)
    for pattern, replacement in ARROW_PATTERNS:
        text = pattern.sub(replacement, text)
    for old, new in LATEX_REPLACEMENTS.items():
        text = text.replace(old, new)

    text = re.sub(r"_\{([^{}]+)\}", r"\1", text)
    text = re.sub(r"_(\w)", r"\1", text)
    text = re.sub(r"\^\{([^{}]+)\}", r"^\1", text)
    text = re.sub(r"\^([+\-0-9]+)", r"^\1", text)
    text = re.sub(r"\\[a-zA-Z]+", "", text)
    text = text.replace("{", "").replace("}", "")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def mhchem_candidate(latex: str) -> str:
    plain = normalize_latex_expression(latex)
    return rf"\ce{{{plain}}}" if plain else ""


def split_reaction(plain: str) -> tuple[str, str, str, str]:
    arrow_match = re.search(r"\s*(<=>|->|<-|=>|=)\s*(?:\[([^\]]*)\])?\s*", plain)
    if not arrow_match:
        return "", plain, "", ""
    left = plain[: arrow_match.start()].strip()
    right = plain[arrow_match.end() :].strip()
    arrow = arrow_match.group(1)
    condition = (arrow_match.group(2) or "").strip()
    return left, right, arrow, condition


def parse_species(token: str) -> dict[str, Any]:
    token = token.strip()
    coefficient = "1"
    coeff_match = COEFF_RE.match(token)
    if coeff_match:
        coefficient = coeff_match.group(1)
        token = coeff_match.group(2).strip()

    state = ""
    state_match = STATE_RE.search(token)
    if state_match:
        state = state_match.group(1)
        token = token[: state_match.start()].strip()

    charge = ""
    charge_match = CHARGE_RE.search(token)
    if charge_match:
        charge = charge_match.group(1).strip("{}").lstrip("^")
        token = token[: charge_match.start()].strip()

    return {
        "coefficient": coefficient,
        "formula": token,
        "state": state,
        "charge": charge,
    }


def parse_side(side: str) -> list[dict[str, Any]]:
    if not side:
        return []
    return [parse_species(part) for part in re.split(r"(?<!\^)\s+\+\s+|(?<!\^)\s+\+|(?<!\^)\+\s+", side) if part.strip()]


def reaction_json_candidate(latex: str) -> tuple[dict[str, Any], str, list[str]]:
    plain = normalize_latex_expression(latex)
    left, right, arrow, condition = split_reaction(plain)
    notes: list[str] = []
    status = "needs_review"

    reaction = {
        "source_latex": latex,
        "plain_candidate": plain,
        "arrow": arrow,
        "conditions": [condition] if condition else [],
        "reactants": parse_side(left) if arrow else [],
        "products": parse_side(right) if arrow else [],
    }

    if not plain:
        status = "empty"
        notes.append("empty normalized text")
    elif not arrow:
        status = "expression_only"
        notes.append("no reaction arrow detected")
    elif not reaction["reactants"] or not reaction["products"]:
        notes.append("reaction side is empty after parsing")
    else:
        notes.append("heuristic parse; verify stoichiometry, charge, state, and conditions")

    return reaction, status, notes


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "image_path",
        "source_dataset",
        "split",
        "latex",
        "mhchem_candidate",
        "normalization_status",
        "normalization_notes",
        "reaction_json",
    ]
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_jsonl(path: Path, payloads: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for payload in payloads:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path("data/processed/peace_expression_manifest.csv"),
    )
    parser.add_argument(
        "--output-csv",
        type=Path,
        default=Path("data/processed/peace_normalization_candidates.csv"),
    )
    parser.add_argument(
        "--output-jsonl",
        type=Path,
        default=Path("data/processed/peace_reaction_json_candidates.jsonl"),
    )
    args = parser.parse_args()

    manifest_rows = read_manifest(args.manifest)
    csv_rows: list[dict[str, str]] = []
    jsonl_rows: list[dict[str, Any]] = []

    for row in manifest_rows:
        latex = row.get("latex", "")
        reaction, status, notes = reaction_json_candidate(latex)
        payload = {
            "image_path": row.get("image_path", ""),
            "source_dataset": row.get("source_dataset", ""),
            "split": row.get("split", ""),
            **reaction,
            "normalization_status": status,
            "normalization_notes": notes,
        }
        jsonl_rows.append(payload)
        csv_rows.append(
            {
                "image_path": row.get("image_path", ""),
                "source_dataset": row.get("source_dataset", ""),
                "split": row.get("split", ""),
                "latex": latex,
                "mhchem_candidate": mhchem_candidate(latex),
                "normalization_status": status,
                "normalization_notes": "; ".join(notes),
                "reaction_json": json.dumps(reaction, ensure_ascii=False),
            }
        )

    write_csv(args.output_csv, csv_rows)
    write_jsonl(args.output_jsonl, jsonl_rows)
    print(f"Wrote normalization CSV: {args.output_csv.resolve()}")
    print(f"Wrote reaction JSONL: {args.output_jsonl.resolve()}")
    print(f"Rows: {len(csv_rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
