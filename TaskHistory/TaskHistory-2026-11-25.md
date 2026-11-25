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
