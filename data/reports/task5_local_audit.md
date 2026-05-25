# 任务 5 数据集清洗与审查报告

目标：清洗出与化学/化工有关、可支撑轻量化工流程图节点-箭头-参数解析的数据源。

说明：用户写的是“五个数据集”，但清单实际包含 6 个数据源；本报告全部纳入审查，并按核心、辅助、迁移、后续大规模四档清洗。

## 总览

| 数据集 | 清洗档位 | 决策 | 化学相关 | 图结构适配 | 本地状态 | 关键用途 |
|---|---|---|---:|---:|---|---|
| PID_dataset | later_or_hold | keep_later_large_scale | 5/5 | 5/5 | missing | industrial_pfd_pid_symbol_detection_reference |
| PIDCon | core | keep_core_for_graph_eval | 5/5 | 5/5 | missing | graph_recovery_evaluation_and_connectivity_transfer |
| Dataset-P&ID / Digitize-PID | auxiliary | keep_auxiliary_with_license_check | 5/5 | 4/5 | missing | synthetic_symbol_detection_pretraining |
| ReactionDataExtractor2 | auxiliary | keep_auxiliary | 5/5 | 3/5 | missing | baseline_parser_and_schema_reference |
| RxnScribe | core | keep_core | 5/5 | 3/5 | missing | core_reaction_scheme_graph_pretraining |
| AI2D | transfer_only | keep_transfer_only | 2/5 | 4/5 | missing | generic_diagram_node_arrow_text_pretraining |

## 统一保留信号

- Contains chemical reaction schemes, PFD/P&ID drawings, chemistry apparatus, chemical structures, reaction conditions, process equipment, pipelines, arrows, or machine-readable graph/connectivity annotations.
- Can map source annotations to node-edge-parameter graph fields.
- Has enough label structure to support object detection, arrow/line detection, OCR parameter extraction, or graph recovery.
- License/access allows research use or at least reproducible benchmarking after documented access.

## 统一剔除信号

- General scientific diagrams with no chemical/process subset or no usable object-arrow-text annotation.
- P&ID-only data that cannot be legally accessed or whose annotations do not include equipment/line/connectivity fields.
- Images without annotation, source provenance, or clear permission for research use.
- Samples that are unreadable, duplicated, missing image files, or cannot be mapped to the target graph schema.

## 推荐路线

1. 用 RxnScribe 建立反应 scheme graph 的节点、箭头、条件参数抽取基线。
2. 用 ReactionDataExtractor2 作为 baseline 和结构化输出参考。
3. 用 AI2D 做通用 diagram node-arrow-text 迁移，只保留化学或箭头密集样本。
4. 用 PIDCon 验证 node-edge graph recovery 指标，包括 GED 和 NCA。
5. PID_dataset 和 Dataset-P&ID/Digitize-PID 作为 P&ID/PFD 扩展，不建议一开始全量进入。

## 数据集细审

### PID_dataset

- 原始目录：`D:\competition\date\data\raw\PID_dataset`
- 来源：https://zenodo.org/records/8028570
- 下载：https://zenodo.org/records/8028570
- 许可/访问：CC BY 4.0
- 数据形态：industrial_piping_and_instrumentation_drawings
- 规模说明：PID_Dataset.zip, 6,685,294,325 bytes; industrial and web-scraped P&IDs
- 标注形态：P&ID images plus code/weights according to record; inspect archive for exact labels before model training
- 清洗规则：Keep equipment, valve, vessel, instrument, and pipeline samples after license/provenance review; downsample for light process diagram transfer.
- 局限：Large archive and full P&ID complexity may overwhelm a lightweight optional task.
- 下一步：Do not download by default; first reserve storage, download checksum-verified archive, then sample 50 drawings for symbol taxonomy mapping.
- 本地统计：images=0, annotations=0, archives=0, scanned=0
- 审查提醒：
  - Local dataset root not found; place files under data/raw/PID_dataset and rerun this audit.

### PIDCon

- 原始目录：`D:\competition\date\data\raw\PIDCon`
- 来源：https://github.com/sad123-yx/PIDCon
- 下载：https://github.com/sad123-yx/PIDCon
- 许可/访问：No explicit repository license found as of audit; confirm before redistribution
- 数据形态：pid_connectivity_graph_dataset
- 规模说明：600 P&ID images, 82 component classes, 7,212 component connection pairs
- 标注形态：Box (xywh,class), Line (xyxy,id), Connection [obj_1,obj_2], Path {line_1,...,line_n}
- 清洗规则：Keep all accessible images with box-line-connection-path annotations; convert directly to node-edge graph and evaluate GED/NCA.
- 局限：More engineering-heavy than lightweight diagrams; download is via Baidu Disk and license is unclear.
- 下一步：Confirm access and license; normalize boxes, lines, connections, and paths into task5_graph_schema.json.
- 本地统计：images=0, annotations=0, archives=0, scanned=0
- 审查提醒：
  - Local dataset root not found; place files under data/raw/PIDCon and rerun this audit.

### Dataset-P&ID / Digitize-PID

- 原始目录：`D:\competition\date\data\raw\Dataset-PID`
- 来源：https://arxiv.org/abs/2109.03794
- 下载：https://drive.google.com/drive/u/1/folders/1gMm_YKBZtXB3qUKUpI-LF1HE_MgzwfeR
- 许可/访问：Original Google Drive terms need verification; derived Hugging Face mirrors vary
- 数据形态：synthetic_piping_and_instrumentation_drawings
- 规模说明：Paper reports 500 annotated synthetic P&IDs with noise and complex symbols
- 标注形态：Object detection style symbol labels; public mirrors often provide YOLO or imagefolder variants
- 清洗规则：Keep synthetic P&ID images with symbol boxes; map symbols to task equipment nodes and infer line/edge data only if annotation is present.
- 局限：Often symbol-only, so node-edge graph recovery may require added line/connectivity annotation.
- 下一步：Prefer original Drive or a documented Hugging Face mirror; verify symbol class list and train/val split before ingestion.
- 本地统计：images=0, annotations=0, archives=0, scanned=0
- 审查提醒：
  - Local dataset root not found; place files under data/raw/Dataset-PID and rerun this audit.

### ReactionDataExtractor2

- 原始目录：`D:\competition\date\data\raw\ReactionDataExtractor2`
- 来源：https://github.com/dmw51/reactiondataextractor2
- 下载：https://github.com/dmw51/reactiondataextractor2
- 许可/访问：MIT
- 数据形态：chemical_reaction_scheme_toolkit
- 规模说明：Toolkit and model weights; not primarily a standalone curated dataset
- 标注形态：Detected nodes and adjacency dictionary for reaction scheme entities; arrows, conditions, diagrams, labels
- 清洗规则：Use as a baseline and schema normalizer; keep only outputs generated from chemical reaction scheme images with valid node list and adjacency dictionary.
- 局限：Still reaction scheme oriented; dependency and model-weight setup is heavier than a pure dataset.
- 下一步：Install in isolated environment if needed; run on a small RxnScribe/own sample batch and normalize outputs to task5_graph_schema.json.
- 本地统计：images=0, annotations=0, archives=0, scanned=0
- 审查提醒：
  - Local dataset root not found; place files under data/raw/ReactionDataExtractor2 and rerun this audit.

### RxnScribe

- 原始目录：`D:\competition\date\data\raw\RxnScribe`
- 来源：https://github.com/thomas0809/RxnScribe
- 下载：https://huggingface.co/yujieq/RxnScribe/blob/main/images.zip
- 许可/访问：MIT for code repository; verify dataset/model terms on Hugging Face before redistribution
- 数据形态：chemical_reaction_scheme
- 规模说明：Reaction diagrams, ground truth under data/parse/splits, five-fold cross-validation splits
- 标注形态：reactants, conditions, products with bounding boxes, OCR text, SMILES/molfile when recognized
- 清洗规则：Keep reaction diagrams with complete image and ground-truth split records; map reactants/products to nodes, reaction arrows to directed edges, and conditions text to parameters.
- 局限：Not an industrial PFD/P&ID dataset; equipment such as pump, valve, vessel is mostly absent.
- 下一步：Download images.zip only when storage permits; parse data/parse/splits into graph JSONL; audit OCR condition quality.
- 本地统计：images=0, annotations=0, archives=0, scanned=0
- 审查提醒：
  - Local dataset root not found; place files under data/raw/RxnScribe and rerun this audit.

### AI2D

- 原始目录：`D:\competition\date\data\raw\AI2D`
- 来源：https://prior.allenai.org/projects/diagram-understanding
- 下载：http://ai2-website.s3.amazonaws.com/data/ai2d-all.zip
- 许可/访问：Check AI2D terms before redistribution; dataset is hosted by AllenAI
- 数据形态：general_science_diagram
- 规模说明：4,903 images, 4,563 questions, 4,903 annotations; all package about 945MB
- 标注形态：Object segmentations, diagrammatic elements, text elements, question-answer annotations
- 清洗规则：Keep only samples whose labels/text indicate chemistry, process, flow, reaction, heat, gas, liquid, apparatus, or arrow-rich scientific diagrams; otherwise use as generic pretraining only.
- 局限：Not a chemical engineering dataset and lacks typical process equipment symbols.
- 下一步：After download, keyword-filter annotations/text; sample 100 diagrams to estimate chemistry subset size before full conversion.
- 本地统计：images=0, annotations=0, archives=0, scanned=0
- 审查提醒：
  - Local dataset root not found; place files under data/raw/AI2D and rerun this audit.

## 产物

- `data/processed/task5_dataset_review.csv`：可导入 Google Sheets 的清洗审查表。
- `data/processed/task5_graph_schema.json`：统一 node-edge-parameter graph schema。
- `outputs/task5/task5_dataset_review.xlsx`：带摘要页的 Google Sheets 兼容工作簿。
