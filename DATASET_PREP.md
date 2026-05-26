# RegionOCR 数据准备流程

本项目当前目标是为“化学文档区域识别与分类”准备数据，而不是把候选数据集无差别混在一起。第一阶段优先确认每个数据集能否支持页面级区域检测、化学结构检测或 crop 二级分类。

## 目录约定

下载或申请到的数据放到：

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

## 推荐落地顺序

1. M6Doc：优先申请完整 train/val 数据，用作整页版面检测主数据；第一轮筛选 Chemistry + textbook/test paper/scientific article。
2. Chemical Images Classifier Dataset：保留 Zenodo 的 `dataset_for_image_classifier.zip`，用作化学图片 crop 二级分类。
3. DECIMER-Segmentation：用于补强 `chemical_structure` 区域；如果只有模型没有标注，可先对 M6Doc 页面或图像推理生成候选框，再抽样质检。
4. PatCID：先用 benchmark 或小样本，不建议第一轮下载全量并直接混入主训练集。

## 本地审计

```powershell
python scripts\audit_regionocr_datasets.py
```

输出：

```text
data/reports/regionocr_local_audit.md
```

## 任务一准备度检查

```powershell
python scripts\check_regionocr_task1_readiness.py
```

输出：

```text
data/reports/regionocr_task1_readiness.md
```

该报告会明确四块能力是否可用：

- 整页版面检测。
- 化学结构区域检测。
- 化学图片 crop 二级分类。
- 页面级 RegionOCR JSONL。

## Chemical Images 分类数据 manifest

本项目支持不解压 `dataset_for_image_classifier.zip` 直接生成 manifest：

```powershell
python scripts\build_chemical_classifier_manifest.py
```

输出：

```text
data/processed/chemical_classifier_manifest.csv
```

源标签映射：

```text
one_molecule       -> chemical_structure_single
several_molecules  -> chemical_structure_multiple
reactions          -> reaction_scheme
other/rest         -> non_chemical_image
```

注意：该 manifest 只适合检测后 crop 的二级分类，不适合作整页 bbox 检测数据。

## COCO 标注转换

如果 M6Doc、DECIMER-Segmentation 或 PatCID benchmark 已整理为 COCO JSON，可先转换为 RegionOCR COCO：

```powershell
python scripts\convert_coco_to_regionocr.py `
  --input-json data\raw\M6Doc\annotations\instances_train2017.json `
  --dataset-name M6Doc `
  --output-json data\processed\m6doc_regionocr_coco.json
```

也可以直接转换为任务一目标 JSONL：

```powershell
python scripts\build_regionocr_regions_from_coco.py `
  --input-json data\raw\M6Doc\annotations\instances_train2017.json `
  --dataset-name M6Doc `
  --image-root data\raw\M6Doc\train2017 `
  --output-jsonl data\processed\m6doc_regionocr_regions.jsonl
```

输出 JSONL 每行是一个页面或图片：

```json
{
  "source_dataset": "M6Doc",
  "image_ref": "page_image_path",
  "width": 1000,
  "height": 1400,
  "regions": [
    {
      "bbox": [10.0, 20.0, 200.0, 80.0],
      "type": "paragraph",
      "score": 1.0,
      "text_ref": null,
      "image_ref": "page_image_path"
    }
  ]
}
```

## 第一轮保留规则

保留：

- M6Doc 中与 Chemistry、textbook、test paper、scientific article 相关的页面。
- DECIMER-Segmentation 的分子结构图区域标注，或经过抽样质检的推理候选框。
- Chemical Images Classifier Dataset 的四类裁剪图。
- PatCID benchmark 中人工或高可信标注。

暂不保留：

- M6Doc 中无关学科和无关文档类型。
- Chemical Images Classifier Dataset 中无法对应到整页坐标的图片，不把它直接当检测标注。
- PatCID 全量弱监督数据，除非后续专门做专利域扩展。

## 完成判定

任务一可以宣称“完整清洗完成”的最低条件：

- M6Doc 或等价整页数据已落地，并能生成页面级 `regions`。
- DECIMER/PatCID 或等价结构检测数据已落地，能补强 `chemical_structure`。
- ChemIC manifest 可复跑，四类样本数和标签映射稳定。
- `data/reports/regionocr_task1_readiness.md` 中没有关键能力为“缺失”。
