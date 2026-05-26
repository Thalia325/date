# 任务 3：反应条件表 / 实验参数表 KIE 清洗与审查结论

## 本轮完成状态

已将缺失的任务 3 原始数据补到本地约定目录，并重新生成审查产物：

- `data/raw/ChemTable`
- `data/raw/ChemTables`
- `data/raw/ChEMU`
- `data/raw/ORD`
- `data/raw/ORDerly`
- `data/raw/SolidStateSynthesisRecipes`

已重新运行：

```powershell
python scripts\audit_task3_datasets.py
python -m py_compile scripts\audit_task3_datasets.py
```

输出已更新：

- `data/reports/task3_local_audit.md`
- `data/processed/task3_dataset_manifest.csv`
- `data/processed/task3_kie_schema.json`

## 本地审查结果

| 数据集 | 本地状态 | 文件数 | 抽样记录 | 候选记录 | 结论 |
|---|---:|---:|---:|---:|---|
| ChemTable | present | 1410 | 1000 | 1000 | 核心保留，用于视觉表格 KIE。 |
| ChemTables | present | 8 | 1576 | 1454 | 保留为表格类型路由器和负样本来源。 |
| ChEMU | present | 4765 | 4708 | 4701 | 核心保留，用于专利文本实体/事件 KIE。 |
| ORD / ORDerly | present | 141 | 1754 | 624 | 保留为结构化 schema、标准化和一致性检查参考。 |
| SolidStateSynthesisRecipes | present | 1 | 1000 | 1000 | 保留为实验操作、条件和无机材料合成参数参考。 |

## 数据补充说明

- ChemTable 使用公开 GitHub 仓库 `ustc-ai4science/ChemTable` 的本地浅克隆，实际结构为 `data/img` 和 `data/metadata.csv`。
- ChemTables 使用 Mendeley Data 的公开文件，保留 `ChemTables_ALL.json` 和 60/20/20 的 `Train/Dev/Test` 标准划分。
- ChEMU 使用 Mendeley Data 的公开 NER/EE train/dev zip，并保留标注指南、license 和 readme。
- ORD 目前补入 Hugging Face `open-reaction-database/ord-data` 的真实 `.pb.gz` 分片样本；ORDerly 使用公开仓库轻量克隆，包含 `condition_prediction` 基准目录。
- Solid-state synthesis recipes 使用 Figshare 公开 JSON，文件大小与 Figshare 元数据一致，并已通过 JSON 解析，当前本地记录数为 19,488。

## 当前结论

原先“记录级数据正确性、去重、字段命中率、清洗完整性无法确认”的阻塞已经解除。当前审查脚本已经能对 ChemTable/ChemTables/ChEMU/ORDerly/SolidStateSynthesisRecipes 做本地抽样与字段命中统计。

下一步应进入 dataset-specific converter：

- `convert_chemtable_to_task3_kie.py`
- `convert_chemtables_to_task3_router.py`
- `convert_chemu_to_task3_kie.py`
- `convert_ord_to_task3_reference.py`
- `convert_solid_state_recipes_to_task3_kie.py`
