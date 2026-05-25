# 任务 2 下一步执行清单

## 当前判断

本地 `data/raw` 还没有 PEaCE、DECIMER-Segmentation、MolScribe 或 PatCID 原始数据，因此当前阶段只能完成数据集可用性判断、目录约定、审计脚本和空 manifest 验证。

任务 2 的主线应当以 PEaCE 为核心：

- OCR 标签来源：PEaCE 的 LaTeX ground truth。
- 规范化目标：从 LaTeX 生成 `mhchem_candidate`，再解析为可复核的 reaction JSON。
- 辅助结构识别：DECIMER-Segmentation、MolScribe、PatCID 只进入结构图 OCSR 分支，不混入文本方程式 OCR 主标注。

## 最小可执行流程

1. 将 PEaCE 解压到 `data/raw/PEaCE`，确保包含：

```text
final_renders/
labels.jsonl
train.txt
dev.txt
test.txt
```

2. 重新审计本地数据：

```powershell
python scripts\audit_task2_datasets.py
```

3. 生成 PEaCE 化学表达式 OCR manifest：

```powershell
python scripts\build_peace_expression_manifest.py
```

4. 生成 LaTeX 到 mhchem / reaction JSON 候选：

```powershell
python scripts\build_task2_normalization_candidates.py
```

5. 抽样复核 `data/processed/peace_normalization_candidates.csv`：

- `mhchem_candidate` 是否保留上下标、电荷、物态、箭头和条件。
- `reaction_json` 是否正确拆分 reactants/products。
- `normalization_status=expression_only` 的记录是否应保留为单个化学表达式 OCR 样本。

## 数据集分工

| 数据集 | 是否进入第一阶段 | 角色 | 产物 |
|---|---:|---|---|
| PEaCE | 是 | 化学表达式 OCR 主数据 | LaTeX OCR、mhchem 候选、reaction JSON 候选 |
| DECIMER-Segmentation | 否，第二阶段 | 结构图区域检测 | bbox/mask/segmentation |
| MolScribe | 否，第二阶段 | 分子结构图转结构 | SMILES、molfile、atom-bond graph |
| PatCID | 否，谨慎使用 benchmark | 专利域结构图扩展 | SMILES/graph 或检索评估样本 |

## 风险点

- PEaCE 不是 native `mhchem` 数据集，不能直接把转换结果当最终标注。
- 规则转换容易在复杂电荷、可逆反应、上下标嵌套和反应条件上出错，必须抽样复核。
- PatCID 全量数据规模大且专利域偏强，第一阶段不建议下载全量并混入 OCR 训练。

## 阶段完成标准

第一阶段可交付应包含：

- 非空 `peace_expression_manifest.csv`。
- 非空 `peace_normalization_candidates.csv`。
- 一份抽样复核记录，至少覆盖反应式、单个化学式、电荷、物态、条件箭头五类样本。
