# 任务 5：轻量化工流程图节点-箭头-参数解析数据清洗与审查

目标：清洗出与化学/化工有关、可用于“节点-箭头-参数-图结构恢复”的数据源。

用户材料中写的是“五个数据集”，但实际列出了 6 个候选源。本次审查全部纳入，避免漏掉 PIDCon 这类对 graph recovery 很关键的数据。

## 清洗结论

| 数据集 | 结论 | 建议角色 |
|---|---|---|
| RxnScribe | 保留为核心数据 | 反应 scheme graph 基线：reactants/products -> nodes，reaction arrow -> edge，conditions -> parameters |
| ReactionDataExtractor2 | 保留为辅助数据/工具 | baseline parser 和机器可读反应图 schema 参考 |
| AI2D | 仅做迁移预训练 | 通用 diagram node-arrow-text 结构学习，需筛出化学/流程相关样本 |
| PID_dataset | 保留但暂缓全量进入 | 工业 P&ID/PFD 扩展数据，体量大、复杂度高，先小样本验证 |
| Dataset-P&ID / Digitize-PID | 保留为辅助数据 | 合成 P&ID 符号检测预训练，需核验许可和 annotation 粒度 |
| PIDCon | 保留为 graph eval 核心数据 | box-line-connection-path 可直接映射到 node-edge graph，并支持 GED/NCA 评价 |

## 推荐路线

1. 先用 RxnScribe 做反应图节点、箭头、条件参数抽取。
2. 用 ReactionDataExtractor2 做 baseline 和结构化输出对照。
3. 用 AI2D 学通用节点、箭头、文本区域联合检测，但只作为迁移数据。
4. 用 PIDCon 验证 graph recovery，重点看 Graph Edit Distance 和 Node Connectivity Accuracy。
5. PID_dataset 和 Dataset-P&ID/Digitize-PID 放到第二阶段，用小样本证明方法可扩展到 P&ID/PFD。

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

节点类型覆盖 reactor、heater、cooler、filter、distillation、mixer、pump、valve、vessel、chemical_structure、text_label 等。

边类型覆盖 material_flow、energy_flow、information_flow、reaction_arrow、generic_arrow、line_connection。

参数类型覆盖 temperature、pressure、flow_rate、time、concentration、pH、catalyst、solvent、reagent、yield、generic_condition。

## 输出文件

```text
data/processed/task5_dataset_review.csv
data/processed/task5_graph_schema.json
data/reports/task5_local_audit.md
outputs/task5/task5_dataset_review.xlsx
```

其中 `task5_dataset_review.xlsx` 可直接上传到 Google Sheets 打开。

## 本地目录约定

下载或申请到数据后，放到以下目录再重跑审查脚本：

```text
data/raw/RxnScribe
data/raw/ReactionDataExtractor2
data/raw/AI2D
data/raw/PID_dataset
data/raw/Dataset-PID
data/raw/PIDCon
```

重跑命令：

```powershell
python scripts\audit_task5_datasets.py
```

## 当前限制

- 这次没有下载大体量原始数据，尤其没有下载约 6.7GB 的 PID_dataset。
- Google Drive 插件未安装完成，所以没有直接创建原生 Google Sheets；已生成可上传的 `.xlsx`。
- PIDCon 仓库未见明确 license，Dataset-P&ID/Digitize-PID 的 Google Drive 数据也需要使用前核验许可。
