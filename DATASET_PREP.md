# RegionOCR 数据准备流程

本项目当前目标不是立刻把四个数据集全部混在一起，而是先判断它们是否能服务“化学文档区域识别与分类”。

## 目录约定

下载或申请到的数据请放到：

```text
data/raw/M6Doc
data/raw/DECIMER-Segmentation
data/raw/ChemicalImagesClassifier
data/raw/PatCID
```

处理后的筛选结果放到：

```text
data/processed
```

审计报告放到：

```text
data/reports
```

## 推荐下载顺序

1. M6Doc：先申请完整 train/val 数据，优先筛 Chemistry 的 textbook、test paper、scientific article。
2. Chemical Images Classifier Dataset：下载 Zenodo 的 `dataset_for_image_classifier.zip`，用于化学图片 crop 分类。
3. DECIMER-Segmentation：用于补强 chemical structure detection。
4. PatCID：先只用 benchmark 或小样本，不建议下载全量后直接训练。

## 本地审计命令

```powershell
python scripts\audit_regionocr_datasets.py
```

运行后会生成：

```text
data/reports/regionocr_local_audit.md
```

## Chemical Images 分类数据 manifest

下载并解压到 `data/raw/ChemicalImagesClassifier` 后运行：

```powershell
python scripts\build_chemical_classifier_manifest.py
```

输出：

```text
data/processed/chemical_classifier_manifest.csv
```

该 manifest 会把四个源标签映射成：

```text
one_molecule       -> chemical_structure_single
several_molecules  -> chemical_structure_multiple
reactions          -> reaction_scheme
other              -> non_chemical_image
```

## COCO 标注转换

如果 M6Doc、DECIMER-Segmentation 或 PatCID benchmark 已整理为 COCO JSON，可以运行：

```powershell
python scripts\convert_coco_to_regionocr.py `
  --input-json data\raw\M6Doc\annotations.json `
  --dataset-name M6Doc `
  --output-json data\processed\m6doc_regionocr.json
```

脚本会根据 `config/regionocr_dataset_rules.json` 的映射保留可用类别，并丢弃未映射标注。

## 清洗判断

第一轮只保留：

- M6Doc 中与 Chemistry、textbook、test paper、scientific article 相关的页面。
- DECIMER-Segmentation 的分子结构图区域标注。
- Chemical Images Classifier Dataset 的四类裁剪图。
- PatCID benchmark 中的人工或高可信标注。

第一轮暂不保留：

- M6Doc 中无关学科和无关文档类型。
- Chemical Images Classifier Dataset 中无法对应到整页坐标的图片，不能直接作为检测标注。
- PatCID 全量弱监督数据，除非后续专门做专利域扩展。

## 输出格式建议

最后统一转成 COCO 风格：

```json
{
  "images": [],
  "annotations": [],
  "categories": []
}
```

目标类别以 `config/regionocr_dataset_rules.json` 里的 `target_labels` 为准。
