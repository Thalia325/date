# 任务一 RegionOCR 准备度报告

总体状态：1/4 项可用。

当前还不能宣称任务一完整清洗完成；缺口集中在：整页版面检测、化学结构区域检测、RegionOCR regions JSONL。

| 能力 | 状态 | 本地证据 | 下一步 |
|---|---|---|---|
| 整页版面检测 | 缺失 | M6Doc images=0, annotations=0 | 申请并落地 M6Doc train/val，至少包含 annotations 和 train2017/val2017。 |
| 化学结构区域检测 | 缺失 | DECIMER images=0, annotations=0, models=0 | 落地 DECIMER-Segmentation 模型或可转换标注，用于补强 chemical_structure 区域。 |
| 化学图片 crop 二级分类 | 可用 | chemical_classifier_manifest rows=16000 | 作为检测后 crop 的二级分类数据，不作为整页 bbox 数据。 |
| RegionOCR regions JSONL | 缺失 | region records=0 | M6Doc/DECIMER 标注到位后运行 build_regionocr_regions_from_coco.py。 |

## 推荐复跑命令

```powershell
python scripts\audit_regionocr_datasets.py
python scripts\build_chemical_classifier_manifest.py
python scripts\check_regionocr_task1_readiness.py
```

M6Doc 或 DECIMER 标注转成 COCO 后，继续运行：

```powershell
python scripts\build_regionocr_regions_from_coco.py `
  --input-json data\raw\M6Doc\annotations\instances_train2017.json `
  --dataset-name M6Doc `
  --image-root data\raw\M6Doc\train2017 `
  --output-jsonl data\processed\m6doc_regionocr_regions.jsonl
```
