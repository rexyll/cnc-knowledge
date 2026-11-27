# 17. 操作、维护与维修 — 章节任务计划

**章节编号：** CH17  
**英文名称：** Operation, Maintenance and Repair  
**对应正文：** `docs/17-operation-maintenance-and-repair/`  
**资源归档：** `resouces/17-operation-maintenance-and-repair/`  
**章节范围：** 机床操作规范、开停机、加工准备、日常保养、计划维护、零部件拆装更换、备件策略和维修记录。

> 本文件只拆解本章知识建设任务，统一继承根目录 `TaskPlan.md` 的全部 Guide、Limit、质量标准、资源规则、版权要求和安全要求。

## 1. 章节目标

建立本章节系统化、可验证、可检索且能够与其他知识板块关联的技术资料。按“概念分类—原理结构—参数与型号—工程应用—测试/维护—案例”逐步完善，避免只堆积无上下文的链接或参数表。

## 2. 覆盖范围

- 操作面板、运行模式、程序装载、工件/刀具准备和状态监控
- 每日/每周/每月/年度维护、润滑、冷却液、过滤和清洁
- 部件拆卸、更换、复装、校准、参数备份和复验
- 备件管理、维修工单、保养记录、维护周期和寿命管理

## 3. 任务节点

### CH17-T001 — 建立操作知识框架

- **目标：** 按典型机床类型整理操作流程、状态模式、准备检查和常见操作风险。
- **工作范围：** 操作面板、运行模式、程序装载、工件/刀具准备和状态监控；每日/每周/每月/年度维护、润滑、冷却液、过滤和清洁；部件拆卸、更换、复装、校准、参数备份和复验；备件管理、维修工单、保养记录、维护周期和寿命管理。
- **交付物：** 操作说明目录、开停机/准备检查表。
- **验收标准：** 说明适用机型和控制系统，安全动作有制造商依据。
- **依赖：** CH02、CH07
- **状态：** `IN_PROGRESS`

### CH17-T002 — 建立计划维护体系

- **目标：** 整理维护项目、周期、耗材、检查方法和记录字段。
- **工作范围：** 操作面板、运行模式、程序装载、工件/刀具准备和状态监控；每日/每周/每月/年度维护、润滑、冷却液、过滤和清洁；部件拆卸、更换、复装、校准、参数备份和复验；备件管理、维修工单、保养记录、维护周期和寿命管理。
- **交付物：** 维护矩阵、保养卡、耗材清单。
- **验收标准：** 周期和限值以制造商资料为准，经验建议明确标识。
- **依赖：** CH03、CH04、CH06、CH08
- **状态：** `IN_PROGRESS`

### CH17-T003 — 编制零部件拆装更换专题

- **目标：** 针对可公开的关键部件整理拆装前提、工具、步骤、复装检查和校准。
- **工作范围：** 操作面板、运行模式、程序装载、工件/刀具准备和状态监控；每日/每周/每月/年度维护、润滑、冷却液、过滤和清洁；部件拆卸、更换、复装、校准、参数备份和复验；备件管理、维修工单、保养记录、维护周期和寿命管理。
- **交付物：** 更换指导文档、工具清单、检查点和资源附件。
- **验收标准：** 仅整理具备来源且适合授权人员执行的指导；危险作业明确资质、隔离和安全边界。
- **依赖：** CH04、CH16
- **状态：** `IN_PROGRESS`

### CH17-T004 — 建立维修和备件闭环

- **目标：** 设计维修记录、备件替换、复验、寿命和故障反馈流程。
- **工作范围：** 操作面板、运行模式、程序装载、工件/刀具准备和状态监控；每日/每周/每月/年度维护、润滑、冷却液、过滤和清洁；部件拆卸、更换、复装、校准、参数备份和复验；备件管理、维修工单、保养记录、维护周期和寿命管理。
- **交付物：** 备件主数据、关键度评估、库存/补货、替代件审批、生命周期/停产风险、维修消耗反馈模板；备件管理和跨系统追溯正文。
- **验收标准：** 更换件、参数和复验结果可追踪至设备实例、BOM/部件主数据、库存批次和工单；替代审批有明确适用范围、工程/质量证据及复验记录；库存和停产决策有可追溯数据来源。
- **依赖：** 本章任务1-3、CH18、CH19、CH20
- **状态：** `IN_PROGRESS`


## 4. 章节级交付物

- 章节分类树、术语和知识条目索引。
- 经过来源核验的专题文档及必要的参数/接口/型号数据。
- 与本章相关的图片、动图和完整资料资源，以及资源索引。
- 与机型、零部件、材料、厂商、标准、BOM、算法或故障的跨章节关联。
- 未解决问题、待核验数据和后续研究建议。

## 5. 章节完成验收

本章节只有在任务节点均完成或明确标记延后/不适用，并且至少完成以下检查后，才可整体标记完成：知识覆盖与边界清楚；关键结论有可追溯来源；参数具备单位、版本和适用条件；资源归档和引用正确；跨章节关联建立；安全、版权及保密检查通过；遗留问题有记录。


## 6. 已开展工作与当前状态（2026-11-26）

### CH17-T001 — 第一轮框架与操作准备检查

- 新增正文 docs/17-operation-maintenance-and-repair/overview.md，建立操作、操作者日常维护、计划/状态维护和专业维修边界；覆盖铣床/加工中心、车床/车削中心及特殊配置的资料检索入口。
- 新增资源模板 resouces/17-operation-maintenance-and-repair/operation-readiness-checklist.csv，包含25项设备识别、现场、防护、报警、润滑/冷却/压力系统、工装/程序、运行监视、停机、维护/维修及记录检查项；所有结果初始为NOT_ASSESSED，不包含通用数值限值或强制周期。
- 新建本章ASSET-INDEX.md，登记模板和SRC-000382～SRC-000388来源；更新章节README与资源目录README。
- 依据资料：美国OSHA 29 CFR 1910.147危险能量控制要求；ISO 16090-1:2022及其第三版工作草案目录；ISO 23125:2015目录；Haas官方手册索引、铣床安全说明和车床维护计划。法规/标准仅在其适用范围内引用；厂商资料只作对应产品族示例。
- **未完成项：** 当前没有指定目标机床型号、控制系统版本、配置和受控操作/维护手册，因此没有编写型号级开机步骤、维护周期、润滑剂/冷却液规格、压力/扭矩/温度限值，也未将模板标记为可直接执行的SOP。
- **状态：** CH17-T001保持IN_PROGRESS；下一步需选定至少一个具体机床系列并取得现行官方操作/维护手册，再将检查项映射到具体条款、周期和判定标准。CH17-T002～T004保持TODO。


## 6.2 CH17-T001 维修工作流与记录闭环扩展（2026-11-25）

- 新增正文 `docs/17-operation-maintenance-and-repair/repair-workflow-and-records.md`，明确维修边界、分类、报修证据、风险评估/危险能量控制、OEM文件和人员授权、诊断接口、维修变更追溯、维修后复验、放行与工单关闭。
- 新增 `repair-work-order-template.csv` 与 `post-repair-verification-matrix.csv` 两份原创空白模板；与既有25项开机准备表一起登记为CH17资源实体。
- 新增来源SRC-000389（ISO 17359:2018状态监测计划一般指南）和SRC-000390（ISO 230-2:2014/Amd 1:2016单个数控轴定位准确度与重复定位测试方法入口）。两项均只保存官方目录元数据与链接，不复制标准全文。
- 本文将具体报警/根因诊断交由CH18；不提供任何型号级拆装步骤、能量隔离操作步骤、参数、维护周期或统一验收阈值。维修后的测试范围需按维修影响分析、OEM文件和合同/适用标准确定。
- **未完成项：** 尚无目标机床型号、序列范围、CNC/PLC软件版本及受控OEM服务手册；未形成型号级维修SOP、部件兼容替换表、真实工单或实测复验报告。
- **CI验收：** [GitHub Actions Run 45546453542](https://github.com/rexyll/cnc-knowledge/actions/runs/45546453542) 两个Job均success；知识库单元测试5/5、strict lint 0 errors。CH12数值资源回归测试143/143通过，但不代表CH17现场或实机维修验证。
- **状态：** CH17-T001继续IN_PROGRESS；CH17-T002～T004保持TODO。此切片只完成通用维修管理框架和记录模板，不代表本章维修研究完成。


## 6.3 CH17-T002 计划维护框架与模板第一轮（2026-11-25）

- 新增正文 `docs/17-operation-maintenance-and-repair/maintenance-management-system.md`，建立维护策略分类、日历/运行小时/循环/状态/事件触发、周期来源优先级、到期/延期管理、子系统任务分类、状态监测、保养记录和耗材追溯方法。
- 新增三份原创空白CSV：维护任务矩阵、维护卡、维护耗材登记；另新增Haas车床RD0035（Revision A-04/2026）精选维护项目实例CSV。四份资源全部归档于本章 `resouces/` 并登记ASSET-000011～ASSET-000014。
- 更新SRC-000388的官方维护页URL、文档修订和章节定位；保留SRC-000389作为状态监测通用指南入口。
- **边界：** 通用矩阵的OEM周期/阈值/规格全部留空；Haas精选实例只用于说明制造商维护计划具有产品族/配置特异性，不得推广到其他品牌或未核对的Haas机型。无用户目标机床型号，因此尚未激活具体设备维护任务。
- **未完成项：** 未取得用户目标机型手册、未建立该机型运行小时/循环计数映射、未填写具体油液/滤芯料号和储存参数，也没有真实保养记录或现场执行证据。
- **实施提交：** `ecc70ca326fccacab6ed3036fdf5802309c7bb95`；CSV字段对齐修正提交：`97340c9dfa1f6c77a5120c85c40e772b29b16eca`。
- **CI验收：** 修正后的提交 `97340c9dfa1f6c77a5120c85c40e772b29b16eca` 对应 GitHub Actions [Run 45548286906](https://github.com/rexyll/cnc-knowledge/actions/runs/45548286906) completed/success。Knowledge structure and data quality：5/5单元测试通过、`knowledge_lint --strict` 为 PASS（0 errors），检查22章、138个Markdown、450条内部链接、152条实体、240条关系、387条来源、727处来源引用和22条覆盖记录；CH12 numerical resource tests：143/143通过。该CI不代表CH17现场保养或实机验证。
- **状态：** CH17-T002保持IN_PROGRESS；待目标机型和受控OEM维护手册确定后继续型号级映射与现场流程审查。


## 6.4 CH17-T003 部件更换工作包框架第一轮（2026-11-25）

- 新增正文 docs/17-operation-maintenance-and-repair/component-replacement-work-package.md（KNOW-000023），建立单次部件更换工作包、作业前置停工点、设备/部件身份、OEM文件映射、风险与授权、拆前基线、工具量具、替代兼容性、复装记录、校准、维修后验证和放行闭环。
- 新增三份原创空白CSV资源：component-replacement-work-package-template.csv（ASSET-000015）、component-tool-and-measurement-register-template.csv（ASSET-000016）、component-interface-and-replacement-compatibility-template.csv（ASSET-000017），均归档于本章 resouces 目录。
- 内容只定义记录和审核框架；拆卸/安装顺序、吊装方法、紧固/预紧数值、介质规格、参数和验收阈值均要求引用目标机型现行OEM文件或批准工程资料。缺少关键证据时保持BLOCKED。
- **未完成项：** 用户尚未指定机床型号、序列范围、选件、控制系统版本和受控OEM服务手册；未形成任何型号级拆装步骤、部件替代批准或真实维修/校准/实机验收记录。
- **状态：** CH17-T003保持IN_PROGRESS；本轮只完成通用框架和空白模板，不表示关键部件更换研究或现场维修指导完成。

- **实施提交：** 852bf193dffc7cc3dda31ae9de7da61961267e4c；计划、索引与覆盖度同步提交：200620804124e88a7adf97f78908aabb69f8e3ff。
- **CI验收：** 实施提交Run 45551283372、同步提交Run 45551345376均completed/success；两个Run的知识结构与数据质量、CH12数值资源回归Job全部通过。此CI不表示现场或实机维修验证。


## 6.5 CH17-T003 关键部件族影响分析与复验矩阵（2026-11-25）

- 新增正文 docs/17-operation-maintenance-and-repair/component-family-impact-assessment-and-verification.md（KNOW-000024），将关键部件更换审查细化为九类部件族：主轴、伺服/编码器/驱动、滚珠丝杠/支撑轴承、直线导轨、刀库/换刀/刀塔、卡盘/夹持、液压/气动、润滑/冷却/排屑、CNC/PLC/I/O/传感器。
- 新增原创资源 component-family-impact-verification-matrix-template.csv（ASSET-000018），共57条审查项目、20列；逐项预留拆前基线、兼容性证据、OEM程序、危险能量/风险审核、复验域、验证方法、接受准则、责任专业、停工点、适用性和结果字段。
- 矩阵仅为审查提示，初始适用性/结果为TO_BE_ASSESSED/NOT_TESTED；不表示全部行均适用，不给出机型级拆装动作、吊装/扭矩/预紧参数、润滑介质或验收限值。
- **未完成项：** 尚未指定目标机床和配置，也未取得现行OEM服务文件，故没有完成型号级映射、部件替代批准、实际测量或现场/实机验证。
- **状态：** CH17-T003保持IN_PROGRESS。

- **实施提交：** 698efeecde445e2f63fba7c561c28d7f686369d8；计划/索引/覆盖度同步提交：eb296e24f92a800ac89474da3e7eda9ac719ccb4。
- **CI验收：** 实施提交Run 45556482627和同步提交Run 45556547468均completed/success；两次运行的知识结构/数据质量、strict lint及CH12数值资源Job全部通过。该CI不代表CH17现场或实机维修验证。


## 6.6 CH17-T003 主轴、伺服与滚珠丝杠专项更换工作包（2026-11-25）

- 新增正文 docs/17-operation-maintenance-and-repair/spindle-servo-ballscrew-specialized-replacement-work-packages.md（KNOW-000025），分别细化主轴单元、伺服电机/编码器、滚珠丝杠/支撑轴承的基线、兼容性、风险控制、参数恢复和维修后复验边界。
- 新增三份原创专项CSV工作包：spindle-replacement-work-package-template.csv（ASSET-000019，18检查项/35列）；servo-motor-encoder-replacement-work-package-template.csv（ASSET-000020，17检查项/35列）；ballscrew-support-bearing-replacement-work-package-template.csv（ASSET-000021，17检查项/35列）。
- 三份表采用相同的35字段骨架，将工作包元数据、部件身份、旧/新件替代批准、OEM程序、关键值来源、验收判据、责任专业、危险能量停工点、实测结果与偏差记录分开；各专项检查内容不同。
- **安全与适用边界：** 未提供型号级拆装顺序、吊装/支撑方法、放电/隔离步骤、紧固扭矩、轴承/螺母预紧、润滑介质或验收阈值。必须映射到具体机床序列范围、OEM受控文件和现场风险评估。
- **状态：** CH17-T003保持IN_PROGRESS；本轮只完成三个部件族的通用专项工作包模板，尚无用户目标机型和现场更换证据。

- **实施提交：** a5c3829d4c8fc4cd63bf1b1dbd0a3a57a52a0fec；计划/索引/覆盖度同步提交：8c08cc78f3ccf0497a319b2f01669098e68910ba。
- **CI验收：** 实施提交Run 45557662316和同步提交Run 45557733024均completed/success；知识结构/数据质量、strict lint及CH12数值资源回归Job全部通过。该CI不代表CH17现场或实机维修验证。


## 6.7 CH17-T003 刀库/换刀、卡盘夹持与液压气动专项更换工作包（2026-11-25）

- 新增正文 `docs/17-operation-maintenance-and-repair/atc-chuck-hydraulic-specialized-replacement-work-packages.md`（KNOW-000026），将自动换刀/刀库/刀塔、卡盘/工件夹持、液压/气动动力单元细化为三个专项审查域，并定义G0–G7控制门。
- 新增三份原创35列CSV：`atc-tool-magazine-turret-replacement-work-package-template.csv`（ASSET-000022，20项）、`chuck-workholding-replacement-work-package-template.csv`（ASSET-000023，18项）、`hydraulic-pneumatic-unit-replacement-work-package-template.csv`（ASSET-000024，20项）。
- 模板仅为待评估/未测试审查入口；不提供刀库相位/换刀步骤、夹持力/压力/转速、液压设定、蓄能器处置、泄压/排气动作或通用验收限值。所有技术数据和现场步骤需绑定具体机床序列范围、OEM受控文件、批准工程变更与风险评估。
- **状态：** CH17-T003保持IN_PROGRESS；无目标机型和现行OEM服务文件，未形成型号级维修SOP、替代批准或现场/实机验证。


## 6.8 CH17-T004 备件管理与生命周期闭环第一轮（2026-11-25）

- 新增正文 `docs/17-operation-maintenance-and-repair/spare-parts-management-and-lifecycle.md`（KNOW-000027），建立备件主数据、关键度评估、库存补货、替代件审批、生命周期/停产风险和维修工单消耗反馈六类对象及端到端闭环。
- 新增六份原创空白CSV：备件主数据（ASSET-000025，38列）、关键度评估（ASSET-000026，32列）、库存与补货（ASSET-000027，40列）、替代审批（ASSET-000028，36列）、生命周期/停产风险（ASSET-000029，31列）、维修消耗反馈（ASSET-000030，34列）。
- **数据与安全边界：** 模板不创建真实PART/PRODUCT/MINST，不填备件料号、供应商、采购价格、交期、库存余额、关键度评分、补货参数或替代结论。安全相关部件的决策必须服从适用法规、OEM/合同与企业风险审批；替代件需限定机型/序列/配置/BOM范围并取得适用技术审批和验证。
- **未完成项：** 尚无目标机型受控BOM/OEM备件目录、企业库存/消耗历史、正式供应商交期、PCN/EOL通知和真实维修工单，尚未激活具体库存策略或替代批准。
- **状态：** CH17-T004保持IN_PROGRESS；后续需导入授权数据并由设备、工程、质量、采购和仓储角色完成审核与系统映射。



## 6.9 CH17-T004 备件系统集成、字段映射与数据治理第二轮（2026-11-25）

- 新增正文 `docs/17-operation-maintenance-and-repair/spare-parts-system-integration-and-data-governance.md`（KNOW-000028），补充ERP/CMMS/EAM/PLM/PDM系统职责候选、字段级SoR与外部键、静态知识对象和业务事务对象边界、库存事件对账、数据质量规则、库存策略输入及RACI/状态治理。
- 新增 `spare-parts-enterprise-system-field-mapping-template.csv`（ASSET-000031，27列表头空模板）、`spare-parts-data-quality-and-reconciliation-rules.csv`（ASSET-000032，16条/14列建议规则）、`spare-parts-stock-policy-decision-template.csv`（ASSET-000033，35列表头空模板）。
- **规则及参数边界：** 16条规则均为PROPOSED，需企业数据所有者确认适用性、阻断模式、检测频率、阈值/容差来源和处置责任；库存策略模板不填写安全库存、订货点、最小/最大量、MOQ或复核周期数值。字段权威系统、映射和RACI均未预先指定。
- **模型边界：** 复用当前已有MACHINE、MINST、BOM、PART、PRODUCT、VENDOR、DOC、ASSET及其支持的关系类型。采购单行、收货、库存移动、批次、预留、维修工单和审批实例仍属于源系统事务对象，不伪装成知识实体；本轮不修改全库Schema。
- **未完成项：** 尚未连接任何ERP/CMMS/EAM/PLM，不含真实企业记录、设备配置、供应商交期、库存、交易、工单或经批准的库存策略；企业级映射和对账需待授权数据输入后完成。
- **状态：** CH17-T004保持IN_PROGRESS。


## 6.10 CH17-T004 备件实物流转、事务控制与责任矩阵第三轮（2026-11-25）

- 新增正文 `docs/17-operation-maintenance-and-repair/spare-parts-physical-flow-and-transaction-controls.md`（KNOW-000029），定义备件从需求提出、配置确认、采购收货、质量放行、仓储预留/发料、现场安装、旧件回收/返修/报废、盘点对账至PCN/EOL评估的业务控制链。
- 新增 `spare-parts-transaction-lifecycle-control-matrix.csv`（ASSET-000034，16事件/23列）和 `spare-parts-raci-approval-matrix-template.csv`（ASSET-000035，16活动/16列）。RACI中的角色分配是项目建议，全部PROPOSED，须企业组织与授权制度批准。
- **流程控制：** 区分物理事件、系统过账和技术/质量状态；明确定义事件身份、业务时间、过账时间、数量/单位、库存状态桶、设备/BOM/工单关联、证据、幂等和冲销链。未检/隔离物料不可计为可用；未批准/超范围替代不可发放；旧件不得直接返可用库存。
- **边界：** 流程矩阵不代表已连接ERP/CMMS/EAM或创建真实事务；没有定义企业实际状态代码、盘点频率/容差、授权人员和例外SLA。机型级维修动作必须遵循OEM受控程序、现场风险评估和危险能量控制，不以模板替代SOP。
- **状态：** CH17-T004继续IN_PROGRESS，待真实系统事件样本、企业授权RACI、受控BOM/OEM及现场维修工单映射后继续。


## 6.11 CH17-T004 备件端到端验收场景与测试证据第四轮（2026-11-25）

- 新增正文 `docs/17-operation-maintenance-and-repair/spare-parts-end-to-end-acceptance-testing.md`（KNOW-000030），建立L0静态、L1规则、L2集成/SIT、L3业务/UAT及L4上线准备分层验收方法，定义合成数据集、隔离环境、结果状态、缺陷管理和发布门槛。
- 新增 `spare-parts-end-to-end-acceptance-test-matrix.csv`（ASSET-000036，30用例/24列）和 `spare-parts-acceptance-test-execution-record-template.csv`（ASSET-000037，30列表头空模板）。
- **场景覆盖：** 外部键/BOM适用性、采购/部分收货、检验放行、库存数量/在途、单位换算、幂等、替代边界、发料与安装消耗、批次追溯、返修报废、盘点差异、PCN/EOL、权限、SoR冲突、敏感字段和事件恢复。
- **边界：** 30个场景均为NOT_RUN，不代表已执行SIT/UAT或真实业务测试；执行记录模板为空。所有测试须使用获授权的非生产环境和合成/获准脱敏数据。现场维修仍须服从OEM受控程序、人员授权和危险能量控制，不能以测试矩阵替代机床SOP。
- **状态：** CH17-T004保持IN_PROGRESS；待企业授权系统环境、字段映射/SoR和合成数据集冻结后执行测试并补录证据。

## 6.12 CH17-T004 备件合成测试数据与环境就绪规范第五轮（2026-11-25）

- 新增正文 `docs/17-operation-maintenance-and-repair/spare-parts-synthetic-test-data-and-environment-readiness.md`（KNOW-000031），规定数据集标识/版本/生成器/冻结与校验、合成对象及依赖关系、业务时间/接收时间/重放顺序、L0～L4环境隔离、最小权限、秘密管理、备份恢复、重置和清理。
- 新增三份原创CSV：`spare-parts-synthetic-test-dataset-manifest-template.csv`（ASSET-000038，29列表头空模板）；`spare-parts-test-environment-readiness-checklist.csv`（ASSET-000039，22项/11列，全部NOT_ASSESSED）；`spare-parts-test-fixture-cross-reference-template.csv`（ASSET-000040，27列表头空模板）。
- **模型边界：** 复用现有MACHINE/MINST/BOM/PART/PRODUCT/VENDOR等静态概念；PO行、收货、检验、库存流水、预留、维修工单、审批和PCN/EOL事件只作为测试环境事务/夹具，不新增全库实体类型或关系谓词。
- **安全与环境边界：** 默认纯合成数据；脱敏数据需单独批准。L2/L3必须使用经批准的隔离非生产环境、专用身份、测试端点、秘密管理、非生产快照/恢复及清理证据；禁止生产写入、真实供应商/客户通知和生产机床动作。
- **未完成项：** 尚未取得企业非生产环境授权、正式角色及网络隔离证据；尚未生成/冻结企业专用合成数据集，也未执行备件30项SIT/UAT（仍全部NOT_RUN）。本轮模板不代表环境就绪或测试通过；CH17-T004保持IN_PROGRESS。

## 6.13 CH17-T004 备件合成测试夹具基线与30项用例映射第六轮（2026-11-25）

- 新增 `docs/17-operation-maintenance-and-repair/spare-parts-synthetic-fixture-baseline-v1.md`（KNOW-000032），建立数据集 `SPAREPARTS-SYN-BASE-001` v1.0.0 的固定静态合成夹具、隔离重置、使用限制和事件时间语义。
- 新增 `spare-parts-synthetic-fixture-baseline-v1-manifest.csv`（ASSET-000041，29列/1行，DRAFT）；`spare-parts-synthetic-fixture-baseline-v1.csv`（ASSET-000042，89条记录/27列，67对象+22事件）；`spare-parts-synthetic-fixture-test-case-coverage-v1.csv`（ASSET-000043，30用例/11列，SPAT-001～SPAT-030全部映射）。
- **数据与事务边界：** 所有ID均为虚构SYN-/FX-/EVT-标识，没有导入生产或脱敏源数据。采购、收货、库存、维修工单、审批和生命周期项目仅作为测试夹具/业务事件，不扩展全库静态知识实体Schema。数量和换算比例只用于测试逻辑，不是企业库存策略或机械技术参数。
- **版本和BOM边界：** 数据集版本1.0.0，当前DRAFT、未获批准、未冻结至环境。BOM R1在2026-01-01至2026-06-30（含）有效，R2自2026-07-01起有效，仅供日期边界测试。
- **未完成项：** 尚未开发/运行fixture validator，未批准企业非生产环境，未执行任何SPAT用例；30项状态保持NOT_RUN。CH17-T004继续IN_PROGRESS。

## 6.14 CH17-T004 备件合成夹具本地静态校验器第七轮（2026-11-25）

- 新增 `scripts/spare_parts_fixture_validator.py`，纯Python标准库、本地静态运行；验证四份输入CSV的列结构/字段、数据集ID与版本、合成标记、ID唯一、对象引用、30项用例覆盖和双向夹具引用、BOM有效期不重叠、事件时间戳/时区/接收顺序/序号及显式乱序标记。
- 新增 `tests/test_spare_parts_fixture_validator.py`，新增9项回归测试；CI现自动执行单元测试、夹具校验及JSON报告Artifact归档。
- 运行报告数据：89条夹具（67对象/22事件）、89个唯一ID、30项用例映射、2个BOM修订、17个重置组；10项校验PASS、0错误。发现5条延迟投递、1条显式乱序事件。
- **状态边界：** 校验器只证明夹具文件内部结构与映射一致；数据集仍DRAFT，企业环境和测试层级未批准，30项业务用例仍NOT_RUN。未连接企业系统、未执行SIT/UAT/HIL/实机测试。
- **CI：** [Run 45588285648](https://github.com/rexyll/cnc-knowledge/actions/runs/45588285648)两个Job均成功；报告Artifact [JSON验证报告](https://github.com/rexyll/cnc-knowledge/actions/runs/45588285648/artifacts/15009916943)。

## 6.15 CH17-T004 备件测试场景重置配置与本地包生成器第八轮（2026-11-25）

- 新增 `spare-parts-synthetic-fixture-reset-profiles-v1.csv`（ASSET-000044，30行/15列），逐SPAT用例明确直接夹具、依赖闭包、事件、reset group、幂等键和文件包清理范围；由场景映射和夹具关系确定性推导。
- 新增 `scripts/spare_parts_fixture_loader.py`，校验源数据集与重置配置一致后生成单用例或全部30个本地场景包；对象按父先子后排序，事件按接收时间/序号排序。
- 每个本地场景包包含scenario-manifest、fixtures/objects/events CSV、load-plan和PLAN_ONLY reset-plan；目标目录存在时拒绝覆盖。工具没有企业系统适配器，不访问数据库/API/队列，不执行任何企业重置/删除。
- 新增 `tests/test_spare_parts_fixture_loader.py`，验证单场景、全30场景、父子顺序、重置计划、未知用例、拒绝覆盖、配置篡改和源数据不变；CI全量打包和Artifact归档。
- **边界：** 30项业务测试仍NOT_RUN；数据集仍DRAFT；22项环境检查仍NOT_ASSESSED。CH17-T004保持IN_PROGRESS。

## 6.16 CH17-T004 备件场景包完整性校验与离线事件投影第九轮（2026-11-25）

- 新增 `scripts/spare_parts_scenario_runner.py`：独立重建场景包，逐文件验证内容与哈希，复核源夹具引用闭包、纯合成字段、对象/事件分区及事件接收顺序；缺失/额外文件、内容漂移或符号链接均失败关闭。
- 显式维护22类事件离线行为目录；重复消息必须保留原事件引用且零增量，迟到冲销不得删除原事件，乱序必须显式标记，非库存事件不得改变库存桶。
- 使用Decimal对夹具声明的期望数量变化做reset_group隔离投影；无企业初始库存快照和库存口径，不计算期末库存/可用量，也不跨组求和。
- 新增11项执行器专项测试；CI共33项单测通过，生成并检查30个场景包，离线模拟30/30、0失败，报告Artifact归档。
- **边界：** simulation PASS不是业务验收，business_rule_assertions=NOT_EVALUATED，30项业务测试NOT_RUN；无企业系统适配器、无数据库/API写入、无SIT/UAT/HIL/实机运行。CH17-T004保持IN_PROGRESS。

## 6.17 CH17-T004 独立库存状态机内核与双边转移契约第十轮（2026-11-25）

- 新增 `scripts/spare_parts_inventory_state_model.py`：通用双边库存账户转移内核，采用Decimal，检查账户完整性、正数数量、单位、来源余额非负、数量守恒及失败原子性；内核无企业系统适配器。
- 新增 `spare-parts-inventory-state-transition-contract-v1.csv`（ASSET-000045，22类事件）。来源账户、目标账户、单位字段、批准人和批准依据均未预填，状态全部NOT_APPROVED。
- 新增9项专项测试；CI校验22类事件契约唯一、审批门禁失败关闭，并上传就绪报告Artifact。
- **模型边界：** 现有单桶期望增量不具备双边分录信息；库存快照缺少完整物料/批次/库位期初余额。不得由模型自行推断业务规则或期末库存。CH17-T004保持IN_PROGRESS。

## 6.18 CH17-T004 期初状态与库存维度候选模型第十一轮（2026-11-25）

- 新增ASSET-000046候选账户字典：将实物数量账户、外部对方账户、非实物备忘/承诺账户和观察记录分开；所有13类候选均PROPOSED_NOT_APPROVED。
- 新增ASSET-000047候选维度字典：物料、批次、库位、所有权、质量状态、单位、工单和采购行等候选维度；适用性与必填性均待批准。
- 新增ASSET-000048期初余额空白模板：只有表头，无预填库存数量；要求源系统、源记录、截止时间/时区、提取时间、哈希、单位换算及批准依据。
- 新增ASSET-000049期初状态场景矩阵：针对9个代表性测试场景登记所需期初输入与守恒断言；全部PROPOSED_NOT_APPROVED、NOT_RUN。
- **边界：** 不把预留/分配/采购承诺混入实物数量；不假定企业账户字典或库存维度；无获批期初余额，禁止计算期末库存或启用22类转移契约。CH17-T004继续IN_PROGRESS。

## 6.19 CH17-T004 多维库存余额内核与事件回放第十二轮（2026-11-25）

- 新增 scripts/spare_parts_multidimensional_inventory.py：余额键包含账户/物料/批次/库位/所有权/状态/单位；使用Decimal；同物料/批次/库位/所有权/单位下执行双边转移；跨库位、物料、批次、所有权及单位变化失败关闭。
- 新增显式单位换算记录接口：仅APPROVED且包含批准人/批准依据的换算记录可计算；内核不自动套用换算。
- 新增纯合成期初快照装载器：仅接受synthetic_only=TRUE且snapshot_status=SYNTHETIC_TEST_ONLY的行，要求reset_group，拒绝企业快照。
- 新增事件顺序与ID检查、整批回放原子性；新增14个专项unittest方法，覆盖ASSET-000050中的17个断言场景。
- CI运行模型自检并归档报告；自检状态BLOCKED_PENDING_ENTERPRISE_APPROVAL，business_rule_assertions=NOT_EVALUATED。
- **边界：** 不执行企业业务规则、不计算企业期末库存、不连接外部系统。CH17-T004继续IN_PROGRESS。

## 6.20 CH17-T004 不可变库存事件账本与时点重建第十三轮（2026-11-25）

- 新增 `scripts/spare_parts_inventory_event_ledger.py`：内存追加式账本，记录event_id、business_event_id、source_system_id、idempotency_key、business_time、ingestion_time、事件类型、双边余额键、Decimal数量及冲销引用。
- 同幂等键同载荷重复投递为NO_OP；幂等键载荷冲突、跨幂等键重复event_id拒绝。迟到/乱序事件按接收顺序留档，余额重建按业务时间与账本序号排序；可选known_at_cutoff还原某知识时点。
- 冲销只能新增REVERSAL事件，必须引用已存在TRANSFER、精确反向键和相同数量；原事件不可修改。当前模型仅支持一次完整冲销，不定义部分冲销/多次补偿政策。
- 从显式合成期初余额重建截止时点投影，提供账本记录与余额投影核对；禁止跨单位、跨reset group或全局总额汇总。
- 新增18个断言场景及专项测试，CI运行self-check并上传JSON报告；报告保持BLOCKED_PENDING_ENTERPRISE_APPROVAL、business_rule_assertions=NOT_EVALUATED。
- **边界：** 仅内存、非持久化WORM账本；不连接消息队列/ERP/WMS/CMMS，不提供企业审计留存、并发/权限或签名能力。CH17-T004继续IN_PROGRESS。


## 6.21 CH17-T004 库存事件账本完整性链与快照恢复第十四轮（2026-11-25）

- 新增 scripts/spare_parts_inventory_ledger_integrity.py：规范化JSON序列化；时间统一UTC微秒ISO-8601，Decimal统一定点字符串，维度键字段显式编码。
- 每条事件计算SHA-256内容摘要，并将前序链头与当前摘要组合为链哈希；校验ledger_sequence连续性、事件ID/幂等键唯一性、事件内容、前序链和最终链头。
- 快照记录schema_version、ledger_sequence、链头、业务/知识截止时点、合成期初余额、余额投影及snapshot_hash。恢复先验证快照和账本前缀，再回放后续事件，并与全量重放结果比较。
- 若后续到达事件的business_time不晚于快照截止时点，恢复失败并要求从期初余额全量重建；业务截止时点不得倒退。未知版本、链头不匹配、摘要损坏和序号缺口均失败关闭。
- 新增ASSET-000052及15个纯合成测试场景，13个专项unittest方法；CI运行自检并归档报告。
- **限制：** 哈希链不是数字签名、WORM或法律意义防篡改；不具备外部信任根、生产持久化、访问控制、职责分离和并发保护。业务规则仍NOT_EVALUATED，审批门禁保持BLOCKED_PENDING_ENTERPRISE_APPROVAL，CH17-T004继续IN_PROGRESS。

- **CI验收：** GitHub Actions Run 45629680465 completed/success；Knowledge structure and data quality与CH12 numerical resource tests两个Job均成功；全库87个unittest方法通过，完整性/快照专项13项通过。自检报告显示2条事件封链、快照后增量回放1条、与全量重放一致。Artifact ch17-inventory-ledger-integrity-45629680465。


## 6.22 CH17-T004 库存事件账本本地持久化与故障恢复第十五轮（2026-11-25）

- 新增 scripts/spare_parts_inventory_ledger_persistence.py：代际目录写入ledger.json、snapshot.json和COMMIT.json；对文件执行flush/fsync并同步目录，最后通过同目录临时CURRENT指针+os.replace原子发布已提交代际。
- 恢复只读取CURRENT指定代际，验证指针版本、generation标识、COMMIT状态、账本/快照文件SHA-256、事件链、快照摘要和提交元数据，再重建AppendOnlyEventLedger。
- 故障注入覆盖账本写后、快照写后、代际目录rename后、CURRENT替换前；证明未发布代际不会成为当前版本，旧CURRENT在下一代发布失败时仍可恢复。增加损坏文件、缺失提交标记、未知版本、路径穿越和重复代际测试。
- 新增ASSET-000053及11个纯合成故障场景，11个专项unittest方法；CI自检只在临时目录完成，不写生产数据。
- **边界：** 原子rename/fsync耐久性依赖OS/文件系统/挂载/设备；无多进程锁、数据库事务、分布式共识、WORM、签名、外部信任根、异机复制和密钥管理。CH17-T004继续IN_PROGRESS，业务规则NOT_EVALUATED，审批门禁BLOCKED_PENDING_ENTERPRISE_APPROVAL。

## 6.23 CH17-T004 库存账本并发写入控制与多进程恢复一致性第十六轮（2026-11-25）

- 在本地代际持久化中引入POSIX fcntl.flock跨进程排他锁；锁超时失败关闭，进程退出/崩溃由内核释放锁。锁文件保留不等于锁占用。
- 增加expected_current_generation compare-and-swap：持锁后读取CURRENT并与调用者预期比较；过期写入者拒绝提交。默认*不启用CAS，None要求当前无提交代际。
- 新增并发两个进程竞争、CAS唯一胜者、陈旧写入冲突、锁超时、进程崩溃自动释放和中断后再提交测试；新增5个专项unittest方法。
- CI多进程自检：2个独立写入者、1个COMMITTED、1个CONFLICT，恢复CURRENT成功。Run 45635237388两个Job均success，全库103个unittest方法通过；Artifact ch17-inventory-ledger-concurrency-45635237388。
- **平台限制：** 当前使用POSIX flock，Windows原生锁未实现；advisory lock要求写入者遵守协议，网络文件系统锁语义需单独验证；不是分布式锁，不保护绕过模块的外部写入。
- CH17-T004保持IN_PROGRESS；业务断言NOT_EVALUATED；审批门禁BLOCKED_PENDING_ENTERPRISE_APPROVAL。


## 6.24 CH17-T004 库存账本读取一致性、并发读取与代际生命周期管理第十七轮（2026-11-25）

- **状态：** IN_PROGRESS；仅完成本地POSIX合成模型和静态测试矩阵，不提升CH17-T004整体状态。
- **实现：** scripts/spare_parts_inventory_ledger_persistence.py 的 recover_current() 在完整读取/验证CURRENT所指代际期间持有 .gc.lock 共享锁；garbage_collect_generations() 先取 .writer.lock 排他锁，再取 .gc.lock 排他锁，避免读取中删除及清理已rename但尚未切换CURRENT的在途代际。
- **保留策略：** CURRENT始终保留；至少保留最近 keep_last 个已验证代际（最小1）；不删除年龄小于 minimum_age_seconds 的代际。只有COMMIT身份正确且ledger/snapshot摘要一致的目录可被回收；未验证条目跳过。
- **删除门禁：** 默认 apply=False，CLI默认输出dry-run计划；仅显式 --gc-apply 执行删除。先rename至 .gc-trash-* 再递归删除，后续apply可处理异常退出留下的trash；不自动清理 .staging-*。
- **测试：** 新增ASSET-000055，10个纯合成测试场景；新增6个unittest方法，全库109项通过。含读写/回收多进程压力和活动读锁阻止GC用例。
- **CI：** 代码实现与测试修复提交 a9d5b094dddb15b476d9b2e5f9e02f85163b52e8 对应Run 45641575977，Knowledge structure and data quality及CH12 numerical resource tests两个Job均completed/success；持久化self-check报告reader GC exclusion、dry-run、retention/recovery均PASS。
- **限制：** POSIX advisory flock协作模型；Windows原生文件锁、NFS/SMB、跨主机分布式锁、企业备份/留存期限/删除审批均未验证。纯临时目录、无企业连接/生产写入；业务断言NOT_EVALUATED，execution_status=BLOCKED_PENDING_ENTERPRISE_APPROVAL。


## 6.25 CH17-T004 库存账本备份完整性与隔离恢复演练第十八轮（2026-11-25）

- **状态：** IN_PROGRESS；新增本地纯合成备份/校验/恢复机制，不改变企业审批门禁。
- **实现：** create_backup() 从CURRENT指向的已提交代际创建独立备份目录；BACKUP.json清单包含backup ID、源代际、UTC时间、文件大小/SHA-256、账本记录数、链头及清单自身摘要。创建过程持有源存储.gc.lock共享锁，备份暂存目录fsync后原子发布。
- **验证：** verify_backup() 检查目录精确文件集合、普通文件/非符号链接、清单摘要、文件大小和SHA-256、COMMIT身份、事件哈希链、快照和对应账本前缀以及事件重建。
- **恢复：** restore_backup() 只接受新建或空白隔离目标目录；验证后恢复原代际文件，先发布代际目录，最后原子切换CURRENT；不覆盖非空目录。中断在CURRENT之前时只留下孤立代际。
- **资源与测试：** 新增ASSET-000056，10个纯合成测试场景；新增6个专项unittest，全库CI共116项测试通过。覆盖备份篡改、清单篡改、创建中断、源代际被GC后恢复、非空目标拒绝覆盖、恢复中断和路径隔离。
- **CI：** 实现提交 0fdef80a2da217c0fbd622f3185fb820287be8f5 对应Run 45643219363，两个Job均completed/success，全库116个unittest通过，备份验证/隔离恢复self-check均PASS；文档同步提交 2f6cdb72418582c94035e4359a9171b1fcd4f1b8 对应Run 45643684590，Knowledge structure and data quality与CH12 numerical resource tests两个Job均completed/success。
- **限制：** 未实现备份加密、数字签名/外部信任根、异地副本、对象存储/WORM、介质恢复、企业RPO/RTO或真实灾备演练。仅POSIX本地临时目录合成数据，无企业连接/生产写入；30项企业业务测试仍NOT_RUN，业务断言NOT_EVALUATED，审批门禁BLOCKED_PENDING_ENTERPRISE_APPROVAL。


## 6.26 CH17-T004 库存备份保留、RPO/RTO、安全与灾备治理第十九轮（2026-11-26）

- **状态：** IN_PROGRESS；交付供应商中立的治理模板和结构校验，不代表企业备份政策已获批准。
- **知识条目：** 新增KNOW-000033《数控机床备件库存账本备份治理、RPO/RTO与灾备验收》。
- **资源：** ASSET-000057备份保留策略、ASSET-000058 RPO/RTO目标、ASSET-000059加密/密钥管理、ASSET-000060异地存储评估、ASSET-000061恢复演练验收矩阵（10个场景）。
- **门禁字段：** 明确保留范围/期限/法律保全/删除角色、RPO/RTO测量边界、静态/传输加密、KMS/HSM/密钥恢复、区域/司法辖区/数据驻留、不可变保护、访问隔离、恢复吞吐及退出方案。
- **自动校验：** scripts/spare_parts_backup_governance_validator.py 检查五个CSV的schema/行宽/唯一ID、审批状态和APPROVED记录的证据/数值字段；所有恢复演练场景初始PROPOSED_NOT_APPROVED、NOT_RUN。
- **生产启用门禁：** 企业BIA、保留/法律保全、RPO/RTO、安全评审、供应商/异地副本验证、隔离恢复与业务对账签核全部齐全前，production_backup_enabled=false、governance_readiness=BLOCKED_PENDING_ENTERPRISE_APPROVAL。
- **严格边界：** 未选择供应商/区域、未设默认保留期限或RPO/RTO、未实现KMS/HSM/加密适配器/远端复制；不连接企业系统或生产账户、不保存密钥、不实施真实删除/备份；所有恢复演练矩阵项保持NOT_RUN。

- **最终实现/矩阵修正CI验收：** 提交 9e8e3e0b19d7052b2899515575747f1c0b100834 对应Run 45732010499，Knowledge structure and data quality与CH12 numerical resource tests两个Job均completed/success；全库127个unittest方法通过。新增校验器检查5个CSV schema、10条DRB用例状态和验收定义字段，报告0 errors；strict knowledge lint 0 errors。
- **治理报告Artifact：** ch17-backup-governance-readiness-45732010499，Artifact ID 15076713318；报告模板文件5个、策略记录0条、批准策略0条、恢复演练10条；governance_readiness=BLOCKED_PENDING_ENTERPRISE_APPROVAL，production_backup_enabled=false，enterprise_backup_test_status=NOT_RUN。
- **实施与文档CI：** 实现/初版模板提交 095deffdbf173c70f973d15844033b7a0deeaa7b 对应Run 45731635763两个Job均success；文档/实体同步提交 32fa8aa889350398539945620df7ad418e9e46a5 对应Run 45731937638两个Job均success。

## 6.27 CH17-T004 供应商中立备份存储适配器与Mock验证第二十轮（2026-11-26）

- **状态：** IN_PROGRESS；仅完成本地文件和进程内Mock Provider契约，不接真实对象存储。
- **知识条目：** 新增KNOW-000034《数控机床备件库存账本备份存储适配器契约》。
- **实现：** `scripts/spare_parts_backup_storage_adapter.py` 定义ObjectStorageProvider的capabilities、put_if_absent、get_object；实现FileSystemStorageProvider和MockObjectStorageProvider；BackupStorageAdapter提供publish_backup、verify_stored_backup、restore_from_provider。
- **提交协议：** 四个负载对象先写，BACKUP-RECEIPT.json最后发布作为提交标记。失败留下未提交孤儿对象，无回执不视为完整备份；同字节重试幂等，不同内容冲突；无delete/list API。
- **安全边界：** 能力声明附带evidence_scope；Mock的版本/对象锁/加密/TLS仅为模拟声明。无真实网络、凭据、KMS/HSM、加密、对象锁、云区域或远端副本。
- **测试：** 新增13项Provider/适配器专项unittest；ASSET-000063包含12个测试场景，覆盖幂等、冲突、中断续传、回执最后提交、篡改/缺失、版本ID、路径安全和隔离恢复；CI增加Mock self-check与Artifact。
- **生产门禁：** 真实Provider接入前须评审条件创建/读后写语义、身份权限、加密与密钥、对象锁/保留、数据驻留、恢复吞吐、RPO/RTO与供应商退出证据；production_backup_enabled=false，governance_readiness=BLOCKED_PENDING_ENTERPRISE_APPROVAL。

- **CI验收：** 最终代码提交 2b95bca7741efa359bd287ffec16dc9c98f131c7 对应Run 45732798249，两个Job均completed/success；全库140个unittest通过。Provider self-check与strict knowledge lint均PASS（0 errors）；Artifact `ch17-backup-storage-adapter-45732798249`，ID 15076314703。
- **CI修复记录：** 初始Run 45732501248发现对象版本读取/测试篡改样本问题；Run 45732585785修正后140个单测通过，但CI直接执行脚本发现repo import path问题；提交2b95bca7741efa359bd287ffec16dc9c98f131c7补齐ROOT/sys.path后最终CI通过。


## 6.28 CH17-T004 备份Provider身份权限、分块续传与孤儿对象治理第二十一轮（2026-11-26）

- **状态：** IN_PROGRESS；仅本地/Mock验证，未接真实对象存储。
- **知识条目：** KNOW-000035《库存账本备份 Provider 身份权限、分块续传与孤儿回收治理》。
- **实现扩展：** ProviderCapabilities新增身份认证、授权模型、租户隔离、审计记录、multipart和prefix-scoped inventory能力声明。Mock Provider加入principal/action/prefix ACL、tenant隔离声明和元数据审计轨迹。
- **分块传输：** 新增MultipartObjectStorageProvider，支持确定性会话ID、分块SHA-256、分块序号验证、同块幂等/冲突、缺块拒绝、汇总长度与摘要校验、断点续传。abort仅作用于未完成上传会话，不删除最终对象。
- **孤儿盘点：** 新增ScopedInventoryProvider，只在指定前缀返回对象元数据/未完成分块会话。区分未提交对象、已验证包、缺失/异常已发布包和未完成分块会话。回收状态仅PROPOSED_NOT_APPROVED，不提供完成对象delete API或自动回收。
- **测试：** 新增10个unittest方法；覆盖权限拒绝、审计元数据、租户隔离、multipart续传、分块完整性、abort边界、孤儿分类和prefix权限。
- **资源：** 新增ASSET-000064～000066，分别为身份权限评估、孤儿回收审批、14条Provider可靠性合成测试矩阵。
- **生产门禁：** 真实身份系统、MFA/工作负载身份、凭据托管、云审计、服务端版本/一致性、分块限制、保留/法律保全与清理审批均未验证；不执行实际回收。

- **最终资源同步CI：** 资源列宽修正提交 `540ab361a59dd54a2eb078e58257da4d4d8238dd` 对应Run 45738063901，Knowledge structure and data quality与CH12 numerical resource tests两个Job均success；全库150个unittest通过、知识校验0 errors；Provider Artifact ID 15080002233。
- **最终资源结构：** ASSET-000064空白身份/权限评估模板26列；ASSET-000065空白孤儿盘点/回收审批模板30列；ASSET-000066测试矩阵14条、11列，均PROPOSED_NOT_APPROVED / NOT_RUN。


## 6.29 CH17-T004 备份Provider瞬态故障、重试与一致性恢复第二十二轮（2026-11-26）

- **状态：** IN_PROGRESS；本地/Mock测试，不接真实云Provider。
- **知识条目：** KNOW-000036《备份Provider重试、一致性与模糊提交恢复》。
- **错误分类：** 新增ProviderTransientError，可附Retry-After和outcome_unknown。只捕获该异常进行重试；权限拒绝、摘要冲突、版本缺失和永久校验错误不重试。
- **退避：** retry_max_attempts默认4（含首调），base delay默认0.1秒，max delay默认2秒；指数增长并受上限约束，Provider Retry-After提示合并进等待时间；sleep函数可注入。当前Mock为确定性无jitter，生产参数/抖动待供应商限流证据。
- **模糊提交恢复：** Mock能在对象/分块/完成对象已实际写入后丢失响应并返回outcome_unknown；相同key/session/part/content重试必须幂等。
- **读后写一致性：** Mock可以延迟若干次读取才显示对象；预算内可重试，预算耗尽不返回成功，后续以原backup ID重新盘点/验证。
- **版本切换：** 模拟对象最新版本变化及历史版本不可用；验证按receipt固定历史version ID，版本缺失则失败关闭。
- **测试：** 新增10项专项unittest，覆盖退避、限流、写响应丢失、延迟可见/重试耗尽、版本固定/缺失、multipart part/complete响应丢失、永久错误不重试。实现提交全库150个unittest通过；故障测试提交全库160个unittest通过，CI Run 45738812474两个Job均success。扩展self-check CI待最终确认。
- **资源：** 新增ASSET-000067，12条Provider瞬态故障与一致性测试场景，全部PROPOSED_NOT_APPROVED / NOT_RUN。
- **生产门禁：** 无真实429/5xx/SDK超时/云端延迟可见性/版本生命周期/跨区一致性实测；无真实账户/凭据/网络/KMS/HSM/加密/对象锁/删除。生产备份继续关闭。

- **代码/自检CI：** 代码及新增故障测试Run 45739249726两个Job均completed/success，全库160个unittest通过；扩展Mock自检Run 45738938023两个Job均completed/success，Artifact `ch17-backup-storage-adapter-45738938023`（ID 15079098689），自检结果PASS且无网络/凭据/删除。
- **资源列顺序修复：** 三份Provider适配器矩阵（ASSET-000063、000066、000067）统一为 `synthetic_only=TRUE`、`approval_status=PROPOSED_NOT_APPROVED`、`execution_status=NOT_RUN`、`notes`最后列；修复CI Run 45739179773两个Job均success。


## 6.30 CH17-T004 备份Provider熔断、舱壁和任务重试预算第二十三轮（2026-11-26）

- **状态：** IN_PROGRESS；仅本地/Mock验证。
- **知识条目：** KNOW-000037《备份Provider熔断、半开探测、舱壁与总重试预算》。
- **熔断：** read/write/multipart/inventory四域独立CircuitBreaker；CLOSED/OPEN/HALF_OPEN；默认failure threshold=3、reset timeout=30s、half-open probe=1；仅ProviderTransientError累加失败，OPEN快速拒绝。
- **舱壁：** 四域独立BoundedSemaphore；默认并发read=4/write=2/multipart=2/inventory=1；bulkhead等待默认0秒，满载返回ProviderBulkheadFullError；每次Provider调用结束或异常后释放。
- **任务级总预算：** ContextVar与RetryBudget按顶层备份/验证/恢复/盘点操作作用域累计嵌套调用的重试次数；默认20次。并发线程/任务有独立上下文预算；耗尽抛RetryBudgetExceededError，不报告成功。
- **测试：** 新增9项专项unittest；代码测试CI Run 45740068529两个Job均success，全库169个unittest通过。自检扩展Run 45740213445待最终确认。
- **资源：** 新增KNOW-000037、ASSET-000068；14条故障/并发场景，均PROPOSED_NOT_APPROVED / NOT_RUN。
- **限制：** 状态和舱壁仅单Adapter实例/进程内，不支持分布式协调；默认值不是生产推荐；没有真实云网络、跨进程/跨容器/集群容量与RTO验收。

- **最终CI验收：** 代码与新增测试Run 45740068529两个Job均completed/success，全库169个unittest通过；增强自检Run 45740213445两个Job均success，熔断OPEN/快速拒绝/HALF_OPEN恢复与零预算失败关闭均PASS，Artifact `ch17-backup-storage-adapter-45740213445`（ID 15081155445）；文档/资源/历史最终同步Run 45740530720两个Job均success，Knowledge lint 0 errors，全库169个unittest通过，Artifact `ch17-backup-storage-adapter-45740530720`（ID 15080399203）。


## CH17-T004 第二十四轮：备份Provider公平调度、租户配额与取消/截止时间

- 新增 `ProviderTaskContext`：调用方显式携带任务ID、租户ID、整数优先级、deadline和线程安全取消事件；嵌套Provider调用自动继承同一上下文。
- 新增按read/write/multipart/inventory域独立的公平舱壁等待队列：较大priority值优先，同分FIFO，等待时间aging增加effective priority以抑制饥饿；可配置每租户域内并发上限。
- 排队、Provider调用边界和重试退避检查取消/截止时间；等待中的取消移除队列项，任务控制异常不计入Provider瞬态失败、不继续重试。
- 新增5项专项unittest和15项公平调度测试规格（ASSET-000069）；默认优先级老化间隔1s、租户限额未配置、bulkhead等待仍默认0s，全部只是实现基线而非生产推荐。
- **限制：** 调度与配额只在一个Adapter/进程/操作域内；同步Provider调用没有强制中断接口，底层连接/读写超时需由真实Provider适配器实现。未执行跨进程/跨容器/真实Provider/生产负载测试。
- **状态：** CH17-T004继续IN_PROGRESS；生产备份仍关闭，治理门禁待企业审批，业务断言未评估。


### 第二十四轮最终验收补记（2026-11-26）

- 首次Run 45741995037因测试模块缺少两个新增异常类型的import而失败；修复提交 `dc2deced6db5138a6880f71df190dd9a6549d45b`。
- 修复后Run 45742134721：Knowledge structure and data quality、CH12 numerical resource tests两个Job均completed/success；全库174个unittest通过，strict knowledge lint 0 errors。
- Provider Mock自检PASS，Artifact ID 15081747151；Provider专项目标46个测试。CH17当前18篇KNOW、68个登记实体、62项资源、9条去重来源。
- 该验收仅覆盖CI与合成/Mock测试，不代表真实Provider、跨进程/跨容器配额、企业业务测试或生产灾备验收。


## CH17-T004 第二十五轮：备份Provider共享协调器、多实例配额和租约恢复

- 新增 `ProviderAdmissionCoordinator` 契约和 `InMemoryProviderAdmissionCoordinator` 合成实现；多个Adapter共享同一对象时，跨实例应用操作域全局并发限额与每租户并发限额。
- 增加共享优先级aging队列、按域令牌桶速率/burst、租约续期/释放/校验、到期回收和单调fencing token；Adapter启用共享协调器后，先拿本地公平舱壁槽位，再获取共享租约。
- 若Provider调用返回时共享租约已过期，返回 `ProviderAdmissionLeaseLostError` 且标明 `outcome_unknown=True`，不报告成功、不自动重试。调用方必须保留原对象键/backup ID进行盘点或幂等验证。
- 新增8项专项unittest，新增ASSET-000070：17个合成跨实例配额、限流、租约、fencing与故障场景。
- **限制：** 当前协调器只共享于同一进程内的多个Adapter对象；无跨进程/主机共享、持久化、自动心跳、quorum、时钟漂移治理或下游fencing验证。lease TTL必须大于Provider硬超时，但当前同步Provider接口不强制实施此超时。
- **状态：** CH17-T004继续IN_PROGRESS；无真实Provider/集群负载测试，生产备份仍关闭，企业治理审批门禁仍阻断。


### 第二十五轮最终CI验收补记（2026-11-26）

- 首次Run 45743739362暴露测试模块遗漏导入 `ProviderTaskContext` 的两处NameError；修复提交 `a77a4b51723fe9f2e01109cca0496cd00d843a37`。
- 同一修复加固租约失效的异常出口检查，新增测试确保租约过期时Provider永久/瞬态错误都不再触发第二次调用。
- 最终Run 45743927996：两个Job completed/success，全库182个unittest通过（Provider专项54个），strict knowledge lint 0 errors，Mock adapter self-check PASS；Artifact ID 15081984380。
- CH17统计19篇KNOW、69个登记实体、63项资源；共享协调仍仅为同进程Mock，不能作为跨进程或生产分布式一致性证据。


### 第二十六轮：共享协调器故障注入与 fail-closed 恢复策略（2026-11-26）

- **交付：** 扩展 KNOW-000039，新增 KNOW-000040；实现协调器可用状态切换和 acquire/acquire_response/renew/release/validate/snapshot 六阶段故障注入；新增 ProviderCoordinatorUnavailableError 与 ProviderCoordinatorStateUnknownError。
- **失败策略：** 当前只实现fail-closed，不支持fail-open。协调器在Provider调用前不可用时不调用Provider；acquire响应丢失时保留TTL租约但不执行Provider；Provider已执行后若无法验证或释放租约，则按outcome-unknown处理并禁止自动重试。
- **资源：** 扩展ASSET-000070测试矩阵至24条。24条全部合成规格，PROPOSED_NOT_APPROVED / NOT_RUN。
- **测试与验收：** 新增6项Provider专项unittest；CI Run 45745399203两个Job均completed/success，全库188项unittest通过，Provider专项共60项；knowledge_lint.py --strict为PASS（0 errors），Provider Mock self-check PASS（Artifact 15083022622）。
- **未实现：** 跨进程协调后端、真实网络分区/主备/quorum、自动租约心跳、下游fencing、最大等待队列、恢复抖动/限速、生产容量与故障演练。
- **状态：** CH17-T004继续IN_PROGRESS；生产备份仍关闭，governance_readiness=BLOCKED_PENDING_ENTERPRISE_APPROVAL，business_rule_assertions=NOT_EVALUATED。

- **CI失败修复记录：** 首轮提交fdac7308f23f4e4ab656174be92f57b987d559fc触发Run 45745264278失败，原因是acquire故障检查错误插入本地ProviderFairBulkhead；修复提交1a9a623e52475059872d8662fb64ee8956b973c2将检查移至共享协调器。最终Run 45745399203通过。
- **治理边界：** 24条故障矩阵全部PROPOSED_NOT_APPROVED / NOT_RUN；生产备份仍关闭，governance_readiness=BLOCKED_PENDING_ENTERPRISE_APPROVAL，business_rule_assertions=NOT_EVALUATED。


## CH17-T004 第二十七轮：Provider准入队列容量保护与恢复期背压

- **实现：** ProviderFairBulkhead与InMemoryProviderAdmissionCoordinator分别新增max_waiters；BackupStorageAdapter暴露bulkhead_max_waiters。默认256仅是实现基线，非生产容量建议；0表示禁止等待但允许立即准入。
- **失败语义：** 队列满抛ProviderAdmissionQueueFullError，并区分local_bulkhead/shared_coordinator；不驱逐既有等待者。协调器在每次等待循环醒来后重新检查可用性，排队期间故障则清理等待者并fail-closed。
- **恢复语义：** 旧等待任务不会自动重放；协调器恢复后需按原任务身份重新查询/提交。令牌桶burst可作为限速边界，但未实现随机jitter、恢复预热/速率斜坡或持久队列。
- **交付：** 新增KNOW-000041和ASSET-000071（7条合成场景）；新增3项Provider专项unittest，并补充配置边界检查。
- **最终验收：** CI Run 45746342659两个必需Job均completed/success；全库191个unittest通过，CH12数控资源测试143项通过；`knowledge_lint.py --strict` 为PASS（0 errors）。Provider适配器测试文件共有64个测试方法定义（含本轮新增3项）。Provider Mock self-check PASS，Artifact ID 15083925258。
- **限制：** 仍仅同进程Mock；无跨进程/主机协调、真实网络故障、生产容量和恢复风暴证据。生产备份保持关闭，CH17-T004继续IN_PROGRESS。


## CH17-T004 第二十八轮：Provider持久化准入协调器与幂等租约

- **实现：** 新增 `SQLiteProviderAdmissionCoordinator`，SQLite WAL + synchronous FULL + `BEGIN IMMEDIATE`；将活动租约、等待者、终态request ID和fencing token序列持久化。
- **准入：** 支持read/write/multipart/inventory域全局容量、租户配额、优先级aging/FIFO和有界共享等待队列；数据库策略哈希不一致时拒绝连接。
- **幂等：** Protocol及InMemory/SQLite实现增加request_id。相同请求身份重放返回原租约；身份冲突和已释放/过期请求键分别拒绝。Adapter每次Provider准入尝试生成request ID；响应丢失时在异常中暴露request_id，调用方可用相同key重放准入。
- **持久化语义：** SQLite租约期限使用Unix wall-clock秒数，支持进程重启后验证；fencing token在事务中持久化单调递增。InMemory依旧使用单调时钟，两个后端的expires_at不可跨实现比较。
- **测试：** 新增11项Provider协调器unittest，含`multiprocessing.spawn`两个子进程同时争抢同一数据库的容量竞争测试、响应丢失后重放、策略冲突、续租、过期回收、独立实例队列可见性。
- **资源：** 新增KNOW-000042与ASSET-000072，10条测试场景全部PROPOSED_NOT_APPROVED / NOT_RUN。
- **边界：** SQLite仅同主机本地文件系统多进程；不支持多主机、NFS/SMB、HA/复制/quorum；无自动心跳、持久QPS令牌桶、下游fencing、文件静态加密/备份恢复、tombstone清理和生产容量测量。墙钟跳变是租约恢复依赖。
- **状态：** CH17-T004继续IN_PROGRESS；生产备份保持关闭，`governance_readiness=BLOCKED_PENDING_ENTERPRISE_APPROVAL`，`business_rule_assertions=NOT_EVALUATED`。


### 第二十八轮最终CI验收与SQLite CLI导入路径修复

- 代码提交 3867b6c2ad3a3ab8832cf518b1c3b27db056bd6f 对应Run 45748405672通过：全库201项unittest、CH12资源测试143项，两个Job success。
- 文档同步提交 8f7211c213131f4ceb972fcbb3228daa2b6b21f4 增加续租测试与SQLite CLI自检。其Run 45748616308中全库202项unittest通过，但SQLite CLI因脚本直接运行时仓库根目录没有加入sys.path而失败。
- 修复提交 8d2a36b6240f20b1968a7e2ef148dcc02e745f88 在CLI入口补充仓库根目录sys.path；最终Run 45748707053两个必需Job均completed/success，全库202项unittest通过，CH12数值资源测试143项通过，strict lint 0 errors。
- SQLite本地持久化自检PASS，Artifact ID 15084821221；Provider Mock adapter self-check PASS，Artifact ID 15084277008。
- ASSET-000072的10项场景仍PROPOSED_NOT_APPROVED / NOT_RUN；本轮没有真实多主机、NFS/SMB、HA、数据库灾备或下游fencing验证。


### 第二十八轮附加诊断回归

- 修复SQLite队列满异常回滚时rejected_queue诊断计数也被回滚的问题；改为准入事务回滚后单独提交计数。
- 新增1项SQLite unittest，验证拒绝新请求、保留活动租约、清理等待者并持久增加rejected_queue。
- ASSET-000072新增SACQ-011；11条场景全部保持PROPOSED_NOT_APPROVED / NOT_RUN。


### 第二十八轮附加队列拒绝计数回归最终验收

- 首轮补充提交 331fe25d4dd966e0e2c97b51d12f9db05c935696 的Run 45749038281仅因新测试遗漏导入ProviderAdmissionQueueFullError发生NameError；队列计数逻辑的回归断言尚未执行。提交 b4dcebb5249546954090a50a1c7dff809796345c补齐import。
- 最终Run 45749107843两个Job均completed/success，全库203项unittest通过，CH12资源143项通过，strict lint 0 errors。
- 队列满诊断回归通过：活动租约保持、没有残留等待者、rejected_queue增加1。SQLite self-check Artifact ID 15083979275。
- ASSET-000072扩展至11条合成场景；全部仍PROPOSED_NOT_APPROVED / NOT_RUN。


## CH17-T004 第二十九轮：Provider fencing 契约与 SQLite 安全恢复

- **目标：** 明确存储端陈旧写入隔离必须由下游原子校验 fencing token，补齐SQLite协调器在线快照和安全恢复准备。
- **交付：** scripts/spare_parts_provider_fencing_contract.py、tests/test_spare_parts_provider_fencing_contract.py、SQLite协调器新增在线备份/验证/新库恢复API及6项专项测试；KNOW-000043；ASSET-000073/000074。
- **验收边界：** 合成存储端只证明合同测试，不代表真实Provider支持；当前BackupStorageAdapter尚未把lease token传递给远端PUT/multipart/receipt。SQLite恢复必须给出独立可信的下游fencing高水位和证据引用，只准备新库，不覆盖原库、不自动cutover。
- **代码验收：** Run 45751336613两个必需Job均success；全库217项unittest、CH12 143项资源测试通过，strict lint 0 errors（5 warnings）。
- **状态：** CH17-T004继续IN_PROGRESS；生产备份仍关闭，治理门禁BLOCKED_PENDING_ENTERPRISE_APPROVAL，业务规则断言NOT_EVALUATED；ASSET-000073/074共16条情景全部PROPOSED_NOT_APPROVED / NOT_RUN。
- **后续：** 完成真实Provider能力合同审查、资源级高水位完整性证明和企业受控恢复演练后，才能评估是否集成真实fencing。不得以Mock测试替代供应商或生产验收。


## CH17-T004 第三十轮：Provider 适配器 fencing token 贯穿

- **目标：** 将 admission lease token 贯穿实际Provider对象写入、multipart和receipt最后提交，阻止同一备份包内的陈旧写入者。
- **实现：** 新增显式 require_provider_fencing=True 严格模式；_bulkhead_slot()向Provider调用提供当前租约；fenced Provider方法接收token和稳定幂等键。以备份 object_prefix 作为统一 fencing_scope，而非每个object key单独计数。
- **交付：** 更新 scripts/spare_parts_backup_storage_adapter.py 与Provider专项测试；新增KNOW-000044和ASSET-000075（12条场景）。
- **测试：** 适配器新增4项unittest，覆盖strict mode门禁、payload/multipart/receipt token传递、同scope跨key旧token拒绝、complete响应丢失重放。默认兼容模式保持非fenced，不能宣称安全模式已启用。
- **验收：** Run 45753519142两个必需Job均success；全库221项unittest、CH12 143项资源测试通过；strict lint 0 errors（5 warnings），Provider self-check token propagation PASS。
- **边界：** FencedMock仅单进程内存模拟，真实云Provider/本地生产Provider仍未接入。真实实现需认证/授权绑定、持久scope高水位和对象/分块/完成/回执原子提交。ASSET-000075全部12条场景PROPOSED_NOT_APPROVED / NOT_RUN；生产备份继续关闭，CH17-T004仍IN_PROGRESS。


## CH17-T004 第三十一轮：SQLite fenced Provider 服务端原子参考实现

- **目标：** 把严格 fencing 从内存Mock提升为同主机可持久化的Provider端事务参考实现；实现主体认证/tenant-action-prefix授权、备份包scope高水位、对象/multipart/幂等和审计原子提交。
- **实现：** 新增 scripts/spare_parts_provider_sqlite_fenced.py。Provider以SQLite WAL、synchronous=FULL、BEGIN IMMEDIATE写事务，把权限校验、旧token比较、对象/分块写入、fence high-water和幂等回执放在同一事务。
- **主体模型：** provisioning时存PBKDF2-HMAC-SHA256 verifier，不存明文secret；每次操作复查主体启用状态和tenant/action/prefix ACL。此为本机可信服务进程凭据，不是TLS/IAM网络认证。
- **恢复：** 支持SQLite online backup、integrity_check/foreign_key_check和新库恢复准备。必须提供独立external_fencing_floor与reconciliation reference；恢复清理未完成multipart会话、提升全部已知scope和全局floor，只准备新库、不cutover。
- **测试：** 新增20项Provider专项unittest，覆盖错误凭据、ACL、租户隔离、scope路径、陈旧token、幂等/冲突、事务rollback、响应丢失、multipart、多进程竞争、备份恢复及严格适配器端到端发布。ASSET-000076定义22条形式化参考验收场景，全部PROPOSED_NOT_APPROVED / NOT_RUN。
- **验收：** [Run 45755448153](https://github.com/rexyll/cnc-knowledge/actions/runs/45755448153)两个必需Job均success；全库241项unittest、CH12 143项通过；strict lint 0 errors（5 warnings）；SQLite fenced Provider self-check PASS（Artifact 15087184041）。
- **剩余安全门禁：** Provider目前不验证token由可信Coordinator签发，持有效本地主体凭据的调用者仍能构造异常大token；生产化前必须增加tenant+scope+token+lease绑定的HMAC/签名attestation。SQLite仅同主机本地文件，不支持NFS/SMB/多主机；真实云/生产Provider未集成；生产备份继续关闭，CH17-T004仍IN_PROGRESS。


## CH17-T004 第三十二轮：Coordinator签名证明、Provider强制验签与密钥轮换

- **目标：** 让Provider验证fencing token确实由可信Coordinator在活动lease下签发，并绑定租户、scope、resource、operation和幂等请求。
- **签发：** 新增scripts/spare_parts_fencing_attestation.py。SQLite Coordinator签发前在BEGIN IMMEDIATE事务中复查lease ACTIVE、过期时间和owner/tenant/domain/token/lease ID；默认证明TTL 15秒，Coordinator配置上限60秒。
- **Claims：** 固定15项claims：v、iss、kid、lease_id、owner_id、tenant_id、domain、fencing_token、issued_at、expires_at、lease_expires_at、fencing_scope、resource_key、operation、idempotency_key；使用规范化JSON和HMAC-SHA256。
- **适配器：** BackupStorageAdapter对每次payload、multipart begin/part/complete和receipt-last写入获取当前lease proof并传入Provider；每次重试获取新lease/proof，保持逻辑idempotency key不变。
- **Provider：** SQLite Provider强制fencing_attestation，校验签名和全部claims，并在写事务内复查trusted_fencing_keys。新增本地admin key registry API，支持ACTIVE/RETIRING/REVOKED，REVOKED不可逆；secret只在运行时注入，不写入SQLite。
- **测试/资产：** Coordinator及Provider增加签名、lease释放、scope、tenant、resource、operation、idempotency、过期proof、key rotation覆盖。新增KNOW-000046和ASSET-000077，20条正式参考验收场景全部PROPOSED_NOT_APPROVED / NOT_RUN。
- **验收：** [CI Run 45758028329](https://github.com/rexyll/cnc-knowledge/actions/runs/45758028329)两个必需Job completed/success；全库248项unittest、CH12 143项通过；strict lint 0 errors（5 warnings）；Provider fenced self-check PASS（Artifact 15087973420），Admission Artifact 15087604559，Adapter Artifact 15087868629。
- **限制：** 当前是本机HMAC共享secret参考方案，Provider进程持有verify secret，不是公钥验签；已签proof在lease release后仍可生存至expires_at，默认最大15秒。admin key API依赖本地数据库文件owner权限。生产远端Provider应改为Coordinator/KMS私钥、Provider公钥的非对称签名，并实现在线撤销、时钟同步、TLS/KMS/HSM；真实网络/多主机Provider未接入。生产备份继续关闭，CH17-T004仍IN_PROGRESS。


## CH17-T004 第三十三轮：Ed25519 v2、公钥验签与在线lease状态查询

- **目标：** 将Coordinator签名证明从HMAC-only参考实现升级到非对称签名；Provider只持公钥，支持在线检查当前lease状态。
- **签名协议：** 保留v1 HMAC-SHA256作为迁移兼容；新增v2.ed25519.kid.payload.signature。新增FencingAttestationSigner协议、Ed25519PrivateKeySigner本地参考实现和CallbackEd25519Signer回调适配接口。Coordinator配置attestation_signer，私钥只在Signer/KMS边界，Coordinator SQLite不保存私钥。
- **KMS边界：** CallbackEd25519Signer可对接外部KMS/HSM的签名回调，但当前没有任何云KMS SDK、凭据、网络调用或真实服务集成。实际KMS Provider/算法策略/密钥IAM仍待后续部署项目。
- **Provider：** 新增trusted_ed25519_keys注册表，保存issuer/key ID、算法、公钥SHA-256指纹、状态与有效时间；Provider只注入公钥。新增admin_register_trusted_ed25519_key、admin_set_trusted_ed25519_key_status，支持ACTIVE/RETIRING/REVOKED。
- **在线状态：** Coordinator新增is_attestation_active(claims)；Provider可开启require_online_attestation_status=True并配置attestation_status_checker。检查发现lease RELEASED/EXPIRED/unknown则拒绝；状态接口不可用时抛FencingAttestationStatusUnavailableError并回滚Provider写事务。
- **竞态限制：** Coordinator和Provider是两个SQLite数据库及事务；lease状态检查成功到Provider commit之间仍有TOCTOU。当前不是线性一致的即时撤销，也无远程HTTP/gRPC checker。真正严格顺序需要同一个线性化事务服务或Provider原生条件写/单调high-water保障。
- **依赖：** requirements-ch17-security.txt锁定cryptography==50.0.2；Knowledge Quality workflow在单测前安装。
- **测试：** 新增Ed25519 callback签发、公钥-only Provider验签、ACTIVE/RELEASED在线检查、Coordinator不可用fail-closed；全库252项unittest通过，CH12 143项通过。
- **资产：** 新增KNOW-000047和ASSET-000078（22条Ed25519/online status参考场景，全部PROPOSED_NOT_APPROVED / NOT_RUN）。本轮真实KMS/HSM和远程多主机场景不具备凭据/环境，不宣称已测试。
- **验收：** 代码提交0912a955通过[CI Run 45760844653](https://github.com/rexyll/cnc-knowledge/actions/runs/45760844653)两个必需Job；252项全库、143项CH12通过，strict lint 0 errors/5 warnings；Provider self-check PASS。
- **安全状态：** HMAC v1仍可用于迁移；生产远端应启用Ed25519/KMS签名、公钥验签、require_online_attestation_status fail-closed，并解决跨事务TOCTOU。真实云Provider/多主机网络仍未接入；生产备份继续关闭，CH17-T004仍IN_PROGRESS。


- 第三十三轮文档同步CI：[Run 45761309007](https://github.com/rexyll/cnc-knowledge/actions/runs/45761309007)两个必需Job success；全库252、CH12 143测试通过，strict lint 0 errors/5 warnings；新增KNOW-000047、ASSET-000078并将CH17统计更新为27/77/71。Provider artifact 15089229555，Coordinator 15089968457。

## CH17-T004 第三十四轮：SQLite 同库原子 lease 撤销与 Provider 写入顺序

- **目标：** 解决第三十三轮独立 Coordinator/Provider SQLite 状态查询与对象提交之间的 TOCTOU 窗口；实现一个显式 opt-in 的本机同库原子参考模式，不将其泛化为远程分布式保证。
- **Coordinator：** 新增 is_attestation_active_in_transaction(connection, claims)，要求传入已打开的 SQLite 写事务连接；检查 connection.in_transaction 和 PRAGMA database_list 的 main 路径，确认与 Coordinator database_path 相同；复用当前 connection 查询活动lease。
- **Provider：** 新增 require_atomic_online_attestation_status=True；该选项要求 require_online_attestation_status=True、checker实现同事务接口且Coordinator/Provider解析后的数据库路径一致，否则Provider启动失败。原有分库在线状态检查保持兼容但仍明确有TOCTOU风险。
- **事务顺序：** Provider通过BEGIN IMMEDIATE先取得数据库写锁，在该连接内核验lease，再执行对象PUT或multipart begin/part/complete，并把对象、scope high-water、幂等receipt和audit放在同一事务。Coordinator release也使用相同数据库的写事务，因此release与Provider mutation只能串行提交：Provider先获得锁则写入先于release，release先获得锁则Provider看到RELEASED并拒绝。
- **测试：** 在Provider专项测试新增配置依赖/路径不一致拒绝，以及并发顺序测试：Provider在事务内完成正向状态检查并暂停时，Coordinator release被同库写锁阻塞；Provider提交后release完成；旧proof再次使用被拒绝。测试使用合成本地SQLite，不构成企业验收。
- **外部依据：** 新增SRC-000391（SQLite Transaction）和SRC-000392（SQLite WAL）；后者明确WAL依赖同机共享内存，不适用于网络文件系统。
- **新增知识与资源：** KNOW-000048；ASSET-000079（12条同库原子撤销场景，均PROPOSED_NOT_APPROVED / NOT_RUN）；补齐既有ASSET-000078结构化实体记录。新增文章 spare-parts-inventory-backup-provider-atomic-lease-revocation.md。
- **代码提交：** Coordinator 1504a0d8；Provider 3bed9959；Provider专项测试 1efa13ad。最终CI以本节后续补录为准。
- **限制：** 仅支持同一主机、同一真实SQLite文件和受支持本地文件系统；WAL/NFS/SMB/多主机不支持；没有真实KMS/HSM、远程Coordinator、真实对象存储或生产Provider接入。数据库共置扩大安全/备份边界，SQLite单写事务限制吞吐。生产备份继续关闭，治理门禁 BLOCKED_PENDING_ENTERPRISE_APPROVAL，CH17-T004保持IN_PROGRESS。

### 第三十四轮最终代码与文档CI验收补记

- **代码与资源验收：** [GitHub Actions Run 45762883991](https://github.com/rexyll/cnc-knowledge/actions/runs/45762883991)两个必需Job均completed/success；全库254项unittest通过（约6.2秒），CH12数值资源143项通过；strict knowledge lint PASS（0 errors，5 warnings）；Provider/Coordinator相关自检所在Job success。
- **最终文档同步验收：** [GitHub Actions Run 45762994591](https://github.com/rexyll/cnc-knowledge/actions/runs/45762994591)两个必需Job均completed/success；全库254项unittest、CH12 143项均通过；strict lint 0 errors/5 warnings；知识结构与数据质量Job结果PASS（0 errors）。
- **Artifacts：** Provider fenced self-check 15091340011；Admission Coordinator self-check 15090661225；BackupStorageAdapter self-check 15090885721；Backup governance readiness 15089609979；CH12 S-curve资源 15090308493。
- **登记：** CH17更新为28篇KNOW、79个登记实体、72项资源、11条去重来源。ASSET-000079的12条形式化场景仍全部PROPOSED_NOT_APPROVED / NOT_RUN；CI单测通过不等于矩阵场景获批或执行。
- **安全边界：** 同库原子模式仅同一主机、同一SQLite文件及受支持的本地文件系统；分库在线检查仍有TOCTOU；WAL不支持网络文件系统/多主机。真实KMS/HSM、远程Provider、企业灾备和生产备份启用仍未完成。

## CH17-T004 第三十五轮：远程 Coordinator 与对象存储 Provider 分布式 fencing 提交协议

- **目标：** 将第三十四轮同机SQLite原子租约检查提升为厂商中立的远程对象存储协议参考；明确多对象payload与单对象提交指针之间的事务边界。
- **关键设计：** 每个tenant+fencing scope维护唯一control object，包含monotonic high-water token、活动lease状态、latest operation sequence、近期receipt和current manifest pointer。大型payload先写入token/operation专属immutable staging key；只有control object使用ETag/generation条件替换成功，manifest才成为可见已提交备份。
- **激活/撤销：** Coordinator先分配高于历史值的token并签发Ed25519 activation proof；Provider对control object执行CAS，将lease推进ACTIVE。撤销同样通过该对象CAS从ACTIVE改REVOKED；只有撤销CAS确认后，Coordinator才能报告release成功。control object CAS分别构成lease激活/撤销/manifest发布的线性化点。
- **写入和恢复：** publish proof额外绑定manifest key、manifest SHA-256和Coordinator分配的operation_sequence；相同sequence/idempotency和operation hash返回原receipt；回执超窗时OUTCOME_UNKNOWN，绝不盲目重放。CAS响应丢失后要求强一致重读并按幂等状态收敛。
- **参考实现：** 新增scripts/spare_parts_provider_distributed_fencing.py，定义ConditionalObjectControlStore、单对象CAS控制面、Ed25519 claims校验、activate/revoke/publish状态机、有限receipt和单进程InMemoryConditionalObjectControlStore合成模型；新增tests/test_spare_parts_provider_distributed_fencing.py（14项测试）。
- **厂商映射：** 新增SRC-000393 S3 Conditional Writes、SRC-000394 GCS Request Preconditions、SRC-000395 Azure Blob ETag/Lease并发控制、SRC-000396 Azure Blob无跨Blob事务说明。未创建AWS/GCS/Azure SDK或网络适配器。
- **新增知识和资源：** KNOW-000049；ASSET-000080（20条参考场景，均PROPOSED_NOT_APPROVED / NOT_RUN）；新增分布式fencing技术正文和资源索引。
- **代码验收：** Commit 430816f0b466a6040cd0a48e4bf1730c7f4afb4c；[Run 45767324560](https://github.com/rexyll/cnc-knowledge/actions/runs/45767324560)两个必需Job均completed/success；全库268项unittest、CH12数值资源143项通过；strict lint 0 errors / 5 warnings；知识结构与数据质量0 errors。
- **生产边界：** InMemoryConditionalObjectControlStore只模拟单进程CAS，不是多主机服务。现有Coordinator尚未实现fencing:activate/revoke/publish操作proof远程端点，也尚未分配持久operation_sequence；无真实KMS/HSM、IAM/RBAC策略、远程HTTP/gRPC、S3/GCS/Azure SDK和对象存储集成。生产备份继续关闭，治理门禁 BLOCKED_PENDING_ENTERPRISE_APPROVAL。

### 第三十五轮最终文档同步验收补记

- **最终文档提交：** 52bab72e401c39254b5c9aff2339e51ca5d36560。
- **最终文档同步CI：** [Run 45767658789](https://github.com/rexyll/cnc-knowledge/actions/runs/45767658789)两个必需Job均completed/success；全库268项unittest、CH12数值资源143项均通过；strict knowledge lint PASS（0 errors，5 warnings）；知识结构与数据质量PASS（0 errors）。
- **Artifact：** CH12 S-curve synthetic 15091879973；BackupStorageAdapter self-check 15093210029；Provider admission 15092029877；SQLite fenced Provider 15092204228；Backup governance readiness 15092980848。
- **登记：** CH17更新为29篇KNOW、81个登记实体、73项资源、15条去重来源。ASSET-000080的20条分布式fencing场景全部PROPOSED_NOT_APPROVED / NOT_RUN。
- **边界：** 本轮验证只覆盖单进程内存CAS参考模型；无远程Coordinator、云对象存储SDK、真实KMS/HSM、IAM/RBAC配置或多主机故障演练。生产备份继续关闭，CH17-T004仍IN_PROGRESS。


## CH17-T004 第三十六轮：Coordinator 持久权威、Leader epoch 与两阶段恢复

- **目标：** 在KNOW-000049单对象分布式fencing协议之上，增加Coordinator本地持久权威参考层，保证tenant-qualified scope token、publish operation sequence、Leader epoch、幂等操作和Provider结果确认可在进程重启后追溯。
- **代码：** 新增 `scripts/spare_parts_provider_coordinator_authority.py` 与 `tests/test_spare_parts_provider_coordinator_authority.py`。使用同一Admission SQLite文件及WAL/BEGIN IMMEDIATE，新增leader、scope authority、operation ledger和schema版本表。
- **租户与序列：** scope强制 `tenants/<tenant_id>/...` 命名空间；每scope单调token及operation sequence独立持久化；idempotency key绑定规范化request SHA-256，冲突内容拒绝。
- **两阶段状态：** activation为PENDING_ACTIVATION→Provider control object CAS/强一致读回→ACTIVE；revoke为ACTIVE→REVOKING→Provider CAS/读回→REVOKED；publish先分配sequence、签署绑定manifest key/SHA-256 proof，再以完整Provider receipt确认COMMITTED。
- **Leader隔离：** 全局Leader lease持久化leader_id/epoch/expires_at；prepare/confirm/renew和proof签发均核验当前Leader，proof签发前还重新核对operation ledger仍处于pending。新Leader可恢复并重新签署仍pending的原operation；旧Leader缓存对象不得签新proof或确认。
- **恢复：** `list_pending_operations()`不自动补成功；须强一致读取Provider control object与receipt后精确确认。数据库从旧备份恢复时要求独立token/sequence/Leader epoch floors；`reconcile_after_restore()`提升高水位、置RECOVERY_REQUIRED及RECOVERY_REVIEW，不自动cutover。
- **测试：** 新增15项本地合成Coordinator authority unittest，覆盖端到端activation/publish/revoke、重启持久化、幂等与冲突、并发sequence分配、Leader TTL接管、proof签发旧Leader拒绝、新Leader恢复pending和外部高水位恢复门禁。
- **新增知识/资源：** KNOW-000050；ASSET-000081为16条场景矩阵，全部PROPOSED_NOT_APPROVED / NOT_RUN；复用SRC-000391/392（SQLite Transaction/WAL）。
- **限制：** 同机本地SQLite参考，不支持NFS/SMB或多主机；没有远程共识服务/Coordinator API、KMS/HSM、真实云Provider/IAM/Gateway或生产灾备环境。已签发且未过期的旧短时proof不能仅由本地Leader epoch变化撤销，仍依赖Provider token high-water、TTL和CAS防线。生产备份关闭，治理门禁不变。


### 第三十六轮最终代码与文档同步CI验收补记

- **代码提交：** `abb73ebd6e3268d15f149333d904369c5cc1a42d`；[Run 45769331991](https://github.com/rexyll/cnc-knowledge/actions/runs/45769331991)两个必需Job均completed/success。
- **文档同步提交：** `262c7fe71f0a436ec1b95686cbb1c6c7448b2575`；[Run 45769584662](https://github.com/rexyll/cnc-knowledge/actions/runs/45769584662)两个必需Job均completed/success。
- **验证：** 两次最终CI均全库283项unittest、CH12 143项数值资源测试通过；strict knowledge lint PASS（0 errors，5 warnings）；知识结构与数据质量PASS（0 errors）。
- **资源/覆盖：** 新增KNOW-000050、ASSET-000081（16条参考场景，全部PROPOSED_NOT_APPROVED / NOT_RUN）；CH17更新为30篇KNOW、83个登记实体、74项资源、15条去重来源。
- **边界：** 代码只支持同一主机本地SQLite WAL；无多主机分布式共识、远程Coordinator、KMS/HSM、真实云Provider/IAM Gateway或企业灾备验收。生产备份仍关闭，CH17-T004为IN_PROGRESS。


## CH17-T004 第三十七轮：Coordinator 后端契约与 etcd v3 一致性适配设计

- **目标：** 在第三十六轮持久Coordinator领域状态机基础上，将应用服务端口与低层原子KV/Txn/Lease端口分离，为多主机强一致后端预留可验证契约。
- **应用端口：** 新增 `DurableCoordinatorAuthorityBackend` Protocol，描述Leader、activation/revoke、sequence、publish确认、proof签发门禁及恢复接口；现有`SQLiteDurableCoordinatorAuthority`通过结构化Protocol测试。
- **存储端口：** 新增 `CoordinatorAuthorityStore` Protocol，要求线性一致Get、Compare/Success/Failure原子Txn、多key同一修订写入，以及Lease Grant/KeepAlive/Revoke。
- **适配器：** 新增`SQLiteCoordinatorAuthorityStore`本地WAL参考适配器；新增`EtcdV3CoordinatorAuthorityStore`，将线性一致Range(serializable=false)、KV Txn Compare与Lease API映射到注入式`EtcdV3Client` driver；新增`InMemoryEtcdV3Client`仅用于单进程合成测试。
- **关键安全要求：** 每次关键Txn对LeaderKey revision/epoch、scope mod_revision和幂等记录做条件比较；Lease/Lock本身不保证旧进程停止，也不保护外部Provider；Watch只用于通知，权威判断重新线性一致读取；Txn响应丢失必须OUTCOME_UNKNOWN并按原幂等键读回。
- **测试：** 新增底层跨适配器一致性测试，覆盖KV线性一致读、事务CAS、多key revision、失败分支、并发单赢家、Lease过期/撤销、旧Leader revision compare和Txn响应丢失。
- **外部依据：** 新增SRC-000397～SRC-000401（etcd官方API guarantees、KV Txn/Lease、Election LeaderKey、Lease/Lock边界、failure modes）。
- **知识与资源：** KNOW-000051；ASSET-000082（20条多主机/etcd要求场景，全部PROPOSED_NOT_APPROVED / NOT_RUN）。
- **集成边界：** EtcdV3Client是注入式API driver接口，不是已安装/连接的gRPC或JSON Gateway客户端。SQLite领域状态机仍直接使用SQL，尚未重构为通过低层store port执行；etcd层也未做真实服务集成。无mTLS/RBAC、真实quorum/网络分区/多主机及Provider故障演练。


### 第三十七轮最终代码与文档同步CI验收补记

- **最终代码提交：** `e274067e7e601c026252ddf3dacb87db5971bd63`；[Run 45770717942](https://github.com/rexyll/cnc-knowledge/actions/runs/45770717942)两个必需Job均completed/success。
- **最终文档提交：** `3a83763239ec2ecda8607eca0977139c41dd6df9`；[Run 45770955018](https://github.com/rexyll/cnc-knowledge/actions/runs/45770955018)两个必需Job均completed/success。
- **测试与质量：** 两次最终CI均全库300项unittest、CH12数值资源143项通过；strict lint 0 errors/5 warnings；知识结构与数据质量0 errors。
- **覆盖：** 新增KNOW-000051、ASSET-000082及SRC-000397～SRC-000401；CH17为31篇KNOW、85个登记实体、76项资源、20条去重来源。ASSET-000082的20条场景全部PROPOSED_NOT_APPROVED / NOT_RUN。
- **集成边界：** SQLite业务服务仍SQL专用；etcd v3仅底层注入式客户端适配器设计，未连接真实etcd server、mTLS/RBAC或多主机集群。未做quorum、网络分区、Leader failover或云Provider故障演练。


## 6.10 CH17-T004 第三十八轮：Coordinator事务内有序读取基础（2026-11-26）

- **目标：** 为Coordinator状态机向通用KV/Txn端口迁移补齐事务分支内读取能力，避免读取与CAS写被拆成不同一致性时点。
- **实现：** `CoordinatorAuthorityStore.transact` 的Success/Failure分支现在支持 `AuthorityStoreGet`、Put和Delete按列表顺序执行；结果增加按Get顺序排列的 `reads` 元组。SQLite在同一个 `BEGIN IMMEDIATE` 中完成；etcd将Get映射为同一个Txn分支内的 `request_range`。
- **测试：** 新增分支内写前/写后读取及Compare失败后Failure分支快照测试。SQLite与InMemoryEtcdV3Client两种适配器各运行两项新增测试，共4次执行。代码CI Run 45772420144通过：全库304项unittest、CH12 143项测试，strict lint 0 errors/5 warnings，结构质量0 errors。
- **知识与资源：** KNOW-000052；ASSET-000083定义16条场景，均 `PROPOSED_NOT_APPROVED / NOT_RUN`；复用SRC-000397/398与SRC-000391/392。
- **未完成边界：** `SQLiteDurableCoordinatorAuthority` 仍直接使用SQL领域表；Admission lease仍通过同库 `admission_requests` 表事务校验，未迁移到通用Store。etcd仍是注入式API driver，无真实集群、gRPC/JSON Gateway、mTLS/RBAC、quorum或多主机证据。后续必须先把Admission lease权威记录及续租/释放迁移到同一强一致Txn后端，再迁移Leader、scope和operation ledger；禁止将独立Admission Range与后续authority Txn组合成存在TOCTOU的流程。
- **状态：** CH17-T004保持IN_PROGRESS；生产备份关闭、治理门禁和业务断言状态不变。


### 第三十八轮文档同步CI验收补记

- **文档提交：** `a1548dad6ad1c47d4645600a162a866076de6993`；[Run 45772844275](https://github.com/rexyll/cnc-knowledge/actions/runs/45772844275)两个必需Job均completed/success。
- **质量结果：** 全库304项unittest、CH12 143项数值资源测试通过；strict knowledge lint 0 errors/5 warnings；知识结构与数据质量0 errors。
- **状态：** ASSET-000083的16条场景仍全部PROPOSED_NOT_APPROVED / NOT_RUN；领域状态机和Admission lease尚未迁移到CoordinatorAuthorityStore；生产备份关闭，治理门禁不变。


## 6.11 CH17-T004 第三十九轮：Admission Lease Authority统一事务参考组件（2026-11-26）

- **目标：** 在KNOW-000051/052定义的CoordinatorAuthorityStore与事务内读写契约上，建立后端无关Admission lease生命周期与authority事务保护比较。
- **实现：** 新增 `scripts/spare_parts_provider_admission_authority_store.py` / `StoreBackedAdmissionLeaseAuthority`。活动lease键附着backend TTL Lease；request_id索引为持久幂等/终态tombstone；全局fencing token通过counter revision CAS递增。Acquire原子写counter/lease/request，renew同Txn切换backend lease并更新两条记录，release同Txn删除活动键并写RELEASED。新增 `active_lease_compares()` 与 `transact_with_active_lease()`，让调用方把Admission lease检查与Leader/scope/operation写入置于同一Txn。
- **测试：** 新增5个契约测试方法，SQLite与InMemoryEtcdV3Client分别执行，共10次适配器测试执行；覆盖幂等、身份冲突、终态request ID、token单调、renew/release、TTL失效、Txn guard竞争和提交响应丢失恢复。代码CI Run 45775642132通过：全库314项unittest、CH12 143项测试、strict lint 0 errors/5 warnings、结构质量0 errors。
- **知识/资源：** 新增KNOW-000053和ASSET-000084；20条场景均 `PROPOSED_NOT_APPROVED / NOT_RUN`；复用SRC-000391/392/397/398。
- **未完成边界：** 这不是完整Admission scheduler迁移。旧SQLite代码仍持有等待队列、fair scheduling、global/tenant capacity quota、policy hash与Admission lease表；不能把其中一部分单独迁移并双写。SQLiteDurableCoordinatorAuthority也尚未通过store port执行。下一步需把队列/配额/lease/counter/idempotency和Coordinator Leader/scope/operation状态共同迁移，且保护写必须在同一Txn带入lease guard。真实etcd、mTLS/RBAC、quorum、多主机和Provider故障演练未完成。
- **状态：** CH17-T004保持IN_PROGRESS；生产备份关闭，治理门禁BLOCKED_PENDING_ENTERPRISE_APPROVAL，business_rule_assertions=NOT_EVALUATED。


### 第三十九轮文档同步CI验收补记

- **文档提交：** `b79aede8a06cc55ac60681cbfc9acf03b1f44a55`；[Run 45776156101](https://github.com/rexyll/cnc-knowledge/actions/runs/45776156101)两个必需Job均completed/success。
- **质量结果：** 全库314项unittest、CH12 143项数值资源测试通过；strict knowledge lint 0 errors/5 warnings；知识结构与数据质量0 errors。
- **状态：** ASSET-000084的20条场景仍全部PROPOSED_NOT_APPROVED / NOT_RUN；旧SQLite Admission排队/配额调度与SQLite Coordinator领域状态机未迁移；生产备份关闭，治理门禁不变。


### 第三十九轮最终元数据CI验收

- 最终元数据提交 `7209c094079830eb0789fbbe041757ee764e611c`；[Run 45776292616](https://github.com/rexyll/cnc-knowledge/actions/runs/45776292616)两个必需Job均completed/success。
- 全库314项unittest、CH12 143项数值资源测试通过；strict lint 0 errors/5 warnings；知识结构质量0 errors。
- ASSET-000084的20条场景仍全部PROPOSED_NOT_APPROVED / NOT_RUN；生产备份关闭，业务断言NOT_EVALUATED。


## 6.12 CH17-T004 第四十轮：Unified Admission Scheduler与配额状态统一事务模型（2026-11-26）

- **目标：** 将Admission全局/租户配额、跨domain等待队列、公平调度、fencing token、活动Lease和request_id幂等收敛到同一个强一致Txn权威快照，避免lease与容量计数分开提交。
- **实现：** 新增 `scripts/spare_parts_provider_unified_admission_store.py` / `StoreBackedProviderAdmissionCoordinator`。单一revisioned aggregate保存policy hash、global/tenant limits、活动集合、waiters、fencing/waiter序号和统计；活动Lease键附着backend TTL，request索引持久保留。Acquire在同一个Txn比较aggregate revision、当前所有活动Lease/request精确值、目标键不存在，并一次写入aggregate/token/活动Lease/request；renew与release同步更新aggregate和两个索引。Waiter按priority + age/aging interval排序，sequence用于同分平局，全局max_waiters跨domain生效。
- **并发与过期：** 事务根据线性一致读到的活动键构建精确Compare；backend TTL删除或lease变化会令原Txn比较失败。expired lease在成功CAS中从active map清理并把request记录标记EXPIRED。CAS失败重新读取最新状态，不使用陈旧容量计数。
- **Namespace：** 使用 `/cnc/admission/unified/v2/` 与第三十九轮独立Lease Authority键空间隔离；禁止两套Authority对同一业务范围并行写入或双写。
- **测试：** 新增6个测试方法，SQLite与InMemoryEtcdV3Client分别执行，共12次适配器测试执行，覆盖global/tenant quota、跨实例不超卖、公平队列/aging、waiter上限与清理、TTL回收、renew/release与同Txn authority guard、request幂等与竞争。最终代码CI Run 45778008494两个必需Job通过：全库328项unittest、CH12 143项数值资源测试通过；strict knowledge lint 0 errors；知识结构与数据质量0 errors。
- **知识/资源：** 新增KNOW-000054、ASSET-000085；24条正式验收场景均 `PROPOSED_NOT_APPROVED / NOT_RUN`；复用SRC-000391/392/397/398。
- **限制：** 单aggregate状态键让所有domain更新全局串行化，且每次事务需比较活动集合；这是正确性参考基线，不是高吞吐/生产规模设计。旧 `SQLiteProviderAdmissionCoordinator` 的数据、队列、策略及旧 `SQLiteDurableCoordinatorAuthority` 仍未迁移；真实etcd、gRPC/JSON Gateway、mTLS/RBAC、quorum、多主机、Provider端到端和分片吞吐尚未验证。禁止与旧scheduler双写。
- **状态：** CH17-T004保持IN_PROGRESS；生产备份关闭，治理门禁BLOCKED_PENDING_ENTERPRISE_APPROVAL，business_rule_assertions=NOT_EVALUATED。


### 第四十轮文档同步CI验收补记

- **文档提交：** `87d749147d2c32da547ce23ed56db69725271a00`；[Run 45778328441](https://github.com/rexyll/cnc-knowledge/actions/runs/45778328441)两个必需Job均completed/success。
- **质量结果：** 全库328项unittest、CH12 143项数值资源测试通过；strict knowledge lint 0 errors；知识结构与数据质量0 errors（报告5条非阻断warning）。
- **状态：** ASSET-000085的24条场景仍全部PROPOSED_NOT_APPROVED / NOT_RUN；旧SQLite Admission及Coordinator领域服务未迁移；生产备份关闭，治理门禁不变。


### 第四十轮文档同步CI验收补记

- **文档提交：** `87d749147d2c32da547ce23ed56db69725271a00`；[Run 45778328441](https://github.com/rexyll/cnc-knowledge/actions/runs/45778328441)两个必需Job均completed/success。
- **质量结果：** 全库328项unittest、CH12 143项数值资源测试通过；strict knowledge lint 0 errors；知识结构与数据质量0 errors（报告5条非阻断warning）。
- **状态：** ASSET-000085的24条场景仍全部PROPOSED_NOT_APPROVED / NOT_RUN；旧SQLite Admission与Coordinator领域服务尚未迁移；生产备份关闭，治理门禁不变。


## 6.13 CH17-T004 第四十一轮：Coordinator Leader / Scope / Operation统一事务（2026-11-26）

- **目标：** 将旧 `SQLiteDurableCoordinatorAuthority` 的Leader epoch、每个tenant scope的high-water fencing token、ACTIVATE/REVOKE/PUBLISH两阶段操作、publish sequence与恢复审查状态，纳入第四十轮统一Admission scheduler的同一个存储aggregate。
- **实现：** 新增 `scripts/spare_parts_provider_unified_coordinator_authority.py` / `StoreBackedCoordinatorAuthority`。统一Admission aggregate schema升级为v2，namespace为 `/cnc/admission/unified/v2/`；`aggregate.coordinator` 保存Leader镜像、scope map和operation map。Leader KV key附着backend TTL Lease，与aggregate Leader状态同Txn更新。Coordinator状态转换比较aggregate revision、Leader TTL key精确值，并在操作关联Admission Lease时追加活动Lease与request index精确值Compare。
- **Leader：** claim单调递增epoch、拒绝有效TTL key重复claim；恢复claim需要严格更高外部epoch floor与reconciliation reference；renew更换TTL Lease但不改变epoch。Leader TTL过期/新epoch takeover后，旧epoch不能继续授权operation/signing。
- **Scope/Operation：** tenant scope规范化；ACTIVATE prepare提升scope high-water token并进入PENDING_ACTIVATION，只有Provider read-back才能confirm ACTIVE；REVOKE需精确ACTIVE lease/token并read-back confirm；PUBLISH仅对ACTIVE scope lease分配每scope单调sequence，receipt匹配token/sequence/manifest后才COMMITTED；operation idempotency key绑定canonical request digest。
- **签名授权：** `sign_distributed_fencing_proof()`改成backend-neutral authority port，要求`authorize_operation_signing()`，持久比对operation身份字段（含owner/tenant/domain/lease expiry），可由SQLite与Unified Coordinator共用。测试用Ed25519 signer及InMemoryConditionalObjectControlStore完成合成Provider端到端流程。
- **恢复：** external high-water与sequence floors不得低于持久状态；pending operations降为RECOVERY_REVIEW，scope进入RECOVERY_REQUIRED，返回automatic_cutover=false，不自动提升为ACTIVE/COMMITTED。
- **测试：** 新增8个契约测试方法，SQLite与InMemoryEtcdV3Client各运行一次，共16次适配器测试执行。覆盖端到端ACTIVATE/PUBLISH/REVOKE、Leader expiry/takeover、epoch recovery floor、scope tenant boundary、idempotency、并发sequence唯一、restore review、同aggregate及Admission release guard、签名身份篡改拒绝。最终代码提交 `3d79149c1112550b4fb25efbe02b5f536b08cacd`；[CI Run 45810737444](https://github.com/rexyll/cnc-knowledge/actions/runs/45810737444)两个必需Job通过，全库344项unittest、CH12 143项测试通过，strict lint 0 errors，结构质量0 errors。
- **知识/资源：** 新增KNOW-000055、ASSET-000086；35条场景均 `PROPOSED_NOT_APPROVED / NOT_RUN`；复用SRC-000391/392/397/398。
- **限制：** 旧 `SQLiteDurableCoordinatorAuthority` 与 `SQLiteProviderAdmissionCoordinator` 未替换；v1→v2生产导入/回滚cutover未实现；真实etcd、mTLS/RBAC/quorum、多主机和外部Provider未验证。单aggregate仍是全局写热点，operation map会增长，必须有受控归档/分片方案和容量证明。
- **状态：** CH17-T004仍为IN_PROGRESS；生产备份关闭，治理门禁BLOCKED_PENDING_ENTERPRISE_APPROVAL，business_rule_assertions=NOT_EVALUATED。


### 第四十一轮文档同步CI验收补记

- **文档提交：** `706cfcf36204c1bfe996501e65031a21e8536783`；[Run 45811108498](https://github.com/rexyll/cnc-knowledge/actions/runs/45811108498)两个必需Job均completed/success。
- **质量结果：** 全库344项unittest、CH12 143项数值资源测试通过；strict knowledge lint 0 errors；知识结构与数据质量0 errors（5条非阻断warning）。
- **状态：** ASSET-000086的35条场景仍全部PROPOSED_NOT_APPROVED / NOT_RUN；旧SQLite Coordinator和Admission服务仍未迁移；生产备份关闭，治理门禁不变。


### 第四十一轮文档同步CI验收补记

- **文档提交：** `706cfcf36204c1bfe996501e65031a21e8536783`；[Run 45811108498](https://github.com/rexyll/cnc-knowledge/actions/runs/45811108498)两个必需Job均completed/success。
- **质量结果：** 全库344项unittest、CH12 143项数值资源测试通过；strict knowledge lint 0 errors；知识结构与数据质量0 errors（5条非阻断warning）。
- **状态：** ASSET-000086的35条场景仍全部PROPOSED_NOT_APPROVED / NOT_RUN；旧SQLite Coordinator / Admission仍未迁移；生产备份关闭，治理门禁不变。


### 第四十一轮文档同步CI验收补记

- **文档提交：** `706cfcf36204c1bfe996501e65031a21e8536783`；[Run 45811108498](https://github.com/rexyll/cnc-knowledge/actions/runs/45811108498)两个必需Job均completed/success。
- **质量结果：** 全库344项unittest、CH12 143项数值资源测试通过；strict knowledge lint 0 errors；知识结构与数据质量0 errors（5条非阻断warning）。
- **状态：** ASSET-000086的35条场景仍PROPOSED_NOT_APPROVED / NOT_RUN；旧SQLite Coordinator及Admission服务尚未迁移；生产备份保持关闭。


## 6.14 CH17-T004 Unified Coordinator Aggregate容量画像（第四十二轮，2026-11-26）

- **目标：** 在不改变schema-v2状态机、不接入真实存储的前提下，量化单aggregate内scope、operation ledger、活动Admission lease和waiter的合成数据增长。
- **代码：** 新增 scripts/spare_parts_coordinator_capacity_probe.py；使用现有Admission/Coordinator记录构造器与canonical JSON编码，支持14条CSV profile执行和JSON stdout报告。
- **测试：** 新增 tests/test_spare_parts_coordinator_capacity_probe.py，共12个测试方法，覆盖canonical字节对齐、scope/operation增长、活动lease比较项模型、只读性、阈值参数、异常输入和矩阵唯一性。
- **资料：** 新增 KNOW-000056、ASSET-000087、SRC-000402；正文为 docs/17-operation-maintenance-and-repair/spare-parts-inventory-backup-provider-coordinator-capacity-model.md，场景矩阵归档于 resouces/17-operation-maintenance-and-repair/spare-parts-coordinator-capacity-profile-v1.csv。
- **测量边界：** JSON aggregate value字节数为精确值；完整etcd请求大小只得到下界，协议封装和传输请求未测。比较项数为基于当前实现的结构模型，不是RPC延迟/吞吐测量。
- **安全边界：** 50%仅为画像展示预算，不设生产硬限制、不修改运行写入行为。所有数据均为合成数据；未连接真实etcd、SQLite生产库或对象存储Provider。
- **状态：** 该切片交付后，CH17-T004仍保持 IN_PROGRESS；真实etcd容量与性能、operation ledger归档/分片、迁移与cutover仍未完成。


### 第四十二轮CI验收补记（2026-11-26）

- **实现提交：** `f52937e1af7b622c11801e2ca502661365e75d05`；[GitHub Actions Run 45814052446](https://github.com/rexyll/cnc-knowledge/actions/runs/45814052446)两个必需Job均completed/success。
- **质量结果：** 全库356项unittest（包括新增12个容量探针测试）、CH12 143项数值资源测试通过；strict knowledge lint 0 errors；知识结构与数据质量0 errors（5项非阻断warning）。
- **范围说明：** 14个容量profile通过CI中的合成构造/统计测试。真实etcd集群、实际gRPC/protobuf请求大小、Txn latency/throughput及多主机故障未测；生产容量门禁尚未建立。
- **状态：** KNOW-000056 / ASSET-000087已登记；ASSET-000087仍为PROPOSED_NOT_APPROVED，真实容量验收NOT_RUN。CH17-T004继续IN_PROGRESS。


## 6.15 CH17-T004 Coordinator Operation Ledger生命周期与安全归档（第四十三轮，2026-11-26）

- **目标：** 定义历史Operation Ledger从hot aggregate向不可变归档介质迁移的安全协议，避免归档破坏幂等、fencing和恢复审查。
- **核心协议：** 只选择COMMITTED/REVOKED及已被明确取代的旧ACTIVE ACTIVATE；任何PENDING_ACTIVATION、REVOKING、PENDING_PUBLISH、RECOVERY_REVIEW都会阻断该scope归档。归档对象先写入并读回校验，再由Coordinator权威scope pointer执行CAS切换；CAS冲突保留hot records，可能产生的orphan对象不在本事务删除。
- **幂等和恢复：** 精确idempotency index跨manifest链查找；archive outage/corruption时fail-closed。high_water_token与latest_operation_sequence不得下降；归档不自动完成恢复、重新绑定Lease或改变Provider状态。
- **新增参考模型：** scripts/spare_parts_operation_ledger_archive.py；新增tests/test_spare_parts_operation_ledger_archive.py，共24个测试方法；新增25项正式待批准场景矩阵ASSET-000088及来源SRC-000403～SRC-000405。
- **范围边界：** 参考模型仅用内存archive adapter，不修改StoreBackedCoordinatorAuthority schema-v2，不连接SQLite/真实etcd/对象存储。生产归档、schema v3迁移、保留期、法律保留、WORM/密钥和物理删除策略均未批准。
- **状态：** CH17-T004继续IN_PROGRESS；本轮只完成协议设计与参考模型，不能视为生产归档功能或企业验收完成。


### 第四十三轮CI验收补记（2026-11-26）

- **最终代码/测试head：** 4ed91a04138e30ecf2275c07bb947ecc872fadd2；[GitHub Actions Run 45817146500](https://github.com/rexyll/cnc-knowledge/actions/runs/45817146500)两个必需Job均completed/success。
- **质量结果：** 全库380项unittest通过（新增24项归档参考模型测试）；CH12 143项数值资源测试通过；strict knowledge lint 0 errors；知识结构与数据质量0 errors。5项warning来自既有合成夹具治理检查。
- **修正记录：** 首次CI发现未知提交响应测试的故障注入发生在归档准备前；提交 f8e373411c3612b733d525b475cf64dcd79ed699 修正。第二次CI发现测试断言字段名不一致；提交 4ed91a04138e30ecf2275c07bb947ecc872fadd2 修正，最终Run通过。
- **状态：** KNOW-000057 / ASSET-000088已同步CI证据；25项正式归档场景依旧PROPOSED_NOT_APPROVED / NOT_RUN。参考模型没有连接真实etcd、SQLite生产库或对象存储，CH17-T004继续IN_PROGRESS。


## 6.16 CH17-T004 Archive Index与Schema v3迁移/回滚（第四十四轮，2026-11-26）

- **目标：** 将历史幂等查询从全manifest链线性扫描优化为可验证的精确分片索引，并定义单权威、冻结写入、对象先建后切换的schema-v2到v3迁移协议。
- **Archive Index：** 新增 scripts/spare_parts_operation_archive_index.py，支持16/256/4096桶，提供manifest链全量回填、按触及bucket增量更新、root/shard/batch三层摘要验证、精确hit/miss和full-chain audit。查询必须带入从Coordinator scope独立读取的archived_operation_count；不能用Bloom Filter代替精确negative判定。
- **Schema Migration：** 新增 scripts/spare_parts_coordinator_schema_migration.py；冻结v2写入，捕获source revision/digest，构造分离scheduler、Leader、scope、hot-operation与archive-index-pointer对象，校验operation数量/键集合/fencing和sequence floors，再通过单控制指针CAS切换。
- **Rollback：** V3尚未接受mutation时可在冻结窗口切回未变化的v2快照；V3接受第一笔mutation后禁止直接回指旧快照。若需反向迁移，必须冻结V3、完整重建archive历史和v2 shadow、验证所有操作/外部floor及v2容量后再切换，否则向前修复。
- **测试/资源：** 新增2个实现文件与2个测试文件，共46个自动化测试方法；新增KNOW-000058、ASSET-000089和47项企业正式场景矩阵；来源沿用SRC-000403～SRC-000405。
- **范围：** 两个脚本均为纯内存参考模型；不修改StoreBackedCoordinatorAuthority生产schema-v2，不接入真实etcd/对象存储，不执行迁移/cutover/回滚。ASSET-000089保持PROPOSED_NOT_APPROVED / NOT_RUN。
- **状态：** CH17-T004继续IN_PROGRESS；schema-v2仍是唯一生产权威，生产归档与Schema v3均未启用。


### 第四十四轮CI验收补记（2026-11-26）

- **最终代码/测试head：** `2b66224909d2bcd9b326c1cffcf220bef5d14b7f`；[GitHub Actions Run 45819520749](https://github.com/rexyll/cnc-knowledge/actions/runs/45819520749)两个必需Job均completed/success。
- **质量结果：** 全库426项unittest通过（本轮新增21项索引测试+25项迁移测试，共46项）；CH12 143项数值资源测试通过；strict knowledge lint 0 errors；知识结构与数据质量0 errors。另有5项既有合成fixture的非阻断warning。
- **修正记录：** 首轮CI发现两个测试夹具前置条件不正确：历史指针测试使用了当前archived count，reverse-migration size测试未进入V3冻结反向迁移状态。最终修正提交为 `2b66224909d2bcd9b326c1cffcf220bef5d14b7f`，Run 45819520749通过。
- **状态：** KNOW-000058 / ASSET-000089已同步；47项正式场景仍PROPOSED_NOT_APPROVED / NOT_RUN。参考模型没有连接真实etcd/对象存储，没有执行生产Schema v3迁移或回滚；CH17-T004继续IN_PROGRESS。


## 6.17 CH17-T004 Coordinator Schema v3分片准入与分布式事务预算（第四十五轮，2026-11-26）

- **目标：** 在不替换schema-v2生产权威的情况下，建立Tenant分区Admission模型，避免全局aggregate revision与活动Lease逐项Compare造成的跨Tenant写冲突。
- **双槽容量：** 新增 scripts/spare_parts_provider_admission_partition_model.py。每次Admission必须在同一Txn原子占用一个global/domain permit slot和一个tenant/domain permit slot；活动lease record与两个slot附着同一native TTL Lease，request idempotency tombstone保持持久。槽池长度直接约束global与tenant最大并发，不通过每次Acquire更新单一全局计数器。
- **队列与公平：** waiter按tenant hash路由；跨Tenant采用round-robin，Tenant内部使用priority+aging及local FIFO。该策略与V2全局priority+aging排序不完全等价，列为显式业务策略变更，未经批准不切换。dispatch使用有界batch及queue-head/dispatcher epoch保护。
- **Fencing：** 每个partition单Leader；Leader在token block耗尽时从全局high-water预留非重叠区间。Leader故障时丢弃未使用尾部区间，新Leader以更高epoch和外部floor预留新range；允许token空洞，不允许复用。不同partition token数值不代表跨partition时间顺序。
- **事务预算：** 新增EtcdTransactionBudget，估算Compare + max(success, failure)和canonical JSON模型字节；默认分析目标70%仅是本项目安全余量，不是服务端限制。16分区/4grant dispatch模型计58操作，64分区/4grant模型计106，超出70%参考预算。
- **测试/资源：** 新增36项纯内存参考模型测试，KNOW-000059、ASSET-000090和54项正式验收场景矩阵；新增SRC-000406记录etcd v3.7 Lease TTL key删除语义。
- **边界：** 没有连接真实etcd、没有真实多主机Dispatcher/Leader测试、没有实测protobuf/gRPC请求字节或p95/p99；slot与queue模型不代表生产适配器。逻辑partition仍位于同一etcd集群，Raft提交路径并未被拆分。
- **状态：** schema-v2仍是唯一生产权威；V3分片准入和V2→V3切换均未启用；公平策略变化待业务批准；CH17-T004继续IN_PROGRESS。


### 第四十五轮CI验收补记（2026-11-26）

- **最终代码head：** \`a035cdf1f82e6ea9274195b2872953e9f12e83ba\`；[GitHub Actions Run 45823628905](https://github.com/rexyll/cnc-knowledge/actions/runs/45823628905)两个必需Job均completed/success。
- **质量结果：** 全库462项unittest通过（本轮新增36项分片准入/事务预算参考模型测试）；CH12 143项数值资源测试通过；strict knowledge lint 0 errors；知识结构与数据质量0 errors，5项既有非阻断warning。
- **验收边界：** 纯内存模型，不接真实etcd/native Lease/多主机Dispatcher，不测真实protobuf/gRPC请求字节、quorum或p95/p99。ASSET-000090的54项正式场景仍PROPOSED_NOT_APPROVED / NOT_RUN；V3公平策略变更待企业批准。
- **状态：** schema-v2仍是唯一生产权威；无生产分片/切换；CH17-T004继续IN_PROGRESS。


### 第四十五轮最终 Fencing floor 补强（2026-11-26）

- **补强提交：** e8a4fb4c91bac3b279c5a0f8a06d3ae121da75a1；当同一有效Partition Leader观察到更高external high-water，且floor到达当前Token range的下一个未发Token时，立即丢弃未使用range，确保新Token在global reserved high-water以上重新分配。
- **新增测试：** 1项“same leader discards unconsumed range when external floor advances”，本轮测试总数37项。
- **最终CI：** [Run 45824510175](https://github.com/rexyll/cnc-knowledge/actions/runs/45824510175)两个必需Job均completed/success：全库463项unittest、CH12 143项测试通过；strict lint 0 errors；知识结构与数据质量0 errors（5项既有warning）。
- **状态：** ASSET-000090的54项正式场景仍PROPOSED_NOT_APPROVED / NOT_RUN；不接入真实etcd或多主机Dispatcher，不执行生产schema-v3切换；CH17-T004继续IN_PROGRESS。


## 6.18 CH17-T004 etcd v3 Watch、Range恢复与多实例故障注入（第四十六轮，2026-11-26）

- **现状复用：** 本轮复用既有CoordinatorAuthorityStore、EtcdV3CoordinatorAuthorityStore、EtcdV3Client、InMemoryEtcdV3Client和Txn/Lease契约，不重复创建KV/Txn/Lease层。
- **可选Watch：** 在scripts/spare_parts_provider_authority_store.py增加AuthorityStoreWatchResponse/Event、CoordinatorAuthorityWatchStore/EtcdV3WatchClient可选extension，ETCD Adapter提供watch/watch_progress，并增加linearizable_range(prefix)。SQLite不被强制实现Watch。
- **Cursor语义：** start_revision包含式；created不推进业务cursor；完整event/progress response可按header_revision+1恢复；fragment未完成不能推进；compact cancellation必须Range重建后R+1重订阅；Watch永远不作为授权判据。
- **多客户端故障注入：** 新增InMemoryEtcdV3WatchClient共享后端测试替身，多个独立EtcdV3CoordinatorAuthorityStore实例共享revision/KV/Lease/watch history；注入Txn提交前/后超时、LeaseGrant/KeepAlive/Revoke响应丢失、Watcher断线/compact/cancel。
- **测试/资源：** 新增tests/test_spare_parts_provider_authority_store_watch.py，共21项测试方法；新增KNOW-000060、SRC-000407、ASSET-000091和30项正式场景矩阵，全部PROPOSED_NOT_APPROVED / NOT_RUN。
- **范围：** 共享Python fake不是多etcd成员/多主机共识，不模拟真实gRPC Watch stream、Raft quorum、mTLS/RBAC或网络分区。真实etcd driver和Coordinator领域服务从SQLite SQL迁移仍未完成。
- **状态：** schema-v2仍为唯一生产权威；没有真实etcd接入/迁移；CH17-T004继续IN_PROGRESS。


### 第四十六轮CI验收补记（2026-11-26）

- **最终代码head：** `cdaff0dc43834b3250d8803efb0591a8656c363d`；[GitHub Actions Run 45826709629](https://github.com/rexyll/cnc-knowledge/actions/runs/45826709629)两个必需Job均completed/success。
- **质量结果：** 全库484项unittest通过（本轮新增21项Watch/多客户端故障注入测试）；CH12 143项数值资源测试通过；strict knowledge lint 0 errors；知识结构与数据质量0 errors，5项既有非阻断warning。
- **边界：** 多客户端测试为两个adapter共享单进程fake backend；没有真实etcd server、Raft quorum、多主机gRPC Watch、mTLS/RBAC或网络分区验证。30条ASSET-000091正式场景保持PROPOSED_NOT_APPROVED / NOT_RUN。
- **状态：** schema-v2仍为唯一生产权威；真实etcd driver和Coordinator领域服务迁移未完成；CH17-T004继续IN_PROGRESS。


## 6.19 CH17-T004 第二十四轮：真实 etcd v3 Gateway 驱动与三节点集成框架（全局第四十七轮，2026-11-26）

- **客户端选型：** 固定OpenStack维护的第三方Python etcd v3 gRPC-gateway客户端 `etcd3gw==2.7.0`，作为可选依赖，不增加普通知识库CI环境依赖。
- **网络驱动：** 新增 `scripts/spare_parts_provider_etcd3gw_driver.py`，实现KV Range、Txn Compare/Success/Failure和Lease Grant/KeepAlive/Revoke；Base64二进制编解码、revision解码；只读Range/status/member-list在连接失败时尝试其他endpoint并保持serializable=false；Txn/Lease写请求仅发送一次，继续使用OUTCOME_UNKNOWN，不盲目重试。
- **Watch能力门禁：** etcd3gw高层Watch helper跳过created握手并只向回调交付event，未保留完整header/canceled/compact_revision/cancel_reason/fragment；驱动故意不声明Watch/WatchProgress能力。后续需原生gRPC或完整stream-envelope适配器。
- **集成环境：** 新增etcd v3.7.0三成员Compose、独立named volume、健康检查、显式runner和说明文档。普通CI不启动Docker/etcd服务。
- **测试/资源：** 新增10项fake gateway契约测试和5项opt-in live integration tests；新增KNOW-000061、SRC-000408/409、ASSET-000092（30项正式场景，全部PROPOSED_NOT_APPROVED / NOT_RUN）。
- **CI：** `871fe0d2673fb1b39502236568dc7dd57ad3bef0`；[Run 45832644686](https://github.com/rexyll/cnc-knowledge/actions/runs/45832644686)两个必需Job成功。全库499项测试完成，494通过、5项live etcd测试skip；CH12 143项通过；strict knowledge lint 0 errors；独立的CH17合成夹具校验为0 errors、5 warnings。5项均为既有治理门禁提示：数据集仍为DRAFT、未批准企业测试环境、未批准企业测试级别、30项SPAT源测试案例仍NOT_RUN、manifest checksum pending；并非etcd驱动测试失败。
- **边界：** 未启动真实三节点、未执行5项live集成测试；未验证mTLS/RBAC、Raft/quorum、多主机或生产吞吐；SQLite Coordinator业务服务未迁移，schema-v2仍是唯一生产权威；CH17-T004保持IN_PROGRESS。

## 6.20 CH17-T004 真实 etcd 单成员故障与多数派读写验证（第四十八轮，2026-11-26）

- **依赖：** 复用第四十七轮etcd3gw 2.7.0、`Etcd3gwV3Client`、三成员etcd v3.7.0 Compose；不重建KV/Txn/Lease适配层。
- **新增文件：** `tests/test_spare_parts_provider_authority_store_member_outage_etcd_integration.py`，增加第6项 opt-in live integration test；runner及工作流path过滤已扩展，可自动纳入所有`test_*etcd_integration.py`。
- **故障步骤：** 停止etcd1；让linearizable Range从失效首endpoint切换至etcd2；等待存活成员选出Leader；在剩余2/3多数派上完成Txn Compare/Put和线性一致读回；最后启动etcd1并确认三成员恢复。
- **最终实测：** [Run 45839556952](https://github.com/rexyll/cnc-knowledge/actions/runs/45839556952)真实etcd v3.7.0三成员一次性集群，6/6 PASS、0失败、0跳过；清理成功。诊断Artifact 15127610627，SHA-256 `74b04904535cce72b7a08fdf6265020bcb9086b43003106ab4eb4271847869f2`。
- **默认CI回归：** [Run 45839557095](https://github.com/rexyll/cnc-knowledge/actions/runs/45839557095)两个Job成功；全库500项unittest（494通过，6项opt-in live测试按设计skip），CH12 143项数值测试通过；strict lint 0 errors；fixture validator 0 errors/5项既有DRAFT与审批warning。
- **边界：** 这是一组Disposable CI smoke/integration test，不等于企业正式验收；ASSET-000092的30条正式场景全部继续PROPOSED_NOT_APPROVED / NOT_RUN。没有测试2成员失去quorum、网络分区、数据损坏、性能、mTLS/RBAC或真实多主机Coordinator；SQLite业务状态机没有迁移，schema-v2仍是生产唯一权威。CH17-T004保持IN_PROGRESS。

## 6.21 CH17-T004 etcd 双成员故障、失去多数派与恢复验证（第四十九轮，2026-11-26）

- **新增文件：** `tests/test_spare_parts_provider_authority_store_quorum_loss_etcd_integration.py`，新增第7项opt-in live integration test。
- **测试步骤：** 在初始3成员集群停止etcd1、etcd2；通过etcd3验证linearizable_get失败关闭；再对etcd3发送一次Txn，接受明确不可用或OUTCOME_UNKNOWN，但不允许返回成功；重新启动两个成员、等待quorum leader恢复；确认原key不存在，再对同一key执行VERSION=0 CAS写入和线性一致读回。
- **关键语义：** 没有多数派时不允许把单节点可达视为线性一致读写可用；写操作不自动重试；未知结果需在quorum恢复后进行线性一致读回确认。
- **真实集成结果：** [Run 45840903997](https://github.com/rexyll/cnc-knowledge/actions/runs/45840903997)在一次性etcd v3.7.0三成员集群7/7 PASS，0失败、0跳过；节点清理成功；Artifact 15128755397，SHA-256 `d326119ddda7cc64a1cf3e14fbefc83e21d4693b25d2b9d870604bbee28747b8`。
- **默认CI：** [Run 45840904137](https://github.com/rexyll/cnc-knowledge/actions/runs/45840904137)全库501项unittest（494通过、7项live测试按默认策略skip）、CH12 143项测试通过、strict lint 0 errors、fixture validator 0 errors/5项既有warning；两个Job全部成功。
- **限制：** 这是单次、受控、可丢弃环境验证，不是网络分区、磁盘损坏、性能、mTLS/RBAC或企业生产验收。ASSET-000092的30项正式场景均保持PROPOSED_NOT_APPROVED / NOT_RUN；schema-v2仍为唯一生产权威；CH17-T004继续IN_PROGRESS。

## 6.22 CH17-T004 etcd Watch Gateway 流式包络保真（第五十轮，2026-11-26）

- **目标：** 基于etcd3gw使用的HTTP Gateway server-streaming传输形式，补充低层Watch响应包络适配，避免高层事件迭代器丢失WatchResponse控制字段。
- **交付：** `Etcd3gwV3Client.watch()`可选流式接口；逐JSON响应帧解码；规范化WatchResponse header、watch_id、created/canceled/compact_revision/cancel_reason/fragment/events；KV和prev_kv二进制解码；HTTP响应关闭与断线异常传播。
- **能力门禁：** 只有真实服务端测试覆盖完整响应后才在Etcd driver上暴露Watch；若HTTP server-streaming不支持发送后续WatchProgress/Cancel请求，则不声明WatchProgress，取消只关闭流，不伪造服务端确认。
- **测试：** 默认Fake gateway contract覆盖任意chunk边界、完整字段、PUT/DELETE/prev_kv、fragment/compaction与断线；opt-in真实etcd集成覆盖created、变更事件和连接关闭。
- **安全和一致性：** Watch仅提供通知；安全状态仍来自linearizable Range/Txn；created/fragment不能错误推进cursor；流断线/compaction由上层Range snapshot + R+1恢复；写Txn仍一次发送并保留OUTCOME_UNKNOWN。
- **状态：** CH17-T004保持IN_PROGRESS；ASSET-000092正式矩阵未批准前不改写执行状态；schema-v2仍为唯一生产权威。

### 第五十轮 CI 验收补记（2026-11-26）

- 驱动 `scripts/spare_parts_provider_etcd3gw_driver.py` 新增可关闭的 `_Etcd3gwWatchStream`，使用已配置的 HTTP session 发送 `/v3/watch` create_request，并以增量 UTF-8/JSON 解析器恢复完整 server-streaming 响应帧。
- 规范化 header revision、watch_id、created、canceled、compact_revision、cancel_reason、fragment、events 及 KV/prev_kv；处理 proto3 默认 PUT 枚举省略时的默认值。WatchCreate 支持 start_revision、progress_notify、filters、prev_kv、range_end、watch_id 和 fragment。
- HTTP 接口未实现后续双向 WatchProgress/WatchCancel 请求；本驱动不暴露 watch_progress，close 只关闭底层响应流，不声称服务端 cancel ack。已建立流断线显式传播，上层通过线性一致 Range 和 R+1 恢复。
- Fake Gateway 新增任意 chunk 边界、完整包络、PUT/DELETE/prev_kv、流建立 failover、断线传播和 close 资源释放测试；driver 契约测试现 13 项。
- 真实服务端测试：[Run 45842517310](https://github.com/rexyll/cnc-knowledge/actions/runs/45842517310)在三成员 etcd v3.7.0 临时集群执行 8/8 live 测试全通过；诊断 Artifact 15128407498，SHA-256 `9c45a263c409f9f7eb808670df14c5a7f7455f8cea85ad0cadec5d053699ccb9`。
- 完整回归：[Run 45842517156](https://github.com/rexyll/cnc-knowledge/actions/runs/45842517156)两个 Job 成功；全库 505 项（497 passed、8 live opt-in skipped）；CH12 143 项通过；strict knowledge lint 0 errors；fixture validator 0 errors、5 项既有治理 warning。
- 限制：这证明指定版本/临时 Compose 环境的 server-streaming 字段解析和简单 PUT/DELETE 事件链路，不证明双向 WatchProgress/Cancel、生产断线压测、TLS/mTLS、RBAC 或多主机 Coordinator；30 项正式 ASSET-000092 场景仍未批准/未执行。CH17-T004 继续 IN_PROGRESS。

## 6.23 CH17-T004 etcd v3 Gateway mTLS 双向证书与信任链验证（第五十一轮，2026-11-26）

- **目标：** 在可丢弃三成员etcd v3.7.0 TLS集群中真实验证HTTPS服务端证书校验、强制客户端证书认证及失败关闭。
- **交付：** 临时CA/服务器证书/客户端证书生成脚本或runner；独立TLS Compose拓扑；opt-in live tests覆盖有效mTLS Range/Txn、缺失client certificate、错误CA；所有敏感材料仅存runner临时目录。
- **验证边界：** 不提交私钥/证书，不使用真实企业PKI，不把禁用verify或回退HTTP作为测试成功条件；明确区分证书链验证、客户端认证和etcd RBAC授权。
- **状态：** CH17-T004保持IN_PROGRESS；ASSET-000092的30项正式场景仍须企业批准；schema-v2仍是唯一生产权威。


### 第五十一轮执行结果（2026-11-27）

- mTLS runner、独立三成员 TLS Compose 拓扑和三个 live tests 已执行；[Run 45918152363](https://github.com/rexyll/cnc-knowledge/actions/runs/45918152363)成功，mTLS 3/3通过（有效证书读写、缺失客户端证书拒绝、错误CA拒绝）。Artifact 15163390323，SHA-256 `91014d3f47cf09152dd81488231494fdc04afc675b428cdad3e0556cf00aac74`。
- 默认 CI [Run 45918152436](https://github.com/rexyll/cnc-knowledge/actions/runs/45918152436)成功：508项unittest、CH12 143项、strict lint 0 errors、结构/数据0 errors/5项既有warning。
- mTLS 测试证书/私钥只在runner临时目录生成，退出清理；不作为企业PKI验收。ASSET-000092正式30项仍PROPOSED_NOT_APPROVED / NOT_RUN；CH17-T004仍IN_PROGRESS。

## 6.24 CH17-T004 etcd v3 Gateway RBAC 与最小权限账户验证（第五十二轮，2026-11-27）

- **目标：** 在mTLS三节点集成拓扑上启用etcd原生Authentication/RBAC，验证Coordinator etcd Gateway adapter能以认证用户执行受限KV操作，并严格遵守key prefix授权范围。
- **依赖：** 第五十一轮 compose-mtls.yaml、临时CA/client certificate runner、Etcd3gwV3Client和etcd v3.7.0三成员环境；不修改schema-v2生产权威，不迁移SQLite业务状态机。
- **场景：** root管理员临时配置reader/writer角色；reader仅可读 /cnc-knowledge-it/authorized/，不得写入；writer仅可读写 /cnc-knowledge-it/writable/，不得访问相邻未授权前缀；无token/错误凭证失败；mTLS仍保持强制。
- **驱动研究：** 核查etcd3gw 2.7.0的session/header扩展点；必要时增加显式token provider/Authorization header注入。token仅内存保存，密码/token不进入URL、日志和仓库；认证/授权失败不得被误判为transport failure而跨endpoint重试，不允许匿名或HTTP降级。token自动刷新/过期若本轮未实现须明确记录。
- **测试：** Fake transport验证Authorization header注入和fail-closed；独立live suite通过 /v3/auth/authenticate 取得临时token，再对真实etcd三成员集群执行Range/Txn正反向权限断言。所有CA、证书、密码和token均由CI临时生成/注入并清理。
- **验收：** 合法角色在授权范围内成功；读写和前缀越权均由etcd返回拒绝；无凭证/错误密码认证失败；TLS验证仍有效；权限拒绝不触发网络failover、不吞错、不降级。
- **状态边界：** 这是一次性集成验证，不代表企业IAM/密码管理/token轮换撤销/审计/生产RBAC验收。ASSET-000092正式30项仍PROPOSED_NOT_APPROVED / NOT_RUN；CH17-T004保持IN_PROGRESS。

### 第五十二轮执行结果（2026-11-27）

- Etcd3gwV3Client增加可选auth_token，给每个endpoint session注入Authorization header；Fake Gateway验证token传播和空token拒绝。
- Live [Run 45919206834](https://github.com/rexyll/cnc-knowledge/actions/runs/45919206834)成功：mTLS suite 8/8（原mTLS 3项 + RBAC 5项），普通三节点suite 8项全部通过。RBAC实测reader只读授权prefix、writer只读写授权prefix、跨prefix越权拒绝、无token/错误密码失败。Artifact 15163741056，SHA-256 `b7e7476a08e1e9c4a77e4bb02e2b80727dd09e1baadc1b66866b6a54b72c8ee0`。
- etcd gRPC-Gateway不接受通过非空客户端证书CN映射用户；最终使用无CN的CA签名client cert继续强制mTLS，RBAC身份通过用户名/密码换token和Authorization header实现。
- 默认CI [Run 45919206886](https://github.com/rexyll/cnc-knowledge/actions/runs/45919206886)成功：515项unittest（499通过、16项opt-in live skip）、CH12 143项、strict lint 0 errors、结构/数据0 errors/5项既有warning。
- token只显式注入并保存在内存，本轮不实现自动刷新/续期；企业IAM、凭据轮换、审计及生产密钥托管仍未验证。ASSET-000092正式30项继续PROPOSED_NOT_APPROVED / NOT_RUN；CH17-T004仍IN_PROGRESS。


## 6.25 CH17-T004 etcd Gateway Token 生命周期与认证故障语义（第五十三轮，2026-11-27）

- **目标：** 研究etcd v3.7.0 token TTL/类型及Gateway认证错误语义，在mTLS+RBAC三成员临时集群验证过期、重新认证、跨endpoint传递和认证服务暂时不可用行为。
- **任务拆解：** 核验v3.7.0 token TTL配置及默认值；实现短TTL隔离测试；捕获过期token、无效密码、权限拒绝、TLS失败、连接中断和服务端不可用的HTTP/gRPC错误细节；验证重新认证后新token可用及旧token行为；验证多个endpoint和Watch stream使用一致Authorization token；验证一成员停机时已有token数据请求与认证请求的区别。
- **安全要求：** token/密码/证书只在runner临时目录或进程内存；错误信息不得泄露凭据；权限拒绝/认证失败不得作为网络错误进行endpoint failover，不得匿名或明文降级。
- **实现决策门：** 不预设必须自动刷新。只有在真实协议、token TTL、并发刷新锁、时钟偏差、凭据来源/托管和故障语义可验证后，才引入自动token provider；否则保留显式token更新接口并将生命周期责任交给外部安全凭据提供方。
- **交付物：** etcd版本/配置与token生命周期说明、Fake Gateway错误分类/多endpoint测试、mTLS+RBAC live集成测试、更新后的CH17知识文章/实体/资源索引及CI证据。
- **验收边界：** 不声称企业IAM/生产轮换撤销/审计已完成；ASSET-000092仍由企业正式审批控制，schema-v2仍是唯一生产权威，SQLite Coordinator未迁移，CH17-T004保持IN_PROGRESS。


### 第五十三轮执行进展（2026-11-27）

- 新增SRC-000410～SRC-000412，核实etcd v3.7 simple token默认TTL为300秒、JWT TTL独立配置及simple/JWT设计差异。
- 驱动增加显式set_auth_token(token|None)更新全部endpoint session；新增Fake Gateway更新/清除和认证异常不触发failover测试。
- 新增独立10秒simple token mTLS集成阶段，覆盖token过期拒绝、重新认证、全部endpoint token更新、KV Range与Watch created握手；默认RBAC套件仍使用300秒TTL。
- 正文/实体/README/资源索引已同步。**验收结果：** Live [Run 45920726761](https://github.com/rexyll/cnc-knowledge/actions/runs/45920726761)成功：基础三节点6项、mTLS/RBAC 8项、10秒simple-token生命周期1项通过；Artifact 15164208273，SHA-256 `0b66c69eb7f1ecc12e0d8bfbbf80ab0bf51de739ec31d8d2e9f3db878619e476`。默认质量[Run 45920726730](https://github.com/rexyll/cnc-knowledge/actions/runs/45920726730)两个Job成功：518项unittest（501通过、17项opt-in skip）、CH12 143项、strict lint 0 errors。第五十三轮任务验收通过；自动刷新仍未实现，正式ASSET-000092状态不变。
