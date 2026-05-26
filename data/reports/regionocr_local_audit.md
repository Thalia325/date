# RegionOCR 本地数据可用性审计

本报告由 `scripts/audit_regionocr_datasets.py` 生成。脚本只读取文件，不删除或改写原始数据。

## 总览

| 数据集 | 本地目录 | 图片数 | 标注文件数 | 压缩包图片数 | 压缩包标注数 | 一阶段建议 |
|---|---:|---:|---:|---:|---:|---|
| M6Doc | 缺失 | 0 | 0 | 0 | 0 | use_if_train_val_annotations_are_available |
| DECIMER-Segmentation | 缺失 | 0 | 0 | 0 | 0 | use_for_chemical_structure_class |
| Chemical Images Classifier Dataset | 存在 | 0 | 0 | 16000 | 0 | use_as_second_stage_classifier |
| PatCID | 缺失 | 0 | 0 | 0 | 0 | use_benchmark_first_avoid_full_download |

## M6Doc

- 目录：`D:\competition\date\data\raw\M6Doc`
- 角色：`main_layout_detection`
- 本地状态：缺失
- 图片数量：0
- 标注文件数量：0
- 注意事项：
  - 本地未发现数据目录，暂时只能做方案级判断。

## DECIMER-Segmentation

- 目录：`D:\competition\date\data\raw\DECIMER-Segmentation`
- 角色：`chemical_structure_detection`
- 本地状态：缺失
- 图片数量：0
- 标注文件数量：0
- 注意事项：
  - 本地未发现数据目录，暂时只能做方案级判断。

## Chemical Images Classifier Dataset

- 目录：`D:\competition\date\data\raw\ChemicalImagesClassifier`
- 角色：`crop_level_chemical_image_classification`
- 本地状态：存在
- 图片数量：0
- 标注文件数量：0
- 压缩包内可识别图片数量：16000
- 识别到的压缩包：dataset_for_image_classifier.zip
- 分类目录图片数：one_molecule=0, several_molecules=0, reactions=0, other=0
- 压缩包分类图片数：one_molecule=4000, several_molecules=4000, reactions=4000, other=4000
- 注意事项：
  - 图片目前位于压缩包内；如果训练框架不支持 zip 成员路径，需要先解压或实现 zip-aware dataloader。

## PatCID

- 目录：`D:\competition\date\data\raw\PatCID`
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
