# 任务 3：反应条件表 / 实验参数表 KIE 清洗与审查结论

## 任务目标

本任务清洗和审查五类数据源，目标是保留能服务于化学、化工场景中反应条件表和实验参数表 KIE 的数据。目标字段包括：

- 反应物、产物、催化剂、试剂、溶剂
- 温度、时间、pH、压力
- 产率、选择性、转化率、摩尔比
- 实验编号、表格行号、文档来源
- 操作步骤、合成条件、平衡化学方程式

## 统一清洗口径

保留含有以下信息的数据：

- 表格类型为 condition optimization、condition optimisation、substrate screening、reaction feature、synthesis recipe、patent reaction step。
- 文本或字段中出现 catalyst、reagent、solvent、temperature、time、yield、selectivity、conversion、pressure、pH、molar ratio、entry、reaction product 等信号。
- ChEMU 中保留 `STARTING_MATERIAL`、`REAGENT_CATALYST`、`REACTION_PRODUCT`、`SOLVENT`、`TEMPERATURE`、`TIME`、`YIELD_PERCENT`、`YIELD_OTHER` 等实体。
- solid-state synthesis recipes 中保留 target material、starting compounds、operations、conditions、balanced chemical equation。

剔除或降权：

- bibliography、funding、author contribution、table of contents
- 纯统计表、无化学实体的说明表
- 没有实验参数、反应角色或合成操作证据的记录

## 五个数据集审查结论

| 数据集 | 审查结论 | 用途 | 局限 |
|---|---|---|---|
| ChemTable | 核心保留，优先级 P0 | 反应条件优化表、底物筛选表、表格结构与化学字段联合抽取 | benchmark 标注不一定直接等于目标 KIE schema，需要转换 |
| ChemTables | 保留为前置分类器，优先级 P1 | 判断专利表格是否值得进入 KIE，构造负样本 | 主要是表格级分类，不是字段级 KIE |
| ChEMU | 核心保留，优先级 P0 | 化学专利文本中的反应步骤、实体、条件抽取 | 文本数据，不含视觉表格 bbox/cell 证据 |
| ORD / ORDerly | 保留为 schema 与标准化参照，优先级 P1 | 反应条件 JSON schema、字段规范化、产率/条件一致性检查 | 结构化反应数据，不是 OCR/表格图像数据 |
| 无机材料合成 recipes | 保留为实验参数 JSON 参考，优先级 P1 | 合成操作、温度/时间/条件、目标材料、起始物抽取 | 偏无机材料合成文本，非表格图片 |

## 当前本地审查状态

已执行：

```powershell
python scripts\audit_task3_datasets.py
python -m py_compile scripts\audit_task3_datasets.py
```

当前 `data/raw` 目录下尚未发现五个 Task 3 原始数据集，因此已经完成数据集级清洗审查、schema 设计和可复跑脚本；记录级清洗需要在原始文件下载或挂载后继续执行。

## 已生成产物

- `config/task3_reaction_condition_kie_rules.json`
- `scripts/audit_task3_datasets.py`
- `data/reports/task3_local_audit.md`
- `data/processed/task3_dataset_manifest.csv`
- `data/processed/task3_kie_schema.json`

## Google Chrome 已打开页面

- ChemTable: https://github.com/lqzxt/ChemTable
- ChemTables: https://data.mendeley.com/datasets/g7tjh7tbrj
- ChEMU: https://researchcollaborations.elsevier.com/en/datasets/chemu-dataset-for-information-extraction-from-chemical-patents/
- ORD / ORDerly: https://github.com/sustainable-processes/ORDerly
- Solid-state synthesis recipes: https://www.nature.com/articles/s41597-019-0224-1
- 本地审查报告：`data/reports/task3_local_audit.md`

## 后续记录级清洗入口

将数据放入以下目录后，重新运行审查脚本即可产生记录级候选数量和字段命中统计：

```text
data/raw/ChemTable
data/raw/ChemTables
data/raw/ChEMU
data/raw/ORD
data/raw/ORDerly
data/raw/SolidStateSynthesisRecipes
```
