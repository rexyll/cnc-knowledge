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
