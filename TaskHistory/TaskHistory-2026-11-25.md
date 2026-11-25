# TaskHistory — 2026-11-25

## CH17-T001 维修工作流与记录闭环扩展

- **实际完成时间：** 2026-11-25T12:23:27+08:00（Asia/Shanghai）
- **所在分支：** main
- **实施提交：** 5cd0082d1e9322ef6b3990a8cab906c7ab2dd67d
- **新增正文：** `docs/17-operation-maintenance-and-repair/repair-workflow-and-records.md`
- **新增资源：** `resouces/17-operation-maintenance-and-repair/repair-work-order-template.csv`、`post-repair-verification-matrix.csv`；并将既有 `operation-readiness-checklist.csv` 登记为ASSET-000008。
- **新增结构化记录：** KNOW-000021；ASSET-000008～ASSET-000010；SRC-000389～SRC-000390。
- **新增来源：** ISO 17359:2018（状态监测计划一般指南）；ISO 230-2:2014及Amd 1:2016（单个数控轴定位准确度/重复定位测试方法）；并引用既有OSHA法规和Haas官方手册来源。外部全文均未复制。
- **内容范围：** 建立报修证据固化、危险能量/授权审查、OEM文件匹配、诊断接口、维修执行与部件/参数追溯、维修后验证、放行和关闭流程。
- **验收边界：** 只形成通用维修管理框架与空白记录模板。未给出任何机型级拆装/隔离步骤、维护周期、油液规格、压力/扭矩/温度参数或通用验收阈值；无真实维修工单或实测复验数据。CH17-T001继续IN_PROGRESS，CH17-T002～T004仍TODO。
- **CI验收：** [GitHub Actions Run 45546453542](https://github.com/rexyll/cnc-knowledge/actions/runs/45546453542) completed/success，两个Job均通过。Knowledge structure and data quality：5/5单元测试通过，knowledge_lint --strict为PASS（0 errors），检查22章、137个Markdown文件、443条内部链接、147条实体记录、240条关系、387条来源记录、718处来源引用和22条覆盖记录。CH12 numerical resource tests：143/143通过；该回归Job验证仓库既有CH12数值资源，不代表CH17现场/实机维修验证。
- **遗留事项：** 选定具体机床系列并取得现行OEM服务/维护手册；将通用模板映射到该机型的条款、复验要求和受控记录流程。


## CH17-T002 计划维护体系第一轮

- **实际完成时间：** 2026-11-25T12:38:27+08:00（Asia/Shanghai）
- **所在分支：** main
- **新增正文：** `docs/17-operation-maintenance-and-repair/maintenance-management-system.md`
- **新增资源：** `maintenance-task-matrix-template.csv`、`maintenance-card-template.csv`、`maintenance-consumables-register-template.csv`、`haas-lathe-rd0035-selected-maintenance-examples.csv`；均位于 `resouces/17-operation-maintenance-and-repair/`。
- **新增结构化记录：** KNOW-000022；ASSET-000011～ASSET-000014；更新SRC-000388官方来源定位和URL。
- **来源核验：** Haas官方车床交互式服务手册RD0035 Revision A-04/2026；ISO 17359:2018官方目录（状态监测计划一般指南）。Haas示例摘录保留产品族、修订和配置边界；未复制完整手册或标准全文。
- **内容范围：** 维护策略分类、日历/运行小时/循环/状态/事件触发、周期来源优先级、到期延期管理、子系统任务矩阵、状态监测、保养卡和耗材批次追溯。
- **验收边界：** 通用矩阵不填跨品牌周期/阈值/油液规格；Haas示例不得推广到其他品牌或未核实配置。未指定用户目标机型，未激活具体设备维护任务；无真实保养工单、现场测量或实机执行验证。
- **状态：** CH17-T002保持IN_PROGRESS；需要目标机型及现行OEM手册后继续型号级映射。CH17-T001仍为IN_PROGRESS，T003/T004仍TODO。
- **实施提交：** `ecc70ca326fccacab6ed3036fdf5802309c7bb95`；CSV字段对齐修正提交：`97340c9dfa1f6c77a5120c85c40e772b29b16eca`。
- **CI验收：** 修正后的提交 `97340c9dfa1f6c77a5120c85c40e772b29b16eca` 对应 GitHub Actions [Run 45548286906](https://github.com/rexyll/cnc-knowledge/actions/runs/45548286906) completed/success。Knowledge structure and data quality：5/5单元测试通过、`knowledge_lint --strict` 为 PASS（0 errors），检查22章、138个Markdown、450条内部链接、152条实体、240条关系、387条来源、727处来源引用和22条覆盖记录；CH12 numerical resource tests：143/143通过。该CI不代表CH17现场保养或实机验证。


## CH17-T002 CSV列结构复核与修正

- 在维护模板提交 `ecc70ca326fccacab6ed3036fdf5802309c7bb95` 后进行逐行CSV列数审查，发现维护任务矩阵与耗材登记表的预置行存在多余空字段，已在本次更正提交中统一重建字段映射。
- 修正后维护任务矩阵表头/数据行均为37列（22个任务分类入口）；耗材登记表均为41列（8类耗材类别示例）；保养卡为空白单表头模板；Haas RD0035示例CSV为11列、15条数据记录。
- 该更正只修复CSV结构和字段映射；维护周期、油液规格、阈值仍保持待核实，不增加设备级执行授权。


## CH17-T003 部件更换工作包框架第一轮

- **实际完成时间：** 2026-11-25T13:06:35+08:00（Asia/Shanghai；实施提交时间）
- **所在分支：** main（未创建其他分支）
- **新增正文：** docs/17-operation-maintenance-and-repair/component-replacement-work-package.md（KNOW-000023，verification_status=in_review）。
- **新增资源：** component-replacement-work-package-template.csv（ASSET-000015，57列）；component-tool-and-measurement-register-template.csv（ASSET-000016，25列）；component-interface-and-replacement-compatibility-template.csv（ASSET-000017，28列）。均为 resouces/17-operation-maintenance-and-repair 下的原创空白模板。
- **结构化记录与索引：** 新增 KNOW-000023、ASSET-000015～ASSET-000017；更新本章ASSET-INDEX、资源README、章节README、docs入口、CH17章节计划、根TaskPlan和CHAPTER-COVERAGE。
- **来源与边界：** 仅引用SRC-000382（OSHA 29 CFR 1910.147，限适用美国场景的法规入口）和SRC-000390（ISO 230-2:2014及2016修正案官方目录，单个NC轴定位/重复定位方法入口）。未复制受版权限制的标准全文。
- **内容范围：** 建立设备/部件身份、OEM文件、停工点、风险与人员授权、拆前基线、工具量具、接口兼容性、拆装证据、参数/补偿恢复、校准、维修后复验和放行记录框架；不提供型号级拆装步骤、吊装方法、扭矩/预紧数值、介质规格、参数或验收阈值。
- **CSV验收：** 远程复读三份文件，均为单行表头模板且列宽分别为57、25、28；四份新JSON实体记录均可解析，ASSET记录均关联KNOW-000023。
- **实施提交：** 852bf193dffc7cc3dda31ae9de7da61961267e4c；计划/索引/覆盖度同步提交：200620804124e88a7adf97f78908aabb69f8e3ff。
- **CI验收：** 实施提交对应GitHub Actions [Run 45551283372](https://github.com/rexyll/cnc-knowledge/actions/runs/45551283372)，计划/索引同步提交对应 [Run 45551345376](https://github.com/rexyll/cnc-knowledge/actions/runs/45551345376)，两个Run的全部Job均completed/success；知识结构与数据质量测试、strict lint及CH12数值资源回归Job通过。CH12回归仅验证既有数值资源，不构成CH17维修现场、设备/HIL或实机验证。
- **状态与遗留：** CH17-T003保持IN_PROGRESS；尚无用户指定的机床型号、序列范围、配置和受控OEM服务手册，未形成型号级维修SOP、替代件批准或真实拆装/校准/复验记录。


## CH17-T003 关键部件族影响分析与复验矩阵第一轮

- **实际完成时间：** 2026-11-25T13:53:23+08:00（Asia/Shanghai；补录与远程验收完成时间）
- **所在分支：** main（未创建其他分支）
- **新增正文：** docs/17-operation-maintenance-and-repair/component-family-impact-assessment-and-verification.md（KNOW-000024，verification_status=in_review）。
- **新增资源：** resouces/17-operation-maintenance-and-repair/component-family-impact-verification-matrix-template.csv（ASSET-000018），九类部件族、57条审查记录、20列。
- **部件族范围：** 主轴单元/主轴电机；伺服电机/编码器/驱动；滚珠丝杠/支撑轴承/联接件；直线导轨/滑块；刀库/换刀机械手/刀塔/夹持机构；卡盘/夹具/工件夹持；液压/气动动力单元；润滑/冷却/过滤/排屑；CNC/PLC/驱动模块/I/O/传感器。
- **矩阵范围：** 每项预留拆前基线、替代兼容性证据、OEM程序、危险能量/风险审查、维修后验证域、验证方法、接受准则来源、责任专业、停工点、适用性、结果和证据引用。
- **结构化记录与索引：** 新增KNOW-000024、ASSET-000018；更新CH17章节计划、根TaskPlan、章节README、docs入口、资源README、ASSET-INDEX和CHAPTER-COVERAGE。
- **边界：** 矩阵所有行初始TO_BE_ASSESSED/NOT_TESTED，仅为审查提示，不是所有设备的通用要求。无目标机床型号、序列范围、选件和受控OEM服务手册，因此未生成型号级拆装动作、吊装参数、紧固/预紧数值、介质规格、参数或验收阈值；没有真实测量或现场/实机验证。
- **CSV验收：** 远程复读文件共58行（1行表头+57条数据），20列表头，所有行均为20列；9个部件族ID均存在。新建KNOW/ASSET JSON可解析，ASSET路径及索引关联正确。
- **实施提交：** 698efeecde445e2f63fba7c561c28d7f686369d8；计划/索引/覆盖度同步提交：eb296e24f92a800ac89474da3e7eda9ac719ccb4。
- **CI验收：** 实施提交对应GitHub Actions [Run 45556482627](https://github.com/rexyll/cnc-knowledge/actions/runs/45556482627)，计划/索引同步提交对应 [Run 45556547468](https://github.com/rexyll/cnc-knowledge/actions/runs/45556547468)，两个Run的全部Job均completed/success；知识结构与数据质量检查、strict lint及CH12数值资源回归Job均成功。CH12回归只验证仓库既有数值资源，不构成CH17现场维修、HIL或实机验收。
- **状态与遗留：** CH17-T003保持IN_PROGRESS；下一步需取得目标机床系列、序列范围、选件和受控OEM服务文件，将适用矩阵行逐项映射到OEM条款、批准的替代关系、验证方法和现场证据。


## CH17-T003 主轴、伺服与滚珠丝杠专项更换工作包第一轮

- **实际完成时间：** 2026-11-25T14:03:49+08:00（Asia/Shanghai；实施及资源同步完成）
- **所在分支：** main（未创建其他分支）
- **新增正文：** docs/17-operation-maintenance-and-repair/spindle-servo-ballscrew-specialized-replacement-work-packages.md（KNOW-000025，verification_status=in_review）。
- **新增资源：** spindle-replacement-work-package-template.csv（ASSET-000019，18条检查项/35列）；servo-motor-encoder-replacement-work-package-template.csv（ASSET-000020，17条检查项/35列）；ballscrew-support-bearing-replacement-work-package-template.csv（ASSET-000021，17条检查项/35列）。全部位于resouces/17-operation-maintenance-and-repair。
- **专项内容：** 主轴模板审查总成身份、主轴/驱动配套、反馈/定向、刀具夹持、润滑冷却、转子/轴承特殊要求、吊装支撑、安装基准、参数恢复及性能复验；伺服模板审查轴/电机/驱动/编码器配套、制动器、联轴器、电缆接地、诊断基线、参数恢复、反馈/方向和定位复验；丝杠模板审查轴系BOM、丝杠/螺母配套、支撑轴承、几何基线、预紧来源、润滑、重力/搬运风险、轴线/全行程和定位复验。
- **结构化记录与索引：** 新增KNOW-000025、ASSET-000019～ASSET-000021；更新CH17章节计划、根TaskPlan、章节README、docs入口、资源README、ASSET-INDEX和CHAPTER-COVERAGE。
- **边界：** 所有模板均为待评估/未测试状态；没有写入通用拆装顺序、吊点/支撑方法、直流母线等待时间、编码器换相值、丝杠/轴承预紧、紧固扭矩、润滑规格或验收限值。所有具体步骤/值需绑定目标机床序列范围和现行OEM文件；未获文件时保持BLOCKED。
- **CSV验收：** 从GitHub远程复读三份CSV；每行均与35列表头对齐，数据行数分别为18、17、17；三份文件均通过引号/列宽检查。三个ASSET实体均可解析并关联KNOW-000025。
- **实施提交：** a5c3829d4c8fc4cd63bf1b1dbd0a3a57a52a0fec；章节计划/索引/覆盖度同步提交：8c08cc78f3ccf0497a319b2f01669098e68910ba。
- **CI验收：** 实施提交对应GitHub Actions [Run 45557662316](https://github.com/rexyll/cnc-knowledge/actions/runs/45557662316)，同步提交对应 [Run 45557733024](https://github.com/rexyll/cnc-knowledge/actions/runs/45557733024)，两个Run的全部Job均completed/success；知识结构与数据质量、strict lint及CH12数值资源回归均成功。CH12回归仅验证仓库既有数值资源，不构成CH17现场维修、台架/HIL或实机验收。
- **状态与遗留：** CH17-T003保持IN_PROGRESS；尚无目标机床型号、序列范围、选件、控制系统版本和受控OEM服务文件，未形成型号级拆装SOP、已批准替代关系或现场更换/校准记录。


## CH17-T003 刀库/换刀、卡盘夹持与液压气动专项更换工作包第二轮

- **实际完成时间：** 2026-11-25T15:05:29+08:00（Asia/Shanghai；最终CI通过后补录）
- **所在分支：** `main`（未创建其他分支）
- **新增正文：** `docs/17-operation-maintenance-and-repair/atc-chuck-hydraulic-specialized-replacement-work-packages.md`（KNOW-000026，`verification_status=in_review`）。
- **新增资源：** `atc-tool-magazine-turret-replacement-work-package-template.csv`（ASSET-000022，20条检查项/35列）；`chuck-workholding-replacement-work-package-template.csv`（ASSET-000023，18条检查项/35列）；`hydraulic-pneumatic-unit-replacement-work-package-template.csv`（ASSET-000024，20条检查项/35列），均归档于 `resouces/17-operation-maintenance-and-repair/`。
- **专项内容：** ATC模板覆盖刀位/刀具映射、刀套/保持接口、换刀机械手/凸轮/链传动、刀塔/动力刀具适用性、流体/电气/I/O反馈、防护互锁、拆前基线、备份、搬运支撑、空运行和换刀验证；卡盘模板覆盖主轴接口、适配盘、爪/夹具、拉杆、执行缸/旋转接头、夹持确认、工件包络、夹持力/压力/转速/质量等OEM值来源、跳动及受控动态复验；液压气动模板覆盖泵阀/执行机构、管路、介质与过滤、蓄能器、残压、保护阀、压力/流量/温度传感器、校准、泄漏和系统复验。
- **结构化记录与索引：** 新增KNOW-000026、ASSET-000022～ASSET-000024；更新CH17章节计划、根TaskPlan、章节README、docs入口、资源README、ASSET-INDEX和CHAPTER-COVERAGE。覆盖度更新为6篇知识文章、17项资源记录、9条去重来源；CH17仍为IN_PROGRESS。
- **安全/适用边界：** 三份模板均初始 `TO_BE_ASSESSED/NOT_TESTED`，没有通用换刀相位/步骤、夹持力/压力/转速/流量/温度/蓄能器预充、泄压/排气/储能处置动作、紧固值或验收阈值；禁止旁路防护和安全互锁。所有具体动作和技术值必须映射到机床型号/序列范围、现行OEM受控文件、批准工程变更及现场风险评估。SRC-000382（OSHA 29 CFR 1910.147）仅作为其法定适用范围内危险能量控制参考。
- **CSV/实体验收：** 从GitHub远程复读三份CSV；数据行数分别为20、18、20，表头及每个数据行均为35列。KNOW-000026及ASSET-000022～000024 JSON均可解析，三个资源路径和实体关联一致；远程确认临时根目录文件`0`/`1`/`2`已删除。
- **提交与修正记录：** 初始实施提交 `46a1a69042e3aeceb82a3db1dfd1fc15b976cfb6`；该提交中CSV路径误落到根目录临时文件`0`/`1`/`2`，其CI Run 45565074614的Knowledge lint失败（CH12数值资源Job成功）。已通过修正提交 `a8c024973d9b07194e675a7f60185d8002c4842d` 将三份CSV迁移至约定资源目录、删除误放文件并修正KNOW-000026的`linked_templates`；计划/索引同步提交为 `8a5333cbc4ee248587f5d24ac8d24d3f94cbb55d`。
- **CI验收：** 修正提交对应 [Run 45565219082](https://github.com/rexyll/cnc-knowledge/actions/runs/45565219082) completed/success；计划与索引同步提交对应 [Run 45565331120](https://github.com/rexyll/cnc-knowledge/actions/runs/45565331120) completed/success。两个Run的Knowledge structure and data quality与CH12 numerical resource tests均成功；CH12回归只验证仓库数值资源，不构成CH17现场维修、HIL或实机验收。
- **状态与遗留：** CH17-T003保持IN_PROGRESS；仍未指定目标机床型号、序列范围、选件、CNC/PLC软件版本和受控OEM服务手册，未形成型号级拆装SOP、替代件批准、真实工单或现场更换/校准/实机复验记录。


## CH17-T004 备件管理与生命周期闭环第一轮

- **实际完成时间：** 2026-11-25T15:28:58+08:00（Asia/Shanghai；两次主CI全部通过后补录）
- **所在分支：** `main`（未创建其他分支）
- **新增正文：** `docs/17-operation-maintenance-and-repair/spare-parts-management-and-lifecycle.md`（KNOW-000027，`verification_status=in_review`）。
- **新增资源：** `spare-part-master-data-template.csv`（ASSET-000025，38列）；`spare-part-criticality-assessment-template.csv`（ASSET-000026，32列）；`spare-part-inventory-and-replenishment-template.csv`（ASSET-000027，40列）；`spare-part-substitution-approval-template.csv`（ASSET-000028，36列）；`spare-part-lifecycle-and-obsolescence-template.csv`（ASSET-000029，31列）；`repair-spare-consumption-feedback-template.csv`（ASSET-000030，34列）。全部位于 `resouces/17-operation-maintenance-and-repair/`。
- **专项内容：** 建立备件主数据与BOM/机型适用关系、关键度评估因素、库存分桶与补货口径、候选替代件技术证据和审批流程、制造商PCN/EOL及last-time-buy跟踪、工单备件领用/旧件返回/故障反馈闭环；明确CH18故障分析、CH19供应链、CH20 BOM及配置的跨章接口。
- **安全/数据治理边界：** 没有建立真实PART/PRODUCT/MINST、备件料号、供应商、价格、库存余额、采购交期、关键度评分、补货阈值、替代结论或最后采购数量。库存公式只定义字段口径；替代审批必须限定机型/序列/配置/BOM范围并具备OEM或批准工程证据及验证结果。所有模板均为空白，不是已执行的企业ERP/CMMS记录。
- **结构化记录和索引：** 新增KNOW-000027、ASSET-000025～ASSET-000030；更新CH17章节TaskPlan、根TaskPlan、章节README、docs目录入口、资源README、ASSET-INDEX和CHAPTER-COVERAGE。T004由TODO调整为IN_PROGRESS；覆盖度更新为7篇知识文章、23项资源记录、9条去重来源。
- **CSV/实体验收：** 从GitHub远程复读6份CSV；列宽分别为38、32、40、36、31、34，所有文件表头格式一致且当前为header-only空模板。KNOW-000027及6个ASSET JSON均可解析，文件路径、`linked_templates`和`related_knowledge_id`关联一致。
- **实施提交：** `5a329add7c0996db1414ee9211b5f4b26c22df8c`；对应 [GitHub Actions Run 45568231521](https://github.com/rexyll/cnc-knowledge/actions/runs/45568231521) completed/success。
- **计划/索引同步提交：** `a0304e6b4fe7ff22b91a10e4fc1097207db3aea3`；对应 [GitHub Actions Run 45568350982](https://github.com/rexyll/cnc-knowledge/actions/runs/45568350982) completed/success。两个Run的Knowledge structure and data quality与CH12 numerical resource tests Job均成功；CH12回归只验证仓库既有数值资源，不构成CH17现场库存盘点、替代件验证或实机维修验证。
- **状态与遗留：** CH17-T004保持IN_PROGRESS；尚无目标机型受控BOM/OEM备件目录、企业库存和消耗历史、正式供应商交期/报价、PCN/EOL通知及真实维修工单，未激活具体库存策略或批准任何替代件。


## CH17-T004 备件系统集成、字段映射与数据治理第二轮

- **实际完成时间：** 2026-11-25T15:44:31+08:00（Asia/Shanghai；TaskHistory补录时间）
- **所在分支：** `main`（未创建其他分支）
- **新增正文：** `docs/17-operation-maintenance-and-repair/spare-parts-system-integration-and-data-governance.md`（KNOW-000028，`verification_status=in_review`）。
- **新增资源：** `spare-parts-enterprise-system-field-mapping-template.csv`（ASSET-000031，27列表头空模板）；`spare-parts-data-quality-and-reconciliation-rules.csv`（ASSET-000032，16条建议规则/14列）；`spare-parts-stock-policy-decision-template.csv`（ASSET-000033，35列表头空模板）。全部位于 `resouces/17-operation-maintenance-and-repair/`。
- **结构化实体与索引：** 新增KNOW-000028、ASSET-000031～ASSET-000033；更新根TaskPlan、CH17 TaskPlan（新增6.9）、章节README、docs总入口、资源README、ASSET-INDEX和CHAPTER-COVERAGE。覆盖度更新为8篇KNOW条目、26项资源记录、SRC去重9条；CH17-T004继续IN_PROGRESS。
- **专题内容：** 建立ERP/CMMS/EAM/PLM/PDM职责候选、字段级SoR与外部键、主数据/事务对象边界、现有MACHINE/MINST/BOM/PART/PRODUCT/VENDOR/DOC/ASSET模型映射、库存事件桥接与三类对账、数据质量规则、库存策略输入、RACI和建议状态机、只读/影子集成实施验收门槛。
- **数据模型边界：** 复用当前实体和关系类型，不增加全库Schema/关系谓词；库存流水、PO行、收货、批次、预留、维修工单及审批实例仍保留为源系统业务事务对象，不伪装为知识实体。本轮没有创建无真实业务事实支持的REL记录。
- **验收：** 远程复读三份CSV，字段宽度分别27、14、35；字段映射和库存策略模板均为header-only，规则目录16条记录均为PROPOSED且每行14列。KNOW/ASSET JSON均可解析，linked_templates、file_path、related_knowledge_id与资源文件路径匹配；ASSET-INDEX三条资源记录均位于资源表格内。根/章计划、导航链接和覆盖度均包含本轮内容。
- **实施提交：** `a8bd56803c1f51bfb36de28b104844f457ff5ed2`；GitHub Actions [Run 45570074088](https://github.com/rexyll/cnc-knowledge/actions/runs/45570074088) completed/success，Knowledge structure and data quality与CH12 numerical resource tests均成功。
- **计划/索引同步提交：** `62746a5342983f96ad28680b3c085728ce0e8fc7`；GitHub Actions [Run 45570215559](https://github.com/rexyll/cnc-knowledge/actions/runs/45570215559) completed/success，两个Job均成功。
- **资源索引落位修正：** `e5d1372bef4da6c6a3d82bd3b5d2bab6ca407575`；将新增ASSET-000031～ASSET-000033记录放回ASSET-INDEX资源表内；GitHub Actions [Run 45570300758](https://github.com/rexyll/cnc-knowledge/actions/runs/45570300758) completed/success，两个Job均成功。
- **状态与遗留：** 尚无用户企业ERP/CMMS/EAM/PLM字段清单、接口授权、脱敏样本、真实BOM/库存/采购/工单/供应商交期/PCN/EOL资料；未确定字段级SoR、映射转换、对账容差/频率/SLA、企业RACI、库存参数或替代件批准。所有16条规则维持PROPOSED，不能直接视作生产阻断规则。CI只验证仓库结构/数据质量及CH12既有数值资源，不代表企业系统集成、库存盘点、现场维修或实机验证。


## CH17-T004 备件实物流转、事务控制与责任矩阵第三轮

- **实际完成时间：** 2026-11-25T16:05:25+08:00（Asia/Shanghai；TaskHistory补录时间）
- **所在分支：** `main`（未创建其他分支）
- **新增正文：** `docs/17-operation-maintenance-and-repair/spare-parts-physical-flow-and-transaction-controls.md`（KNOW-000029，`verification_status=in_review`）。
- **新增资源：** `spare-parts-transaction-lifecycle-control-matrix.csv`（ASSET-000034，16个控制节点/23列）；`spare-parts-raci-approval-matrix-template.csv`（ASSET-000035，16项活动/16列），均归档于 `resouces/17-operation-maintenance-and-repair/`。
- **流程范围：** 需求提出、技术/配置适用性、采购下单、到货接收、来料检验、上架储存、库存盘点、预留、拣配发料、现场交接、实际安装/消耗、旧件回收、返修处置、报废、库存对账及PCN/EOL影响评估；明确实物事实、系统过账事实和技术/质量放行事实的分离。
- **结构化实体与索引：** 新增KNOW-000029、ASSET-000034～ASSET-000035；更新根TaskPlan、CH17 TaskPlan（新增6.10）、章节README、docs总入口、资源README、ASSET-INDEX和CHAPTER-COVERAGE。覆盖度更新为9篇KNOW条目、28项资源记录、SRC去重9条；CH17-T004继续IN_PROGRESS。
- **数据/安全边界：** 16个事务控制节点和16项RACI分配均为建议/PROPOSED，不代表企业流程、系统接口、授权RACI或真实库存事务已建立。每项RACI建议恰有一个A且至少一个R。现场维修依具体机床OEM受控程序、合格授权人员、现场风险评估和危险能量控制要求；模板不提供危险拆装步骤或通用技术阈值。
- **CSV/JSON验收：** 远程复读流程矩阵为16条数据/23列，RACI矩阵为16条数据/16列，所有行与表头列宽一致；本地预提交检查每项RACI恰有一个A和至少一个R。KNOW-000029及ASSET-000034～ASSET-000035 JSON均可解析，`linked_templates`、`file_path`和`related_knowledge_id`路径关联一致。
- **实施提交：** `305b7a5e057926dab2540a510aeaca8040c9c636`；GitHub Actions [Run 45573023428](https://github.com/rexyll/cnc-knowledge/actions/runs/45573023428) completed/success，Knowledge structure and data quality与CH12 numerical resource tests均成功。
- **计划/索引同步提交：** `23b5bfec010166a8c5b7b277c27e4db4d770b7c5`；GitHub Actions [Run 45573116169](https://github.com/rexyll/cnc-knowledge/actions/runs/45573116169) completed/success，两个Job均成功。
- **状态与遗留：** 尚无真实企业ERP/CMMS/EAM状态字典、交易接口、收货/库存/工单样本、正式企业组织授权RACI、目标机型受控BOM/OEM和现场维修证据；未导入真实采购/收货/库存移动/领退料记录，未确定企业实际审批权限、盘点频率/容差或异常SLA。CI仅验证仓库结构/数据质量及CH12既有数值资源，不代表企业事务集成、库存盘点、现场维修或实机验收。


## CH17-T004 备件端到端验收场景与测试证据第四轮

- **实际完成时间：** 2026-11-25T16:18:31+08:00（Asia/Shanghai；TaskHistory补录时间）
- **所在分支：** `main`（未创建其他分支）
- **新增正文：** `docs/17-operation-maintenance-and-repair/spare-parts-end-to-end-acceptance-testing.md`（KNOW-000030，`verification_status=in_review`）。
- **新增资源：** `spare-parts-end-to-end-acceptance-test-matrix.csv`（ASSET-000036，30测试用例/24列）；`spare-parts-acceptance-test-execution-record-template.csv`（ASSET-000037，30列表头空模板），均位于 `resouces/17-operation-maintenance-and-repair/`。
- **测试内容：** L0静态、L1组件/规则、L2集成/SIT、L3业务/UAT、L4上线准备；覆盖主数据/外部键/BOM适用性、采购收货/质量放行、库存桶/在途PO/单位、事件幂等、替代审批范围、发料与实际安装、批次追溯、返修/报废、盘点对账、PCN/EOL、权限/SoR/敏感数据和事件恢复。
- **验收边界：** 30个场景全部为NOT_RUN；执行记录模板为header-only。未连接用户企业ERP/CMMS/EAM/PLM，未导入生产数据，未执行SIT/UAT/生产影子运行或机床现场/实机测试。测试阈值、容差、接口时延、环境与审批角色由企业批准。
- **结构化实体与索引：** 新增KNOW-000030、ASSET-000036～ASSET-000037；更新根TaskPlan、CH17 TaskPlan（新增6.11）、章节README、docs总入口、资源README、ASSET-INDEX与CHAPTER-COVERAGE。覆盖度更新为10篇KNOW条目、30项资源记录、SRC去重9条；CH17-T004继续IN_PROGRESS。
- **CSV/JSON验收：** 远程复读测试矩阵为30行/24列且所有行宽一致；执行记录模板为0数据行/30列表头。KNOW-000030及两个ASSET JSON均可解析，`linked_templates`、`file_path`和`related_knowledge_id`关联正确；测试矩阵所有执行状态均为NOT_RUN。
- **实施提交：** `039960f85923b8c3a521f3267db4396fb8dd0a63`；GitHub Actions [Run 45574910040](https://github.com/rexyll/cnc-knowledge/actions/runs/45574910040) completed/success，Knowledge structure and data quality与CH12 numerical resource tests均成功。
- **计划/索引同步提交：** `6e93d3e251531317e3ec7a461376a8d312b5ae4f`；GitHub Actions [Run 45574998349](https://github.com/rexyll/cnc-knowledge/actions/runs/45574998349) completed/success，两个Job均成功。
- **状态与遗留：** 尚无企业授权非生产环境、系统字段/SoR正式批准、合成数据集版本、企业测试角色授权和测试执行证据；未实际运行30个场景或生成PASS/FAIL。CI只验证仓库知识结构/数据质量及CH12既有数值资源，不代表备件系统SIT/UAT、库存实盘、现场维修或实机验收。

## CH17-T004 备件合成测试数据集与环境就绪规范第五轮

- **实际完成时间：** 2026-11-25T17:01:07+08:00（Asia/Shanghai；两次主提交的CI全部通过后补录）
- **所在分支：** `main`（未创建其他分支）
- **新增正文：** `docs/17-operation-maintenance-and-repair/spare-parts-synthetic-test-data-and-environment-readiness.md`（KNOW-000031，`verification_status=in_review`）。
- **新增资源：** `spare-parts-synthetic-test-dataset-manifest-template.csv`（ASSET-000038，29列表头空模板）；`spare-parts-test-environment-readiness-checklist.csv`（ASSET-000039，22项/11列，全部NOT_ASSESSED）；`spare-parts-test-fixture-cross-reference-template.csv`（ASSET-000040，27列表头空模板），均归档于 `resouces/17-operation-maintenance-and-repair/`。
- **专题内容：** 建立合成数据集身份/语义版本/生成器/种子引用/冻结/校验；覆盖组织与仓库、虚构机床实例和配置、BOM、PART/PRODUCT、虚构供应来源、采购收货、质量处置、库存流水、维修工单、替代审批、PCN/EOL及测试身份；区分业务时间、接收时间、顺序号、版本、重复/乱序/冲销和事件重放；定义L0～L4测试环境分层、身份/网络/数据隔离、mock/sandbox、最小权限、秘密管理、非生产备份恢复和清理。
- **安全与数据边界：** 默认仅使用纯合成数据；经批准的脱敏数据须单独记录数据所有者、隐私/安全审批、方法版本和重识别风险。禁止生产快照、真实生产主键、个人信息、凭证或供应商机密进入合成夹具或公共仓库；禁止生产写入、真实供应商/客户通知和未授权机床动作。采购行、收货、质检、库存流水、预留、维修工单和审批仍为测试系统事务/事件，不扩展全库静态实体Schema。
- **结构化记录与索引：** 新增KNOW-000031、ASSET-000038～ASSET-000040；更新根TaskPlan、CH17 TaskPlan（新增6.12）、章节README、docs总入口、资源README、ASSET-INDEX和CHAPTER-COVERAGE。CH17覆盖度更新为11篇KNOW条目、34个登记实体、33项资源记录、SRC去重9条；CH17-T004继续IN_PROGRESS。
- **CSV/JSON验收：** 从GitHub远程复读三份新增CSV：数据集清单29列/0数据行；环境就绪表22行/11列；夹具引用模板27列/0数据行；三份文件各行列宽一致。新增KNOW/ASSET四份JSON均可解析；三个ASSET的file_path、related_knowledge_id及ASSET-INDEX条目与实际文件一致，索引条目位于资源表格内。覆盖度CSV行宽为13列。
- **实施提交：** `9b7b20b3acabde5032ca98249775e0c5dde74fa8`；GitHub Actions [Run 45581158205](https://github.com/rexyll/cnc-knowledge/actions/runs/45581158205) completed/success，Knowledge structure and data quality与CH12 numerical resource tests两个Job均success。
- **计划/索引同步提交：** `5ed043b580d05ec88157c43f6004120c136245d5`；GitHub Actions [Run 45581324072](https://github.com/rexyll/cnc-knowledge/actions/runs/45581324072) completed/success，两个Job均success。
- **状态与遗留：** 22项环境检查仍为NOT_ASSESSED；尚未取得企业授权非生产环境清单、网络隔离/角色/备份恢复证据，也未生成或冻结企业专用合成数据集。既有30项备件端到端测试仍全部NOT_RUN；未执行企业SIT/UAT、生产影子运行、HIL或实机测试。CH17-T004保持IN_PROGRESS。CI只证明仓库结构/数据质量及CH12既有数值资源回归成功，不代表企业系统、库存业务或机床现场验收。

## CH17-T004 备件合成测试夹具基线与30项用例映射第六轮

- **实际完成时间：** 2026-11-25T17:20:35+08:00（Asia/Shanghai；实施、BOM修正及计划/索引同步CI全部通过后补录）
- **所在分支：** `main`（未创建其他分支）
- **新增正文：** `docs/17-operation-maintenance-and-repair/spare-parts-synthetic-fixture-baseline-v1.md`（KNOW-000032，`verification_status=in_review`）。
- **新增资源：** `spare-parts-synthetic-fixture-baseline-v1-manifest.csv`（ASSET-000041，29列/1数据行，数据集DRAFT）；`spare-parts-synthetic-fixture-baseline-v1.csv`（ASSET-000042，89条/27列，其中67对象+22事件）；`spare-parts-synthetic-fixture-test-case-coverage-v1.csv`（ASSET-000043，30行/11列，覆盖SPAT-001～SPAT-030）。全部位于 `resouces/17-operation-maintenance-and-repair/`。
- **数据集定义：** `SPAREPARTS-SYN-BASE-001` v1.0.0，固定静态CSV和稳定ID，不依赖运行时随机数。使用虚构SYN-/FX-/EVT-标识；未使用生产/脱敏源数据，不含真实机床、供应商、人员、客户、采购主键、账号或凭证。所有样例数量/单位换算只用于软件逻辑验证，不构成企业库存政策、产品规格或工程阈值。
- **场景覆盖：** 组织/仓库、虚构机床配置与BOM修订、物料外部键冲突、采购授权/部分收货、质量放行/隔离、库存桶/预留/分配/在途PO、单位换算、替代件范围/有效期、发料与安装、批次追溯、旧件返修/报废、库存对账、PCN/EOL、权限、SoR、字段最小化和重复/迟到/乱序/冲销事件。
- **BOM修订修正：** R1有效期为2026-01-01至2026-06-30（含）；R2从2026-07-01起生效。仅为虚构数据，服务SPAT-004日期边界场景。
- **结构化记录与索引：** 新增KNOW-000032、ASSET-000041～ASSET-000043；更新根TaskPlan、CH17 TaskPlan（新增6.13）、章节README、docs总入口、资源README、ASSET-INDEX和CHAPTER-COVERAGE。覆盖度为12篇知识文章、38个登记实体、36项资源记录、SRC去重9条；CH17-T004继续IN_PROGRESS。
- **远端数据验收：** 89个Fixture ID唯一；67个对象/22个事件；父/关联引用无悬空；30个测试用例ID唯一且映射齐全，映射引用的正向/负向夹具和事件全部存在。使用支持引号转义的CSV解析复读：manifest 1行/29列，fixture 89行/27列，coverage 30行/11列；新增KNOW/ASSET四份JSON可解析，资源路径与KNOW关联一致。
- **实施提交：** `08f7188bd8fd0198ceac3cae97cd1c3d31b766da`；GitHub Actions [Run 45584153406](https://github.com/rexyll/cnc-knowledge/actions/runs/45584153406) completed/success，知识结构与数据质量、CH12数值回归两个Job均成功。
- **BOM日期修正提交：** `0cb9514d30f2874dc5f642ae7704b94578b15d13`；GitHub Actions [Run 45584246386](https://github.com/rexyll/cnc-knowledge/actions/runs/45584246386) completed/success，两个Job均成功。
- **计划/索引同步提交：** `4121f6777a2bce84e42e012375688c4ef6e80aed`；GitHub Actions [Run 45584345318](https://github.com/rexyll/cnc-knowledge/actions/runs/45584345318) completed/success，两个Job均成功。
- **状态与遗留：** 数据集清单保持DRAFT，未获企业批准/冻结；未开发或执行自动fixture validator；22项环境检查仍NOT_ASSESSED；30项测试仍NOT_RUN。未连接ERP/WMS/QMS/CMMS/EAM，未执行企业SIT/UAT、生产影子、HIL或实机验证。后续需先完成本地fixture validator，并取得获批的隔离非生产环境后再运行测试。
