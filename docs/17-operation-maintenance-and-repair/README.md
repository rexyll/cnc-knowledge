# 17. 操作、维护与维修

**English:** Operation, Maintenance and Repair  
**范围：** 机床操作规范、开停机、加工准备、日常保养、计划维护、零部件拆装更换、备件策略和维修记录。

## 本章覆盖内容

- 操作面板、运行模式、程序装载、工件/刀具准备和状态监控
- 每日/每周/每月/年度维护、润滑、冷却液、过滤和清洁
- 部件拆卸、更换、复装、校准、参数备份和复验
- 备件管理、维修工单、保养记录、维护周期和寿命管理

## 本章任务计划

[打开本章 TaskPlan](../TaskPlan/17-operation-maintenance-and-repair/TaskPlan.md)

本章知识内容按任务计划逐步研究，不预填未经核实的技术参数或结论。第一版框架见 [机床操作、维护与维修总览](overview.md)；维修闭环见 [数控机床维修工作流、工单与维修后复验](repair-workflow-and-records.md)；计划维护体系见 [数控机床计划维护体系与维护任务管理](maintenance-management-system.md)；部件更换工作包见 [数控机床零部件更换工作包与复验框架](component-replacement-work-package.md)。 关键部件族审查见 [关键部件更换影响分析与复验矩阵](component-family-impact-assessment-and-verification.md)。 主轴/伺服/丝杠专项模板见 [主轴、伺服与滚珠丝杠专项更换工作包](spindle-servo-ballscrew-specialized-replacement-work-packages.md)。开机准备检查、维修工单、维修后复验矩阵、维护任务矩阵、维护卡和耗材登记均位于本章resouces目录。

## 建议正文结构

- `overview.md`：章节总览、概念和分类。
- `architecture.md` / `principles.md`：结构、原理和系统关系（适用时）。
- `specifications.md`：参数、型号、接口和指标（适用时）。
- `procedures/`：设计、制造、安装、操作或维护专题（适用时）。
- `cases/`：工程案例、测试和故障分析（适用时）。
- `ASSET-INDEX.md`：本章在 `resouces/17-operation-maintenance-and-repair/` 中的资源索引。

## 相关资源

本章图片、动图和有权保存的完整文档统一放在 [`resouces/17-operation-maintenance-and-repair/`](../../resouces/17-operation-maintenance-and-repair/README.md)。正文使用相对链接引用资源。外部版权受限资料只记录合法元数据和官方链接。

## 来源与审查

事实性内容需记录来源、版本、适用机型/系统、核验日期和证据等级；未知项显式标记待核实。安全、版权和保密要求遵循根目录 `TaskPlan.md`。


本轮新增 [刀库/换刀、卡盘夹持与液压气动专项更换工作包](atc-chuck-hydraulic-specialized-replacement-work-packages.md)，对应三份CSV模板位于本章 `resouces/17-operation-maintenance-and-repair/`。


备件管理与数据闭环见 [数控机床备件管理、替代审批与生命周期闭环](spare-parts-management-and-lifecycle.md)，六份备件主数据、关键度、库存补货、替代审批、生命周期及维修消耗反馈模板位于本章 `resouces/17-operation-maintenance-and-repair/`。


备件跨系统数据治理见 [数控机床备件系统集成、字段映射与数据治理](spare-parts-system-integration-and-data-governance.md)，字段映射、数据质量/对账规则和库存策略决策模板位于本章 `resouces/17-operation-maintenance-and-repair/`。


备件实物流转及事务控制见 [数控机床备件实物流转、事务控制与责任矩阵](spare-parts-physical-flow-and-transaction-controls.md)，包括生命周期控制矩阵和企业待批准的RACI责任矩阵，资源位于本章 `resouces/17-operation-maintenance-and-repair/`。


备件验收与测试证据见 [数控机床备件端到端验收场景与测试证据规范](spare-parts-end-to-end-acceptance-testing.md)，包含30个未执行测试规格和每次测试的证据记录模板；资源归档于本章 `resouces/17-operation-maintenance-and-repair/`。

备件测试数据与环境准备见 [数控机床备件合成测试数据集与环境就绪规范](spare-parts-synthetic-test-data-and-environment-readiness.md)，配套包含数据集清单、22项环境就绪检查和合成夹具对象/事件交叉引用模板；环境检查初始均为NOT_ASSESSED，不能视作已获企业授权。

备件合成测试夹具基线见 [备件合成测试夹具基线 v1.0.0](spare-parts-synthetic-fixture-baseline-v1.md)：包括89条静态对象/事件记录和SPAT-001～SPAT-030逐项映射。该数据集当前为DRAFT，所有测试仍NOT_RUN，不可视作已获企业环境批准。

备件合成夹具基线附带 [本地静态校验工具](../../scripts/spare_parts_fixture_validator.py) 和 [单元测试](../../tests/test_spare_parts_fixture_validator.py)。工具只读取本地CSV，不连接企业系统；CI会生成JSON验证报告Artifact。

备件合成夹具现提供 [30项场景重置配置](../../resouces/17-operation-maintenance-and-repair/spare-parts-synthetic-fixture-reset-profiles-v1.csv) 与 [本地场景包生成器](../../scripts/spare_parts_fixture_loader.py)。该工具仅在指定目录生成文件系统场景包和PLAN_ONLY重置计划，不连接或写入企业数据库；CI会生成全部30个场景包供审查。

备件合成夹具增加 [离线场景包校验与事件期望投影工具](../../scripts/spare_parts_scenario_runner.py)。它逐场景验证包哈希/依赖/事件顺序，并按reset_group独立列出夹具声明的数量增量。模拟结果PASS仅代表静态包和期望事件投影一致；业务规则未执行，30项测试仍NOT_RUN。

库存状态机内核见 [独立双边转移模型](../../scripts/spare_parts_inventory_state_model.py)，配套 [22类事件转移契约](../../resouces/17-operation-maintenance-and-repair/spare-parts-inventory-state-transition-contract-v1.csv) 当前均未获批准，CI只验证内核性质与审批门禁，不代表业务状态机已激活。

新增 [候选库存账户字典](../../resouces/17-operation-maintenance-and-repair/spare-parts-inventory-account-catalog-candidates-v1.csv)、[候选维度字典](../../resouces/17-operation-maintenance-and-repair/spare-parts-inventory-dimension-dictionary-candidates-v1.csv)、[期初余额空白模板](../../resouces/17-operation-maintenance-and-repair/spare-parts-inventory-opening-balance-template-v1.csv) 和 [期初状态场景矩阵](../../resouces/17-operation-maintenance-and-repair/spare-parts-inventory-opening-state-scenario-matrix-v1.csv)。这些资源只提出候选分类与数据字段，不预设企业库存账户、维度或期初数量；全部业务语义须经企业库存数据所有者批准。

新增 [多维库存余额模型测试矩阵](../../resouces/17-operation-maintenance-and-repair/spare-parts-multidimensional-inventory-model-test-cases-v1.csv)；模型实现位于 [spare_parts_multidimensional_inventory.py](../../scripts/spare_parts_multidimensional_inventory.py)，专项测试位于 [test_spare_parts_multidimensional_inventory.py](../../tests/test_spare_parts_multidimensional_inventory.py)。模型仅接受显式合成测试快照，不自动换算单位，不跨库位/物料/批次/所有权转移；企业业务规则未获批准时保持阻断。

新增 [不可变库存事件账本测试矩阵](../../resouces/17-operation-maintenance-and-repair/spare-parts-inventory-event-ledger-test-cases-v1.csv)；模型实现位于 [spare_parts_inventory_event_ledger.py](../../scripts/spare_parts_inventory_event_ledger.py)，专项测试位于 [test_spare_parts_inventory_event_ledger.py](../../tests/test_spare_parts_inventory_event_ledger.py)。事件账本仅驻留内存，使用合成事件；重复投递幂等、迟到事件保留、按业务时间重建、冲销以新事件追加；不提供企业数据库/API连接。


新增库存事件账本完整性与恢复模型（../../scripts/spare_parts_inventory_ledger_integrity.py），配套15项测试场景矩阵及专项测试。该模型用于纯合成完整性检测与增量快照回放，不是签名/WORM存储或生产审计系统。


库存账本持久化新增 [读取一致性、并发读取与旧代际回收](spare-parts-synthetic-fixture-baseline-v1.md#17-库存账本读取一致性并发读取与代际生命周期)：recover_current() 通过POSIX共享锁保护代际加载，GC默认dry-run、至少保留CURRENT与最近N代，并要求显式 --gc-apply 删除。该功能仅用于合成数据的本地临时存储验证。
