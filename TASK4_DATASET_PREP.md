# 任务 4：教育题目与实验讲义结构化解析数据准备

任务 4 分成两条线：

1. 教育文档页面结构化：题号、题干、选项、图、表、公式、实验步骤、注意事项、答案区域等。
2. 科学教育内容理解：化学题目、实验现象、实验装置、概念解释、图文上下文问答等。

## 数据集结论

| 数据集 | 建议角色 | 当前口径 |
|---|---|---|
| M6Doc | 页面结构识别核心数据 | 保留，但完整训练/验证集需要向官方申请；优先筛选 Chemistry + textbook/test paper。 |
| ScienceQA | 题目理解核心数据 | 保留；筛选 chemistry 题目，转换为题干、选项、答案、解释、图文上下文 JSONL。 |
| SceMQA | 多模态科学题目理解补充数据 | 保留；使用 chemistry 多选题和图片，解析 A/B/C/D、答案、解释、知识点。 |
| ChineseChemExam | 中文试卷自建核心数据 | 必建；公开数据不足以覆盖中文化学试卷细粒度版面解析。 |
| ChineseChemLabHandout | 中文实验讲义自建核心数据 | 必建；公开数据缺少实验目的、原理、药品、仪器、步骤、现象、结论、注意事项等细标。 |

## 目录约定

```text
data/raw/M6Doc
data/raw/ScienceQA
data/raw/SceMQA
data/raw/ChineseChemExam
data/raw/ChineseChemLabHandout
```

处理后的结果放在：

```text
data/processed
data/reports
```

## 自动补公开数据

可直接下载的公开部分：

```powershell
python scripts\download_task4_public_datasets.py
```

默认行为：

- 下载 ScienceQA 的 `problems.json`、`pid_splits.json`、`captions.json`。
- 下载 SceMQA chemistry JSON/JSONL 和 Chemistry 图片。
- 下载 M6Doc 官方 README 与申请表；完整 train/val 数据需获批后手动放入约定目录。

如果要补全 ScienceQA 图片，额外加参数：

```powershell
python scripts\download_task4_public_datasets.py --scienceqa-images
```

ScienceQA 图片约 1GB，默认不强制下载；未下载图片时，清洗脚本仍会用 `captions.json` 保留图像文本上下文。

## 审查与清洗命令

```powershell
python scripts\audit_task4_datasets.py
python scripts\build_task4_manifests.py
```

输出：

```text
data/reports/task4_local_audit.md
data/reports/task4_public_dataset_sources.md
data/processed/task4_dataset_review.csv
data/processed/task4_page_layout_regions.jsonl
data/processed/task4_question_choice_answer_explanation.jsonl
data/processed/task4_self_collected_annotation_manifest.csv
```

## 清洗口径

保留：

- Chemistry 或 Chemical Engineering 明确相关。
- 含化学式、反应式、元素、化合物、离子、溶液、沉淀、气体、酸碱盐、氧化还原等信号。
- 含实验仪器、试剂、步骤、现象、注意事项、安全提示、实验报告填写区。
- 图、表、公式、题目区域或讲义段落能映射到任务 4 schema。

剔除：

- 非化学、非化工、非科学实验或非教育场景。
- 缺失题干、选项、答案、页面图像、上下文或关键标注。
- 重复页面、重复题目、同卷不同扫描版本的近重复样本。
- 授权不清或不能用于研究复现/内部标注训练的来源。

## 当前判断

ScienceQA 与 SceMQA 已能作为题目理解数据自动转成 JSONL；M6Doc 受官方申请限制，在获批前不能声称完整落盘。中文化学试卷与中文实验讲义仍是任务最终效果的核心自建数据，需要单独完成授权、去重、脱敏和人工标注。
