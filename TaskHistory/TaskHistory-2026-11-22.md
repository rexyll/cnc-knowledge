

## CH04-T001 — 零部件分类与主数据阶段性交付/验收记录

### 交付内容

- 新增正文：`docs/04-components-materials-and-manufacturing/part-classification-and-master-data.md`，知识实体KNOW-000016。
- 建立项目级三级分类树，覆盖结构承载、直线运动进给、主轴回转、ATC、工作台工件支承、润滑介质、液压气动、排屑防护、电气控制硬件边界、紧固标准件及易损耗材。
- 明确PART、PRODUCT、SUBSYS、BOM、MAT、PROCESS身份边界；明确PART内部ID与OEM物料号、图号、标准件代码、供应商订货代码分离；定义修订、有效期、去重与证据状态规则。
- 新增字段字典：`docs/data-model/chapter-dictionaries/CH04.csv`；新增空白模板：`docs/data-model/templates/part-master.template.json`。模板不代表实际零件。
- 新增来源SRC-000095～SRC-000097（ISO 13584-35:2010、IEC 61360-1:2017、ISO 8000-100:2016官方目录页）；新增KNOW-000016；标准来源直接挂接知识实体，不创建标准伪实体或来源关系。
- 更新CH04 README、docs总目录、章节计划、根计划、数据字典索引、覆盖矩阵和本日历史。

### 证据与边界

- ISO 13584系列用于零件库数据表达/交换方法背景；IEC 61360-1用于属性定义和分类层级方法参考；ISO 8000-100用于主数据质量方法背景。本文分类树为项目参考设计，不声称是上述标准的规范分类。
- 当前没有经授权的具体机床图纸/BOM，因此没有新增PART/MAT/PROCESS实体，没有录入型号级零件数量、图号、公差、材料牌号、OEM制造商或替代关系。
- 典型部件名称仅用于分类示例；不表示所有机型均配置该部件。PART的实际装配数量/位号必须由CH20 BOM及其配置版本承载。
- 标准全文未下载或复制，仅登记官方元数据和链接。

### 验收边界

- 分类树覆盖任务要求的结构、传动、主轴、ATC、工作台、辅助介质、液压气动、防护排屑、标准件和易损件类别。
- 主数据模板将内部ID与外部编号分离，包含配置、图纸修订、材料、接口、制造商/供应商、检验、追溯和来源字段。
- 严格质量检查通过后任务标记DONE；CH04整体保持IN_PROGRESS，后续继续材料数据库、制造工艺和型号级规格研究。

# TaskHistory — 2026-11-22

> 时区：Asia/Shanghai（UTC+08:00）  
> 当日目标：完成MAP-001行业全景图首轮建图，形成行业分类、产业链、代表性厂商/产品生态及可追溯实体数据。

## 已完成任务

| 任务ID | 任务名称 | 完成时间（UTC+08:00） | 分支 | 最终提交SHA | 交付物 | 验收结果 |
|---|---|---|---|---|---|---|
| MAP-001 | 建立数控机床行业、机型、厂商、系统及供应链首轮全景图 | 2026-11-22T00:11:41+08:00 | main | [19de9c6](https://github.com/rexyll/cnc-knowledge/commit/19de9c62a884c297086c524390fe740703e8cfc2) | `docs/01-industry-and-fundamentals/industry-map.md`、`docs/02-machine-types-and-products/machine-tool-classification.md`、`docs/19-manufacturers-products-and-supply-chain/representative-ecosystem.md`、`docs/data/`、`docs/data-model/chapter-dictionaries/CH02.csv`、`CH19.csv`、`docs/coverage/CHAPTER-COVERAGE.csv` | 建立26条SRC来源、50个实体、30条关系；包括14种机床类型、8个术语、15家代表性组织、7个整机型号/系列、6项CNC/运动/直线运动产品；GitHub Actions Run #4通过，5项单元测试通过，质量脚本PASS（0 errors），检查22章、203条内部链接、42处来源引用和22条覆盖记录。 |
| CH01-T002 | 整理数控机床基本原理、坐标系、轴系与运动链术语 | 2026-11-22T00:26:22+08:00 | main | [1a5c3f6](https://github.com/rexyll/cnc-knowledge/commit/1a5c3f64927db7c9e51e1cb1e79008176e8683a6) | docs/01-industry-and-fundamentals/cnc-machine-fundamentals.md、docs/GLOSSARY.md、docs/data/entities/TERM/TERM-000020～TERM-000035.json、docs/data/sources/SRC-000027～SRC-000034.json、章节README | 新增1篇基础原理文章、16条术语实体和8条来源记录；覆盖NC程序执行链、HMI/NC/PLC职责、MCS/WCS、零点/参考点、XYZ/ABC/UVW轴系、轴数与联动、运动链、插补和反馈控制。GitHub Actions Run #9通过，5项单元测试通过，严格知识质量检查PASS（0 errors），全库统计66实体、30关系、34来源、207条内部链接。 |
| CH01-T003 | 构建行业实体与关系索引 | 2026-11-22T00:43:13+08:00 | main | [ba4cf6d](https://github.com/rexyll/cnc-knowledge/commit/ba4cf6df110246a2f0e9c995e28c8531b65b443e) | docs/01-industry-and-fundamentals/entity-relationship-index.md、docs/data/entities/KNOW/KNOW-000002.json～KNOW-000005.json、docs/data/relationships/REL-000031.json～REL-000097.json、docs/data-model/chapter-dictionaries/CH01.csv、相关README与登记规范 | 为4篇正式知识文章建立KNOW主记录；新增67条有来源的DERIVED_FROM文章索引关系，复用14种机床类型、7个整机型号、15家组织、6项产品及24个术语实体；增加CH01字段字典与索引。主提交GitHub Actions Run #11通过，5项单元测试及严格质量检查PASS（0 errors）；全库70实体、97关系、34来源。 |

> 最终验收以提交 `19de9c62a884c297086c524390fe740703e8cfc2` 触发的GitHub Actions Run #4为准：  
> https://github.com/rexyll/cnc-knowledge/actions/runs/44923203355

## 本次研究与数据范围

- 行业边界：区分宏观统计分类、协会产品目录与本项目的工程知识分类；纳入数控车削、铣削、加工中心、钻镗、磨削、齿轮加工、特种加工、金属成形及直接相关的控制/功能部件、自动化和生命周期服务。
- 分类模型：采用“加工过程 × 结构布局 × 运动/轴配置 × 自动化程度 × 工艺集成能力”的多维分类；明确轴数不等于同时联动轴数，FMC/FMS属于制造单元/系统层级。
- 产业链：覆盖基础材料与基础制造、机械功能部件、CNC/PLC/伺服/反馈、电气与通信、刀具夹具/测量、整机OEM、系统集成、终端应用和生命周期服务。
- 代表性组织：DMG MORI、Mazak、Okuma、Makino、DN Solutions、TRUMPF、沈阳机床、秦川机床、Nidec、FANUC、Siemens、HEIDENHAIN、广州数控、Yaskawa、THK。
- 代表性产品：INH 63、INTEGREX i NEO、VARIAXIS i NEO、GENOS M560-V、DVF series、沈阳机床H系列、秦川YKS7225A，以及FANUC 0i-F Plus、SINUMERIK ONE、TNC7、GSK 988MA、Sigma-7、THK LM Guide。
- 数据边界：产品归属基于厂商官方目录；没有将目录信息扩展成未经核实的精度、行程、配置、价格、库存、市场份额或采购评级。当前样本不代表全球完整厂商/型号名录。

## 章节进度与覆盖度

| 章节 | 本次完成节点 | 当前覆盖度 | 后续重点 |
|---|---|---|---|
| CH01 | CH01-T001 行业知识地图 | 1级 inventory | CH01-T002：基础原理、坐标系、轴系与通用术语 |
| CH02 | CH02-T001 机床分类体系 | 1级 inventory | CH02-T002：主要机型结构/技术档案；补充具体型号规格 |
| CH19 | CH19-T001 厂商与产品主数据 | 1级 inventory | CH19-T002继续整理整机与系统厂商；CH19-T003补齐功能部件/刀具/测量供应商 |

覆盖矩阵采用“章节主归属实体、与该章主数据相连的关系、正文/实体实际引用的去重SRC ID”口径；未归档媒体资产计数保持为0。首轮地图只是inventory，不代表相应章节整体完成。

## CI问题与修复记录

- 数据录入后首次质量检查发现4条来源记录的 `source_type` / `evidence_kind` 与Source Schema枚举不一致。
- 已将统计/协会页面的来源类型和证据性质调整为Schema允许且语义匹配的值；没有删除来源，也没有改变引用论据。
- 后续重新运行通过；覆盖矩阵去重计数校准后再次运行Run #4通过，最终结果为0 errors。

## 验收结论

MAP-001首轮行业地图已完成并在根目录TaskPlan标记为DONE。CH01-T001、CH02-T001、CH19-T001已标记DONE；CH19-T002保持IN_PROGRESS。行业地图和实体数据是具有官方资料支撑的代表性样本，不是全球完整供应商/型号库。其余知识内容继续按章节TaskPlan逐项研究，不因地图完成而自动标记完成。



## CH01-T002研究与验收记录

### 研究范围与主要结论

- 建立NC程序到加工运动的完整概念链，说明HMI、NC核心/NCK、PLC、插补/轨迹规划、坐标变换、伺服驱动、机械执行机构和位置反馈的职责边界。
- 依据ISO 841与原厂编程手册解释MCS/WCS、机床零点、工件零点和参考点，明确回参考点过程不等于返回机床零点。
- 整理X/Y/Z、A/B/C、U/V/W轴命名；把物理轴、可控轴、通道/路径轴和同时联动轴数分开，避免仅凭“五轴”描述推断五轴同时联动能力。
- 说明典型运动链、插补与伺服反馈；按位置测量点区分半闭环和全闭环，不将特定Siemens/HEIDENHAIN控制器实现泛化为所有品牌的统一架构。
- 资料来源包含2项ISO标准目录、4份原厂控制器手册/功能手册、1篇原厂技术说明和1篇同行评审论文综述。标准与原厂文档仅记录可追溯元数据、版本和定位，不复制受版权保护的全文。

### 结构化数据与覆盖度

- 新增来源：SRC-000027～SRC-000034，共8条；source_records全库由26条增至34条。
- 新增术语实体：TERM-000020～TERM-000035，共16条；CH01术语实体由8条增至24条。
- 新增知识正文：docs/01-industry-and-fundamentals/cnc-machine-fundamentals.md；CH01文章数由1篇增至2篇。
- CH01覆盖等级由1级inventory提升至2级foundational；章节引用去重SRC ID共24条；未新增需要归档的图片、动图或完整文档副本。

### 验收证据

- 主要内容提交：https://github.com/rexyll/cnc-knowledge/commit/1a5c3f64927db7c9e51e1cb1e79008176e8683a6
- GitHub Actions Run #9：https://github.com/rexyll/cnc-knowledge/actions/runs/44924463835 — success。
- 单元测试：5项全部通过。
- 严格质量检查：RESULT: PASS (0 errors)；检查22章、207条内部链接、93个Markdown文件、66条实体、30条关系、34条来源、22条覆盖记录。
- 本轮检查不包含外部URL实时存活验证；外部链接的持续可用性仍需后续网络检查。

## 当前章节进度

| 章节 | 已完成节点 | 当前覆盖等级 | 下一步 |
|---|---|---|---|
| CH01 | CH01-T001、CH01-T002 | 2级 foundational | CH01-T003：行业实体与关系索引 |
| CH02 | CH02-T001 | 1级 inventory | CH02-T002：主要机型结构与技术档案 |
| CH19 | CH19-T001 | 1级 inventory | CH19-T002/T003：整机、系统厂商与功能部件供应链 |

## 未完成 / 后续任务

- CH01-T003：构建行业实体与关系索引，避免重复登记已存在的机型/厂商实体。
- CH02-T002：按机型建立结构、工作原理、关键配置和应用技术档案。
- CH19-T002：补充整机与数控/驱动系统厂商的具体系列和地区资料。
- CH19-T003：研究主轴、轴承、丝杠、导轨、转台、刀库、编码器、刀具、夹具、测量和辅助系统供应商。
- 后续更新必须继续遵守main分支、来源证据、资源归档、质量门禁和每日历史规则。


## CH01-T003研究与验收记录

### 实体身份与关系范围

- 为4篇已有正文建立正式KNOW实体主记录：KNOW-000002行业全景图、KNOW-000003机床分类体系、KNOW-000004厂商生态图、KNOW-000005基础原理。
- KNOW-000001只存在于文章模板中，是示例ID，不作为实际知识条目登记。
- 复用CH02/CH19已有实体，不复制记录：14个MTYPE、7个MACHINE、15个VENDOR、6个PRODUCT及24个TERM。
- 新增67条DERIVED_FROM关系：行业地图9条、分类文章14条、厂商生态28条、基础原理16条。每条关系包含来源ID、正文路径、版本和引用角色。
- 本任务中的DERIVED_FROM仅表示文章对实体的内容索引和溯源；不表示制造、供货、组成、适用、兼容或标准符合关系。
- 未为尚缺少具体来源的子系统、零部件、材料、标准符合性和应用对象臆造实体；缺项由CH03～CH15等主责任章节继续研究。

### 交付物与覆盖度

- 正式知识条目主记录：4条KNOW JSON。
- 关系记录：REL-000031～REL-000097，共67条；原有30条分类、型号和制造事实关系保留。
- 新增索引正文：docs/01-industry-and-fundamentals/entity-relationship-index.md。
- 新增字段字典：docs/data-model/chapter-dictionaries/CH01.csv。
- 更新docs/ENTITY-REGISTRY.md、实体/关系记录说明、章节README和总目录。
- 全库结构统计：70条实体、97条关系、34条来源。
- 覆盖矩阵复核后：CH01为2级foundational，26个主归属实体、25条关联关系、24个去重SRC；CH02为22实体/46关系/10来源；CH19为22实体/34关系/20来源。

### 验收证据

- 主要内容提交：https://github.com/rexyll/cnc-knowledge/commit/ba4cf6df110246a2f0e9c995e28c8531b65b443e
- GitHub Actions Run #11：https://github.com/rexyll/cnc-knowledge/actions/runs/44926071399 — success。
- 覆盖矩阵更正提交：https://github.com/rexyll/cnc-knowledge/commit/ae8f28529967bb2c37c1bb5df2d67e5e95fbc83f；Run #13：https://github.com/rexyll/cnc-knowledge/actions/runs/44926221521 — success。
- TaskHistory更正提交Run #14：https://github.com/rexyll/cnc-knowledge/actions/runs/44926318124 — success。
- 单元测试5项全部通过；严格知识质量检查PASS（0 errors），检查22章、218条内部链接、94个Markdown文件、70条实体、97条关系、34条来源及22条覆盖记录。
- 离线CI不验证外部URL实时可用性。

> 本节于2026-11-22T00:46:06+08:00补齐，用于修复前一版TaskHistory遗漏T003完成详情的问题；保留此前任务计划、正文及数据的实际完成时间与提交SHA。

## 覆盖矩阵计数复核与更正记录

- 在CH01-T003完成后的最终审查中发现：CH02覆盖矩阵尚保留T003前的计数；CH19行已在前次更新中同步正确，不需修改。
- 已将CH02修正为22个主归属实体（14个MTYPE、7个MACHINE、1个KNOW）和46条主归属/关联关系（24条既有分类与机型事实关系，另有22条文章索引边）；来源数仍为10。
- CH01保持2级foundational，26个主归属实体、25条关系、24个去重SRC；CH19保持1级inventory，22个主归属实体、34条关系、20个去重SRC。
- 覆盖矩阵更正提交：[ae8f28529967bb2c37c1bb5df2d67e5e95fbc83f](https://github.com/rexyll/cnc-knowledge/commit/ae8f28529967bb2c37c1bb5df2d67e5e95fbc83f)。
- GitHub Actions Run #13：[44926221521](https://github.com/rexyll/cnc-knowledge/actions/runs/44926221521) — success；5项单元测试通过，严格知识质量检查PASS（0 errors）。最终统计仍为70实体、97关系、34来源、218条内部链接、94个Markdown文件和22条覆盖记录。
- 更正日期：2026-11-22T00:45:20+08:00。更正只校准覆盖计数和下一优先任务，不更改实体/关系事实。


## CH01-T004研究与验收记录

### 审查范围与结论

- 对根目录总体范围、22章目录映射和22份章节TaskPlan进行交叉审查，形成22章唯一主归属矩阵。
- 明确CH01行业导航与基础概念、CH02机型分类与产品家族、CH19厂商/产品主数据的边界；明确CH02产品家族与CH22具体参考整机实例的分工。
- 梳理CH03～CH08物理系统与控制职责、CH07～CH12控制器/平台/通信/软件/算法、CH12～CH15算法/工艺/检测/规范、CH16～CH18生命周期阶段、CH19～CH22供应链/工程文档/数字化/案例的交叉边界。
- 识别SUBSYS、PART、MAT、刀具/夹具、电气元件与SIGNAL、PARAM、INTERFACE/PROTO、STD、性能参数、APP、BOM配置和真实工程案例等结构化数据缺项，并指定主责任章节和建议任务。
- 结论：现有22章足以覆盖项目范围，当前不需要新增第23章；优先治理章节边界和实体主归属，避免重复建档。未把尚未研究的主题写成已验证技术事实。
- 本报告是项目治理文件，不是新增技术知识文章；不创建KNOW、TERM或其他实体，不新增关系/来源/资源记录，不调整覆盖度等级和计数。

### 交付物与验收

- 新增：docs/01-industry-and-fundamentals/industry-scope-gap-audit.md。
- 更新：docs/TaskPlan/01-industry-and-fundamentals/TaskPlan.md，CH01-T004状态改为DONE。
- 更新：根目录TaskPlan.md，下一优先任务调整为CH02-T002及CH19-T002/T003。
- 更新：docs/coverage/CHAPTER-COVERAGE.csv，仅调整CH01下一优先任务和审查说明；CH01仍为2级foundational、2篇文章、26个实体、25条关系、24条来源、0项资源。
- 审查依据：仓库当前22份章节任务计划、根目录范围/Guide/Limit及现有目录和数据登记；没有将外部链接实时可用性作为本任务验收内容。
- 所在分支：main。完成时间：2026-11-22T10:51:00+08:00。最终提交SHA：ee29ce4f755544f00f6e0c557724e46ba451fd57；GitHub Actions Run #16（44978323889）success，5项单元测试全部通过，严格知识检查PASS（0 errors）。



## CH02-T002研究与验收记录

### 研究范围与交付

- 新增正文：docs/02-machine-types-and-products/machine-type-technical-archives.md，KNOW-000006，版本1.0。
- 覆盖车床/车削中心、铣床/加工中心（立式、卧式、龙门、五轴）、钻床/镗床、磨削/精整、齿轮加工、EDM/其他特种加工、金属成形、车铣复合/多任务及专用/组合机床。
- 每类档案按工作原理、典型结构、轴系/运动、适用工件、应用边界和选型关注点组织；增加类型级比较矩阵、跨章节边界和术语速查。
- 明确机床类型、结构布局、轴配置、自动化和工艺集成是不同维度；明确可控轴数量不等于同时联动轴数；不从“5轴”标签推断实际五轴同时联动或精度。
- 使用ISO 10791、ISO 13041、ISO/TC 39/SC 2标准目录、同行评审研究、Brother公开业务简报、Mazak和Okuma厂商资料建立9条新来源SRC-000035～SRC-000043。
- 为KNOW-000006建立主记录；新增14条DERIVED_FROM文章索引关系REL-000098～REL-000111，分别链接已有14个MTYPE实体。索引边不代表产品组成、制造、适用或性能符合关系。
- 扩展CH02字段字典，补充工作原理、典型结构、典型轴系、典型工件/工序和选型约束字段定义。
- 更新CH02 README、TaskPlan、覆盖矩阵及总计划；CH02-T002标记DONE，下一任务为CH02-T003。

### 证据与边界

- ISO 10791-6:2014用于加工中心速度/插补测试范围；ISO 10791-7:2020用于加工试件精度测试及3～5轴同时加工的适用范围。
- ISO 13041-5:2015用于数控车床/车削中心速度、进给和插补测试；ISO 13041-2:2020用于立式工件主轴车削机床几何测试。
- ISO/TC 39/SC 2官方目录用于定位机床几何/定位/热效应及EDM测试标准系列；具体标准的适用性和现行状态仍需按项目合同和机床配置核验。
- 厂商资料只作为厂商声明和结构示例，不视为独立实测、长期可靠性证明或跨品牌兼容证据。
- 本任务没有下载/复制受版权限制的标准或厂商文档；仅保存来源元数据和官方链接。未生成或收集需要归档的图片/动图/完整文档副本。

### 覆盖度与验收

- CH02覆盖度调整为2级foundational：2篇文章、23个主归属实体（14 MTYPE + 7 MACHINE + 2 KNOW）、60条关系（含14条新文章索引边）、19条去重来源、2项SVG资源文件。
- 覆盖统计按实体主归属、关系关联及文章/实体引用的去重SRC计算；未把型号未核验参数填入实体。
- 所在分支：main。完成时间：2026-11-22T11:20:00+08:00。主要内容提交SHA：a80017ec5b17c57d534e5907fe7ff5229bae4088；GitHub Actions Run #18（44978860961）success，5项单元测试通过，严格知识检查PASS（0 errors）。最终目录索引与来源权利状态校正由后续提交补充。

## CH02-T003研究与验收记录

### 研究范围与交付

- 新增正文：`docs/02-machine-types-and-products/representative-model-catalog.md`，知识实体KNOW-000007，版本1.0。
- 复用已有7条MACHINE记录，新增3条型号实体：MACHINE-000008 DMG MORI DMU 50 3rd Generation、MACHINE-000009 Mazak QUICK TURN 200MSY、MACHINE-000010 TRUMPF TruLaser 3030 fiber。
- 新增来源SRC-000044～SRC-000048，共5条制造商官方产品页；全部标记link_only，不复制版权受限文档。
- 新增6条型号事实关系（MODEL_OF、MANUFACTURED_BY）和10条目录索引关系DERIVED_FROM；索引关系只表示导航与溯源。
- 为Okuma GENOS M560-V、Mazak INTEGREX i-200 NEO/i-200S NEO、Mazak QUICK TURN 200MSY、DMG MORI DMU 50 3rd Generation及TRUMPF TruLaser 3030 fiber记录型号级公开参数，逐项标明单位和SRC ID。
- 对INH 63、VARIAXIS i NEO、DN Solutions DVF series、沈阳机床H系列、秦川YKS7225A保留官方产品目录身份，未在缺少精确规格书时补造参数。
- 扩展CH02字段字典，补充官方产品页、规格版本/核验日期、规格适用范围字段；更新CH02/总目录、根计划、章节计划和覆盖矩阵。

### 规格边界与资料权利

- 所有规格均为制造商公开声明，不是独立第三方测试或现场实测。
- GENOS M560-V记录明确限定OSP-P500配置，不与GENOS M560V-5AX规格混用。
- INTEGREX系列区分i-200、i-200S等子型号；第二主轴、下刀塔和主轴选项不得跨型号泛化。
- QUICK TURN 200MSY参数只对应原厂页面该型号行；其他QUICK TURN型号不继承该参数。
- DMU 50基础/选配主轴、刀库配置分开记录；TruLaser 3030 fiber的激光功率/板厚受激光器与工艺包影响。
- 本轮没有下载/复制完整PDF或其他文档，没有生成/保存图片、动图；资源计数为0。外部资料保留官方链接并按link-only处理。

### 覆盖度与验收

- CH02覆盖度：2级foundational，3篇知识文章、27个主归属实体（14 MTYPE+10 MACHINE+3 KNOW）、76条关系、24条去重来源、0项资源。
- CH19覆盖矩阵同步增加3条跨章OEM制造关系及5条新官方来源，更新为22个主归属实体、37条关系、25条去重来源。
- 所在分支：main。完成时间：2026-11-22T12:10:00+08:00。内容提交SHA：000da457f0a766d825bbb674acabbd8e557a885f；GitHub Actions Run #20（44979575609）success，5项单元测试通过，严格知识检查PASS（0 errors）。
- 验收包含Schema结构、ID唯一性、来源/关系引用、Markdown内部链接和严格知识质量脚本；离线CI不等于外部URL实时可用性验证。


## CH02-T004研究与验收记录

### 研究范围与交付

- 新增正文：`docs/02-machine-types-and-products/machine-tool-selection-methodology.md`，知识实体KNOW-000008，版本1.0。
- 建立需求输入清单、工艺路线与机型初筛表、硬性门槛（Gate）检查、8维度加权比较矩阵、1～5分评分尺度、证据等级和N/V未验证处理规则。
- 建立精度测试证据框架，区分几何精度、数控轴定位/重复定位、热效应、动态性能和代表性工件试切；引用ISO 230-1:2012、ISO 230-2:2014及Amd 1:2016、ISO 10791-7:2020和ISO 13041-6:2009的官方目录范围。
- 建立完整循环产能模型、TCO/单位合格件成本模型、风险台账和项目选型决策记录模板。
- 增加轴类车削、箱体/复杂壳体加工、齿轮精加工、薄板切割4个工程方法案例；案例用于说明决策方法，不构成具体品牌或型号排名。
- 新增来源SRC-000049～SRC-000052，均为ISO官方标准目录链接，rights_status=link_only；未复制标准全文或下载受版权限制资料。
- 新增14条DERIVED_FROM索引关系REL-000128～REL-000141，关联14个MTYPE实体，仅表示选型方法文章的主题索引，不表达具体工件适用性或性能保证。
- 扩展CH02字段字典，增加硬门槛、评价权重、分项分值、证据层级和选型假设字段；更新章节README、docs总目录、章节计划、覆盖矩阵和根计划。

### 证据与边界

- ISO 230-1:2012范围为无负载/准静态几何精度测试，不等于动态切削性能测试。
- ISO 230-2:2014及Amd 1:2016用于数控直线轴和旋转轴定位精度/重复性评估，不单独代表成品加工精度。
- ISO 10791-7:2020用于与测试配置兼容的加工中心试件切削精度评估；其范围覆盖3～5轴同时加工测试。
- ISO 13041-6:2009用于数控车床/车削中心标准试件切削精度评估。
- 评分权重、评分尺度、产能和TCO模型属于可调整工程方法模板，不是ISO规定或行业统一权重；项目选型须以实际工件、配置、试切、报价和现场条件为准。
- 本轮无本地图片、动图或完整文档资源新增，资源数0；外部标准全文不复制，保留官方目录链接。

### 覆盖度与验收

- CH02覆盖度：2级foundational，4篇知识文章、28个主归属实体（14 MTYPE+10 MACHINE+4 KNOW）、90条关系、28条去重来源、0项资源。
- 所在分支：main。完成时间：2026-11-22T13:00:00+08:00。内容提交SHA：0746f0785d15ae0b329783d07519c66a4f45de45；GitHub Actions Run #21（44980892285）success，单元测试和严格知识质量检查均通过。覆盖矩阵计数校准提交：b616aec7a42353ab4e5353f91b0080b9f0262487；该提交仅修正CH02覆盖统计行。
- 离线CI只验证仓库结构、Schema、内部链接和质量规则，不代表已对某具体设备完成试切、产能测定或采购验收。


## CH19-T002研究与验收记录

### 研究范围与交付

- 新增正文：`docs/19-manufacturers-products-and-supply-chain/machine-tool-oem-and-system-vendor-profiles.md`，知识实体KNOW-000009，版本1.0。
- 复用现有15家VENDOR实体：DMG MORI、Yamazaki Mazak、Okuma、Makino、DN Solutions、TRUMPF、沈阳机床、秦川机床、Nidec、FANUC、Siemens、HEIDENHAIN、广州数控GSK、Yaskawa和THK；没有重复创建组织实体。
- 新增官方来源SRC-000053～SRC-000061，共9条，覆盖DMG MORI、Mazak、Okuma、Makino、TRUMPF、FANUC、Siemens、HEIDENHAIN和THK。全部标记manufacturer_product_page、authority_tier=A、evidence_kind=manufacturer_declaration、rights_status=link_only。
- 新增15条文章索引关系REL-000142～REL-000156，subject均为KNOW-000009，predicate为DERIVED_FROM，object为既有15家VENDOR实体。每条关系均带来源、核验状态、置信度、文章路径/版本和明确的非事实关系边界。
- 档案区分整机OEM、钣金/激光加工设备OEM、CNC/运动控制平台和机械功能部件供应商；对Mazak集团/世界总部/美国法人/工厂/支持据点、DMG MORI服务网络等信息注明组织和证据边界。
- 明确控制器、驱动、整机OEM的职责边界；禁止从供应商产品目录推断具体机床BOM、控制器配置、互操作性、当前库存、交期或中国本地服务能力。
- 更新CH19 README、docs总目录、CH19 TaskPlan、根TaskPlan和覆盖矩阵。CH19-T002标记DONE，CH19-T003标记IN_PROGRESS。

### 覆盖度与验收

- CH19覆盖等级提升为2级foundational：2篇文章、23个主归属实体（15 VENDOR + 6 PRODUCT + 2 KNOW）、52条关联关系（16条制造事实关系 + 36条文章索引边）、34条去重来源、0项资源文件。
- 没有下载或复制受版权限制的厂商手册/目录；只保存官方链接元数据。未新增图片、动图或完整文档资源。
- 所在分支：main。完成时间：2026-11-22T10:00:00+08:00。主要内容提交SHA：[64144980b3992448a24a744db883cc6747c1dd5d](https://github.com/rexyll/cnc-knowledge/commit/64144980b3992448a24a744db883cc6747c1dd5d)。GitHub Actions Run #26（44981812672）success；5项单元测试通过，严格知识质量检查PASS（0 errors）。
- 研究结论均限定为原厂公开声明；本任务不包含第三方产品测试、采购价格、库存、交期或供应商质量评级。


## CH19-T003研究与验收记录

### 研究范围与交付

- 新增正文：`docs/19-manufacturers-products-and-supply-chain/key-component-suppliers-and-products.md`，知识实体KNOW-000010，版本1.0。
- 复用既有THK实体VENDOR-000015，不重复创建；新增8家厂商VENDOR-000016～VENDOR-000023：SKF、NSK、HIWIN、Bosch Rexroth、Renishaw、BLUM-Novotest、Sandvik Coromant、SCHUNK。
- 新增10个产品族PRODUCT-000007～PRODUCT-000016：THK Ball Screw、SKF主轴超精密轴承、NSK超精密轴承、NSK精密主轴、HIWIN机械部件、Bosch Rexroth线性运动技术、Renishaw机床测量、BLUM机床测量、Sandvik Coromant刀具系统、SCHUNK VERO-S。
- 新增官方来源SRC-000062～SRC-000070，共9条；来源均为原厂产品/应用页面，authority_tier=A、evidence_kind=manufacturer_declaration、rights_status=link_only。
- 新增9条文章索引关系REL-000157～REL-000165（KNOW-000010 DERIVED_FROM VENDOR）和10条产品制造归属关系REL-000166～REL-000175（PRODUCT MANUFACTURED_BY VENDOR）。所有关系均有source_ids、verification_status、confidence、产品范围和不推断整机采用/兼容/供货状态的限定。
- 供应链类别覆盖直线导轨、滚珠丝杠、主轴轴承、主轴单元、工件/刀具测量、断刀检测、位置反馈、切削刀具、工件装夹和零点快换；新增选型/替代核验清单。
- 更新CH19 README、docs总目录、CH19字段字典、章节TaskPlan、根TaskPlan和覆盖矩阵；CH19-T003标记DONE，CH19-T004标记IN_PROGRESS。
- 没有下载或复制版权受限的原厂PDF/手册；未新增图片、动图或完整文档资源。

### 证据边界与未完成项

- 官方页面只证明其发布者公开列出的产品类别/产品族；不证明任何特定整机OEM的实际BOM、产品在某地区的库存、交期、当前销售状态或本地授权服务能力。
- 未取得具体订货代码/版本时，不录入精度、尺寸、额定载荷、预压、转速、切削参数、夹紧力等数字；这些字段需由对应原厂具体型号目录/图纸支持。
- 未做第三方性能测试、替代互换试验、现场兼容验证或采购询价；跨品牌替代和供应状态均not_assessed。
- 后续CH19-T004将建立比较字段、兼容性证据等级和供应风险核验流程；需结合具体机床配置和采购区域进一步研究。

### 覆盖度与验收

- CH19覆盖等级保持2级foundational：3篇文章、42个主归属实体（23 VENDOR + 16 PRODUCT + 3 KNOW）、71条关系（26条制造事实关系 + 45条文章索引边）、43条去重来源、0项资源文件。
- 所在分支：main。完成时间：2026-11-22T11:30:00+08:00。内容提交SHA：[a6f672466194462b9b15fbad739e731897651341](https://github.com/rexyll/cnc-knowledge/commit/a6f672466194462b9b15fbad739e731897651341)。GitHub Actions Run #28（44982389647）success；5项单元测试通过，严格知识质量检查PASS（0 errors）。


## CH19-T004研究与验收记录

### 研究范围与交付

- 新增正文：docs/19-manufacturers-products-and-supply-chain/supply-chain-comparison-and-risk-management.md，知识实体KNOW-000011，版本1.0。
- 建立跨供应商比较基线，明确比较对象层级、完整订货代码、硬件/软件版本、机床配置、工况、地区和文件修订版等必需字段。
- 建立C0～C4兼容性证据等级（未知/目录线索/文件对照/台架或离线验证/目标机床验证与批准），分别评价机械、电气、通信、软件、工艺和安全接口；未验证项N/V不打分。
- 建立替代矩阵、生命周期状态模型、停产/最后订货/支持结束核验、地区供货/授权服务/备件证据要求、风险台账和采购阶段门流程。
- 使用THK官方停产/替代页面SRC-000071作方法示例；明确该公告只适用于其列出的型号、尺寸、区域和页面核验时点，原厂替代声明不等于机床级互换批准。
- 新增关系REL-000176（KNOW-000011 DERIVED_FROM VENDOR-000015），仅用于文章导航和THK生命周期公告溯源，不表达制造、供货或兼容事实。
- 扩展CH19数据字典，增加分域兼容性证据、生命周期状态、地区供应、售后、风险评估和采购比较字段；更新CH19 README、docs总目录、根计划、覆盖矩阵和本日历史记录。
- 未创建具体产品跨品牌替代事实、兼容性等级、供应商风险分值、价格、库存、交期或地区售后结论；未知状态保留N/V/not_assessed。未下载或复制版权受限资料，未新增图片/动图/完整文档资源。

### 证据与边界

- THK官方页面列出部分LM/LME/LM-L直线轴承和LM Guide产品的停产安排及替代系列，并提醒替代尺寸并非全部相同；该页面不能证明具体机床接口、性能、库存、交期或当地服务。
- C0～C4、风险台账字段和采购阶段门是本知识库的工程管理方法，不是ISO标准或厂商认证等级。
- 兼容性需按具体型号/版本/机床配置和六个接口域分别核验；安全域独立评审。没有原厂文件或测试证据时，不作兼容判断。
- GitHub Actions离线质量检查验证结构、Schema、来源/关系引用、内部链接和质量规则，不验证外部URL实时可用性，也不替代实际产品互换试验、实机验证、采购询价或地区服务审计。

### 覆盖度与验收

- CH19覆盖等级保持2级foundational：4篇知识文章、43个主归属实体（23 VENDOR + 16 PRODUCT + 4 KNOW）、72条关系（26条制造事实关系 + 46条文章索引边）、44条去重来源、0项资源文件。
- 所在分支：main。完成时间：2026-11-22T11:52:00+08:00。内容提交SHA：[6432a6e8582cb72a6a37aeeefdd91b62cd2beca3](https://github.com/rexyll/cnc-knowledge/commit/6432a6e8582cb72a6a37aeeefdd91b62cd2beca3)。GitHub Actions Run 44982785371 success；5项单元测试通过，严格知识检查PASS（0 errors；22章、97实体、176关系、71来源、276条内部链接）。


## CH03-T001研究与验收记录

### 研究范围与交付

- 新增正文：docs/03-system-architecture-and-mechanics/architecture.md，知识实体KNOW-000012，版本1.0。
- 建立L0加工对象与工艺、L1机械结构与运动执行、L2驱动与能源、L3数控与机床逻辑、L4测量反馈、L5人机交互/制造信息，以及横向安全约束层的通用功能架构。
- 正文内嵌两幅Mermaid架构/运动链文本图，并另行导出两幅原创SVG图，说明典型加工任务链、运动链、力流及能量/控制/反馈/信息流；SVG文件和资源索引均归档在resouces/03-system-architecture-and-mechanics/。
- 建立10类功能子系统（含抽象整机架构根节点）及15项功能接口关系表，明确接口双方、类别、方向/内容和验证关注点。
- 新增11条SUBSYS实体（SUBSYS-000001～SUBSYS-000011）和5条TERM实体（TERM-000036～TERM-000040），新增KNOW-000012。
- 新增10条HAS_SUBSYSTEM关系、8条CONTROLS关系和16条文章/术语DERIVED_FROM索引关系（REL-000177～REL-000210）；所有关系带来源和范围限定。抽象架构关系不代表具体机型BOM、接线或安全设计。
- 新增来源SRC-000072～SRC-000076：ISO 841:2001标准目录、NISTIR 5331、NIST CAM/CNC集成研究、机床机械接口研究及机床系统标准化建模案例。
- 新建CH03字段字典；新增ASSET-000001/000002及REL-000211/000212；建立resouces/03-system-architecture-and-mechanics/ASSET-INDEX.md；更新正文图片引用、KNOW-000012资源字段、CH03 README、docs总目录、GLOSSARY、章节TaskPlan、根TaskPlan、覆盖矩阵和本日历史。
- 未创建具体机型BOM、实际接线关系、产品参数或安全等级；未下载/复制版权受限的ISO/学术论文全文，新增两幅原创SVG图，归档至resouces/03-system-architecture-and-mechanics/并建立ASSET-INDEX.md；未复制外部受版权保护图片或标准/论文全文。

### 证据与边界

- ISO 841:2001作为机床坐标系与运动命名标准目录参考；标准全文受版权保护，仅保存元数据和官方链接。
- NISTIR 5331（1993）用于控制模块、接口、层次化控制和反馈架构的历史参考；其旧平台实例不代表当前产品实现或行业唯一架构。
- NIST 2020 CAM/CNC研究用于说明NC程序路径与过程反馈集成问题；不泛化为所有现代CNC均存在同一限制。
- NIST 2022机床机械接口研究用于结构接口、刚度、热稳定性、几何精度和磨损等问题范围；不据此填入任何具体机型参数。
- NIST 2020标准化建模案例用于机床几何/运动学信息的系统建模与互操作参考。
- 本文分层、子系统分类和接口矩阵属于通用工程参考模型，不是ISO强制结构、厂商配置清单或实际机床验证结论。具体机型必须由原厂图纸、规格、接线、CNC/PLC/驱动文件和现场验证补全。
- 安全相关功能必须按具体机型风险评估和适用标准验证；本文不提供旁路防护/联锁操作。

### 覆盖度与验收

- CH03覆盖度提升为2级foundational：1篇知识文章、14个主归属实体（11 SUBSYS + 1 KNOW + 2 ASSET；5个TERM由CH01主归属并由本章引用）、36条关系（10 HAS_SUBSYSTEM + 8 CONTROLS + 16 DERIVED_FROM索引 + 2 HAS_ASSET）、5条去重来源、2项SVG资源文件。
- 所在分支：main。完成时间：2026-11-22T12:42:00+08:00。架构正文与实体关系提交SHA：[8e643f801d2f896a31a6e2ddd8dea9675455c525](https://github.com/rexyll/cnc-knowledge/commit/8e643f801d2f896a31a6e2ddd8dea9675455c525)；术语主归属/覆盖矩阵校准提交SHA：[8963ac033c0192d10d92e6d3501a976571bd5f72](https://github.com/rexyll/cnc-knowledge/commit/8963ac033c0192d10d92e6d3501a976571bd5f72)；SVG资源归档提交SHA：[1e8304fa2ec7726ba408c4224fbc2b6646debcda](https://github.com/rexyll/cnc-knowledge/commit/1e8304fa2ec7726ba408c4224fbc2b6646debcda)。GitHub Actions Run 44983319094、44983367599、44983452904均success；5项单元测试通过，严格知识检查PASS（0 errors）。最终结构统计：116实体、212关系、76来源、103个Markdown文件、2项SVG资源、280条内部链接。
- 自动CI验证Schema、ID唯一性、来源/关系引用、Markdown内部链接和严格质量规则；离线检查不替代外部URL实时检查、具体机型拆机/BOM/接线核验或安全验证。


## CH03-T002 — 主要机械结构研究与验收记录

### 任务完成信息

| 项目 | 记录 |
|---|---|
| 任务ID | CH03-T002 |
| 任务名称 | 整理主要机械结构 |
| 完成时间（UTC+08:00） | 2026-11-22T12:15:36+08:00 |
| 分支 | `main` |
| 任务状态 | DONE |
| 主要内容提交 | [f749fa0](https://github.com/rexyll/cnc-knowledge/commit/f749fa075cc58cf4332d9d69533c8977d3e685ac) |
| 术语/覆盖度校准 | [aa1d7b3](https://github.com/rexyll/cnc-knowledge/commit/aa1d7b3d6f4a740b67e97f186d1746f74bf6fa0b) |
| 用户提供PNG资源入库审查 | [1249982](https://github.com/rexyll/cnc-knowledge/commit/124998227e2be4945b69dd5b4e35b849d00c4a59) |
| CI验收 | [GitHub Actions Run 44984206408](https://github.com/rexyll/cnc-knowledge/actions/runs/44984206408) — success |

### 研究范围与主要交付

- 新增正文 `docs/03-system-architecture-and-mechanics/major-mechanical-structures.md`（KNOW-000013），覆盖床身/底座、立柱/横梁、滑鞍/滑枕/主轴箱、工作台/托盘/回转工作台、滚动/滑动/静压导向、滚珠丝杠、齿轮齿条、其他直线驱动、联轴器和支承轴承。
- 梳理结构件的承载/运动关系、典型力流、安装基准、机械接口、导向与传动的方案边界；明确结构布局因机型变化，不将通用示意误作具体机型BOM或装配图。
- 建立关键参数字典和测量口径：行程、导轨跨距/滑块间距、丝杠导程、轴向/径向刚度、预压、回差、几何误差、跳动、热漂移及定位精度。明确必须同时记录测点、基准、测量长度、温度、暖机、载荷、仪器和标准版本。
- 复用CH02既有ISO 230-1:2012、ISO 230-2:2014来源；新增SRC-000077～SRC-000083，包含ISO 8636-1:2026官方范围页，以及THK、SKF、mayr和Bosch Rexroth原厂技术资料。原厂资料只支持对应产品族声明，不推断特定OEM采用、兼容性或库存。
- 新增CH01主归属共用术语TERM-000041～TERM-000049，并在术语表中登记；CH03正文引用其ID，不另造重复术语。
- 新增原创SVG资源：`mechanical-structure-overview.svg`、`linear-feed-axis.svg`；分别建立ASSET-000003、ASSET-000004和HAS_ASSET关系REL-000214、REL-000215。
- 新增知识上下文关系REL-000213（KNOW-000013 DERIVED_FROM KNOW-000012），其语义仅为专题导航/上下文，不表示具体机型组成。
- 仓库所有者在本任务执行期间另行上传 `Block Diagram of CNC Machine.png`（提交5b6285f）。已登记为ASSET-000005，但由于图片存在疑似拼写/识别错误，且作者、出处和权利状态未确认，状态保持candidate/in_review；暂不在正文中作为技术证据引用。
- 更新CH03章节README、总目录、CH03字段字典、资源README/ASSET-INDEX、章节TaskPlan、覆盖矩阵和根TaskPlan。

### 来源与技术边界

- ISO 8636-1:2026只适用于其规定的固定双立柱、移动工作台固定横梁桥式铣床范围，不能外推至所有龙门/单柱/移动横梁布局。
- ISO 230-1与ISO 230-2用于区分几何精度和数控轴定位精度/重复定位测试；不以单个导轨或丝杠产品参数代替整机验收。
- THK、SKF、mayr、Bosch Rexroth资料均标记为原厂声明/官方技术文档；不将其产品特征或示例数值泛化到其他品牌和型号。
- 没有录入未经来源核实的机床尺寸、材料牌号、载荷限值、安装公差、产品型号或OEM BOM；标准全文和厂商受版权保护的完整资料均未复制。
- 维护与装配章节仅给出工程检查关注点；实际拆装、预紧、校准、吊装及维修必须遵循具体机床手册、风险评估和能量隔离/LOTO程序。

### 覆盖度与质量验收

- CH03：2篇技术文章；17个已核验主归属实体（11个SUBSYS、2个KNOW、4个已核验ASSET）；另有1个待审查ASSET-000005；39条关系；14条去重来源；5项资源文件。
- CH01：新增9个主归属术语实体；覆盖矩阵更新为35个主归属实体、32条去重来源。
- 全库：129条实体、215条关系、83条来源；104个Markdown文件、289条内部链接。
- GitHub Actions Run 44984206408：5项单元测试全部通过；严格知识质量检查PASS（0 errors）；实体/关系/来源引用与资源路径检查通过。
- 质量门禁检查本地结构和引用完整性，不验证外部URL的实时可访问性，也不构成实机性能验证。

### 后续任务

- CH03-T003：分析关键机械单元（主轴、进给轴、导轨丝杠、转台、刀库和辅助系统），依赖本任务及CH04。
- 用户提供的 `Block Diagram of CNC Machine.png`：待核对原始出处、版权/许可和图中文字；未完成前不引用、不编辑原图、不作为技术依据。


## CH03-T003研究与验收记录

### 研究范围与交付

- 新增正文：`docs/03-system-architecture-and-mechanics/key-mechanical-units.md`，知识条目KNOW-000014，版本1.0。
- 深入覆盖主轴单元（驱动、轴承、夹紧、润滑冷却和热管理）、ATC（刀库/交换机构/状态互锁）、回转/摆动单元（蜗轮蜗杆、滚子凸轮、直驱及夹紧反馈）、集中润滑、切削/主轴冷却、液压气动、排屑与过滤。
- 与T002去重：进给轴、导向副、滚珠丝杠、齿轮齿条、联轴器和丝杠支承仍以major-mechanical-structures.md为主，不在本专题重复建档；主轴电机/驱动控制细节归CH08，刀具夹具细节归CH05，零件级BOM/材料归CH04。
- 新增CH01主归属术语TERM-000050～TERM-000054：主轴单元、自动换刀装置、刀库、集中润滑系统、排屑输送机；CH03通过关联章节和索引关系复用。
- 新增原创SVG：`resouces/03-system-architecture-and-mechanics/key-mechanical-units.svg`，登记ASSET-000006并建立HAS_ASSET关系。
- 新增来源SRC-000084～SRC-000090：Siemens主轴单元手册、Haas换刀/冷却排屑服务资料、Kitagawa回转台官方目录、Bijur Delimon集中润滑资料、Mayfran排屑过滤产品资料及Gökler自动换刀学术案例。受版权资料均仅记录链接，没有复制完整文档。
- 新增关系REL-000216～REL-000225，共10条，均有来源ID；DERIVED_FROM只表示文章导航/溯源，不代表具体机型配置事实。

### 技术边界与验收

- 主轴冷却、夹紧和旋转限制引用限定于Siemens 2SP1系列；ATC布局/维修内容限定于Haas相应服务手册；回转台型号参数仅属于Kitagawa具体产品页；Mayfran过滤等级仅作为其具体产品声明。
- 未推断任何OEM实际BOM、供应兼容性、所有机型通用换刀时间、主轴温度/压力/流量阈值或维护周期。
- 文章明确区分主轴冷却与切削冷却、分度与连续回转、夹紧转矩与驱动转矩、定位精度与重复定位精度；增加辅助系统选型验证矩阵和LOTO/储能/高速旋转安全边界。
- 资源索引、章节README、docs总目录、术语表、实体登记、覆盖矩阵、章节TaskPlan及根TaskPlan已同步更新。

### 覆盖度与验收

- CH03：3篇技术文章、19个主归属实体（11 SUBSYS + 3 KNOW + 5 ASSET）、49条关联关系、21条去重来源、6项资源文件；另有19个CH01主归属术语可跨章引用。
- 任务完成时间：2026-11-22T12:17:00+08:00；所在分支：main。最终提交SHA和CI结果以本节后续补录为准。
- CI验收：待提交后运行；严格知识质量检查需0 errors，5项单元测试全部通过。


### CH03-T003验收信息补录（2026-11-22T12:24:00+08:00）

- 最终提交：[7a842e9ce0df78e3b35e20ff4601a31186ad0ad2](https://github.com/rexyll/cnc-knowledge/commit/7a842e9ce0df78e3b35e20ff4601a31186ad0ad2)，所在分支：main。
- GitHub Actions Run [44984556535](https://github.com/rexyll/cnc-knowledge/actions/runs/44984556535)：success；5项单元测试全部通过；严格知识质量检查PASS（0 errors）。
- Linter统计：22章、105个Markdown文件、303条内部链接、136条实体、225条关系、90条来源、229处正文来源引用；本地结构和内部链接检查通过。
- 本地质量门禁不检查外部URL实时可访问性，也不构成具体机床实机性能验证。
- 本补录替代前文“SHA和CI结果以本节后续补录为准”的临时状态；不改变任务实际交付范围。


## CH03-T004 — 机械接口、精度链与故障关联阶段性交付记录（任务仍进行中）

### 任务完成信息

| 项目 | 记录 |
|---|---|
| 任务ID | CH03-T004 |
| 任务名称 | 建立机械接口与故障关联 |
| 阶段性交付时间（UTC+08:00） | 2026-11-22T12:48:00+08:00 |
| 分支 | `main` |
| 任务状态 | IN_PROGRESS（通用框架已交付，跨章实体映射未完成） |
| 主要交付 | `docs/03-system-architecture-and-mechanics/mechanical-interfaces-accuracy-and-faults.md`（KNOW-000015） |
| 资源 | `resouces/03-system-architecture-and-mechanics/structural-loop-interface.svg`（ASSET-000007） |
| 结构化记录 | SRC-000091～SRC-000094；REL-000226～REL-000240 |

### 研究范围与交付

- 建立16类典型机械接口清单，覆盖基础支承、床身/立柱/横梁、导轨/滑块、丝杠传动、主轴/刀柄、ATC、工作台/夹具、回转台、润滑、冷却、液压气动和排屑过滤。
- 定义刀具侧/工件侧结构环及基础闭合路径；按基础安装、结构装配、运动副、传动/反馈、热载荷、工件装夹分层梳理精度链。
- 建立设计/制造/装配/整机检测/工件基准分类，给出测量条件、测点、仪器、原始数据、不确定度和追溯字段。
- 建立10类典型异常排查矩阵，明确现象、优先检查接口、证据收集项和诊断边界；未创建未经证实的FAULT实体或CAUSES关系。
- 新增原创SVG结构环图并登记ASSET-000007；新增来源SRC-000091～SRC-000094（ISO 230-1:2012、ISO/TR 16907:2015、ISO 230-7:2015及2024几何误差综述）。ISO标准只记录官方目录元数据和范围，不复制全文。
- 更新CH03字段字典、资源索引、章节README、docs总目录、章节TaskPlan、根TaskPlan和覆盖矩阵。

### 技术边界

- ISO 230-1用于几何精度测试范围；ISO/TR 16907用于几何误差数值补偿方法背景；ISO 230-7用于回转轴误差运动/速度诱导偏移测试范围。各标准均不替代具体机型专用验收规范。
- 故障矩阵只提供排查假设，不是已确认根因或统计失效率。报警、振动、温升或加工误差均不能单独证明某一机械部件损坏。
- CH16和CH18目前仍为章节入口级内容；本任务建立跨章交接点，不代表装配工艺、型号级故障库已完成。
- 无具体机型图纸/BOM、设备实物和测量数据；未验证接口尺寸、公差、预紧参数、故障概率和实机性能。

### 阶段性交付检查

- 16类接口有双方、职责、记录字段和验证方向；结构环与精度链覆盖刀具侧和工件侧；测量记录包含基准、工况、仪器、原始数据和不确定度；异常矩阵显式区分症状与根因；原创SVG已归档并有ASSET记录。
- 新增关系仅为文章导航/资源关联，source_ids可追溯；没有建立未经证实的制造、兼容、装配或故障因果关系。
- CI Run 44984783373：5项单元测试通过，严格知识质量检查PASS（0 errors）。

### 尚未满足的最终验收条件

- 需要CH04提供型号级PART/BOM记录，CH16提供装配工序和检验点，CH18提供经证据核验的FAULT/诊断/维修实体；目前这三个章节仅有入口文档，不能将本文通用接口编号映射成具体零件或维修结论。
- 在上述依赖内容可用之前，CH03-T004保持IN_PROGRESS，不宣称最终验收完成。

### 遗留事项

- 获取具体机型授权图纸、BOM和手册后，补充型号级接口/装配基准映射。
- CH16建立装配/安装专题后映射接口到工序和检验点；CH18建立故障模式库后，将排查假设拆分为有证据的FAULT/CAUSES/RESOLVED_BY关系。
- CH14建立计量验收专题后补充适用测量方法、仪器和不确定度模型。

### CH04-T001验收信息补录（2026-11-22T12:26:42+08:00）

- 最终内容提交：[502a998988dc5627cdedabfc2a09526365b46f27](https://github.com/rexyll/cnc-knowledge/commit/502a998988dc5627cdedabfc2a09526365b46f27)，所在分支：main。
- GitHub Actions Run [44985068660](https://github.com/rexyll/cnc-knowledge/actions/runs/44985068660)：success；5项单元测试全部通过；严格知识质量检查PASS（0 errors）。
- 全库统计：22章、107个Markdown文件、310条内部链接、139个实体、240条关系、97条来源、239处正文来源引用。
- 首轮两次CI失败是由于误将SRC来源记录建模为实体关系的object；已按数据模型边界移除不合法关系记录，来源保留在KNOW实体source_ids中，最终CI通过。
- 自动检查验证结构、Schema、ID、来源引用和内部链接；不验证外部URL实时可访问性，也不构成具体机床零件身份、BOM、材料或互换性的实机验证。


## CH04-T002 — 材料数据库标准框架阶段性交付记录（任务仍进行中）

### 交付内容
- 新增正文：docs/04-components-materials-and-manufacturing/materials-database.md，知识实体KNOW-000017。
- 新增标准入口表：resouces/04-components-materials-and-manufacturing/materials-standard-map.csv。
- 新增模板：docs/data-model/templates/material-master.template.json、docs/data-model/templates/material-property-record.template.json。
- 扩展CH04字段字典，增加MAT材料身份、标准状态、交货/热处理状态、性能观测、试样方向/尺寸/取样位置和数据性质等字段。
- 新增SRC-000098～SRC-000109共12条标准目录/标准状态来源，涵盖ISO灰铸铁、球墨铸铁、金属拉伸/硬度/冲击测试、塑料/复合材料拉伸和聚合物指定、ASTM灰铸铁及EN结构钢。
- 更新章节README、docs总目录、实体登记表、数据目录说明、覆盖矩阵、章节TaskPlan和根TaskPlan。

### 技术边界与遗留
- 已区分材料族、标准牌号、材料状态和性能观测；标准分类、产品交付规范和测试方法分层管理。
- 跨标准映射状态包括正式等同、条件比较、近似参考、不等同和未知；不得仅凭相近强度/硬度或二手对照表认定等同。
- ISO 185:2020、ISO 1083:2018和ASTM A48/A48M分别限定铸铁分类/试样条件；试棒数据不能直接代表铸件任意截面。
- ISO 16396-1:2022明确同一PA指定不保证相同性能；ISO 148-1:2016仍为已出版版次，同时跟踪2026 FDIS状态，草案不作为现行标准。
- 本轮未录入具体材料牌号性能数值、未创建虚构MAT牌号实体，也未推断任何机床PART的实际用料。
- 铝合金、铜合金、合金钢/轴承钢/工具钢、硬质合金、陶瓷、复合材料的具体牌号/性能数据，以及GB/JIS标准体系仍待补充；须取得合法标准全文或制造商质保书后核录。
- 任务状态保持IN_PROGRESS；本次为标准入口与数据模型阶段性交付，不满足完整材料性能数据库验收。

### 提交与CI
- 提交前状态：main；无新建分支。
- 提交SHA与CI结果将在后续验收补录。


### CH04-T002阶段性交付验收补录（2026-11-22T13:14:00+08:00）

- 最终内容提交：[3fc8406bc61881ef267e65a6eeedcc11a6309f70](https://github.com/rexyll/cnc-knowledge/commit/3fc8406bc61881ef267e65a6eeedcc11a6309f70)，分支main。
- 资源归档校正：材料标准映射CSV已按全局资源规则移动至resouces/04-components-materials-and-manufacturing/materials-standard-map.csv，并登记在该章资源README；正文、章节计划和索引均已更新。
- GitHub Actions Run [44985442087](https://github.com/rexyll/cnc-knowledge/actions/runs/44985442087)：success；5项单元测试通过；严格知识质量检查PASS（0 errors）。
- CI统计：22章、108个Markdown文件、318条内部链接、140条实体、240条关系、109条来源、251处正文来源引用。
- 来源记录中仅在发布机构给出明确日级发布日期时填写published_on；仅有年份/月或页面最近更新日期时留空，避免把页面更新日期伪装为标准发布日期。
- 本任务继续保持IN_PROGRESS：当前交付是标准入口和数据模型，不是具体牌号性能数据全集。


### CH04-T002 — 中国GB材料标准目录核验增量（2026-11-22T14:10:00+08:00）

- 在main分支继续核验国家标准官方目录，新增SRC-000110～SRC-000116：GB/T 9439-2023、GB/T 1348-2019、GB/T 700-2006、GB/T 1591-2018、GB/T 3077-2015、GB/T 3190-2020、GB/T 3880.1-2023。
- 已确认GB/T 9439-2023现行且GB/T 9439-2010废止；GB/T 1591-2018现行且2008版废止；其余新增标准目录记录显示现行。
- 更新材料标准映射CSV、材料数据库文章、章节README和资源README。将“目录状态确认”与“标准全文条款/牌号性能数据核录”明确分开。
- 未录入未经核实的牌号性能值；未创建MAT实体；未建立GB与ISO/EN/ASTM/JIS牌号等同关系；未推断机床零件实际用料。
- 本增量仍属于CH04-T002阶段性研究，任务保持IN_PROGRESS。内容提交：62716230b7e87d9d4ad91b30f66de009e136c48d（main）。GitHub Actions Run [44986160684](https://github.com/rexyll/cnc-knowledge/actions/runs/44986160684)：success；5项单元测试通过；严格知识质量检查PASS（0 errors）。CI统计：22章、108个Markdown文件、318条内部链接、140条实体、240条关系、116条来源、258处正文来源引用。


### CH04-T002 — GB铸铁标准范围与数据采集模型增量（2026-11-22T15:20:00+08:00）

- 核验国家标准官方目录：GB/T 9439-2023现行、全部代替GB/T 9439-2010、非等效采用ISO 185:2020；官方标准项目摘要说明其产品范围、内容组成及本轮修订涉及单铸/并排/附铸试样术语。GB/T 1348-2019现行、全部代替GB/T 1348-2009、2025复审继续有效、修改采用ISO 1083:2018。
- 更新SRC-000110、SRC-000111为可直接定位的官方详情页；新增SRC-000117记录灰铸铁标准修订项目官方范围摘要，并明确其不是正式标准全文。
- 在材料数据库中分别建立灰铸铁和球墨铸铁的数据采集边界；明确主要壁厚、试样类别、试样几何、取样约定、验收指标和批次追溯字段。不得将试棒数据等同于铸件任意截面性能。
- 扩展CH04字段字典和material-property-record模板；新增资源空白采集CSV模板。未录入具体HT/QT性能值、未创建MAT牌号实体、未宣称牌号等同或机床实际用料关系。
- 任务保持IN_PROGRESS；待合法取得正式标准文本后逐表核对牌号、壁厚分档、试样类型和性能保证值。


### CH04-T002 — 铸铁数据采集模型CI验收补录（2026-11-22T15:28:00+08:00）

- 内容提交：4a9d7ce6afac3aefece938533e7faa04b4cb20a2。首次CI Run [44986392266](https://github.com/rexyll/cnc-knowledge/actions/runs/44986392266)失败，原因是新增来源SRC-000117的source_type不属于仓库允许枚举；已修正为standard_catalog，未改变来源事实内容。
- 修正提交：072a0bd0dde959139da99f2f26a0c5a146e301be（main）。GitHub Actions Run [44986422182](https://github.com/rexyll/cnc-knowledge/actions/runs/44986422182)：success；5项单元测试通过；严格知识质量检查PASS（0 errors）。
- CI统计：22章、108个Markdown文件、318条内部链接、140条实体、240条关系、117条来源、262处正文来源引用。
- 本次验收对应修正提交072a0bd；后续TaskHistory补录提交另行运行CI确认。


### CH04-T002 — GB铸铁标准正式文本获取与版权边界核验（2026-11-22）

- 核验国家标准全文公开系统公开说明：采标类推荐性标准文本公开须遵守国际版权政策；系统电子文本有个人学习研究及禁止未经授权复制/发行/网络传播等限制。GB/T 9439-2023官方详情页明确因版权保护不提供文本阅读；GB/T 1348-2019官方目录虽可核验元数据，仍未取得可逐表核录的正式文本。
- 新增来源SRC-000118记录国家标准全文公开系统的公开/使用声明；新增SRC-000119、SRC-000120记录第三方采购页面，二者仅作为采购线索，卖方授权链、交付版本、使用许可和公开仓库再分发权均标记待核验，不作为标准技术条款来源。
- 更新材料数据库2.4节，明确区分官方目录元数据、第三方销售声明、合法购买、个人研究许可和公开Git仓库再分发许可；更新标准映射CSV的正式文本访问、采购线索和权利核验字段。
- 未下载或归档版权状态不明的标准全文；未录入HT/QT牌号性能数值；未创建MAT牌号实体或任何机床实际用料关系。CH04-T002保持IN_PROGRESS。
- 所在分支：main。质量验收和最终提交SHA以本次提交触发的GitHub Actions为准。


### CH04-T002 — 正式文本获取与版权边界核验CI验收补录（2026-11-22）

- 内容提交：[fce67e7b9e8ecd3fe5f036bf503fad346feefcc0](https://github.com/rexyll/cnc-knowledge/commit/fce67e7b9e8ecd3fe5f036bf503fad346feefcc0)，所在分支：main。
- GitHub Actions Run [44986603836](https://github.com/rexyll/cnc-knowledge/actions/runs/44986603836)：success；5项单元测试全部通过；严格知识质量检查PASS（0 errors）。
- Linter统计：22章、108个Markdown文件、318条内部链接、140条实体、240条关系、120条来源、267处正文来源引用。
- 质量门禁验证仓库结构、数据记录和内部链接；不验证第三方销售商授权链，不构成标准全文的版权许可，也不验证外部URL实时可访问性。
- CH04-T002保持IN_PROGRESS；待合法取得正式标准文本且确认允许的使用范围后，才逐表录入HT/QT牌号和性能数据。


### CH04-T002 — 正式出版渠道与第三方授权线索再核验（2026-11-22）

- 查阅国家市场监督管理总局公开的《标准出版管理办法》：第3条明确国家标准由中国标准出版社出版；第7条规定经营性复制标准任何部分及将标准任何部分存入电子信息网络传播，须事先取得享有专有出版权单位的书面同意。新增官方来源SRC-000121。
- 将GB/T 9439-2023、GB/T 1348-2019的优先获取路径调整为中国标准出版社正式出版发行渠道；具体书目是否在售、载体/价格、交付完整性及授权许可范围仍待出版社直接确认。没有把第三方采购平台或SACINFO国外标准服务页面误认为已确认的GB标准官方销售渠道。
- 更新SRC-000119：Antpedia页面声称中国标准出版社正式授权销售并可官方验证，但未取得授权证明或出版方确认；搜索索引还出现全文附件入口，因来源和传播许可不明，本项目未下载、未阅读、未引用。SRC-000120仍仅为GBSTD采购线索。
- 更新材料数据库2.4节、标准映射CSV、章节README、资源README、CH04任务计划和根TaskPlan。未购买标准、未下载第三方全文、未录入HT/QT性能值或创建牌号MAT实体。
- CH04-T002保持IN_PROGRESS；下一步需要通过出版社正式渠道确认具体书目和许可，且购买行为/费用须经用户明确批准。


### CH04-T002 — 正式出版渠道核验增量CI验收补录（2026-11-22）

- 内容提交：[923ba8b9b1e4f9c4012a5c7bfbdaa6802d90ff4d](https://github.com/rexyll/cnc-knowledge/commit/923ba8b9b1e4f9c4012a5c7bfbdaa6802d90ff4d)，所在分支：main。
- GitHub Actions Run [44986798209](https://github.com/rexyll/cnc-knowledge/actions/runs/44986798209)：success；5项单元测试全部通过；严格知识质量检查PASS（0 errors）。
- Linter统计：22章、108个Markdown文件、318条内部链接、140条实体、240条关系、121条来源、270处正文来源引用。
- 质量门禁仅验证仓库结构、数据记录、来源引用和内部链接；不验证出版社具体书目库存、第三方授权链或公开仓库再分发许可。
- CH04-T002保持IN_PROGRESS；未采购、未下载标准全文，待正式出版渠道确认具体书目和许可范围。


### CH04-T002 — 结构钢与铝合金标准体系核验增量（2026-11-22）

- 复核国家标准官方详情页及全文公开系统，更新GB/T 700-2006、GB/T 1591-2018、GB/T 3077-2015、GB/T 3190-2020、GB/T 3880.1-2023的标准状态和文本获取边界。
- 发现GB/T 700-2006官方详情明确标记采标并因版权保护不提供文本阅读；其非等效采用ISO 630:1995。官方平台另显示结构钢新标准计划20251168-T-605处于批准阶段，但尚未替代现行GB/T 700-2006。
- GB/T 1591-2018现行，替代GB/T 1591-2008；官方详情页列有预览/下载入口，但本轮未提取全文。GB/T 3077-2015现行，GB/T 3077-1999废止；目录未标记采标，但未确认具体全文访问。
- GB/T 3190-2020现行，官方详情页列有预览/下载入口；明确其化学成分标准职责不替代具体产品交付和力学性能规范。
- 发现铝板带材标准体系还包括GB/T 3880.2-2024（力学性能）和GB/T 3880.3-2024（尺寸偏差），两者现行、2024-11-01实施并全部代替对应2012版；新增SRC-000122、SRC-000123。
- 更新材料数据库2.5节、标准映射CSV、CH04 README、资源README、章节TaskPlan及根TaskPlan。明确GB/T 3880.1/.2/.3与GB/T 3190之间的职责边界，并补充铝合金成分、状态、厚度、试样方向和尺寸公差采集字段。
- 未下载或归档任何标准全文；未录入未经全文核验的材料牌号成分/性能值；未创建MAT牌号实体或推断机床实际用料。CH04-T002保持IN_PROGRESS。
- 官方核验入口：GB/T 700-2006（SRC-000112）、GB/T 1591-2018（SRC-000113）、GB/T 3077-2015（SRC-000114）、GB/T 3190-2020（SRC-000115）、GB/T 3880.1-2023（SRC-000116）、GB/T 3880.2-2024（SRC-000122）、GB/T 3880.3-2024（SRC-000123）。


### CH04-T002 — 结构钢与铝合金标准增量CI验收补录（2026-11-22）

- 内容提交：[7210e2249e98f38f4495fd17cf89f39bc577a3ec](https://github.com/rexyll/cnc-knowledge/commit/7210e2249e98f38f4495fd17cf89f39bc577a3ec)，所在分支：main。
- GitHub Actions Run [44987255888](https://github.com/rexyll/cnc-knowledge/actions/runs/44987255888)：success；5项单元测试全部通过；严格知识质量检查PASS（0 errors）。
- Linter统计：22章、108个Markdown文件、318条内部链接、140条实体、240条关系、123条来源、276处正文来源引用。
- 本轮仅增加标准元数据/范围与全文获取状态，不复制标准全文；官方详情页的预览/下载入口不等于本项目已提取或核验全文。未录入GB钢材或铝合金具体牌号性能数值，未创建MAT实体。
- 自动质量门禁验证本地结构、数据记录、来源引用和内部链接；不验证外部URL实时可访问性、标准全文许可或材料性能实物符合性。CH04-T002保持IN_PROGRESS。


### CH04-T002 — 钢板带材与铝合金取样方法标准补充（2026-11-22）

- 核验国家标准官方目录并新增SRC-000124～SRC-000126：GB/T 17432-2012《变形铝及铝合金化学成分分析取样方法》现行，2025-08-06复审结论为修订，修订计划20253721-T-610处于审查阶段；GB/T 3274-2017《碳素结构钢和低合金结构钢热轧钢板和钢带》现行，全部代替GB/T 912-2008和GB/T 3274-2007，结构钢新标准计划20251168-T-605处于批准阶段但未替代现行版；GB/T 709-2019《热轧钢板和钢带的尺寸、外形、重量及允许偏差》现行，全部代替GB/T 709-2006。
- 进一步区分材料牌号/成分规范、产品交付标准、尺寸基础标准和化学成分取样/制样方法。GB/T 17432不定义GB/T 3190牌号成分限值；GB/T 3274不等于GB/T 709；热轧板带标准不得外推到棒材、锻件、冷轧材或其他产品形态。
- 更新材料数据库正文、标准映射CSV、章节TaskPlan、章节README、资源README和根TaskPlan。未提取或归档标准全文；未录入未经核验的材料牌号成分/性能值；未创建MAT牌号实体或机床实际用料关系。
- 官方来源：GB/T 17432-2012（https://std.samr.gov.cn/gb/search/gbDetailed?id=71F772D7E602D3A7E05397BE0A0AB82A）；GB/T 3274-2017（https://std.samr.gov.cn/gb/search/gbDetailed?id=Kp06oCXybAo%3D&mode=p）；GB/T 709-2019（https://std.samr.gov.cn/gb/search/gbDetailed?id=8531C702DB296551E05397BE0A0ACD16）。
- 所在分支：main；本任务保持IN_PROGRESS，待提交和CI验收。


### CH04-T002 — 钢板带材与铝合金取样方法标准补充CI验收补录（2026-11-22）

- 内容提交：[4f4c3d3a373c20fabd2d6c756d9360dd39aba3b8](https://github.com/rexyll/cnc-knowledge/commit/4f4c3d3a373c20fabd2d6c756d9360dd39aba3b8)，所在分支：main。
- GitHub Actions Run [44987566055](https://github.com/rexyll/cnc-knowledge/actions/runs/44987566055)：success；5项单元测试全部通过；严格知识质量检查PASS（0 errors）。
- Linter统计：22章、108个Markdown文件、318条内部链接、140条实体、240条关系、126条来源、279处正文来源引用。
- 自动门禁验证本地结构、Schema、来源引用和内部链接；不验证外部URL实时可访问性、标准全文许可或具体材料批次符合性。
- CH04-T002保持IN_PROGRESS；本次为标准目录元数据与职责边界增量，不代表牌号/性能数据库完成。


### CH04-T002 — 轴承钢与工具钢标准版本/修订状态核验（2026-11-22）

- 核验国家标准官方目录并新增SRC-000127～SRC-000130。
- GB/T 18254-2016《高碳铬轴承钢》仍为现行，全部代替GB/T 18254-2002；修订计划20251190-T-605当前处于征求意见阶段，拟同时修订GB/T 18254-2016和GB/T 38885-2020。计划页提供征求意见稿和编制说明入口，但本轮未下载/审阅其技术条款；草案不作为现行验收依据。
- GB/T 1299-2025《工模具钢》于2025-10-31发布、2026-05-01实施，全部代替GB/T 1299-2014和GB/T 33811-2017。
- GB/T 9943-2025《高速工具钢》于2025-08-01发布、2026-02-01实施，全部代替GB/T 9943-2008、GB/T 9941-2009和GB/T 36708-2018。原GB/T 9943-2008已于2026-02-01废止。
- GB/T 3077-2015《合金结构钢》官方详情页更新显示2026-11-09复审结论为继续有效。
- 更新材料数据库2.6节、标准映射CSV、CH04 TaskPlan、章节README、资源README和根TaskPlan。明确高碳铬轴承钢不能代表全部轴承钢；工模具钢与高速工具钢分开建档；修订计划/征求意见稿不得当作已发布标准；多项旧标准的替代关系需保留。
- 未下载或归档标准全文/修订草案；未录入轴承钢或工具钢的具体牌号成分、硬度、组织、淬透性或性能值；未创建MAT牌号实体或推断机床实际用料。
- 官方来源：GB/T 18254-2016（https://std.samr.gov.cn/gb/search/gbDetailed?id=71F772D8111ED3A7E05397BE0A0AB82A）；修订计划20251190-T-605（https://std.samr.gov.cn/gb/search/gbDetailed?id=3495E6C27C6B32A0E06397BE0A0AFC9E）；GB/T 1299-2025（https://std.samr.gov.cn/gb/search/gbDetailedCNF?id=42BA7D06A37FE936E06397BE0A0ACDC9）；GB/T 9943-2025（https://std.samr.gov.cn/gb/search/gbDetailed?id=3B46A026CC24469CE06397BE0A0AEEB8）。
- 所在分支：main；CH04-T002保持IN_PROGRESS，待标准全文合法取得和牌号级数据逐表核验。


### CH04-T002 — 轴承钢与工具钢标准版本核验CI验收补录（2026-11-22）

- 内容提交：[8d84ad7a6cb512ec8339ea01efc833795490cd06](https://github.com/rexyll/cnc-knowledge/commit/8d84ad7a6cb512ec8339ea01efc833795490cd06)，所在分支：main。
- GitHub Actions Run [44987770706](https://github.com/rexyll/cnc-knowledge/actions/runs/44987770706)：success；5项单元测试全部通过；严格知识质量检查PASS（0 errors）。
- Linter统计：22章、108个Markdown文件、318条内部链接、140条实体、240条关系、130条来源、288处正文来源引用。
- 自动门禁验证仓库结构、数据记录、来源引用和内部链接；不验证外部URL实时可访问性、标准全文许可、修订草案的技术内容或材料批次符合性。
- CH04-T002保持IN_PROGRESS；本轮仅完成标准元数据、版本替代关系及修订计划状态核验，尚未完成牌号/性能数据核录。


### CH04-T002 — 轴承钢材料族与产品形态标准扩展（2026-11-22）

- 对国家标准官方目录“轴承钢”结果进行分类梳理，新增SRC-000131～SRC-000139。
- 新增现行标准：GB/T 29913-2025《中碳合金轴承钢》（全部代替GB/T 29913.1-2013）；GB/T 32959-2025《轴承钢锻制棒材、环件及毛坯》（全部代替GB/T 32959-2016）；GB/T 28417-2023《碳素轴承钢》（全部代替GB/T 28417-2012）；GB/T 3086-2019《高碳铬不锈轴承钢》（全部代替GB/T 3086-2008）；GB/T 42785-2023《轴承钢盘条》；GB/T 18579-2019《高碳铬轴承钢丝》；GB/T 33522-2017《渗碳轴承钢锻件 技术条件》（2023-12-28复审结论继续有效）。
- 新增修订计划跟踪：20251189-T-605“高温轴承钢”拟修订GB/T 38886-2020和GB/T 38936-2020；20251191-T-605“渗碳轴承钢”拟修订GB/T 3203-2016和GB/T 33161-2016。计划项目与正式发布标准分开登记；没有证据确认的项目阶段不做推断。
- 材料数据库新增2.7节，明确高碳铬、中碳合金、碳素、高碳铬不锈、渗碳和高温轴承钢分别建档；区分牌号/材料标准、盘条/钢丝/棒材/环件/毛坯产品形态标准、锻件技术条件和零件热处理标准。
- 更新标准映射CSV、CH04 TaskPlan、章节README、资源README和根TaskPlan。官方来源包括：GB/T 29913-2025（https://std.samr.gov.cn/gb/search/gbDetailed?id=3DBA213285570D16E06397BE0A0A8119）；GB/T 32959-2025（https://std.samr.gov.cn/gb/search/gbDetailed?id=mZeF8VfZ7yI%3D&mode=p）；GB/T 28417-2023（https://std.samr.gov.cn/gb/search/gbDetailed?id=wCe3c21CrKU%3D&mode=p）；GB/T 3086-2019（https://openstd.samr.gov.cn/bzgk/std/newGbInfo?hcno=9E1558EA8CE059994AB353664BC331B2）；GB/T 42785-2023（https://std.samr.gov.cn/gb/search/gbDetailed?id=027A6096B05F643EE06397BE0A0A0867）；GB/T 18579-2019（https://openstd.samr.gov.cn/bzgk/std/newGbInfo?hcno=E62D1EC609871B95FE7C52D0041FF2B8）；GB/T 33522-2017（https://std.samr.gov.cn/gb/search/gbDetailed?id=71F772D816CDD3A7E05397BE0A0AB82A）；高温轴承钢修订项目（https://std.samr.gov.cn/gb/search/gbDetailed?id=23033A607868B961E06397BE0A0ADCC4）；渗碳轴承钢修订项目（https://std.samr.gov.cn/gb/search/gbDetailed?id=23124F8A31FDA2F5E06397BE0A0A652B）。
- 未下载或归档标准全文/修订草案；未录入具体轴承钢牌号成分、洁净度、夹杂物、碳化物、淬透性、硬度或疲劳性能值；未创建MAT牌号实体或推断机床实际用料。CH04-T002保持IN_PROGRESS。
- 所在分支：main；本轮待提交和CI验收。


### CH04-T002 — 轴承钢材料族与产品形态标准扩展CI验收补录（2026-11-22）

- 内容提交：[fe04c6e7eadcd5037a6fc9f5e5b9600e8357f346](https://github.com/rexyll/cnc-knowledge/commit/fe04c6e7eadcd5037a6fc9f5e5b9600e8357f346)，所在分支：main。
- GitHub Actions Run [44987962532](https://github.com/rexyll/cnc-knowledge/actions/runs/44987962532)：success；5项单元测试全部通过；严格知识质量检查PASS（0 errors）。
- Linter统计：22章、108个Markdown文件、318条内部链接、140条实体、240条关系、139条来源；正文来源引用数量以本次workflow日志为准。
- 自动门禁验证仓库结构、数据记录、来源引用和内部链接；不验证外部URL实时可访问性、标准全文许可、修订计划后续进度或材料批次符合性。
- CH04-T002保持IN_PROGRESS；本轮仅完成轴承钢材料族/产品形态标准入口与版本关系核验，未完成牌号/性能数据库。


### CH04-T002 — 齿轮钢、淬透性结构钢与热处理标准扩展（2026-11-22）

- 新增SRC-000140～SRC-000151，基于国家标准官方目录核验齿轮钢、保证淬透性结构钢和钢件热处理标准。
- GB/T 37786-2019《数控机床用齿轮钢》及GB/T 33160-2016《风力发电用齿轮钢》均仍为现行标准；20260141-T-605《齿轮钢》修订项目正在起草，拟全部代替这两项标准。20262037-T-605《减速器用齿轮钢》是独立的新制定项目，2026-04-28下达，项目正在起草；不得与20260141修订项目混为一谈。
- GB/T 5216-2014《保证淬透性结构钢》仍为现行版；20260929-T-605修订计划拟全部代替本版。未获得新版正式发布信息前，不提前切换现行版本。
- 更新20251191-T-605《渗碳轴承钢》修订计划状态为官方目录显示“正在批准”，拟全部代替GB/T 3203-2016《渗碳轴承钢》和GB/T 33161-2016《汽车轴承用渗碳钢》。两项旧版在官方目录中仍标记现行，故保留当前版本状态。
- 新增热处理工艺标准入口：GB/T 34889-2017《钢件的渗碳与碳氮共渗淬火回火》、GB/T 34882-2017《钢铁件的感应淬火与回火》、GB/T 16924-2008《钢件的淬火与回火》。其中20251401-T-469修订计划官方目录显示正在批准，拟全部代替GB/T 16924-2008。
- 更新材料数据库2.8节和标准映射CSV，明确齿轮钢产品标准、淬透性钢种标准、热处理工艺标准、修订项目之间的边界；更新CH04 TaskPlan、章节README、资源README、根TaskPlan。
- 官方来源：GB/T 37786-2019（https://std.samr.gov.cn/gb/search/gbDetailed?id=YPRlHxPZwQs%3D&mode=p）；GB/T 33160-2016（https://std.samr.gov.cn/gb/search/gbDetailed?id=71F772D81749D3A7E05397BE0A0AB82A）；20260141-T-605（https://std.samr.gov.cn/gb/search/gbDetailed?id=49FD1852C812C31FE06397BE0A0A1304）；20262037-T-605（https://std.samr.gov.cn/gb/search/gbDetailed?id=511EEE661D8D9F8CE06397BE0A0A6C96）；GB/T 5216-2014（https://std.samr.gov.cn/gb/search/gbDetailed?id=P8OJDirzlQg%3D&mode=p）；20260929-T-605（https://std.samr.gov.cn/gb/search/gbDetailed?id=4C30F07BDC59BF1CE06397BE0A0A1DC6）；GB/T 3203-2016（https://std.samr.gov.cn/gb/search/gbDetailed?id=71F772D8156ED3A7E05397BE0A0AB82A）；GB/T 33161-2016（https://std.samr.gov.cn/gb/search/gbDetailed?id=71F772D816D0D3A7E05397BE0A0AB82A）；GB/T 34889-2017（https://std.samr.gov.cn/gb/search/gbDetailed?id=71F772D822B1D3A7E05397BE0A0AB82A）；GB/T 34882-2017（https://std.samr.gov.cn/gb/search/gbDetailed?id=xMl4lHY0Ogs%3D&mode=p）；GB/T 16924-2008（https://std.samr.gov.cn/gb/search/gbDetailed?id=q1Hv1bJztgk%3D&mode=p）；20251401-T-469（https://std.samr.gov.cn/gb/search/gbDetailed?id=3495F17D86B33675E06397BE0A0A0E61）。
- 未下载或归档标准全文/修订草案；未录入齿轮钢牌号成分、洁净度、淬透性带数值、渗碳层深度、硬度、金相组织或疲劳寿命保证值；未录入任何热处理温度/时间/介质/工艺窗口；未创建MAT实体或具体机床齿轮BOM关系。
- CH04-T002保持IN_PROGRESS；本轮仅完成标准目录入口、版本状态和对象边界核验。所在分支：main；待提交及CI验收。


### CH04-T002 — 齿轮钢、淬透性结构钢与热处理标准扩展CI验收补录（2026-11-22）

- 内容提交：[1d57d3e50efb0ddb1061fd2a366813a4ffe5d634](https://github.com/rexyll/cnc-knowledge/commit/1d57d3e50efb0ddb1061fd2a366813a4ffe5d634)，所在分支：main。
- GitHub Actions Run [44988157612](https://github.com/rexyll/cnc-knowledge/actions/runs/44988157612)：success；5项单元测试通过；知识质量严格检查通过。
- 本次CI日志中的统计以workflow实际输出为准；自动门禁不验证外部标准链接实时可用性、标准全文许可、计划后续进度或具体零件批次符合性。
- CH04-T002保持IN_PROGRESS：本轮只完成齿轮钢、淬透性结构钢、渗碳/感应/淬火回火标准目录及版本状态核验，没有取得标准全文，也未录入牌号性能值和热处理工艺参数。


### CH04-T002 — 滚珠丝杠与滚动直线导轨材料体系及可靠性标准边界（2026-11-22）

- 新增SRC-000152～SRC-000161，核验20263810-T-605《丝杠用结构钢》国家标准制定计划，以及GB/T 17587.5-2008、JB/T 13813.1～.7-2020、JB/T 7175.1-2011、JB/T 7175.2-2006、JB/T 7175.6-2015的官方目录/备案信息。
- 20263810-T-605属于2026年第七批推荐性国家标准制定项目，项目周期15个月；计划列出东北特殊钢集团、大冶特殊钢、江阴兴澄特种钢铁、南京工艺装备制造有限公司、陕西汉江机床有限公司和冶金工业信息标准研究院等参与单位。计划信息不代表标准已发布、已进入某个具体技术阶段或某厂商已采用特定材料。
- 在材料数据库新增2.9节和2.10节，分别定义丝杠轴、螺母、滚动体、导轨、滑块的材料数据采集边界，并区分钢材/材料标准、部件产品标准、功能可靠性、精度保持性、额定载荷和疲劳寿命试验标准。
- 更新材料标准映射CSV、CH04章节README、资源README、章节TaskPlan和根TaskPlan。未下载标准全文或计划草案；未录入具体牌号、成分、硬度、渗层深度、疲劳寿命或热处理工艺数值；未创建MAT实体或机床实际BOM关系。
- 所在分支：main。内容提交SHA和CI结果待补录；CH04-T002保持IN_PROGRESS。


### CH04-T002 — 滚珠丝杠与滚动直线导轨标准扩展CI验收补录（2026-11-22）

- 内容提交：[bb23ba01190f33ddb2fc94154666f2f3ac97dd3c](https://github.com/rexyll/cnc-knowledge/commit/bb23ba01190f33ddb2fc94154666f2f3ac97dd3c)，所在分支：main。
- GitHub Actions Run [44988480508](https://github.com/rexyll/cnc-knowledge/actions/runs/44988480508)：success；5项单元测试全部通过；严格知识质量检查PASS（0 errors）。
- Linter统计：22章、108个Markdown文件、319条内部链接、140条实体、240条关系、161条来源、331处正文来源引用。
- 本次CI验证仓库结构、来源记录Schema、数据命名空间、正文来源引用及内部链接；不验证标准全文许可、计划草案内容、材料性能实测或具体机床BOM。
- CH04-T002保持IN_PROGRESS；本轮仅完成标准计划/目录元数据与数据边界，不代表丝杠/导轨材料牌号及性能数据库已完成。


### CH04-T002 — 滚动功能部件性能试验与制造工艺证据链扩展（2026-11-22）

- 新增SRC-000162～SRC-000169，依据国家市场监督管理总局/国家标准化管理委员会行业标准目录，补充JB/T 13813.3/.5-2020、JB/T 10890.1/.2-2020、JB/T 13814～13817-2020。目录级信息支持标准身份、现行状态、发布日期/实施日期和对象范围；未取得标准全文，不提取具体试验参数或验收限值。
- 新增SRC-000170：T/ZZB 3824-2024《汽车制动用滚珠丝杠副》。公开文本明确限定汽车制动用途，给出该特定产品的材料、钢球、热处理装备和滚道表面硬度要求，并将寿命试验指向JB/T 13813.6。仅用作产品规范如何连接材料/工艺/成品试验的限定案例，不推广为数控机床通用要求或OEM BOM事实；未复制或归档PDF。
- 材料数据库新增2.11节，定义材料批次、零件批次和部件总成试验三层证据链；细化原材料、毛坯预加工、热处理、精密磨削、清洗装配、成品验证的数据采集字段。无制造商/工厂工艺文件时，不推断具体磨削参数和热处理窗口。
- 更新材料标准映射CSV、章节TaskPlan、章节README、资源README及根TaskPlan。所在分支：main；本轮未下载/归档标准全文、草案或团体标准PDF；未录入通用牌号性能/工艺数值；未创建MAT实体或OEM BOM关系。内容提交和CI结果待补录。


### CH04-T002 — 滚动功能部件性能试验与制造工艺证据链扩展CI验收补录（2026-11-22）

- 内容提交：[85ec94696b1f0bfcc8b1796c35dbeedad3c5808d](https://github.com/rexyll/cnc-knowledge/commit/85ec94696b1f0bfcc8b1796c35dbeedad3c5808d)，所在分支：main。
- GitHub Actions Run [44988991771](https://github.com/rexyll/cnc-knowledge/actions/runs/44988991771)：success；5项单元测试全部通过；严格知识质量检查PASS（0 errors）。
- Linter统计：22章、108个Markdown文件、320条内部链接、140条实体、240条关系、170条来源、340处正文来源引用。
- 自动质量门禁验证仓库结构、来源记录Schema、数据命名空间、正文来源引用及内部链接；不验证标准全文授权、外部URL长期可用性、标准技术全文或实际材料/部件批次符合性。
- 本轮未下载/归档标准全文或团体标准PDF，未录入通用丝杠/导轨材料牌号和工艺参数，未创建MAT实体或机床OEM BOM关系；CH04-T002保持IN_PROGRESS。


### CH04-T002 — 滚动体产品标准与残余应力测量方法扩展（2026-11-22）

- 新增SRC-000171～SRC-000178：GB/T 308.1-2013成品钢球、GB/T 309-2021钢制滚针、GB/T 25767-2025圆锥滚子、GB/T 41103-2022陶瓷圆柱滚子GPS、ISO 683-17:2023球/滚子轴承钢材料交付、ISO 3290-1:2014成品钢球，以及GB/T 45597-2025和GB/T 7704-2017残余应力X射线测量方法。
- 重点版本修正：GB/T 25767-2025于2025-10-31发布、2026-02-01实施，全部代替GB/T 25767-2010；GB/T 309-2021现行；GB/T 308.1-2013于2025-07-01复审继续有效。成品滚动体标准与轴承钢材料交付标准分别建档，不互相替代。
- ISO 683-17:2023覆盖整体淬硬、渗碳、感应淬火、不锈和高温轴承钢五类锻轧材料交付要求；仅作为国际标准入口，不推断其与GB/T等同或特定丝杠/导轨实际用料。ISO 3290-1:2014官方页面显示2025年复审确认继续有效。
- 残余应力方法：GB/T 45597-2025（短波长X射线衍射法）现行，2025-11-01实施；GB/T 7704-2017现行，修订计划20251450-T-469处于批准阶段。方法标准不提供滚动体/滚道产品验收阈值，曲面测量需验证光斑、入射几何、测点、有效深度和不确定度。
- 明确ISO 14104:2017为齿轮磨削后表面回火蚀刻检查方法，不自动适用于钢球、滚子或滚珠丝杠滚道；后续若要扩展须有产品规范、工艺验证及方法适用性证据。本轮未将其作为滚动体有效标准关系。
- 更新材料数据库2.12节、材料标准映射CSV、CH04 TaskPlan、章节README、资源README和根TaskPlan。未录入材料牌号性能、硬度/组织限值、磨削参数、残余应力阈值或寿命保证值；未创建滚动体MAT实体或OEM BOM关系；未下载/归档标准全文。CH04-T002保持IN_PROGRESS。
- 所在分支：main；提交与CI验收待补录。

### CH04-T002 — CI失败修复与ISO 14104范围来源补录（2026-11-22）

- 首次内容提交 `ad927646444a4f701dca5301b6466f0f41289ab5` 的CI Run [44989186733](https://github.com/rexyll/cnc-knowledge/actions/runs/44989186733) 中5/5单元测试通过，但strict lint报错：材料数据库引用了尚未登记的SRC-000179（1 error）。
- 已补录SRC-000179：ISO 14104:2017官方标准页面，确认其范围为齿轮磨削后化学蚀刻检查，2022年复审继续有效；同步修正正文引用和章节计划。该标准不被推广为滚动体/滚道通用方法。
- 修复提交和后续CI验收待补录。此前提交内容其余来源记录及结构检查均被linter识别，来源记录数178、正文引用346、内部链接321。

### CH04-T002 — 滚动体产品标准与残余应力测量CI验收补录（2026-11-22）

- 首次内容提交 `ad927646444a4f701dca5301b6466f0f41289ab5` 的Run [44989186733](https://github.com/rexyll/cnc-knowledge/actions/runs/44989186733) 因正文引用SRC-000179但来源文件尚未登记而失败；5/5单元测试通过，strict lint 1 error。
- 修复提交 `eb6d0c77c494be7545b6e2b3c84c17efd1199d93` 补录SRC-000179（ISO 14104:2017官方范围页面）并修复引用；Run [44989218260](https://github.com/rexyll/cnc-knowledge/actions/runs/44989218260) success。
- 修复后CI：5/5单元测试通过；strict lint PASS，0 errors；22章、108个Markdown文件、321条内部链接、140个实体、240条关系、179条来源、346处正文来源引用。
- 本轮只增加滚动体标准元数据和方法边界，不录入具体材料性能/验收数值、残余应力阈值或磨削参数；未归档标准全文；CH04-T002保持IN_PROGRESS。


### CH04-T002 — 轴承钢洁净度、夹杂物评价与滚动体表面完整性（2026-11-22）

- 新增来源SRC-000180～SRC-000185：GB/T 10561-2023、ISO 4967:2026、SAE ARP4462C、NSK 2026年10月钢材洁净度技术综述、ISO/AWI 14104第4版在研项目、AKS钢球制造流程官网。
- 核验GB/T 10561-2023现行，2023-12-01实施，全部代替GB/T 10561-2005，修改采用ISO 4967:2013；ISO 4967:2026于2026-05-29发布并替代ISO 4967:2013。明确GB/T 10561-2023不能标记为等同/自动采用ISO 4967:2026。
- 记录夹杂物显微检验、图像分析、BN检测和化学蚀刻的不同对象/能力边界；方法标准不等于采购验收等级。ISO/AWI 14104第4版目前处于20.00在研阶段，不能作为现行标准使用。
- NSK技术综述用于说明夹杂物诱发剥落的机制，作为厂商技术证据，不外推寿命增益或其他厂商内部判据；AKS流程仅作为钢球制造商工艺示例，不推断机床OEM实际工艺。
- 更新材料数据库2.13节、标准映射CSV、CH04章节TaskPlan、章节README、资源README和根TaskPlan；新增来源JSON。未下载/归档标准全文、厂商网页图片或其他受版权限制资料；未录入夹杂物等级、硬度、磨削烧伤阈值、热处理/磨削参数或实际BOM。CH04-T002保持IN_PROGRESS。
- 所在分支：main；提交与CI验收待补录。


### CH04-T002 — 轴承钢洁净度、夹杂物评价与滚动体表面完整性CI验收补录（2026-11-22）

- 内容提交：[`9fd0c3bfb4d3887aa636cb0991a3192ead2dc794`](https://github.com/rexyll/cnc-knowledge/commit/9fd0c3bfb4d3887aa636cb0991a3192ead2dc794)，所在分支：main。
- GitHub Actions Run [44989417545](https://github.com/rexyll/cnc-knowledge/actions/runs/44989417545)：success；5/5单元测试通过；严格知识质量检查PASS（0 errors）。
- Linter统计：22章、108个Markdown文件、322条内部链接、140个实体、240条关系、185条来源、358处正文来源引用。
- 自动门禁验证仓库结构、来源记录Schema、实体/关系命名空间、正文来源引用及内部链接；不验证外部URL长期可用性、标准全文许可、材料批次符合性或检测方法在具体零件几何上的适用性。
- CH04-T002保持IN_PROGRESS；本轮仅完成洁净度/夹杂物方法目录、磨削烧伤检测方法边界和制造商工艺示例，不代表牌号性能数据库或零件工艺数据库完成。


### CH04-T003 — 滚针、圆柱滚子与圆锥滚子制造工艺首轮整理（2026-11-22）

- 新增正文：`docs/04-components-materials-and-manufacturing/manufacturing-processes.md`，首轮整理滚针、圆柱滚子和圆锥滚子的工艺阶段、成品标准边界、工序质量门、表面完整性检测、尺寸分组和批次追溯。
- 新增SRC-000186～SRC-000190：ISO 12297-1:2021钢制圆柱滚子几何标准；ISO 3096:2018钢制滚针几何标准；ACB公开圆柱滚子工艺流程图；Timken无锡工厂制造能力介绍；Timken圆柱滚子产品目录。厂商材料均限定为特定流程/工厂/产品族声明，不推断为行业统一路线。
- 更新材料数据库2.14节、材料标准映射CSV、CH04章节TaskPlan、章节README、资源README、根TaskPlan。
- 未下载/归档ISO或厂商受版权保护PDF；未录入通用热处理参数、硬度、磨削参数、粗糙度、烧伤阈值或寿命数值；未创建无证据PART/MAT/BOM/供应商关系。
- CH04-T003状态：IN_PROGRESS；后续仍需研究丝杠、导轨、主轴、铸件等关键零件的具体制造和检验流程。
- 所在分支：main；内容提交与CI验收待补录。


### CH04-T003 — 滚动体制造工艺首轮整理CI验收补录（2026-11-22）

- 内容提交：[`72447f664afb2ead6d3916fe65ef45737098d6c9`](https://github.com/rexyll/cnc-knowledge/commit/72447f664afb2ead6d3916fe65ef45737098d6c9)，所在分支：main。
- 完成时间：2026-11-22T13:29:00+08:00（Asia/Shanghai）。
- GitHub Actions [Run 44989573468](https://github.com/rexyll/cnc-knowledge/actions/runs/44989573468)：success；5/5单元测试通过；严格知识质量检查PASS（0 errors）。
- Linter统计：22章、109个Markdown文件、323条内部链接、140个实体、240条关系、190条来源、378处正文来源引用。
- 自动门禁验证结构、来源Schema、正文来源引用和内部链接；不验证外部URL长期可用性、标准全文许可、供应商工艺真实性/完整性或具体零件工艺参数。
- CH04-T003保持IN_PROGRESS；本轮仅完成滚动体工艺首轮整理，不代表其他关键零件制造工艺已覆盖。


### CH04-T003 — 滚珠丝杠副与滚动直线导轨副制造工艺扩展（2026-11-22）

- 扩展 `docs/04-components-materials-and-manufacturing/manufacturing-processes.md`，新增滚珠丝杠轴滚道滚轧/旋风加工/磨削候选路线、热处理和热后精加工、螺母/循环结构、预紧与总成质量门；新增滚动直线导轨/滑块工艺阶段、滚动体配组、预压、单件与安装后精度边界、供应商质量审核字段。
- 新增SRC-000191～SRC-000193：ISO 3408-1:2006术语/标记、ISO 3408-2:2021公制尺寸/安装接口、ISO 3408-3:2006验收条件/验收试验。ISO官方目录显示三项标准当前有效并在2026年复审确认。
- 新增SRC-000194～SRC-000197：NSK滚珠丝杠质量技术资料、SCHNEEBERGER滚珠丝杠制造方法、THK LM Guide产品设计资料、IMTEK直线导轨工艺二级文章。厂商资料限定为各自产品/声明；二级文章仅用于工序识别，不作为验收规范。
- 更新材料标准映射CSV、CH04章节README、资源README、CH04 TaskPlan和根TaskPlan。
- 未下载/归档标准全文或厂商PDF；未录入通用材料牌号、热处理/磨削参数、硬度/硬化层深度、导程/直线度验收限值、预紧转矩、刚度或寿命数值；未创建无证据PART/MAT/BOM/供应商兼容关系。CH04-T003保持IN_PROGRESS。
- 所在分支：main；提交和CI验收待补录。


### CH04-T003 — 滚珠丝杠副与滚动直线导轨副制造工艺扩展CI验收补录（2026-11-22）

- 内容提交 `c06a5f469f2f1fc40e94e926c7d86e95f3b6a2fc` 的GitHub Actions Run [44989774167](https://github.com/rexyll/cnc-knowledge/actions/runs/44989774167) 首次失败：5/5单元测试通过，strict lint发现SRC-000197的`source_type`和`evidence_kind`不在Schema枚举中，2 errors。
- 修复提交：[`81257307f526db3f0085ca39c41f57c73c190b48`](https://github.com/rexyll/cnc-knowledge/commit/81257307f526db3f0085ca39c41f57c73c190b48)，将SRC-000197更正为`third_party_article` / `secondary_summary`，并修正文中误将SCHNEEBERGER资料写成KSK来源的描述。
- GitHub Actions [Run 44989817497](https://github.com/rexyll/cnc-knowledge/actions/runs/44989817497)：success；5/5单元测试通过；strict lint PASS（0 errors）。统计：22章、109个Markdown文件、324条内部链接、140条实体、240条关系、197条来源、393处正文来源引用。
- 本轮CI只验证结构、来源Schema、引用与内部链接，不验证外部URL长期可用性、标准全文许可、工艺参数或实际零件批次符合性。CH04-T003保持IN_PROGRESS。


### CH04-T003 — 数控机床主轴制造工艺与精度形成（2026-11-22）

- 新增 `manufacturing-processes.md` 第13节：主轴总成对象分层、轴芯毛坯/粗加工/热处理/精磨数据采集框架、轴承配合与预紧、转子平衡、主轴总成装配质量门、空载运行/功能/热稳定试验，以及整机主轴精度测试标准边界。
- 新增SRC-000198～SRC-000204：ISO 230-7:2015、GB/T 17421.7-2016、修订计划20254003-T-604、ISO 230-3:2020、GB/T 17421.3-2009、修订计划20254203-T-604、ISO 21940-11:2016及Amd 1:2022。特别标注GB/T 17421.7-2016采标ISO 230-7:2006、GB/T 17421.3-2009采标ISO 230-3:2001；两项国内修订计划处于批准阶段，未发布新版。
- 新增SRC-000205～SRC-000209：SKF超精密轴承选型/目录、GMN主轴试验台/服务资料、Makino特定机型主轴技术声明。厂商证据限定于各自产品/服务，不外推为行业统一工艺或其他OEM的BOM。
- 新增 `resouces/04-components-materials-and-manufacturing/manufacturing-standard-map.csv`，将转子平衡、主轴回转轴线几何和热效应试验与主轴制造工艺分开管理。
- 未录入通用材料牌号、热处理参数、轴承配合/预紧量、平衡等级/残余不平衡、振动限值、温升/热漂移或跳动公差；未下载/归档受版权保护PDF；未创建无证据OEM BOM/兼容关系。CH04-T003保持IN_PROGRESS；CI验收待补录。


### CH04-T003 — 主轴制造专题首轮CI验收（2026-11-22）

- 内容提交 [`7e4206f07c1166e59bb9bf46f77ffe9a4797ef82`](https://github.com/rexyll/cnc-knowledge/commit/7e4206f07c1166e59bb9bf46f77ffe9a4797ef82)，GitHub Actions [Run 44990046215](https://github.com/rexyll/cnc-knowledge/actions/runs/44990046215)：success；5/5单元测试通过；strict lint PASS（0 errors）。
- Linter统计：22章、109个Markdown文件、325条内部链接、140个实体、240条关系、209条来源、407处正文来源引用。
- 验收后补充SRC-000210（GB/T 17421.1-2023）并修正SRC-000203官方计划URL和采标说明；这些补录改动在本条历史补录提交中，需独立确认CI。
- CI不验证外部链接长期可用性、标准全文版权、主轴真实材料/工艺批次或制造商测试规范的普遍适用性。CH04-T003保持IN_PROGRESS。


### CH04-T003 — 主轴专题来源补录CI验收（2026-11-22）

- 补录提交 [`ac6802d97e6838c2dcb36016a1e4cd6271268c6b`](https://github.com/rexyll/cnc-knowledge/commit/ac6802d97e6838c2dcb36016a1e4cd6271268c6b) 修正SRC-000203国家标准计划官方URL与采标信息，补充SRC-000210（GB/T 17421.1-2023）及主轴几何检验映射。
- GitHub Actions [Run 44990089036](https://github.com/rexyll/cnc-knowledge/actions/runs/44990089036)：success；5/5单元测试通过；strict lint PASS（0 errors）。
- 最终统计：22章、109个Markdown文件、325条内部链接、140条实体、240条关系、210条来源、409处正文来源引用。
- 当前远程分支仅`main`。CI不验证标准全文版权、外部链接长期可用性、实际主轴工艺或供应商型号/BOM。CH04-T003保持IN_PROGRESS。


### CH04-T003 — 主轴轴承安装、振动诊断与热误差专题CI验收（2026-11-22）

- 内容提交 [`cd569a764cfd6b543c1715f1d3c9b55d0d4f0167`](https://github.com/rexyll/cnc-knowledge/commit/cd569a764cfd6b543c1715f1d3c9b55d0d4f0167)，所在分支：main。
- GitHub Actions [Run 44990582497](https://github.com/rexyll/cnc-knowledge/actions/runs/44990582497)：success；5/5单元测试通过；strict lint PASS（0 errors）。
- Linter统计：22章、109个Markdown文件、327条内部链接、140个实体、240条关系、212条来源、416处正文来源引用。
- 新增SRC-000211～SRC-000212并更新制造工艺正文、主轴标准映射和章节/根计划。CI验证结构、来源Schema、正文引用和内部链接；不验证标准全文版权、外部链接长期可用性、实际主轴型号装配工艺或试验验收限值。
- 本轮未下载/归档ISO标准全文或草案；未录入通用轴承安装温度、压装力、配合过盈量、预紧力、振动限值、热稳态时间、热漂移限值或平衡等级。CH04-T003保持IN_PROGRESS。


### CH04-T003 — 主轴电机与冷却系统专题CI验收（2026-11-22）

- 内容提交 [`342a3e33d8a02f34f486001d29b7b4a2de66d76c`](https://github.com/rexyll/cnc-knowledge/commit/342a3e33d8a02f34f486001d29b7b4a2de66d76c)，所在分支：main。
- GitHub Actions [Run 44990751346](https://github.com/rexyll/cnc-knowledge/actions/runs/44990751346)：success；5/5单元测试通过；strict lint PASS（0 errors）。
- Linter统计：22章、109个Markdown文件、329条内部链接、140个实体、240条关系、219条来源、429处正文来源引用。
- 本轮新增SRC-000213～SRC-000219，覆盖GB/T 755-2025、IEC 60034-1:2026、IEC 60034-6:1991、IEC 60034-2-3:2024、IEC 60034-11:2020、IEC 60034-14:2026及GMN冷却示例。
- CI仅验证结构、来源Schema、正文引用和内部链接；不验证外部URL长期可用性、标准全文版权、型号级电机/冷却参数或实际OEM制造工艺。未下载/归档受版权保护标准/厂商PDF，CH04-T003保持IN_PROGRESS。


### CH04-T003 — 主轴驱动链、反馈传感器、动态性能与整机联调（2026-11-22）

- 制造工艺正文新增第25～29节：驱动器—电机—编码器—CNC接口和PWM/EMC审查；主轴编码器、温度/振动/位移/夹紧/冷却润滑传感器；转速跟随、加减速、恒转矩/恒功率/弱磁区和负载响应；主轴与刀库、夹刀、冷却润滑及安全联锁的整机联调；电机/PDS/主轴总成/机床整机分层验证矩阵。
- 新增SRC-000220～SRC-000225：IEC 61800-3:2022及2025勘误、IEC 61800-5-1:2022及2025-12勘误、IEC 61800-9-2:2023及AMD1:2025整合版、HEIDENHAIN EnDat/EnDat 2.2接口资料、Siemens SINAMICS V6.6工程手册。厂商接口和安装资料均限定于具体协议/产品系列。
- 更新主轴制造/验收标准映射CSV，增加PDS/机床EMC、PDS安全、驱动系统能效、编码器接口和厂商安装示例；同步更新CH04 README、资源README、章节TaskPlan和根TaskPlan。
- 未下载/归档受版权保护标准或Siemens PDF；未录入通用驱动匹配值、PWM滤波参数、电缆长度、编码器采样频率、传感器阈值、动态性能验收值或安全响应时间。CH04-T003保持IN_PROGRESS；提交和CI验收待补录。


### CH04-T003 — 主轴驱动链专题CI验收补录（2026-11-22）

- 内容提交：[`f85b1139c8283a53207e2cb8dbb24f3c67be9697`](https://github.com/rexyll/cnc-knowledge/commit/f85b1139c8283a53207e2cb8dbb24f3c67be9697)，所在分支：main。
- GitHub Actions [Run 44991135602](https://github.com/rexyll/cnc-knowledge/actions/runs/44991135602)：success；5/5单元测试通过；strict lint PASS（0 errors）。
- Linter统计：22章、109个Markdown文件、331条内部链接、140条实体、240条关系、225条来源、437处正文来源引用。
- CI验证仓库结构、来源记录Schema、实体/关系命名空间、正文来源引用和内部链接；不验证外部URL长期可用性、标准全文许可、具体型号驱动兼容性、EMC实测、动态性能验收值或真实机床安全验证。
- 本轮未下载/归档受版权保护标准全文或Siemens手册；未录入通用驱动匹配数值、PWM滤波参数、电缆长度、编码器采样频率、传感器阈值、动态性能验收值或安全响应时间。CH04-T003保持IN_PROGRESS。


### CH04-T003 — 结构铸件、焊接结构件与钣金件制造工艺（2026-11-22）

- 制造工艺正文新增第30～33节，覆盖床身/立柱/横梁/工作台等铸铁结构件对象边界、灰铸铁和球墨铸铁试样条件、铸造工艺质量门、铸件公差/加工余量/基准加工、铸件NDT；焊接结构件材料/坡口/WPS/工艺评定/变形控制/焊后处理/机加工；钣金件热切割/折弯/连接/表面处理与整机装配检查。
- 新增SRC-000226～SRC-000242：ISO 8062-3:2023、ISO 185:2020、ISO 1083:2018、ISO 3834-2:2021、ISO 5817:2023、ISO 13920:2023、ISO 17635:2025、ISO 4993:2024、ISO 4986:2020、ISO 17640:2018、ISO 17636-1/-2、ISO 9013:2017+Amd1:2024、ISO 15614-1:2017+Amd1:2019及其Edition 3 FDIS、ISO 4992-1:2020。
- 关键边界：标准试样不等于大型铸件各截面性能；ISO 4992-1只覆盖铁素体钢铸件，不套用于灰铸铁/球墨铸铁；ISO 5817焊缝质量等级不等于NDT验收等级；新版FDIS不等于已发布标准。未取得具体机床OEM图纸/工艺卡，不推断实际材料、铸造路线、供应商或焊接参数。
- 未下载/归档受版权保护标准全文或厂商工艺文件；未录入通用铸件壁厚/加工余量、浇注温度、热处理参数、焊接参数/去应力温度、钣金折弯半径或涂层厚度。提交和CI验收待补录。


### CH04-T003 — 结构铸件/焊接/钣金专题CI验收补录（2026-11-22）

- 内容提交：[`bfe25aebb93735a185a1a17b0cc021188dc2c944`](https://github.com/rexyll/cnc-knowledge/commit/bfe25aebb93735a185a1a17b0cc021188dc2c944)，所在分支：main。
- GitHub Actions [Run 44993011321](https://github.com/rexyll/cnc-knowledge/actions/runs/44993011321)：success；5/5单元测试通过；strict lint PASS（0 errors）。
- Linter统计：22章、109个Markdown文件、332条内部链接、140条实体、240条关系、242条来源、458处正文来源引用。
- 本轮新增SRC-000226～SRC-000242并更新制造工艺正文、标准映射CSV、章节README、资源README、章节/根TaskPlan。CI验证仓库结构、来源Schema、实体/关系命名空间、正文来源引用和内部链接；不验证标准全文版权、外部URL长期可用性、铸件实物性能、NDT检测能力或供应商工艺真实性。
- 未下载/归档受版权保护标准全文；未录入通用铸件壁厚/余量/浇注温度、热处理窗口、焊接参数/去应力温度、钣金折弯半径或涂层厚度。CH04-T003保持IN_PROGRESS。


## CH04-T003 跨章节职责与一致性审查第一轮（2026-11-22）

- **任务：** CH04制造工艺与跨章节知识责任边界/引用审查（桌面审查第一轮）。
- **分支：** main；审查基线 `af75401d1963176ae65bfb059ea4f175fd7c7e64`。
- **交付：** `docs/04-components-materials-and-manufacturing/manufacturing-cross-chapter-review.md`，建立CH03、CH05、CH06～CH10、CH13～CH20的职责矩阵、边界声明、交叉引用路径和后续逐文审查项。
- **结果：** 初步识别制造工艺/整机结构/测量验收/装配安装/维护/故障诊断/产品供应链/BOM的知识主归属，提出避免重复维护和无证据推断的链接规则。
- **限制：** 当前只完成第一轮入口和部分正文审查，不声称所有相关章节已逐段检查；无型号级BOM/图纸/工艺卡/现场数据，未建立实际零件或制造关系。
- **验收：** 文档链接和质量门禁待CI。
