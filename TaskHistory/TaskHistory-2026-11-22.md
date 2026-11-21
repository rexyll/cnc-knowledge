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
