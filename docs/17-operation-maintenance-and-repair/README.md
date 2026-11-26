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


库存账本新增 [可验证备份与隔离恢复演练](spare-parts-synthetic-fixture-baseline-v1.md#18-库存账本可验证备份与隔离恢复演练)：提供备份导出、清单/文件SHA-256校验和空白隔离目录恢复接口；不覆盖既有目标存储，备份目录必须与源存储分离。该实现仅通过本地POSIX合成测试。


库存备份治理与灾备就绪规范见 [备件库存账本备份治理、RPO/RTO与恢复验收](spare-parts-inventory-backup-governance.md)（KNOW-000033）；包含保留/删除、RPO/RTO、安全密钥、异地存储和10项恢复演练验收条件，企业政策数值均留空待批准。

- [库存账本备份存储适配器契约与Mock验证](spare-parts-inventory-backup-storage-adapter.md)（KNOW-000034）

- [库存账本备份 Provider 身份权限、分块续传与孤儿回收治理](spare-parts-inventory-backup-provider-security-and-resilience.md)（KNOW-000035）

- [备份 Provider 重试、一致性与模糊提交恢复](spare-parts-inventory-backup-provider-retry-consistency-and-recovery.md)（KNOW-000036）

- [备份 Provider 熔断、半开探测、舱壁与总重试预算](spare-parts-inventory-backup-provider-circuit-breaker-bulkhead-and-budget.md)（KNOW-000037）

- [备份Provider公平调度、租户配额与任务取消/截止时间](spare-parts-inventory-backup-provider-fair-scheduling-and-tenant-isolation.md)（KNOW-000038）；配套15项合成测试场景矩阵位于本章 `resouces/`。

- [备份Provider多实例共享协调、租户配额与租约恢复](spare-parts-inventory-backup-provider-shared-coordination-and-lease-recovery.md)（KNOW-000039）；配套24项共享协调模拟场景矩阵位于本章 `resouces/`。


- [备份Provider协调器故障注入、失败关闭与恢复](spare-parts-inventory-backup-provider-shared-coordination-and-lease-recovery.md)（KNOW-000040）；与KNOW-000039共用ASSET-000070矩阵，覆盖协调器不可用、响应丢失、租约校验/释放失败及恢复路径；全部合成场景NOT_RUN。


- [备份 Provider 准入队列容量保护与恢复](spare-parts-inventory-backup-provider-admission-queue-bounds-and-recovery.md)（KNOW-000041）；新增7项本地/共享队列上限、故障中断和恢复后重新准入合成场景（ASSET-000071），全部NOT_RUN。


- [备份 Provider 持久化准入协调器与幂等租约](spare-parts-inventory-backup-provider-sqlite-persistent-admission-coordinator.md)（KNOW-000042）；使用SQLite WAL/BEGIN IMMEDIATE验证同主机多进程原子准入、租约恢复、request_id幂等和持久fencing序列；新增10条合成验收场景（ASSET-000072）。


- [备份 Provider fencing 契约与 SQLite 安全恢复](spare-parts-inventory-backup-provider-fencing-and-sqlite-recovery.md)（KNOW-000043）；定义下游原子陈旧写入防护与本地SQLite在线备份/新库恢复门禁，配套16条合成场景（ASSET-000073/000074），均未批准/未执行。


- [备份 Provider 适配器 fencing token 贯穿与备份包范围原子提交](spare-parts-inventory-backup-provider-adapter-fencing-integration.md)（KNOW-000044）；显式严格模式下覆盖payload、multipart与receipt-last写入，ASSET-000075定义12条合成场景，均未批准/未执行。


- [备件库存备份 SQLite fenced Provider 参考实现、主体授权与恢复门禁](spare-parts-inventory-backup-provider-sqlite-fenced-reference.md)（KNOW-000045）；同主机SQLite事务内原子提交scope高水位、对象/multipart及幂等回执，ASSET-000076定义22条形式化参考场景，均未批准/未执行。

- [Coordinator签发的scope-bound fencing attestation、Provider验签与密钥轮换](spare-parts-inventory-backup-provider-fencing-attestation-and-key-rotation.md)（KNOW-000046）；默认15秒HMAC proof绑定lease/tenant/scope/resource/operation/idempotency；ASSET-000077定义20条形式化参考场景，均未批准/未执行。

- [Provider Ed25519 公钥验签、KMS 签名回调与在线租约状态检查](spare-parts-inventory-backup-provider-ed25519-and-online-revocation.md)（KNOW-000047）；Ed25519 v2签名与本地Coordinator在线lease状态检查已实现，在线检查不可用时fail-closed；跨数据库status check到Provider commit仍有TOCTOU竞态。ASSET-000078定义22条参考验收场景，均未批准/未执行。
- [SQLite 同库原子 lease 撤销与 Provider 写入顺序](spare-parts-inventory-backup-provider-atomic-lease-revocation.md)（KNOW-000048）；可选同库事务模式复用Provider BEGIN IMMEDIATE连接校验lease，使Coordinator release与对象/multipart写入串行化；要求同一主机、本地SQLite文件。ASSET-000079定义12条形式化场景，均未批准/未执行。代码CI Run 45762883991与文档同步Run 45762994591均两个必需Job success，全库254项和CH12 143项测试通过，strict lint 0 errors/5 warnings。
- [远程 Coordinator 与对象存储 Provider 的分布式 fencing 提交协议](spare-parts-inventory-backup-provider-distributed-fencing.md)（KNOW-000049）；以同一个scope control object的ETag/generation CAS作为activation、revoke和manifest publish线性化点；payload先不可变staging，最终通过manifest pointer发布。ASSET-000080定义20条参考场景，均未批准/未执行。当前仅有内存CAS模型，未接入真实云SDK或远程Coordinator。


- [备件库存备份 Coordinator 持久权威、Leader 切换与故障恢复](spare-parts-inventory-backup-provider-coordinator-durable-authority-and-recovery.md)（KNOW-000050）；在本地SQLite WAL参考层持久分配租户scope token与publish operation sequence，增加Leader epoch门禁、activation/revocation两阶段Provider确认及崩溃恢复；ASSET-000081为16条场景，全部未批准/未执行。非多主机共识实现。


- 第三十六轮新增 [Coordinator 持久权威、Leader 切换与故障恢复](spare-parts-inventory-backup-provider-coordinator-durable-authority-and-recovery.md)（KNOW-000050）。代码Run 45769331991、文档同步Run 45769584662均通过；全库283项测试和CH12 143项测试通过。ASSET-000081的16条场景仍未批准/未执行；当前实现仅为同机SQLite WAL参考，不是多主机协调服务。


- [Coordinator 权威存储后端契约与 etcd v3 适配设计](spare-parts-inventory-backup-provider-coordinator-backend-contract-and-etcd-v3.md)（KNOW-000051）；定义线性一致Get、CAS多键Txn和Lease端口，提供SQLite参考适配器与注入式etcd v3接口；ASSET-000082包含20条待批准/未执行场景。没有真实etcd多主机集群接入。


- 第三十七轮新增 [Coordinator 权威存储后端契约与 etcd v3 适配设计](spare-parts-inventory-backup-provider-coordinator-backend-contract-and-etcd-v3.md)（KNOW-000051）。代码Run 45770717942与文档Run 45770955018均通过（全库300项、CH12 143项）；但etcd仅为注入式driver适配器，无真实集群连接。ASSET-000082的20条场景仍未批准/未执行。


Coordinator 权威状态迁移基础见 [事务内有序读取与状态快照](spare-parts-inventory-backup-provider-coordinator-transactional-read-batches.md)（KNOW-000052）：新增Txn分支内精确键Get/Put/Delete有序读取契约；ASSET-000083包含16条待批准/未执行场景。现有SQLite业务状态机和Admission lease仍未迁移到通用Store，etcd仅为注入式driver适配器。

第三十八轮文档同步CI Run 45772844275（提交 a1548dad6ad1c47d4645600a162a866076de6993）两个必需Job均completed/success：304项全库unittest、CH12 143项测试、strict lint 0 errors/5 warnings、知识结构质量0 errors。ASSET-000083场景仍待批准/未执行。


Admission lease 统一事务参考模型见 [Admission Lease Authority 与Coordinator统一事务存储](spare-parts-inventory-backup-provider-admission-lease-authority-store.md)（KNOW-000053）：提供基于CoordinatorAuthorityStore的lease创建、续租、释放、单调fencing token及可纳入authority Txn的双键guard；ASSET-000084包含20条待批准/未执行场景。该组件尚未替代旧SQLite Admission排队/全局与租户配额调度器，也未接入SQLite Coordinator领域状态机。

第三十九轮文档同步CI Run 45776156101（提交 b79aede8a06cc55ac60681cbfc9acf03b1f44a55）两个必需Job均completed/success：314项全库unittest、CH12 143项测试、strict lint 0 errors/5 warnings、知识结构质量0 errors。ASSET-000084场景仍待批准/未执行。

第三十九轮最终元数据CI Run 45776292616两个必需Job均completed/success：314项全库unittest、CH12 143项测试、strict lint 0 errors/5 warnings、知识结构质量0 errors。生产备份关闭，企业场景仍待批准/执行。


Admission调度与配额统一事务参考模型见 [Unified Admission Scheduler 与配额状态统一事务模型](spare-parts-inventory-backup-provider-unified-admission-scheduler-and-quota-state.md)（KNOW-000054）：将global/tenant quota、跨domain公平等待队列、fencing token和活动Lease收敛到一个revisioned aggregate Txn；ASSET-000085有24条待批准/未执行场景。单aggregate存在全局写入串行热点；旧SQLite Admission及Coordinator服务尚未切换，真实etcd未连接。

第四十轮文档同步CI Run 45778328441（提交 87d749147d2c32da547ce23ed56db69725271a00）两个必需Job均completed/success：328项全库unittest、CH12 143项测试、strict lint 0 errors、知识结构与数据质量0 errors（5条非阻断warning）。ASSET-000085场景仍待批准/未执行。

第四十轮文档同步CI Run 45778328441（提交 87d749147d2c32da547ce23ed56db69725271a00）两个必需Job均completed/success：328项全库unittest、CH12 143项测试、strict lint 0 errors、知识结构与数据质量0 errors（5条非阻断warning）。ASSET-000085场景仍待批准/未执行。
