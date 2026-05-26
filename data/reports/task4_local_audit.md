# 任务 4 本地数据清洗与审查报告

目标：清洗出与化学/化工教育相关的数据，支撑教育文档页面结构化和科学教育内容理解。

本报告由 `scripts/audit_task4_datasets.py` 生成；脚本只读文件，不删除或改写原始数据。

## 总览

| 数据集 | 角色 | 本地状态 | 图片 | 文档 | 标注/文本 | 初步结论 |
|---|---|---:|---:|---:|---:|---|
| M6Doc | page_layout_structure_core | access_required_or_incomplete | 0 | 1 | 1 | keep_as_core_layout_dataset |
| ScienceQA | structured_science_question_understanding | present | 16100 | 0 | 3 | keep_as_core_question_understanding_dataset |
| SceMQA | multimodal_science_question_knowledge_understanding | present | 218 | 0 | 5 | keep_as_core_multimodal_science_qa_dataset |
| ChineseChemExam | self_collected_chinese_exam_core | missing | 0 | 0 | 0 | create_as_primary_chinese_layout_and_exam_dataset |
| ChineseChemLabHandout | self_collected_lab_handout_core | missing | 0 | 0 | 0 | create_as_primary_chinese_experiment_handout_dataset |

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
- 本地状态：access_required_or_incomplete
- 文件统计：图片 0，文档 1，标注/文本 1
- 审查结论：
  - 已发现 M6Doc 目录，但未发现官方 annotations 目录；完整数据仍需申请或解压落盘。
- 下一步清洗动作：
  - 完整训练/验证集需要按官方 README 提交申请并获得下载链接与解压密码。
  - 取得数据后放入 data/raw/M6Doc/annotations、train2017、val2017、test2017。
  - 优先筛出 Chemistry + textbook/test paper 页面，并映射原生 layout label 到任务 4 标签。
  - 数据更新后重跑：python scripts\audit_task4_datasets.py 和 python scripts\build_task4_manifests.py。

## ScienceQA

- 目录：`D:\competition\date\data\raw\ScienceQA`
- 角色：`structured_science_question_understanding`
- 类型：`multimodal_questions`
- 本地状态：present
- 文件统计：图片 16100，文档 0，标注/文本 3
- 审查结论：
  - 本地文件结构未发现明显问题，可进入任务 4 清洗转换。
- 下一步清洗动作：
  - 保留 chemistry 题目，规范化 question、choices、answer、lecture、solution、caption、image_path。
  - 图文题可使用本地图片；若未下载图片，至少保留 captions.json 作为图像文本上下文。
  - 数据更新后重跑：python scripts\audit_task4_datasets.py 和 python scripts\build_task4_manifests.py。

## SceMQA

- 目录：`D:\competition\date\data\raw\SceMQA`
- 角色：`multimodal_science_question_knowledge_understanding`
- 类型：`multimodal_science_questions`
- 本地状态：present
- 文件统计：图片 218，文档 0，标注/文本 5
- 审查结论：
  - 本地文件结构未发现明显问题，可进入任务 4 清洗转换。
- 下一步清洗动作：
  - 保留 Chemistry 多选题，解析题干中 A/B/C/D 选项、答案、解释和图片引用。
  - 自由回答题暂不进入 choice-answer schema，可后续扩展到开放题 schema。
  - 数据更新后重跑：python scripts\audit_task4_datasets.py 和 python scripts\build_task4_manifests.py。

## ChineseChemExam

- 目录：`D:\competition\date\data\raw\ChineseChemExam`
- 角色：`self_collected_chinese_exam_core`
- 类型：`self_collected_pages`
- 本地状态：missing
- 文件统计：图片 0，文档 0，标注/文本 0
- 审查结论：
  - 本地未发现数据目录，当前只能完成方案级审查。
- 下一步清洗动作：
  - 完成来源授权、脱敏、PDF/图片入库和去重后，再进入人工版面标注。
  - 建议首批标注 500-2000 页，覆盖题干、选项、图表、公式、答案区、解析区。
  - 数据更新后重跑：python scripts\audit_task4_datasets.py 和 python scripts\build_task4_manifests.py。

## ChineseChemLabHandout

- 目录：`D:\competition\date\data\raw\ChineseChemLabHandout`
- 角色：`self_collected_lab_handout_core`
- 类型：`self_collected_pages`
- 本地状态：missing
- 文件统计：图片 0，文档 0，标注/文本 0
- 审查结论：
  - 本地未发现数据目录，当前只能完成方案级审查。
- 下一步清洗动作：
  - 完成来源授权、模板去重和页面化后，再标注实验目的、原理、药品、仪器、步骤、现象、结论、安全说明。
  - 建议首批标注 300-500 页，后续扩展到 1000-2000 页。
  - 数据更新后重跑：python scripts\audit_task4_datasets.py 和 python scripts\build_task4_manifests.py。

## 当前判断

- ScienceQA 和 SceMQA 可自动补入公开题目数据，并生成题目理解 JSONL。
- M6Doc 完整训练/验证集受官方申请与密码限制；未获批前只能保留公开说明、申请表或测试集。
- 中文化学试卷与实验讲义仍应作为自采核心数据，公开数据不能直接替代细粒度中文教育版面标注。
