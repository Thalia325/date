# 任务 5：轻量化工流程图节点-箭头-参数解析数据清洗与审查

目标：审查项目中是否已经覆盖与化学/化工相关、可用于解析流程图、反应路线图、PFD/P&ID 中节点、箭头、条件、参数、流向的数据源，并给出清洗结论。

## 结论

当前项目此前已经有任务五审查框架和产物，但存在两类问题：

1. 报告文本存在中文编码乱码，影响交付可读性。
2. 数据清单没有完整覆盖用户明确点名的数据源，缺少 `RxnCaption / U-RxnDiagram-15k` 和 `PID2Graph`。

本次已补齐这两个数据源，并重新生成审查产物。当前任务五共纳入 8 个候选源：4 个核心/图评估源、2 个辅助源、1 个迁移预训练源、1 个后续大规模扩展源。

## 数据源审查表

| 数据源 | 是否包含 | 清洗结论 | 建议角色 |
|---|---|---|---|
| RxnScribe | 已包含 | 保留为核心反应图数据 | 反应 scheme graph 基线：reactants/products -> nodes，reaction arrow -> edge，conditions -> parameters |
| ReactionDataExtractor2 | 已包含 | 保留为辅助工具/基线 | baseline parser、结构化输出参考、反应图 schema 对照 |
| RxnCaption / U-RxnDiagram-15k | 本次补齐 | 保留为核心反应图数据 | 约 1.5 万反应图，适合反应图拓扑、箭头、条件/参数解析训练 |
| PID2Graph | 本次补齐 | 保留为核心 P&ID 图结构数据 | P&ID 图到 graph structure，节点含 bbox/label，线表示 edge，可作为 PFD/P&ID 代理 |
| PIDCon | 已包含 | 保留为图结构评估扩展 | box-line-connection-path 可直接映射 node-edge graph，适合 GED/NCA 评估 |
| PID_dataset | 已包含 | 暂缓全量进入 | 工业 P&ID/PFD 扩展数据，体量大，先做小样本验证 |
| Dataset-P&ID / Digitize-PID | 已包含 | 保留为辅助扩展 | 合成 P&ID 符号检测预训练；需要核验许可和标注粒度 |
| AI2D | 已包含 | 仅用于迁移预训练 | 通用 diagram node-arrow-text 学习；需筛出化学/流程相关样本 |

## 数据正确性判断

- 化学反应图方向较成熟：`RxnScribe`、`ReactionDataExtractor2`、`RxnCaption / U-RxnDiagram-15k` 都与反应路线图解析直接相关，可覆盖反应物/产物、箭头、条件、文字标签、拓扑结构等核心要素。
- 真正公开的化工 PFD 数据较少：本项目采用 `PID2Graph`、`PIDCon`、`PID_dataset`、`Dataset-P&ID / Digitize-PID` 作为 P&ID/PFD 工程图代理，方向合理。
- 当前本地 `data/raw` 尚未放入这些任务五原始数据目录，因此审查结果是“源级清洗完成，原始文件未落地”。不能声称已经完成样本级去重、坏图剔除、bbox/edge 坐标校验或 train/val/test 完整性校验。
- 已生成统一 graph schema，可承接不同数据源的节点、边、参数、OCR 文本块映射。

## 统一目标 Schema

已写入：

```text
data/processed/task5_graph_schema.json
```

核心结构：

```text
diagram_id, source_dataset, image_path, split
nodes: node_id, type, bbox, text, attributes
edges: edge_id, type, source_node_id, target_node_id, polyline, arrowhead, parameters
text_blocks: text_id, text, bbox, linked_node_id, linked_edge_id
```

节点类型覆盖：reactor、heater、cooler、filter、distillation、mixer、pump、valve、vessel、chemical_structure、text_label、generic_diagram_object。

边类型覆盖：material_flow、energy_flow、information_flow、reaction_arrow、generic_arrow、line_connection。

参数类型覆盖：temperature、pressure、flow_rate、time、concentration、pH、catalyst、solvent、reagent、yield、generic_condition。

## 推荐清洗路线

1. 先用 `RxnScribe` 建立反应图节点、箭头、条件参数抽取基线。
2. 用 `RxnCaption / U-RxnDiagram-15k` 扩大反应图拓扑、箭头、条件/参数解析覆盖。
3. 用 `ReactionDataExtractor2` 做 baseline parser 和结构化输出对照。
4. 用 `PID2Graph` 验证 P&ID/PFD 代理图结构恢复，重点检查节点 bbox、label、edge/line 连接。
5. 用 `PIDCon` 做 graph recovery 补充评估，关注 Graph Edit Distance 和 Node Connectivity Accuracy。
6. `PID_dataset` 与 `Dataset-P&ID / Digitize-PID` 放到第二阶段，先抽样核验许可、标注粒度和符号体系，再决定是否全量进入。
7. `AI2D` 只做通用图表迁移，必须筛出化学、流程、箭头密集、装置相关样本。

## 输出文件

```text
data/processed/task5_dataset_review.csv
data/processed/task5_graph_schema.json
data/reports/task5_local_audit.md
outputs/task5/task5_dataset_review.xlsx
```

`task5_dataset_review.xlsx` 可直接上传到 Google Sheets 打开。

## 本地目录约定

下载或申请到数据后，按以下目录放置并重跑审查脚本：

```text
data/raw/RxnScribe
data/raw/ReactionDataExtractor2
data/raw/U-RxnDiagram-15k
data/raw/PID2Graph
data/raw/PIDCon
data/raw/PID_dataset
data/raw/Dataset-PID
data/raw/AI2D
```

重跑命令：

```powershell
python scripts\audit_task5_datasets.py
node scripts\build_task5_workbook.mjs
```

## 当前限制

- 本次没有下载大体量原始数据，尤其没有下载约 GB 级的 P&ID/PID 数据包。
- 所有任务五候选源当前在本地均显示为 `missing`，说明清洗规则、审查表和统一 schema 已完成，但样本级清洗要等原始数据落地后继续。
- `RxnCaption / U-RxnDiagram-15k`、`PID2Graph`、`PIDCon`、`Dataset-P&ID / Digitize-PID` 使用前仍需逐项核验 license、访问方式和可再分发范围。
