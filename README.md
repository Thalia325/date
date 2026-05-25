# date

RegionOCR 数据准备与筛选项目。

当前任务方向：化学文档区域识别与分类，包括正文、标题、表格、化学方程式、分子结构图、反应路线图、实验步骤、题目区域、答案区域、图注、表注等区域。

## 当前内容

- `RegionOCR_dataset_screening.md`：M6Doc、DECIMER-Segmentation、Chemical Images Classifier Dataset、PatCID 的可用性筛选结论。
- `DATASET_PREP.md`：数据下载、目录放置、清洗与转换流程。
- `TASK2_DATASET_PREP.md`：任务 2 化学表达式 OCR 与 mhchem/JSON 规范化数据准备。
- `TASK2_NEXT_STEPS.md`：任务 2 从下载、审计、manifest 到规范化候选的执行清单。
- `TASK4_DATASET_PREP.md`：任务 4 教育题目与实验讲义结构化解析的数据清洗、审查和 schema 设计。
- `TASK4_ANNOTATION_GUIDE.md`：任务 4 中文化学试卷与实验讲义的人工标注口径。
- `config/`：RegionOCR 标签映射和数据集规则。
- `scripts/`：数据审计、manifest 构建、COCO 转换脚本。
- `data/`：原始数据、处理后数据和审计报告目录。

## 数据放置

推荐把数据放在：

```text
data/raw/M6Doc
data/raw/DECIMER-Segmentation
data/raw/ChemicalImagesClassifier
data/raw/PEaCE
data/raw/MolScribe
data/raw/PatCID
data/raw/ScienceQA
data/raw/TQA
data/raw/ChineseChemExam
data/raw/ChineseChemLabHandout
```

处理结果放在：

```text
data/processed
```

## GitHub 数据说明

本仓库已配置 Git LFS，用于跟踪常见图片、PDF、压缩包和表格数据文件。

注意：PatCID 全量数据规模极大，不建议直接推送到 GitHub。优先提交脚本、manifest、清洗后的标注、小规模 benchmark 或下载说明。

## 常用命令

```powershell
python scripts\audit_regionocr_datasets.py
python scripts\build_chemical_classifier_manifest.py
python scripts\audit_task2_datasets.py
python scripts\build_peace_expression_manifest.py
python scripts\build_task2_normalization_candidates.py
python scripts\audit_task4_datasets.py
python scripts\build_task4_manifests.py
```
