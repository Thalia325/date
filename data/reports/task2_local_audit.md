# 任务 2 本地数据可用性审计

目标：化学表达式 OCR，并将识别结果规范化为 mhchem 或结构化 JSON。

此报告由 `scripts/audit_task2_datasets.py` 生成。脚本只读取文件，不会删除或改写原始数据。

## 总览

| 数据集 | 角色 | 本地状态 | 图片数 | 标注文件数 | 建议 |
|---|---|---:|---:|---:|---|
| PEaCE | primary_expression_ocr | 缺失 | 0 | 0 | core_dataset_keep_when_labels_and_images_exist |
| DECIMER-Segmentation | structure_region_detection | 缺失 | 0 | 0 | keep_as_auxiliary_structure_detection |
| MolScribe | molecular_image_to_structure | 缺失 | 0 | 0 | keep_as_auxiliary_ocsr |
| PatCID | patent_domain_structure_dataset | 缺失 | 0 | 0 | use_benchmark_first_not_full_dataset |

## PEaCE

- 目录：`D:\competition\date\data\raw\PEaCE`
- 角色：`primary_expression_ocr`
- 本地状态：缺失
- 图片数量：0
- 标注文件数量：0
- 注意事项：
  - 本地未发现数据目录，当前只能做方案级可用性判断。

## DECIMER-Segmentation

- 目录：`D:\competition\date\data\raw\DECIMER-Segmentation`
- 角色：`structure_region_detection`
- 本地状态：缺失
- 图片数量：0
- 标注文件数量：0
- 注意事项：
  - 本地未发现数据目录，当前只能做方案级可用性判断。

## MolScribe

- 目录：`D:\competition\date\data\raw\MolScribe`
- 角色：`molecular_image_to_structure`
- 本地状态：缺失
- 图片数量：0
- 标注文件数量：0
- 注意事项：
  - 本地未发现数据目录，当前只能做方案级可用性判断。

## PatCID

- 目录：`D:\competition\date\data\raw\PatCID`
- 角色：`patent_domain_structure_dataset`
- 本地状态：缺失
- 图片数量：0
- 标注文件数量：0
- 注意事项：
  - 本地未发现数据目录，当前只能做方案级可用性判断。

## 清洗结论

- PEaCE 是任务 2 的核心数据源；只有当 `final_renders/`、`labels.jsonl` 和 split 文件齐全时，才可进入 OCR 训练/评估。
- DECIMER-Segmentation、MolScribe、PatCID 属于结构图 OCSR 辅助数据，适合输出 SMILES、molfile 或结构 JSON，不应直接当作 mhchem 方程式 OCR 标注。
- 当前公开数据链条缺少大规模 native mhchem ground truth；建议从 PEaCE 的 LaTeX 标签生成候选 mhchem，再做规则校验和人工抽样。

## 目标输出

- `latex_ocr`
- `mhchem`
- `reaction_json`
- `smiles`
- `structure_json`
