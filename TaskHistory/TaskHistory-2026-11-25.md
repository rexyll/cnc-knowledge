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
- **提交与CI：** 本次提交和GitHub Actions结果将在提交后补录。
