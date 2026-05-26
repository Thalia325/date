# 任务一：化学教育题目与实验讲义结构化解析数据审查

审查日期：2026-05-25

## 审查目标

本次审查聚焦“教育题目与实验讲义结构化解析”，目标是确认项目中是否已包含可用于化学/化工教育场景的数据，并判断数据是否正确、是否清洗完全。目标解析对象包括：

- 化学教材、试卷、笔记、实验讲义中的题干、选项、图表、公式、实验步骤、答案、解析、知识点。
- M6Doc：用于教材、试卷、讲义页面版面切分。
- ScienceQA：用于科学题目中的题干、图像、选项、答案、lecture、explanation 建模。
- SceMQA：用于高中到大学入学水平的多模态科学问答，筛选化学题目并保留知识点和详细解释。

## 本地包含情况

| 数据集 | 项目是否已落盘 | 当前可识别数据量 | 数据正确性 | 清洗状态 | 结论 |
|---|---:|---:|---|---|---|
| M6Doc | 否 | 0 图像，0 文档，0 标注 | 无法校验 | 未开始 | 适合作为页面版面切分主数据，但当前缺失 |
| ScienceQA | 否 | 0 图像，0 文档，0 标注 | 无法校验 | 未开始 | 适合作为题目结构、图文问答、答案解析主数据，但当前缺失 |
| SceMQA | 否 | 0 图像，0 文档，0 标注 | 无法校验 | 未开始 | 适合作为题目结构、知识点和详细解释建模数据，但当前缺失 |
| ChineseChemExam | 否 | 0 图像，0 文档，0 标注 | 无法校验 | 未开始 | 中文化学试卷需要自建，当前缺失 |
| ChineseChemLabHandout | 否 | 0 图像，0 文档，0 标注 | 无法校验 | 未开始 | 中文实验讲义/报告模板需要自建，当前缺失 |

补充说明：`data/raw` 当前只有 `ChemicalImagesClassifier`，它更适合化学结构图片二级分类，不适合直接完成教材、试卷、实验讲义的整页结构化解析。

## 已修正的问题

1. 将任务 4 配置、脚本和说明中的第三个公开数据集从 `TQA` 修正为用户指定的 `SceMQA`。
2. 审查脚本现在会把 SceMQA 作为多模态科学题目、知识点和详细解释建模数据源检查。
3. manifest 构建脚本现在会从 SceMQA 读取题干、选项、答案、解析、图片引用和知识点字段，并输出到统一的问答 JSONL schema。
4. README 与原始数据目录说明已同步推荐 `data/raw/SceMQA`。

## 数据是否正确

当前无法判定 M6Doc、ScienceQA、SceMQA 原始样本是否正确，因为三个数据集均未落盘。项目只能完成方案级审查，不能完成样本级正确性校验。

样本级校验需要至少检查：

- M6Doc：页面图片、区域标注、bbox/polygon、subject、document type 是否完整；是否能筛出 Chemistry + textbook/test paper/handout 页面。
- ScienceQA：question、choices、answer、lecture、explanation、image、split 是否完整；answer 索引是否能映射到选项。
- SceMQA：题干、选项、答案、知识点、详细解释、图像引用是否完整；是否覆盖化学/化工主题。

## 数据是否清洗完全

结论：未清洗完全。

原因是目标数据尚未进入 `data/raw`，因此当前输出文件只能证明 schema 和流程已准备好，不能证明真实数据已清洗完成：

- `data/processed/task4_dataset_review.csv`：可生成审查清单，但所有目标数据集均为 missing。
- `data/processed/task4_page_layout_regions.jsonl`：当前为空，等待 M6Doc 落盘后生成页面区域数据。
- `data/processed/task4_question_choice_answer_explanation.jsonl`：当前为空，等待 ScienceQA/SceMQA 落盘后生成题目结构数据。
- `data/processed/task4_self_collected_annotation_manifest.csv`：当前只有表头，等待中文试卷和实验讲义自采数据落盘。

## 建议清洗路线

1. 将 M6Doc 放入 `data/raw/M6Doc`，优先筛选 Chemistry、textbook、test paper、handout 类页面，并映射到 `question_block`、`question_stem`、`choice_item`、`figure`、`table`、`formula`、`answer_area` 等标签。
2. 将 ScienceQA 放入 `data/raw/ScienceQA`，筛选 Chemistry topic，保留题干、选项、答案、lecture、explanation、图片路径和 split。
3. 将 SceMQA 放入 `data/raw/SceMQA`，筛选化学/化工相关题目，保留知识点和详细解释，剔除选项缺失、答案非法、图片损坏样本。
4. 自建 `ChineseChemExam` 与 `ChineseChemLabHandout`，第一阶段建议分别标注 500 页和 300-500 页，覆盖中文化学试卷和实验讲义真实版面。
5. 数据落盘后运行：

```powershell
python scripts\audit_task4_datasets.py
python scripts\build_task4_manifests.py
```

## 总体结论

任务方向正确，schema 和流程已具备基础；但本地缺少 M6Doc、ScienceQA、SceMQA 以及中文自采试卷/实验讲义，因此目前不能认为数据已经正确或清洗完全。下一步必须先补齐原始数据，再进行样本级清洗、去重、字段完整性校验和人工抽检。
