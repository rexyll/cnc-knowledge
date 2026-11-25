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
