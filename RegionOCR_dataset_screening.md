# RegionOCR 数据集清洗筛选报告

任务目标：化学文档区域识别与分类，也就是在整页文档中检测并分类标题、正文、表格、化学方程式、分子结构图、反应路线图、实验步骤、题目区域、答案区域、图注、表注等区域。

## 筛选标准

优先级最高的数据需要同时满足：

- 整页文档图像或 PDF 页面，而不是单独裁剪图。
- 有区域级标注，最好是 bounding box、mask 或 COCO 格式标注。
- 类别能映射到 RegionOCR 目标类别。
- 化学教材、化学试卷、科学论文或化学专利页面占比足够。
- 许可证和下载方式允许当前项目使用。

辅助数据可以只满足其中一部分，例如只提供分子结构图检测，或只提供化学图片分类。

## 结论总览

| 数据集 | 结论 | 推荐用途 | 不推荐用途 |
|---|---|---|---|
| M6Doc | 可作为主干训练集，但需要申请训练/验证集 | 通用文档区域检测；化学教材/试卷页面筛选；标题、正文、表格、题目、答案等区域 | 直接学习精细化学语义，如反应条件、实验步骤、化学方程式细分类 |
| DECIMER-Segmentation | 可作为化学结构区域专家模块 | 分子结构图检测、mask/框标注、RegionOCR 的 chemical_structure 类 | 完整页面多类别 layout 训练 |
| Chemical Images Classifier Dataset | 可作为区域裁剪分类器训练集 | 判断裁剪区域是一分子、多分子、反应图、其他；给检测后的化学区域做二级分类 | 整页区域检测，因为它不是 page-level 标注 |
| PatCID | 不建议作为主训练集；建议只取 benchmark 或弱监督子集 | 专利化学结构弱监督、分子图区域扩展、专利域评估 | 教育文档 RegionOCR 主训练集；高精度人工区域标注主来源 |

## 数据集 1：M6Doc

可用性：高，但有访问门槛。

保留建议：

- 优先保留 `textbook`、`test paper`、`scientific article`。
- 在 `textbook` 和 `test paper` 内进一步筛选 Chemistry 学科页面。
- 保留可映射到 RegionOCR 的类别：title、text/paragraph、figure、table、caption、question、answer、header/footer 等。
- 如果标注里没有独立的 chemical_equation、reaction_scheme、experiment_step，则先不要强行细分，可统一映射到 `formula_or_equation`、`figure`、`text_block`，后续再人工抽样细标。

剔除建议：

- magazine、newspaper、book、note 如果不是当前模型目标域，先不进入第一版训练。
- 与化学文档无关的科目页面先剔除，避免版面分布污染。

清洗动作：

1. 申请完整训练/验证集。
2. 读取 COCO 格式 annotation。
3. 按文档类型、学科、语言、页面质量过滤。
4. 建立 M6Doc 标签到 RegionOCR 标签的映射表。
5. 对 Chemistry 子集抽样检查 50-100 页，确认题目、答案、图表、公式类区域是否足够。

结论：作为 RegionOCR 的 layout backbone 最合适，但不能单独覆盖全部“化学语义区域”。

## 数据集 2：DECIMER-Segmentation

可用性：中高，适合专家类。

保留建议：

- 保留所有 chemical structure depiction 检测结果。
- 输出统一转成 `chemical_structure` 类。
- 如果有 mask，保留 mask；如果模型或下游只用检测框，则从 mask 计算 bbox。

剔除建议：

- 非结构图区域不要尝试从该数据集扩展成正文、表格、标题等类别。
- 对反应路线图、多个分子组合图要单独抽样确认，避免被误当成单个结构图。

清洗动作：

1. 使用 DECIMER-Segmentation 对科学论文 PDF/图像跑结构图检测。
2. 将检测结果转为 RegionOCR 标注格式。
3. 对低置信度、过小 bbox、页面边缘残缺结构进行过滤。
4. 抽样人工复核，作为 chemical_structure 类的补充训练/验证数据。

结论：不是完整 RegionOCR 数据集，但非常适合补强“分子结构图”这个关键类别。

## 数据集 3：Chemical Images Classifier Dataset

可用性：中高，适合分类器，不适合检测器。

保留建议：

- `one_molecule` -> `chemical_structure_single`
- `several_molecules` -> `chemical_structure_multiple`
- `reactions` -> `reaction_scheme`
- `other` -> 负样本或 `non_chemical_image`

剔除建议：

- 不要把它当作整页 layout detection 数据。
- 如果训练 RegionOCR 检测器，只能作为检测后 crop 的二级分类模块。

清洗动作：

1. 下载 `dataset_for_image_classifier.zip`。
2. 校验 md5。
3. 解压后按 `classified` 和 `for_model` 两套目录分别处理。
4. 统一图片格式、尺寸统计、损坏文件检查。
5. 对 `other` 类抽样，确认是否包含数学公式、普通图、表格或文字块，必要时拆成更细负样本。

结论：适合作为 RegionOCR 后处理分类器或化学区域判别器。

## 数据集 4：PatCID

可用性：低到中，适合大规模弱监督和专利域评估。

保留建议：

- 优先使用 D2C-RND / D2C-UNI benchmark，而不是直接使用完整 PatCID。
- 保留人工标注页面、chemical image bbox、molecular/Markush/background 分类。
- 如果需要专利域模型，再抽取小规模弱监督子集。

剔除建议：

- 暂不把完整 PatCID 作为第一阶段训练集，规模太大、领域偏专利、标注多为自动生成。
- 不用于教育文档题目/答案/实验步骤区域识别。

清洗动作：

1. 先下载 benchmark 数据，不下载全量数据。
2. 转换 bbox/class 标注到 RegionOCR 格式。
3. 将 `Molecular Structure` 映射到 `chemical_structure`。
4. 将 `Markush Structure` 映射到 `markush_structure` 或并入 `chemical_structure_special`。
5. 将 `Background` 作为困难负样本。
6. 对全量 PatCID 只做弱监督扩展，需单独设计质量阈值。

结论：对“化学专利分子图区域”很强，但对“化学教育文档 RegionOCR”不是主数据源。

## 推荐组合

第一阶段：

- M6Doc Chemistry textbook/test paper/scientific article 子集：训练通用文档区域检测。
- DECIMER-Segmentation：补强 `chemical_structure` 区域。
- Chemical Images Classifier Dataset：训练检测框 crop 的二级分类器。

第二阶段：

- PatCID D2C benchmark：做专利域评估和少量补充训练。
- PatCID 全量或子集：只在需要专利域弱监督扩展时使用。

## RegionOCR 标签映射建议

| RegionOCR 目标类 | 首选来源 | 辅助来源 |
|---|---|---|
| title | M6Doc | 无 |
| paragraph/text | M6Doc | 无 |
| table | M6Doc | 无 |
| figure | M6Doc | 无 |
| figure_caption | M6Doc | 无 |
| table_caption | M6Doc | 无 |
| question | M6Doc test paper | 无 |
| answer | M6Doc test paper | 无 |
| chemical_structure | DECIMER-Segmentation | PatCID benchmark |
| reaction_scheme | Chemical Images Classifier `reactions` | PatCID/人工细标 |
| chemical_equation | M6Doc 近似 + 人工补标 | im2latex/公式数据只能辅助 |
| experiment_step | M6Doc text block + 人工补标 | 无 |
| non_chemical_image | Chemical Images Classifier `other` | M6Doc figure/table/text 负样本 |

## 最终可用性判断

可直接进入候选池：

- M6Doc：主数据，但需申请完整 train/val。
- DECIMER-Segmentation：化学结构检测模块。
- Chemical Images Classifier Dataset：裁剪图分类模块。

暂缓全量使用：

- PatCID：先用 benchmark，小心使用全量弱监督数据。

不建议当前直接做的事：

- 不建议把 Chemical Images Classifier 当整页检测数据。
- 不建议把 PatCID 全量直接混入教育文档训练。
- 不建议只靠 M6Doc 解决化学方程式、反应路线、实验步骤等细粒度化学语义类别。
