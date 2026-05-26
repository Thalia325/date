# 任务 2：化学表达式识别与 mhchem / JSON 规范化清洗审查结论

审查日期：2026-05-25

## 任务定位

目标是把化学表达式、化学方程式、上下标、离子、电荷、反应箭头、物态和反应条件从图像中识别出来，并规范化为：

```json
{
  "latex": "",
  "mhchem": "",
  "entities": [],
  "reaction_arrow": "",
  "charge": [],
  "state": [],
  "stoichiometry": []
}
```

本任务分两层：

- OCR 层：图像到 LaTeX，核心数据应有图片和表达式 ground truth。
- 规范化层：LaTeX 到 `\ce{...}` / reaction JSON，需要规则转换和人工抽样复核，不能把规则候选直接当最终标注。

## 本地数据包含情况

已执行：

```powershell
python scripts\audit_task2_datasets.py
python scripts\build_peace_expression_manifest.py
python scripts\build_task2_normalization_candidates.py
python scripts\build_chemical_classifier_manifest.py
python -m py_compile scripts\audit_task2_datasets.py scripts\build_peace_expression_manifest.py scripts\build_task2_normalization_candidates.py
```

当前本地 `data/raw` 中没有任务 2 所需的 `PEaCE`、`DECIMER-Segmentation`、`MolScribe`、`PatCID` 原始目录。实际存在的是 `ChemicalImagesClassifier` 压缩包和下载分片，并已索引出 16000 条分类样本；它可辅助区域/类别判断，但不含图像到 LaTeX / mhchem / reaction JSON 的直接标注。

## 数据集审查表

| 模块 | 任务定位 | 推荐数据集 / 网站 | 本地是否包含 | 数据是否正确 | 清洗是否完成 | 能解决什么 | 建议输出格式 | 适配度 |
|---|---|---|---|---|---|---|---|---|
| 化学表达式 OCR 主数据 | 图像识别化学式、反应式、上下标、电荷、箭头、条件 | PEaCE: Printed English and Chemical Equations | 否，`data/raw/PEaCE` 缺失 | 公开来源与任务匹配；本地未下载，无法做记录级正确性核验 | 未完成，只完成脚本和空 manifest 验证 | 训练“化学表达式图像 -> LaTeX”；为 mhchem/JSON 规范化提供源标签 | `image_path, split, latex, mhchem_candidate, reaction_json` | 高，P0 |
| 化学排版规范层 | 规范化化学式、方程式、上下标、电荷、箭头 | mhchem / CTAN | 不是数据集，不应放入 raw 数据 | 作为输出规范正确；不提供训练样本 | 规则候选脚本已准备，需 PEaCE 非空数据后复核 | 把 LaTeX/OCR 输出统一成 `\ce{...}` 表达 | `mhchem`, `reaction_arrow`, `charge`, `state`, `stoichiometry` | 高，P0 标准层 |
| 分子结构图区域检测 | 文档中结构式图片区域检测，不负责文本方程式 OCR | DECIMER-Segmentation | 否 | 本地无法核验 | 未完成 | 找出分子结构图 crop，供 OCSR 使用 | `bbox/mask/segmentation` | 中，P1 辅助 |
| 分子结构图转结构 | 结构图转 SMILES / molfile / atom-bond graph | MolScribe | 否 | 本地无法核验 | 未完成 | 把结构式图片转成结构化分子表示 | `smiles, molfile, structure_json` | 中，P1 辅助 |
| 专利域结构图扩展 | 专利图片中的分子结构识别和检索评估 | PatCID，优先 D2C benchmark | 否 | 本地无法核验 | 未完成 | 扩展专利域 OCSR，不替代 PEaCE | `smiles, graph_json, benchmark_id` | 中低，P2 谨慎使用 |
| 图像类别辅助数据 | 化学图片区域分类：单分子、多分子、反应图、其他 | Chemical Images Classifier Dataset | 是，zip/分片存在 | 压缩包目录含 `one_molecule`、`several_molecules`、`reactions`、`rest/other` 类别；但无 LaTeX/mhchem 标签 | 已生成辅助分类 manifest，共 16000 条；不是任务2主清洗结果 | 可训练区域分类器，不能直接训练表达式 OCR 或规范化 | `image_path, source_label, target_label, split` | 低到中，辅助而非任务2主数据 |

## 已生成产物状态

| 文件 | 当前状态 | 结论 |
|---|---:|---|
| `data/reports/task2_local_audit.md` | 已生成 | 确认四个任务2目标数据集本地缺失 |
| `data/processed/peace_expression_manifest.csv` | 仅表头，0 条记录 | PEaCE 未下载，无法形成 OCR 样本 |
| `data/processed/peace_normalization_candidates.csv` | 仅表头，0 条记录 | 无 LaTeX 输入，无法生成 mhchem 候选 |
| `data/processed/peace_reaction_json_candidates.jsonl` | 空文件，0 条记录 | 无 reaction JSON 候选 |
| `data/processed/chemical_classifier_manifest.csv` | 16000 条分类记录 | 可作为区域/类别辅助数据；仍不能替代 PEaCE 的 LaTeX OCR 标注 |

## 清洗结论

任务 2 方向成立，且与化学化工场景高度相关；但当前本地还没有可用于训练/评估的 PEaCE 原始数据，所以记录级清洗尚未开始。

PEaCE 应作为第一阶段核心数据集。它提供图片和 LaTeX 标注，适合做“化学表达式图像 -> LaTeX”。但 PEaCE 不是 native mhchem 数据集，必须经过 `latex -> mhchem_candidate -> reaction_json_candidate -> 抽样复核` 的链路后，才能变成可靠规范化标注。

DECIMER-Segmentation、MolScribe、PatCID 只建议进入结构图 OCSR 分支；它们可以服务化工文档中的结构图识别和 SMILES/graph 生成，但不应当混入 `\ce{2H2 + O2 -> 2H2O}` 这类文本化学方程式 OCR 主标注。

## 下一步最小闭环

1. 下载并解压 PEaCE 到 `data/raw/PEaCE`，确保存在：

```text
final_renders/
labels.jsonl
train.txt
dev.txt
test.txt
```

2. 重新运行审计和清洗候选生成：

```powershell
python scripts\audit_task2_datasets.py
python scripts\build_peace_expression_manifest.py
python scripts\build_task2_normalization_candidates.py
```

3. 人工抽样复核至少覆盖五类样本：

- 普通化学式：如 `H2O`、`NaCl`
- 反应式：如 `2H2 + O2 -> 2H2O`
- 离子/电荷：如 `SO4^2-`
- 物态：如 `(s)`、`(l)`、`(g)`、`(aq)`
- 条件箭头：如 `\xrightarrow{heat}`、可逆箭头

## 参考来源

- PEaCE paper: https://arxiv.org/abs/2403.15724
- PEaCE code/data instructions: https://github.com/ZN1010/PEaCE
- mhchem package: https://ctan.org/pkg/mhchem
