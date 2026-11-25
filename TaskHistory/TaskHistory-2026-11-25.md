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

## CH17-T004 备件合成夹具本地静态校验工具第七轮

- **实际完成时间：** 2026-11-25T17:47:31+08:00（Asia/Shanghai；最终CI全部通过）
- **所在分支：** `main`（未创建其他分支）
- **新增工具：** `scripts/spare_parts_fixture_validator.py`，使用Python标准库，默认只读验证，不访问网络、不连接ERP/WMS/QMS/CMMS/EAM，不执行采购/库存/维修事务。
- **新增测试：** `tests/test_spare_parts_fixture_validator.py`，包含9项专项单元测试：真实基线通过、重复Fixture ID、悬空父引用、缺失用例、BOM重叠、缺失事件时间、JSON报告CLI、CSV列宽损坏、用例映射双向引用不一致。仓库全量unittest共14项通过。
- **验证规则：** manifest/CSV表头和行宽；数据集ID/版本/纯合成声明；89个Fixture/Event ID唯一；parent/related引用完整；test_case_id有效；SPAT-001～SPAT-030与源测试矩阵分类/标题/前置条件/执行状态一致；正/负Fixture与事件引用存在且双向test_case_ids一致；BOM修订时间窗带时区且不重叠；事件ID、业务时间/接收时间、正序号、延迟/乱序显式标记及reset group序号唯一。
- **夹具数据修正：** 补齐22个事件的业务时间与接收时间；重复收货重放及迟到冲销明确关联原始收货事件；正式PCN和来源不明EOL线索采用独立reset group；根据30项用例映射反向补齐各Fixture的test_case_ids。数据仍为固定合成样例。
- **静态校验结果：** 10项检查全部PASS、0 errors；89条夹具记录（67对象+22事件）、89个唯一ID、30项用例映射、2个BOM修订、17个reset group，5条延迟投递和1条显式乱序事件。验证报告保留5项warning：数据集DRAFT、无获批企业环境、无获批测试层级、30项测试仍NOT_RUN、manifest内容校验值pending。
- **报告归档：** CLI支持JSON输出；本地报告命令将报告写入 `resouces/17-operation-maintenance-and-repair/generated/spare-parts-fixture-validation-report-v1.json`。CI上传同路径报告Artifact：[下载Run 45588745895验证报告](https://github.com/rexyll/cnc-knowledge/actions/runs/45588745895/artifacts/15008764661)。生成报告不更改测试状态，也不代表企业验收。
- **实施/数据修正提交：**
  - `2375517199ba6bd744d0b75c7c1b99f58abb5e24`（事件时间、PCN reset group等修正），[Run 45587839338](https://github.com/rexyll/cnc-knowledge/actions/runs/45587839338) completed/success。
  - `d885c17ded62aebcd7edec529539d11cc7592f22`（校验器、测试与CI集成初版），[Run 45588189699](https://github.com/rexyll/cnc-knowledge/actions/runs/45588189699) 首轮有1项单元测试断言文案不匹配，未通过；该失败已记录并修正。
  - `235497e56860ebd2b5b14465f8b25f42c12c0e47`（修正诊断信息），[Run 45588285648](https://github.com/rexyll/cnc-knowledge/actions/runs/45588285648) completed/success。
- **计划/索引/报告路径同步提交：** `0a9559ce47b265b6643529e53ffe43cb5e5fa664`，更新根计划、CH17计划（6.14）、章节/资源README、docs导航、覆盖度和CI报告路径；[Run 45588555063](https://github.com/rexyll/cnc-knowledge/actions/runs/45588555063) completed/success。
- **回归测试强化提交：** `b5d677e4eb67e16bd31166adc4bfad6f779ca958`，新增CSV列宽损坏、映射双向引用异常测试，并验证CLI子进程报告输出；修正KNOW-000032中的报告命令路径。GitHub Actions [Run 45588745895](https://github.com/rexyll/cnc-knowledge/actions/runs/45588745895) completed/success：14/14 unittest、Knowledge structure and data quality、CH12 numerical resource tests均通过。
- **状态与遗留：** CH17-T004继续IN_PROGRESS。静态夹具验证已完成，但数据集依然DRAFT，22项企业环境检查仍NOT_ASSESSED，30项备件业务测试仍NOT_RUN；没有企业授权非生产环境、SIT/UAT、生产影子、HIL或实机验证。下一阶段需先由企业数据/系统/安全责任角色审批并冻结数据集与环境，再逐项执行测试并保留实际证据。

## CH17-T004 备件测试场景重置配置与本地fixture loader第八轮

- **实际完成时间：** 2026-11-25T17:54:45+08:00（Asia/Shanghai；30场景本地打包及两个CI Job完成后补录）
- **所在分支：** `main`（未创建其他分支）
- **新增重置配置：** `resouces/17-operation-maintenance-and-repair/spare-parts-synthetic-fixture-reset-profiles-v1.csv`（ASSET-000044，30行/15列），逐用例登记正向/负向夹具、事件、依赖闭包、reset group、装载/清理策略、稳定幂等键、执行状态及FILESYSTEM_STAGING_ONLY范围。配置由标准用例映射和夹具父/关联依赖确定性生成；loader运行时重新推导并比对。
- **新增工具：** `scripts/spare_parts_fixture_loader.py`，纯Python标准库本地文件包生成器。运行前复用KNOW-000032静态验证；校验30份重置配置；递归装入父/关联依赖闭包；对象按父先子后拓扑排序，事件按接收时间/序号排序；为选定场景输出独立文件包。若目标场景目录已存在则拒绝覆盖。
- **每个场景包：** `scenario-manifest.json`（数据集/用例/源文件哈希/生成文件哈希）；`fixtures.csv`（有序全集）；`objects.csv`、`events.csv`；`load-plan.json`（适配器NOT_IMPLEMENTED、仅计划）；`reset-plan.json`（PLAN_ONLY、反向本地包清理顺序、未执行）。
- **安全边界：** loader只写用户指定的本地输出目录，不连接或写入数据库、API、事件队列、ERP、WMS、CMMS、EAM、QMS或CNC硬件；不执行企业系统导入、事务、重置或删除。清理范围仅为生成的本地场景包，不包含外部系统数据。所有30个源测试状态继续NOT_RUN。
- **新增测试：** `tests/test_spare_parts_fixture_loader.py` 8项测试，覆盖单场景、全30场景生成、父子依赖顺序、PLAN_ONLY及逆序清理、未知场景、拒绝覆盖、重置配置篡改、源夹具只读。CI全量单元测试共22项通过。
- **CI全量行为：** Knowledge Quality Job先执行22项unittest、静态夹具校验和严格知识库lint，再生成SPAT-001～SPAT-030全部30个本地场景包；包全部输出到Runner临时目录并作为Artifact上传。日志确认 `STAGED: 30 local package(s)`、external connections=NO、mutations=NO。
- **实施提交：** `0505bba51ad455e839a4159049e2d2d2fd3106ed`；[Run 45589600573](https://github.com/rexyll/cnc-knowledge/actions/runs/45589600573) completed/success，22项测试通过，知识结构/数据质量Job通过。
- **计划/文档/CI同步提交：** `c9163756363309a2f8e056fac2938cb95b136c6a`；新增CH17任务6.15，更新根TaskPlan、KNOW-000032、CH17/Docs/Resource README、ASSET-INDEX、coverage及CI全量打包和Artifact上传；[Run 45589763906](https://github.com/rexyll/cnc-knowledge/actions/runs/45589763906) completed/success，Knowledge structure and data quality与CH12 numerical resource tests两个Job均成功。
- **CI产物：** [30个场景包Artifact](https://github.com/rexyll/cnc-knowledge/actions/runs/45589763906/artifacts/15009054417)；[静态校验报告Artifact](https://github.com/rexyll/cnc-knowledge/actions/runs/45589763906/artifacts/15009508463)。Artifact用于审查和本地/测试环境适配准备，不是企业数据导入结果。
- **结构化登记：** 新增ASSET-000044，CH17覆盖度调整为12篇KNOW、39个登记实体、37项资源记录、SRC去重9条。30行重置配置字段/列数与ASSET-INDEX一致。
- **状态与遗留：** CH17-T004保持IN_PROGRESS。合成数据集仍DRAFT，22项企业环境就绪检查仍NOT_ASSESSED，30项业务测试仍NOT_RUN；尚无企业批准的非生产环境，目标系统适配器未开发，未执行SIT/UAT、生产影子、HIL或实机验证。下一步需先取得企业数据/系统/安全责任角色批准，再按目标系统设计适配器和执行证据闭环。

## CH17-T004 场景包完整性校验与离线事件期望投影第九轮

- **实际完成时间：** 2026-11-25T18:07:00+08:00（Asia/Shanghai）
- **所在分支：** `main`（未创建其他分支）
- **新增执行器：** `scripts/spare_parts_scenario_runner.py`。从固定数据集、30项用例映射和场景重置配置确定性重建每个场景包，逐字节核对六份输出文件；检查源文件及生成文件SHA-256、夹具/对象/事件身份、依赖闭包、纯合成标记、事件分区、目录结构和加载/接收顺序。缺失/额外文件、内容漂移、符号链接及未知事件类型失败关闭。
- **离线事件契约：** 对22类合成事件定义显式处理类型：期望库存桶增量、重复消息幂等零增量、恢复/冲销零增量，以及非库存事件不改库存桶。重复消息需引用原始收货事件；迟到冲销保留原始事件引用；乱序事件需有明确标记且实际呈现业务时间回退。
- **库存投影边界：** 使用Python `Decimal` 投影夹具声明的期望数量增量，按 `reset_group` 隔离输出，不跨组求和、不输出全局库存余额。当前数据集没有获批期初库存快照和企业库存桶语义，执行器不计算期末库存/可用量，也不把预期夹具值当作实际交易。
- **结果状态语义：** `simulation_status=PASS`仅表示包完整性和期望事件投影符合静态约束；报告始终写入 `business_rule_assertions=NOT_EVALUATED`、`business_test_status=NOT_RUN`。执行器无数据库/API/队列适配器，无业务写操作，不访问CNC硬件。
- **新增测试：** `tests/test_spare_parts_scenario_runner.py` 11项专项测试，覆盖30包全量运行、单场景重复事件零增量、reset group隔离、迟到冲销与乱序标记、包篡改/缺失文件拒绝、未知事件拒绝、重复消息非零增量拒绝、非库存事件库存桶修改拒绝、源夹具只读和CLI JSON报告。CI全量单元测试共33项通过。
- **实施/CI集成提交：** `f283d903eb818831fd7a573845dce1894b0f75e5` 新增执行器与首版测试；`bb6bee5df5cc1c5fb2c199c50705f7a80741bb54`强化事件契约回归、符号链接检查并集成CI执行与报告Artifact。GitHub Actions [Run 45592581657](https://github.com/rexyll/cnc-knowledge/actions/runs/45592581657) completed/success：33/33 unittest通过；静态夹具校验通过；30个包全部生成；离线模拟 `RESULT: PASS; simulated=30; failed=0`；Knowledge Quality与CH12数值资源两个Job均成功。
- **CI产物：** [静态夹具校验报告](https://github.com/rexyll/cnc-knowledge/actions/runs/45592581657/artifacts/15011722205)；[30个独立场景包](https://github.com/rexyll/cnc-knowledge/actions/runs/45592581657/artifacts/15011677420)；[离线期望事件投影报告](https://github.com/rexyll/cnc-knowledge/actions/runs/45592581657/artifacts/15011981592)。
- **正文/索引/计划同步：** `cae586530cdb07b7b522159cde45b2937577e022`更新KNOW-000032、夹具基线正文第9节、CH17和Docs导航、资源README、根TaskPlan、CH17 TaskPlan 6.16和coverage；`9262fa7ad80ac074b634051da7f64a19828f05cf`修正本地运行命令示例。同步提交的GitHub Actions [Run 45592782629](https://github.com/rexyll/cnc-knowledge/actions/runs/45592782629) completed/success，两个Job均通过。
- **结构化覆盖统计：** CH17维持12篇KNOW、39个登记实体、37项资源记录、SRC去重9条；新增代码工具不增加技术知识文章或测试资产实体。
- **状态与遗留：** CH17-T004仍为IN_PROGRESS。数据集为DRAFT，22项企业环境就绪检查仍NOT_ASSESSED，30项企业业务测试仍NOT_RUN；离线模拟没有评估业务规则，不代表SIT/UAT、生产影子、HIL或实机验证。后续若要验证真实库存守恒和业务断言，必须先取得企业批准的非生产环境、SoR/库存口径、期初快照和独立业务预期，再开发明确授权的系统适配器。
## CH17-T004 独立库存状态机内核与双边转移契约第十轮

- **实际完成时间：** 2026-11-25T20:35:00+08:00（Asia/Shanghai）
- **所在分支：** `main`（未创建其他分支）
- **新增内核：** `scripts/spare_parts_inventory_state_model.py`。实现独立、纯内存的双边账户转移：来源/目标账户必须明确且不同，数量必须为有限正数，单位必填，来源余额不得为负，转移前后数量总和必须相等；失败操作不修改输入状态。无数据库/API/队列/ERP/WMS/CMMS连接和写操作。
- **新增契约资源：** `spare-parts-inventory-state-transition-contract-v1.csv`（ASSET-000045，22类事件）。为每类事件预留来源账户、目标账户、数量字段、单位、守恒维度、批准人和批准依据。当前22项全部`NOT_APPROVED`，不从单桶expected delta推断双边账户。
- **模型输入缺口：** 现有夹具仅提供单桶`expected_inventory_bucket + expected_quantity_delta`，不足以确定完整的转入/转出分录；库存快照只在说明文本中给出汇总值，缺少按物料/批次/库位维度的期初余额。预留/分配语义、外部供应商/报废账户、退料和冲销规则也需要企业数据所有者批准。因此当前模型执行状态为`BLOCKED`是预期门禁，不是CI错误。
- **新增测试：** `tests/test_spare_parts_inventory_state_model.py`新增9项，覆盖内部转移守恒、输入不可变、来源余额不足、负数/零/非有限数量拒绝、账户校验、单位校验、失败原子性和22项审批门禁。
- **CI实施提交：** `a0a364bdab25e834505bf7f234112a133dbe2159`新增内核、测试与22类契约；`59b033782afb0dc38b748097cf8f41bcbb9c48d5`集成CI、资源登记、ASSET-000045、正文第10节、TaskPlan第6.17节和coverage；首轮CI因CSV列错位失败并已记录；`e620c38802bf6b3ace4912aeb74637e97d6fa3ad`修正契约CSV字段位置。
- **CI验收：** GitHub Actions [Run 45614737126](https://github.com/rexyll/cnc-knowledge/actions/runs/45614737126) completed/success；Knowledge Quality与CH12 numerical resource tests两个Job均成功；全量单元测试42/42通过；22类契约读取成功，报告`execution_status=BLOCKED`、`business_rule_assertions=NOT_EVALUATED`；此前CSV列错位失败保留在CI历史，不隐藏。
- **CI产物：** [库存状态模型就绪/审批门禁报告](https://github.com/rexyll/cnc-knowledge/actions/runs/45614737126/artifacts/15022026919)；[静态夹具验证报告](https://github.com/rexyll/cnc-knowledge/actions/runs/45614737126/artifacts/15022166087)；[30个场景包](https://github.com/rexyll/cnc-knowledge/actions/runs/45614737126/artifacts/15022265662)；[离线事件期望投影报告](https://github.com/rexyll/cnc-knowledge/actions/runs/45614737126/artifacts/15021792830)。
- **覆盖统计：** CH17更新为12篇KNOW、40个登记实体、38项资源记录、SRC去重9条。新增ASSET-000045为待批准契约资源；未新增技术知识文章。
- **遗留与状态：** CH17-T004继续IN_PROGRESS。当前内核只证明通用双边转移的数学性质，不表示库存业务状态机已获批准或执行；22项转移契约均NOT_APPROVED，企业环境检查22项NOT_ASSESSED，30项业务测试NOT_RUN。下一阶段须由企业库存数据所有者批准账户字典、库存维度、期初快照、单位换算、预留/分配、退料、冲销和外部账户映射后，才能生成可执行期望模型。
## CH17-T004 库存账户分类、维度字典与期初状态场景设计第十一轮

- **实际完成时间：** 2026-11-25T21:25:00+08:00（Asia/Shanghai）
- **所在分支：** `main`（未创建其他分支）
- **新增候选账户字典：** `spare-parts-inventory-account-catalog-candidates-v1.csv`（ASSET-000046），13类候选账户，区分内部实物数量账户、外部对方账户、非实物备忘/承诺账户和观察记录。预留/分配不默认重复计入实物库存；PO未交承诺不混入实物库存；盘点差异观察不自动调整账面。
- **新增候选维度字典：** `spare-parts-inventory-dimension-dictionary-candidates-v1.csv`（ASSET-000047），提出物料、批次、库位、所有权、质量状态、计量单位及工单/采购行等候选维度。必填性、适用范围和规范化规则均未获企业批准。
- **新增期初余额空白模板：** `spare-parts-inventory-opening-balance-template-v1.csv`（ASSET-000048），仅有表头，无预填库存数量；要求来源系统/记录、截止时点/时区、提取时间、SHA-256、单位换算版本和批准依据。
- **新增期初状态场景矩阵：** `spare-parts-inventory-opening-state-scenario-matrix-v1.csv`（ASSET-000049），覆盖SPAT-006/008/010/012/017/019/020/021/022/023的期初输入要求与候选守恒断言；均为PROPOSED_NOT_APPROVED、NOT_RUN。
- **结构化登记：** 新增ASSET-000046～ASSET-000049四项资源实体；更新ASSET-INDEX、资源README、章节README、KNOW-000032第11节、根TaskPlan、CH17 TaskPlan第6.18节和CHAPTER-COVERAGE。CH17统计12篇KNOW、44个登记实体、42项资源记录、SRC去重9条。
- **CI验收：** GitHub Actions [Run 45617936840](https://github.com/rexyll/cnc-knowledge/actions/runs/45617936840) completed/success；Knowledge structure and data quality与CH12 numerical resource tests两个Job均成功；全量单元测试42/42通过；22类转移契约继续全部NOT_APPROVED，库存模型就绪状态仍为BLOCKED。
- **CI产物：** [库存状态模型就绪/审批门禁报告](https://github.com/rexyll/cnc-knowledge/actions/runs/45617936840/artifacts/15022767310)。
- **边界与遗留：** 本轮只建立候选账户/维度结构和期初输入模板，不推断企业库存政策、不填充期初数量、不启用双边转移契约、不计算业务期末库存。企业库存数据所有者仍需批准账户字典、维度组合、所有权/质量状态、单位换算、预留/分配语义、期初快照及外部账户。数据集DRAFT、22项环境检查NOT_ASSESSED、30项业务测试NOT_RUN；CH17-T004继续IN_PROGRESS。

## CH17-T004 多维库存余额内核与事件回放第十二轮（2026-11-25）

- 实际完成时间：2026-11-25T22:10:00+08:00（Asia/Shanghai）。
- 所在分支：main（未创建新分支）。
- 新增 scripts/spare_parts_multidimensional_inventory.py：余额键包含账户、物料、批次、库位、所有权、质量状态和单位；Decimal数量；同物料/批次/库位/所有权/单位的双边转移守恒；跨库位、物料、批次、所有权和单位变化拒绝由普通转移隐式完成。
- 单位换算门禁：显式UnitConversion接口必须提供APPROVED状态、批准人和批准依据，换算因子必须为有限正数。内核不自动应用换算、不从夹具推断BOX/EA关系；跨单位转移仍拒绝。
- 期初快照隔离：只允许synthetic_only=TRUE且snapshot_status=SYNTHETIC_TEST_ONLY的行进入测试装载器，并要求reset_group；企业生产/正式快照无法通过该入口。重复余额键拒绝，禁止静默累加。
- 事件回放：event_id唯一、sequence严格递增；整批回放使用候选账本，全部事件成功后才提交，后续失败时整批原子回滚。
- 测试与资源：新增14个专项unittest方法及ASSET-000050的17个断言场景矩阵，覆盖维度隔离、守恒、显式换算审批、合成快照门禁、事件顺序和整批原子性。
- CI：Knowledge Quality增加模型self-check与JSON Artifact；自检报告声明execution_status=BLOCKED_PENDING_ENTERPRISE_APPROVAL、business_rule_assertions=NOT_EVALUATED，不连接企业系统、不写数据库/API。
- 文档登记：更新KNOW-000032第12节、章节README、资源README、ASSET-INDEX、根TaskPlan、CH17 TaskPlan第6.19节和coverage。CH17覆盖统计12篇KNOW、45个实体、43项资源、9条去重来源。
- 遗留：22类事件转移契约、13类候选账户及候选维度均未获企业批准；期初余额模板无正式数据；30项业务测试NOT_RUN。数学自检PASS不构成企业业务验收，CH17-T004继续IN_PROGRESS。

## CH17-T004 不可变库存事件账本与时点重建第十三轮（2026-11-25）

- 实际完成时间：2026-11-25T23:10:00+08:00（Asia/Shanghai）。
- 所在分支：main（未创建新分支）。
- 新增 `scripts/spare_parts_inventory_event_ledger.py`：追加式内存账本，事件记录包含event_id、business_event_id、source_system_id、idempotency_key、business_time、ingestion_time、TRANSFER/REVERSAL类型、双边多维键、Decimal数量及冲销引用。
- 幂等与身份：同幂等键同载荷重复投递返回NO_OP；同键异载荷、不同幂等键复用event_id均拒绝。账本序号单调递增，记录只读tuple暴露。
- 迟到/乱序：按接收顺序追加保留，不覆盖原事件；余额重建按business_time与ledger_sequence排序。可选known_at_cutoff重现特定知识时点收到的事件集合；所有时间戳要求显式时区。
- 冲销：新增REVERSAL记录引用已存在TRANSFER，要求相反余额键、相同数量、业务时间不早于原事件；不修改原始事件。当前模型只支持一次完整冲销，部分冲销/多次补偿待企业定义。
- 重建与核对：从显式提供的合成期初余额重建业务截止时点投影，输出已应用事件ID和余额；失败不修改账本。禁止跨单位、跨reset group或全局库存总额汇总。
- 新增18个纯合成断言场景及专项测试；CI自检上传JSON Artifact。报告execution_status=BLOCKED_PENDING_ENTERPRISE_APPROVAL、business_rule_assertions=NOT_EVALUATED；无外部连接和数据库/API写入。
- 文档更新：KNOW-000032第13节、ASSET-000051、资源/章节README、ASSET-INDEX、CH17 TaskPlan第6.20节、根TaskPlan、coverage和本TaskHistory。
- **明确限制：** 当前为内存模拟，不是持久化WORM存储；没有签名、权限/职责分离、并发/跨进程控制、企业审计保留或消息队列交付保证。事件语义、部分冲销、SoR与期初快照审批仍待企业确认；CH17-T004继续IN_PROGRESS。

## 第十三轮CI缺陷修复记录（2026-11-25）

- 首轮CI（Run 45623563238）发现冲销重建方向重复反转，导致原余额未恢复；已修正为按REVERSAL记录中显式反向的source/destination直接入账。
- 原“知识时点可见冲销但不可见原事件”测试与账本追加顺序（冲销必须引用已存在事件）矛盾，改为验证知识截止时点尚未接收冲销时，只投影原转移，冲销仍保留在账本但不影响该时点余额。
- 保留业务时间/接收时间双截止语义，不放宽事件引用约束。

- 后续CI复核：73项全库unittest已全部通过；self-check直接脚本执行时因Python脚本入口未将仓库根目录加入sys.path而无法导入同仓库模块。已补充与既有场景运行器一致的仓库根路径初始化，修复仅涉及本地模块导入，不改变账本语义。


- 第十三轮补充：将投影核对从单纯输出重建余额改为必须与调用者显式提供的独立合成期望余额逐维比较；新增匹配与不匹配两条测试断言，避免将“成功重建”误称为“对账一致”。测试矩阵扩展为18个断言场景。

- **最终CI验收：** Run 45624471980 completed/success；Knowledge structure and data quality、CH12 numerical resource tests两个Job均success。Knowledge Job全库74个unittest方法通过；CH17库存事件账本18个专项测试方法通过；账本self-check与多维余额self-check JSON Artifact均成功上传。CI数学自检仍声明BLOCKED_PENDING_ENTERPRISE_APPROVAL、business_rule_assertions=NOT_EVALUATED。最终提交为 `f7e7c793fe780aa4d9ed6057e41b3af36f83340d`。


## 第十四轮：库存事件账本完整性链与快照恢复（2026-11-25）

- 所在分支：main（未创建新分支）。
- 新增完整性模块、13个专项单元测试和ASSET-000052测试矩阵（15个断言场景）；首轮CI中全库87项unittest均通过（既有74项+新增13项），但脚本直接执行阶段因未显式加入仓库根目录而出现ModuleNotFoundError: No module named 'scripts'。
- 已定位并修复入口导入路径初始化；后续必须重新运行CI确认模块self-check、两个workflow Job和Artifact全部成功，未把首轮失败标记为通过。
- 功能包括规范化JSON/Decimal/UTC时间编码、SHA-256事件内容摘要及前序哈希链、账本连续序号/唯一身份检查、版本化快照、前缀校验、增量回放与全量重放比较；对影响快照历史窗口的迟到事件失败关闭并要求全量重建。
- 安全边界：哈希链不等于签名/WORM，不具备外部信任根、生产持久化、访问控制或并发保护；纯合成、无企业连接/数据库API写入。CH17-T004保持IN_PROGRESS，business_rule_assertions=NOT_EVALUATED、审批门禁BLOCKED_PENDING_ENTERPRISE_APPROVAL。


- **第十四轮CI复验成功：** Run 45629680465 completed/success；Knowledge structure and data quality、CH12 numerical resource tests两个Job均success；全库87个unittest方法通过（新增13项完整性/快照专项测试通过）。完整性self-check PASS，2条事件完成哈希链封装，快照后增量回放1条并与全量重放一致；Artifact ch17-inventory-ledger-integrity-45629680465。第十四轮交付记录补齐；本轮首轮Run 45628703377的入口导入路径失败已修复，不隐藏失败历史。


# 第十五轮：库存事件账本本地持久化与故障恢复（2026-11-25）

- 所在分支：main（未创建新分支）。
- 新增本地持久化模块、11个专项单元测试、ASSET-000053及11个纯合成故障场景矩阵。
- 采用代际目录+原子CURRENT指针：每代存储账本、快照和COMMIT；完成文件flush/fsync及目录同步后发布代际，再原子切换CURRENT。恢复时校验COMMIT、文件SHA-256、账本哈希链、快照摘要及代际元数据。
- 故障注入覆盖账本写入后、快照写入后、代际目录rename后、CURRENT替换前中断；旧CURRENT仍指向上一已提交代际。另覆盖损坏文件、缺失COMMIT、未知版本、路径穿越、重复代际。
- CI Run 45631566264：Knowledge structure and data quality与CH12 numerical resource tests两个Job均completed/success；全库98个unittest方法通过（新增11项持久化故障测试）。Artifact ch17-inventory-ledger-persistence-45631566264。
- 限制：文件系统原子rename/fsync耐久性依赖运行环境；没有多进程写锁、数据库事务、WORM、签名、外部信任根或异机复制。纯临时目录合成测试，无企业系统连接或生产写入。
- CH17-T004保持IN_PROGRESS；business_rule_assertions=NOT_EVALUATED；execution_status=BLOCKED_PENDING_ENTERPRISE_APPROVAL。

# 第十六轮：库存账本并发写入控制与多进程恢复一致性（2026-11-25）

- 所在分支：main（未创建新分支）。
- 在本地持久化模块增加POSIX flock跨进程排他锁、锁超时和CURRENT代际CAS；写入全流程位于锁临界区，陈旧代际提交拒绝。
- 新增5个专项测试：双进程CAS竞争、唯一胜者/冲突、陈旧写入拒绝、锁超时、进程异常退出后锁自动释放及中断后再提交。
- 首次CI Run 45635025633：全库103个unittest通过，但Knowledge self-check入口缺少仓库根目录导入路径，失败；已补充sys.path初始化。保留失败记录，不将其视为验收通过。
- 修复后CI Run 45635237388：completed/success；Knowledge structure and data quality、CH12 numerical resource tests两个Job均success；全库103个unittest通过。并发自检PASS：2个进程、1个提交胜者、1个CAS冲突、CURRENT恢复成功。Artifact ch17-inventory-ledger-concurrency-45635237388。
- POSIX flock为协作式advisory lock；Windows原生文件锁、网络文件系统锁语义和分布式协调未验证。无企业系统连接或生产写入。
- CH17-T004保持IN_PROGRESS；business_rule_assertions=NOT_EVALUATED；execution_status=BLOCKED_PENDING_ENTERPRISE_APPROVAL。


# 第十七轮：库存账本读取一致性、并发读取与代际生命周期管理（2026-11-25）

- 所在分支：main（未创建新分支）。
- 修改 scripts/spare_parts_inventory_ledger_persistence.py：recover_current() 在指针解析、代际文件读取、摘要/哈希链/快照校验及内存恢复期间持有 .gc.lock 共享锁；避免CURRENT切换期间读取者引用的旧代际被回收。
- 新增 garbage_collect_generations()：回收器按writer lock→GC exclusive lock顺序获取锁，避免误删正在发布或正在读取的代际；每次删除前重读CURRENT。
- 生命周期策略：始终保留CURRENT、最近N个有效代际和未达到最短保留时间的代际；只处理COMMIT与账本/快照SHA-256均有效的目录。默认dry-run，只有CLI显式 --gc-apply 才删除；先原子rename到 .gc-trash-*，异常退出后的trash可由后续显式apply回收；.staging-* 保留人工检查。
- 新增CLI入口：--gc-root输出计划，--gc-apply才执行；默认保留最近3代且最短保留7天，可显式调整 --keep-last / --minimum-age-seconds。调用者应审阅dry-run清单并确认备份与企业留存政策后再apply。
- 新增ASSET-000055：读取一致性与代际回收测试矩阵10个场景；新增6项专项unittest，全库109个unittest方法通过。场景覆盖dry-run、最近N代/当前代际、最短年龄、读锁阻止GC、writer/GC协调、异常trash恢复和三进程压力。
- CI缺陷过程：首次Run 45641486782的Knowledge Job因新增多进程测试辅助函数缺少time导入失败；已补充导入，未将失败Run计为验收通过。
- 修复后Run 45641575977：completed/success，两个Job（Knowledge structure and data quality、CH12 numerical resource tests）均success；全库109个unittest通过。持久化self-check reader_gc_exclusion、dry_run_non_mutating、retention_and_recovery均PASS。
- **限制：** POSIX flock协作式本地临时目录模型；Windows原生文件锁、NFS/SMB网络文件系统、跨主机分布式协调、企业备份/保留时限/删除审批均未验证。无企业数据库/API连接、无生产写入。business_rule_assertions仍NOT_EVALUATED，execution_status仍BLOCKED_PENDING_ENTERPRISE_APPROVAL；CH17-T004继续IN_PROGRESS。


# 第十八轮：库存账本可验证备份与隔离恢复演练（2026-11-25）

- 所在分支：main（未创建新分支）。
- 新增 create_backup()：在源账本.gc.lock共享锁保护下读取CURRENT所指有效代际，将COMMIT.json、ledger.json和snapshot.json复制到独立备份目录，生成BACKUP.json清单；每个负载记录size_bytes与SHA-256，清单自身也计算SHA-256；备份暂存目录完成fsync后原子rename发布，拒绝覆盖既有备份。
- 新增 verify_backup()：要求备份目录只含四个预期普通文件，拒绝符号链接/额外文件；验证清单哈希、负载长度/哈希、COMMIT状态/代际身份、事件哈希链、快照摘要、快照账本前缀和事件重建。
- 新增 restore_backup()：先校验备份，再仅恢复到新建或空白隔离存储；不覆盖既有数据。恢复先发布代际目录，最后原子发布CURRENT；代际发布后中断不会暴露为当前代际。
- 新增CLI：--backup-root/--backup-parent/--backup-id创建；--verify-backup验证；--restore-backup/--restore-target隔离恢复。
- 新增ASSET-000056：10个纯合成备份/恢复测试场景；新增6项专项unittest。首轮CI Run 45643219363：Knowledge structure and data quality Job成功，全库116个unittest通过；持久化self-check的备份清单/负载验证、隔离恢复、源代际GC后仍能恢复均PASS。另一CH12 Job及文档同步提交CI需最终复核。
- 严格边界：POSIX临时目录合成模型，无企业系统连接/生产写入；不含加密/签名/外部信任根、异地副本、对象存储/WORM、备份介质恢复、RPO/RTO、企业留存审批或生产灾备实测。30项企业业务测试仍NOT_RUN，business_rule_assertions仍NOT_EVALUATED，execution_status仍BLOCKED_PENDING_ENTERPRISE_APPROVAL；CH17-T004保持IN_PROGRESS。
