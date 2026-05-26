# 任务 2 本地数据可用性审计

目标：化学表达式 OCR，并将识别结果规范化为 mhchem 或结构化 JSON。

此报告由 `scripts/audit_task2_datasets.py` 生成。脚本只读取文件，不会删除或改写原始数据。

## 总览

| 数据集 | 角色 | 本地状态 | 图片数 | 标注文件数 | 建议 |
|---|---|---:|---:|---:|---|
| PEaCE | primary_expression_ocr | 存在 | 319 | 1 | core_dataset_keep_when_labels_and_images_exist |
| DECIMER-Segmentation | structure_region_detection | 缺失 | 0 | 0 | keep_as_auxiliary_structure_detection |
| MolScribe | molecular_image_to_structure | 缺失 | 0 | 0 | keep_as_auxiliary_ocsr |
| PatCID | patent_domain_structure_dataset | 缺失 | 0 | 0 | use_benchmark_first_not_full_dataset |

## PEaCE

- 目录：`D:\competition\date\data\raw\PEaCE`
- 角色：`primary_expression_ocr`
- 本地状态：存在
- 图片数量：319
- 标注文件数量：1
- PEaCE full release 必需文件：final_renders=缺失, train.txt=缺失, dev.txt=缺失, test.txt=缺失, labels.jsonl=缺失
- split/子集行数：train=0, dev=0, test=0, real_world_test=319
- 注意事项：
  - 已发现 PEaCE real-world test set，可用于记录级清洗/评估；full release 仍需单独下载。
  - PEaCE full release 目录不完整，缺少：final_renders, train.txt, dev.txt, test.txt, labels.jsonl
  - 未发现 full release 的 labels.jsonl；若只存在 real-world labels.json，只能生成测试子集 manifest。

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

- PEaCE 是任务 2 的核心数据源；full release 到位后可进入大规模 OCR 训练/评估。
- 当前若只有 PEaCE real-world test set，也可以进入记录级清洗，产出测试/复核用的 LaTeX、mhchem 候选和 reaction JSON 候选。
- DECIMER-Segmentation、MolScribe、PatCID 属于结构图 OCSR 辅助数据，不应直接当作 mhchem 方程式 OCR 标注。
- PEaCE 标签是 LaTeX，不是 native mhchem ground truth；mhchem/JSON 输出必须作为候选并经过规则校验和人工抽样。

## 目标输出

- `latex_ocr`
- `mhchem`
- `reaction_json`
- `smiles`
- `structure_json`
