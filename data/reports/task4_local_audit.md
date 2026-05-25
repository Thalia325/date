# 任务 4 本地数据清洗与审查报告

目标：清洗出与化学/化工教育相关的数据，支撑教育文档页面结构化和科学教育内容理解两类任务。

本报告由 `scripts/audit_task4_datasets.py` 生成。脚本只读取文件，不删除或改写原始数据。

## 总览

| 数据集 | 角色 | 本地状态 | 图片 | 文档 | 标注/文本 | 初步结论 |
|---|---|---:|---:|---:|---:|---|
| M6Doc | page_layout_structure_core | 缺失 | 0 | 0 | 0 | keep_as_core_layout_dataset |
| ScienceQA | structured_science_question_understanding | 缺失 | 0 | 0 | 0 | keep_as_core_question_understanding_dataset |
| TQA | textbook_context_multimodal_qa | 缺失 | 0 | 0 | 0 | keep_as_auxiliary_textbook_qa_dataset |
| ChineseChemExam | self_collected_chinese_exam_core | 缺失 | 0 | 0 | 0 | create_as_primary_chinese_layout_and_exam_dataset |
| ChineseChemLabHandout | self_collected_lab_handout_core | 缺失 | 0 | 0 | 0 | create_as_primary_chinese_experiment_handout_dataset |

## 统一保留口径

- chemistry subject metadata
- chemical formula or equation
- element, compound, ion, solution, gas, precipitate, oxidation, reduction, acid, base, salt
- laboratory apparatus, reagent, procedure, observation, safety note
- chemical engineering concept such as separation, distillation, reactor, process flow, material balance

## 统一剔除口径

- not related to chemistry, chemical engineering, science experiment, or science education
- missing image/page/question text required by the dataset task
- duplicate page or near-duplicate question after normalization
- unreadable scan, severe occlusion, or broken image/PDF
- annotation cannot be mapped to any target schema field
- license or source does not allow research reuse

## M6Doc

- 目录：`D:\competition\date\data\raw\M6Doc`
- 角色：`page_layout_structure_core`
- 类型：`document_pages`
- 本地状态：缺失
- 文件统计：图片 0，文档 0，标注/文本 0
- 审查结论：
  - 本地未发现数据目录，当前只能完成方案级审查。
- 下一步清洗动作：
  - 把数据放到 data/raw/M6Doc 后重跑本脚本。
  - 筛出 Chemistry + textbook/test paper 页面。
  - 把原生版面类映射到 question_block、figure、table、formula、paragraph 等目标类。
  - 抽样检查题干、选项、答案、实验步骤是否需要二次细标。

## ScienceQA

- 目录：`D:\competition\date\data\raw\ScienceQA`
- 角色：`structured_science_question_understanding`
- 类型：`multimodal_questions`
- 本地状态：缺失
- 文件统计：图片 0，文档 0，标注/文本 0
- 审查结论：
  - 本地未发现数据目录，当前只能完成方案级审查。
- 下一步清洗动作：
  - 把数据放到 data/raw/ScienceQA 后重跑本脚本。
  - 按 metadata 优先、关键词兜底筛选 Chemistry 题目。
  - 输出 question -> choices -> answer -> explanation 的 JSONL。
  - 图文题保留 image_path 与 text context，不能当作文档版面检测数据。

## TQA

- 目录：`D:\competition\date\data\raw\TQA`
- 角色：`textbook_context_multimodal_qa`
- 类型：`textbook_lessons_questions`
- 本地状态：缺失
- 文件统计：图片 0，文档 0，标注/文本 0
- 审查结论：
  - 本地未发现数据目录，当前只能完成方案级审查。
- 下一步清洗动作：
  - 把数据放到 data/raw/TQA 后重跑本脚本。
  - 筛选化学课程、章节、题目和关联图片。
  - 建立 question、supporting_text、supporting_figure 的链接清单。
  - 剔除上下文缺失或答案缺失的孤立样本。

## ChineseChemExam

- 目录：`D:\competition\date\data\raw\ChineseChemExam`
- 角色：`self_collected_chinese_exam_core`
- 类型：`self_collected_pages`
- 本地状态：缺失
- 文件统计：图片 0，文档 0，标注/文本 0
- 审查结论：
  - 本地未发现数据目录，当前只能完成方案级审查。
- 下一步清洗动作：
  - 把数据放到 data/raw/ChineseChemExam 后重跑本脚本。
  - 先完成来源授权、PDF/图片入库、去重，再进入人工标注。
  - 按来源、年级、年份、题型建清单并脱敏。
  - 对 500-2000 页高价值样本标注题号、题干、选项、图表、公式、答案区。
  - 按来源隔离 train/val/test，避免同卷泄漏。

## ChineseChemLabHandout

- 目录：`D:\competition\date\data\raw\ChineseChemLabHandout`
- 角色：`self_collected_lab_handout_core`
- 类型：`self_collected_pages`
- 本地状态：缺失
- 文件统计：图片 0，文档 0，标注/文本 0
- 审查结论：
  - 本地未发现数据目录，当前只能完成方案级审查。
- 下一步清洗动作：
  - 把数据放到 data/raw/ChineseChemLabHandout 后重跑本脚本。
  - 先完成来源授权、PDF/图片入库、去重，再进入人工标注。
  - 按实验名称、课程阶段和来源建清单并去重。
  - 标注实验目的、原理、药品、仪器、步骤、现象、结论、注意事项、报告填写区。
  - 把装置图、表格和安全说明与对应实验步骤建立关系。

## 目标输出

- `data/processed/task4_dataset_review.csv`
- `data/processed/task4_page_layout_regions.jsonl`
- `data/processed/task4_question_choice_answer_explanation.jsonl`
- `data/processed/task4_self_collected_annotation_manifest.csv`
- `future data/processed/task4_experiment_handout.jsonl`

## 当前判断

- M6Doc 是页面结构识别主数据；ScienceQA 和 TQA 是题目理解、图文上下文理解数据。
- 公开数据缺少可直接训练的中文化学实验讲义细粒度解析标注。
- 中文化学试卷与中文实验讲义/报告模板应作为任务 4 的核心自建数据，建议先标注 500-2000 页。
