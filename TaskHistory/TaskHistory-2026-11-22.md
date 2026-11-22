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

- CH02覆盖度调整为2级foundational：2篇文章、23个主归属实体（14 MTYPE + 7 MACHINE + 2 KNOW）、60条关系（含14条新文章索引边）、19条去重来源、0项资源文件。
- 覆盖统计按实体主归属、关系关联及文章/实体引用的去重SRC计算；未把型号未核验参数填入实体。
- 所在分支：main。完成时间：2026-11-22T11:20:00+08:00。主要内容提交SHA：a80017ec5b17c57d534e5907fe7ff5229bae4088；GitHub Actions Run #18（44978860961）success，5项单元测试通过，严格知识检查PASS（0 errors）。最终目录索引与来源权利状态校正由后续提交补充。
