# RegionOCR 本地数据可用性审计

此报告由 `scripts/audit_regionocr_datasets.py` 生成。脚本只读取文件，不会删除或改写原始数据。

## 总览

| 数据集 | 本地目录 | 图片数 | 标注文件数 | 一阶段建议 |
|---|---:|---:|---:|---|
| M6Doc | 缺失 | 0 | 0 | use_if_train_val_annotations_are_available |
| DECIMER-Segmentation | 缺失 | 0 | 0 | use_for_chemical_structure_class |
| Chemical Images Classifier Dataset | 缺失 | 0 | 0 | use_as_second_stage_classifier |
| PatCID | 缺失 | 0 | 0 | use_benchmark_first_avoid_full_download |

## M6Doc

- 目录：`C:\Users\13711\Documents\date\data\raw\M6Doc`
- 角色：`main_layout_detection`
- 本地状态：缺失
- 图片数量：0
- 标注文件数量：0
- 注意事项：
  - 本地未发现数据目录，暂时只能做方案级判断。

## DECIMER-Segmentation

- 目录：`C:\Users\13711\Documents\date\data\raw\DECIMER-Segmentation`
- 角色：`chemical_structure_detection`
- 本地状态：缺失
- 图片数量：0
- 标注文件数量：0
- 注意事项：
  - 本地未发现数据目录，暂时只能做方案级判断。

## Chemical Images Classifier Dataset

- 目录：`C:\Users\13711\Documents\date\data\raw\ChemicalImagesClassifier`
- 角色：`crop_level_chemical_image_classification`
- 本地状态：缺失
- 图片数量：0
- 标注文件数量：0
- 注意事项：
  - 本地未发现数据目录，暂时只能做方案级判断。

## PatCID

- 目录：`C:\Users\13711\Documents\date\data\raw\PatCID`
- 角色：`patent_domain_chemical_structure_detection`
- 本地状态：缺失
- 图片数量：0
- 标注文件数量：0
- 注意事项：
  - 本地未发现数据目录，暂时只能做方案级判断。

## 目标标签

- `title`
- `paragraph`
- `table`
- `figure`
- `figure_caption`
- `table_caption`
- `question`
- `answer`
- `chemical_structure`
- `chemical_structure_single`
- `chemical_structure_multiple`
- `reaction_scheme`
- `chemical_equation`
- `experiment_step`
- `non_chemical_image`
- `markush_structure`
