# 任务一 RegionOCR 数据清洗审查结论

审查日期：2026-05-26

任务定位：化学文档区域识别与分类，目标输出为
`regions:[{bbox,type,score,text_ref,image_ref}]`，覆盖标题、正文、表格、图、图注、表注、题目、答案、化学结构、反应图等区域。

## 总体结论

当前任务一只能认定为“部分完成”，还不能认定为完整清洗完成。

本地已经具备：

- RegionOCR 数据筛选方案、标签映射配置、审计脚本和转换脚本。
- Chemical Images Classifier / ChemIC 原始压缩包。
- ChemIC crop 分类 manifest，已生成 16,000 行。

本地仍缺：

- `data/raw/M6Doc`：整页文档版面检测主数据。
- `data/raw/DECIMER-Segmentation`：化学结构区域检测或推理补强数据。
- 页面级 RegionOCR JSONL：`data/processed/m6doc_regionocr_regions.jsonl`、`data/processed/decimer_regionocr_regions.jsonl` 等。

因此，当前项目已经能支持“化学图片 crop 二级分类”，但还不能完整产出页面级
`regions:[{bbox,type,score,text_ref,image_ref}]` 训练/评测数据。

## 本地数据状态

| 数据集 | 本地是否包含 | 当前可识别数据量 | 清洗状态 | 任务一适配判断 |
|---|---:|---:|---|---|
| M6Doc | 否 | 0 图片，0 标注 | 未开始 | 高适配；缺 train/val 图片与区域标注 |
| DECIMER-Segmentation | 否 | 0 图片，0 标注 | 未开始 | 高适配；缺化学结构检测数据或模型推理产物 |
| Chemical Images Classifier / ChemIC | 是 | zip 内 16,000 张已分类图片 | manifest 已生成 | 中高适配；只能做 crop 分类，不能做整页 bbox 检测 |
| PatCID | 否 | 0 图片，0 标注 | 未开始 | 可作为专利结构区域补充，不建议作为第一阶段主数据 |

## 已修复的问题

1. ChemIC 压缩包内负类目录实际名称为 `rest`，原规则只期望 `other`。
2. 原审计脚本只扫描解压后的图片目录，无法识别 zip 内部样本。
3. 原 manifest 脚本不支持直接读取 zip，导致 `chemical_classifier_manifest.csv` 只有表头。
4. 任务一审查报告和审计报告存在中文乱码，已重写为 UTF-8 可读文本。
5. 已新增 COCO 到 RegionOCR JSONL 的转换入口，方便 M6Doc/DECIMER 标注落地后直接生成页面级 `regions`。

## 已生成或更新的产物

- `config/regionocr_dataset_rules.json`
  - 补充 `other -> rest` 别名。
  - 保留 RegionOCR 目标标签和 M6Doc / DECIMER / ChemIC / PatCID 标签映射。
- `scripts/audit_regionocr_datasets.py`
  - 支持统计 zip 内图片和标注。
  - 输出可读中文审计报告。
- `scripts/build_chemical_classifier_manifest.py`
  - 支持不解压 zip 直接生成 manifest。
- `scripts/build_regionocr_regions_from_coco.py`
  - 新增 COCO 标注到页面级 RegionOCR JSONL 的转换能力。
- `scripts/check_regionocr_task1_readiness.py`
  - 新增任务一准备度报告，明确哪些能力已可用、哪些仍缺数据。
- `data/reports/regionocr_local_audit.md`
  - 重新审计后识别到 ChemIC zip 内 16,000 张已分类图片。
- `data/reports/regionocr_task1_readiness.md`
  - 新增任务一准备度报告。
- `data/processed/chemical_classifier_manifest.csv`
  - 已生成 16,000 行，四类各 4,000 条。

## ChemIC manifest 核验

输出文件：`data/processed/chemical_classifier_manifest.csv`

总行数：16,000

| source_label | 数量 | target_label |
|---|---:|---|
| one_molecule | 4,000 | chemical_structure_single |
| several_molecules | 4,000 | chemical_structure_multiple |
| reactions | 4,000 | reaction_scheme |
| other/rest | 4,000 | non_chemical_image |

划分结果以脚本当前稳定哈希为准，约为 train 80%、val 10%、test 10%。

说明：manifest 使用 `zip_path!inner_path` 格式引用图片，保留原始压缩包不变。如果后续训练框架不支持直接读取 zip 成员路径，需要先解压，或增加 dataloader 读取逻辑。

## 页面级输出适配度

ChemIC 只能补足 crop 的二级类型分类能力，不能直接生成整页 `bbox`。

当前可用格式：

```json
{
  "image_path": "zip_path!inner_image_path",
  "target_label": "chemical_structure_single | chemical_structure_multiple | reaction_scheme | non_chemical_image"
}
```

完整任务一需要的格式：

```json
{
  "source_dataset": "M6Doc",
  "image_ref": "page_image_path",
  "regions": [
    {
      "bbox": [0, 0, 100, 80],
      "type": "chemical_structure",
      "score": 1.0,
      "text_ref": null,
      "image_ref": "page_image_path"
    }
  ]
}
```

M6Doc 或 DECIMER 标注整理为 COCO 后，可运行：

```powershell
python scripts\build_regionocr_regions_from_coco.py `
  --input-json data\raw\M6Doc\annotations\instances_train2017.json `
  --dataset-name M6Doc `
  --image-root data\raw\M6Doc\train2017 `
  --output-jsonl data\processed\m6doc_regionocr_regions.jsonl
```

## 下一步

1. 申请并落地 M6Doc train/val，优先保留 Chemistry + textbook/test paper/scientific article。
2. 落地 DECIMER-Segmentation 模型、标注或推理输出，用于补强 `chemical_structure` 区域。
3. 将 M6Doc/DECIMER 标注统一转为 COCO 或直接转为 RegionOCR JSONL。
4. 抽样 50-100 页人工核验标题、正文、表格、题目、答案、图注、表注、公式和化学结构区域。
5. 不要把 ChemIC 当作整页检测数据使用；它只适合作检测后 crop 的二级分类器。
