# Task 2 Completion Summary

Date: 2026-05-26

## What was completed

- Added a local PEaCE source under `data/raw/PEaCE/real_world_test_set`.
- Indexed 319 PEaCE real-world OCR records from the GitHub-hosted test set.
- Generated a non-empty Task 2 OCR manifest with 78 likely chemical-expression records:
  - `data/processed/peace_expression_manifest.csv`
- Generated reviewable LaTeX -> mhchem / reaction JSON candidates:
  - `data/processed/peace_normalization_candidates.csv`
  - `data/processed/peace_reaction_json_candidates.jsonl`
- Updated the Task 2 audit script so it recognizes both the full PEaCE release layout and the PEaCE real-world test-set layout.
- Updated normalization so PEaCE character-spaced labels such as `C O _ { 2 }` are converted into usable candidates such as `CO2`.
- Added `scripts/download_peace_full_release.ps1` for resumable full-release download and optional extraction.

## Current counts

| Output | Count | Notes |
|---|---:|---|
| PEaCE real-world source images | 319 | 135 chemical/special, 184 normal cells |
| `peace_expression_manifest.csv` | 78 | Filtered likely chemical-expression records |
| `peace_normalization_candidates.csv` | 78 | Candidate labels, not final mhchem ground truth |
| `peace_reaction_json_candidates.jsonl` | 78 | 77 expression-only, 1 equality-style candidate |

## Sample review

| Coverage type | Example source | Candidate | Review note |
|---|---|---|---|
| Molecular formula | `cell_chemical&special/3_8.png` | `\ce{CO2 desorption \ temperature^e [^deg C]}` | Formula recovered from token-spaced PEaCE label; surrounding prose/unit text still needs human review before final mhchem labeling. |
| Simple formula | `cell_normal/5_25.png` | `\ce{MgO}` | Good OCR-to-candidate example for simple formula recognition. |
| Gas/condition text | `cell_chemical&special/11_10.png` | `\ce{4^deg C/min H2 flow 30 mL/min}` | Captures temperature/rate/gas condition text; should remain expression metadata rather than reaction JSON. |
| Unit expression | `cell_chemical&special/21_6.png` | `\ce{(s^-1 or L mol^-1 s^-1)}` | Useful for exponent/unit OCR; not a reaction record. |
| Equality-like expression | `cell_chemical&special/14_54.png` | `\ce{MN = (MNCARB+MNGRI)/2 .}` | Flagged as `needs_review`; parser treats `=` as an equation delimiter, but this is not a chemical reaction. |

## Remaining boundary

The local dataset is now sufficient for record-level Task 2 cleaning on the PEaCE real-world subset. It is not yet sufficient for full-scale OCR training, because the 5.43GB PEaCE full release still needs to be downloaded and extracted into:

```text
data/raw/PEaCE/final_renders/
data/raw/PEaCE/labels.jsonl
data/raw/PEaCE/train.txt
data/raw/PEaCE/dev.txt
data/raw/PEaCE/test.txt
```

The full-release download was reachable, but the first local download attempt timed out before completion. The partial archive was removed to avoid corrupt raw data. Use the resumable downloader when ready:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\download_peace_full_release.ps1 -Extract
```

After the full release is present, rerun:

```powershell
python scripts\audit_task2_datasets.py
python scripts\build_peace_expression_manifest.py
python scripts\build_task2_normalization_candidates.py
```

## Conclusion

Task 2 has moved from dataset-level screening to record-level cleaning for the available PEaCE subset. The current outputs are usable as a normalization worklist and evaluation subset. Final large-scale training coverage still depends on the PEaCE full release, especially for reaction arrows, charges, states, and richer chemical equation examples.
