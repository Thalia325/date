# 任务 2：化学表达式 OCR 与 mhchem / JSON 规范化数据准备

本项目这轮只筛选是否能服务两层任务：

1. OCR：从图像中识别化学式、反应式、上下标、电荷、箭头和条件。
2. 规范化：把 OCR 结果转成 `mhchem` 或结构化 JSON。

## 目录约定

请把下载或申请到的数据放到：

```text
data/raw/PEaCE
data/raw/DECIMER-Segmentation
data/raw/MolScribe
data/raw/PatCID
```

处理后的筛选结果放到：

```text
data/processed
```

审计报告放到：

```text
data/reports
```

## 数据集判断

### 1. PEaCE

结论：核心数据集，优先使用。

保留：

- `final_renders/` 中的记录图像。
- `labels.jsonl` 中的 LaTeX ground truth。
- `train.txt`、`dev.txt`、`test.txt` split。
- 包含化学元素、上下标、箭头、电荷、加号、状态符号或反应条件的候选样本。

暂不直接当作最终规范化标签：

- PEaCE 的标签是 LaTeX，不是 native `mhchem`。
- 需要另做 LaTeX 到 `\ce{...}` 和 reaction JSON 的转换、校验、抽样复核。

### 2. DECIMER / MolScribe / PatCID

结论：辅助 OCSR 数据，不是化学方程式 OCR 主数据。

保留用途：

- DECIMER-Segmentation：检测文档里的分子结构图区域。
- MolScribe：把分子结构图转换成 SMILES、molfile 或 atom-bond graph。
- PatCID：专利域分子结构图数据；第一阶段只建议用 D2C benchmark，不建议直接混入全量弱监督数据。

不建议用途：

- 不要直接把这些数据当成 `\ce{2H2 + O2 -> 2H2O}` 这类文本方程式 OCR 标注。
- 不要用 PatCID 全量数据替代 PEaCE 做通用化学表达式识别。

## 本地审计

```powershell
python scripts\audit_task2_datasets.py
```

输出：

```text
data/reports/task2_local_audit.md
```

## PEaCE 表达式 manifest

PEaCE 数据解压到 `data/raw/PEaCE` 后运行：

```powershell
python scripts\build_peace_expression_manifest.py
```

输出：

```text
data/processed/peace_expression_manifest.csv
```

该 manifest 只保留疑似化学表达式/反应式样本，字段包括：

```text
image_path, source_dataset, split, latex, normalization_target
```

如果要保留 PEaCE 全量记录用于混合 OCR 预训练，可运行：

```powershell
python scripts\build_peace_expression_manifest.py --include-all
```

## LaTeX 到 mhchem / JSON 候选

生成 `peace_expression_manifest.csv` 后，可先做一轮规则候选转换：

```powershell
python scripts\build_task2_normalization_candidates.py
```

输出：

```text
data/processed/peace_normalization_candidates.csv
data/processed/peace_reaction_json_candidates.jsonl
```

注意：该脚本只生成可复核候选，不把 PEaCE LaTeX 直接视为最终 `mhchem` 或 reaction JSON ground truth。后续需要抽样检查化学计量数、电荷、物态、反应条件和箭头方向。

推荐复核字段：

```text
latex, mhchem_candidate, normalization_status, normalization_notes, reaction_json
```

## 推荐训练/评估组合

第一阶段：

- 用 PEaCE 训练化学表达式 OCR。
- 从 PEaCE LaTeX 标签生成 `mhchem` 候选。
- 对 `mhchem` 候选再解析成 reaction JSON。

第二阶段：

- 用 DECIMER-Segmentation 发现结构图区域。
- 用 MolScribe 或 PatCID 相关模型把结构图转成 SMILES / graph JSON。
- 将文本反应式 JSON 与结构图 SMILES/graph 结果合并。

## 当前结论

任务 2 可做，且 PEaCE 是最直接的数据源。但公开数据里没有成熟的大规模 `mhchem` ground truth，因此“化学 OCR + mhchem 标准化 + JSON 结构化”本身可以作为项目贡献点。
