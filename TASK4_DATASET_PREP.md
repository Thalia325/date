# 任务 4：教育题目与实验讲义结构化解析数据准备

本任务分成两条线：

1. 教育文档页面结构化：题号、题干、选项、图、表、公式、实验步骤、注意事项、答案区域等。
2. 科学教育内容理解：化学题目、实验现象、实验装置、概念解释、图文上下文问答等。

## 数据集结论

| 数据集 | 建议角色 | 结论 |
|---|---|---|
| M6Doc | 页面结构识别核心数据 | 保留。优先筛选 Chemistry + textbook/test paper，用于教材页、试卷页、讲义页区域检测。 |
| ScienceQA | 题目理解核心数据 | 保留。筛选 Chemistry 题目，转成题干、选项、答案、解释、图文上下文 JSON。 |
| TQA | 教材图文问答辅助数据 | 保留。筛选化学相关课程和题目，用于知识点、文本、图片、题目的关系建模。 |
| ChineseChemExam | 中文试卷核心自建数据 | 必建。公开数据不足以覆盖中文化学试卷细粒度题目区域解析。 |
| ChineseChemLabHandout | 中文实验讲义核心自建数据 | 必建。公开数据缺少实验目的、原理、药品、仪器、步骤、现象、结论、注意事项等细标。 |

> 说明：用户材料中明确列出 3 个公开数据集，同时建议自采中文化学试卷、实验讲义、实验报告模板。这里把中文试卷和中文实验讲义/报告模板拆成两个自建核心数据源，因此形成 5 个审查对象。

## 目录约定

请把下载、申请或自采到的数据放到：

```text
data/raw/M6Doc
data/raw/ScienceQA
data/raw/TQA
data/raw/ChineseChemExam
data/raw/ChineseChemLabHandout
```

处理后的清洗结果放到：

```text
data/processed
```

审查报告放到：

```text
data/reports
```

## 本地审查命令

```powershell
python scripts\audit_task4_datasets.py
```

输出：

```text
data/reports/task4_local_audit.md
data/processed/task4_dataset_review.csv
```

## 第一轮清洗 manifest 命令

```powershell
python scripts\build_task4_manifests.py
```

输出：

```text
data/processed/task4_page_layout_regions.jsonl
data/processed/task4_question_choice_answer_explanation.jsonl
data/processed/task4_self_collected_annotation_manifest.csv
```

在当前数据未落盘时，脚本会生成空文件或只有表头的 CSV；等 M6Doc、ScienceQA、TQA 或自采数据放入 `data/raw` 后，重跑即可生成真实清洗清单。

## 统一保留口径

- 与 Chemistry 或 Chemical Engineering 明确相关。
- 含化学式、反应式、元素、化合物、离子、溶液、沉淀、气体、酸碱盐、氧化还原等信号。
- 含实验仪器、试剂、实验步骤、实验现象、注意事项、安全提示、实验报告填写区。
- 含化工教育概念，例如分离、蒸馏、反应器、流程图、物料衡算。
- 图、表、公式、题目区域或讲义段落能映射到任务 4 的目标 schema。

## 统一剔除口径

- 非化学、非化工、非科学实验或非教育场景。
- 缺失题干、选项、答案、页面图像、上下文或关键标注。
- 重复页面、重复题目、同卷不同扫描版本的近重复样本。
- 扫描严重模糊、遮挡、裁切，无法稳定 OCR 或标注。
- 原始标签无法映射到页面结构或教育内容字段。
- 授权不清、不能用于研究复现或内部标注训练的来源。

## 数据集清洗方案

### 1. M6Doc

适合做：

- 化学试卷版面解析。
- 教材页面结构化。
- 讲义页面区域检测。
- 题目区域、图表区域、正文区域分割。

第一轮保留：

- subject 为 Chemistry 的页面。
- document type 为 textbook、test paper 的页面。
- 有可用 bbox、polygon 或 region label 的页面。

第一轮不强求：

- 题干、选项、解析、答案、实验目的、实验步骤、实验现象的细粒度标签。

需要补充：

- 把 M6Doc 原生区域标签映射到 `question_block`、`paragraph`、`figure`、`table`、`formula`、`answer_area` 等目标类。
- 对化学试卷和实验讲义样式做二次细标抽样。

### 2. ScienceQA

适合做：

- 化学教育题目理解。
- 图文结合选择题解析。
- 题目、选项、答案、解释的 JSON schema 设计。

第一轮保留：

- metadata 标注为 Chemistry 的题目。
- 无明确 metadata 时，题干、hint、lecture、solution 中命中化学关键词的题目。
- 有 choices 和 answer 的选择题。

第一轮剔除：

- 非化学题。
- 选项缺失、答案索引非法、图片路径缺失且题目必须依赖图片的样本。

目标字段：

```text
question_id, source_dataset, language, subject, topic_tags,
question_stem, choices, answer, explanation, context.text,
context.image_paths, split
```

### 3. TQA

适合做：

- 教材内容理解。
- 实验讲义中的图文关系建模。
- 题目和知识点关联。
- 图文上下文问答。

第一轮保留：

- 化学相关课程、章节、图文段落和问题。
- 问题能链接到 supporting text 或 supporting figure 的样本。
- 有答案或可评估 target 的样本。

第一轮剔除：

- 上下文缺失的孤立题目。
- 非化学章节。
- 图片、段落或答案文件损坏的样本。

### 4. ChineseChemExam

适合做：

- 中文化学试卷真实版面解析。
- 中文题号、题干、选项、图表、公式、答案区细粒度检测。
- OCR 后题目结构恢复。

建议自建规模：

- 第一阶段 500 页高质量标注。
- 第二阶段扩展到 2,000 页，覆盖不同地区、年份、年级、题型和扫描质量。

必标字段：

```text
page_title, section_title, question_block, question_stem,
choice_block, choice_item, figure, table, formula,
chemical_equation, answer_area, analysis_area
```

### 5. ChineseChemLabHandout

适合做：

- 中文实验讲义、实验报告模板、实验安全说明解析。
- 实验目的、原理、药品、仪器、步骤、现象、结论、注意事项结构化。
- 实验装置图与步骤、现象、问题的关系建模。

建议自建规模：

- 第一阶段 300-500 页，覆盖常见中学和大学基础化学实验。
- 第二阶段扩展到 1,000-2,000 页，加入化工原理和工程实验讲义。

必标字段：

```text
experiment_purpose, experiment_principle, experiment_apparatus,
experiment_reagents, experiment_steps, experiment_observation,
experiment_conclusion, safety_note, figure, table, answer_area
```

## 目标 JSON Schema

### 题目结构

```json
{
  "question_id": "string",
  "source_dataset": "ScienceQA",
  "language": "en",
  "subject": "chemistry",
  "topic_tags": ["acid_base"],
  "question_stem": "string",
  "choices": [
    {
      "label": "A",
      "text": "string"
    }
  ],
  "answer": {
    "label": "A",
    "text": "string"
  },
  "explanation": "string",
  "context": {
    "text": "string",
    "image_paths": ["string"]
  },
  "page_regions": [],
  "split": "train"
}
```

### 实验讲义结构

```json
{
  "document_id": "string",
  "page_id": "string",
  "source_dataset": "ChineseChemLabHandout",
  "language": "zh",
  "experiment_name": "string",
  "curriculum_tags": ["string"],
  "sections": [
    {
      "type": "experiment_steps",
      "order": 1,
      "text": "string",
      "regions": [
        {
          "bbox": [0, 0, 0, 0]
        }
      ]
    }
  ],
  "figures": [
    {
      "type": "apparatus_diagram",
      "caption": "string",
      "bbox": [0, 0, 0, 0]
    }
  ],
  "safety_notes": ["string"],
  "answer_regions": []
}
```

## 当前判断

任务 4 可以做，但公开数据不是“直接可用的中文化学实验讲义解析数据集”。合理路线是：

1. 用 M6Doc 做页面结构识别底座。
2. 用 ScienceQA / TQA 做题目理解和图文上下文理解。
3. 自建中文化学试卷与中文实验讲义/报告模板细粒度标注集，作为最终任务效果的核心数据。
