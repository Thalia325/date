# 任务 4 标注指南：化学教育题目与实验讲义

本指南用于中文化学试卷、中文化学实验讲义和实验报告模板的人工标注。M6Doc、ScienceQA、SceMQA 可用于预训练或辅助理解，但中文实验讲义的细粒度结构仍需要自建标注。

## 标注目标

一页文档同时保留两层信息：

1. 页面结构：区域在页面上是什么，例如题目、正文、选项、图、表、公式、答案区。
2. 教育语义：内容在化学教学中是什么，例如实验目的、实验步骤、实验现象、实验装置、概念解释。

## 页面级元数据

每页至少记录：

```text
document_id, page_id, source, language, grade_or_stage,
document_type, subject, chemistry_topic, source_year,
license_status, split
```

推荐 `document_type`：

```text
exam, textbook, handout, lab_report_template, safety_sheet, worksheet
```

## 通用区域标签

| 标签 | 含义 | 标注口径 |
|---|---|---|
| `page_title` | 页面或文档主标题 | 如“高一化学期末试卷”“酸碱中和滴定实验”。 |
| `section_title` | 小节标题 | 如“一、选择题”“实验步骤”。 |
| `paragraph` | 普通正文 | 不属于题目、选项、图表或实验专门字段的正文。 |
| `figure` | 图片或示意图 | 实验装置图、曲线图、结构图、流程图等。 |
| `figure_caption` | 图题/图注 | 与最近的 `figure` 关联。 |
| `table` | 表格 | 实验记录表、数据表、选项表。 |
| `table_caption` | 表题/表注 | 与最近的 `table` 关联。 |
| `formula` | 数学公式或普通公式 | 如计算公式、比例关系。 |
| `chemical_equation` | 化学式、离子方程式、反应式 | 优先从 `formula` 中单独拆出。 |

## 题目标注

| 标签 | 含义 | 标注口径 |
|---|---|---|
| `question_block` | 完整题目区域 | 含题号、题干、选项、图表、答案区时可框整个大题。 |
| `question_stem` | 题干 | 不含选项；跨行或跨栏时合并为同一题干区域。 |
| `choice_block` | 选项整体区域 | 选项密集排版时先标整体区域。 |
| `choice_item` | 单个选项 | A/B/C/D 分开标，保留 label 和 text。 |
| `answer_area` | 学生填写或标准答案区域 | 空格、横线、括号、答题框、解析后的答案区域。 |
| `analysis_area` | 解析/解答过程 | 标准解析、解题步骤、原因说明。 |

题号单独成块时，可并入 `question_stem` 或在属性中记录 `question_number`，不强制单独设标签。

## 实验讲义标签

| 标签 | 含义 | 标注口径 |
|---|---|---|
| `experiment_purpose` | 实验目的 | 如“掌握酸碱中和滴定原理”。 |
| `experiment_principle` | 实验原理 | 反应原理、平衡原理、定量关系。 |
| `experiment_apparatus` | 实验仪器/装置 | 文字列表或装置说明；装置图仍标 `figure`。 |
| `experiment_reagents` | 药品/试剂 | 药品名称、浓度、规格。 |
| `experiment_steps` | 实验步骤 | 按步骤编号或操作顺序标注，可保留 order。 |
| `experiment_observation` | 实验现象 | 颜色变化、气体、沉淀、温度变化等。 |
| `experiment_conclusion` | 实验结论 | 结论、结果分析、误差分析。 |
| `safety_note` | 注意事项/安全提示 | 防护、废液处理、危险试剂提醒。 |

同一段同时包含“步骤”和“注意事项”时，优先按主要功能标注；安全风险句可额外作为 `safety_note` 子区域。

## 关系标注

建议补充区域关系：

```text
question_block -> contains -> question_stem
question_block -> contains -> choice_item
question_block -> refers_to -> figure/table/chemical_equation
experiment_steps -> uses -> experiment_reagents
experiment_steps -> uses -> experiment_apparatus
experiment_steps -> produces -> experiment_observation
figure -> captioned_by -> figure_caption
table -> captioned_by -> table_caption
```

## 质量控制

每批数据至少抽检 10%。重点检查：

- 化学无关页面是否误保留。
- 同一试卷或同一模板是否重复进入不同 split。
- 题干和选项是否切分过粗或过细。
- 反应式、离子方程式、实验装置图是否漏标。
- 实验步骤和实验现象是否混标。
- 答案区和解析区是否混标。
- 图片、PDF 页码和 JSON `page_id` 是否能稳定追溯。

## 推荐切分

- `train`：80%，用于训练。
- `val`：10%，用于调参和规则检查。
- `test`：10%，用于最终评估。

同一份试卷、同一套讲义、同一学校同一年份模板必须进入同一个 split，避免泄漏。
